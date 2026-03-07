"""
CheckIn Service — v4.0 (Institutional-Grade Behavioral Engine)
══════════════════════════════════════════════════════════════════
ARCHITECTURE CHANGES FROM v3.0:

  MULTI-WINDOW BLENDING:
    v3: 7-day window only
    v4: 30/60/90-day blended windows
        30d × 0.20 (recent signal)
        60d × 0.35 (trend signal)
        90d × 0.45 (baseline signal)
    Long-term behavior dominates. One bad week cannot crater the score.

  SLOWER EMA:
    v3: α = 0.20
    v4: α = 0.15
    Score reacts more slowly. Institutional-grade stability.

  MOVEMENT CAPS:
    v3: No caps
    v4: ±3 points max FCS movement per day
        ±2 points max per pillar per day
    Prevents single check-in from creating volatility.

  OUTLIER DAMPENING:
    If a single normalized response deviates > 2σ from the user's
    rolling mean for that dimension, it is pulled toward the mean.
    Extreme single responses are dampened, not discarded.

  MINIMUM DATA THRESHOLDS:
    Score requires ≥ 3 of 5 pillars with data AND ≥ 5 check-ins
    in the 30-day window. Below threshold: score is "provisional"
    (still computed but flagged, confidence < 50%).

  CONSISTENCY WEIGHTING:
    Users who check in regularly get higher-confidence scores.
    Sporadic users get lower confidence, which dampens their
    contribution to the GFCI population index.

INTERFACE: Same as v3 — drop-in replacement.
  save_responses(db, user_id, answers) → List[CheckInResponse]
  compute_user_snapshot(db, user_id)   → UserMetricSnapshot
  get_user_metric_history(db, user_id) → List[UserMetricSnapshot]
"""

from datetime import datetime, timezone, timedelta, date
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import math

from app.models.checkin import CheckInResponse, UserMetricSnapshot
from app.models import User
from app.services.question_bank import (
    DAILY_QUESTIONS,
    WEEKLY_QUESTIONS,
    INVERTED_QUESTION_IDS,
    FCS_WEIGHTS,
)


# ══════════════════════════════════════════
#  INSTITUTIONAL CONFIG
# ══════════════════════════════════════════

# EMA smoothing factor — lower = more stable
EMA_ALPHA: float = 0.15

# Multi-window blending weights (must sum to 1.0)
WINDOW_WEIGHTS: Dict[int, float] = {
    30: 0.20,   # recent behavioral signal
    60: 0.35,   # trend signal
    90: 0.45,   # baseline stability signal
}

# Movement caps — maximum score change per computation
MAX_FCS_MOVEMENT: float = 3.0       # ±3 points max per day
MAX_PILLAR_MOVEMENT: float = 0.02   # ±0.02 on 0-1 scale (= ±2 pts on 0-100)

# Minimum data requirements
MIN_CHECKINS_FOR_CONFIDENT: int = 5     # in 30-day window
MIN_PILLARS_FOR_SCORE: int = 3          # of 5 pillars must have data
CONFIDENT_THRESHOLD: float = 50.0       # fcs_confidence >= this = "confident"

# Outlier dampening
OUTLIER_SIGMA_THRESHOLD: float = 2.0    # responses beyond 2σ get dampened
OUTLIER_DAMPEN_FACTOR: float = 0.5      # pull 50% toward mean

# BSI shock detection
BSI_SHOCK_THRESHOLD: float = 20.0


# ══════════════════════════════════════════
#  NORMALIZATION
# ══════════════════════════════════════════

