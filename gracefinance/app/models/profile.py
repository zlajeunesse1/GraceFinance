"""
GraceFinance - UserProfile Model
Separate from auth credentials. 1:1 with User.
Designed for scale: JSONB preferences, audit logging, institutional flags ready.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class ThemeOption(str, PyEnum):
    DARK = "dark"
    WEALTH = "wealth"
    AGGRESSIVE = "aggressive"
    CALM = "calm"


class RiskStyle(str, PyEnum):
    CALM = "calm"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class UserProfile(Base):
    __tablename__ = "user_profiles"

    # ── Primary Key ──────────────────────────────────────────────────────────
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    # ── Foreign Key (never exposed to client) ────────────────────────────────
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Core Profile ─────────────────────────────────────────────────────────
    display_name = Column(String(64), nullable=True)
    timezone = Column(String(64), nullable=False, default="America/New_York")
    currency = Column(String(8), nullable=False, default="USD")

    # ── Grace Platform Settings ───────────────────────────────────────────────
    onboarding_completed = Column(Boolean, nullable=False, default=False)
    theme = Column(
        Enum(ThemeOption, name="theme_option"),
        nullable=False,
        default=ThemeOption.WEALTH,
    )
    risk_style = Column(
        Enum(RiskStyle, name="risk_style"),
        nullable=False,
        default=RiskStyle.BALANCED,
    )

    # ── Scalability Fields (future-ready) ────────────────────────────────────
    # Add Grace Intelligence institutional flags here when needed
    preferences = Column(JSONB, nullable=True, default=dict)
    # e.g. {"notifications": true, "weekly_digest": false}

    subscription_tier = Column(String(32), nullable=True)
    # e.g. "free", "premium", "institutional"

    feature_flags = Column(JSONB, nullable=True, default=dict)
    # e.g. {"grace_intelligence": false, "b2b_api": false}

    profile_completion_score = Column(Integer, nullable=False, default=0)
    # 0-100, computed on save

    # ── Audit / Activity ─────────────────────────────────────────────────────
    last_active = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Constraints ──────────────────────────────────────────────────────────
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_profiles_user_id"),)

    # ── Relationship ─────────────────────────────────────────────────────────
    user = relationship("User", back_populates="profile")

    def __repr__(self) -> str:
        return f"<UserProfile user_id={self.user_id} theme={self.theme}>"

    def compute_completion_score(self) -> int:
        """
        Returns 0-100 score based on filled fields.
        Extend this as profile fields grow.
        """
        fields = {
            "display_name": self.display_name,
            "timezone": self.timezone,
            "currency": self.currency,
            "onboarding_completed": self.onboarding_completed,
            "risk_style": self.risk_style,
            "theme": self.theme,
        }
        filled = sum(1 for v in fields.values() if v is not None and v is not False)
        return round((filled / len(fields)) * 100)