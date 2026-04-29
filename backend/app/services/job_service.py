from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings
from app.services.snowflake_service import run_sql_with_context_no_schema


@dataclass(frozen=True)
class JobRecord:
    job_id: str


def _ensure_jobs_table(settings: Settings) -> None:
    run_sql_with_context_no_schema(
        settings,
        sql=f"""
        CREATE TABLE IF NOT EXISTS "{settings.snowflake_database}"."CORE"."JOBS" (
          job_id STRING,
          created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
          updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
          status STRING,
          endpoint STRING,
          params VARIANT,
          error STRING
        );
        """,
    )


def start_job(
    settings: Settings, *, endpoint: str, params: dict[str, Any]
) -> JobRecord:
    _ensure_jobs_table(settings)
    job_id = str(uuid.uuid4())
    params_json = json.dumps(params)
    run_sql_with_context_no_schema(
        settings,
        sql=f"""
        INSERT INTO "{settings.snowflake_database}"."CORE"."JOBS"(job_id, status, endpoint, params)
        SELECT '{job_id}', 'started', '{endpoint.replace("'", "''")}', PARSE_JSON('{params_json.replace("'", "''")}');
        """,
    )
    return JobRecord(job_id=job_id)


def succeed_job(settings: Settings, *, job_id: str) -> None:
    run_sql_with_context_no_schema(
        settings,
        sql=f"""
        UPDATE "{settings.snowflake_database}"."CORE"."JOBS"
        SET status='succeeded', updated_at=CURRENT_TIMESTAMP()
        WHERE job_id='{job_id.replace("'", "''")}';
        """,
    )


def fail_job(settings: Settings, *, job_id: str, error: str) -> None:
    run_sql_with_context_no_schema(
        settings,
        sql=f"""
        UPDATE "{settings.snowflake_database}"."CORE"."JOBS"
        SET status='failed', updated_at=CURRENT_TIMESTAMP(), error='{error.replace("'", "''")}'
        WHERE job_id='{job_id.replace("'", "''")}';
        """,
    )


def get_job(settings: Settings, *, job_id: str) -> dict[str, Any] | None:
    rows = run_sql_with_context_no_schema(
        settings,
        sql=f"""
        SELECT job_id, created_at, updated_at, status, endpoint, params, error
        FROM "{settings.snowflake_database}"."CORE"."JOBS"
        WHERE job_id='{job_id.replace("'", "''")}'
        LIMIT 1;
        """,
    )
    return rows[-1] if rows else None