def normalize_answer(raw: int, scale_max: int, inverted: bool = False) -> float:
    """
    Maps raw answer (1..scale_max) → 0.0..1.0.
    Formula: (raw - 1) / (scale_max - 1)
    Inverted questions: result = 1.0 - normalized
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
    """Save check-in answers with correct normalization."""
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
#  MULTI-WINDOW DATA GATHERING
# ══════════════════════════════════════════

def _gather_windowed_responses(
    db: Session, user_id, now: datetime
) -> Dict[int, List[CheckInResponse]]:
    """
    Gather check-in responses for each rolling window (30/60/90 days).
    Returns dict keyed by window size in days.
    """
    windows = {}
    for days in WINDOW_WEIGHTS.keys():
        start = now - timedelta(days=days)
        responses = (
            db.query(CheckInResponse)
            .filter(
                and_(
                    CheckInResponse.user_id == user_id,
                    CheckInResponse.checkin_date >= start,
                    CheckInResponse.dimension != "conversation_theme",
                )
            )
            .all()
        )
        windows[days] = responses
    return windows


def _compute_dimension_averages(
    responses: List[CheckInResponse],
) -> Dict[str, Optional[float]]:
    """Compute per-dimension averages from a set of responses."""
    dim_scores: Dict[str, List[float]] = {dim: [] for dim in FCS_WEIGHTS}

    for r in responses:
        dim = r.dimension
        if dim in dim_scores and r.normalized_value is not None:
            dim_scores[dim].append(r.normalized_value)

    averages: Dict[str, Optional[float]] = {}
    for dim in FCS_WEIGHTS:
        vals = dim_scores[dim]
        averages[dim] = (sum(vals) / len(vals)) if vals else None
    return averages


# ══════════════════════════════════════════
#  OUTLIER DAMPENING
# ══════════════════════════════════════════

def _dampen_outliers(
    responses: List[CheckInResponse],
) -> List[CheckInResponse]:
    """
    Identify responses that deviate > 2σ from the user's per-dimension
    rolling mean and pull them toward the mean.

    Does NOT modify the database — works on in-memory copies.
    """
    from copy import copy

    # Group by dimension
    dim_vals: Dict[str, List[float]] = {}
    for r in responses:
        if r.dimension not in dim_vals:
            dim_vals[r.dimension] = []
        if r.normalized_value is not None:
            dim_vals[r.dimension].append(r.normalized_value)

    # Compute mean and std per dimension
    dim_stats: Dict[str, tuple] = {}
    for dim, vals in dim_vals.items():
        if len(vals) >= 3:  # need at least 3 data points for meaningful σ
            mean = sum(vals) / len(vals)
            variance = sum((v - mean) ** 2 for v in vals) / len(vals)
            std = math.sqrt(variance) if variance > 0 else 0.0
            dim_stats[dim] = (mean, std)

    # Dampen outliers
    dampened = []
    for r in responses:
        if r.dimension in dim_stats and r.normalized_value is not None:
            mean, std = dim_stats[r.dimension]
            if std > 0:
                deviation = abs(r.normalized_value - mean)
                if deviation > OUTLIER_SIGMA_THRESHOLD * std:
                    # Pull toward mean
                    r_copy = copy(r)
                    r_copy.normalized_value = round(
                        r.normalized_value + OUTLIER_DAMPEN_FACTOR * (mean - r.normalized_value),
                        4,
                    )
                    dampened.append(r_copy)
                    continue
        dampened.append(r)

    return dampened


# ══════════════════════════════════════════
#  MOVEMENT CAPPING
# ══════════════════════════════════════════

def _cap_pillar_movement(
    new_val: Optional[float],
    old_val: Optional[float],
) -> Optional[float]:
    """Cap per-pillar movement to ±MAX_PILLAR_MOVEMENT per computation."""
    if new_val is None:
        return new_val
    if old_val is None:
        return new_val

    delta = new_val - old_val
    if abs(delta) > MAX_PILLAR_MOVEMENT:
        capped = old_val + (MAX_PILLAR_MOVEMENT if delta > 0 else -MAX_PILLAR_MOVEMENT)
        return round(capped, 4)
    return new_val


def _cap_fcs_movement(
    new_fcs: Optional[float],
    old_fcs: Optional[float],
) -> Optional[float]:
    """Cap FCS composite movement to ±MAX_FCS_MOVEMENT per computation."""
    if new_fcs is None:
        return new_fcs
    if old_fcs is None:
        return new_fcs

    delta = new_fcs - old_fcs
    if abs(delta) > MAX_FCS_MOVEMENT:
        capped = old_fcs + (MAX_FCS_MOVEMENT if delta > 0 else -MAX_FCS_MOVEMENT)
        return round(capped, 2)
    return new_fcs


# ══════════════════════════════════════════
#  SNAPSHOT COMPUTATION — INSTITUTIONAL ENGINE
# ══════════════════════════════════════════

def compute_user_snapshot(db: Session, user_id) -> UserMetricSnapshot:
    """
    Institutional-grade FCS computation pipeline:

    Step 1 — Gather responses across 30/60/90-day windows
    Step 2 — Dampen outliers per dimension
    Step 3 — Compute per-dimension averages per window
    Step 4 — Blend windows (30d×0.20 + 60d×0.35 + 90d×0.45)
    Step 5 — Cap pillar movement vs previous snapshot
    Step 6 — Compute raw FCS composite (0–100)
    Step 7 — Apply EMA smoothing (α=0.15)
    Step 8 — Cap FCS movement (±3 points max)
    Step 9 — Compute confidence score
    Step 10 — Compute BSI from weekly behavioral questions
    Step 11 — Update streak
    Step 12 — Persist and return snapshot
    """
    now = datetime.now(timezone.utc)

    # Update streak first
    _update_streak(db, user_id, now)

    # Get previous snapshot for movement capping and EMA
    previous_snapshot = _get_latest_snapshot(db, user_id)

    # ── Step 1: Gather multi-window responses ─────────────────────────────
    windowed = _gather_windowed_responses(db, user_id, now)

    # Check if we have any data at all
    all_responses = windowed.get(90, [])
    if not all_responses:
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

    # ── Step 2: Dampen outliers ───────────────────────────────────────────
    dampened_windows = {}
    for days, responses in windowed.items():
        dampened_windows[days] = _dampen_outliers(responses)

    # ── Step 3: Per-dimension averages per window ─────────────────────────
    window_averages: Dict[int, Dict[str, Optional[float]]] = {}
    for days, responses in dampened_windows.items():
        window_averages[days] = _compute_dimension_averages(responses)

    # ── Step 4: Blend windows ─────────────────────────────────────────────
    blended: Dict[str, Optional[float]] = {}
    for dim in FCS_WEIGHTS:
        weighted_sum = 0.0
        total_weight = 0.0

        for days, weight in WINDOW_WEIGHTS.items():
            val = window_averages[days].get(dim)
            if val is not None:
                weighted_sum += val * weight
                total_weight += weight

        if total_weight > 0:
            blended[dim] = round(weighted_sum / total_weight, 4)
        else:
            blended[dim] = None

    # ── Step 5: Cap pillar movement ───────────────────────────────────────
    if previous_snapshot:
        prev_dims = {
            "current_stability": previous_snapshot.current_stability,
            "future_outlook": previous_snapshot.future_outlook,
            "purchasing_power": previous_snapshot.purchasing_power,
            "emergency_readiness": previous_snapshot.emergency_readiness,
            "financial_agency": previous_snapshot.financial_agency,
        }
        for dim in FCS_WEIGHTS:
            blended[dim] = _cap_pillar_movement(blended[dim], prev_dims.get(dim))

    # ── Step 6: Raw FCS composite (0–100) ─────────────────────────────────
    answered_weight = sum(
        w for dim, w in FCS_WEIGHTS.items() if blended.get(dim) is not None
    )
    pillars_with_data = sum(
        1 for dim in FCS_WEIGHTS if blended.get(dim) is not None
    )

    fcs_raw: Optional[float] = None
    if pillars_with_data >= MIN_PILLARS_FOR_SCORE and answered_weight > 0:
        weighted_sum = sum(
            blended[dim] * weight
            for dim, weight in FCS_WEIGHTS.items()
            if blended.get(dim) is not None
        )
        fcs_raw = round((weighted_sum / answered_weight) * 100, 2)

    # ── Step 7: EMA smoothing ─────────────────────────────────────────────
    fcs_composite: Optional[float] = None
    bsi_shock = False

    if fcs_raw is not None:
        prev_fcs = (
            previous_snapshot.fcs_composite
            if previous_snapshot and previous_snapshot.fcs_composite is not None
            else None
        )

        if prev_fcs is not None:
            # BSI shock detection before smoothing
            swing = abs(fcs_raw - prev_fcs)
            if swing >= BSI_SHOCK_THRESHOLD:
                bsi_shock = True

            # Apply EMA
            fcs_composite = round(
                (EMA_ALPHA * fcs_raw) + ((1 - EMA_ALPHA) * prev_fcs), 2
            )
        else:
            fcs_composite = fcs_raw

    # ── Step 8: Cap FCS movement ──────────────────────────────────────────
    if previous_snapshot and previous_snapshot.fcs_composite is not None:
        fcs_composite = _cap_fcs_movement(fcs_composite, previous_snapshot.fcs_composite)

    # ── Step 9: Confidence score ──────────────────────────────────────────
    checkin_count_30d = len(windowed.get(30, []))
    participation_ratio = min(checkin_count_30d / max(MIN_CHECKINS_FOR_CONFIDENT, 1), 1.0)
    pillar_coverage = pillars_with_data / 5.0
    fcs_confidence = round(participation_ratio * pillar_coverage * 100, 1)

    # ── Step 10: BSI from weekly questions ────────────────────────────────
    bsi_start = now - timedelta(days=7)
    bsi_score = _compute_bsi(db, user_id, bsi_start, now)

    if bsi_shock and bsi_score is not None:
        bsi_score = round(bsi_score * 1.25, 2)
    elif bsi_shock:
        bsi_score = -25.0

    # ── Step 12: Persist ──────────────────────────────────────────────────
    snapshot = UserMetricSnapshot(
        user_id=user_id,
        computed_at=now,
        current_stability=blended.get("current_stability"),
        future_outlook=blended.get("future_outlook"),
        purchasing_power=blended.get("purchasing_power"),
        emergency_readiness=blended.get("emergency_readiness"),
        financial_agency=blended.get("financial_agency"),
        fcs_raw=fcs_raw,
        fcs_composite=fcs_composite,
        fcs_confidence=fcs_confidence,
        bsi_score=bsi_score,
        bsi_shock=bsi_shock,
        checkin_count=len(all_responses),
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
    Scale: -100 (contraction) to +100 (expansion). 0 = neutral.
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
    bsi = (avg - 0.5) * 200
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
    last_checkin = getattr(user, "last_checkin_at", None)
    today = now.date()

    if last_checkin is not None:
        last_date = last_checkin.date() if hasattr(last_checkin, "date") else last_checkin
        if last_date == today:
            return
        elif last_date == today - timedelta(days=1):
            user.current_streak = current_streak + 1
        else:
            user.current_streak = 1
    else:
        user.current_streak = 1

    user.last_checkin_at = now
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