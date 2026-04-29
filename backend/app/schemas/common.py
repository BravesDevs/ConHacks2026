from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ApiError(BaseModel):
    error: str
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str
    time: datetime
