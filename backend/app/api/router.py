from __future__ import annotations

from fastapi import APIRouter

from app.api.routers.github import router as github_router
from app.api.routers.health import router as health_router
from app.api.routers.jobs import router as jobs_router
from app.api.routers.runs import router as runs_router
from app.api.routers.snowflake import router as snowflake_router
from app.api.routers.snowflake_manual import router as snowflake_manual_router
from app.api.routers.webhooks import router as webhooks_router


api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(webhooks_router)
api_router.include_router(jobs_router)
api_router.include_router(runs_router)
api_router.include_router(github_router)
api_router.include_router(snowflake_router)
api_router.include_router(snowflake_manual_router)
