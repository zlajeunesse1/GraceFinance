"""
CheckIn Service — v5.0 (Three-Component FCS Formula)
══════════════════════════════════════════════════════════════════
ARCHITECTURE CHANGES FROM v4.0:

  THREE-COMPONENT FCS FORMULA:
    v4: FCS = weighted_pillar_average * 100
    v5: FCS = (Behavior * 0.60) + (Consistency * 0.30) + (Trend * 0.10)

    Behavior Score (0-100):
      Weighted average of blended pillar scores. Same computation as v4.
      Measures the quality of financial behavior right now.

    Consistency Score (0-100):
      participation_ratio * pillar_coverage * 100
      Measures how reliably the user checks in and covers all dimensions.
      7/7 days + 5/5 pillars = 100. 2/7 days + 3/5 pillars = ~17.

    Trend Score (0-100):
      Based on 14-day slope of fcs_behavior (behavior component only).
      Positive slope = improving = above 50. Negative = declining = below 50.
      Flat = 50. Maxes at 0 and 100.

  PER-USER DRIFT DETECTION:
    Stores fcs_slope_7d and fcs_slope_30d on each snapshot.
    Enables 'sustained deterioration' detection without relying on
    movement caps to surface the signal.

  RETAINED FROM v4:
    Multi-window blending (30/60/90-day)
    EMA smoothing (alpha=0.15)
    Movement caps (+/-3 FCS, +/-0.02 pillar)
    Outlier dampening (2-sigma, 50% pull)
    Minimum data thresholds
    BSI computation

INTERFACE: Same as v4 — drop-in replacement.
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

# Three-component FCS formula weights (must sum to 1.0)
FORMULA_BEHAVIOR_WEIGHT: float = 0.60
FORMULA_CONSISTENCY_WEIGHT: float = 0.30
FORMULA_TREND_WEIGHT: float = 0.10

assert abs(FORMULA_BEHAVIOR_WEIGHT + FORMULA_CONSISTENCY_WEIGHT + FORMULA_TREND_WEIGHT - 1.0) < 1e-9

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

# Trend computation
TREND_LOOKBACK_DAYS: int = 14           # days of history for trend slope
TREND_SLOPE_SCALE: float = 2.0          # slope of +/-2 pts/day = max trend score
TREND_NEUTRAL: float = 50.0             # neutral trend = 50/100

# Outlier dampening
OUTLIER_SIGMA_THRESHOLD: float = 2.0
OUTLIER_DAMPEN_FACTOR: float = 0.5

# BSI shock detection
BSI_SHOCK_THRESHOLD: float = 20.0


# ══════════════════════════════════════════
#  NORMALIZATION
# ══════════════════════════════════════════

def normalize_answer(raw: int, scale_max: int, inverted: bool = False) -> float:
    if scale_max <= 1:
        return 1.0
    raw_clamped = max(1, min(raw, scale_max))
    normalized = (raw_clamped - 1) / (scale_max - 1)
    return round(1.0 - normalized if inverted else normalized, 4)


# ══════════════════════════════════════════
#  RESPONSE PERSISTENCE
# ══════════════════════════════════════════

def save_responses(db: Session, user_id, answers: list) -> List[CheckInResponse]:
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
    from copy import copy

    dim_vals: Dict[str, List[float]] = {}
    for r in responses:
        if r.dimension not in dim_vals:
            dim_vals[r.dimension] = []
        if r.normalized_value is not None:
            dim_vals[r.dimension].append(r.normalized_value)

    dim_stats: Dict[str, tuple] = {}
    for dim, vals in dim_vals.items():
        if len(vals) >= 3:
            mean = sum(vals) / len(vals)
            variance = sum((v - mean) ** 2 for v in vals) / len(vals)
            std = math.sqrt(variance) if variance > 0 else 0.0
            dim_stats[dim] = (mean, std)

    dampened = []
    for r in responses:
        if r.dimension in dim_stats and r.normalized_value is not None:
            mean, std = dim_stats[r.dimension]
            if std > 0:
                deviation = abs(r.normalized_value - mean)
                if deviation > OUTLIER_SIGMA_THRESHOLD * std:
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

def _cap_pillar_movement(new_val, old_val):
    if new_val is None or old_val is None:
        return new_val
    delta = new_val - old_val
    if abs(delta) > MAX_PILLAR_MOVEMENT:
        return round(old_val + (MAX_PILLAR_MOVEMENT if delta > 0 else -MAX_PILLAR_MOVEMENT), 4)
    return new_val


def _cap_fcs_movement(new_fcs, old_fcs):
    if new_fcs is None or old_fcs is None:
        return new_fcs
    delta = new_fcs - old_fcs
    if abs(delta) > MAX_FCS_MOVEMENT:
        return round(old_fcs + (MAX_FCS_MOVEMENT if delta > 0 else -MAX_FCS_MOVEMENT), 2)
    return new_fcs


# ══════════════════════════════════════════
#  TREND SCORE COMPUTATION
# ══════════════════════════════════════════

def _compute_trend_score(db: Session, user_id, now: datetime) -> float:
    """
    Compute trend score (0-100) based on the 14-day slope of fcs_behavior.
    50 = flat. >50 = improving. <50 = declining.
    Uses simple linear regression on available snapshots.
    """
    cutoff = now - timedelta(days=TREND_LOOKBACK_DAYS)

    snapshots = (
        db.query(UserMetricSnapshot)
        .filter(
            UserMetricSnapshot.user_id == user_id,
            UserMetricSnapshot.computed_at >= cutoff,
            UserMetricSnapshot.fcs_behavior.isnot(None),
        )
        .order_by(UserMetricSnapshot.computed_at.asc())
        .all()
    )

    if len(snapshots) < 2:
        return TREND_NEUTRAL  # not enough data, return neutral

    # Simple linear regression: slope of fcs_behavior over time
    n = len(snapshots)
    first_time = snapshots[0].computed_at.timestamp()

    xs = []
    ys = []
    for snap in snapshots:
        # x = days since first snapshot in window
        days_elapsed = (snap.computed_at.timestamp() - first_time) / 86400.0
        xs.append(days_elapsed)
        ys.append(float(snap.fcs_behavior))

    x_mean = sum(xs) / n
    y_mean = sum(ys) / n

    numerator = sum((xs[i] - x_mean) * (ys[i] - y_mean) for i in range(n))
    denominator = sum((xs[i] - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return TREND_NEUTRAL

    slope = numerator / denominator  # points per day

    # Map slope to 0-100: slope of +TREND_SLOPE_SCALE = 100, -TREND_SLOPE_SCALE = 0
    normalized = TREND_NEUTRAL + (slope / TREND_SLOPE_SCALE) * 50.0
    return round(max(0.0, min(100.0, normalized)), 2)


def _compute_user_slopes(db: Session, user_id, now: datetime) -> Dict[str, Optional[float]]:
    """
    Compute per-user FCS slopes over 7-day and 30-day windows.
    Returns dict with fcs_slope_7d and fcs_slope_30d.
    """
    slopes = {}

    for label, days in [("fcs_slope_7d", 7), ("fcs_slope_30d", 30)]:
        cutoff = now - timedelta(days=days)

        snapshots = (
            db.query(UserMetricSnapshot)
            .filter(
                UserMetricSnapshot.user_id == user_id,
                UserMetricSnapshot.computed_at >= cutoff,
                UserMetricSnapshot.fcs_composite.isnot(None),
            )
            .order_by(UserMetricSnapshot.computed_at.asc())
            .all()
        )

        if len(snapshots) < 2:
            slopes[label] = None
            continue

        first_time = snapshots[0].computed_at.timestamp()
        n = len(snapshots)

        xs = [(s.computed_at.timestamp() - first_time) / 86400.0 for s in snapshots]
        ys = [float(s.fcs_composite) for s in snapshots]

        x_mean = sum(xs) / n
        y_mean = sum(ys) / n

        num = sum((xs[i] - x_mean) * (ys[i] - y_mean) for i in range(n))
        den = sum((xs[i] - x_mean) ** 2 for i in range(n))

        slopes[label] = round(num / den, 4) if den != 0 else 0.0

    return slopes


# ══════════════════════════════════════════
#  SNAPSHOT COMPUTATION — v5 THREE-COMPONENT ENGINE
# ══════════════════════════════════════════

def compute_user_snapshot(db: Session, user_id) -> UserMetricSnapshot:
    """
    v5 FCS computation pipeline:

    Step 1  — Gather responses across 30/60/90-day windows
    Step 2  — Dampen outliers per dimension
    Step 3  — Compute per-dimension averages per window
    Step 4  — Blend windows (30d*0.20 + 60d*0.35 + 90d*0.45)
    Step 5  — Cap pillar movement vs previous snapshot
    Step 6a — Compute Behavior Score (0-100): weighted pillar composite
    Step 6b — Compute Consistency Score (0-100): participation * coverage
    Step 6c — Compute Trend Score (0-100): 14-day slope of behavior
    Step 6d — Compute raw FCS: Behavior*0.60 + Consistency*0.30 + Trend*0.10
    Step 7  — Apply EMA smoothing (alpha=0.15)
    Step 8  — Cap FCS movement (+/-3 points max)
    Step 9  — Compute confidence metadata
    Step 10 — Compute BSI from weekly behavioral questions
    Step 11 — Update streak
    Step 12 — Compute per-user slopes (7d, 30d)
    Step 13 — Persist and return snapshot
    """
    now = datetime.now(timezone.utc)

    # Update streak first
    _update_streak(db, user_id, now)

    # Get previous snapshot for movement capping and EMA
    previous_snapshot = _get_latest_snapshot(db, user_id)

    # ── Step 1: Gather multi-window responses ─────────────────────────────
    windowed = _gather_windowed_responses(db, user_id, now)

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
            fcs_behavior=None,
            fcs_consistency=None,
            fcs_trend=None,
            fcs_raw=None,
            fcs_composite=None,
            fcs_confidence=0.0,
            fcs_slope_7d=None,
            fcs_slope_30d=None,
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

    # ── Step 6a: Behavior Score (0-100) ───────────────────────────────────
    answered_weight = sum(
        w for dim, w in FCS_WEIGHTS.items() if blended.get(dim) is not None
    )
    pillars_with_data = sum(
        1 for dim in FCS_WEIGHTS if blended.get(dim) is not None
    )

    fcs_behavior: Optional[float] = None
    if pillars_with_data >= MIN_PILLARS_FOR_SCORE and answered_weight > 0:
        weighted_sum = sum(
            blended[dim] * weight
            for dim, weight in FCS_WEIGHTS.items()
            if blended.get(dim) is not None
        )
        fcs_behavior = round((weighted_sum / answered_weight) * 100, 2)

    # ── Step 6b: Consistency Score (0-100) ────────────────────────────────
    checkin_count_30d = len(windowed.get(30, []))
    participation_ratio = min(checkin_count_30d / max(MIN_CHECKINS_FOR_CONFIDENT, 1), 1.0)
    pillar_coverage = pillars_with_data / 5.0
    fcs_consistency = round(participation_ratio * pillar_coverage * 100, 2)

    # ── Step 6c: Trend Score (0-100) ──────────────────────────────────────
    fcs_trend = _compute_trend_score(db, user_id, now)

    # ── Step 6d: Raw FCS composite using three-component formula ──────────
    fcs_raw: Optional[float] = None
    if fcs_behavior is not None:
        fcs_raw = round(
            (fcs_behavior * FORMULA_BEHAVIOR_WEIGHT)
            + (fcs_consistency * FORMULA_CONSISTENCY_WEIGHT)
            + (fcs_trend * FORMULA_TREND_WEIGHT),
            2,
        )

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
            swing = abs(fcs_raw - prev_fcs)
            if swing >= BSI_SHOCK_THRESHOLD:
                bsi_shock = True

            fcs_composite = round(
                (EMA_ALPHA * fcs_raw) + ((1 - EMA_ALPHA) * prev_fcs), 2
            )
        else:
            fcs_composite = fcs_raw

    # ── Step 8: Cap FCS movement ──────────────────────────────────────────
    if previous_snapshot and previous_snapshot.fcs_composite is not None:
        fcs_composite = _cap_fcs_movement(fcs_composite, previous_snapshot.fcs_composite)

    # ── Step 9: Confidence metadata ───────────────────────────────────────
    fcs_confidence = round(participation_ratio * pillar_coverage * 100, 1)

    # ── Step 10: BSI from weekly questions ────────────────────────────────
    bsi_start = now - timedelta(days=7)
    bsi_score = _compute_bsi(db, user_id, bsi_start, now)

    if bsi_shock and bsi_score is not None:
        bsi_score = round(bsi_score * 1.25, 2)
    elif bsi_shock:
        bsi_score = -25.0

    # ── Step 12: Per-user slopes ──────────────────────────────────────────
    slopes = _compute_user_slopes(db, user_id, now)

    # ── Step 13: Persist ──────────────────────────────────────────────────
    snapshot = UserMetricSnapshot(
        user_id=user_id,
        computed_at=now,
        current_stability=blended.get("current_stability"),
        future_outlook=blended.get("future_outlook"),
        purchasing_power=blended.get("purchasing_power"),
        emergency_readiness=blended.get("emergency_readiness"),
        financial_agency=blended.get("financial_agency"),
        fcs_behavior=fcs_behavior,
        fcs_consistency=fcs_consistency,
        fcs_trend=fcs_trend,
        fcs_raw=fcs_raw,
        fcs_composite=fcs_composite,
        fcs_confidence=fcs_confidence,
        fcs_slope_7d=slopes.get("fcs_slope_7d"),
        fcs_slope_30d=slopes.get("fcs_slope_30d"),
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

def _compute_bsi(db, user_id, start, end):
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
    return round((avg - 0.5) * 200, 2)


# ══════════════════════════════════════════
#  STREAK MANAGEMENT
# ══════════════════════════════════════════

def _update_streak(db: Session, user_id, now: datetime) -> None:
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

def _get_latest_snapshot(db, user_id):
    return (
        db.query(UserMetricSnapshot)
        .filter(
            UserMetricSnapshot.user_id == user_id,
            UserMetricSnapshot.fcs_composite.isnot(None),
        )
        .order_by(UserMetricSnapshot.computed_at.desc())
        .first()
    )


def get_user_metric_history(db, user_id, days=30):
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


def get_fcs_label(score):
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