"""
GraceFinance Data Quality Pipeline
====================================
Sits BETWEEN checkin_service and index_engine_service.
Every user response gets validated, scored, and filtered
before it ever touches the GF-RWI.

Clean data is the moat. This module protects it.

Pipeline stages:
  1. Response Validation  — reject impossible/nonsensical answers
  2. Engagement Scoring   — measure response quality per session
  3. Consistency Checks   — flag contradictions within a session
  4. Temporal Analysis    — detect speed-runners and bot patterns
  5. User Reliability     — weight users by their track record
  6. Outlier Detection    — statistical filters before aggregation
  7. Index-Ready Export   — only clean, weighted data hits the index

Place at: app/services/data_quality.py

Usage:
    from app.services.data_quality import (
        validate_session,
        score_response_quality,
        get_index_eligible_snapshots,
    )
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
import math

from app.models.checkin import CheckInResponse, UserMetricSnapshot, DailyIndex
from app.services.checkin_service import FCS_WEIGHTS, get_user_metric_history
from app.services.question_bank import DAILY_QUESTIONS, WEEKLY_QUESTIONS


# ============================================================
#  DATA QUALITY THRESHOLDS
#  Tune these as your user base grows
# ============================================================

# Minimum seconds a valid check-in session should take (4 questions)
MIN_SESSION_DURATION_SECONDS = 15

# Maximum seconds before a session is considered abandoned/distracted
MAX_SESSION_DURATION_SECONDS = 1800  # 30 minutes

# Minimum per-question time to count as "thoughtful" (seconds)
MIN_PER_QUESTION_SECONDS = 3

# How many check-ins a user needs before their data enters the index
MIN_CHECKINS_FOR_INDEX = 3

# Minimum user reliability score to contribute to the index (0.0 - 1.0)
MIN_RELIABILITY_FOR_INDEX = 0.3

# Maximum standard deviations from mean before an FCS score is an outlier
OUTLIER_STDDEV_THRESHOLD = 2.5

# Minimum quality score for a session to count (0.0 - 1.0)
MIN_SESSION_QUALITY = 0.4


# ============================================================
#  DATA STRUCTURES
# ============================================================

@dataclass
class SessionQuality:
    """Quality assessment for a single check-in session."""
    user_id: int
    session_date: datetime
    response_count: int = 0
    duration_seconds: Optional[float] = None
    quality_score: float = 0.0           # 0.0 - 1.0 composite
    speed_score: float = 0.0             # 0.0 - 1.0 (too fast = low)
    consistency_score: float = 1.0       # 1.0 = no contradictions
    variance_score: float = 1.0          # 1.0 = reasonable spread
    is_valid: bool = True
    flags: List[str] = field(default_factory=list)


@dataclass
class UserReliability:
    """Reliability profile for a user's data contributions."""
    user_id: int
    total_checkins: int = 0
    avg_session_quality: float = 0.0
    consistency_ratio: float = 0.0       # % of sessions without contradictions
    streak_days: int = 0
    days_active: int = 0
    reliability_score: float = 0.0       # 0.0 - 1.0 composite
    is_index_eligible: bool = False
    flags: List[str] = field(default_factory=list)


# ============================================================
#  1. SESSION VALIDATION
#     First pass: reject obviously bad data
# ============================================================

