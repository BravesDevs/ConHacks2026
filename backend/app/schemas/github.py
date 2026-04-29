from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator


class TrackReposIn(BaseModel):
    user_id: str
    repos: list[str]

    @field_validator("repos")
    @classmethod
    def _validate_repos(cls, v: list[str]) -> list[str]:
        for repo in v:
            if "/" not in repo or any(c.isspace() for c in repo) or len(repo) > 140:
                raise ValueError(
                    f"invalid repo: {repo!r} (expected 'owner/repo', no whitespace, len <= 140)"
                )
        return v


class GitHubConnectionOut(BaseModel):
    id: int
    user_id: str
    tracked_repos: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OAuthCallbackOut(BaseModel):
    user_id: str
    tracked_repos: list[str]
    connected: bool = True


class RevokeOut(BaseModel):
    user_id: str
    deleted: bool
    revoked_at_github: bool
