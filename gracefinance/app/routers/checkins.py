"""
Check-In Router — Frontend endpoints for the daily check-in flow.

Endpoints:
  GET  /checkin/questions       → Get today's questions (empty if already checked in today)
  POST /checkin/submit          → Submit answers — enforces ONE check-in per user per day
  GET  /checkin/metrics         → User's FCS metric snapshots over time
  POST /checkin/reset           → Dev tool — clear today's check-in (ADMIN ONLY)
  POST /checkin/migrate-v51     → Dev tool — add v5.1 audit columns

Data quality rule:
  One check-in per user per calendar day (UTC). Enforced at the server level on
  both endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, text
from datetime import datetime, timezone, timedelta, date

from app.database import get_db
from app.models import User
from app.models.checkin import CheckInResponse, UserMetricSnapshot
from app.services.auth import get_current_user
from app.services.question_bank import get_todays_questions
from app.services.checkin_service import (
    save_responses,
    compute_user_snapshot,
    get_user_metric_history,
)
from app.services.reward_engine import compute_reward
from app.services.gfci_engine import compute_daily_gfci
from app.schemas.checkin_schemas import (
    TodaysQuestionsOut,
    QuestionOut,
    CheckInSubmit,
    UserMetricOut,
    UserMetricHistory,
)
from app.routers.me import _build_snapshot


router = APIRouter(prefix="/checkin", tags=["Check-In"])

ADMIN_EMAILS = {"zaclajeunesse1@gmail.com"}


# ── Internal helpers ───────────────────────────────────────────────────────────

def _utc_today_bounds():
    """Return (today_start, tomorrow_start) as UTC-aware datetimes."""
    now_utc = datetime.now(timezone.utc)
    today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)
    return today_start, tomorrow_start


def _has_checked_in_today(db: Session, user_id) -> bool:
    """
    Returns True if the user has ANY check-in response recorded today (UTC).
    Uses explicit UTC boundaries — no timezone ambiguity.
    """
    today_start, tomorrow_start = _utc_today_bounds()

    count = (
        db.query(func.count(CheckInResponse.id))
        .filter(
            and_(
                CheckInResponse.user_id == user_id,
                CheckInResponse.checkin_date >= today_start,
                CheckInResponse.checkin_date < tomorrow_start,
            )
        )
        .scalar() or 0
    )
    return count > 0


# ──────────────────────────────────────────
#  GET TODAY'S QUESTIONS
# ──────────────────────────────────────────

@router.get("/questions", response_model=TodaysQuestionsOut)
def get_questions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Serve today's check-in questions.
    Daily: 5 rotating FCS questions (one per dimension).
    Sundays: also includes 5 weekly BSI questions.
    Returns empty lists + already_completed=True if user already checked in today.
    """
    today_utc = datetime.now(timezone.utc).date()

    if _has_checked_in_today(db, user.id):
        return TodaysQuestionsOut(
            date=str(today_utc),
            daily_questions=[],
            weekly_questions=[],
            is_weekly_day=False,
            already_completed=True,
        )

    result = get_todays_questions(user.id, today_utc)

    return TodaysQuestionsOut(
        date=result["date"],
        daily_questions=[
            QuestionOut(
                question_id=q.question_id,
                question_text=q.question_text,
                dimension=q.dimension,
                scale_type=q.scale_type,
                scale_max=q.scale_max,
                is_weekly=q.is_weekly,
                low_label=q.low_label,
                high_label=q.high_label,
            )
            for q in result["daily_questions"]
        ],
        weekly_questions=[
            QuestionOut(
                question_id=q.question_id,
                question_text=q.question_text,
                dimension=q.dimension,
                scale_type=q.scale_type,
                scale_max=q.scale_max,
                is_weekly=q.is_weekly,
                low_label=q.low_label,
                high_label=q.high_label,
            )
            for q in result["weekly_questions"]
        ],
        is_weekly_day=result["is_weekly_day"],
        already_completed=False,
    )


# ──────────────────────────────────────────
#  SUBMIT CHECK-IN ANSWERS (with Reward Loop + Real-Time GFCI)
# ──────────────────────────────────────────

