"""
CheckIn Service — v3.0 (Institutional-Grade FCS Engine)
════════════════════════════════════════════════════════
CHANGES FROM v2.0:

  NORMALIZATION FIX (critical):
    Old: normalized = raw / scale_max
         → raw=1 on 1-10 scale = 0.10  (WRONG — should be floor)
    New: normalized = (raw - 1) / (scale_max - 1)
         → raw=1 = 0.0, raw=max = 1.0  (correct true floor/ceiling)

  EMA SMOOTHING (institutional-grade):
    FCS now uses Exponential Moving Average (α=0.20).
    One bad day cannot crater the score.
    Score reflects behavioral trend, not daily noise.
    raw_fcs stored alongside smoothed_fcs for full transparency.

  CONFIDENCE BAND:
    If user has answered < 3 of 5 dimensions, score is flagged
    as low-confidence and returned with a data_coverage % field.
    No score is returned if coverage < 40% (2/5 dimensions).

  BSI SHOCK DETECTION:
    If new raw FCS moves > 20 pts from previous smoothed FCS,
    a behavioral shift event is logged and BSI is intensified.

  INVERTED QUESTIONS:
    CS-2 and CS-3 (stress scales) are inverted so high raw = worse.

  DIMENSION ALIGNMENT:
    debt_pressure REMOVED.
    emergency_readiness ADDED at 15% weight.

REPLACES: app/services/checkin_service.py
"""

from datetime import datetime, timezone, timedelta, date
from typing import List, Optional, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.checkin import CheckInResponse, UserMetricSnapshot
from app.models import User
from app.services.question_bank import (
    DAILY_QUESTIONS,
    WEEKLY_QUESTIONS,
    INVERTED_QUESTION_IDS,
    FCS_WEIGHTS,
)


# ══════════════════════════════════════════
#  EMA CONFIG
# ══════════════════════════════════════════

EMA_ALPHA: float = 0.20
"""
Smoothing factor for Exponential Moving Average.
Lower = slower to react (more stable, more institutional).
Higher = faster to react (more volatile, more gamified).

α=0.20 means:
  - Today's raw score contributes 20% to new FCS
  - Previous smoothed FCS contributes 80%
  - A single bad day cannot drop score more than ~16 points
  - 5 consecutive bad days drops score ~67% of the raw gap
"""

BSI_SHOCK_THRESHOLD: float = 20.0
"""
If raw FCS swings more than this vs prior smoothed FCS,
a behavioral shift event fires. FCS still smooths normally —
shock is captured in BSI, not hidden from the data.
"""

MIN_DIMENSION_COVERAGE: float = 0.40
"""
Minimum answered weight (as fraction of total) required to
return a valid FCS. Below this, return None + low_confidence flag.
Example: if only current_stability (0.30) is answered → 30% < 40% → None.
"""


# ══════════════════════════════════════════
#  NORMALIZATION
# ══════════════════════════════════════════

def normalize_answer(raw: int, scale_max: int, inverted: bool = False) -> float:
    """
    Maps raw answer (1..scale_max) → 0.0..1.0.

    Formula: (raw - 1) / (scale_max - 1)
    This ensures:
      raw=1   → 0.0  (true floor — worst possible)
      raw=max → 1.0  (true ceiling — best possible)

    For inverted questions (high raw = worse outcome):
      result = 1.0 - normalized
    """
    if scale_max <= 1:
        return 1.0

    raw_clamped = max(1, min(raw, scale_max))
    normalized = (raw_clamped - 1) / (scale_max - 1)

    return round(1.0 - normalized if inverted else normalized, 4)


# ══════════════════════════════════════════
#  RESPONSE PERSISTENCE
# ══════════════════════════════════════════

