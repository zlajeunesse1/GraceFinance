"""
/index/summary Router — Published index with user contribution context.

Endpoints:
  GET /index/summary → Latest published index + user contribution status + changelog

This is the primary endpoint for the Index page. It combines:
  - Layer B data (the published DailyIndex)
  - User-specific contribution status
  - Aggregated changelog (non-identifiable)

Auth: JWT-scoped identity. No user_id in request body.

Place at: app/routers/index_summary.py
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from datetime import date, datetime, timezone, timedelta

from app.database import get_db
from app.models import User
from app.models.checkin import DailyIndex
from app.models.contribution_queue import IndexContributionEvent
from app.services.auth import get_current_user
from app.services.index_worker import get_cached_index
from app.schemas.index_summary import (
    IndexSummaryResponse,
    IndexCurrent,
    UserContribution,
    ChangelogEntry,
)


router = APIRouter(prefix="/index", tags=["Index"])


@router.get("/summary", response_model=IndexSummaryResponse)
def get_index_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Returns the published index snapshot with user-specific contribution
    context and a non-identifiable changelog of what changed.
    """
    today = date.today()
    now = datetime.now(timezone.utc)

    # -- Current published index (try cache first, then DB) --
    cache = get_cached_index()
    current = None
    last_updated = None

    if cache.get("gci") is not None:
        current = IndexCurrent(
            date=today,
            gci=cache["gci"],
            csi=cache.get("csi", 0),
            dpi=cache.get("dpi", 0),
            frs=cache.get("frs", 0),
            trend_direction=cache.get("trend_direction"),
            gci_slope_7d=None,
        )
        last_updated = cache.get("last_updated_at")
    else:
        # Fallback to DB
        latest = (
            db.query(DailyIndex)
            .order_by(desc(DailyIndex.date))
            .first()
        )
        if latest:
            current = IndexCurrent(
                date=latest.date,
                gci=float(latest.gci_close),
                csi=float(latest.csi_close),
                dpi=float(latest.dpi_close),
                frs=float(latest.frs_close),
                trend_direction=latest.trend_direction,
                gci_slope_7d=float(latest.gci_slope_7d) if latest.gci_slope_7d else None,
            )
            last_updated = (
                latest.updated_at.isoformat()
                if hasattr(latest, "updated_at") and latest.updated_at
                else None
            )

    # -- User's contribution status --
    user_contrib = (
        db.query(IndexContributionEvent)
        .filter(
            and_(
                IndexContributionEvent.user_id == user.id,
                IndexContributionEvent.checkin_date == today,
            )
        )
        .first()
    )

    if user_contrib:
        if user_contrib.status == "counted":
            contribution = UserContribution(
                status="counted",
                counted_in="today",
                expected_direction=_infer_direction(user_contrib),
            )
        else:
            contribution = UserContribution(
                status="queued",
                counted_in="next update",
                expected_direction=_infer_direction(user_contrib),
            )
    else:
        contribution = UserContribution(
            status="none",
            counted_in=None,
            expected_direction=None,
        )

    # -- Changelog: compare today vs yesterday (aggregated, non-identifiable) --
    changelog = _build_changelog(db, today)

    # -- Next update window --
    if now.hour < 18:
        next_window = "later today"
    else:
        next_window = "tomorrow morning"

    # -- Contributors count --
    contributors = (
        db.query(func.count(IndexContributionEvent.id))
        .filter(
            and_(
                IndexContributionEvent.checkin_date == today,
                IndexContributionEvent.status.in_(["counted", "pending", "processing"]),
            )
        )
        .scalar() or 0
    )

    return IndexSummaryResponse(
        current=current,
        last_updated_at=last_updated,
        next_update_window=next_window,
        user_contribution=contribution,
        changelog=changelog,
        active_contributors_today=contributors,
    )


def _infer_direction(contrib: IndexContributionEvent) -> str:
    """
    Infer the expected direction of the user's contribution based on their FCS.
    This is derived ONLY from their own score — no cross-user inference.
    """
    fcs = float(contrib.fcs_composite or 0)
    # Above 0.5 normalized → positive contribution to resilience
    if fcs > 0.55:
        return "up"
    elif fcs < 0.45:
        return "down"
    return "flat"


def _build_changelog(db: Session, today: date) -> list:
    """
    Compare today's published index vs yesterday's.
    Returns human-readable changelog entries.
    Only uses aggregated data — no user-level info.
    """
    yesterday = today - timedelta(days=1)

    today_idx = db.query(DailyIndex).filter(DailyIndex.date == today).first()
    yesterday_idx = db.query(DailyIndex).filter(DailyIndex.date == yesterday).first()

    if not today_idx or not yesterday_idx:
        return []

    entries = []
    metrics = [
        ("Consumer Confidence", "csi_close", True),   # True = lower is better (stress), so invert label
        ("Spending Pressure", "dpi_close", True),
        ("Financial Resilience", "frs_close", False),  # Higher is better
    ]

    for label, field, invert in metrics:
        today_val = float(getattr(today_idx, field, 0) or 0)
        yest_val = float(getattr(yesterday_idx, field, 0) or 0)
        delta = round(today_val - yest_val, 1)

        if abs(delta) < 0.05:
            continue

        # For stress metrics, a decrease is "good" (direction = down for stress)
        if delta > 0:
            direction = "up"
        else:
            direction = "down"

        entries.append(ChangelogEntry(
            metric=label,
            delta=abs(delta),
            direction=direction,
        ))

    return entries
