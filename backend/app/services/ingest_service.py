from __future__ import annotations

from typing import Any, Mapping, Sequence

from app.core.config import Settings
from app.services.digitalocean_service import fetch_digitalocean_sizes
from app.services.snowflake_service import (
    SnowflakeNames,
    upload_json_to_stage_and_ingest,
)
from app.services.terraform_reader import parse_terraform_dir


def ingest_metrics_json(
    settings: Settings,
    *,
    payload: Mapping[str, Any] | Sequence[Any],
    filename: str | None = None,
) -> dict[str, Any]:
    names = SnowflakeNames.from_settings(settings)
    pipe = f'"{names.database}"."{names.schema_metrics}"."RAW_PIPE"'
    return upload_json_to_stage_and_ingest(
        settings,
        data=payload,
        stage_prefix="metrics",
        pipe_fqn=pipe,
        filename=filename,
    )


def ingest_resources_json(
    settings: Settings,
    *,
    payload: Mapping[str, Any] | Sequence[Any],
    filename: str | None = None,
) -> dict[str, Any]:
    names = SnowflakeNames.from_settings(settings)
    pipe = f'"{names.database}"."{names.schema_resources}"."RAW_PIPE"'
    return upload_json_to_stage_and_ingest(
        settings,
        data=payload,
        stage_prefix="resources",
        pipe_fqn=pipe,
        filename=filename,
    )


def ingest_terraform_config_json(
    settings: Settings,
    *,
    payload: Mapping[str, Any] | Sequence[Any],
    filename: str | None = None,
) -> dict[str, Any]:
    names = SnowflakeNames.from_settings(settings)
    pipe = f'"{names.database}"."{names.schema_terraform}"."RAW_PIPE"'
    return upload_json_to_stage_and_ingest(
        settings,
        data=payload,
        stage_prefix="terraform_config",
        pipe_fqn=pipe,
        filename=filename,
    )


def ingest_terraform_sample_file(
    settings: Settings, *, content: str, filename: str = "sample.tf"
) -> dict[str, Any]:
    names = SnowflakeNames.from_settings(settings)
    pipe = f'"{names.database}"."{names.schema_terraform}"."RAW_PIPE"'
    payload = {"filename": filename, "content": content, "type": "terraform_hcl"}
    return upload_json_to_stage_and_ingest(
        settings,
        data=payload,
        stage_prefix="terraform_config",
        pipe_fqn=pipe,
        filename=f"{filename}.json",
    )


def ingest_terraform_resolved_resources(
    settings: Settings,
    *,
    resources: Sequence[Mapping[str, Any]],
    filename: str = "resolved_resources.json",
) -> dict[str, Any]:
    names = SnowflakeNames.from_settings(settings)
    pipe = f'"{names.database}"."{names.schema_terraform}"."RAW_PIPE"'
    payload = {
        "filename": filename,
        "type": "terraform_resolved",
        "resources": resources,
    }
    return upload_json_to_stage_and_ingest(
        settings,
        data=payload,
        stage_prefix="terraform_config",
        pipe_fqn=pipe,
        filename=filename,
    )


def ingest_terraform_from_local(
    settings: Settings, *, run_id: str, filename: str | None = None
) -> dict[str, Any]:
    if not settings.terraform_local_path:
        raise ValueError("TERRAFORM_LOCAL_PATH is not configured")
    payload = parse_terraform_dir(settings.terraform_local_path)
    payload["run_id"] = run_id
    return ingest_terraform_config_json(settings, payload=payload, filename=filename)


async def ingest_digitalocean_sizes(
    settings: Settings, *, filename: str | None = None
) -> dict[str, Any]:
    names = SnowflakeNames.from_settings(settings)
    pipe = f'"{names.database}"."{names.schema_cost}"."SIZES_RAW_PIPE"'
    sizes_payload = await fetch_digitalocean_sizes(token=settings.digitalocean_token)
    return upload_json_to_stage_and_ingest(
        settings,
        data=sizes_payload,
        stage_prefix="do_sizes",
        pipe_fqn=pipe,
        filename=filename,
    )
