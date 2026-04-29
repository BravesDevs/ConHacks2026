from __future__ import annotations

from app.core.config import Settings
from app.services.snowflake_service import SnowflakeNames, run_sql


def ensure_cleaning_procs_and_tasks(settings: Settings) -> None:
    names = SnowflakeNames.from_settings(settings)
    db = names.database

    sql = f"""
    USE DATABASE "{db}";

    CREATE TABLE IF NOT EXISTS "{db}"."{names.schema_metrics}"."CLEAN" (
      ingested_at TIMESTAMP_NTZ,
      resource_id STRING,
      metric_name STRING,
      payload VARIANT
    );

    CREATE OR REPLACE PROCEDURE "{db}"."{names.schema_metrics}"."SP_CLEAN_RAW"()
    RETURNS STRING
    LANGUAGE SQL
    AS
    $$
      BEGIN
        INSERT INTO "{db}"."{names.schema_metrics}"."CLEAN"(ingested_at, resource_id, metric_name, payload)
        SELECT r.ingested_at,
               r.payload:resource_id::STRING,
               r.payload:metric_name::STRING,
               r.payload
        FROM "{db}"."{names.schema_metrics}"."RAW" r;
        RETURN 'ok';
      END;
    $$;

    CREATE TASK IF NOT EXISTS "{db}"."{names.schema_metrics}"."TASK_CLEAN_RAW"
      WAREHOUSE = "{names.warehouse}"
      SCHEDULE = 'USING CRON 0 * * * * UTC'
    AS
      CALL "{db}"."{names.schema_metrics}"."SP_CLEAN_RAW"();
    """
    run_sql(settings, sql=sql)


def ensure_suggestion_procs_and_tasks(settings: Settings) -> None:
    names = SnowflakeNames.from_settings(settings)
    db = names.database

    sql = f"""
    USE DATABASE "{db}";

    CREATE TABLE IF NOT EXISTS "{db}"."{names.schema_cost}"."COST_RECOMMENDATIONS" (
      created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
      resource_id STRING,
      old_size STRING,
      new_size STRING,
      estimated_savings NUMBER(10,2),
      reason STRING
    );

    CREATE OR REPLACE PROCEDURE "{db}"."{names.schema_cost}"."SP_ANALYZE_METRICS"()
    RETURNS STRING
    LANGUAGE SQL
    AS
    $$
      BEGIN
        -- Placeholder: replace with real logic.
        INSERT INTO "{db}"."{names.schema_cost}"."COST_RECOMMENDATIONS"(resource_id, old_size, new_size, estimated_savings, reason)
        SELECT DISTINCT
          c.resource_id,
          'unknown',
          'unknown',
          0,
          'analysis_not_implemented'
        FROM "{db}"."{names.schema_metrics}"."CLEAN" c;
        RETURN 'ok';
      END;
    $$;

    CREATE TASK IF NOT EXISTS "{db}"."{names.schema_cost}"."TASK_ANALYZE_METRICS"
      WAREHOUSE = "{names.warehouse}"
      SCHEDULE = 'USING CRON 15 * * * * UTC'
    AS
      CALL "{db}"."{names.schema_cost}"."SP_ANALYZE_METRICS"();
    """
    run_sql(settings, sql=sql)


def ensure_cortex_procs_and_tasks(settings: Settings) -> None:
    names = SnowflakeNames.from_settings(settings)
    db = names.database

    sql = f"""
    USE DATABASE "{db}";

    CREATE TABLE IF NOT EXISTS "{db}"."{names.schema_terraform}"."TERRAFORM_SUGGESTIONS" (
      created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
      terraform_config VARIANT,
      explanation STRING
    );

    CREATE OR REPLACE PROCEDURE "{db}"."{names.schema_terraform}"."SP_CORTEX_TERRAFORM"()
    RETURNS STRING
    LANGUAGE SQL
    AS
    $$
      BEGIN
        -- Placeholder: wire up Snowflake Cortex calls once model/prompt is finalized.
        INSERT INTO "{db}"."{names.schema_terraform}"."TERRAFORM_SUGGESTIONS"(terraform_config, explanation)
        SELECT PARSE_JSON('{{\"todo\":true}}'), 'cortex_not_implemented';
        RETURN 'ok';
      END;
    $$;

    CREATE TASK IF NOT EXISTS "{db}"."{names.schema_terraform}"."TASK_CORTEX_TERRAFORM"
      WAREHOUSE = "{names.warehouse}"
      SCHEDULE = 'USING CRON 30 * * * * UTC'
    AS
      CALL "{db}"."{names.schema_terraform}"."SP_CORTEX_TERRAFORM"();
    """
    run_sql(settings, sql=sql)
