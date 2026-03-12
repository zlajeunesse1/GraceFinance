"""
GraceFinance — Preferences Router
PATCH  /api/profile/preferences → update user platform preferences
GET    /api/profile/preferences → fetch current preferences

Stores in UserProfile.preferences (JSONB column — already exists, no migration).
Handles: coaching_style, daily_reminder, reminder_time.

v1.1: Added "unhinged" to valid coaching styles.

Wire into main.py:
    from app.routers.preferences import router as preferences_router
    app.include_router(preferences_router)
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.database import get_db
from app.models.profile import UserProfile
from app.models.models import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/profile", tags=["Preferences"])


# ── Schema ────────────────────────────────────────────────────────────────────

VALID_COACHING_STYLES = {"encouraging", "direct", "balanced", "unhinged"}
VALID_REMINDER_TIMES = {
    "07:00", "08:00", "09:00", "10:00",
    "12:00", "13:00", "18:00", "20:00",
}


class PreferencesUpdate(BaseModel):
    coaching_style: Optional[str] = None
    daily_reminder: Optional[bool] = None
    reminder_time: Optional[str] = None

    class Config:
        extra = "forbid"

    @field_validator("coaching_style")
    @classmethod
    def validate_coaching_style(cls, v):
        if v is not None and v.lower() not in VALID_COACHING_STYLES:
            raise ValueError(f"coaching_style must be one of: {', '.join(VALID_COACHING_STYLES)}")
        return v.lower() if v else v

    @field_validator("reminder_time")
    @classmethod
    def validate_reminder_time(cls, v):
        if v is not None and v not in VALID_REMINDER_TIMES:
            raise ValueError(f"reminder_time must be one of: {', '.join(sorted(VALID_REMINDER_TIMES))}")
        return v


class PreferencesRead(BaseModel):
    coaching_style: str = "balanced"
    daily_reminder: bool = True
    reminder_time: str = "13:00"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_create_profile(db: Session, user: User) -> UserProfile:
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if profile is None:
        profile = UserProfile(
            user_id=user.id,
            display_name=getattr(user, "full_name", None),
        )
        if getattr(user, "onboarding_completed", False):
            profile.onboarding_completed = True
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def _get_preferences(profile: UserProfile) -> dict:
    """Extract preferences from JSONB column with defaults."""
    prefs = profile.preferences or {}
    return {
        "coaching_style": prefs.get("coaching_style", "balanced"),
        "daily_reminder": prefs.get("daily_reminder", True),
        "reminder_time": prefs.get("reminder_time", "13:00"),
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get(
    "/preferences",
    response_model=PreferencesRead,
    status_code=status.HTTP_200_OK,
    summary="Get user platform preferences",
)
def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PreferencesRead:
    profile = _get_or_create_profile(db, current_user)
    return PreferencesRead(**_get_preferences(profile))


@router.patch(
    "/preferences",
    response_model=PreferencesRead,
    status_code=status.HTTP_200_OK,
    summary="Update user platform preferences",
)
def update_preferences(
    payload: PreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PreferencesRead:
    """
    Partial update of platform preferences.
    Only updates fields explicitly provided in the payload.
    Merges into existing JSONB — never clobbers unrelated keys.
    """
    profile = _get_or_create_profile(db, current_user)

    # Get existing preferences (or empty dict)
    current_prefs = dict(profile.preferences or {})

    # Merge only the fields the client sent
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        current_prefs[key] = value

    # Write back to JSONB column
    profile.preferences = current_prefs
    profile.updated_at = datetime.now(timezone.utc)

    # Ensure SQLAlchemy detects the JSONB mutation
    flag_modified(profile, "preferences")

    db.commit()
    db.refresh(profile)

    return PreferencesRead(**_get_preferences(profile))