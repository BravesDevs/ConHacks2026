from __future__ import annotations

from typing import Any, Literal

import asyncio

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.api.deps import require_internal_job_token
from app.schemas.snowflake_v2 import (
    SnowflakeCortexChatResponse,
    SnowflakeCortexSummarizeResponse,
    SnowflakeIngestDoSizesExample,
    SnowflakeJobItemsResponse,
    SnowflakeJobResultResponse,
    SnowflakeMetricsCleanExample,
    SnowflakePipeStatusResponse,
    SnowflakeSetupResponse,
    SnowflakeTerraformCleanExample,
    SnowflakeTerraformUploadResolvedExample,
    SnowflakeWorkflowsSetupResponse,
)
from app.services.digitalocean_monitoring_service import fetch_digitalocean_metrics
from app.services.digitalocean_ai_service import chat_complete
from app.services.ingest_service import (
    ingest_digitalocean_sizes,
    ingest_metrics_json,
    ingest_terraform_resolved_resources,
)
from app.services.snowflake_service import (
    SnowflakeNames,
    ensure_snowflake_setup,
    refresh_pipe,
    run_sql,
    run_sql_with_context,
    run_sql_with_context_no_schema,
)
from app.services.job_service import fail_job, start_job, succeed_job
from app.services.snowflake_workflows import (
    ensure_cleaning_procs_and_tasks,
    ensure_cortex_procs_and_tasks,
    ensure_suggestion_procs_and_tasks,
    ensure_terraform_cleaning,
)


router = APIRouter(prefix="/snowflake/v2", tags=["snowflake-setup"])


@router.post("/setup", tags=["snowflake-setup"])
def setup_all(
    settings=Depends(require_internal_job_token),
) -> SnowflakeSetupResponse:
    """
    Create/replace Snowflake database objects needed for the pipeline:
    - raw tables + pipes (created by /snowflake/setup)
    - cleaning/analyze/cortex stored procedures and tasks (created by /snowflake/manual/workflows/setup)
    """
    try:
        job = start_job(settings, endpoint="/snowflake/v2/setup", params={})
        ensure_snowflake_setup(settings)
        succeed_job(settings, job_id=job.job_id)
        return {
            "job_id": job.job_id,
            "status": "ok",
            "note": "Snowflake core objects created/verified (db/schemas/stage/raw tables/pipes).",
        }
    except Exception as e:
        try:
            fail_job(settings, job_id=locals().get("job").job_id, error=str(e))  # type: ignore[attr-defined]
        except Exception:
            pass
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
) -> SnowflakeJobResultResponse:
    """Fetch a metrics payload from DigitalOcean, upload to stage, and refresh the metrics pipe."""
    try:
        job = start_job(
            settings,
            endpoint="/snowflake/v2/ingest/metrics/from-do",
            params={"endpoint": endpoint, "params": params},
        )
        payload = await fetch_digitalocean_metrics(
            token=settings.digitalocean_token, endpoint=endpoint, params=params
        )
        out = ingest_metrics_json(settings, payload=payload)
        succeed_job(settings, job_id=job.job_id)
        return {"job_id": job.job_id, "result": out}
    except Exception as e:
        try:
            fail_job(settings, job_id=locals().get("job").job_id, error=str(e))  # type: ignore[attr-defined]
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(e)) from e


@ingest_router.post("/metrics/dummy")
def ingest_metrics_dummy(
    payload: dict[str, Any] = Body(
        ..., description="Raw DigitalOcean metrics JSON payload."
    ),
    settings=Depends(require_internal_job_token),
) -> SnowflakeJobResultResponse:
    """Upload a metrics JSON payload to stage and refresh the metrics pipe."""
    try:
        job = start_job(
            settings,
            endpoint="/snowflake/v2/ingest/metrics/dummy",
            params={"filename": "dummy_metrics.json"},
        )
        out = ingest_metrics_json(
            settings, payload=payload, filename="dummy_metrics.json"
        )
        succeed_job(settings, job_id=job.job_id)
        return {"job_id": job.job_id, "result": out}
    except Exception as e:
        try:
            fail_job(settings, job_id=locals().get("job").job_id, error=str(e))  # type: ignore[attr-defined]
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(e)) from e


