"""
GraceFinance - Profile Router
GET    /api/profile  → fetch authenticated user's profile (auto-creates if missing)
PATCH  /api/profile  → update authenticated user's profile
DELETE /api/profile/account → permanently delete account + all data

Security:
- JWT required on all routes
- user_id derived from token ONLY via get_current_user()
- No user_id accepted from client in any form
- Pydantic forbids extra fields (no mass assignment)

v6: Added financial snapshot sync (income, expenses, debt, goals, mission).
    Profile fields sync back to User model so legacy reads still work.
    Added DELETE /account for permanent account deletion.
    Onboarding data seeds profile on first access.

v7: Hardened delete_account with explicit child table cleanup.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.profile import UserProfile
from app.models.models import User, Debt, Transaction, Bill
from app.models.checkin import CheckInResponse, UserMetricSnapshot
from app.schemas.profile import ProfileRead, ProfileUpdate
from app.services.auth import get_current_user

logger = logging.getLogger("gracefinance")

router = APIRouter(prefix="/api/profile", tags=["Profile"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_create_profile(db: Session, user: User) -> UserProfile:
    """
    Fetch existing profile or auto-create one on first access.
    Seeds from onboarding data on the User model if available.
    Never called with a client-supplied user_id.
    """
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()

    if profile is None:
        profile = UserProfile(
            user_id=user.id,
            display_name=getattr(user, "full_name", None),
        )

        # ── Seed financial snapshot from onboarding data ─────────────────
        if getattr(user, "monthly_income", None):
            profile.income = user.monthly_income
        if getattr(user, "monthly_expenses", None):
            profile.expenses = user.monthly_expenses
        if getattr(user, "financial_goal", None):
            profile.mission = user.financial_goal
        if getattr(user, "onboarding_goals", None):
            profile.goals = user.onboarding_goals
        if getattr(user, "onboarding_completed", False):
            profile.onboarding_completed = True

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
    Seeds from onboarding data if profile is new.
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

    v6: Financial fields (income, expenses, debt, goals, mission)
    sync back to the User model so legacy reads (dashboard, grace_service
    fallback) still work.
    """
    profile = _get_or_create_profile(db, current_user)

    # Apply only the fields the client sent (exclude_unset prevents overwriting
    # fields the client didn't include)
    update_data = payload.model_dump(exclude_unset=True)

    # ── Validate risk_style if provided ──────────────────────────────────
    if "risk_style" in update_data:
        valid_risk = {"calm", "balanced", "aggressive"}
        if update_data["risk_style"] and update_data["risk_style"].lower() not in valid_risk:
            del update_data["risk_style"]
        elif update_data["risk_style"]:
            update_data["risk_style"] = update_data["risk_style"].lower()

    # ── Validate goals if provided ───────────────────────────────────────
    if "goals" in update_data and update_data["goals"] is not None:
        valid_goals = {"save", "debt", "track", "budget", "wealth", "habits"}
        update_data["goals"] = [g for g in update_data["goals"] if g in valid_goals]

    for field, value in update_data.items():
        setattr(profile, field, value)

    # ── Sync financial fields back to User model ─────────────────────────
    # So legacy reads (dashboard, grace_service fallback) still work.
    if "income" in update_data:
        current_user.monthly_income = update_data["income"]
    if "expenses" in update_data:
        current_user.monthly_expenses = update_data["expenses"]
    if "goals" in update_data:
        current_user.onboarding_goals = update_data["goals"]
    if "mission" in update_data:
        current_user.financial_goal = update_data["mission"]

    # Recompute completion score after update
    profile.profile_completion_score = profile.compute_completion_score()
    profile.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(profile)

    return profile


# ── DELETE /api/profile/account ──────────────────────────────────────────────

@router.delete(
    "/account",
    status_code=status.HTTP_200_OK,
    summary="Permanently delete account and all data",
)
def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Permanently delete the user's account and ALL associated data.
    Explicit child-table cleanup + CASCADE as backup.
    This is irreversible.
    """
    try:
        user_id = current_user.id

        # ── Explicit child cleanup (safety net for missing DB-level CASCADE) ──
        db.query(CheckInResponse).filter(CheckInResponse.user_id == user_id).delete(synchronize_session=False)
        db.query(UserMetricSnapshot).filter(UserMetricSnapshot.user_id == user_id).delete(synchronize_session=False)
        db.query(Debt).filter(Debt.user_id == user_id).delete(synchronize_session=False)
        db.query(Transaction).filter(Transaction.user_id == user_id).delete(synchronize_session=False)
        db.query(Bill).filter(Bill.user_id == user_id).delete(synchronize_session=False)

        # Profile (1:1)
        db.query(UserProfile).filter(UserProfile.user_id == user_id).delete(synchronize_session=False)

        # ── Delete the user row itself ──
        db.delete(current_user)
        db.commit()

        return {
            "status": "deleted",
            "message": "Your account and all data have been permanently deleted.",
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Account deletion failed for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to delete account. Please try again or contact support.",
        )