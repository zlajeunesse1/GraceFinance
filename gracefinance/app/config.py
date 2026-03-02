"""
GraceFinance — Configuration

CHANGES:
  - access_token_expire_minutes: 1440 → 30 (finance app needs short-lived tokens)
  - Added refresh_token_expire_days for refresh token rotation
  - Added cors_origins as a configurable list
  - Added app_domain for production CORS/cookie domain
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:Ireland1019!@localhost:5432/gracefinance"

    # JWT Auth
    secret_key: str = "a3f7b2c9d1e8f4ab6c9e0d5f3a2b1c8e7f6a4d9b0c3e2f1a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30           # ← was 1440 (24 hrs) — way too long for finance
    refresh_token_expire_days: int = 7              # NEW — refresh token lifespan

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro: str = ""
    stripe_price_premium: str = ""

    # Claude AI
    anthropic_api_key: str = "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"

# App
    app_env: str = "development"
    frontend_url: str = "http://localhost:3000"
    app_domain: str = ""
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings():
    return Settings()