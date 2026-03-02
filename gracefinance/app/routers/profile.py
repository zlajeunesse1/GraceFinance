"""
GraceFinance - Profile Router
GET  /api/profile  → fetch authenticated user's profile (auto-creates if missing)
PATCH /api/profile → update authenticated user's profile

Security:
- JWT required on all routes
- user_id derived from token ONLY via get_current_user()
- No user_id accepted from client in any form
- Pydantic forbids extra fields (no mass assignment)
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.profile import UserProfile
from app.models.models import User
from app.schemas.profile import ProfileRead, ProfileUpdate
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/profile", tags=["Profile"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_create_profile(db: Session, user: User) -> UserProfile:
    """
    Fetch existing profile or auto-create one on first access.
    Never called with a client-supplied user_id.
    """
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()

    if profile is None:
        profile = UserProfile(
            user_id=user.id,
            display_name=getattr(user, "full_name", None),
        )
        profile.profile_completion_score = profile.compute_completion_score()
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return profile


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=ProfileRead,
    status_code=status.HTTP_200_OK,
    summary="Get authenticated user's profile",
)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileRead:
    """
    Returns the profile for the currently authenticated user.
    Auto-creates profile on first access — no 404 on new users.
    """
    profile = _get_or_create_profile(db, current_user)
    return profile


@router.patch(
    "",
    response_model=ProfileRead,
    status_code=status.HTTP_200_OK,
    summary="Update authenticated user's profile",
)
def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileRead:
    """
    Partial update of the authenticated user's profile.
    Only updates fields explicitly provided in the payload.
    user_id is derived from JWT — never from client payload.
    """
    profile = _get_or_create_profile(db, current_user)

    # Apply only the fields the client sent (exclude_unset prevents overwriting
    # fields the client didn't include)
    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(profile, field, value)

    # Recompute completion score after update
    profile.profile_completion_score = profile.compute_completion_score()
    profile.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(profile)

    return profile