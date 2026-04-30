from __future__ import annotations

from fastapi import APIRouter

from app.api.routers.frontend_api import router as frontend_router
from app.api.routers.github import router as github_router
from app.api.routers.health import router as health_router
from app.api.routers.jobs import router as jobs_router
from app.api.routers.runs import router as runs_router
from app.api.routers.snowflake_v2 import (
    cortex_router as snowflake_v2_cortex_router,
    ingest_router as snowflake_v2_ingest_router,
    recommendations_router as snowflake_v2_recommendations_router,
    router as snowflake_v2_router,
    terraform_router as snowflake_v2_terraform_router,
    workflows_router as snowflake_v2_workflows_router,
)
from app.api.routers.jobs_snowflake import router as snowflake_v2_jobs_router
from app.api.routers.voice import router as voice_router
from app.api.routers.webhooks import router as webhooks_router


api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(frontend_router)
api_router.include_router(webhooks_router)
api_router.include_router(jobs_router)
api_router.include_router(runs_router)
api_router.include_router(github_router)
api_router.include_router(snowflake_v2_router)
api_router.include_router(snowflake_v2_ingest_router)
api_router.include_router(snowflake_v2_terraform_router)
api_router.include_router(snowflake_v2_workflows_router)
api_router.include_router(snowflake_v2_recommendations_router)
api_router.include_router(snowflake_v2_cortex_router)
api_router.include_router(snowflake_v2_jobs_router)
api_router.include_router(voice_router)
