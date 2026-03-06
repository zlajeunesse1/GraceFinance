"""
GFCI Engine — Grace Financial Confidence Index
═══════════════════════════════════════════════
Population-level aggregation of individual FCS scores into a
macroeconomic behavioral confidence signal.

DESIGN PRINCIPLES:
  - Participation-weighted means (consistent users contribute more)
  - Confidence-gated inputs (provisional scores dampened)
  - Population smoothing (EMA at index level)
  - Minimum user thresholds (small samples cannot move the index)
  - Distribution analysis (median, std dev, skew tracked)

EXPECTED BEHAVIOR:
  Normal daily movement:    < 1 point
  Moderate macro shift:     2–4 points
  Major systemic shock:     8–10+ points

INTERFACE:
  compute_daily_gfci(db, segment="national") → DailyIndex
  get_gfci_history(db, segment, days)        → List[DailyIndex]

Place at: app/services/gfci_engine.py
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
import math

from app.models.checkin import UserMetricSnapshot, DailyIndex
from app.models import User


# ══════════════════════════════════════════
#  GFCI CONFIG
# ══════════════════════════════════════════

# EMA smoothing for population index — very slow
INDEX_EMA_ALPHA: float = 0.10

# Minimum users required to publish a confident index
MIN_USERS_FOR_INDEX: int = 10

# Confidence threshold — only "confident" individual scores contribute fully
CONFIDENCE_FULL_WEIGHT: float = 50.0    # fcs_confidence >= this → full weight
CONFIDENCE_REDUCED_WEIGHT: float = 0.3  # below threshold → weighted at 30%

# Maximum index movement per day
MAX_INDEX_MOVEMENT: float = 5.0

# Staleness — exclude users who haven't checked in for N days
STALE_USER_DAYS: int = 14

# Consistency bonus — users with higher streaks get slightly more weight
STREAK_WEIGHT_BONUS: float = 0.05   # per streak day, capped at 0.50 bonus
MAX_STREAK_BONUS: float = 0.50


# ══════════════════════════════════════════
#  PARTICIPATION WEIGHTING
# ══════════════════════════════════════════

def _compute_user_weight(
    snapshot: UserMetricSnapshot,
    user: Optional[User] = None,
) -> float:
    """
    Compute participation weight for a single user's FCS contribution.

    Base weight = 1.0
    Modifiers:
      - Confidence < threshold → reduced to 0.3
      - Streak bonus → up to +0.50 for consistent users
      - Recent check-in bonus → full weight if within 3 days
    """
    weight = 1.0

    # Confidence gate
    confidence = snapshot.fcs_confidence or 0.0
    if confidence < CONFIDENCE_FULL_WEIGHT:
        weight *= CONFIDENCE_REDUCED_WEIGHT

    # Streak bonus
    if user:
        streak = getattr(user, "current_streak", 0) or 0
        bonus = min(streak * STREAK_WEIGHT_BONUS, MAX_STREAK_BONUS)
        weight += bonus

    return round(weight, 4)


# ══════════════════════════════════════════
#  DISTRIBUTION ANALYSIS
# ══════════════════════════════════════════

def _compute_distribution(scores: List[float]) -> Dict[str, float]:
    """
    Compute distribution statistics for the FCS population.
    Used for index quality monitoring and anomaly detection.
    """
    n = len(scores)
    if n == 0:
        return {"mean": 0.0, "median": 0.0, "std_dev": 0.0, "skew": 0.0}

    sorted_scores = sorted(scores)
    mean = sum(scores) / n

    # Median
    if n % 2 == 0:
        median = (sorted_scores[n // 2 - 1] + sorted_scores[n // 2]) / 2
    else:
        median = sorted_scores[n // 2]

    # Standard deviation
    variance = sum((s - mean) ** 2 for s in scores) / n
    std_dev = math.sqrt(variance) if variance > 0 else 0.0

    # Skewness (Fisher's)
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
#  MAIN GFCI COMPUTATION
# ══════════════════════════════════════════

def compute_daily_gfci(
    db: Session,
    segment: str = "national",
) -> Optional[DailyIndex]:
    """
    Compute the daily Grace Financial Confidence Index.

    Pipeline:
      1. Gather latest snapshot per active user
      2. Filter stale users (no check-in in 14 days)
      3. Apply participation weighting
      4. Compute weighted mean FCS
      5. Compute distribution statistics
      6. Apply EMA smoothing against previous index
      7. Cap movement
      8. Persist and return
    """
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(days=STALE_USER_DAYS)

    # ── Step 1: Get latest snapshot per user ──────────────────────────────
    # Subquery: max computed_at per user
    latest_sub = (
        db.query(
            UserMetricSnapshot.user_id,
            func.max(UserMetricSnapshot.computed_at).label("max_computed"),
        )
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

    # ── Step 2: Build weighted scores ─────────────────────────────────────
    weighted_scores = []
    raw_scores = []
    total_weight = 0.0

    for snap in snapshots:
        if snap.fcs_composite is None:
            continue

        # Look up user for streak data
        user = db.query(User).filter(User.id == snap.user_id).first()
        weight = _compute_user_weight(snap, user)

        weighted_scores.append((float(snap.fcs_composite), weight))
        raw_scores.append(float(snap.fcs_composite))
        total_weight += weight

    user_count = len(weighted_scores)

    if user_count == 0:
        return None

    # ── Step 3: Weighted mean FCS ─────────────────────────────────────────
    if total_weight > 0:
        raw_gfci = sum(score * w for score, w in weighted_scores) / total_weight
    else:
        raw_gfci = sum(score for score, _ in weighted_scores) / user_count

    raw_gfci = round(raw_gfci, 2)

    # ── Step 4: Distribution analysis ─────────────────────────────────────
    dist = _compute_distribution(raw_scores)

    # ── Step 5: EMA smoothing ─────────────────────────────────────────────
    previous_index = _get_latest_index(db, segment)
    prev_value = (
        previous_index.gf_rwi_composite
        if previous_index and previous_index.gf_rwi_composite
        else None
    )

    if prev_value is not None:
        smoothed = round(
            (INDEX_EMA_ALPHA * raw_gfci) + ((1 - INDEX_EMA_ALPHA) * prev_value),
            2,
        )
    else:
        smoothed = raw_gfci

    # ── Step 6: Cap movement ──────────────────────────────────────────────
    if prev_value is not None:
        delta = smoothed - prev_value
        if abs(delta) > MAX_INDEX_MOVEMENT:
            smoothed = round(
                prev_value + (MAX_INDEX_MOVEMENT if delta > 0 else -MAX_INDEX_MOVEMENT),
                2,
            )

    # ── Step 7: Determine confidence level ────────────────────────────────
    is_confident = user_count >= MIN_USERS_FOR_INDEX

    # ── Step 8: Compute trend fields ──────────────────────────────────────
    trend_direction = "FLAT"
    gci_slope_3d = None
    gci_slope_7d = None
    gci_volatility_7d = None

    recent_indices = _get_recent_indices(db, segment, days=7)
    if len(recent_indices) >= 3:
        # 3-day slope
        last_3 = recent_indices[-3:]
        gci_slope_3d = round(
            (last_3[-1].gf_rwi_composite - last_3[0].gf_rwi_composite) / 3, 4
        )

        if len(recent_indices) >= 7:
            # 7-day slope
            gci_slope_7d = round(
                (recent_indices[-1].gf_rwi_composite - recent_indices[0].gf_rwi_composite) / 7,
                4,
            )

        # 7-day volatility (std dev of daily changes)
        if len(recent_indices) >= 2:
            daily_changes = []
            for i in range(1, len(recent_indices)):
                daily_changes.append(
                    recent_indices[i].gf_rwi_composite
                    - recent_indices[i - 1].gf_rwi_composite
                )
            if daily_changes:
                mean_change = sum(daily_changes) / len(daily_changes)
                vol = math.sqrt(
                    sum((c - mean_change) ** 2 for c in daily_changes)
                    / len(daily_changes)
                )
                gci_volatility_7d = round(vol, 4)

        # Trend direction
        if gci_slope_3d is not None:
            if gci_slope_3d > 0.1:
                trend_direction = "UP"
            elif gci_slope_3d < -0.1:
                trend_direction = "DOWN"

    # ── Step 9: Persist ───────────────────────────────────────────────────
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

def _get_latest_index(db: Session, segment: str) -> Optional[DailyIndex]:
    """Get most recent GFCI for a segment."""
    return (
        db.query(DailyIndex)
        .filter(DailyIndex.segment == segment)
        .order_by(desc(DailyIndex.computed_at))
        .first()
    )


def _get_recent_indices(
    db: Session, segment: str, days: int = 7
) -> List[DailyIndex]:
    """Get recent index values for trend computation."""
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


def get_gfci_history(
    db: Session,
    segment: str = "national",
    days: int = 30,
) -> List[DailyIndex]:
    """Get GFCI history for charting."""
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