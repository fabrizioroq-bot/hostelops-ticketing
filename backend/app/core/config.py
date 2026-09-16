"""Application configuration, loaded from environment variables.

Never hardcode secrets here — every sensitive value comes from the
environment (see .env.example at the repo root).
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    supabase_jwt_secret: str

    # CORS
    cors_origins: str = "http://localhost:5173"

    # Session / security
    session_timeout_minutes: int = 30

    # Mews Connector API (PMS integration)
    mews_client_token: str | None = None
    mews_base_url: str = "https://api.mews.com/api/connector/v1"

    # Email (Resend) — used for scheduled weekly PDF reports
    resend_api_key: str | None = None
    resend_from_email: str = "reports@hostelops.example"
    report_recipient_emails: str = ""  # comma-separated fallback list

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def report_recipient_list(self) -> list[str]:
        return [e.strip() for e in self.report_recipient_emails.split(",") if e.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
