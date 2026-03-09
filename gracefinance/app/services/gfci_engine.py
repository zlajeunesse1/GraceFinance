"""
GFCI Engine — GraceFinance Composite Index
═══════════════════════════════════════════════
v2.2 — Early-stage fixes

CHANGES FROM v2.1:
  - MIN_USERS_FOR_INDEX lowered to 1 (preview mode). The index always
    computes if there's at least 1 eligible user. The "published" vs
    "beta" vs "preview" tier label communicates credibility instead of
    blocking computation entirely.
  - Upserts today's index row instead of creating duplicates. Uses
    index_date (date, not datetime) to dedup — one row per segment
    per calendar day.
  - contributor_count helper uses stale_cutoff (14d) for active count.
  - compute_daily_gfci returns the index even with 1 user so the
    dashboard always has data during early testing/launch.
"""

from datetime import datetime, timezone, timedelta, date as date_type
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
import math

from app.models.checkin import UserMetricSnapshot, DailyIndex
from app.models import User


# ══════════════════════════════════════════
#  GFCI CONFIG
# ══════════════════════════════════════════

INDEX_EMA_ALPHA: float = 0.10

# Credibility tiers (labels only — no longer blocks computation)
MIN_USERS_FOR_PUBLISHED: int = 200     # "published" tier
MIN_USERS_FOR_BETA: int = 50           # "beta" tier
# Below 50 = "preview" tier — still computes, just labeled accordingly

CONFIDENCE_FULL_WEIGHT: float = 50.0
CONFIDENCE_REDUCED_WEIGHT: float = 0.3

MAX_INDEX_MOVEMENT: float = 5.0
STALE_USER_DAYS: int = 14

STREAK_WEIGHT_BONUS: float = 0.05
MAX_STREAK_BONUS: float = 0.50


# ══════════════════════════════════════════
#  PARTICIPATION WEIGHTING
# ══════════════════════════════════════════

def _compute_user_weight(snapshot, user=None):
    weight = 1.0

    confidence = snapshot.fcs_confidence or 0.0
    if confidence < CONFIDENCE_FULL_WEIGHT:
        weight *= CONFIDENCE_REDUCED_WEIGHT

    if user:
        streak = getattr(user, "current_streak", 0) or 0
        bonus = min(streak * STREAK_WEIGHT_BONUS, MAX_STREAK_BONUS)
        weight += bonus

    return round(weight, 4)


# ══════════════════════════════════════════
#  DISTRIBUTION ANALYSIS
# ══════════════════════════════════════════

