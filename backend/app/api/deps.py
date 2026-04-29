from __future__ import annotations

from fastapi import Header, HTTPException, status

from app.core.config import Settings, get_settings


def require_internal_job_token(
    authorization: str | None = Header(default=None),
) -> Settings:
    settings = get_settings()
    token = settings.internal_job_token
    if not token or not authorization or authorization != f"Bearer {token}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized"
        )
    return settings
