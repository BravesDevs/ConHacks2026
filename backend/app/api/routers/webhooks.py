from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import verify_github_signature
from app.db.session import get_db
from app.models.terraform_snapshot import TerraformSnapshot
from app.models.webhook_delivery import WebhookDelivery
from app.services.events import event_bus


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/github", status_code=204)
async def github_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> None:
    settings = get_settings()
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_github_signature(
        secret=settings.github_webhook_secret, body=body, signature_header=signature
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_signature"
        )

    delivery_id = request.headers.get("X-GitHub-Delivery", "")
    event_type = request.headers.get("X-GitHub-Event", "")
    payload = json.loads(body.decode("utf-8") or "{}")

    repo = (
        (payload.get("repository") or {}).get("full_name")
        or (payload.get("repo") or {}).get("full_name")
        or "unknown"
    )
    sha = (
        payload.get("after")
        or ((payload.get("pull_request") or {}).get("head") or {}).get("sha")
        or ""
    )
    paths: list[str] = []

    # Idempotency: store delivery record (unique constraint).
    db.add(WebhookDelivery(delivery_id=delivery_id, repo=repo, event_type=event_type))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return

    # Snapshot storage: store raw payload for now as "content".
    snap = TerraformSnapshot(
        repo=repo, sha=sha, paths=paths, content=json.dumps(payload)
    )
    db.add(snap)
    await db.commit()

    await event_bus.publish(
        "terraform.updated", {"type": "terraform.updated", "repo": repo, "sha": sha}
    )
