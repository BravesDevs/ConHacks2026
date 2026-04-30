from __future__ import annotations

import json
import logging
import re
import uuid
from urllib.parse import quote
from xml.etree.ElementTree import Element, SubElement, tostring

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.rest import Client as TwilioClient

from app.core.config import get_settings
from app.core.security import decrypt_token
from app.db.session import get_db
from app.models.enums import RunStatus
from app.models.github_connection import GitHubConnection
from app.models.optimization_run import OptimizationRun
from app.services.events import event_bus
from app.services.voice_call_service import initiate_call, resolve_phone_for_run

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])

GITHUB_REF_URL = "https://api.github.com/repos/{owner}/{repo}/git/ref/heads/{branch}"
GITHUB_REFS_URL = "https://api.github.com/repos/{owner}/{repo}/git/refs"
GITHUB_CONTENTS_URL = "https://api.github.com/repos/{owner}/{repo}/contents/{path}"
GITHUB_PULLS_URL = "https://api.github.com/repos/{owner}/{repo}/pulls"


async def _fetch_signed_url(agent_id: str, api_key: str) -> str:
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(
            "https://api.elevenlabs.io/v1/convai/conversation/get_signed_url",
            params={"agent_id": agent_id},
            headers={"xi-api-key": api_key},
        )
        if res.status_code != 200:
            raise HTTPException(status_code=502, detail="elevenlabs_signed_url_failed")
        return res.json()["signed_url"]


def _append_dynamic_vars(signed_url: str, vars_dict: dict) -> str:
    encoded = quote(json.dumps(vars_dict, separators=(",", ":")), safe="")
    sep = "&" if "?" in signed_url else "?"
    return f"{signed_url}{sep}dynamic_variables={encoded}"


async def _get_elevenlabs_signed_url(agent_id: str, api_key: str, run: OptimizationRun) -> str:
    """Signed URL with run-context dynamic variables for the OptimizationRun flow."""
    signed_url = await _fetch_signed_url(agent_id, api_key)
    return _append_dynamic_vars(
        signed_url,
        {
            "run_id": str(run.id),
            "repo": run.repo,
            "savings_summary": _truncate(run.explanation or "No explanation available."),
        },
    )


def _truncate(text: str, max_chars: int = 400) -> str:
    return text[:max_chars]


def _twiml_stream(ws_url: str) -> bytes:
    response = Element("Response")
    connect = SubElement(response, "Connect")
    SubElement(connect, "Stream", url=ws_url)
    return b'<?xml version="1.0" encoding="UTF-8"?>' + tostring(response)