@ingest_router.post(
    "/do-sizes",
    response_model=SnowflakeIngestDoSizesExample,
)
async def ingest_do_sizes(
    settings=Depends(require_internal_job_token),
) -> SnowflakeJobResultResponse:
    """Fetch DigitalOcean /v2/sizes, upload to stage, and refresh SIZES_RAW pipe."""
    try:
        job = start_job(settings, endpoint="/snowflake/v2/ingest/do-sizes", params={})
        out = await ingest_digitalocean_sizes(settings)
        succeed_job(settings, job_id=job.job_id)
        return {"job_id": job.job_id, "result": out}
    except Exception as e:
        try:
            fail_job(settings, job_id=locals().get("job").job_id, error=str(e))  # type: ignore[attr-defined]
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(e)) from e


@ingest_router.post("/pipe/refresh")
def refresh_named_pipe(
    pipe: Literal["metrics", "resources", "terraform", "do_sizes"] = Query(
        ...,
        description="Which pipe to refresh.",
    ),
    settings=Depends(require_internal_job_token),
) -> SnowflakeJobResultResponse:
    """Refresh a Snowflake pipe (forces COPY from stage into the raw table)."""
    try:
        job = start_job(
            settings,
            endpoint="/snowflake/v2/ingest/pipe/refresh",
            params={"pipe": pipe},
        )
        names = SnowflakeNames.from_settings(settings)
        pipe_map = {
            "metrics": f'"{names.database}"."{names.schema_metrics}"."RAW_PIPE"',
            "resources": f'"{names.database}"."{names.schema_resources}"."RAW_PIPE"',
            "terraform": f'"{names.database}"."{names.schema_terraform}"."RAW_PIPE"',
            "do_sizes": f'"{names.database}"."{names.schema_cost}"."SIZES_RAW_PIPE"',
        }
        out = refresh_pipe(settings, pipe_fqn=pipe_map[pipe])
        succeed_job(settings, job_id=job.job_id)
        return {"job_id": job.job_id, "result": out}
    except Exception as e:
        try:
            fail_job(settings, job_id=locals().get("job").job_id, error=str(e))  # type: ignore[attr-defined]
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(e)) from e


@ingest_router.get("/pipe/status")
def pipe_status(
    pipe: Literal["metrics", "resources", "terraform", "do_sizes"] = Query(...),
    hours: int = Query(default=1, ge=1, le=168),
    limit: int = Query(default=25, ge=1, le=200),
    settings=Depends(require_internal_job_token),
) -> SnowflakePipeStatusResponse:
    """Return SYSTEM$PIPE_STATUS and recent COPY_HISTORY rows for the pipe's raw table."""
    try:
        job = start_job(
            settings,
            endpoint="/snowflake/v2/ingest/pipe/status",
            params={"pipe": pipe, "hours": hours, "limit": limit},
        )
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
        succeed_job(settings, job_id=job.job_id)
        return {
            "job_id": job.job_id,
            "pipe": pipe,
            "pipe_fqn": pipe_fqn,
            "raw_table": raw_table,
            "pipe_status": (status_rows[0]["PIPE_STATUS"] if status_rows else None),
            "copy_history": copy_history_rows,
        }
    except Exception as e:
        try:
            fail_job(settings, job_id=locals().get("job").job_id, error=str(e))  # type: ignore[attr-defined]
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(e)) from e


terraform_router = APIRouter(
    prefix="/snowflake/v2/terraform", tags=["snowflake-terraform"]
)


