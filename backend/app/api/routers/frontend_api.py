from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from app.core.config import get_settings
from app.services.ingest_service import (
    ingest_digitalocean_sizes,
    ingest_metrics_json,
    ingest_terraform_from_github,
    ingest_terraform_from_local,
)
from app.services.digitalocean_ai_service import chat_complete
from app.services.snowflake_service import SnowflakeNames, run_sql_with_context_no_schema

_SAMPLE_PAYLOADS_DIR = Path(__file__).parent.parent.parent.parent / "sample_payloads"

router = APIRouter(prefix="/api", tags=["frontend"])


def _severity(savings: float) -> str:
    if savings >= 40:
        return "critical"
    if savings >= 20:
        return "high"
    if savings >= 10:
        return "medium"
    return "low"


def _tf_diff(resource_name: str, size_var: str, old_size: str, new_size: str) -> str:
    return (
        f'# terraform.tfvars\n'
        f'-{size_var} = "{old_size}"\n'
        f'+{size_var} = "{new_size}"'
    )


def _map_row(row: dict[str, Any]) -> dict[str, Any]:
    resource_id = row.get("RESOURCE_ID") or "unknown"
    old_size = row.get("OLD_SIZE") or "unknown"
    new_size = row.get("NEW_SIZE") or "unknown"
    savings = float(row.get("ESTIMATED_SAVINGS") or 0)
    old_price = float(row.get("OLD_PRICE") or 0)
    new_price = float(row.get("NEW_PRICE") or 0)
    explanation = row.get("EXPLANATION") or f"Downsize from {old_size} to {new_size} — estimated ${savings:.0f}/month savings."
    region = row.get("REGION") or "nyc3"
    tf_name = row.get("TF_NAME") or resource_id
    size_var = row.get("SIZE_VAR") or "droplet_size"

    return {
        "id": resource_id,
        "name": tf_name,
        "provider": "DigitalOcean",
        "type": "Droplet",
        "equivalentCategory": "Compute",
        "region": region,
        "currentCost": old_price,
        "optimizedCost": new_price,
        "cpuUsage": float(row.get("AVG_CPU") or 0),
        "memoryUsage": 0,
        "networkUsageGb": 0,
        "utilizationScore": int((new_price / old_price * 100)) if old_price else 0,
        "trendCurrent": [old_price] * 12,
        "trendOptimized": [new_price] * 12,
        "recommendation": explanation,
        "terraformDiff": _tf_diff(tf_name, size_var, old_size, new_size),
        "terraformFile": "terraform.tfvars",
        "severity": _severity(savings),
        "approvalStatus": "pending",
    }


