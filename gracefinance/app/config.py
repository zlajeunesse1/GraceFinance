"""
GraceFinance — Configuration
v1.1 — Critical settings now validated, JWT expiry extended to 7 days

CHANGES:
  - secret_key, database_url now have no default — app crashes if missing
    instead of running with empty JWT secret or no database
  - access_token_expire_minutes extended from 30 to 10080 (7 days)
    so daily check-in users don't get logged out every half hour
  - Added validator to catch missing critical env vars at startup
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    # Database — REQUIRED (no default — crashes if missing)
    database_url: str

    # JWT Auth — secret_key REQUIRED
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7 days (was 30 min — caused silent logouts)
    refresh_token_expire_days: int = 7

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro_monthly: str = ""
    stripe_price_pro_yearly: str = ""
    stripe_price_premium_monthly: str = ""
    stripe_price_premium_yearly: str = ""

    # Claude AI
    anthropic_api_key: str = ""

    # Email (Google SMTP via support@gracefinance.co)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    # App
    app_env: str = "development"
    frontend_url: str = "https://gracefinance.co"
    app_domain: str = ""

    @field_validator("secret_key")
    @classmethod
    def secret_key_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError(
                "SECRET_KEY env var is missing or empty. "
                "The app cannot start without a JWT signing key."
            )
        return v

    @field_validator("database_url")
    @classmethod
    def database_url_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError(
                "DATABASE_URL env var is missing or empty. "
                "The app cannot start without a database connection."
            )
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings():
    return Settings()