@terraform_router.post(
    "/upload-resolved",
    response_model=SnowflakeTerraformUploadResolvedExample,
)
def upload_resolved(
    resources: list[dict[str, Any]] = Body(
        ...,
        description="Resolved/normalized terraform resources.",
        examples=[
            [
                {
                    "resource_type": "digitalocean_droplet",
                    "name": "app",
                    "region": "nyc3",
                    "size": "s-4vcpu-8gb",
                    "image": "ubuntu-22-04-x64",
                    "tags": ["conhacks", "dev"],
                }
            ]
        ],
    ),
    filename: str = Query(default="resolved_resources.json"),
    settings=Depends(require_internal_job_token),
) -> SnowflakeJobResultResponse:
    """Upload resolved terraform resources JSON to stage and refresh terraform pipe."""
    try:
        job = start_job(
            settings,
            endpoint="/snowflake/v2/terraform/upload-resolved",
            params={"filename": filename, "count": len(resources)},
        )
        out = ingest_terraform_resolved_resources(
            settings, resources=resources, filename=filename
        )
        succeed_job(settings, job_id=job.job_id)
        return {"job_id": job.job_id, "result": out}
    except Exception as e:
        try:
            fail_job(settings, job_id=locals().get("job").job_id, error=str(e))  # type: ignore[attr-defined]
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(e)) from e


@terraform_router.post("/clean")
@terraform_router.post(
    "/clean",
    response_model=SnowflakeTerraformCleanExample,
)
def clean(settings=Depends(require_internal_job_token)) -> SnowflakeJobResultResponse:
    """Run the terraform cleaning procedure (RAW -> CLEAN)."""
    try:
        job = start_job(settings, endpoint="/snowflake/v2/terraform/clean", params={})
        names = SnowflakeNames.from_settings(settings)
        out = run_sql(
            settings,
            sql=f'CALL "{names.database}"."{names.schema_terraform}"."SP_CLEAN_RAW"();',
        )
        succeed_job(settings, job_id=job.job_id)
        return {"job_id": job.job_id, "result": out}
    except Exception as e:
        try:
            fail_job(settings, job_id=locals().get("job").job_id, error=str(e))  # type: ignore[attr-defined]
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(e)) from e


workflows_router = APIRouter(
    prefix="/snowflake/v2/workflows", tags=["snowflake-workflows"]
)


@workflows_router.post("/setup")
def workflows_setup(
    settings=Depends(require_internal_job_token),
) -> SnowflakeWorkflowsSetupResponse:
    """Create/replace stored procedures and tasks for cleaning/analyze/cortex."""
    try:
        job = start_job(settings, endpoint="/snowflake/v2/workflows/setup", params={})
        # Ensure base objects exist first (db/schema).
        ensure_snowflake_setup(settings)
        ensure_cleaning_procs_and_tasks(settings)
        ensure_terraform_cleaning(settings)
        ensure_suggestion_procs_and_tasks(settings)
        ensure_cortex_procs_and_tasks(settings)
        succeed_job(settings, job_id=job.job_id)
        return {
            "job_id": job.job_id,
            "status": "ok",
            "note": "Workflows created/verified (cleaning/analyze/cortex procedures and tasks).",
        }
    except Exception as e:
        try:
            fail_job(settings, job_id=locals().get("job").job_id, error=str(e))  # type: ignore[attr-defined]
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(e)) from e


@workflows_router.post(
    "/metrics/clean",
    response_model=SnowflakeMetricsCleanExample,
)
def metrics_clean(
    settings=Depends(require_internal_job_token),
) -> SnowflakeJobResultResponse:
    """Run metrics cleaning (METRICS.RAW -> METRICS.CLEAN)."""
    try:
        job = start_job(
            settings, endpoint="/snowflake/v2/workflows/metrics/clean", params={}
        )
        names = SnowflakeNames.from_settings(settings)
        out = run_sql(
            settings,
            sql=f'CALL "{names.database}"."{names.schema_metrics}"."SP_CLEAN_RAW"();',
        )
        succeed_job(settings, job_id=job.job_id)
        return {"job_id": job.job_id, "result": out}
    except Exception as e:
        try:
            fail_job(settings, job_id=locals().get("job").job_id, error=str(e))  # type: ignore[attr-defined]
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(e)) from e


