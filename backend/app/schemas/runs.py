from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import RunStatus


class RunOut(BaseModel):
    id: int
    repo: str
    status: RunStatus
    error: str | None
    constraints: dict
    suggested_config: dict
    explanation: str | None
    pr_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ManualOptimizeIn(BaseModel):
    repo: str
    terraform_sha: str | None = None
    metrics_window: dict | None = None
    constraints: dict | None = None
