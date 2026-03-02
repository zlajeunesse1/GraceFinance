"""
Progression Router — Serves behavioral unlock tier status.

Endpoint:
  GET /progression/status → Full progression state for the current user

Drop this into: gracefinance/app/routers/progression.py
Then add to main.py:
  from app.routers.progression import router as progression_router
  app.include_router(progression_router)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.auth import get_current_user
from app.services.progression_service import get_user_progression


router = APIRouter(prefix="/progression", tags=["Progression"])


@router.get("/status")
def progression_status(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get the user's full progression status.

    Returns:
      - tiers: all tiers with unlock status + progress
      - next_unlock: the closest locked tier
      - unlocked_features: flat list of all unlocked feature keys
      - total_checkins, current_streak, data_points
    """
    streak = getattr(user, "current_streak", 0) or 0
    return get_user_progression(db, user.id, current_streak=streak)