@workflows_router.post("/analyze")
def analyze(settings=Depends(require_internal_job_token)) -> SnowflakeJobResultResponse:
    """Run analysis to populate COST.COST_RECOMMENDATIONS."""
    try:
        job = start_job(settings, endpoint="/snowflake/v2/workflows/analyze", params={})
        names = SnowflakeNames.from_settings(settings)
        out = run_sql(
            settings,
            sql=f'CALL "{names.database}"."{names.schema_cost}"."SP_ANALYZE_METRICS"();',
        )
        succeed_job(settings, job_id=job.job_id)
        return {"job_id": job.job_id, "result": out}
    except Exception as e:
        try:
            fail_job(settings, job_id=locals().get("job").job_id, error=str(e))  # type: ignore[attr-defined]
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(e)) from e


recommendations_router = APIRouter(
    prefix="/snowflake/v2/recommendations", tags=["snowflake-workflows"]
)


@recommendations_router.get("")
def list_cost_recommendations(
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Max number of most-recent recommendations to return.",
    ),
    settings=Depends(require_internal_job_token),
) -> SnowflakeJobItemsResponse:
    """Return the most recent rows from COST.COST_RECOMMENDATIONS."""
    try:
        job = start_job(
            settings,
            endpoint="/snowflake/v2/recommendations",
            params={"limit": limit},
        )
        names = SnowflakeNames.from_settings(settings)
        rows = run_sql_with_context(
            settings,
            sql=f"""
            SELECT created_at, resource_id, old_size, new_size, estimated_savings, reason
            FROM "{names.database}"."{names.schema_cost}"."COST_RECOMMENDATIONS"
            ORDER BY created_at DESC
            LIMIT {limit};
            """,
        )
        rows = [r for r in rows if "CREATED_AT" in r]
        succeed_job(settings, job_id=job.job_id)
        return {"job_id": job.job_id, "items": rows, "limit": limit}
    except Exception as e:
        try:
            fail_job(settings, job_id=locals().get("job").job_id, error=str(e))  # type: ignore[attr-defined]
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(e)) from e


cortex_router = APIRouter(prefix="/snowflake/v2/cortex", tags=["snowflake-cortex"])


