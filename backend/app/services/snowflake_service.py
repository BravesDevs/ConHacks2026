from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import snowflake.connector

from app.core.config import Settings


@dataclass(frozen=True)
class SnowflakeNames:
    database: str
    schema_core: str
    schema_metrics: str
    schema_resources: str
    schema_terraform: str
    schema_cost: str
    warehouse: str
    role: str
    stage_landing: str
    integration_user: str

    @staticmethod
    def from_settings(settings: Settings) -> "SnowflakeNames":
        return SnowflakeNames(
            database=settings.snowflake_database,
            schema_core=settings.snowflake_schema_core,
            schema_metrics=settings.snowflake_schema_metrics,
            schema_resources=settings.snowflake_schema_resources,
            schema_terraform=settings.snowflake_schema_terraform,
            schema_cost=settings.snowflake_schema_cost,
            warehouse=settings.snowflake_warehouse,
            role=settings.snowflake_role,
            stage_landing=settings.snowflake_stage_landing,
            integration_user=settings.snowflake_integration_user,
        )


def _connect_admin(settings: Settings) -> snowflake.connector.SnowflakeConnection:
    return snowflake.connector.connect(
        account=settings.snowflake_account,
        user=settings.snowflake_user,
        password=settings.snowflake_token or settings.snowflake_password,
        role=settings.snowflake_role or None,
        warehouse=settings.snowflake_warehouse or None,
        autocommit=True,
    )


def _connect_integration(settings: Settings) -> snowflake.connector.SnowflakeConnection:
    return snowflake.connector.connect(
        account=settings.snowflake_account,
        user=settings.snowflake_user,
        password=settings.snowflake_token or settings.snowflake_password,
        role=settings.snowflake_role or None,
        warehouse=settings.snowflake_warehouse or None,
        database=settings.snowflake_database or None,
        autocommit=True,
    )


def _exec_many(
    cur: snowflake.connector.cursor.SnowflakeCursor, statements: Sequence[str]
) -> None:
    for stmt in statements:
        cur.execute(stmt)


