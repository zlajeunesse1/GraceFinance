"""
/me Router — User-scoped status endpoints.

Endpoints:
  GET /me/today → Current day check-in status, streak, latest scores

Auth: JWT-scoped identity only. No user_id in request body or path.

Place at: app/routers/me.py
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from datetime import date, datetime, timezone

from app.database import get_db
from app.models.user import User
from app.models.checkin import CheckInResponse, UserMetricSnapshot
from app.models.contribution_queue import IndexContributionEvent
from app.services.auth import get_current_user
from app.schemas.checkin_reward import TodayStatus


router = APIRouter(prefix="/me", tags=["Me"])


@router.get("/today", response_model=TodayStatus)
def get_today_status(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Returns the user's current-day status:
    - Whether they've checked in today
    - Current streak
    - Latest FCS + dimension scores
    - Contribution queue status
    """
    today = date.today()

    # -- Has checked in today? --
    today_checkins = (
        db.query(func.count(CheckInResponse.id))
        .filter(
            and_(
                CheckInResponse.user_id == user.id,
                func.date(CheckInResponse.check_in_date) == today,
            )
        )
        .scalar()
    )
    has_checked_in = (today_checkins or 0) > 0

    # -- Total check-in count --
    total_count = (
        db.query(func.count(CheckInResponse.id))
        .filter(CheckInResponse.user_id == user.id)
        .scalar() or 0
    )

    # -- Latest snapshot --
    latest_snap = (
        db.query(UserMetricSnapshot)
        .filter(UserMetricSnapshot.user_id == user.id)
        .order_by(desc(UserMetricSnapshot.computed_at))
        .first()
    )

    prev_snap = (
        db.query(UserMetricSnapshot)
        .filter(UserMetricSnapshot.user_id == user.id)
        .order_by(desc(UserMetricSnapshot.computed_at))
        .offset(1)
        .first()
    )

    # -- FCS trend --
    fcs_trend = None
    if latest_snap and prev_snap:
        diff = float(latest_snap.fcs_composite or 0) - float(prev_snap.fcs_composite or 0)
        if diff > 0.005:
            fcs_trend = "up"
        elif diff < -0.005:
            fcs_trend = "down"
        else:
            fcs_trend = "flat"

    # -- Dimension scores --
    dimension_scores = None
    weakest = None
    if latest_snap:
        dims = {
            "current_stability": float(latest_snap.current_stability or 0),
            "future_outlook": float(latest_snap.future_outlook or 0),
            "purchasing_power": float(latest_snap.purchasing_power or 0),
            "emergency_readiness": float(latest_snap.emergency_readiness or 0),
            "income_adequacy": float(latest_snap.income_adequacy or 0),
        }
        dimension_scores = dims
        weakest = min(dims, key=dims.get)

    # -- Contribution status --
    contrib = (
        db.query(IndexContributionEvent)
        .filter(
            and_(
                IndexContributionEvent.user_id == user.id,
                IndexContributionEvent.checkin_date == today,
            )
        )
        .first()
    )
    contribution_status = contrib.status if contrib else None

    # -- Last check-in timestamp --
    last_checkin = (
        db.query(func.max(CheckInResponse.check_in_date))
        .filter(CheckInResponse.user_id == user.id)
        .scalar()
    )

    return TodayStatus(
        has_checked_in_today=has_checked_in,
        streak=user.current_streak or 0,
        latest_fcs=float(latest_snap.fcs_composite) if latest_snap else None,
        fcs_trend=fcs_trend,
        dimension_scores=dimension_scores,
        weakest_dimension=weakest,
        checkin_count_total=total_count,
        contribution_status=contribution_status,
        last_checkin_at=last_checkin,
    )