@router.get("/recommendations")
def get_recommendations() -> dict[str, Any]:
    settings = get_settings()
    names = SnowflakeNames.from_settings(settings)
    db = names.database

    try:
        rows = run_sql_with_context_no_schema(
            settings,
            sql=f"""
            WITH latest_ts AS (
              SELECT MAX(created_at) AS max_ts
              FROM "{db}"."{names.schema_cost}"."COST_RECOMMENDATIONS"
              WHERE resource_id IS NOT NULL AND resource_id <> ''
                AND old_size IS NOT NULL AND old_size <> 'unknown'
            ),
            recs AS (
              SELECT created_at, resource_id, old_size, new_size, estimated_savings
              FROM "{db}"."{names.schema_cost}"."COST_RECOMMENDATIONS"
              WHERE resource_id IS NOT NULL AND resource_id <> ''
                AND old_size IS NOT NULL AND old_size <> 'unknown'
                AND created_at >= DATEADD('minute', -5, (SELECT max_ts FROM latest_ts))
              QUALIFY ROW_NUMBER() OVER (PARTITION BY resource_id ORDER BY created_at DESC) = 1
            )
            SELECT
              r.resource_id,
              r.old_size,
              r.new_size,
              r.estimated_savings,
              os.price_monthly  AS old_price,
              ns.price_monthly  AS new_price,
              s.explanation,
              t.region,
              t.payload:name::STRING       AS tf_name,
              t.payload:size_var::STRING   AS size_var,
              (100 - COALESCE(c.avg_cpu, 100)) AS avg_cpu
            FROM recs r
            LEFT JOIN "{db}"."{names.schema_cost}"."SIZES" os ON os.slug = r.old_size
            LEFT JOIN "{db}"."{names.schema_cost}"."SIZES" ns ON ns.slug = r.new_size
            LEFT JOIN (
              SELECT resource_id, explanation
              FROM "{db}"."{names.schema_terraform}"."TERRAFORM_SUGGESTIONS"
              WHERE suggestion_type = 'recommendation_summary'
              QUALIFY ROW_NUMBER() OVER (PARTITION BY resource_id ORDER BY created_at DESC) = 1
            ) s ON s.resource_id = r.resource_id
            LEFT JOIN (
              SELECT droplet_size, region, payload
              FROM "{db}"."{names.schema_terraform}"."CLEAN"
              QUALIFY ROW_NUMBER() OVER (PARTITION BY droplet_size ORDER BY ingested_at DESC) = 1
            ) t ON t.droplet_size = r.old_size
            LEFT JOIN (
              SELECT resource_id,
                     AVG(TRY_TO_NUMBER(v.value[1]::STRING, 38, 10)) AS avg_cpu
              FROM "{db}"."{names.schema_metrics}"."CLEAN",
                   LATERAL FLATTEN(input => metric_values) v
              WHERE metric_name = 'idle'
              GROUP BY resource_id
            ) c ON c.resource_id = r.resource_id;
            """,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"snowflake_query_failed: {e}") from e

    resources = [
        _map_row(r) for r in rows
        if r.get("RESOURCE_ID") and r.get("OLD_SIZE") not in (None, "unknown", "")
    ]
    return {
        "scannedAt": datetime.utcnow().isoformat(),
        "resources": resources,
    }


@router.post("/chat")
async def chat(question: str = Body(..., embed=True)) -> dict[str, Any]:
    settings = get_settings()
    names = SnowflakeNames.from_settings(settings)

    # Fetch context from Snowflake
    try:
        recs_rows = run_sql_with_context_no_schema(
            settings,
            sql=f"""
            SELECT resource_id, old_size, new_size, estimated_savings
            FROM "{names.database}"."{names.schema_cost}"."COST_RECOMMENDATIONS"
            ORDER BY created_at DESC LIMIT 20;
            """,
        )
        metrics_rows = run_sql_with_context_no_schema(
            settings,
            sql=f"""
            SELECT resource_id, metric_name, payload
            FROM "{names.database}"."{names.schema_metrics}"."CLEAN"
            QUALIFY ROW_NUMBER() OVER (PARTITION BY resource_id, metric_name ORDER BY ingested_at DESC) = 1
            LIMIT 10;
            """,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"context_fetch_failed: {e}") from e

    context = (
        f"Cost recommendations:\n{json.dumps(recs_rows, default=str)}\n\n"
        f"Latest metrics:\n{json.dumps(metrics_rows, default=str)}"
    )

    try:
        answer = await chat_complete(
            settings,
            messages=[
                {"role": "system", "content": "You are a helpful assistant for cloud cost optimization. Answer concisely using the context provided."},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
            ],
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"do_ai_chat_failed: {e}") from e

    return {"answer": answer}


class PipelineRunRequest(BaseModel):
    github_token: str = ""
    repo_owner: str = ""
    repo_name: str = ""
    branch: str = "main"


