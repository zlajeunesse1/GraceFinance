"""
CheckIn Service — v2 (FCS Pillar Update)
═════════════════════════════════════════
CHANGES FROM v1:
  - FCS_WEIGHTS: debt_pressure → debt_pressure, financial_agency → financial_agency
  - Snapshot columns renamed to match
  - Everything else unchanged

REPLACES: app/services/checkin_service.py
"""

from datetime import datetime, timezone, timedelta, date
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.checkin import CheckInResponse, UserMetricSnapshot
from app.models import User
from app.services.question_bank import DAILY_QUESTIONS, WEEKLY_QUESTIONS


# FCS dimension weights (UPDATED — must sum to 1.0)
FCS_WEIGHTS = {
    "current_stability": 0.30,
    "future_outlook": 0.25,
    "purchasing_power": 0.20,
    "debt_pressure": 0.15,       # was debt_pressure
    "financial_agency": 0.10,    # was financial_agency
}


def save_responses(db: Session, user_id: int, answers: list) -> List[CheckInResponse]:
    """
    Save a batch of check-in answers. Normalizes each answer to 0.0–1.0.
    """
    saved = []
    now = datetime.now(timezone.utc)

    for answer in answers:
        qid = answer.question_id
        raw = answer.raw_value

        question = DAILY_QUESTIONS.get(qid) or WEEKLY_QUESTIONS.get(qid)
        if not question:
            continue

        raw = max(1, min(raw, question.scale_max))
        normalized = raw / question.scale_max

        response = CheckInResponse(
            user_id=user_id,
            question_id=qid,
            dimension=question.dimension,
            question_text=question.question_text,
            raw_value=raw,
            scale_max=question.scale_max,
            normalized_value=normalized,
            checkin_date=now,
            is_weekly=question.is_weekly,
        )
        db.add(response)
        saved.append(response)

    db.commit()
    for r in saved:
        db.refresh(r)

    return saved


def compute_user_snapshot(db: Session, user_id: int) -> UserMetricSnapshot:
    """
    Compute FCS sub-scores and composite from a user's recent check-in responses.
    Uses a 7-day rolling window. Also updates streak.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=7)

    responses = (
        db.query(CheckInResponse)
        .filter(
            and_(
                CheckInResponse.user_id == user_id,
                CheckInResponse.checkin_date >= window_start,
                CheckInResponse.is_weekly == False,  # noqa: E712
            )
        )
        .all()
    )

    # Update streak regardless of response count
    _update_streak(db, user_id, now)

    if not responses:
        snapshot = UserMetricSnapshot(
            user_id=user_id,
            computed_at=now,
            current_stability=None,
            future_outlook=None,
            purchasing_power=None,
            debt_pressure=None,          # was debt_pressure
            financial_agency=None,       # was financial_agency
            fcs_composite=None,
            bsi_score=None,
            checkin_count=0,
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot

    # Group by dimension, average normalized values
    dimension_scores = {}
    dimension_counts = {}

    for r in responses:
        dim = r.dimension
        if dim not in dimension_scores:
            dimension_scores[dim] = 0.0
            dimension_counts[dim] = 0
        dimension_scores[dim] += r.normalized_value
        dimension_counts[dim] += 1

    # Average each dimension — missing = None, not 0
    dim_averages = {}
    for dim in FCS_WEIGHTS.keys():
        if dim in dimension_scores and dimension_counts[dim] > 0:
            dim_averages[dim] = dimension_scores[dim] / dimension_counts[dim]
        else:
            dim_averages[dim] = None

    # FCS composite only from dimensions that have data
    weighted_sum = 0.0
    weight_used = 0.0
    for dim, weight in FCS_WEIGHTS.items():
        if dim_averages.get(dim) is not None:
            weighted_sum += dim_averages[dim] * weight
            weight_used += weight

    fcs_composite = round((weighted_sum / weight_used) * 100, 2) if weight_used > 0 else None

    bsi_score = _compute_bsi(db, user_id, window_start, now)

    snapshot = UserMetricSnapshot(
        user_id=user_id,
        computed_at=now,
        current_stability=dim_averages.get("current_stability"),
        future_outlook=dim_averages.get("future_outlook"),
        purchasing_power=dim_averages.get("purchasing_power"),
        debt_pressure=dim_averages.get("debt_pressure"),          # was debt_pressure
        financial_agency=dim_averages.get("financial_agency"),    # was financial_agency
        fcs_composite=fcs_composite,
        bsi_score=bsi_score,
        checkin_count=len(responses),
    )

    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def _update_streak(db: Session, user_id: int, now: datetime) -> None:
    """Increment or reset the user's check-in streak."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return

    current_streak = getattr(user, 'current_streak', 0) or 0
    last_checkin = getattr(user, 'last_checkin_date', None)

    today = now.date()

    if last_checkin is not None:
        last_date = last_checkin.date() if hasattr(last_checkin, 'date') else last_checkin
        if last_date == today:
            return  # already checked in today
        elif last_date == today - timedelta(days=1):
            user.current_streak = current_streak + 1
        else:
            user.current_streak = 1  # streak broken
    else:
        user.current_streak = 1  # first ever check-in

    user.last_checkin_date = now
    db.commit()


def _compute_bsi(db: Session, user_id: int, start: datetime, end: datetime) -> Optional[float]:
    """
    Compute BSI from weekly BX- questions.
    Scale: -100 (max stress) to +100 (max expansion).
    """
    weekly_responses = (
        db.query(CheckInResponse)
        .filter(
            and_(
                CheckInResponse.user_id == user_id,
                CheckInResponse.checkin_date >= start,
                CheckInResponse.checkin_date <= end,
                CheckInResponse.is_weekly == True,  # noqa: E712
            )
        )
        .all()
    )

    if not weekly_responses:
        return None

    # BSI: each response is 1-5 where 1=stress behavior, 5=stable
    # Normalize to [-100, +100]: (avg - 3) / 2 * 100
    total = sum(r.normalized_value for r in weekly_responses)
    avg = total / len(weekly_responses)

    bsi = (avg - 0.5) * 200  # 0.0→-100, 0.5→0, 1.0→+100
    return round(bsi, 2)


def get_user_metric_history(
    db: Session, user_id: int, days: int = 30
) -> list:
    """Get user's metric snapshots for the last N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return (
        db.query(UserMetricSnapshot)
        .filter(
            UserMetricSnapshot.user_id == user_id,
            UserMetricSnapshot.computed_at >= cutoff,
        )
        .order_by(UserMetricSnapshot.computed_at.asc())
        .all()
    )