def validate_session(responses: List[CheckInResponse]) -> SessionQuality:
    """
    Validate a batch of check-in responses from a single session.
    Returns a SessionQuality assessment.

    Checks:
      - Minimum number of responses
      - Response timing (too fast = spam, too slow = abandoned)
      - Value range validity
      - Within-session consistency
      - Answer variance (all identical = suspicious)
    """
    if not responses:
        sq = SessionQuality(user_id=0, session_date=datetime.now(timezone.utc))
        sq.is_valid = False
        sq.flags.append("empty_session")
        return sq

    user_id = responses[0].user_id
    session_date = responses[0].checkin_date
    sq = SessionQuality(
        user_id=user_id,
        session_date=session_date,
        response_count=len(responses),
    )

    # --- Timing analysis ---
    timestamps = sorted([r.checkin_date for r in responses])
    if len(timestamps) >= 2:
        first = timestamps[0]
        last = timestamps[-1]
        # Handle timezone-naive datetimes
        if first.tzinfo is None:
            first = first.replace(tzinfo=timezone.utc)
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        sq.duration_seconds = (last - first).total_seconds()
    else:
        sq.duration_seconds = None

    # Speed scoring
    if sq.duration_seconds is not None:
        per_question = sq.duration_seconds / max(len(responses), 1)

        if sq.duration_seconds < MIN_SESSION_DURATION_SECONDS:
            sq.speed_score = 0.2
            sq.flags.append("speed_runner")
        elif per_question < MIN_PER_QUESTION_SECONDS:
            sq.speed_score = 0.4
            sq.flags.append("fast_responses")
        elif sq.duration_seconds > MAX_SESSION_DURATION_SECONDS:
            sq.speed_score = 0.6
            sq.flags.append("long_session")
        else:
            # Sweet spot: normalize between min and a reasonable max
            reasonable_max = 120  # 2 minutes for 4 questions is thoughtful
            sq.speed_score = min(1.0, per_question / (reasonable_max / max(len(responses), 1)))
            sq.speed_score = max(0.5, sq.speed_score)  # floor at 0.5 for valid timing
    else:
        sq.speed_score = 0.7  # single response, assume reasonable

    # --- Value range check ---
    for r in responses:
        if r.normalized_value < 0.0 or r.normalized_value > 1.0:
            sq.flags.append(f"out_of_range:{r.question_id}")
            sq.is_valid = False

    # --- Variance check (all identical answers = suspicious) ---
    normalized_vals = [r.normalized_value for r in responses if not r.is_weekly]
    if len(normalized_vals) >= 3:
        unique_vals = set(round(v, 2) for v in normalized_vals)
        if len(unique_vals) == 1:
            sq.variance_score = 0.3
            sq.flags.append("identical_answers")
        elif len(unique_vals) == 2:
            sq.variance_score = 0.7
        else:
            sq.variance_score = 1.0
    else:
        sq.variance_score = 0.8

    # --- Within-session consistency ---
    sq.consistency_score = _check_session_consistency(responses)

    # --- Composite quality score ---
    sq.quality_score = (
        sq.speed_score * 0.30
        + sq.consistency_score * 0.35
        + sq.variance_score * 0.35
    )

    if sq.quality_score < MIN_SESSION_QUALITY:
        sq.flags.append("low_quality_session")

    return sq


def _check_session_consistency(responses: List[CheckInResponse]) -> float:
    """
    Check for contradictions within a single session.

    Examples of contradictions:
      - CS-1 (confident about bills) = 5/5 but CS-3 (financial stress) = 9/10
      - ER-1 (weeks of coverage) = 5/5 but ER-2 (dipped into savings) = 1/5

    Returns 0.0 (fully contradictory) to 1.0 (fully consistent).
    """
    # Build a map of dimension -> normalized values
    dim_values = {}
    for r in responses:
        if r.dimension not in dim_values:
            dim_values[r.dimension] = []
        dim_values[r.dimension].append(r.normalized_value)

    contradictions = 0
    checks = 0

    for dim, values in dim_values.items():
        if len(values) < 2:
            continue

        # Within the same dimension, answers shouldn't wildly disagree
        for i in range(len(values)):
            for j in range(i + 1, len(values)):
                checks += 1
                diff = abs(values[i] - values[j])
                # More than 0.6 spread within same dimension = contradiction
                if diff > 0.6:
                    contradictions += 1

    if checks == 0:
        return 1.0

    return max(0.0, 1.0 - (contradictions / checks))


# ============================================================
#  2. USER RELIABILITY SCORING
#     Track record determines index weight
# ============================================================