@router.post("/pipeline/run")
async def run_pipeline(body: PipelineRunRequest = Body(default=PipelineRunRequest())) -> dict[str, Any]:
    settings = get_settings()
    names = SnowflakeNames.from_settings(settings)
    db = names.database
    run_id = uuid.uuid4().hex
    steps: list[str] = []

    # 1. Ingest DO sizes
    try:
        await ingest_digitalocean_sizes(settings, filename=f"sizes_{run_id}.json")
        steps.append("ingest_do_sizes: ok")
    except Exception as e:
        steps.append(f"ingest_do_sizes: skipped ({e})")

    # 2. Ingest sample metric payloads
    if _SAMPLE_PAYLOADS_DIR.is_dir():
        for path in sorted(_SAMPLE_PAYLOADS_DIR.glob("*.json")):
            try:
                payload = json.loads(path.read_text())
                ingest_metrics_json(settings, payload=payload, filename=f"{path.stem}_{run_id}.json")
                steps.append(f"ingest_metrics:{path.stem}: ok")
            except Exception as e:
                steps.append(f"ingest_metrics:{path.stem}: failed ({e})")
    else:
        steps.append("ingest_metrics: no sample_payloads dir found")

    # 3. Ingest Terraform — GitHub repo takes priority over local path
    if body.github_token and body.repo_owner and body.repo_name:
        try:
            await ingest_terraform_from_github(
                settings,
                owner=body.repo_owner,
                repo=body.repo_name,
                branch=body.branch or "main",
                token=body.github_token,
                run_id=run_id,
            )
            steps.append(f"ingest_terraform_github:{body.repo_owner}/{body.repo_name}: ok")
        except Exception as e:
            steps.append(f"ingest_terraform_github: failed ({e})")
    elif settings.terraform_local_path:
        try:
            ingest_terraform_from_local(settings, run_id=run_id)
            steps.append("ingest_terraform_local: ok")
        except Exception as e:
            steps.append(f"ingest_terraform_local: failed ({e})")
    else:
        steps.append("ingest_terraform: skipped (no GitHub token or local path configured)")

    # 4-7. Run stored procedures in sequence
    sp_calls = [
        ("clean_metrics",   f'CALL "{db}"."{names.schema_metrics}"."SP_CLEAN_RAW"();'),
        ("clean_terraform", f'CALL "{db}"."{names.schema_terraform}"."SP_CLEAN_RAW"();'),
        ("analyze_metrics", f'CALL "{db}"."{names.schema_cost}"."SP_ANALYZE_METRICS"();'),
    ]
    # Recreate SP_REFRESH_SIZES with the dedup fix before analyze runs
    try:
        run_sql_with_context_no_schema(
            settings,
            sql=f"""
            CREATE OR REPLACE PROCEDURE "{db}"."{names.schema_cost}"."SP_REFRESH_SIZES"()
            RETURNS STRING
            LANGUAGE SQL
            AS
            $$
              BEGIN
                MERGE INTO "{db}"."{names.schema_cost}"."SIZES" t
                USING (
                  SELECT
                    s.value:slug::STRING AS slug,
                    s.value:available::BOOLEAN AS available,
                    s.value:description::STRING AS description,
                    s.value:disk::NUMBER AS disk_gb,
                    s.value:transfer::NUMBER AS transfer_tb,
                    s.value:vcpus::NUMBER AS vcpus,
                    s.value:memory::NUMBER AS memory_mb,
                    s.value:networking_throughput::NUMBER AS networking_throughput,
                    s.value:price_hourly::NUMBER AS price_hourly,
                    s.value:price_monthly::NUMBER AS price_monthly,
                    s.value:disk_info[0]:type::STRING AS disk_type,
                    s.value:disk_info[0]:size:amount::NUMBER AS disk_size_gib,
                    s.value:disk_info[0]:size:unit::STRING AS disk_unit,
                    s.value AS payload
                  FROM (
                    SELECT payload FROM "{db}"."{names.schema_cost}"."SIZES_RAW"
                    ORDER BY ingested_at DESC LIMIT 1
                  ) r,
                  LATERAL FLATTEN(input => r.payload:sizes) s
                ) src
                ON t.slug = src.slug
                WHEN MATCHED THEN UPDATE SET
                  available = src.available, description = src.description,
                  disk_gb = src.disk_gb, transfer_tb = src.transfer_tb,
                  vcpus = src.vcpus, memory_mb = src.memory_mb,
                  networking_throughput = src.networking_throughput,
                  price_hourly = src.price_hourly, price_monthly = src.price_monthly,
                  disk_type = src.disk_type, disk_size_gib = src.disk_size_gib,
                  disk_unit = src.disk_unit, payload = src.payload
                WHEN NOT MATCHED THEN INSERT (
                  slug, available, description, disk_gb, transfer_tb, vcpus, memory_mb,
                  networking_throughput, price_hourly, price_monthly,
                  disk_type, disk_size_gib, disk_unit, payload
                ) VALUES (
                  src.slug, src.available, src.description, src.disk_gb, src.transfer_tb,
                  src.vcpus, src.memory_mb, src.networking_throughput,
                  src.price_hourly, src.price_monthly,
                  src.disk_type, src.disk_size_gib, src.disk_unit, src.payload
                );
                RETURN 'ok';
              END;
            $$;
            """,
        )
        steps.append("recreate_sp_refresh_sizes: ok")
    except Exception as e:
        steps.append(f"recreate_sp_refresh_sizes: failed ({e})")

    errors: list[str] = []
    for sp_name, sql in sp_calls:
        try:
            run_sql_with_context_no_schema(settings, sql=sql)
            steps.append(f"{sp_name}: ok")
        except Exception as e:
            steps.append(f"{sp_name}: failed ({e})")
            errors.append(f"{sp_name}: {e}")

    # 8. Summarize recommendations via DigitalOcean AI (replaces Cortex)
    try:
        recs = run_sql_with_context_no_schema(
            settings,
            sql=f"""
            SELECT r.resource_id, r.old_size, r.new_size, r.estimated_savings,
                   m.payload AS metrics_payload
            FROM "{db}"."{names.schema_cost}"."COST_RECOMMENDATIONS" r
            LEFT JOIN "{db}"."{names.schema_metrics}"."CLEAN" m ON m.resource_id = r.resource_id
            QUALIFY ROW_NUMBER() OVER (PARTITION BY r.resource_id ORDER BY r.created_at DESC, m.ingested_at DESC) = 1
            LIMIT 20;
            """,
        )
        for rec in recs:
            rid = rec.get("RESOURCE_ID") or "unknown"
            prompt = (
                f"You are a cloud cost optimization assistant. Explain this recommendation in 2-3 plain English sentences.\n"
                f"Resource: {rid}\n"
                f"Current size: {rec.get('OLD_SIZE')} → Recommended: {rec.get('NEW_SIZE')}\n"
                f"Estimated monthly savings: ${rec.get('ESTIMATED_SAVINGS') or 'unknown'}\n"
                f"Metrics context: {json.dumps(rec.get('METRICS_PAYLOAD'), default=str)}"
            )
            explanation = await chat_complete(
                settings,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
            )
            run_sql_with_context_no_schema(
                settings,
                sql=f"""
                INSERT INTO "{db}"."{names.schema_terraform}"."TERRAFORM_SUGGESTIONS"
                  (suggestion_type, resource_id, terraform_config, explanation)
                VALUES (
                  'recommendation_summary',
                  '{rid.replace("'", "''")}',
                  NULL,
                  '{explanation.replace("'", "''")}'
                );
                """,
            )
        steps.append(f"do_ai_summarize: ok ({len(recs)} recommendations)")
    except Exception as e:
        steps.append(f"do_ai_summarize: failed ({e})")
        errors.append(f"do_ai_summarize: {e}")

    return {
        "runId": run_id,
        "steps": steps,
        "errors": errors,
        "completedAt": datetime.utcnow().isoformat(),
    }
