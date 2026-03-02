"""
GraceFinance - Profile Schemas
Read + Update schemas. No user_id ever accepted from client.
Pydantic v2 compatible.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.profile import RiskStyle, ThemeOption


# ── Base (shared field definitions) ──────────────────────────────────────────

class ProfileBase(BaseModel):
    display_name: str | None = Field(
        default=None,
        max_length=64,
        description="Public display name on Grace platform",
    )
    timezone: str = Field(
        default="America/New_York",
        max_length=64,
        description="IANA timezone string",
    )
    currency: str = Field(
        default="USD",
        max_length=8,
        description="ISO 4217 currency code",
    )
    theme: ThemeOption = Field(
        default=ThemeOption.WEALTH,
        description="App theme preference",
    )
    risk_style: RiskStyle = Field(
        default=RiskStyle.BALANCED,
        description="User's self-identified financial risk style",
    )
    onboarding_completed: bool = Field(default=False)

    @field_validator("currency")
    @classmethod
    def currency_uppercase(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("display_name")
    @classmethod
    def display_name_clean(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
        return v


# ── Update Schema (PATCH payload from client) ────────────────────────────────

class ProfileUpdate(ProfileBase):
    """
    Accepted from client on PUT/PATCH /profile.
    All fields optional — partial updates supported.
    user_id is NEVER accepted here.
    """

    display_name: str | None = Field(default=None, max_length=64)
    timezone: str | None = Field(default=None, max_length=64)
    currency: str | None = Field(default=None, max_length=8)
    theme: ThemeOption | None = None
    risk_style: RiskStyle | None = None
    onboarding_completed: bool | None = None

    model_config = ConfigDict(extra="forbid")  # Reject any unknown fields


# ── Read Schema (response to client) ─────────────────────────────────────────

class ProfileRead(ProfileBase):
    """
    Returned to client on GET /profile.
    Includes computed/audit fields. Never includes user_id.
    """

    id: UUID
    profile_completion_score: int
    subscription_tier: str | None
    preferences: dict[str, Any] | None
    feature_flags: dict[str, Any] | None
    last_active: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Internal schema (used by services, never exposed) ────────────────────────

class ProfileCreate(ProfileBase):
    """
    Used internally to seed a new profile on first access.
    Never exposed to the API layer directly.
    """
    pass