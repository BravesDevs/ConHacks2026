from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.api.deps import require_internal_job_token
from app.services.digitalocean_monitoring_service import fetch_digitalocean_metrics
from app.services.ingest_service import (
    ingest_metrics_json,
    ingest_terraform_resolved_resources,
)
from app.services.snowflake_service import (
    SnowflakeNames,
    refresh_pipe,
    run_sql,
    run_sql_with_context,
    run_sql_with_context_no_schema,
)


router = APIRouter(prefix="/snowflake/v2", tags=["snowflake-setup"])


@router.post("/setup", tags=["snowflake-setup"])
def setup_all(settings=Depends(require_internal_job_token)) -> dict[str, str]:
    """
    Create/replace Snowflake database objects needed for the pipeline:
    - raw tables + pipes (created by /snowflake/setup)
    - cleaning/analyze/cortex stored procedures and tasks (created by /snowflake/manual/workflows/setup)
    """
    try:
        # Reuse existing endpoints indirectly by calling the same procs.
        names = SnowflakeNames.from_settings(settings)
        _ = names  # for clearer error messages if settings missing
        return {
            "status": "ok",
            "note": "Use /snowflake/setup and /snowflake/manual/workflows/setup for full init.",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


ingest_router = APIRouter(prefix="/snowflake/v2/ingest", tags=["snowflake-ingest"])


@ingest_router.post("/metrics/from-do")
async def ingest_metrics_from_do(
    endpoint: str = Query(
        ...,
        description="DigitalOcean Monitoring endpoint path, e.g. /v2/monitoring/metrics/droplet/cpu",
    ),
    params: dict[str, Any] | None = Body(
        default=None,
        description="Optional query params dict passed through to DigitalOcean.",
    ),
    settings=Depends(require_internal_job_token),
) -> dict[str, Any]:
    """Fetch a metrics payload from DigitalOcean, upload to stage, and refresh the metrics pipe."""
    try:
        payload = await fetch_digitalocean_metrics(
            token=settings.digitalocean_token, endpoint=endpoint, params=params
        )
        return ingest_metrics_json(settings, payload=payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@ingest_router.post("/metrics/dummy")
def ingest_metrics_dummy(
    payload: dict[str, Any] = Body(
        ..., description="Raw DigitalOcean metrics JSON payload."
    ),
    settings=Depends(require_internal_job_token),
) -> dict[str, Any]:
    """Upload a metrics JSON payload to stage and refresh the metrics pipe."""
    try:
        return ingest_metrics_json(
            settings, payload=payload, filename="dummy_metrics.json"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@ingest_router.post("/pipe/refresh")
def refresh_named_pipe(
    pipe: Literal["metrics", "resources", "terraform", "do_sizes"] = Query(
        ...,
        description="Which pipe to refresh.",
    ),
    settings=Depends(require_internal_job_token),
) -> dict[str, Any]:
    """Refresh a Snowflake pipe (forces COPY from stage into the raw table)."""
    try:
        names = SnowflakeNames.from_settings(settings)
        pipe_map = {
            "metrics": f'"{names.database}"."{names.schema_metrics}"."RAW_PIPE"',
            "resources": f'"{names.database}"."{names.schema_resources}"."RAW_PIPE"',
            "terraform": f'"{names.database}"."{names.schema_terraform}"."RAW_PIPE"',
            "do_sizes": f'"{names.database}"."{names.schema_cost}"."SIZES_RAW_PIPE"',
        }
        return refresh_pipe(settings, pipe_fqn=pipe_map[pipe])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@ingest_router.get("/pipe/status")
def pipe_status(
    pipe: Literal["metrics", "resources", "terraform", "do_sizes"] = Query(...),
    hours: int = Query(default=1, ge=1, le=168),
    limit: int = Query(default=25, ge=1, le=200),
    settings=Depends(require_internal_job_token),
) -> dict[str, Any]:
    """Return SYSTEM$PIPE_STATUS and recent COPY_HISTORY rows for the pipe's raw table."""
    try:
        names = SnowflakeNames.from_settings(settings)
        pipe_map = {
            "metrics": {
                "pipe_fqn": f"{names.database}.{names.schema_metrics}.RAW_PIPE",
                "raw_table": f"{names.database}.{names.schema_metrics}.RAW",
            },
            "resources": {
                "pipe_fqn": f"{names.database}.{names.schema_resources}.RAW_PIPE",
                "raw_table": f"{names.database}.{names.schema_resources}.RAW",
            },
            "terraform": {
                "pipe_fqn": f"{names.database}.{names.schema_terraform}.RAW_PIPE",
                "raw_table": f"{names.database}.{names.schema_terraform}.RAW",
            },
            "do_sizes": {
                "pipe_fqn": f"{names.database}.{names.schema_cost}.SIZES_RAW_PIPE",
                "raw_table": f"{names.database}.{names.schema_cost}.SIZES_RAW",
            },
        }
        pipe_fqn = pipe_map[pipe]["pipe_fqn"]
        raw_table = pipe_map[pipe]["raw_table"]
        status_rows = run_sql(
            settings, sql=f"SELECT SYSTEM$PIPE_STATUS('{pipe_fqn}') AS PIPE_STATUS;"
        )
        copy_history_rows = run_sql(
            settings,
            sql=f"""
            SELECT *
            FROM TABLE(
              INFORMATION_SCHEMA.COPY_HISTORY(
                table_name => '{raw_table}',
                start_time => DATEADD('hour', -{hours}, CURRENT_TIMESTAMP())
              )
            )
            ORDER BY LAST_LOAD_TIME DESC
            LIMIT {limit};
            """,
        )
        return {
            "pipe": pipe,
            "pipe_fqn": pipe_fqn,
            "raw_table": raw_table,
            "pipe_status": (status_rows[0]["PIPE_STATUS"] if status_rows else None),
            "copy_history": copy_history_rows,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


terraform_router = APIRouter(
    prefix="/snowflake/v2/terraform", tags=["snowflake-terraform"]
)


@terraform_router.post("/upload-resolved")
def upload_resolved(
    resources: list[dict[str, Any]] = Body(
        ..., description="Resolved/normalized terraform resources."
    ),
    filename: str = Query(default="resolved_resources.json"),
    settings=Depends(require_internal_job_token),
) -> dict[str, Any]:
    """Upload resolved terraform resources JSON to stage and refresh terraform pipe."""
    try:
        return ingest_terraform_resolved_resources(
            settings, resources=resources, filename=filename
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@terraform_router.post("/clean")
def clean(settings=Depends(require_internal_job_token)) -> dict[str, Any]:
    """Run the terraform cleaning procedure (RAW -> CLEAN)."""
    try:
        names = SnowflakeNames.from_settings(settings)
        out = run_sql(
            settings,
            sql=f'CALL "{names.database}"."{names.schema_terraform}"."SP_CLEAN_RAW"();',
        )
        return {"result": out}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


workflows_router = APIRouter(
    prefix="/snowflake/v2/workflows", tags=["snowflake-workflows"]
)


@workflows_router.post("/setup")
def workflows_setup(settings=Depends(require_internal_job_token)) -> dict[str, str]:
    """Create/replace stored procedures and tasks for cleaning/analyze/cortex."""
    try:
        names = SnowflakeNames.from_settings(settings)
        _ = names
        return {
            "status": "ok",
            "note": "Use /snowflake/manual/workflows/setup (v1) to actually create objects.",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@workflows_router.post("/metrics/clean")
def metrics_clean(settings=Depends(require_internal_job_token)) -> dict[str, Any]:
    """Run metrics cleaning (METRICS.RAW -> METRICS.CLEAN)."""
    try:
        names = SnowflakeNames.from_settings(settings)
        out = run_sql(
            settings,
            sql=f'CALL "{names.database}"."{names.schema_metrics}"."SP_CLEAN_RAW"();',
        )
        return {"result": out}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@workflows_router.post("/analyze")
def analyze(settings=Depends(require_internal_job_token)) -> dict[str, Any]:
    """Run analysis to populate COST.COST_RECOMMENDATIONS."""
    try:
        names = SnowflakeNames.from_settings(settings)
        out = run_sql(
            settings,
            sql=f'CALL "{names.database}"."{names.schema_cost}"."SP_ANALYZE_METRICS"();',
        )
        return {"result": out}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


cortex_router = APIRouter(prefix="/snowflake/v2/cortex", tags=["snowflake-cortex"])


@cortex_router.post("/summarize")
def cortex_summarize(settings=Depends(require_internal_job_token)) -> dict[str, Any]:
    """Generate explanation summaries for COST_RECOMMENDATIONS and store them in TERRAFORM_CONFIG.TERRAFORM_SUGGESTIONS."""
    try:
        names = SnowflakeNames.from_settings(settings)
        # Revert to per-recommendation loop to make "inserted" explicit and easier to reason about.
        recs = run_sql_with_context(
            settings,
            sql=f"""
            SELECT resource_id, old_size, new_size, estimated_savings, created_at
            FROM "{names.database}"."{names.schema_cost}"."COST_RECOMMENDATIONS"
            WHERE resource_id IS NOT NULL AND resource_id <> ''
            QUALIFY ROW_NUMBER() OVER (PARTITION BY resource_id ORDER BY created_at DESC) = 1;
            """,
        )
        recs = [r for r in recs if "RESOURCE_ID" in r]
        inserted = 0
        for r in recs:
            rid = (r.get("RESOURCE_ID") or "").replace("'", "''")
            old_size = (r.get("OLD_SIZE") or "unknown").replace("'", "''")
            new_size = (r.get("NEW_SIZE") or "unknown").replace("'", "''")
            savings = r.get("ESTIMATED_SAVINGS")
            prompt = (
                "You are a cloud cost optimization assistant. Explain the recommendation in plain English.\\n"
                f"Resource ID: {rid}\\n"
                f"Old size: {old_size} New size: {new_size}\\n"
                f"Estimated savings (monthly): {savings if savings is not None else 'unknown'}\\n\\n"
                "Use the provided metrics payload JSON context when relevant."
            ).replace("'", "''")
            exists = run_sql_with_context(
                settings,
                sql=f"""
                SELECT 1 AS X
                FROM "{names.database}"."{names.schema_terraform}"."TERRAFORM_SUGGESTIONS"
                WHERE suggestion_type='recommendation_summary'
                  AND resource_id='{rid}'
                ORDER BY created_at DESC
                LIMIT 1;
                """,
            )
            exists = any("X" in row for row in exists)
            if exists:
                continue

            run_sql_with_context(
                settings,
                sql=f"""
                INSERT INTO "{names.database}"."{names.schema_terraform}"."TERRAFORM_SUGGESTIONS"(
                  suggestion_type, resource_id, terraform_config, explanation
                )
                SELECT
                  'recommendation_summary',
                  '{rid}',
                  NULL,
                  SNOWFLAKE.CORTEX.COMPLETE(
                    'llama3.1-70b',
                    CONCAT(
                      '{prompt}',
                      '\\n\\nMetrics payload JSON:\\n',
                      COALESCE((
                        SELECT TO_VARCHAR(payload)
                        FROM "{names.database}"."{names.schema_metrics}"."CLEAN"
                        WHERE resource_id = '{rid}'
                        ORDER BY ingested_at DESC
                        LIMIT 1
                      ), 'no_metrics')
                    )
                  )::STRING;
                """,
            )
            inserted += 1

        return {"status": "ok", "inserted": inserted}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@cortex_router.post("/chat")
def cortex_chat(
    question: str = Body(
        ..., embed=True, description="User question about recommendations/metrics."
    ),
    settings=Depends(require_internal_job_token),
) -> dict[str, Any]:
    """Ask Cortex a question using recommendations + latest metrics + latest terraform resolved resources as context."""
    try:
        names = SnowflakeNames.from_settings(settings)
        q = question.replace("'", "''")
        # Avoid QUALIFY in Cortex query to reduce risk of "secure object" errors in some accounts.
        out = run_sql_with_context_no_schema(
            settings,
            sql=f"""
            WITH latest_metrics AS (
              SELECT
                resource_id,
                metric_name,
                payload,
                ROW_NUMBER() OVER (PARTITION BY resource_id, metric_name ORDER BY ingested_at DESC) AS rn
              FROM "{names.database}"."{names.schema_metrics}"."CLEAN"
            ),
            latest_tf AS (
              SELECT
                filename,
                payload,
                ROW_NUMBER() OVER (PARTITION BY filename ORDER BY ingested_at DESC) AS rn
              FROM "{names.database}"."{names.schema_terraform}"."CLEAN"
            )
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
              'llama3.1-70b',
              CONCAT(
                'You are a helpful assistant for cloud cost optimization. Answer the user question using the context.\\n\\n',
                'User question: {q}\\n\\n',
                'Cost recommendations (JSON):\\n',
                COALESCE((SELECT TO_VARCHAR(TO_VARIANT(ARRAY_AGG(OBJECT_CONSTRUCT(*))))
                          FROM "{names.database}"."{names.schema_cost}"."COST_RECOMMENDATIONS"), '[]'),
                '\\n\\nLatest metrics samples (JSON):\\n',
                COALESCE((SELECT TO_VARCHAR(TO_VARIANT(ARRAY_AGG(OBJECT_CONSTRUCT('resource_id', resource_id, 'metric_name', metric_name, 'payload', payload))))
                          FROM latest_metrics WHERE rn = 1), '[]'),
                '\\n\\nLatest Terraform resolved resources (JSON):\\n',
                COALESCE((SELECT TO_VARCHAR(TO_VARIANT(ARRAY_AGG(payload)))
                          FROM latest_tf WHERE rn = 1), '[]')
              )
            )::STRING AS ANSWER;
            """,
        )
        rows = [r for r in out if "ANSWER" in r]
        return {"answer": rows[0]["ANSWER"] if rows else None}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
