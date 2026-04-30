from __future__ import annotations

from functools import lru_cache

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # repo-root (.env sits next to backend/, frontend/, terraform/)
        env_file=str(Path(__file__).resolve().parents[3] / ".env"),
        extra="ignore",
    )

    app_env: str = "local"
    cors_origins: str = ""

    database_url: str = ""
    redis_url: str = ""

    github_webhook_secret: str = ""
    internal_job_token: str = ""
    manual_trigger_token: str = ""

    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = ""
    github_token_encryption_key: str = ""

    scheduler_enabled: bool = True

    snowflake_account: str = ""
    snowflake_user: str = ""
    snowflake_password: str = ""
    snowflake_token: str = ""
    snowflake_role: str = ""
    snowflake_warehouse: str = ""
    snowflake_database: str = ""
    snowflake_schema_core: str = "CORE"
    snowflake_schema_metrics: str = "METRICS"
    snowflake_schema_resources: str = "RESOURCES"
    snowflake_schema_terraform: str = "TERRAFORM_CONFIG"
    snowflake_schema_cost: str = "COST"

    snowflake_stage_landing: str = "LANDING_STAGE"
    snowflake_integration_user: str = ""
    snowflake_integration_user_password: str = ""

    digitalocean_token: str = ""
    digitalocean_openapi_key: str = ""

    terraform_local_path: str = ""

    elevenlabs_api_key: str = ""
    elevenlabs_agent_id: str = ""
    elevenlabs_agent_phone_number_id: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    public_base_url: str = ""
    call_security_code: str = "1234"
    customer_phone_number: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