def save_responses(db: Session, user_id, answers: list) -> List[CheckInResponse]:
    """
    Save a batch of check-in answers with correct normalization.
    Inverted questions (CS-2, CS-3) are flipped automatically.
    """
    saved = []
    now = datetime.now(timezone.utc)

    for answer in answers:
        qid = answer.question_id
        raw = answer.raw_value

        question = DAILY_QUESTIONS.get(qid) or WEEKLY_QUESTIONS.get(qid)
        if not question:
            continue

        is_inverted = qid in INVERTED_QUESTION_IDS
        normalized = normalize_answer(raw, question.scale_max, inverted=is_inverted)

        response = CheckInResponse(
            user_id=user_id,
            question_id=qid,
            dimension=question.dimension,
            raw_value=raw,
            scale_max=question.scale_max,
            normalized_value=normalized,
            checkin_date=now,
        )
        db.add(response)
        saved.append(response)

    db.commit()
    for r in saved:
        db.refresh(r)

    return saved


# ══════════════════════════════════════════
#  SNAPSHOT COMPUTATION
# ══════════════════════════════════════════

def compute_user_snapshot(db: Session, user_id) -> UserMetricSnapshot:
    """
    Core FCS computation pipeline:

    Step 1 — Aggregate recent responses into per-dimension averages
    Step 2 — Apply confidence gate (skip if < MIN_DIMENSION_COVERAGE)
    Step 3 — Compute raw FCS composite (0–100)
    Step 4 — Apply EMA smoothing against previous snapshot
    Step 5 — Detect BSI shock if swing > BSI_SHOCK_THRESHOLD
    Step 6 — Compute BSI from weekly behavioral questions
    Step 7 — Persist and return snapshot
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=7)

    responses = (
        db.query(CheckInResponse)
        .filter(
            and_(
                CheckInResponse.user_id == user_id,
                CheckInResponse.checkin_date >= window_start,
                # Exclude conversation theme records
                CheckInResponse.dimension != "conversation_theme",
            )
        )
        .all()
    )

    _update_streak(db, user_id, now)

    if not responses:
        snapshot = UserMetricSnapshot(
            user_id=user_id,
            computed_at=now,
            current_stability=None,
            future_outlook=None,
            purchasing_power=None,
            emergency_readiness=None,
            financial_agency=None,
            fcs_raw=None,
            fcs_composite=None,
            fcs_confidence=0.0,
            bsi_score=None,
            bsi_shock=False,
            checkin_count=0,
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot

    # ── Step 1: Per-dimension averages ──────────────────────────────────────
    dim_scores: Dict[str, List[float]] = {dim: [] for dim in FCS_WEIGHTS}

    for r in responses:
        dim = r.dimension
        if dim in dim_scores and r.normalized_value is not None:
            dim_scores[dim].append(r.normalized_value)

    dim_averages: Dict[str, Optional[float]] = {}
    for dim in FCS_WEIGHTS:
        vals = dim_scores[dim]
        dim_averages[dim] = (sum(vals) / len(vals)) if vals else None

    # ── Step 2: Confidence gate ──────────────────────────────────────────────
    answered_weight = sum(
        weight for dim, weight in FCS_WEIGHTS.items()
        if dim_averages.get(dim) is not None
    )
    data_coverage = round(answered_weight, 4)  # 0.0–1.0

    # ── Step 3: Raw FCS composite (0–100) ────────────────────────────────────
    fcs_raw: Optional[float] = None

    if data_coverage >= MIN_DIMENSION_COVERAGE:
        weighted_sum = sum(
            dim_averages[dim] * weight
            for dim, weight in FCS_WEIGHTS.items()
            if dim_averages.get(dim) is not None
        )
        # Normalize to answered weight so partial data doesn't deflate score
        fcs_raw = round((weighted_sum / answered_weight) * 100, 2)

    # ── Step 4: EMA smoothing ─────────────────────────────────────────────────
    fcs_composite: Optional[float] = None
    bsi_shock = False

    if fcs_raw is not None:
        previous_snapshot = _get_latest_snapshot(db, user_id)
        prev_fcs = (
            previous_snapshot.fcs_composite
            if previous_snapshot and previous_snapshot.fcs_composite is not None
            else None
        )

        if prev_fcs is not None:
            # ── Step 5: BSI shock detection ───────────────────────────────────
            swing = abs(fcs_raw - prev_fcs)
            if swing >= BSI_SHOCK_THRESHOLD:
                bsi_shock = True

            # Apply EMA
            fcs_composite = round(
                (EMA_ALPHA * fcs_raw) + ((1 - EMA_ALPHA) * prev_fcs), 2
            )
        else:
            # First ever score — no previous to smooth against
            fcs_composite = fcs_raw

    # ── Step 6: BSI from weekly behavioral questions ─────────────────────────
    bsi_score = _compute_bsi(db, user_id, window_start, now)

    # Amplify BSI if shock detected
    if bsi_shock and bsi_score is not None:
        bsi_score = round(bsi_score * 1.25, 2)
    elif bsi_shock:
        bsi_score = -25.0  # default negative signal when no BSI data

    # ── Step 7: Persist ───────────────────────────────────────────────────────
    snapshot = UserMetricSnapshot(
        user_id=user_id,
        computed_at=now,
        current_stability=dim_averages.get("current_stability"),
        future_outlook=dim_averages.get("future_outlook"),
        purchasing_power=dim_averages.get("purchasing_power"),
        emergency_readiness=dim_averages.get("emergency_readiness"),
        financial_agency=dim_averages.get("financial_agency"),
        fcs_raw=fcs_raw,
        fcs_composite=fcs_composite,
        fcs_confidence=round(data_coverage * 100, 1),  # store as 0–100%
        bsi_score=bsi_score,
        bsi_shock=bsi_shock,
        checkin_count=len(responses),
    )

    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


# ══════════════════════════════════════════
#  BSI COMPUTATION
# ══════════════════════════════════════════

def _compute_bsi(
    db: Session, user_id, start: datetime, end: datetime
) -> Optional[float]:
    """
    Behavioral Shift Indicator from weekly BX- questions.

    Scale: -100 (maximum contraction / stress) to +100 (maximum expansion).
    Midpoint (0) = neutral, no behavioral shift.

    Logic:
      - Each BX question normalized 0.0–1.0 (high = stable/positive)
      - Average → center around 0.5 → scale to -100..+100
    """
    weekly_responses = (
        db.query(CheckInResponse)
        .filter(
            and_(
                CheckInResponse.user_id == user_id,
                CheckInResponse.checkin_date >= start,
                CheckInResponse.checkin_date <= end,
                CheckInResponse.question_id.like("BX-%"),
            )
        )
        .all()
    )

    if not weekly_responses:
        return None

    avg = sum(r.normalized_value for r in weekly_responses) / len(weekly_responses)
    bsi = (avg - 0.5) * 200  # maps 0→-100, 0.5→0, 1.0→+100
    return round(bsi, 2)


# ══════════════════════════════════════════
#  STREAK MANAGEMENT
# ══════════════════════════════════════════

def _update_streak(db: Session, user_id, now: datetime) -> None:
    """Increment or reset the user's check-in streak."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return

    current_streak = getattr(user, "current_streak", 0) or 0
    last_checkin = getattr(user, "last_checkin_date", None)
    today = now.date()

    if last_checkin is not None:
        last_date = last_checkin.date() if hasattr(last_checkin, "date") else last_checkin
        if last_date == today:
            return  # Already checked in today
        elif last_date == today - timedelta(days=1):
            user.current_streak = current_streak + 1
        else:
            user.current_streak = 1  # Streak broken
    else:
        user.current_streak = 1  # First ever check-in

    user.last_checkin_date = now
    db.commit()


# ══════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════

def _get_latest_snapshot(db: Session, user_id) -> Optional[UserMetricSnapshot]:
    """Fetch most recent snapshot with a real FCS score."""
    return (
        db.query(UserMetricSnapshot)
        .filter(
            UserMetricSnapshot.user_id == user_id,
            UserMetricSnapshot.fcs_composite.isnot(None),
        )
        .order_by(UserMetricSnapshot.computed_at.desc())
        .first()
    )


def get_user_metric_history(
    db: Session, user_id, days: int = 30
) -> List[UserMetricSnapshot]:
    """Get user's metric snapshots for the last N days, oldest first."""
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


def get_fcs_label(score: Optional[float]) -> str:
    """Human-readable label for FCS score range."""
    if score is None:
        return "No Data"
    if score >= 80:
        return "Thriving"
    if score >= 65:
        return "Strong"
    if score >= 50:
        return "Building"
    if score >= 35:
        return "Growing"
    if score >= 20:
        return "Struggling"
    return "Critical"