def _compute_distribution(scores):
    n = len(scores)
    if n == 0:
        return {"mean": 0.0, "median": 0.0, "std_dev": 0.0, "skew": 0.0}

    sorted_scores = sorted(scores)
    mean = sum(scores) / n

    if n % 2 == 0:
        median = (sorted_scores[n // 2 - 1] + sorted_scores[n // 2]) / 2
    else:
        median = sorted_scores[n // 2]

    variance = sum((s - mean) ** 2 for s in scores) / n
    std_dev = math.sqrt(variance) if variance > 0 else 0.0

    skew = 0.0
    if std_dev > 0 and n >= 3:
        skew = (
            sum(((s - mean) / std_dev) ** 3 for s in scores)
            * n / ((n - 1) * (n - 2))
        )

    return {
        "mean": round(mean, 2),
        "median": round(median, 2),
        "std_dev": round(std_dev, 2),
        "skew": round(skew, 4),
    }


# ══════════════════════════════════════════
#  ACTIVE CONTRIBUTOR COUNT
# ══════════════════════════════════════════

def get_active_contributor_count(db: Session) -> int:
    """
    Count distinct users who have submitted at least one check-in
    within the STALE_USER_DAYS window (14 days). This is the real
    'active contributors' number — not all-time.
    """
    from app.models.checkin import CheckInResponse

    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=STALE_USER_DAYS)
    return (
        db.query(func.count(func.distinct(CheckInResponse.user_id)))
        .filter(CheckInResponse.checkin_date >= stale_cutoff)
        .scalar() or 0
    )


# ══════════════════════════════════════════
#  MAIN GFCI COMPUTATION
# ══════════════════════════════════════════

def compute_daily_gfci(db, segment="national"):
    now = datetime.now(timezone.utc)
    today = now.date()
    stale_cutoff = now - timedelta(days=STALE_USER_DAYS)

    # Get latest snapshot per ACTIVE user (excludes orphaned snapshots)
    latest_sub = (
        db.query(
            UserMetricSnapshot.user_id,
            func.max(UserMetricSnapshot.computed_at).label("max_computed"),
        )
        .join(User, UserMetricSnapshot.user_id == User.id)
        .filter(
            UserMetricSnapshot.fcs_composite.isnot(None),
            UserMetricSnapshot.computed_at >= stale_cutoff,
        )
        .group_by(UserMetricSnapshot.user_id)
        .subquery()
    )

    snapshots = (
        db.query(UserMetricSnapshot)
        .join(
            latest_sub,
            and_(
                UserMetricSnapshot.user_id == latest_sub.c.user_id,
                UserMetricSnapshot.computed_at == latest_sub.c.max_computed,
            ),
        )
        .all()
    )

    if not snapshots:
        return None

    # Build weighted scores
    weighted_scores = []
    raw_scores = []
    total_weight = 0.0

    for snap in snapshots:
        if snap.fcs_composite is None:
            continue
        user = db.query(User).filter(User.id == snap.user_id).first()
        if not user:
            continue
        weight = _compute_user_weight(snap, user)
        weighted_scores.append((float(snap.fcs_composite), weight))
        raw_scores.append(float(snap.fcs_composite))
        total_weight += weight

    user_count = len(weighted_scores)

    if user_count == 0:
        return None

    # Weighted mean FCS
    if total_weight > 0:
        raw_gfci = sum(score * w for score, w in weighted_scores) / total_weight
    else:
        raw_gfci = sum(score for score, _ in weighted_scores) / user_count

    raw_gfci = round(raw_gfci, 2)

    # Distribution analysis
    dist = _compute_distribution(raw_scores)

    # EMA smoothing against previous index
    previous_index = _get_latest_index(db, segment)
    prev_value = (
        previous_index.gf_rwi_composite
        if previous_index and previous_index.gf_rwi_composite
        else None
    )

    if prev_value is not None:
        smoothed = round(
            (INDEX_EMA_ALPHA * raw_gfci) + ((1 - INDEX_EMA_ALPHA) * prev_value), 2
        )
    else:
        smoothed = raw_gfci

    # Cap movement
    if prev_value is not None:
        delta = smoothed - prev_value
        if abs(delta) > MAX_INDEX_MOVEMENT:
            smoothed = round(
                prev_value + (MAX_INDEX_MOVEMENT if delta > 0 else -MAX_INDEX_MOVEMENT), 2
            )

    # Trend fields
    trend_direction = "FLAT"
    gci_slope_3d = None
    gci_slope_7d = None
    gci_volatility_7d = None

    recent_indices = _get_recent_indices(db, segment, days=7)
    if len(recent_indices) >= 3:
        last_3 = recent_indices[-3:]
        gci_slope_3d = round(
            (last_3[-1].gf_rwi_composite - last_3[0].gf_rwi_composite) / 3, 4
        )

        if len(recent_indices) >= 7:
            gci_slope_7d = round(
                (recent_indices[-1].gf_rwi_composite - recent_indices[0].gf_rwi_composite) / 7, 4
            )

        if len(recent_indices) >= 2:
            daily_changes = []
            for i in range(1, len(recent_indices)):
                daily_changes.append(
                    recent_indices[i].gf_rwi_composite - recent_indices[i - 1].gf_rwi_composite
                )
            if daily_changes:
                mean_change = sum(daily_changes) / len(daily_changes)
                vol = math.sqrt(
                    sum((c - mean_change) ** 2 for c in daily_changes) / len(daily_changes)
                )
                gci_volatility_7d = round(vol, 4)

        if gci_slope_3d is not None:
            if gci_slope_3d > 0.1:
                trend_direction = "UP"
            elif gci_slope_3d < -0.1:
                trend_direction = "DOWN"

    # ── Upsert: one row per segment per calendar day ──
    existing = (
        db.query(DailyIndex)
        .filter(
            DailyIndex.segment == segment,
            func.date(DailyIndex.index_date) == today,
        )
        .first()
    )

    if existing:
        # Update in place — no duplicate rows
        existing.fcs_value = raw_gfci
        existing.gf_rwi_composite = smoothed
        existing.user_count = user_count
        existing.computed_at = now
        existing.trend_direction = trend_direction
        existing.gci_slope_3d = gci_slope_3d
        existing.gci_slope_7d = gci_slope_7d
        existing.gci_volatility_7d = gci_volatility_7d
        index = existing
    else:
        index = DailyIndex(
            index_date=now,
            segment=segment,
            fcs_value=raw_gfci,
            gf_rwi_composite=smoothed,
            user_count=user_count,
            computed_at=now,
            trend_direction=trend_direction,
            gci_slope_3d=gci_slope_3d,
            gci_slope_7d=gci_slope_7d,
            gci_volatility_7d=gci_volatility_7d,
        )
        db.add(index)

    db.commit()
    db.refresh(index)
    return index


# ══════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════

def _get_latest_index(db, segment):
    return (
        db.query(DailyIndex)
        .filter(DailyIndex.segment == segment)
        .order_by(desc(DailyIndex.computed_at))
        .first()
    )


def _get_recent_indices(db, segment, days=7):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return (
        db.query(DailyIndex)
        .filter(
            DailyIndex.segment == segment,
            DailyIndex.computed_at >= cutoff,
        )
        .order_by(DailyIndex.computed_at.asc())
        .all()
    )


def get_gfci_history(db, segment="national", days=30):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return (
        db.query(DailyIndex)
        .filter(
            DailyIndex.segment == segment,
            DailyIndex.computed_at >= cutoff,
        )
        .order_by(DailyIndex.computed_at.asc())
        .all()
    )


def get_index_confidence_tier(user_count: int) -> str:
    """Return the credibility tier label for the current index."""
    if user_count >= MIN_USERS_FOR_PUBLISHED:
        return "published"
    elif user_count >= MIN_USERS_FOR_BETA:
        return "beta"
    else:
        return "preview"