@router.post("/demo/{run_id}")
async def demo_trigger(
    run_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Demo button — places the voice call immediately, bypassing the 3-6 day nudge wait.
    Use this in the dashboard 'Call me now' button during demos."""
    from datetime import datetime, timezone

    run = await db.get(OptimizationRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run_not_found")
    if run.status != RunStatus.suggestion_ready:
        raise HTTPException(
            status_code=409,
            detail=f"run_status_is_{run.status.value}_expected_suggestion_ready",
        )

    phone = await resolve_phone_for_run(db, run)
    if not phone:
        raise HTTPException(status_code=503, detail="no_phone_number_on_file")

    sid = await initiate_call(db, run)
    run.call_attempted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"call_sid": sid, "phone_number": phone, "run_id": run.id}


@router.post("/twiml/{run_id}")
async def twiml_webhook(
    run_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Twilio calls this when the customer answers. Returns TwiML that streams audio to ElevenLabs."""
    settings = get_settings()
    run = await db.get(OptimizationRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run_not_found")

    signed_url = await _get_elevenlabs_signed_url(
        settings.elevenlabs_agent_id,
        settings.elevenlabs_api_key,
        run,
    )
    return Response(content=_twiml_stream(signed_url), media_type="application/xml")


@router.post("/confirm/{run_id}")
async def confirm_merge(
    run_id: int,
    code: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Called by ElevenLabs agent after customer speaks their PIN. Creates the GitHub PR if correct."""
    settings = get_settings()

    if code.strip() != settings.call_security_code.strip():
        return {"merged": False, "reason": "incorrect_code"}

    run = await db.get(OptimizationRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run_not_found")
    if run.status != RunStatus.suggestion_ready:
        return {"merged": False, "reason": f"run_status_is_{run.status.value}"}

    # Find any stored GitHub connection to get an access token
    res = await db.execute(select(GitHubConnection).limit(1))
    conn = res.scalar_one_or_none()
    if conn is None:
        raise HTTPException(status_code=503, detail="no_github_connection")

    access_token: str | None = decrypt_token(conn.encrypted_token)
    if not access_token:
        raise HTTPException(status_code=503, detail="github_token_decrypt_failed")

    # Parse owner/repo from run.repo (expected format "owner/repo")
    parts = run.repo.split("/", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=422, detail="run_repo_format_invalid")
    owner, repo_name = parts

    # Build file content from suggested_config
    file_content = json.dumps(run.suggested_config, indent=2)
    branch_name = f"infrabott/{uuid.uuid4().hex[:8]}"
    base_branch = "main"

    import base64

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {access_token}",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        ref_res = await client.get(
            GITHUB_REF_URL.format(owner=owner, repo=repo_name, branch=base_branch),
            headers=headers,
        )
        if ref_res.status_code == 404:
            # Fall back to "master"
            base_branch = "master"
            ref_res = await client.get(
                GITHUB_REF_URL.format(owner=owner, repo=repo_name, branch=base_branch),
                headers=headers,
            )
        if ref_res.status_code != 200:
            raise HTTPException(status_code=502, detail="github_base_ref_fetch_failed")
        base_sha = (ref_res.json().get("object") or {}).get("sha")

        await client.post(
            GITHUB_REFS_URL.format(owner=owner, repo=repo_name),
            headers=headers,
            json={"ref": f"refs/heads/{branch_name}", "sha": base_sha},
        )

        encoded = base64.b64encode(file_content.encode()).decode("ascii")
        await client.put(
            GITHUB_CONTENTS_URL.format(
                owner=owner, repo=repo_name, path="infrabott-optimization.json"
            ),
            headers=headers,
            json={
                "message": "infrabott: apply optimization (voice confirmed)",
                "content": encoded,
                "branch": branch_name,
            },
        )

        pr_res = await client.post(
            GITHUB_PULLS_URL.format(owner=owner, repo=repo_name),
            headers=headers,
            json={
                "title": "InfraBott: apply Terraform optimization",
                "head": branch_name,
                "base": base_branch,
                "body": f"Voice-confirmed optimization.\n\n{run.explanation or ''}",
            },
        )
        if pr_res.status_code != 201:
            raise HTTPException(status_code=502, detail="github_pr_create_failed")
        pr_data = pr_res.json()

    run.status = RunStatus.pr_opened
    run.pr_url = pr_data["html_url"]
    await db.commit()

    await event_bus.publish(
        "run.pr_opened",
        {"type": "run.pr_opened", "repo": run.repo, "run_id": run.id, "pr_url": run.pr_url},
    )

    logger.info("PR created via voice confirmation: %s", run.pr_url)
    return {"merged": True, "pr_url": run.pr_url}


@router.post("/status")
async def call_status(request_data: dict = None) -> dict:
    """Twilio status callback — logs call outcome."""
    logger.info("Twilio call status update: %s", request_data)
    return {"ok": True}


# ---- Ad-hoc call flow (no OptimizationRun required) -------------------------
# Stash per-call context in-process so the Twilio TwiML webhook can look it up.
_ADHOC_CALLS: dict[str, dict] = {}

_E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")


class AdhocCallRequest(BaseModel):
    phone_number: str = Field(..., description="E.164 format, e.g. +15551234567")
    savings_summary: str = Field(..., min_length=1, max_length=2000)
    customer_name: str | None = None
    # Optional repo context — when provided, PIN approval will open a PR.
    github_token: str | None = None
    repo_url: str | None = None
    branch: str | None = None
    file_path: str | None = None
    file_content: str | None = None


@router.post("/call")
async def adhoc_call(payload: AdhocCallRequest = Body(...)) -> dict:
    """Place an outbound call via ElevenLabs' native Twilio integration.

    Requires the Twilio number to be imported into ElevenLabs and assigned to the agent
    (see Conversational AI > Phone Numbers in the ElevenLabs dashboard)."""
    settings = get_settings()
    phone = payload.phone_number.strip().replace(" ", "")
    if not _E164_RE.match(phone):
        raise HTTPException(status_code=422, detail="phone_number_must_be_e164")
    if not (
        settings.elevenlabs_api_key
        and settings.elevenlabs_agent_id
        and settings.elevenlabs_agent_phone_number_id
    ):
        raise HTTPException(status_code=503, detail="elevenlabs_not_configured")

    call_id = uuid.uuid4().hex
    _ADHOC_CALLS[call_id] = {
        "phone_number": phone,
        "savings_summary": payload.savings_summary,
        "customer_name": payload.customer_name or "there",
        "github_token": payload.github_token,
        "repo_url": payload.repo_url,
        "branch": payload.branch or "main",
        "file_path": payload.file_path or "infrabott-optimization.md",
        "file_content": payload.file_content,
    }

    body = {
        "agent_id": settings.elevenlabs_agent_id,
        "agent_phone_number_id": settings.elevenlabs_agent_phone_number_id,
        "to_number": phone,
        "conversation_initiation_client_data": {
            "dynamic_variables": {
                "call_id": call_id,
                "customer_name": _ADHOC_CALLS[call_id]["customer_name"],
                "savings_summary": _truncate(payload.savings_summary, max_chars=1500),
            }
        },
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(
            "https://api.elevenlabs.io/v1/convai/twilio/outbound-call",
            headers={"xi-api-key": settings.elevenlabs_api_key},
            json=body,
        )
    if res.status_code >= 300:
        logger.error("ElevenLabs outbound_call failed: %s %s", res.status_code, res.text)
        raise HTTPException(
            status_code=502,
            detail=f"elevenlabs_outbound_call_failed: {res.text[:300]}",
        )
    data = res.json()
    call_sid = data.get("callSid") or data.get("call_sid") or ""
    logger.info("ElevenLabs outbound call placed call_id=%s sid=%s to=%s", call_id, call_sid, phone)
    return {"call_id": call_id, "call_sid": call_sid, "raw": data}


@router.post("/twiml/adhoc/{call_id}")
async def adhoc_twiml(call_id: str) -> Response:
    """Twilio fetches this when the customer answers an ad-hoc call."""
    settings = get_settings()
    ctx = _ADHOC_CALLS.get(call_id)
    if ctx is None:
        raise HTTPException(status_code=404, detail="call_id_not_found")
    if not (settings.elevenlabs_agent_id and settings.elevenlabs_api_key):
        raise HTTPException(status_code=503, detail="elevenlabs_not_configured")

    signed_url = await _fetch_signed_url(
        settings.elevenlabs_agent_id, settings.elevenlabs_api_key
    )
    signed_url = _append_dynamic_vars(
        signed_url,
        {
            "call_id": call_id,
            "customer_name": ctx["customer_name"],
            "savings_summary": _truncate(ctx["savings_summary"], max_chars=1500),
        },
    )
    return Response(content=_twiml_stream(signed_url), media_type="application/xml")


@router.post("/confirm/adhoc/{call_id}")
async def adhoc_confirm(
    call_id: str,
    code: str | None = Query(default=None),
    payload: dict | None = Body(default=None),
) -> dict:
    """ElevenLabs agent calls this with the 4-digit PIN spoken by the customer.
    Accepts `code` from either the query string or the JSON body.
    If approved AND repo context was passed at call placement, also opens a PR."""
    settings = get_settings()
    ctx = _ADHOC_CALLS.get(call_id)
    if ctx is None:
        raise HTTPException(status_code=404, detail="call_id_not_found")
    submitted = (code or (payload or {}).get("code") or "").strip()
    approved = submitted == settings.call_security_code.strip()
    logger.info(
        "Ad-hoc PIN check call_id=%s submitted=%r approved=%s",
        call_id, submitted, approved,
    )

    pr_url: str | None = None
    pr_error: str | None = None
    if approved and ctx.get("github_token") and ctx.get("repo_url"):
        try:
            pr_url = await _open_pr_for_adhoc(ctx)
            logger.info("Voice-confirmed PR opened call_id=%s url=%s", call_id, pr_url)
        except Exception as e:
            pr_error = str(e)
            logger.exception("PR creation failed for call_id=%s", call_id)

    response: dict = {"approved": approved}
    if pr_url:
        response["pr_url"] = pr_url
    if pr_error:
        response["pr_error"] = pr_error
    return response


async def _open_pr_for_adhoc(ctx: dict) -> str:
    """Create a GitHub PR using the repo context stashed for this call."""
    import base64

    repo_url = ctx["repo_url"] or ""
    cleaned = repo_url.replace("https://github.com/", "").replace("http://github.com/", "")
    cleaned = cleaned.rstrip("/").removesuffix(".git")
    parts = cleaned.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"repo_url_invalid: {repo_url!r}")
    owner, repo_name = parts

    token = ctx["github_token"]
    base_branch = ctx.get("branch") or "main"
    file_path = ctx.get("file_path") or "infrabott-optimization.md"
    file_content = ctx.get("file_content") or (
        f"# InfraBott voice-confirmed optimization\n\n"
        f"**Customer:** {ctx.get('customer_name') or 'unknown'}\n\n"
        f"**Savings summary:**\n\n{ctx.get('savings_summary') or ''}\n"
    )
    branch_name = f"infrabott/voice-{uuid.uuid4().hex[:8]}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        ref = await client.get(
            GITHUB_REF_URL.format(owner=owner, repo=repo_name, branch=base_branch),
            headers=headers,
        )
        if ref.status_code == 404 and base_branch == "main":
            base_branch = "master"
            ref = await client.get(
                GITHUB_REF_URL.format(owner=owner, repo=repo_name, branch=base_branch),
                headers=headers,
            )
        if ref.status_code != 200:
            raise RuntimeError(f"github_base_ref_fetch_failed: {ref.status_code} {ref.text[:200]}")
        base_sha = (ref.json().get("object") or {}).get("sha")

        await client.post(
            GITHUB_REFS_URL.format(owner=owner, repo=repo_name),
            headers=headers,
            json={"ref": f"refs/heads/{branch_name}", "sha": base_sha},
        )

        encoded = base64.b64encode(file_content.encode()).decode("ascii")
        put_res = await client.put(
            GITHUB_CONTENTS_URL.format(owner=owner, repo=repo_name, path=file_path),
            headers=headers,
            json={
                "message": "infrabott: apply optimization (voice confirmed)",
                "content": encoded,
                "branch": branch_name,
            },
        )
        if put_res.status_code >= 300:
            raise RuntimeError(f"github_file_put_failed: {put_res.status_code} {put_res.text[:200]}")

        pr_res = await client.post(
            GITHUB_PULLS_URL.format(owner=owner, repo=repo_name),
            headers=headers,
            json={
                "title": "InfraBott: apply Terraform optimization",
                "head": branch_name,
                "base": base_branch,
                "body": (
                    f"Voice-confirmed optimization for {ctx.get('customer_name') or 'customer'}.\n\n"
                    f"{ctx.get('savings_summary') or ''}"
                ),
            },
        )
        if pr_res.status_code != 201:
            raise RuntimeError(f"github_pr_create_failed: {pr_res.status_code} {pr_res.text[:200]}")
        return pr_res.json()["html_url"]
