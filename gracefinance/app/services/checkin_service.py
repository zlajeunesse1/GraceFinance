"""
CheckIn Service — v5.2 (Adaptive Dampening Fix)
══════════════════════════════════════════════════════════════════
CHANGES FROM v5.1:

  ADAPTIVE PILLAR MOVEMENT CAP:
    Early users (< 10 snapshots) get a wider movement cap so their
    score can actually respond to check-ins. Tightens over time as
    the score becomes more established and meaningful.

      Snapshots 1-3:   cap = 0.15 (pillar can move 15% per check-in)
      Snapshots 4-9:   cap = 0.08
      Snapshots 10-19: cap = 0.04
      Snapshots 20+:   cap = 0.02 (original value — fully stabilized)

  ADAPTIVE EMA ALPHA:
    New users need their score to be responsive. The EMA alpha starts
    high and tapers as data accumulates:

      Snapshots 1-3:   alpha = 0.60 (score mostly follows raw)
      Snapshots 4-9:   alpha = 0.35
      Snapshots 10-19: alpha = 0.20
      Snapshots 20+:   alpha = 0.15 (original value — fully smoothed)

  ADAPTIVE FCS MOVEMENT CAP:
    Same idea — allow bigger jumps early, tighten with maturity:

      Snapshots 1-3:   cap = 10.0
      Snapshots 4-9:   cap = 6.0
      Snapshots 10-19: cap = 4.0
      Snapshots 20+:   cap = 3.0 (original value)

  CHECKIN_COUNT FIX:
    The snapshot's checkin_count now stores the number of distinct
    check-in DAYS (not response rows), consistent with the router fix.

All v5.1 audit features (coherence, deterioration, entropy, population
recalibration, temporal weighting) are preserved unchanged.

INTERFACE: Same as v5.1 — drop-in replacement.
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

# ── Adaptive EMA Alpha (by snapshot count) ──
# New users need responsiveness; mature users need stability.
EMA_ALPHA_TIERS = [
    (3,  0.60),   # snapshots 1-3:  score mostly follows raw
    (9,  0.35),   # snapshots 4-9:  transitional
    (19, 0.20),   # snapshots 10-19: moderate smoothing
]
EMA_ALPHA_DEFAULT: float = 0.15  # 20+ snapshots: original fully-smoothed value

# ── Adaptive Pillar Movement Cap (by snapshot count) ──
PILLAR_CAP_TIERS = [
    (3,  0.15),   # snapshots 1-3:  generous — let pillars find their level
    (9,  0.08),   # snapshots 4-9:  tightening
    (19, 0.04),   # snapshots 10-19: approaching steady state
]
PILLAR_CAP_DEFAULT: float = 0.02  # 20+ snapshots: original tight cap

# ── Adaptive FCS Movement Cap (by snapshot count) ──
FCS_CAP_TIERS = [
    (3,  10.0),   # snapshots 1-3:  allow meaningful initial movement
    (9,   6.0),   # snapshots 4-9:  tightening
    (19,  4.0),   # snapshots 10-19
]
FCS_CAP_DEFAULT: float = 3.0  # 20+ snapshots: original cap

WINDOW_WEIGHTS: Dict[int, float] = {
    30: 0.20,
    60: 0.35,
    90: 0.45,
}

# Temporal weighting boosts
TEMPORAL_BOOST_WEEK_30D: float = 1.5
TEMPORAL_BOOST_MONTH_60D: float = 1.3

MIN_CHECKINS_FOR_CONFIDENT: int = 5
MIN_PILLARS_FOR_SCORE: int = 3
CONFIDENT_THRESHOLD: float = 50.0

TREND_LOOKBACK_DAYS: int = 14
TREND_SLOPE_SCALE: float = 2.0
TREND_NEUTRAL: float = 50.0

OUTLIER_SIGMA_THRESHOLD: float = 2.0
OUTLIER_DAMPEN_FACTOR: float = 0.5

BSI_SHOCK_THRESHOLD: float = 20.0

DETERIORATION_CONSECUTIVE_THRESHOLD: int = 5
MIN_USERS_FOR_RECALIBRATION: int = 100


# ══════════════════════════════════════════
#  ADAPTIVE TIER HELPER
# ══════════════════════════════════════════

def _get_tiered_value(snapshot_count: int, tiers: list, default: float) -> float:
    """
    Given a snapshot count, return the appropriate value from the tier list.
    Tiers are (max_count, value) pairs checked in order.
    Falls through to default if snapshot_count exceeds all tier thresholds.
    """
    for max_count, value in tiers:
        if snapshot_count <= max_count:
            return value
    return default


def _count_user_snapshots(db: Session, user_id) -> int:
    """Count total existing snapshots for adaptive parameter selection."""
    return (
        db.query(func.count(UserMetricSnapshot.id))
        .filter(
            UserMetricSnapshot.user_id == user_id,
            UserMetricSnapshot.fcs_composite.isnot(None),
        )
        .scalar() or 0
    )


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
#  MOVEMENT CAPPING (now adaptive)
# ══════════════════════════════════════════

def _cap_pillar_movement(new_val, old_val, max_movement: float):
    """Cap pillar movement with an adaptive max_movement parameter."""
    if new_val is None or old_val is None:
        return new_val
    delta = new_val - old_val
    if abs(delta) > max_movement:
        return round(old_val + (max_movement if delta > 0 else -max_movement), 4)
    return new_val


def _cap_fcs_movement(new_fcs, old_fcs, max_movement: float):
    """Cap FCS movement with an adaptive max_movement parameter."""
    if new_fcs is None or old_fcs is None:
        return new_fcs
    delta = new_fcs - old_fcs
    if abs(delta) > max_movement:
        return round(old_fcs + (max_movement if delta > 0 else -max_movement), 2)
    return new_fcs


# ══════════════════════════════════════════
#  CROSS-DIMENSIONAL COHERENCE (Audit #1)
# ══════════════════════════════════════════

def _compute_coherence(blended: Dict[str, Optional[float]]) -> float:
    values = [v for v in blended.values() if v is not None]
    if len(values) < 2:
        return 100.0

    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std_dev = math.sqrt(variance)

    coherence = max(0.0, 100.0 * (1.0 - (std_dev / 0.45)))
    return round(coherence, 1)


# ══════════════════════════════════════════
#  SUSTAINED DETERIORATION (Audit #2)
# ══════════════════════════════════════════

def _check_sustained_deterioration(db, user_id) -> bool:
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
        return 50.0

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

        counts: Dict[int, int] = {}
        for v in values:
            counts[v] = counts.get(v, 0) + 1

        n = len(values)
        entropy = 0.0
        for count in counts.values():
            p = count / n
            if p > 0:
                entropy -= p * math.log2(p)

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
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)

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

    capped_offset = max(-20.0, min(20.0, offset))
    return round(capped_offset * 0.1, 2)


# ══════════════════════════════════════════
#  DISTINCT CHECK-IN DAY COUNT
# ══════════════════════════════════════════

def _count_distinct_checkin_days(db: Session, user_id, since: datetime) -> int:
    """
    Count distinct calendar days (UTC) with at least one check-in response.
    Used instead of raw row count to get the actual number of check-in sessions.
    """
    distinct_days = (
        db.query(
            func.count(
                func.distinct(func.date(CheckInResponse.checkin_date))
            )
        )
        .filter(
            and_(
                CheckInResponse.user_id == user_id,
                CheckInResponse.checkin_date >= since,
            )
        )
        .scalar() or 0
    )
    return distinct_days


# ══════════════════════════════════════════
#  SNAPSHOT COMPUTATION — v5.2 ADAPTIVE ENGINE
# ══════════════════════════════════════════

def compute_user_snapshot(db: Session, user_id) -> UserMetricSnapshot:
    """
    v5.2 FCS computation pipeline (adaptive dampening):

    Same 17-step pipeline as v5.1, but Steps 5/7/8 now use adaptive
    parameters that scale with the user's snapshot count:

      Early users  → responsive (wide caps, high alpha)
      Mature users → stable (tight caps, low alpha)

    This fixes the "flatline at first score" bug where triple-dampening
    (pillar cap + EMA + FCS cap) made it mathematically impossible for
    scores to move meaningfully in the first ~10 check-ins.
    """
    now = datetime.now(timezone.utc)

    _update_streak(db, user_id, now)

    previous_snapshot = _get_latest_snapshot(db, user_id)

    # ── Determine adaptive parameters based on history ──
    snapshot_count = _count_user_snapshots(db, user_id)
    adaptive_pillar_cap = _get_tiered_value(snapshot_count, PILLAR_CAP_TIERS, PILLAR_CAP_DEFAULT)
    adaptive_ema_alpha = _get_tiered_value(snapshot_count, EMA_ALPHA_TIERS, EMA_ALPHA_DEFAULT)
    adaptive_fcs_cap = _get_tiered_value(snapshot_count, FCS_CAP_TIERS, FCS_CAP_DEFAULT)

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

    # Step 5 — Cap pillar movement (ADAPTIVE)
    if previous_snapshot:
        prev_dims = {
            "current_stability": previous_snapshot.current_stability,
            "future_outlook": previous_snapshot.future_outlook,
            "purchasing_power": previous_snapshot.purchasing_power,
            "emergency_readiness": previous_snapshot.emergency_readiness,
            "financial_agency": previous_snapshot.financial_agency,
        }
        for dim in FCS_WEIGHTS:
            blended[dim] = _cap_pillar_movement(
                blended[dim], prev_dims.get(dim), adaptive_pillar_cap
            )

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

    # Step 7 — EMA smoothing (ADAPTIVE ALPHA)
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
            fcs_composite = round(
                (adaptive_ema_alpha * fcs_raw) + ((1 - adaptive_ema_alpha) * prev_fcs), 2
            )
        else:
            fcs_composite = fcs_raw

    # Step 8 — Cap FCS movement (ADAPTIVE)
    if previous_snapshot and previous_snapshot.fcs_composite is not None:
        fcs_composite = _cap_fcs_movement(
            fcs_composite, previous_snapshot.fcs_composite, adaptive_fcs_cap
        )

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
    #   checkin_count = distinct days, not response rows
    distinct_days_90d = _count_distinct_checkin_days(
        db, user_id, now - timedelta(days=90)
    )

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
        checkin_count=distinct_days_90d,
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