def ensure_snowflake_setup(settings: Settings) -> None:
    names = SnowflakeNames.from_settings(settings)
    if not names.database:
        raise ValueError("SNOWFLAKE_DATABASE (settings.snowflake_database) is required")
    if not names.warehouse:
        raise ValueError(
            "SNOWFLAKE_WAREHOUSE (settings.snowflake_warehouse) is required"
        )
    if not names.role:
        raise ValueError("SNOWFLAKE_ROLE (settings.snowflake_role) is required")
    if not settings.snowflake_user:
        raise ValueError("SNOWFLAKE_USER is required")
    if not settings.snowflake_token and not settings.snowflake_password:
        raise ValueError(
            "SNOWFLAKE_TOKEN (preferred) or SNOWFLAKE_PASSWORD is required"
        )

    with _connect_admin(settings) as conn:
        cur = conn.cursor()
        try:
            _exec_many(
                cur,
                [
                    f'CREATE WAREHOUSE IF NOT EXISTS "{names.warehouse}" WAREHOUSE_SIZE = XSMALL AUTO_SUSPEND = 60 AUTO_RESUME = TRUE;',
                    f'CREATE DATABASE IF NOT EXISTS "{names.database}";',
                    f'CREATE ROLE IF NOT EXISTS "{names.role}";',
                    f'GRANT USAGE ON WAREHOUSE "{names.warehouse}" TO ROLE "{names.role}";',
                    f'GRANT USAGE ON DATABASE "{names.database}" TO ROLE "{names.role}";',
                ],
            )

            schemas = [
                names.schema_core,
                names.schema_metrics,
                names.schema_resources,
                names.schema_terraform,
                names.schema_cost,
            ]
            for sch in schemas:
                cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{names.database}"."{sch}";')
                cur.execute(
                    f'GRANT USAGE ON SCHEMA "{names.database}"."{sch}" TO ROLE "{names.role}";'
                )
                cur.execute(
                    f'GRANT CREATE TABLE ON SCHEMA "{names.database}"."{sch}" TO ROLE "{names.role}";'
                )

            # If you want a dedicated ingestion user, add SNOWFLAKE_INTEGRATION_USER(+password)
            # and extend this setup; for now we assume the same user/PAT is used for setup+ingest.

            cur.execute(f'USE DATABASE "{names.database}";')
            cur.execute(f'USE SCHEMA "{names.schema_core}";')
            cur.execute(f'USE WAREHOUSE "{names.warehouse}";')

            cur.execute(
                f'CREATE STAGE IF NOT EXISTS "{names.stage_landing}" FILE_FORMAT = (TYPE = JSON) DIRECTORY = (ENABLE = TRUE);'
            )
            cur.execute(
                f'GRANT READ, WRITE ON STAGE "{names.database}"."{names.schema_core}"."{names.stage_landing}" TO ROLE "{names.role}";'
            )

            _exec_many(
                cur,
                [
                    f'CREATE TABLE IF NOT EXISTS "{names.database}"."{names.schema_metrics}"."RAW" (ingested_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(), payload VARIANT);',
                    f'CREATE TABLE IF NOT EXISTS "{names.database}"."{names.schema_resources}"."RAW" (ingested_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(), payload VARIANT);',
                    f'CREATE TABLE IF NOT EXISTS "{names.database}"."{names.schema_terraform}"."RAW" (ingested_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(), payload VARIANT);',
                    f'CREATE TABLE IF NOT EXISTS "{names.database}"."{names.schema_cost}"."SIZES_RAW" (ingested_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(), payload VARIANT);',
                ],
            )

            for fq in [
                f'"{names.database}"."{names.schema_metrics}"."RAW"',
                f'"{names.database}"."{names.schema_resources}"."RAW"',
                f'"{names.database}"."{names.schema_terraform}"."RAW"',
                f'"{names.database}"."{names.schema_cost}"."SIZES_RAW"',
            ]:
                cur.execute(
                    f'GRANT INSERT, SELECT ON TABLE {fq} TO ROLE "{names.role}";'
                )

            cur.execute(
                f"""
                CREATE PIPE IF NOT EXISTS "{names.database}"."{names.schema_metrics}"."RAW_PIPE"
                AUTO_INGEST=FALSE
                AS
                COPY INTO "{names.database}"."{names.schema_metrics}"."RAW"(payload)
                FROM (SELECT $1 FROM @"{names.database}"."{names.schema_core}"."{names.stage_landing}"/metrics)
                FILE_FORMAT=(TYPE=JSON);
                """
            )
            cur.execute(
                f"""
                CREATE PIPE IF NOT EXISTS "{names.database}"."{names.schema_resources}"."RAW_PIPE"
                AUTO_INGEST=FALSE
                AS
                COPY INTO "{names.database}"."{names.schema_resources}"."RAW"(payload)
                FROM (SELECT $1 FROM @"{names.database}"."{names.schema_core}"."{names.stage_landing}"/resources)
                FILE_FORMAT=(TYPE=JSON);
                """
            )
            cur.execute(
                f"""
                CREATE PIPE IF NOT EXISTS "{names.database}"."{names.schema_terraform}"."RAW_PIPE"
                AUTO_INGEST=FALSE
                AS
                COPY INTO "{names.database}"."{names.schema_terraform}"."RAW"(payload)
                FROM (SELECT $1 FROM @"{names.database}"."{names.schema_core}"."{names.stage_landing}"/terraform_config)
                FILE_FORMAT=(TYPE=JSON);
                """
            )
            cur.execute(
                f"""
                CREATE PIPE IF NOT EXISTS "{names.database}"."{names.schema_cost}"."SIZES_RAW_PIPE"
                AUTO_INGEST=FALSE
                AS
                COPY INTO "{names.database}"."{names.schema_cost}"."SIZES_RAW"(payload)
                FROM (SELECT $1 FROM @"{names.database}"."{names.schema_core}"."{names.stage_landing}"/do_sizes)
                FILE_FORMAT=(TYPE=JSON);
                """
            )
        finally:
            cur.close()


def _write_temp_json(data: Any) -> Path:
    fd, p = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    path = Path(p)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def upload_json_to_stage_and_ingest(
    settings: Settings,
    *,
    data: Mapping[str, Any] | Sequence[Any],
    stage_prefix: str,
    pipe_fqn: str,
    filename: str | None = None,
    poll_seconds: float = 0.5,
    poll_timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    names = SnowflakeNames.from_settings(settings)
    if not names.database or not names.schema_core:
        raise ValueError("Snowflake database/schema not configured")

    tmp_path = _write_temp_json(data)
    try:
        stage_path = f'@"{names.database}"."{names.schema_core}"."{names.stage_landing}"/{stage_prefix}'
        if filename:
            remote_name = filename
        else:
            remote_name = f"{int(time.time())}.json"

        with _connect_integration(settings) as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    f"PUT file://{tmp_path.as_posix()} {stage_path}/{remote_name} AUTO_COMPRESS=FALSE OVERWRITE=TRUE;"
                )
                cur.execute(f"ALTER PIPE {pipe_fqn} REFRESH;")

                deadline = time.time() + poll_timeout_seconds
                while True:
                    cur.execute(f"SELECT SYSTEM$PIPE_STATUS('{pipe_fqn}')")
                    status_raw = cur.fetchone()[0]
                    status = (
                        json.loads(status_raw)
                        if isinstance(status_raw, str)
                        else status_raw
                    )
                    pending = 0
                    try:
                        pending = int(status.get("pendingFileCount", 0))
                    except Exception:
                        pending = 0
                    if pending == 0 or time.time() >= deadline:
                        return {
                            "pipe_status": status,
                            "remote_name": remote_name,
                            "stage_path": stage_path,
                        }
                    time.sleep(poll_seconds)
            finally:
                cur.close()
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