@router.post("/submit")
def submit_checkin(
    payload: CheckInSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Accept user's check-in answers, save them, compute updated metrics,
    recompute the GFCI in real-time, and return the reward payload.

    DATA QUALITY: Returns HTTP 409 if user already submitted today.
    """
    if not payload.answers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No answers provided.",
        )

    # ── One check-in per day — hard server-side enforcement ──
    if _has_checked_in_today(db, user.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You've already completed today's check-in. Come back tomorrow.",
        )

    # 1. Capture previous snapshot BEFORE recomputing (needed for accurate delta)
    previous_snapshot = (
        db.query(UserMetricSnapshot)
        .filter(UserMetricSnapshot.user_id == user.id)
        .order_by(desc(UserMetricSnapshot.computed_at))
        .first()
    )

    # 2. Save all responses (commits internally)
    saved = save_responses(db, user.id, payload.answers)

    # 3. Recompute user's metric snapshot + update streak (commits internally)
    snapshot = compute_user_snapshot(db, user.id)

    # 4. Compute reward payload
    reward = compute_reward(
        db=db,
        user_id=user.id,
        new_snapshot=snapshot,
        previous_snapshot=previous_snapshot,
    )

    # 4b. Recompute GFCI with fresh data — real-time index update
    try:
        compute_daily_gfci(db)
    except Exception:
        pass  # Index failure should never block a user's check-in

    # 5. Final commit
    db.commit()

    # 6. Count check-ins this week for the canonical snapshot
    week_start = datetime.now(timezone.utc) - timedelta(days=7)
    checkins_this_week = (
        db.query(func.count(CheckInResponse.id))
        .filter(
            and_(
                CheckInResponse.user_id == user.id,
                CheckInResponse.checkin_date >= week_start,
            )
        )
        .scalar() or 0
    )

    # 7. Build canonical snapshot — powers all dashboard tiles
    metrics_snapshot = _build_snapshot(
        latest=snapshot,
        previous=previous_snapshot,
        streak=getattr(user, 'current_streak', 0) or 0,
        checkins_this_week=checkins_this_week,
    )

    return {
        "message": "Check-in saved successfully",
        "responses_saved": len(saved),
        "fcs_snapshot": float(snapshot.fcs_composite or 0),
        "metrics": metrics_snapshot,
        "reward": reward,
    }


# ──────────────────────────────────────────
#  DEV: RESET TODAY'S CHECK-IN (ADMIN ONLY)
# ──────────────────────────────────────────

@router.post("/reset")
def reset_today_checkin(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Dev tool — delete the current user's check-in responses from today (UTC).
    Allows re-testing the check-in flow without waiting for the next day.
    RESTRICTED: Only admin emails can access this endpoint.
    """
    if user.email not in ADMIN_EMAILS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )

    today_start, tomorrow_start = _utc_today_bounds()

    deleted = (
        db.query(CheckInResponse)
        .filter(
            and_(
                CheckInResponse.user_id == user.id,
                CheckInResponse.checkin_date >= today_start,
                CheckInResponse.checkin_date < tomorrow_start,
            )
        )
        .delete(synchronize_session="fetch")
    )

    db.commit()

    return {
        "message": f"Deleted {deleted} responses from today. Check-in unlocked.",
        "date": str(datetime.now(timezone.utc).date()),
    }





# ──────────────────────────────────────────
#  USER METRIC HISTORY
# ──────────────────────────────────────────

@router.get("/metrics", response_model=UserMetricHistory)
def get_metrics(
    days: int = 30,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get the user's FCS metric snapshots over time for charting."""
    snapshots = get_user_metric_history(db, user.id, days)

    return UserMetricHistory(
        user_id=user.id,
        snapshots=[
            UserMetricOut(
                computed_at=s.computed_at,
                current_stability=s.current_stability,
                future_outlook=s.future_outlook,
                purchasing_power=s.purchasing_power,
                emergency_readiness=s.emergency_readiness,
                financial_agency=s.financial_agency,
                fcs_composite=s.fcs_composite,
                bsi_score=s.bsi_score,
                checkin_count=s.checkin_count or 0,
            )
            for s in snapshots
        ],
    )