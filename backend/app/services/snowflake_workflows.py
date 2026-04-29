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

    ALTER TABLE "{db}"."{names.schema_metrics}"."CLEAN"
      ADD COLUMN IF NOT EXISTS metric_values ARRAY;

    CREATE TABLE IF NOT EXISTS "{db}"."{names.schema_metrics}"."CLEAN_STATE" (
      last_cleaned_at TIMESTAMP_NTZ
    );

    INSERT INTO "{db}"."{names.schema_metrics}"."CLEAN_STATE"(last_cleaned_at)
    SELECT TO_TIMESTAMP_NTZ(0)
    WHERE NOT EXISTS (SELECT 1 FROM "{db}"."{names.schema_metrics}"."CLEAN_STATE");

    CREATE OR REPLACE PROCEDURE "{db}"."{names.schema_metrics}"."SP_CLEAN_RAW"()
    RETURNS STRING
    LANGUAGE SQL
    AS
    $$
      BEGIN
        CREATE TEMP TABLE IF NOT EXISTS _tmp_clean_state AS
        SELECT COALESCE(MAX(last_cleaned_at), TO_TIMESTAMP_NTZ(0)) AS last_cleaned_at
        FROM "{db}"."{names.schema_metrics}"."CLEAN_STATE";

        INSERT INTO "{db}"."{names.schema_metrics}"."CLEAN"(ingested_at, resource_id, metric_name, payload, metric_values)
        SELECT
          r.ingested_at,
          rr.value:metric:host_id::STRING AS resource_id,
          COALESCE(rr.value:metric:mode::STRING, rr.value:metric:name::STRING, 'unknown') AS metric_name,
          OBJECT_CONSTRUCT(
            'metric', rr.value:metric,
            'values', rr.value:values,
            'source', 'do.monitoring.matrix'
          ) AS payload,
          rr.value:values AS metric_values
        FROM "{db}"."{names.schema_metrics}"."RAW" r,
             LATERAL FLATTEN(input => r.payload:data:result) rr
        WHERE r.payload:data:resultType::STRING = 'matrix'
          AND r.ingested_at > (SELECT last_cleaned_at FROM _tmp_clean_state);

        UPDATE "{db}"."{names.schema_metrics}"."CLEAN_STATE"
        SET last_cleaned_at = (
          SELECT COALESCE(MAX(ingested_at), (SELECT last_cleaned_at FROM _tmp_clean_state))
          FROM "{db}"."{names.schema_metrics}"."RAW"
        );

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

    CREATE TABLE IF NOT EXISTS "{db}"."{names.schema_cost}"."SIZES" (
      slug STRING,
      available BOOLEAN,
      description STRING,
      disk_gb NUMBER,
      transfer_tb NUMBER,
      vcpus NUMBER,
      memory_mb NUMBER,
      networking_throughput NUMBER,
      price_hourly NUMBER(18,6),
      price_monthly NUMBER(10,2),
      disk_type STRING,
      disk_size_gib NUMBER,
      disk_unit STRING,
      payload VARIANT
    );

    ALTER TABLE "{db}"."{names.schema_cost}"."SIZES" ADD COLUMN IF NOT EXISTS available BOOLEAN;
    ALTER TABLE "{db}"."{names.schema_cost}"."SIZES" ADD COLUMN IF NOT EXISTS description STRING;
    ALTER TABLE "{db}"."{names.schema_cost}"."SIZES" ADD COLUMN IF NOT EXISTS disk_gb NUMBER;
    ALTER TABLE "{db}"."{names.schema_cost}"."SIZES" ADD COLUMN IF NOT EXISTS transfer_tb NUMBER;
    ALTER TABLE "{db}"."{names.schema_cost}"."SIZES" ADD COLUMN IF NOT EXISTS networking_throughput NUMBER;
    ALTER TABLE "{db}"."{names.schema_cost}"."SIZES" ADD COLUMN IF NOT EXISTS price_hourly NUMBER(18,6);
    ALTER TABLE "{db}"."{names.schema_cost}"."SIZES" ADD COLUMN IF NOT EXISTS disk_type STRING;
    ALTER TABLE "{db}"."{names.schema_cost}"."SIZES" ADD COLUMN IF NOT EXISTS disk_size_gib NUMBER;
    ALTER TABLE "{db}"."{names.schema_cost}"."SIZES" ADD COLUMN IF NOT EXISTS disk_unit STRING;

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
          FROM "{db}"."{names.schema_cost}"."SIZES_RAW" r,
               LATERAL FLATTEN(input => r.payload:sizes) s
        ) src
        ON t.slug = src.slug
        WHEN MATCHED THEN UPDATE SET
          available = src.available,
          description = src.description,
          disk_gb = src.disk_gb,
          transfer_tb = src.transfer_tb,
          vcpus = src.vcpus,
          memory_mb = src.memory_mb,
          networking_throughput = src.networking_throughput,
          price_hourly = src.price_hourly,
          price_monthly = src.price_monthly,
          disk_type = src.disk_type,
          disk_size_gib = src.disk_size_gib,
          disk_unit = src.disk_unit,
          payload = src.payload
        WHEN NOT MATCHED THEN INSERT (
          slug,
          available,
          description,
          disk_gb,
          transfer_tb,
          vcpus,
          memory_mb,
          networking_throughput,
          price_hourly,
          price_monthly,
          disk_type,
          disk_size_gib,
          disk_unit,
          payload
        )
          VALUES (
            src.slug,
            src.available,
            src.description,
            src.disk_gb,
            src.transfer_tb,
            src.vcpus,
            src.memory_mb,
            src.networking_throughput,
            src.price_hourly,
            src.price_monthly,
            src.disk_type,
            src.disk_size_gib,
            src.disk_unit,
            src.payload
          );
        RETURN 'ok';
      END;
    $$;

    CREATE OR REPLACE PROCEDURE "{db}"."{names.schema_cost}"."SP_ANALYZE_METRICS"()
    RETURNS STRING
    LANGUAGE SQL
    AS
    $$
      BEGIN
        CALL "{db}"."{names.schema_cost}"."SP_REFRESH_SIZES"();

        CREATE TEMP TABLE IF NOT EXISTS _tmp_metrics AS
        WITH base AS (
          SELECT resource_id, metric_name, metric_values
          FROM "{db}"."{names.schema_metrics}"."CLEAN"
        ),
        cpu AS (
          -- DO CPU often comes as per-mode %; we derive usage from idle: usage = 100 - idle.
          SELECT
            resource_id,
            AVG(100.0 - TRY_TO_NUMBER(v.value[1]::STRING, 38, 10)) AS avg_cpu_percent,
            APPROX_PERCENTILE(100.0 - TRY_TO_NUMBER(v.value[1]::STRING, 38, 10), 0.95) AS p95_cpu_percent
          FROM base, LATERAL FLATTEN(input => metric_values) v
          WHERE metric_name = 'idle'
          GROUP BY resource_id
        ),
        mem_used AS (
          -- Expect metric_name like 'used_bytes' (from our sample), value is bytes.
          SELECT
            resource_id,
            MAX(TRY_TO_NUMBER(v.value[1]::STRING, 38, 0)) AS max_mem_used_bytes,
            APPROX_PERCENTILE(TRY_TO_NUMBER(v.value[1]::STRING, 38, 0), 0.95) AS p95_mem_used_bytes
          FROM base, LATERAL FLATTEN(input => metric_values) v
          WHERE metric_name IN ('used_bytes', 'memory_used_bytes')
          GROUP BY resource_id
        )
        SELECT
          c.resource_id,
          c.avg_cpu_percent,
          c.p95_cpu_percent,
          m.max_mem_used_bytes,
          m.p95_mem_used_bytes
        FROM cpu c
        LEFT JOIN mem_used m ON m.resource_id = c.resource_id;

        -- Heuristic requirements:
        -- - vCPU: if p95 CPU < 20% on current box, suggest 1 vCPU; if < 50% suggest 2 vCPU else 4.
        -- - RAM: take p95 used * 1.5 headroom (min 1GiB) and pick smallest size with enough memory.
        CREATE TEMP TABLE IF NOT EXISTS _tmp_req AS
        SELECT
          resource_id,
          CASE
            WHEN p95_cpu_percent IS NULL THEN 1
            WHEN p95_cpu_percent < 20 THEN 1
            WHEN p95_cpu_percent < 50 THEN 2
            ELSE 4
          END AS req_vcpus,
          CEIL(GREATEST(1024.0, (COALESCE(p95_mem_used_bytes, 0) / 1024.0 / 1024.0) * 1.5)) AS req_mem_mb
        FROM _tmp_metrics;

        -- Choose the cheapest size satisfying requirements.
        CREATE TEMP TABLE IF NOT EXISTS _tmp_choice AS
        SELECT
          r.resource_id,
          s.slug AS new_size,
          s.price_monthly AS new_price_monthly,
          r.req_vcpus,
          r.req_mem_mb
        FROM _tmp_req r
        JOIN "{db}"."{names.schema_cost}"."SIZES" s
          ON s.vcpus >= r.req_vcpus AND s.memory_mb >= r.req_mem_mb
        QUALIFY ROW_NUMBER() OVER (PARTITION BY r.resource_id ORDER BY s.price_monthly ASC, s.vcpus ASC, s.memory_mb ASC) = 1;

        INSERT INTO "{db}"."{names.schema_cost}"."COST_RECOMMENDATIONS"(resource_id, old_size, new_size, estimated_savings, reason)
        SELECT
          c.resource_id,
          'unknown' AS old_size,
          c.new_size,
          NULL AS estimated_savings,
          'cpu_mem_sizes_catalog' AS reason
        FROM _tmp_choice c;
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
