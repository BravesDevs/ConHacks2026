from __future__ import annotations

import base64
import binascii
import secrets
from urllib.parse import urlencode

import httpx
from cryptography.fernet import InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decrypt_token, encrypt_token
from app.db.session import get_db
from app.models.github_connection import GitHubConnection
from app.schemas.github import (
    GitHubConnectionOut,
    OAuthCallbackOut,
    RevokeOut,
    TrackReposIn,
    RepoOut,
    RevokeOut,
    TrackReposIn,
    TreeNode,
)
from app.services.events import event_bus


router = APIRouter(prefix="/github", tags=["github"])


GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_USER_REPOS_URL = "https://api.github.com/users/{username}/repos"
GITHUB_REVOKE_GRANT_URL = "https://api.github.com/applications/{client_id}/grant"
GITHUB_TREE_URL = "https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}"
GITHUB_CONTENTS_URL = "https://api.github.com/repos/{owner}/{repo}/contents/{path}"
GITHUB_OAUTH_SCOPES = "repo read:user"

bearer_scheme = HTTPBearer(auto_error=True)


@router.get("/auth")
async def auth() -> RedirectResponse:
    settings = get_settings()
    if not settings.github_client_id or not settings.github_redirect_uri:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="oauth_not_configured",
        )

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
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="oauth_not_configured",
        )

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
            detail = (
                token_data.get("error_description")
                or token_data.get("error")
                or "oauth_exchange_failed"
            )
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

    res = await db.execute(
        select(GitHubConnection).where(GitHubConnection.user_id == login)
    )
    conn = res.scalar_one_or_none()
    if conn is None:
        conn = GitHubConnection(
            user_id=login, encrypted_token=encrypted, tracked_repos=[]
        )
        db.add(conn)
    else:
        conn.encrypted_token = encrypted
    await db.commit()
    await db.refresh(conn)

    await event_bus.publish(
        "github.connected", {"type": "github.connected", "user_id": login}
    )
    return OAuthCallbackOut(user_id=login, tracked_repos=list(conn.tracked_repos or []))


@router.post("/repos/track", response_model=GitHubConnectionOut)
async def track_repos(
    body: TrackReposIn,
    db: AsyncSession = Depends(get_db),
) -> GitHubConnectionOut:
    # auth: open for MVP; gate behind a bearer or session token once user auth lands.
    res = await db.execute(
        select(GitHubConnection).where(GitHubConnection.user_id == body.user_id)
    )
    conn = res.scalar_one_or_none()
    if conn is None:
        raise HTTPException(status_code=404, detail="connection_not_found")

    conn.tracked_repos = sorted(set(body.repos))
    await db.commit()
    await db.refresh(conn)

    await event_bus.publish(
        "github.repos.tracked",
        {
            "type": "github.repos.tracked",
            "user_id": body.user_id,
            "repos": list(conn.tracked_repos),
        },
    )
    return GitHubConnectionOut.model_validate(conn)


@router.get("/repos/{username}", response_model=list[RepoOut])
async def list_user_repos(
    username: str,
    db: AsyncSession = Depends(get_db),
) -> list[RepoOut]:
    res = await db.execute(select(GitHubConnection).where(GitHubConnection.user_id == username))
    conn = res.scalar_one_or_none()
    if conn is None:
        raise HTTPException(status_code=404, detail="connection_not_found")

    try:
        access_token = decrypt_token(conn.encrypted_token)
    except InvalidToken:
        raise HTTPException(status_code=401, detail="token_decrypt_failed")

    async with httpx.AsyncClient(timeout=10.0) as client:
        gh_res = await client.get(
            GITHUB_USER_REPOS_URL.format(username=username),
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {access_token}",
            },
        )

    if gh_res.status_code == 401:
        raise HTTPException(status_code=401, detail="github_unauthorized")
    if gh_res.status_code == 404:
        raise HTTPException(status_code=404, detail="github_user_not_found")
    if gh_res.status_code != 200:
        raise HTTPException(status_code=502, detail="github_repos_fetch_failed")

    return [RepoOut.model_validate(repo) for repo in gh_res.json()]


