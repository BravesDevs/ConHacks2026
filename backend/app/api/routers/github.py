from __future__ import annotations

import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import encrypt_token
from app.db.session import get_db
from app.models.github_connection import GitHubConnection
from app.schemas.github import GitHubConnectionOut, OAuthCallbackOut, TrackReposIn
from app.services.events import event_bus


router = APIRouter(prefix="/github", tags=["github"])


GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_OAUTH_SCOPES = "repo read:user"


@router.get("/auth")
async def auth() -> RedirectResponse:
    settings = get_settings()
    if not settings.github_client_id or not settings.github_redirect_uri:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="oauth_not_configured")

    state = secrets.token_urlsafe(24)
    qs = urlencode(
        {
            "client_id": settings.github_client_id,
            "redirect_uri": settings.github_redirect_uri,
            "scope": GITHUB_OAUTH_SCOPES,
            "state": state,
            "allow_signup": "false",
        }
    )
    return RedirectResponse(url=f"{GITHUB_AUTHORIZE_URL}?{qs}", status_code=307)


@router.get("/callback", response_model=OAuthCallbackOut)
async def callback(
    code: str = Query(...),
    state: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> OAuthCallbackOut:
    if not code:
        raise HTTPException(status_code=400, detail="missing_code")

    settings = get_settings()
    if (
        not settings.github_client_id
        or not settings.github_client_secret
        or not settings.github_redirect_uri
        or not settings.github_token_encryption_key
    ):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="oauth_not_configured")

    async with httpx.AsyncClient(timeout=10.0) as client:
        token_res = await client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": settings.github_redirect_uri,
                "state": state or "",
            },
        )
        if token_res.status_code != 200:
            raise HTTPException(status_code=400, detail="oauth_exchange_failed")
        token_data = token_res.json()
        access_token = token_data.get("access_token")
        if not access_token:
            detail = token_data.get("error_description") or token_data.get("error") or "oauth_exchange_failed"
            raise HTTPException(status_code=400, detail=detail)

        user_res = await client.get(
            GITHUB_USER_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {access_token}",
            },
        )
        if user_res.status_code != 200:
            raise HTTPException(status_code=502, detail="github_user_fetch_failed")
        login = user_res.json().get("login")
        if not login:
            raise HTTPException(status_code=502, detail="github_user_login_missing")

    encrypted = encrypt_token(access_token)

    res = await db.execute(select(GitHubConnection).where(GitHubConnection.user_id == login))
    conn = res.scalar_one_or_none()
    if conn is None:
        conn = GitHubConnection(user_id=login, encrypted_token=encrypted, tracked_repos=[])
        db.add(conn)
    else:
        conn.encrypted_token = encrypted
    await db.commit()
    await db.refresh(conn)

    await event_bus.publish("github.connected", {"type": "github.connected", "user_id": login})
    return OAuthCallbackOut(user_id=login, tracked_repos=list(conn.tracked_repos or []))


@router.post("/repos/track", response_model=GitHubConnectionOut)
async def track_repos(
    body: TrackReposIn,
    db: AsyncSession = Depends(get_db),
) -> GitHubConnectionOut:
    # auth: open for MVP; gate behind a bearer or session token once user auth lands.
    res = await db.execute(select(GitHubConnection).where(GitHubConnection.user_id == body.user_id))
    conn = res.scalar_one_or_none()
    if conn is None:
        raise HTTPException(status_code=404, detail="connection_not_found")

    conn.tracked_repos = sorted(set(body.repos))
    await db.commit()
    await db.refresh(conn)

    await event_bus.publish(
        "github.repos.tracked",
        {"type": "github.repos.tracked", "user_id": body.user_id, "repos": list(conn.tracked_repos)},
    )
    return GitHubConnectionOut.model_validate(conn)
