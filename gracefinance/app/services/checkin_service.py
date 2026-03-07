"""
CheckIn Service — v5.1 (Full Audit Implementation)
══════════════════════════════════════════════════════════════════
ADDITIONS FROM v5.0:

  CROSS-DIMENSIONAL COHERENCE (Audit Item #1):
    Computes standard deviation across the 5 pillar scores.
    High std dev = internally contradictory (e.g., high stability
    but zero emergency readiness). Stored as fcs_coherence (0-100).
    100 = perfectly coherent. Low values = potential dishonesty signal.

  SUSTAINED DETERIORATION FLAG (Audit Item #2):
    If fcs_raw < fcs_composite for 5+ consecutive snapshots,
    sustained_deterioration = True. Means the EMA is masking
    a real downward trend. Grace AI can surface this.

  RAW-COMPOSITE GAP TRACKING (Audit Item #3):
    Stores raw_composite_gap = fcs_raw - fcs_composite.
    Positive = raw is above smoothed (improving faster than shown).
    Negative = raw is below smoothed (declining, masked by EMA).
    Widening gap = real trend being hidden by smoothing.

  POPULATION RECALIBRATION READY (Audit Item #4):
    _compute_population_adjustment() is stubbed and returns 0.0
    until MIN_USERS_FOR_RECALIBRATION (100) is reached. Once
    active, applies a z-score offset to center the population mean
    toward 50. Activates automatically at scale.

  RESPONSE ENTROPY MONITORING (Audit Item #5):
    Computes Shannon entropy of each user's responses per dimension
    over the last 30 days. Low entropy = same answer every day =
    potential gaming or disengagement. Stored as fcs_entropy (0-100).

  TEMPORAL QUESTION WEIGHTING (Audit Item #8):
    Questions tagged with temporal_scope ("week" or "month") are
    weighted differently in each window:
      "week" questions: 30d window weight boosted by 1.5x
      "month" questions: 60d window weight boosted by 1.3x
    This aligns the question's reference frame with the scoring window.

INTERFACE: Same as v5 — drop-in replacement.
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
    QUESTION_TEMPORAL_SCOPE,
)


# ══════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════

FORMULA_BEHAVIOR_WEIGHT: float = 0.60
FORMULA_CONSISTENCY_WEIGHT: float = 0.30
FORMULA_TREND_WEIGHT: float = 0.10

assert abs(FORMULA_BEHAVIOR_WEIGHT + FORMULA_CONSISTENCY_WEIGHT + FORMULA_TREND_WEIGHT - 1.0) < 1e-9

EMA_ALPHA: float = 0.15

WINDOW_WEIGHTS: Dict[int, float] = {
    30: 0.20,
    60: 0.35,
    90: 0.45,
}

# Temporal weighting boosts
TEMPORAL_BOOST_WEEK_30D: float = 1.5    # "week" questions get 1.5x weight in 30d window
TEMPORAL_BOOST_MONTH_60D: float = 1.3   # "month" questions get 1.3x weight in 60d window

MAX_FCS_MOVEMENT: float = 3.0
MAX_PILLAR_MOVEMENT: float = 0.02

MIN_CHECKINS_FOR_CONFIDENT: int = 5
MIN_PILLARS_FOR_SCORE: int = 3
CONFIDENT_THRESHOLD: float = 50.0

TREND_LOOKBACK_DAYS: int = 14
TREND_SLOPE_SCALE: float = 2.0
TREND_NEUTRAL: float = 50.0

OUTLIER_SIGMA_THRESHOLD: float = 2.0
OUTLIER_DAMPEN_FACTOR: float = 0.5

BSI_SHOCK_THRESHOLD: float = 20.0

# Sustained deterioration: raw < composite for N consecutive snapshots
DETERIORATION_CONSECUTIVE_THRESHOLD: int = 5

# Population recalibration: only activate at this user count
MIN_USERS_FOR_RECALIBRATION: int = 100


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

def _gather_windowed_responses(db, user_id, now):
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


def _compute_dimension_averages_temporal(
    responses: List[CheckInResponse],
    window_days: int,
) -> Dict[str, Optional[float]]:
    """
    Compute per-dimension weighted averages with temporal boosting.
    Questions about 'this week' get boosted in the 30d window.
    Questions about 'this month' get boosted in the 60d window.
    """
    dim_weighted: Dict[str, List[tuple]] = {dim: [] for dim in FCS_WEIGHTS}

    for r in responses:
        dim = r.dimension
        if dim in dim_weighted and r.normalized_value is not None:
            # Determine temporal weight
            scope = QUESTION_TEMPORAL_SCOPE.get(r.question_id, "general")
            weight = 1.0

            if scope == "week" and window_days == 30:
                weight = TEMPORAL_BOOST_WEEK_30D
            elif scope == "month" and window_days == 60:
                weight = TEMPORAL_BOOST_MONTH_60D

            dim_weighted[dim].append((r.normalized_value, weight))

    averages: Dict[str, Optional[float]] = {}
    for dim in FCS_WEIGHTS:
        pairs = dim_weighted[dim]
        if pairs:
            total_weight = sum(w for _, w in pairs)
            weighted_sum = sum(v * w for v, w in pairs)
            averages[dim] = weighted_sum / total_weight if total_weight > 0 else None
        else:
            averages[dim] = None
    return averages


# ══════════════════════════════════════════
#  OUTLIER DAMPENING
# ══════════════════════════════════════════

def _dampen_outliers(responses):
    from copy import copy

    dim_vals = {}
    for r in responses:
        if r.dimension not in dim_vals:
            dim_vals[r.dimension] = []
        if r.normalized_value is not None:
            dim_vals[r.dimension].append(r.normalized_value)

    dim_stats = {}
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
                        r.normalized_value + OUTLIER_DAMPEN_FACTOR * (mean - r.normalized_value), 4
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
#  CROSS-DIMENSIONAL COHERENCE (Audit #1)
# ══════════════════════════════════════════

def _compute_coherence(blended: Dict[str, Optional[float]]) -> float:
    """
    Measures how internally consistent the user's pillar scores are.
    Low std dev across pillars = coherent (100).
    High std dev = contradictory signals (lower score).

    Scale: 0-100 where 100 = perfectly coherent.
    A user claiming 100% stability but 0% emergency readiness
    would score low here.
    """
    values = [v for v in blended.values() if v is not None]
    if len(values) < 2:
        return 100.0  # not enough data to judge

    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std_dev = math.sqrt(variance)

    # Max possible std_dev on 0-1 scale with 5 values is ~0.45
    # Map: 0 std_dev = 100 coherence, 0.45 std_dev = 0 coherence
    coherence = max(0.0, 100.0 * (1.0 - (std_dev / 0.45)))
    return round(coherence, 1)


# ══════════════════════════════════════════
#  SUSTAINED DETERIORATION (Audit #2)
# ══════════════════════════════════════════

def _check_sustained_deterioration(db, user_id) -> bool:
    """
    Returns True if fcs_raw has been below fcs_composite for
    DETERIORATION_CONSECUTIVE_THRESHOLD consecutive snapshots.
    This means the EMA smoothing is masking a real downward trend.
    """
    recent = (
        db.query(UserMetricSnapshot)
        .filter(
            UserMetricSnapshot.user_id == user_id,
            UserMetricSnapshot.fcs_raw.isnot(None),
            UserMetricSnapshot.fcs_composite.isnot(None),
        )
        .order_by(UserMetricSnapshot.computed_at.desc())
        .limit(DETERIORATION_CONSECUTIVE_THRESHOLD)
        .all()
    )

    if len(recent) < DETERIORATION_CONSECUTIVE_THRESHOLD:
        return False

    return all(
        float(s.fcs_raw) < float(s.fcs_composite)
        for s in recent
    )


# ══════════════════════════════════════════
#  RESPONSE ENTROPY (Audit #5)
# ══════════════════════════════════════════

def _compute_response_entropy(db, user_id, now) -> float:
    """
    Shannon entropy of response patterns over last 30 days.
    High entropy = varied responses = likely honest.
    Low entropy = same answers every day = potential gaming.

    Scale: 0-100 where 100 = maximum variety, 0 = identical responses.
    """
    cutoff = now - timedelta(days=30)

    responses = (
        db.query(CheckInResponse)
        .filter(
            and_(
                CheckInResponse.user_id == user_id,
                CheckInResponse.checkin_date >= cutoff,
                CheckInResponse.dimension != "conversation_theme",
            )
        )
        .all()
    )

    if len(responses) < 5:
        return 50.0  # not enough data, return neutral

    # Group by dimension, compute entropy per dimension
    dim_responses: Dict[str, List[int]] = {}
    for r in responses:
        if r.dimension not in dim_responses:
            dim_responses[r.dimension] = []
        if r.raw_value is not None:
            dim_responses[r.dimension].append(r.raw_value)

    entropies = []
    for dim, values in dim_responses.items():
        if len(values) < 3:
            continue

        # Count frequency of each unique value
        counts: Dict[int, int] = {}
        for v in values:
            counts[v] = counts.get(v, 0) + 1

        n = len(values)
        entropy = 0.0
        for count in counts.values():
            p = count / n
            if p > 0:
                entropy -= p * math.log2(p)

        # Normalize: max entropy for a 1-5 scale = log2(5) ≈ 2.32
        # For 1-10 scale = log2(10) ≈ 3.32
        scale_max = max(values) if values else 5
        max_entropy = math.log2(min(scale_max, len(set(values)))) if len(set(values)) > 1 else 1.0
        normalized = (entropy / max_entropy) * 100 if max_entropy > 0 else 50.0
        entropies.append(normalized)

    if not entropies:
        return 50.0

    return round(sum(entropies) / len(entropies), 1)


# ══════════════════════════════════════════
#  TREND SCORE COMPUTATION
# ══════════════════════════════════════════

def _compute_trend_score(db, user_id, now):
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
        return TREND_NEUTRAL

    n = len(snapshots)
    first_time = snapshots[0].computed_at.timestamp()

    xs = [(s.computed_at.timestamp() - first_time) / 86400.0 for s in snapshots]
    ys = [float(s.fcs_behavior) for s in snapshots]

    x_mean = sum(xs) / n
    y_mean = sum(ys) / n

    num = sum((xs[i] - x_mean) * (ys[i] - y_mean) for i in range(n))
    den = sum((xs[i] - x_mean) ** 2 for i in range(n))

    if den == 0:
        return TREND_NEUTRAL

    slope = num / den
    normalized = TREND_NEUTRAL + (slope / TREND_SLOPE_SCALE) * 50.0
    return round(max(0.0, min(100.0, normalized)), 2)


def _compute_user_slopes(db, user_id, now):
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
#  POPULATION RECALIBRATION STUB (Audit #4)
# ══════════════════════════════════════════

def _compute_population_adjustment(db) -> float:
    """
    Returns a z-score offset to re-center the population mean toward 50.
    Only activates when MIN_USERS_FOR_RECALIBRATION active users exist.
    Returns 0.0 until then (no effect).

    When active:
      offset = 50 - population_mean
      Applied as: fcs_raw += offset * 0.1 (gentle, max 2 pts adjustment)
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)

    # Count active users with recent scores
    active_count = (
        db.query(func.count(func.distinct(UserMetricSnapshot.user_id)))
        .filter(
            UserMetricSnapshot.computed_at >= cutoff,
            UserMetricSnapshot.fcs_composite.isnot(None),
        )
        .scalar() or 0
    )

    if active_count < MIN_USERS_FOR_RECALIBRATION:
        return 0.0

    # Get population mean from latest snapshots
    from sqlalchemy import desc

    latest_sub = (
        db.query(
            UserMetricSnapshot.user_id,
            func.max(UserMetricSnapshot.computed_at).label("max_ct"),
        )
        .filter(
            UserMetricSnapshot.computed_at >= cutoff,
            UserMetricSnapshot.fcs_composite.isnot(None),
        )
        .group_by(UserMetricSnapshot.user_id)
        .subquery()
    )

    snapshots = (
        db.query(UserMetricSnapshot.fcs_composite)
        .join(
            latest_sub,
            and_(
                UserMetricSnapshot.user_id == latest_sub.c.user_id,
                UserMetricSnapshot.computed_at == latest_sub.c.max_ct,
            ),
        )
        .all()
    )

    scores = [float(s[0]) for s in snapshots if s[0] is not None]
    if not scores:
        return 0.0

    population_mean = sum(scores) / len(scores)
    offset = 50.0 - population_mean

    # Gentle adjustment: max 2 points, applied at 10% strength
    capped_offset = max(-20.0, min(20.0, offset))
    return round(capped_offset * 0.1, 2)