@router.delete("/connections/{user_id}", response_model=RevokeOut)
async def revoke_connection(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> RevokeOut:
    # auth: open for MVP; gate behind a bearer or session token once user auth lands.
    settings = get_settings()
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="oauth_not_configured",
        )

    res = await db.execute(
        select(GitHubConnection).where(GitHubConnection.user_id == user_id)
    )
    conn = res.scalar_one_or_none()
    if conn is None:
        raise HTTPException(status_code=404, detail="connection_not_found")

    try:
        access_token: str | None = decrypt_token(conn.encrypted_token)
    except InvalidToken:
        access_token = None

    revoked_at_github = False
    if access_token:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.request(
                "DELETE",
                GITHUB_REVOKE_GRANT_URL.format(client_id=settings.github_client_id),
                auth=(settings.github_client_id, settings.github_client_secret),
                headers={"Accept": "application/vnd.github+json"},
                json={"access_token": access_token},
            )
        if r.status_code in (204, 404):
            revoked_at_github = True
        elif r.status_code == 401:
            raise HTTPException(status_code=502, detail="github_revoke_unauthorized")
        else:
            raise HTTPException(status_code=502, detail="github_revoke_failed")

    await db.delete(conn)
    await db.commit()

    await event_bus.publish(
        "github.disconnected",
        {
            "type": "github.disconnected",
            "user_id": user_id,
            "revoked_at_github": revoked_at_github,
        },
    )
    return RevokeOut(user_id=user_id, deleted=True, revoked_at_github=revoked_at_github)


async def _fetch_branch_tree(
    client: httpx.AsyncClient, owner: str, repo: str, branch: str, token: str
) -> dict | None:
    res = await client.get(
        GITHUB_TREE_URL.format(owner=owner, repo=repo, branch=branch),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
        },
        params={"recursive": "1"},
    )
    if res.status_code == 404:
        return None
    if res.status_code == 401:
        raise HTTPException(status_code=401, detail="github_unauthorized")
    if res.status_code == 403:
        raise HTTPException(status_code=403, detail="github_forbidden")
    if res.status_code != 200:
        raise HTTPException(status_code=502, detail="github_tree_fetch_failed")
    return res.json()


def _build_tree(entries: list[dict], root_name: str) -> dict:
    root: dict = {"name": root_name, "type": "dir", "_children": {}}
    for entry in entries:
        path = entry.get("path") or ""
        if not path:
            continue
        parts = path.split("/")
        node = root
        for i, part in enumerate(parts):
            is_last = i == len(parts) - 1
            kids = node["_children"]
            existing = kids.get(part)
            if existing is None:
                if is_last and entry.get("type") != "tree":
                    kids[part] = {"name": part, "type": "file"}
                else:
                    new_node = {"name": part, "type": "dir", "_children": {}}
                    kids[part] = new_node
                    node = new_node
            else:
                node = existing

    def finalize(n: dict) -> dict:
        out: dict = {"name": n["name"], "type": n["type"]}
        if n["type"] == "dir":
            kids = n.get("_children") or {}
            out["children"] = sorted(
                (finalize(c) for c in kids.values()),
                key=lambda x: (x["type"] != "dir", x["name"]),
            )
        return out

    return finalize(root)


@router.get("/repos/{owner}/{repo}/tree", response_model=TreeNode)
async def get_repo_tree(
    owner: str,
    repo: str,
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> TreeNode:
    access_token = creds.credentials
    if not access_token:
        raise HTTPException(status_code=401, detail="missing_access_token")

    async with httpx.AsyncClient(timeout=15.0) as client:
        data = await _fetch_branch_tree(client, owner, repo, "main", access_token)
        if data is None:
            data = await _fetch_branch_tree(client, owner, repo, "master", access_token)
        if data is None:
            raise HTTPException(status_code=404, detail="default_branch_not_found")

    entries = data.get("tree") or []
    return TreeNode.model_validate(_build_tree(entries, repo))


@router.get("/repos/{owner}/{repo}/files/{path:path}", response_class=PlainTextResponse)
async def get_repo_file(
    owner: str,
    repo: str,
    path: str,
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> PlainTextResponse:
    access_token = creds.credentials
    if not access_token:
        raise HTTPException(status_code=401, detail="missing_access_token")

    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.get(
            GITHUB_CONTENTS_URL.format(owner=owner, repo=repo, path=path),
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {access_token}",
            },
        )

    if res.status_code == 404:
        raise HTTPException(status_code=404, detail="file_not_found")
    if res.status_code == 401:
        raise HTTPException(status_code=401, detail="github_unauthorized")
    if res.status_code == 403:
        raise HTTPException(status_code=403, detail="github_forbidden")
    if res.status_code != 200:
        raise HTTPException(status_code=502, detail="github_contents_fetch_failed")

    payload = res.json()
    if isinstance(payload, list) or payload.get("type") != "file":
        raise HTTPException(status_code=400, detail="path_is_not_a_file")

    encoding = payload.get("encoding")
    content_b64 = payload.get("content")
    if encoding != "base64" or not content_b64:
        # Files >1MB return empty content per the Contents API; caller should use the blob endpoint.
        raise HTTPException(status_code=413, detail="file_too_large_or_unsupported_encoding")

    try:
        raw = base64.b64decode(content_b64, validate=False)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=502, detail="github_content_decode_failed")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")

    return PlainTextResponse(content=text)
