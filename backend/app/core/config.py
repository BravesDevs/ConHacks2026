from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