@cortex_router.post("/summarize")
async def cortex_summarize(
    settings=Depends(require_internal_job_token),
) -> SnowflakeCortexSummarizeResponse:
    """Generate explanation summaries for COST_RECOMMENDATIONS and store them in TERRAFORM_CONFIG.TERRAFORM_SUGGESTIONS."""
    try:
        names = SnowflakeNames.from_settings(settings)
        job = start_job(settings, endpoint="/snowflake/v2/cortex/summarize", params={})
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

        def _needs_summary(resource_id: str, rec_created_at: Any) -> bool:
            rid_sql = resource_id.replace("'", "''")
            created_at_sql = str(rec_created_at).replace("'", "''")
            exists_rows = run_sql_with_context(
                settings,
                sql=f"""
                SELECT 1 AS X
                FROM "{names.database}"."{names.schema_terraform}"."TERRAFORM_SUGGESTIONS"
                WHERE suggestion_type='recommendation_summary'
                  AND resource_id='{rid_sql}'
                  AND explanation LIKE '%created_at={created_at_sql}%'
                ORDER BY created_at DESC
                LIMIT 1;
                """,
            )
            return not any("X" in row for row in exists_rows)

        to_generate: list[dict[str, Any]] = []
        for r in recs:
            rid_raw = str(r.get("RESOURCE_ID") or "")
            if not rid_raw:
                continue
            if _needs_summary(rid_raw, r.get("CREATED_AT")):
                to_generate.append(r)

        async def _generate_one(r: dict[str, Any]) -> tuple[str, str] | None:
            rid_raw = str(r.get("RESOURCE_ID") or "")
            if not rid_raw:
                return None
            rid_sql = rid_raw.replace("'", "''")
            old_size = str(r.get("OLD_SIZE") or "unknown")
            new_size = str(r.get("NEW_SIZE") or "unknown")
            savings = r.get("ESTIMATED_SAVINGS")

            # Smaller prompt: keep it tight and structured.
            rec_created_at = r.get("CREATED_AT")
            prompt = (
                "Explain this DigitalOcean droplet downsizing recommendation in plain English.\n"
                f"resource_id={rid_raw}\ncreated_at={rec_created_at}\nold_size={old_size}\nnew_size={new_size}\n"
                f"estimated_savings_monthly={savings if savings is not None else 'unknown'}\n"
                "Include: what changes, why, and any risk/caveats. Keep under 8 bullet points."
            )

            metrics_summary_rows = run_sql_with_context(
                settings,
                sql=f"""
                WITH base AS (
                  SELECT metric_name, metric_values
                  FROM "{names.database}"."{names.schema_metrics}"."CLEAN"
                  WHERE resource_id = '{rid_sql}'
                  ORDER BY ingested_at DESC
                  LIMIT 25
                ),
                cpu AS (
                  SELECT
                    AVG(100.0 - TRY_TO_NUMBER(v.value[1]::STRING, 38, 10)) AS avg_cpu_percent,
                    APPROX_PERCENTILE(100.0 - TRY_TO_NUMBER(v.value[1]::STRING, 38, 10), 0.95) AS p95_cpu_percent
                  FROM base, LATERAL FLATTEN(input => metric_values) v
                  WHERE metric_name = 'idle'
                ),
                mem AS (
                  SELECT
                    APPROX_PERCENTILE(TRY_TO_NUMBER(v.value[1]::STRING, 38, 0), 0.95) AS p95_mem_used_bytes
                  FROM base, LATERAL FLATTEN(input => metric_values) v
                  WHERE metric_name IN ('used_bytes','memory_used_bytes')
                )
                SELECT
                  COALESCE(cpu.avg_cpu_percent, NULL) AS avg_cpu_percent,
                  COALESCE(cpu.p95_cpu_percent, NULL) AS p95_cpu_percent,
                  COALESCE(mem.p95_mem_used_bytes, NULL) AS p95_mem_used_bytes
                FROM cpu, mem;
                """,
            )
            metrics_summary = next(
                (row for row in metrics_summary_rows if "AVG_CPU_PERCENT" in row),
                None,
            )

            tf_rows = run_sql_with_context(
                settings,
                sql=f"""
                SELECT droplet_size, region
                FROM "{names.database}"."{names.schema_terraform}"."CLEAN"
                WHERE droplet_size IS NOT NULL
                ORDER BY ingested_at DESC
                LIMIT 5;
                """,
            )
            tf_ctx = tf_rows[0] if tf_rows else None

            ctx = {
                "metrics_summary": metrics_summary,
                "terraform_hint": tf_ctx,
            }

            explanation = await chat_complete(
                settings,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a cloud cost optimization assistant.",
                    },
                    {
                        "role": "user",
                        "content": prompt + "\n\nContext JSON:\n" + str(ctx),
                    },
                ],
                max_tokens=350,
            )
            return rid_sql, explanation

        sem = asyncio.Semaphore(4)

        async def _bounded(r: dict[str, Any]):
            async with sem:
                return await _generate_one(r)

        results = await asyncio.gather(*[_bounded(r) for r in to_generate])
        inserted = 0
        for item in results:
            if not item:
                continue
            rid_sql, explanation = item
            run_sql_with_context(
                settings,
                sql=f"""
                INSERT INTO "{names.database}"."{names.schema_terraform}"."TERRAFORM_SUGGESTIONS"(
                  suggestion_type, resource_id, terraform_config, explanation
                )
                SELECT
                  'recommendation_summary',
                  '{rid_sql}',
                  NULL,
                  '{explanation.replace("'", "''")}';
                """,
            )
            inserted += 1

        succeed_job(settings, job_id=job.job_id)
        # Return the latest summary rows so the caller can display them immediately.
        rows = run_sql_with_context(
            settings,
            sql=f"""
            SELECT created_at, suggestion_type, resource_id, explanation
            FROM "{names.database}"."{names.schema_terraform}"."TERRAFORM_SUGGESTIONS"
            WHERE suggestion_type='recommendation_summary'
            ORDER BY created_at DESC
            LIMIT 25;
            """,
        )
        rows = [r for r in rows if "CREATED_AT" in r]
        return {
            "job_id": job.job_id,
            "status": "ok",
            "inserted": inserted,
            "summaries": rows,
        }
    except Exception as e:
        try:
            fail_job(settings, job_id=locals().get("job").job_id, error=str(e))  # type: ignore[attr-defined]
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(e)) from e


