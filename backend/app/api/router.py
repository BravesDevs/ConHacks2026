from __future__ import annotations

from fastapi import APIRouter

from app.api.routers.github import router as github_router
from app.api.routers.health import router as health_router
from app.api.routers.jobs import router as jobs_router
from app.api.routers.runs import router as runs_router
from app.api.routers.snowflake import router as snowflake_router
from app.api.routers.snowflake_manual import router as snowflake_manual_router
from app.api.routers.snowflake_v2 import (
    cortex_router as snowflake_v2_cortex_router,
    ingest_router as snowflake_v2_ingest_router,
    router as snowflake_v2_router,
    terraform_router as snowflake_v2_terraform_router,
    workflows_router as snowflake_v2_workflows_router,
)
from app.api.routers.webhooks import router as webhooks_router


api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(webhooks_router)
api_router.include_router(jobs_router)
api_router.include_router(runs_router)
api_router.include_router(github_router)
api_router.include_router(snowflake_router)
# Keep legacy/manual endpoints functional but hide them from OpenAPI docs.
api_router.include_router(snowflake_manual_router, include_in_schema=False)
api_router.include_router(snowflake_v2_router)
api_router.include_router(snowflake_v2_ingest_router)
api_router.include_router(snowflake_v2_terraform_router)
api_router.include_router(snowflake_v2_workflows_router)
api_router.include_router(snowflake_v2_cortex_router)
