"""
GraceFinance Intelligence Engine
=================================
Central nervous system that connects every data source into one
unified intelligence layer for Grace and the dashboard.

UPDATED: Now delegates heavy lifting to the 3-stream behavioral engine.
This file retains:
  - log_conversation_themes() — used by grace_service.py
  - generate_proactive_insights() — used by grace_service.py + get_grace_intro()
  - compute_index_trend_fields() — used by nightly index job
  - build_grace_context() — kept for backward compat, delegates to behavioral engine
  - detect_conversation_themes() — kept for backward compat, delegates to NLP stream
  - Shared utilities (compute_fcs_trend, compute_streak, _ols_slope, etc.)

Place at: app/services/intelligence_engine.py
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from app.models.checkin import CheckInResponse, UserMetricSnapshot, DailyIndex
from app.services.checkin_service import FCS_WEIGHTS, get_user_metric_history
from app.services.index_engine_service import get_latest_index, get_index_history


# ============================================================
#  DIMENSION METADATA
#  Single source of truth for labels, tips, icons
# ============================================================

DIMENSION_META = {
    "current_stability": {
        "label": "Current Stability",
        "weight": FCS_WEIGHTS["current_stability"],
        "tip": "Set up autopay for your biggest bills. Knowing they're covered reduces stress instantly.",
    },
    "future_outlook": {
        "label": "Future Outlook",
        "weight": FCS_WEIGHTS["future_outlook"],
        "tip": "Write down one financial goal you want to hit in 90 days. Clarity drives confidence.",
    },
    "purchasing_power": {
        "label": "Purchasing Power",
        "weight": FCS_WEIGHTS["purchasing_power"],
        "tip": "Track 3 grocery swaps this week. Small wins add up to big savings.",
    },
    "debt_pressure": {
        "label": "Debt Pressure",
        "weight": FCS_WEIGHTS["debt_pressure"],
        "tip": "Open a separate savings account and auto-transfer even $10/week. Start the habit.",
    },
    "financial_agency": {
        "label": "Financial Agency",
        "weight": FCS_WEIGHTS["financial_agency"],
        "tip": "List one skill you could develop in 6 months that would increase your earning power.",
    },
}


# ============================================================
#  1. GRACE CONTEXT BUILDER
#     Now delegates to behavioral engine. Kept for backward compat.
# ============================================================

def build_grace_context(db: Session, user_id: int, messages: List[Dict] = None) -> str:
    """
    Build comprehensive context string from ALL data sources.

    UPDATED: Delegates to the 3-stream behavioral engine.
    If the behavioral engine isn't available (import error), falls back
    to the legacy implementation.

    Args:
        db: Database session
        user_id: Current user's ID
        messages: Optional conversation messages for NLP stream
    """
    try:
        from app.services.behavioral_engine import UserProfileBuilder
        profile = UserProfileBuilder().build(db, user_id, messages or [])
        return profile.to_grace_context()
    except ImportError:
        # Fallback to legacy if behavioral engine isn't installed yet
        return _legacy_build_grace_context(db, user_id)


def _legacy_build_grace_context(db: Session, user_id: int) -> str:
    """Original context builder — fallback if behavioral engine unavailable."""
    lines = []

    user_name = _get_user_name(db, user_id)
    days_active = _get_days_active(db, user_id)
    if user_name:
        lines.append(f"User: {user_name}")
    if days_active is not None:
        lines.append(f"Active for {days_active} day{'s' if days_active != 1 else ''}")

    snapshots = get_user_metric_history(db, user_id, days=30)

    if not snapshots:
        lines.append("No check-in data yet — this is a new user.")
        return _format_context(lines)

    latest = snapshots[-1]
    fcs = round(latest.fcs_composite, 1)

    dims = _extract_dimensions(latest)
    sorted_dims = sorted(dims.items(), key=lambda x: x[1])
    weakest_key, weakest_val = sorted_dims[0]
    strongest_key, strongest_val = sorted_dims[-1]

    lines.append(f"FCS Score: {fcs}/100")
    lines.append("Dimensions: " + ", ".join(
        f"{DIMENSION_META[k]['label']}: {v}%" for k, v in dims.items()
    ))
    lines.append(f"Weakest: {DIMENSION_META[weakest_key]['label']} at {weakest_val}%")
    lines.append(f"Strongest: {DIMENSION_META[strongest_key]['label']} at {strongest_val}%")
    lines.append(f"Check-ins recorded: {latest.checkin_count}")

    if latest.bsi_score is not None:
        bsi = round(latest.bsi_score, 1)
        if bsi > 20:
            bsi_label = "expansionary — spending freely, feeling confident"
        elif bsi < -20:
            bsi_label = "contractionary — cutting back, stress-driven changes"
        else:
            bsi_label = "neutral — steady behavior patterns"
        lines.append(f"BSI: {bsi} ({bsi_label})")

    trend = compute_fcs_trend(snapshots)
    if trend:
        lines.append(f"FCS Trend: {trend['direction']} — {trend['description']}")

    streak = compute_streak(snapshots)
    if streak > 0:
        lines.append(f"Check-in streak: {streak} day{'s' if streak != 1 else ''}")
    elif len(snapshots) >= 2:
        last_date = snapshots[-1].computed_at
        if last_date.tzinfo is None:
            last_date = last_date.replace(tzinfo=timezone.utc)
        gap = (datetime.now(timezone.utc) - last_date).days
        if gap >= 2:
            lines.append(f"Last check-in was {gap} days ago — streak broken")

    patterns = _legacy_detect_patterns(db, user_id, snapshots)
    if patterns:
        lines.append("Active alerts: " + "; ".join(patterns))

    peer = _build_peer_comparison(db, latest)
    if peer:
        lines.append(peer)

    themes = _get_recent_themes(db, user_id)
    if themes:
        lines.append("Recent topics they've discussed: " + ", ".join(themes))

    return _format_context(lines)


def _format_context(lines: List[str]) -> str:
    """Wrap context lines in an instruction block for the system prompt."""
    if not lines:
        return ""
    return (
        "\n\n[USER CONTEXT — reference naturally in coaching, "
        "don't recite back verbatim]\n"
        + "\n".join(f"  {line}" for line in lines)
    )


# ============================================================
#  2. PATTERN DETECTION
#     Now delegates to behavioral engine. Legacy kept as fallback.
# ============================================================

def detect_patterns(
    db: Session,
    user_id: int,
    snapshots: Optional[List[UserMetricSnapshot]] = None,
) -> List[str]:
    """
    Analyze snapshot history for patterns worth addressing.

    UPDATED: Delegates to behavioral engine's pattern detector.
    Falls back to legacy if behavioral engine unavailable.
    """
    try:
        from app.services.behavioral_engine import UserProfileBuilder
        profile = UserProfileBuilder().build_quick(db, user_id)
        alerts = []
        # Convert behavioral engine signals to plain-English alerts
        for signal in profile.registry.negative_signals():
            alerts.append(signal.label)
        # Add cross-stream pattern descriptions
        for pattern in profile.patterns:
            alerts.append(pattern.description)
        return alerts[:10]  # Cap at 10 alerts
    except ImportError:
        return _legacy_detect_patterns(db, user_id, snapshots)


def _legacy_detect_patterns(
    db: Session,
    user_id: int,
    snapshots: Optional[List[UserMetricSnapshot]] = None,
) -> List[str]:
    """Original pattern detection — fallback if behavioral engine unavailable."""
    if snapshots is None:
        snapshots = get_user_metric_history(db, user_id, days=14)

    if not snapshots:
        return []

    alerts = []
    latest = snapshots[-1]

    if len(snapshots) >= 2:
        week_ago_idx = max(0, len(snapshots) - 7)
        older = snapshots[week_ago_idx]

        for dim_key in DIMENSION_META:
            current_val = getattr(latest, dim_key, 0.0)
            older_val = getattr(older, dim_key, 0.0)
            if older_val > 0.05:
                drop_pct = (older_val - current_val) / older_val * 100
                if drop_pct >= 15:
                    alerts.append(
                        f"{DIMENSION_META[dim_key]['label']} dropped {drop_pct:.0f}% this week"
                    )

    if len(snapshots) >= 3:
        last_three = [s.fcs_composite for s in snapshots[-3:]]
        if last_three[0] > last_three[1] > last_three[2]:
            alerts.append("FCS has declined for 3 consecutive check-ins")

    if latest.bsi_score is not None and latest.bsi_score < -30:
        alerts.append("BSI indicates significant stress-driven behavior changes")

    if latest.debt_pressure < 0.3 and latest.current_stability < 0.4:
        alerts.append("Both Debt Pressure and stability are critically low")

    if len(snapshots) >= 5:
        recent_fcs = [s.fcs_composite for s in snapshots[-5:]]
        mean_fcs = sum(recent_fcs) / len(recent_fcs)
        variance = sum((x - mean_fcs) ** 2 for x in recent_fcs) / len(recent_fcs)
        if variance > 100:
            alerts.append("FCS scores are fluctuating significantly — possible instability")

    if len(snapshots) >= 3:
        last_three = [s.fcs_composite for s in snapshots[-3:]]
        if last_three[0] < last_three[1] < last_three[2]:
            gain = last_three[2] - last_three[0]
            if gain >= 5:
                alerts.append(f"Strong upward momentum: +{gain:.1f} over last 3 check-ins")

    dims = _extract_dimensions(latest)
    if all(v < 50 for v in dims.values()):
        alerts.append("All dimensions are below 50% — user may need extra encouragement")

    return alerts


# ============================================================
#  3. PROACTIVE INSIGHTS
#     Still lives here — used directly by grace_service.py
# ============================================================

def generate_proactive_insights(db: Session, user_id: int) -> List[Dict]:
    """
    Generate coaching insights Grace can weave into conversation.
    Each insight has type, priority (high/medium/low), and message.
    """
    snapshots = get_user_metric_history(db, user_id, days=14)
    insights = []

    if not snapshots:
        insights.append({
            "type": "onboarding",
            "priority": "high",
            "message": "New user with no check-in data. Make the first check-in feel valuable and low-pressure.",
        })
        return insights

    latest = snapshots[-1]
    streak = compute_streak(snapshots)

    # Streak milestones
    if streak == 3:
        insights.append({
            "type": "streak",
            "priority": "medium",
            "message": "User hit a 3-day check-in streak. Acknowledge the consistency.",
        })
    elif streak == 7:
        insights.append({
            "type": "streak",
            "priority": "high",
            "message": "7-day streak! This is a real milestone — celebrate it.",
        })
    elif streak >= 14:
        insights.append({
            "type": "streak",
            "priority": "high",
            "message": f"{streak}-day streak. This user is committed. Talk about compounding habits.",
        })
    elif streak == 0 and len(snapshots) >= 3:
        insights.append({
            "type": "re_engagement",
            "priority": "medium",
            "message": "User's check-in streak broke. Welcome them back warmly, no guilt.",
        })

    # Weakest dimension coaching
    dims = _extract_dimensions(latest)
    weakest_key = min(dims, key=dims.get)
    weakest_val = dims[weakest_key]
    if weakest_val < 40:
        meta = DIMENSION_META[weakest_key]
        insights.append({
            "type": "dimension_focus",
            "priority": "high",
            "message": f"User's {meta['label']} is at {weakest_val}%. Coaching tip: {meta['tip']}",
        })

    # BSI behavioral shift
    if latest.bsi_score is not None:
        if latest.bsi_score < -40:
            insights.append({
                "type": "behavioral_stress",
                "priority": "high",
                "message": (
                    "BSI is heavily contractionary. User is cutting spending, "
                    "substituting credit, or hoarding cash. Approach with empathy."
                ),
            })
        elif latest.bsi_score > 40:
            insights.append({
                "type": "behavioral_expansion",
                "priority": "medium",
                "message": (
                    "BSI is expansionary. User feels financially comfortable. "
                    "Good time to discuss longer-term goals."
                ),
            })

    # FCS milestone crossings
    if latest.fcs_composite >= 70 and len(snapshots) >= 3:
        older = [s.fcs_composite for s in snapshots[-4:-1]]
        if older and all(s < 70 for s in older):
            insights.append({
                "type": "milestone",
                "priority": "high",
                "message": "User just crossed into Strong FCS territory (70+) for the first time!",
            })

    if latest.fcs_composite >= 50 and len(snapshots) >= 3:
        older = [s.fcs_composite for s in snapshots[-4:-1]]
        if older and all(s < 50 for s in older):
            insights.append({
                "type": "milestone",
                "priority": "medium",
                "message": "User crossed the 50-point Building threshold. Momentum is real.",
            })

    return insights


# ============================================================
#  4. CONVERSATION THEME DETECTION + LOGGING
#     detect_conversation_themes now delegates to NLP stream.
#     log_conversation_themes stays here — used by grace_service.py.
# ============================================================

def detect_conversation_themes(messages: List[Dict]) -> List[str]:
    """
    Scan user messages for theme keywords.

    UPDATED: Delegates to behavioral engine's NLP stream.
    Falls back to legacy keyword matching if unavailable.
    """
    try:
        from app.services.behavioral_engine import GraceNLPStream
        nlp = GraceNLPStream()
        user_text = " ".join(
            m.get("content", "")
            for m in messages
            if m.get("role") == "user"
        )
        themes = nlp.extract_themes(user_text)
        return [t["theme"] for t in themes]
    except ImportError:
        return _legacy_detect_themes(messages)


# Legacy keyword map kept for fallback
THEME_KEYWORDS = {
    "debt_stress": ["debt", "owe", "credit card", "balance", "payment", "behind", "minimum"],
    "savings_goals": ["save", "savings", "emergency fund", "rainy day", "put away", "set aside"],
    "income_concern": ["paycheck", "salary", "raise", "income", "not enough", "underpaid", "hours"],
    "spending_guilt": ["overspent", "impulse", "shouldn't have", "regret", "guilty", "blew"],
    "goal_setting": ["goal", "plan", "target", "milestone", "want to", "trying to"],
    "confusion": ["confused", "don't understand", "what does", "explain", "how does", "what is"],
    "celebration": ["paid off", "milestone", "achieved", "proud", "progress", "hit my"],
    "anxiety": ["stressed", "worried", "anxious", "scared", "overwhelmed", "panic", "can't sleep"],
    "housing": ["rent", "mortgage", "house", "apartment", "lease", "landlord", "down payment"],
    "family": ["kids", "family", "partner", "spouse", "childcare", "diapers", "baby"],
}


def _legacy_detect_themes(messages: List[Dict]) -> List[str]:
    """Original theme detection — fallback if behavioral engine unavailable."""
    user_text = " ".join(
        m.get("content", "").lower()
        for m in messages
        if m.get("role") == "user"
    )

    detected = []
    for theme, keywords in THEME_KEYWORDS.items():
        if any(kw in user_text for kw in keywords):
            detected.append(theme)

    return detected


def log_conversation_themes(db: Session, user_id: int, themes: List[str]):
    """
    Persist detected conversation themes using CheckInResponse table
    with dimension='conversation_theme'. Deduplicates same-day entries.
    """
    if not themes:
        return

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    for theme in themes:
        existing = (
            db.query(CheckInResponse)
            .filter(
                and_(
                    CheckInResponse.user_id == user_id,
                    CheckInResponse.question_id == f"CONV-{theme}",
                    CheckInResponse.checkin_date >= today_start,
                )
            )
            .first()
        )
        if existing:
            continue

        record = CheckInResponse(
            user_id=user_id,
            question_id=f"CONV-{theme}",
            dimension="conversation_theme",
            question_text=theme,
            raw_value=1,
            scale_max=1,
            normalized_value=1.0,
            checkin_date=now,
            is_weekly=False,
        )
        db.add(record)

    try:
        db.commit()
    except Exception:
        db.rollback()


# ============================================================
#  5. INDEX ENGINE ENHANCEMENTS
#     Unchanged — compute slope, volatility, trend for daily_indexes
# ============================================================

def compute_index_trend_fields(db: Session, segment: str = "national") -> Optional[Dict]:
    """
    Compute gci_slope_3d, gci_slope_7d, gci_volatility_7d,
    and trend_direction for the latest DailyIndex row.

    Call AFTER compute_daily_index() to populate the v1.1 columns.
    """
    history = get_index_history(db, segment=segment, days=10)

    if len(history) < 3:
        return None

    gci_values = [
        float(h.gf_rwi_composite) if h.gf_rwi_composite else 0.0
        for h in history
    ]

    result = {}

    if len(gci_values) >= 3:
        result["gci_slope_3d"] = round(_ols_slope(gci_values[-3:]), 4)

    if len(gci_values) >= 7:
        result["gci_slope_7d"] = round(_ols_slope(gci_values[-7:]), 4)
    else:
        result["gci_slope_7d"] = result.get("gci_slope_3d")

    window = gci_values[-7:] if len(gci_values) >= 7 else gci_values
    mean_gci = sum(window) / len(window)
    variance = sum((x - mean_gci) ** 2 for x in window) / len(window)
    result["gci_volatility_7d"] = round(variance ** 0.5, 4)

    slope = result.get("gci_slope_7d") or result.get("gci_slope_3d", 0)
    if slope > 0.5:
        result["trend_direction"] = "UP"
    elif slope < -0.5:
        result["trend_direction"] = "DOWN"
    else:
        result["trend_direction"] = "FLAT"

    latest_index = (
        db.query(DailyIndex)
        .filter(DailyIndex.segment == segment)
        .order_by(DailyIndex.index_date.desc())
        .first()
    )

    if latest_index:
        latest_index.gci_slope_3d = result.get("gci_slope_3d")
        latest_index.gci_slope_7d = result.get("gci_slope_7d")
        latest_index.gci_volatility_7d = result.get("gci_volatility_7d")
        latest_index.trend_direction = result.get("trend_direction")
        db.commit()

    return result


# ============================================================
#  6. SHARED UTILITIES — Unchanged
# ============================================================

def compute_fcs_trend(snapshots: List[UserMetricSnapshot]) -> Optional[Dict]:
    """FCS trend direction from snapshot history using OLS slope."""
    if len(snapshots) < 3:
        return None

    fcs_values = [s.fcs_composite for s in snapshots[-7:]]
    slope = _ols_slope(fcs_values)

    if slope > 1.0:
        return {"direction": "UP", "description": f"improving ~{slope:.1f} pts/day"}
    elif slope < -1.0:
        return {"direction": "DOWN", "description": f"declining ~{abs(slope):.1f} pts/day"}
    else:
        return {"direction": "STABLE", "description": "holding steady"}


def compute_streak(snapshots: List[UserMetricSnapshot]) -> int:
    """Consecutive daily check-in streak counting back from today."""
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


def _ols_slope(values: List[float]) -> float:
    """OLS slope: x-axis is index, y-axis is values."""
    n = len(values)
    if n < 2:
        return 0.0

    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n

    numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    return numerator / denominator if denominator != 0 else 0.0


def _extract_dimensions(snapshot: UserMetricSnapshot) -> Dict[str, int]:
    """Extract 5 FCS dimensions as integer percentages from a snapshot."""
    return {
        "current_stability": round(snapshot.current_stability * 100),
        "future_outlook": round(snapshot.future_outlook * 100),
        "purchasing_power": round(snapshot.purchasing_power * 100),
        "debt_pressure": round(snapshot.debt_pressure * 100),
        "financial_agency": round(snapshot.financial_agency * 100),
    }


def _get_user_name(db: Session, user_id: int) -> Optional[str]:
    try:
        from app.models import User
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return getattr(user, "first_name", None) or getattr(user, "name", None)
    except Exception:
        pass
    return None


def _get_days_active(db: Session, user_id: int) -> Optional[int]:
    try:
        from app.models import User
        user = db.query(User).filter(User.id == user_id).first()
        if user and hasattr(user, "created_at") and user.created_at:
            created = user.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - created).days
    except Exception:
        pass
    return None


def _build_peer_comparison(db: Session, latest_snapshot: UserMetricSnapshot) -> Optional[str]:
    """Compare user's FCS to platform average from GF-RWI."""
    index = get_latest_index(db)
    if index is None or index.user_count < 5:
        return None

    user_fcs = latest_snapshot.fcs_composite
    platform_fcs = index.fcs_value

    diff = user_fcs - platform_fcs
    if abs(diff) < 3:
        position = "right around the platform average"
    elif diff > 0:
        position = f"{abs(diff):.0f} points above the platform average"
    else:
        position = f"{abs(diff):.0f} points below the platform average"

    return f"Peer context: User's FCS is {position} (platform avg: {platform_fcs:.1f}, {index.user_count} users)"


def _get_recent_themes(db: Session, user_id: int) -> List[str]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    try:
        records = (
            db.query(CheckInResponse.question_text)
            .filter(
                and_(
                    CheckInResponse.user_id == user_id,
                    CheckInResponse.dimension == "conversation_theme",
                    CheckInResponse.checkin_date >= cutoff,
                )
            )
            .distinct()
            .all()
        )
        return [r[0].replace("_", " ") for r in records]
    except Exception:
        return []