@cortex_router.post("/chat")
async def cortex_chat(
    question: str = Body(
        ..., embed=True, description="User question about recommendations/metrics."
    ),
    settings=Depends(require_internal_job_token),
) -> SnowflakeCortexChatResponse:
    """Ask Cortex a question using recommendations + latest metrics + latest terraform resolved resources as context."""
    try:
        names = SnowflakeNames.from_settings(settings)
        job = start_job(
            settings,
            endpoint="/snowflake/v2/cortex/chat",
            params={"question": question},
        )
        # Smaller context: top recent recs + summarized metrics.
        rec_rows = run_sql_with_context_no_schema(
            settings,
            sql=f"""
            SELECT created_at, resource_id, old_size, new_size, estimated_savings, reason
            FROM "{names.database}"."{names.schema_cost}"."COST_RECOMMENDATIONS"
            ORDER BY created_at DESC
            LIMIT 10;
            """,
        )
        rec_rows = [r for r in rec_rows if "RESOURCE_ID" in r]

        metrics_summary_rows = run_sql_with_context_no_schema(
            settings,
            sql=f"""
            WITH base AS (
              SELECT resource_id, metric_name, metric_values
              FROM "{names.database}"."{names.schema_metrics}"."CLEAN"
            ),
            cpu AS (
              SELECT
                resource_id,
                AVG(100.0 - TRY_TO_NUMBER(v.value[1]::STRING, 38, 10)) AS avg_cpu_percent,
                APPROX_PERCENTILE(100.0 - TRY_TO_NUMBER(v.value[1]::STRING, 38, 10), 0.95) AS p95_cpu_percent
              FROM base, LATERAL FLATTEN(input => metric_values) v
              WHERE metric_name = 'idle'
              GROUP BY resource_id
            ),
            mem AS (
              SELECT
                resource_id,
                APPROX_PERCENTILE(TRY_TO_NUMBER(v.value[1]::STRING, 38, 0), 0.95) AS p95_mem_used_bytes
              FROM base, LATERAL FLATTEN(input => metric_values) v
              WHERE metric_name IN ('used_bytes','memory_used_bytes')
              GROUP BY resource_id
            )
            SELECT
              c.resource_id,
              c.avg_cpu_percent,
              c.p95_cpu_percent,
              m.p95_mem_used_bytes
            FROM cpu c
            LEFT JOIN mem m ON m.resource_id = c.resource_id
            LIMIT 25;
            """,
        )
        metrics_summary_rows = [r for r in metrics_summary_rows if "RESOURCE_ID" in r]

        tf_hint_rows = run_sql_with_context_no_schema(
            settings,
            sql=f"""
            SELECT filename, droplet_size, region, ingested_at
            FROM "{names.database}"."{names.schema_terraform}"."CLEAN"
            ORDER BY ingested_at DESC
            LIMIT 10;
            """,
        )
        tf_hint_rows = [r for r in tf_hint_rows if "FILENAME" in r]

        ctx = {
            "recent_recommendations": rec_rows,
            "metrics_summary": metrics_summary_rows,
            "terraform_latest": tf_hint_rows,
        }

        answer = await chat_complete(
            settings,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant for cloud cost optimization. Answer the user question using the context.",
                },
                {
                    "role": "user",
                    "content": "User question: "
                    + question
                    + "\n\nContext JSON:\n"
                    + str(ctx),
                },
            ],
            max_tokens=450,
        )

        succeed_job(settings, job_id=job.job_id)
        return {"job_id": job.job_id, "answer": answer}
    except Exception as e:
        try:
            fail_job(settings, job_id=locals().get("job").job_id, error=str(e))  # type: ignore[attr-defined]
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(e)) from e
