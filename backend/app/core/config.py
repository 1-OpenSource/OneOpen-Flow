from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "OneOpen Flow"
    api_prefix: str = "/api"
    secret_key: str = "replace-me-in-production"
    access_token_expire_minutes: int = 1440
    database_url: str = "sqlite:///./oneopen_flow.db"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    storage_backend: str = "local"
    storage_local_path: str = "../storage"
    s3_endpoint: str | None = None
    s3_bucket: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    encryption_key: str = "oneopen-flow-dev-encryption-key-32b"
    workboard_api_url: str = "http://localhost:8001/api"
    workboard_enabled: bool = True
    agent_job_signing_secret: str = "agent-job-signing-secret"
    default_locator_confidence_threshold: int = 90
    artifact_retention_days: int = 30
    max_cli_output_bytes: int = 2_000_000
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    frontend_url: str = "http://localhost:5173"
    # Optional env-based OIDC (overrides org settings when set)
    oidc_enabled: bool = False
    oidc_issuer: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
    oidc_redirect_uri: str | None = None
    oidc_scopes: str = "openid profile email"
    oidc_provider_name: str = "SSO"
    oidc_default_role: str = "member"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