def compute_user_reliability(db: Session, user_id: int) -> UserReliability:
    """
    Build a reliability profile for a user based on their check-in history.

    Factors:
      - Total check-in count (more = more reliable)
      - Average session quality over time
      - Consistency ratio (% of sessions without major contradictions)
      - Engagement pattern (streak, regularity)
      - Account age

    Users with higher reliability scores have their data
    weighted more heavily in the GF-RWI.
    """
    ur = UserReliability(user_id=user_id)

    # Get all snapshots
    snapshots = get_user_metric_history(db, user_id, days=90)
    ur.total_checkins = len(snapshots)

    if ur.total_checkins == 0:
        ur.flags.append("no_data")
        return ur

    # Account age
    try:
        from app.models import User
        user = db.query(User).filter(User.id == user_id).first()
        if user and hasattr(user, "created_at") and user.created_at:
            created = user.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            ur.days_active = (datetime.now(timezone.utc) - created).days
    except Exception:
        ur.days_active = ur.total_checkins  # rough fallback

    # Streak
    ur.streak_days = _compute_streak_from_snapshots(snapshots)

    # Get recent responses for quality analysis
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    recent_responses = (
        db.query(CheckInResponse)
        .filter(
            and_(
                CheckInResponse.user_id == user_id,
                CheckInResponse.checkin_date >= cutoff,
                CheckInResponse.dimension != "conversation_theme",
            )
        )
        .order_by(CheckInResponse.checkin_date.asc())
        .all()
    )

    # Group responses into sessions (by date)
    sessions = _group_into_sessions(recent_responses)
    session_qualities = [validate_session(s) for s in sessions]

    if session_qualities:
        ur.avg_session_quality = (
            sum(sq.quality_score for sq in session_qualities) / len(session_qualities)
        )
        consistent_sessions = sum(
            1 for sq in session_qualities if sq.consistency_score >= 0.7
        )
        ur.consistency_ratio = consistent_sessions / len(session_qualities)

    # --- Compute composite reliability score ---
    # Tenure factor: ramp up over first 14 days
    tenure_factor = min(1.0, ur.days_active / 14) if ur.days_active else 0.0

    # Volume factor: ramp up over first 10 check-ins
    volume_factor = min(1.0, ur.total_checkins / 10)

    # Engagement factor: streak and regularity
    engagement_factor = 0.0
    if ur.total_checkins > 0 and ur.days_active > 0:
        regularity = ur.total_checkins / max(ur.days_active, 1)
        engagement_factor = min(1.0, regularity * 2)  # checking in every other day = 1.0

    ur.reliability_score = (
        tenure_factor * 0.15
        + volume_factor * 0.25
        + ur.avg_session_quality * 0.30
        + ur.consistency_ratio * 0.15
        + engagement_factor * 0.15
    )

    # Eligibility check
    ur.is_index_eligible = (
        ur.total_checkins >= MIN_CHECKINS_FOR_INDEX
        and ur.reliability_score >= MIN_RELIABILITY_FOR_INDEX
    )

    if not ur.is_index_eligible:
        if ur.total_checkins < MIN_CHECKINS_FOR_INDEX:
            ur.flags.append("insufficient_checkins")
        if ur.reliability_score < MIN_RELIABILITY_FOR_INDEX:
            ur.flags.append("low_reliability")

    return ur


def _group_into_sessions(responses: List[CheckInResponse]) -> List[List[CheckInResponse]]:
    """Group responses into daily sessions."""
    sessions = {}
    for r in responses:
        d = r.checkin_date
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        date_key = d.date()
        if date_key not in sessions:
            sessions[date_key] = []
        sessions[date_key].append(r)
    return list(sessions.values())


def _compute_streak_from_snapshots(snapshots: List[UserMetricSnapshot]) -> int:
    """Streak calculation from snapshots."""
    if not snapshots:
        return 0

    today = datetime.now(timezone.utc).date()
    snapshot_dates = set()
    for s in snapshots:
        d = s.computed_at
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        snapshot_dates.add(d.date())

    streak = 0
    check_date = today
    while check_date in snapshot_dates:
        streak += 1
        check_date -= timedelta(days=1)
    return streak


# ============================================================
#  3. OUTLIER DETECTION
#     Statistical filters before index aggregation
# ============================================================

def detect_outlier_snapshots(
    snapshots: List[UserMetricSnapshot],
    threshold: float = OUTLIER_STDDEV_THRESHOLD,
) -> List[int]:
    """
    Identify snapshots that are statistical outliers.
    Returns list of snapshot IDs to exclude from index computation.

    Uses z-score method on FCS composite:
      - Compute mean and stddev across all snapshots
      - Flag any snapshot more than `threshold` stddevs from mean
    """
    if len(snapshots) < 10:
        return []  # need enough data for meaningful statistics

    fcs_values = [s.fcs_composite for s in snapshots]
    mean_fcs = sum(fcs_values) / len(fcs_values)
    variance = sum((x - mean_fcs) ** 2 for x in fcs_values) / len(fcs_values)
    stddev = variance ** 0.5

    if stddev < 1.0:
        return []  # data is tight, no real outliers

    outlier_ids = []
    for s in snapshots:
        z_score = abs(s.fcs_composite - mean_fcs) / stddev
        if z_score > threshold:
            outlier_ids.append(s.id)

    return outlier_ids


