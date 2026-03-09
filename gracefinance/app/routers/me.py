"""
/me Router — User-scoped status and metrics endpoints.

Endpoints:
  GET /me/today    → Current day check-in status
  GET /me/metrics  → UserMetricsSnapshot (canonical source of truth for all UI)

FIX #2 (CRITICAL): /me/today now uses Eastern Time boundaries, matching
    the check-in router exactly. Previously used UTC date, which disagreed
    with the ET-anchored check-in logic between 8-11 PM ET.
FIX #7 (HIGH): Scores of exactly 0.0 no longer treated as 'no data'.
    Changed falsy checks to explicit None checks.
FIX: checkins_this_week counts distinct check-in DAYS, not response rows.

Auth: JWT-scoped identity only. No user_id in request body or path.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc, cast, Date
from datetime import date, datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from app.database import get_db
from app.models import User
from app.models.checkin import CheckInResponse, UserMetricSnapshot
from app.services.auth import get_current_user
from app.schemas.metrics import UserMetricsSnapshot, DimensionScores

router = APIRouter(prefix="/me", tags=["Me"])

# ── Shared timezone anchor — must match the check-in router ──
EASTERN = ZoneInfo("America/New_York")


def _est_today_bounds():
    """
    Return (today_start, tomorrow_start) as UTC-aware datetimes,
    anchored to the Eastern Time calendar day.
    Identical to the check-in router's implementation.
    """
    now_et = datetime.now(EASTERN)
    today_start_et = now_et.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start_et = today_start_et + timedelta(days=1)
    return today_start_et.astimezone(timezone.utc), tomorrow_start_et.astimezone(timezone.utc)


def _build_snapshot(
    latest: UserMetricSnapshot | None,
    previous: UserMetricSnapshot | None,
    streak: int,
    checkins_this_week: int,
) -> UserMetricsSnapshot:
    now = datetime.now(timezone.utc)

    if latest is None:
        return UserMetricsSnapshot(
            fcs_total=None,
            dimensions=DimensionScores(),
            streak_count=None,
            checkins_this_week=None,
            last_checkin_at=None,
            delta_vs_last=None,
            updated_at=now,
        )

    fcs = float(latest.fcs_composite) if latest.fcs_composite is not None else None

    delta = None
    if fcs is not None and previous is not None and previous.fcs_composite is not None:
        delta = round(fcs - float(previous.fcs_composite), 2)

    # FIX #7: Explicit None check instead of falsy check.
    # A score of 0.0 is valid data, not "no data".
    def _dim(val):
        if val is None:
            return None
        return float(val)

    return UserMetricsSnapshot(
        fcs_total=fcs,  # FIX #7: removed `if fcs > 0` guard — 0.0 is valid
        dimensions=DimensionScores(
            stability=_dim(latest.current_stability),
            outlook=_dim(latest.future_outlook),
            purchasing_power=_dim(latest.purchasing_power),
            emergency_readiness=_dim(latest.emergency_readiness),
            financial_agency=_dim(latest.financial_agency),
        ),
        streak_count=streak if streak > 0 else None,
        checkins_this_week=checkins_this_week if checkins_this_week > 0 else None,
        last_checkin_at=latest.computed_at,
        delta_vs_last=delta,
        updated_at=latest.computed_at,
    )


@router.get("/metrics", response_model=UserMetricsSnapshot)
def get_metrics(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    latest = (
        db.query(UserMetricSnapshot)
        .filter(UserMetricSnapshot.user_id == user.id)
        .order_by(desc(UserMetricSnapshot.computed_at))
        .first()
    )
    previous = (
        db.query(UserMetricSnapshot)
        .filter(UserMetricSnapshot.user_id == user.id)
        .order_by(desc(UserMetricSnapshot.computed_at))
        .offset(1)
        .first()
    )

    week_start = datetime.now(timezone.utc) - timedelta(days=7)
    checkins_this_week = (
        db.query(func.count(func.distinct(cast(CheckInResponse.checkin_date, Date))))
        .filter(
            and_(
                CheckInResponse.user_id == user.id,
                CheckInResponse.checkin_date >= week_start,
            )
        )
        .scalar() or 0
    )

    streak = getattr(user, 'current_streak', 0) or 0

    return _build_snapshot(latest, previous, streak, checkins_this_week)


@router.get("/today")
def get_today_status(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    FIX #2 (CRITICAL): Now uses Eastern Time boundaries, identical to the
    check-in router. Previously used UTC date, which caused disagreement
    between 8-11 PM ET (when UTC is already the next day).
    """
    today_start, tomorrow_start = _est_today_bounds()

    today_count = (
        db.query(func.count(CheckInResponse.id))
        .filter(
            and_(
                CheckInResponse.user_id == user.id,
                CheckInResponse.checkin_date >= today_start,
                CheckInResponse.checkin_date < tomorrow_start,
            )
        )
        .scalar() or 0
    )

    last_checkin = (
        db.query(func.max(CheckInResponse.checkin_date))
        .filter(CheckInResponse.user_id == user.id)
        .scalar()
    )

    return {
        "has_checked_in_today": today_count > 0,
        "streak": getattr(user, 'current_streak', 0) or 0,
        "last_checkin_at": last_checkin,
    }