# ══════════════════════════════════════════
#  SNAPSHOT COMPUTATION — v5.1 FULL AUDIT ENGINE
# ══════════════════════════════════════════

def compute_user_snapshot(db: Session, user_id) -> UserMetricSnapshot:
    """
    v5.1 FCS computation pipeline (full audit implementation):

    Step 1  — Gather responses across 30/60/90-day windows
    Step 2  — Dampen outliers per dimension
    Step 3  — Compute per-dimension averages with temporal weighting
    Step 4  — Blend windows (30d*0.20 + 60d*0.35 + 90d*0.45)
    Step 5  — Cap pillar movement vs previous snapshot
    Step 6a — Compute Behavior Score (0-100)
    Step 6b — Compute Consistency Score (0-100)
    Step 6c — Compute Trend Score (0-100)
    Step 6d — Compute raw FCS: Behavior*0.60 + Consistency*0.30 + Trend*0.10
    Step 6e — Apply population recalibration (when at scale)
    Step 7  — Apply EMA smoothing (alpha=0.15)
    Step 8  — Cap FCS movement (+/-3 points max)
    Step 9  — Compute confidence metadata
    Step 10 — Compute BSI from weekly behavioral questions
    Step 11 — Update streak
    Step 12 — Compute per-user slopes (7d, 30d)
    Step 13 — Compute coherence score
    Step 14 — Check sustained deterioration
    Step 15 — Compute response entropy
    Step 16 — Compute raw-composite gap
    Step 17 — Persist and return snapshot
    """
    now = datetime.now(timezone.utc)

    _update_streak(db, user_id, now)

    previous_snapshot = _get_latest_snapshot(db, user_id)

    # Step 1
    windowed = _gather_windowed_responses(db, user_id, now)

    all_responses = windowed.get(90, [])
    if not all_responses:
        snapshot = UserMetricSnapshot(
            user_id=user_id,
            computed_at=now,
            current_stability=None, future_outlook=None,
            purchasing_power=None, emergency_readiness=None,
            financial_agency=None,
            fcs_behavior=None, fcs_consistency=None, fcs_trend=None,
            fcs_raw=None, fcs_composite=None, fcs_confidence=0.0,
            fcs_coherence=None, fcs_entropy=None,
            fcs_slope_7d=None, fcs_slope_30d=None,
            raw_composite_gap=None, sustained_deterioration=False,
            bsi_score=None, bsi_shock=False, checkin_count=0,
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot

    # Step 2
    dampened_windows = {}
    for days, responses in windowed.items():
        dampened_windows[days] = _dampen_outliers(responses)

    # Step 3 — temporal-weighted dimension averages
    window_averages = {}
    for days, responses in dampened_windows.items():
        window_averages[days] = _compute_dimension_averages_temporal(responses, days)

    # Step 4 — blend windows
    blended: Dict[str, Optional[float]] = {}
    for dim in FCS_WEIGHTS:
        weighted_sum = 0.0
        total_weight = 0.0
        for days, weight in WINDOW_WEIGHTS.items():
            val = window_averages[days].get(dim)
            if val is not None:
                weighted_sum += val * weight
                total_weight += weight
        blended[dim] = round(weighted_sum / total_weight, 4) if total_weight > 0 else None

    # Step 5
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

    # Step 6a — Behavior Score
    answered_weight = sum(w for dim, w in FCS_WEIGHTS.items() if blended.get(dim) is not None)
    pillars_with_data = sum(1 for dim in FCS_WEIGHTS if blended.get(dim) is not None)

    fcs_behavior = None
    if pillars_with_data >= MIN_PILLARS_FOR_SCORE and answered_weight > 0:
        ws = sum(blended[dim] * weight for dim, weight in FCS_WEIGHTS.items() if blended.get(dim) is not None)
        fcs_behavior = round((ws / answered_weight) * 100, 2)

    # Step 6b — Consistency Score
    checkin_count_30d = len(windowed.get(30, []))
    participation_ratio = min(checkin_count_30d / max(MIN_CHECKINS_FOR_CONFIDENT, 1), 1.0)
    pillar_coverage = pillars_with_data / 5.0
    fcs_consistency = round(participation_ratio * pillar_coverage * 100, 2)

    # Step 6c — Trend Score
    fcs_trend = _compute_trend_score(db, user_id, now)

    # Step 6d — Raw FCS composite
    fcs_raw = None
    if fcs_behavior is not None:
        fcs_raw = round(
            (fcs_behavior * FORMULA_BEHAVIOR_WEIGHT)
            + (fcs_consistency * FORMULA_CONSISTENCY_WEIGHT)
            + (fcs_trend * FORMULA_TREND_WEIGHT),
            2,
        )

    # Step 6e — Population recalibration
    if fcs_raw is not None:
        pop_adj = _compute_population_adjustment(db)
        if pop_adj != 0.0:
            fcs_raw = round(max(0, min(100, fcs_raw + pop_adj)), 2)

    # Step 7 — EMA smoothing
    fcs_composite = None
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
            fcs_composite = round((EMA_ALPHA * fcs_raw) + ((1 - EMA_ALPHA) * prev_fcs), 2)
        else:
            fcs_composite = fcs_raw

    # Step 8 — Cap FCS movement
    if previous_snapshot and previous_snapshot.fcs_composite is not None:
        fcs_composite = _cap_fcs_movement(fcs_composite, previous_snapshot.fcs_composite)

    # Step 9 — Confidence
    fcs_confidence = round(participation_ratio * pillar_coverage * 100, 1)

    # Step 10 — BSI
    bsi_start = now - timedelta(days=7)
    bsi_score = _compute_bsi(db, user_id, bsi_start, now)
    if bsi_shock and bsi_score is not None:
        bsi_score = round(bsi_score * 1.25, 2)
    elif bsi_shock:
        bsi_score = -25.0

    # Step 12 — Per-user slopes
    slopes = _compute_user_slopes(db, user_id, now)

    # Step 13 — Coherence
    fcs_coherence = _compute_coherence(blended)

    # Step 14 — Sustained deterioration
    sustained_deterioration = _check_sustained_deterioration(db, user_id)

    # Step 15 — Response entropy
    fcs_entropy = _compute_response_entropy(db, user_id, now)

    # Step 16 — Raw-composite gap
    raw_composite_gap = None
    if fcs_raw is not None and fcs_composite is not None:
        raw_composite_gap = round(fcs_raw - fcs_composite, 2)

    # Step 17 — Persist
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
        fcs_coherence=fcs_coherence,
        fcs_entropy=fcs_entropy,
        fcs_slope_7d=slopes.get("fcs_slope_7d"),
        fcs_slope_30d=slopes.get("fcs_slope_30d"),
        raw_composite_gap=raw_composite_gap,
        sustained_deterioration=sustained_deterioration,
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

def _update_streak(db, user_id, now):
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