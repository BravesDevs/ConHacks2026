from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from app.core.config import get_settings
from app.services.snowflake_service import SnowflakeNames, run_sql_with_context_no_schema

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
            WITH latest_recs AS (
              SELECT resource_id, old_size, new_size, estimated_savings, created_at
              FROM "{db}"."{names.schema_cost}"."COST_RECOMMENDATIONS"
              QUALIFY ROW_NUMBER() OVER (PARTITION BY resource_id ORDER BY created_at DESC) = 1
            ),
            latest_summaries AS (
              SELECT resource_id, explanation
              FROM "{db}"."{names.schema_terraform}"."TERRAFORM_SUGGESTIONS"
              WHERE suggestion_type = 'recommendation_summary'
              QUALIFY ROW_NUMBER() OVER (PARTITION BY resource_id ORDER BY created_at DESC) = 1
            ),
            latest_tf AS (
              SELECT
                payload:name::STRING AS tf_name,
                payload:size_var::STRING AS size_var,
                droplet_size,
                region
              FROM "{db}"."{names.schema_terraform}"."CLEAN"
              QUALIFY ROW_NUMBER() OVER (PARTITION BY droplet_size ORDER BY ingested_at DESC) = 1
            ),
            latest_cpu AS (
              SELECT
                resource_id,
                AVG(TRY_TO_NUMBER(v.value[1]::STRING, 38, 10)) AS avg_cpu
              FROM "{db}"."{names.schema_metrics}"."CLEAN",
                   LATERAL FLATTEN(input => metric_values) v
              WHERE metric_name = 'idle'
              GROUP BY resource_id
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
              t.tf_name,
              t.size_var,
              (100 - COALESCE(c.avg_cpu, 100)) AS avg_cpu
            FROM latest_recs r
            LEFT JOIN "{db}"."{names.schema_cost}"."SIZES" os ON os.slug = r.old_size
            LEFT JOIN "{db}"."{names.schema_cost}"."SIZES" ns ON ns.slug = r.new_size
            LEFT JOIN latest_summaries s ON s.resource_id = r.resource_id
            LEFT JOIN latest_tf t ON t.droplet_size = r.old_size
            LEFT JOIN latest_cpu c ON c.resource_id = r.resource_id
            ORDER BY r.estimated_savings DESC NULLS LAST;
            """,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"snowflake_query_failed: {e}") from e

    resources = [_map_row(r) for r in rows]
    return {
        "scannedAt": datetime.utcnow().isoformat(),
        "resources": resources,
    }


@router.post("/chat")
def chat(question: str = Body(..., embed=True)) -> dict[str, Any]:
    settings = get_settings()
    names = SnowflakeNames.from_settings(settings)

    try:
        q = question.replace("'", "''")
        rows = run_sql_with_context_no_schema(
            settings,
            sql=f"""
            WITH latest_metrics AS (
              SELECT resource_id, metric_name, payload,
                ROW_NUMBER() OVER (PARTITION BY resource_id, metric_name ORDER BY ingested_at DESC) AS rn
              FROM "{names.database}"."{names.schema_metrics}"."CLEAN"
            ),
            latest_tf AS (
              SELECT filename, payload,
                ROW_NUMBER() OVER (PARTITION BY filename ORDER BY ingested_at DESC) AS rn
              FROM "{names.database}"."{names.schema_terraform}"."CLEAN"
            )
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
              'llama3.1-70b',
              CONCAT(
                'You are a helpful assistant for cloud cost optimization. Answer the user question using the context.\\n\\n',
                'User question: {q}\\n\\n',
                'Cost recommendations (JSON):\\n',
                COALESCE((SELECT TO_VARCHAR(TO_VARIANT(ARRAY_AGG(OBJECT_CONSTRUCT(*)))) FROM "{names.database}"."{names.schema_cost}"."COST_RECOMMENDATIONS"), '[]'),
                '\\n\\nLatest metrics:\\n',
                COALESCE((SELECT TO_VARCHAR(TO_VARIANT(ARRAY_AGG(OBJECT_CONSTRUCT('resource_id', resource_id, 'metric_name', metric_name, 'payload', payload)))) FROM latest_metrics WHERE rn = 1), '[]'),
                '\\n\\nTerraform resources:\\n',
                COALESCE((SELECT TO_VARCHAR(TO_VARIANT(ARRAY_AGG(payload))) FROM latest_tf WHERE rn = 1), '[]')
              )
            )::STRING AS ANSWER;
            """,
        )
        answer = rows[0].get("ANSWER") if rows else "No answer available."
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"cortex_chat_failed: {e}") from e

    return {"answer": answer}
