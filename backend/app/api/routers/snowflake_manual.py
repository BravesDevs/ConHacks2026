from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.api.deps import require_internal_job_token
from app.services.digitalocean_monitoring_service import fetch_digitalocean_metrics
from app.services.ingest_service import ingest_metrics_json
from app.services.snowflake_service import SnowflakeNames, refresh_pipe, run_sql
from app.services.snowflake_workflows import (
    ensure_cleaning_procs_and_tasks,
    ensure_cortex_procs_and_tasks,
    ensure_suggestion_procs_and_tasks,
)


router = APIRouter(prefix="/snowflake/manual", tags=["snowflake-manual"])


@router.post("/metrics/upload-from-do")
async def upload_metrics_from_do(
    endpoint: str = Query(
        ...,
        description=(
            "DigitalOcean Monitoring endpoint path to fetch, e.g. "
            "`/v2/monitoring/metrics/droplet/cpu`. The raw JSON response is uploaded to the "
            "Snowflake landing stage under `metrics/` and ingested into `METRICS.RAW` via pipe refresh."
        ),
    ),
    settings=Depends(require_internal_job_token),
    params: dict[str, Any] | None = Body(default=None),
) -> dict[str, Any]:
    try:
        payload = await fetch_digitalocean_metrics(
            token=settings.digitalocean_token, endpoint=endpoint, params=params
        )
        return ingest_metrics_json(settings, payload=payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/metrics/upload-dummy")
def upload_dummy_metrics(
    settings=Depends(require_internal_job_token),
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    """Upload a provided JSON payload as a metrics fixture, then refresh the metrics pipe to ingest."""
    try:
        return ingest_metrics_json(
            settings, payload=payload, filename="dummy_metrics.json"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/ingest/refresh-pipe")
def ingest_refresh_pipe(
    pipe: str = Query(
        ...,
        description=(
            "Refresh a Snowflake PIPE (forces Snowflake to scan the landing stage for new files and COPY "
            "them into the corresponding raw table). "
            "Use `metrics`→`METRICS.RAW_PIPE`, `resources`→`RESOURCES.RAW_PIPE`, "
            "`terraform`→`TERRAFORM_CONFIG.RAW_PIPE`, `do_sizes`→`COST.SIZES_RAW_PIPE`."
        ),
    ),
    settings=Depends(require_internal_job_token),
) -> dict[str, Any]:
    try:
        names = SnowflakeNames.from_settings(settings)
        pipe_map = {
            "metrics": f'"{names.database}"."{names.schema_metrics}"."RAW_PIPE"',
            "resources": f'"{names.database}"."{names.schema_resources}"."RAW_PIPE"',
            "terraform": f'"{names.database}"."{names.schema_terraform}"."RAW_PIPE"',
            "do_sizes": f'"{names.database}"."{names.schema_cost}"."SIZES_RAW_PIPE"',
        }
        if pipe not in pipe_map:
            raise ValueError("pipe must be one of metrics|resources|terraform|do_sizes")
        return refresh_pipe(settings, pipe_fqn=pipe_map[pipe])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/workflows/setup")
def setup_workflows(settings=Depends(require_internal_job_token)) -> dict[str, str]:
    """Create placeholder stored procedures + Snowflake TASKs for cleaning, analysis, and Cortex steps."""
    try:
        ensure_cleaning_procs_and_tasks(settings)
        ensure_suggestion_procs_and_tasks(settings)
        ensure_cortex_procs_and_tasks(settings)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/workflows/run-clean-now")
def run_clean_now(settings=Depends(require_internal_job_token)) -> dict[str, Any]:
    """Run the cleaning stored procedure immediately (RAW → CLEAN)."""
    try:
        names = SnowflakeNames.from_settings(settings)
        out = run_sql(
            settings,
            sql=f'CALL "{names.database}"."{names.schema_metrics}"."SP_CLEAN_RAW"();',
        )
        return {"result": out}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/workflows/run-analyze-now")
def run_analyze_now(settings=Depends(require_internal_job_token)) -> dict[str, Any]:
    """Run the analysis stored procedure immediately (CLEAN → COST_RECOMMENDATIONS)."""
    try:
        names = SnowflakeNames.from_settings(settings)
        out = run_sql(
            settings,
            sql=f'CALL "{names.database}"."{names.schema_cost}"."SP_ANALYZE_METRICS"();',
        )
        return {"result": out}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/workflows/refresh-sizes-now")
def refresh_sizes_now(settings=Depends(require_internal_job_token)) -> dict[str, Any]:
    """Refresh normalized DigitalOcean sizes catalog (COST.SIZES_RAW → COST.SIZES)."""
    try:
        names = SnowflakeNames.from_settings(settings)
        out = run_sql(
            settings,
            sql=f'CALL "{names.database}"."{names.schema_cost}"."SP_REFRESH_SIZES"();',
        )
        return {"result": out}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/workflows/run-cortex-now")
def run_cortex_now(settings=Depends(require_internal_job_token)) -> dict[str, Any]:
    """Run the Cortex stored procedure immediately (placeholder implementation today)."""
    try:
        names = SnowflakeNames.from_settings(settings)
        out = run_sql(
            settings,
            sql=f'CALL "{names.database}"."{names.schema_terraform}"."SP_CORTEX_TERRAFORM"();',
        )
        return {"result": out}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