def detect_dimension_outliers(
    snapshots: List[UserMetricSnapshot],
    threshold: float = OUTLIER_STDDEV_THRESHOLD,
) -> Dict[str, List[int]]:
    """
    Detect outliers per dimension, not just composite FCS.
    Returns dict of dimension -> list of outlier snapshot IDs.
    """
    if len(snapshots) < 10:
        return {}

    dimensions = ["current_stability", "future_outlook", "purchasing_power",
                   "debt_pressure", "financial_agency"]

    outliers = {}
    for dim in dimensions:
        values = [getattr(s, dim, 0.0) for s in snapshots]
        mean_val = sum(values) / len(values)
        variance = sum((x - mean_val) ** 2 for x in values) / len(values)
        stddev = variance ** 0.5

        if stddev < 0.01:
            continue

        dim_outliers = []
        for i, s in enumerate(snapshots):
            z_score = abs(values[i] - mean_val) / stddev
            if z_score > threshold:
                dim_outliers.append(s.id)

        if dim_outliers:
            outliers[dim] = dim_outliers

    return outliers


# ============================================================
#  4. INDEX-READY DATA EXPORT
#     Only clean, weighted, eligible data reaches the GF-RWI
# ============================================================

def get_index_eligible_snapshots(
    db: Session,
    hours: int = 24,
) -> List[Tuple[UserMetricSnapshot, float]]:
    """
    Get snapshots eligible for index computation with reliability weights.

    Returns list of (snapshot, weight) tuples where weight is 0.0 - 1.0
    based on the user's reliability score.

    Filters:
      1. Only snapshots from the last `hours` hours
      2. Only users with MIN_CHECKINS_FOR_INDEX+ check-ins
      3. Only users with reliability >= MIN_RELIABILITY_FOR_INDEX
      4. Excludes statistical outliers
      5. Each snapshot weighted by user reliability

    Use this INSTEAD of raw snapshot queries in index_engine_service.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=hours)

    # Pull all recent snapshots
    snapshots = (
        db.query(UserMetricSnapshot)
        .filter(UserMetricSnapshot.computed_at >= window_start)
        .all()
    )

    if not snapshots:
        return []

    # Get unique user IDs
    user_ids = set(s.user_id for s in snapshots)

    # Compute reliability for each user
    user_reliability = {}
    for uid in user_ids:
        ur = compute_user_reliability(db, uid)
        if ur.is_index_eligible:
            user_reliability[uid] = ur.reliability_score

    # Filter to eligible users only
    eligible_snapshots = [
        s for s in snapshots if s.user_id in user_reliability
    ]

    if not eligible_snapshots:
        return []

    # Detect and exclude outliers
    outlier_ids = set(detect_outlier_snapshots(eligible_snapshots))
    dim_outliers = detect_dimension_outliers(eligible_snapshots)
    for dim, ids in dim_outliers.items():
        outlier_ids.update(ids)

    # Build final weighted list
    result = []
    for s in eligible_snapshots:
        if s.id in outlier_ids:
            continue

        weight = user_reliability.get(s.user_id, 0.0)
        result.append((s, weight))

    return result


def compute_weighted_index(
    db: Session,
    segment: str = "national",
) -> Optional[DailyIndex]:
    """
    Compute the GF-RWI using quality-weighted data.
    Drop-in replacement for index_engine_service.compute_daily_index().

    Differences from the original:
      - Only includes index-eligible users
      - Weights each user's contribution by reliability score
      - Excludes statistical outliers
      - Records quality metadata
    """
    now = datetime.now(timezone.utc)

    weighted_snapshots = get_index_eligible_snapshots(db, hours=24)

    if not weighted_snapshots:
        # No eligible data — save a zero index
        index = DailyIndex(
            index_date=now,
            segment=segment,
            fcs_value=0.0,
            user_count=0,
            computed_at=now,
        )
        db.add(index)
        db.commit()
        db.refresh(index)
        return index

    # Weighted averages for each dimension
    total_weight = sum(w for _, w in weighted_snapshots)
    if total_weight == 0:
        total_weight = 1.0  # prevent division by zero

    def weighted_avg(attr):
        return sum(
            getattr(s, attr, 0.0) * w for s, w in weighted_snapshots
        ) / total_weight

    avg_cs = weighted_avg("current_stability")
    avg_fo = weighted_avg("future_outlook")
    avg_pp = weighted_avg("purchasing_power")
    avg_er = weighted_avg("debt_pressure")
    avg_ia = weighted_avg("financial_agency")

    # Weighted FCS composite
    fcs_value = weighted_avg("fcs_composite")

    # Weighted BSI (only from snapshots that have it)
    bsi_pairs = [(s, w) for s, w in weighted_snapshots if s.bsi_score is not None]
    bsi_value = None
    if bsi_pairs:
        bsi_total_weight = sum(w for _, w in bsi_pairs)
        if bsi_total_weight > 0:
            bsi_value = sum(s.bsi_score * w for s, w in bsi_pairs) / bsi_total_weight

    # Compute GF-RWI composite
    WEIGHT_FCS = 0.60
    WEIGHT_BSI = 0.40
    if bsi_value is not None:
        bsi_normalized = (bsi_value + 100) / 2
        gf_rwi = (WEIGHT_FCS * fcs_value) + (WEIGHT_BSI * bsi_normalized)
    else:
        gf_rwi = fcs_value

    user_count = len(set(s.user_id for s, _ in weighted_snapshots))

    index = DailyIndex(
        index_date=now,
        segment=segment,
        spi_value=None,  # Phase 2
        fcs_value=round(fcs_value, 2),
        bsi_value=round(bsi_value, 2) if bsi_value is not None else None,
        fcs_current_stability=round(avg_cs, 4),
        fcs_future_outlook=round(avg_fo, 4),
        fcs_purchasing_power=round(avg_pp, 4),
        fcs_debt_pressure=round(avg_er, 4),
        fcs_financial_agency=round(avg_ia, 4),
        gf_rwi_composite=round(gf_rwi, 2),
        user_count=user_count,
        computed_at=now,
    )

    db.add(index)
    db.commit()
    db.refresh(index)
    return index


# ============================================================
#  5. DATA HEALTH DASHBOARD
#     Metrics for monitoring data quality over time
# ============================================================

def get_data_health_report(db: Session, days: int = 7) -> Dict:
    """
    Generate a data quality health report for the admin dashboard.
    Shows how clean the data feeding the index actually is.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Total responses in period
    total_responses = (
        db.query(func.count(CheckInResponse.id))
        .filter(
            and_(
                CheckInResponse.checkin_date >= cutoff,
                CheckInResponse.dimension != "conversation_theme",
            )
        )
        .scalar() or 0
    )

    # Unique users who checked in
    active_users = (
        db.query(func.count(func.distinct(CheckInResponse.user_id)))
        .filter(
            and_(
                CheckInResponse.checkin_date >= cutoff,
                CheckInResponse.dimension != "conversation_theme",
            )
        )
        .scalar() or 0
    )

    # Snapshots in period
    snapshots = (
        db.query(UserMetricSnapshot)
        .filter(UserMetricSnapshot.computed_at >= cutoff)
        .all()
    )

    # Get all responses for quality analysis
    responses = (
        db.query(CheckInResponse)
        .filter(
            and_(
                CheckInResponse.checkin_date >= cutoff,
                CheckInResponse.dimension != "conversation_theme",
            )
        )
        .order_by(CheckInResponse.checkin_date.asc())
        .all()
    )

    # Group into sessions per user per day
    user_sessions = {}
    for r in responses:
        d = r.checkin_date
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        key = (r.user_id, d.date())
        if key not in user_sessions:
            user_sessions[key] = []
        user_sessions[key].append(r)

    # Validate each session
    quality_scores = []
    flagged_sessions = 0
    flag_counts = {}

    for key, session_responses in user_sessions.items():
        sq = validate_session(session_responses)
        quality_scores.append(sq.quality_score)
        if sq.flags:
            flagged_sessions += 1
            for flag in sq.flags:
                flag_counts[flag] = flag_counts.get(flag, 0) + 1

    # Eligible users for index
    eligible_count = 0
    if active_users > 0:
        user_ids = set(r.user_id for r in responses)
        for uid in user_ids:
            ur = compute_user_reliability(db, uid)
            if ur.is_index_eligible:
                eligible_count += 1

    # Outlier count
    outlier_count = len(detect_outlier_snapshots(snapshots)) if snapshots else 0

    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

    return {
        "period_days": days,
        "total_responses": total_responses,
        "active_users": active_users,
        "index_eligible_users": eligible_count,
        "total_sessions": len(user_sessions),
        "avg_session_quality": round(avg_quality, 3),
        "flagged_sessions": flagged_sessions,
        "flagged_percentage": round(
            flagged_sessions / max(len(user_sessions), 1) * 100, 1
        ),
        "flag_breakdown": flag_counts,
        "outlier_snapshots": outlier_count,
        "snapshots_in_period": len(snapshots),
        "data_health_score": round(
            avg_quality * (1 - flagged_sessions / max(len(user_sessions), 1)), 3
        ),
    }