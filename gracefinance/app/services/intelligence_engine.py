"""
GraceFinance Intelligence Engine — v3.0
════════════════════════════════════════
CHANGES FROM v2.0:
  - debt_pressure REMOVED from all dimension references
  - emergency_readiness ADDED at 15%
  - _extract_dimensions() updated to match locked pillar set
  - FCS confidence band surfaced in Grace context
  - BSI shock flag surfaced in proactive insights
  - DIMENSION_META is now the single source of truth
    (imported from question_bank, not duplicated here)

Place at: app/services/intelligence_engine.py
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.checkin import CheckInResponse, UserMetricSnapshot, DailyIndex
from app.services.checkin_service import FCS_WEIGHTS, get_user_metric_history
from app.services.question_bank import DIMENSION_META
from app.services.index_engine_service import get_latest_index, get_index_history


# ══════════════════════════════════════════
#  FCS LABEL HELPER
# ══════════════════════════════════════════

def _fcs_label(score: float) -> str:
    if score >= 80: return "Thriving"
    if score >= 65: return "Strong"
    if score >= 50: return "Building"
    if score >= 35: return "Growing"
    if score >= 20: return "Struggling"
    return "Critical"


# ══════════════════════════════════════════
#  1. GRACE CONTEXT BUILDER
# ══════════════════════════════════════════

def build_grace_context(db: Session, user_id, messages: List[Dict] = None) -> str:
    """
    Build comprehensive context string for Grace AI system prompt.
    Delegates to 3-stream behavioral engine if available.
    Falls back to legacy if not.
    """
    try:
        from app.services.behavioral_engine import UserProfileBuilder
        profile = UserProfileBuilder().build(db, user_id, messages or [])
        return profile.to_grace_context()
    except ImportError:
        return _legacy_build_grace_context(db, user_id)


def _legacy_build_grace_context(db: Session, user_id) -> str:
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

    # ── FCS Score + Confidence ───────────────────────────────────────────────
    if latest.fcs_composite is not None:
        fcs = round(latest.fcs_composite, 1)
        label = _fcs_label(fcs)
        confidence = getattr(latest, "fcs_confidence", None)

        if confidence is not None and confidence < 60:
            lines.append(
                f"FCS Score: {fcs}/100 ({label}) — "
                f"LOW CONFIDENCE ({confidence:.0f}% data coverage, "
                f"only {_covered_dimensions(latest)}/{len(FCS_WEIGHTS)} dimensions answered)"
            )
        else:
            lines.append(f"FCS Score: {fcs}/100 ({label})")

        # Raw vs smoothed transparency for Grace
        fcs_raw = getattr(latest, "fcs_raw", None)
        if fcs_raw is not None and abs(fcs_raw - fcs) > 3:
            lines.append(
                f"  → Today's raw score: {fcs_raw:.1f} "
                f"(EMA-smoothed to {fcs:.1f} — reflects behavioral trend, not single session)"
            )
    else:
        lines.append("FCS Score: Insufficient data (fewer than 2 dimensions answered)")

    # ── Dimension Breakdown ──────────────────────────────────────────────────
    dims = _extract_dimensions(latest)
    if dims:
        dim_str = ", ".join(
            f"{DIMENSION_META[k]['label']}: {v}%"
            for k, v in dims.items()
            if v is not None
        )
        lines.append(f"Dimensions: {dim_str}")

        answered = {k: v for k, v in dims.items() if v is not None}
        if answered:
            weakest_key = min(answered, key=answered.get)
            strongest_key = max(answered, key=answered.get)
            lines.append(
                f"Weakest: {DIMENSION_META[weakest_key]['label']} at {answered[weakest_key]}%"
            )
            lines.append(
                f"Strongest: {DIMENSION_META[strongest_key]['label']} at {answered[strongest_key]}%"
            )

    # ── BSI ──────────────────────────────────────────────────────────────────
    if latest.bsi_score is not None:
        bsi = round(latest.bsi_score, 1)
        bsi_shock = getattr(latest, "bsi_shock", False)

        if bsi > 20:
            bsi_label = "expansionary — spending freely, feeling confident"
        elif bsi < -20:
            bsi_label = "contractionary — cutting back, stress-driven changes"
        else:
            bsi_label = "neutral — steady behavior patterns"

        shock_note = " ⚡ BEHAVIORAL SHIFT EVENT DETECTED" if bsi_shock else ""
        lines.append(f"BSI: {bsi} ({bsi_label}){shock_note}")

    # ── Trend ────────────────────────────────────────────────────────────────
    trend = compute_fcs_trend(snapshots)
    if trend:
        lines.append(f"FCS Trend (7d): {trend['direction']} — {trend['description']}")

    # ── Streak ───────────────────────────────────────────────────────────────
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

    # ── Active Alerts ────────────────────────────────────────────────────────
    patterns = _legacy_detect_patterns(db, user_id, snapshots)
    if patterns:
        lines.append("Active alerts: " + "; ".join(patterns))

    # ── Peer Comparison ──────────────────────────────────────────────────────
    peer = _build_peer_comparison(db, latest)
    if peer:
        lines.append(peer)

    # ── Conversation Themes ──────────────────────────────────────────────────
    themes = _get_recent_themes(db, user_id)
    if themes:
        lines.append("Recent topics discussed: " + ", ".join(themes))

    return _format_context(lines)


def _format_context(lines: List[str]) -> str:
    if not lines:
        return ""
    return (
        "\n\n[USER CONTEXT — reference naturally in coaching, "
        "don't recite back verbatim]\n"
        + "\n".join(f"  {line}" for line in lines)
    )


# ══════════════════════════════════════════
#  2. PATTERN DETECTION
# ══════════════════════════════════════════

def detect_patterns(
    db: Session,
    user_id,
    snapshots: Optional[List[UserMetricSnapshot]] = None,
) -> List[str]:
    try:
        from app.services.behavioral_engine import UserProfileBuilder
        profile = UserProfileBuilder().build_quick(db, user_id)
        alerts = [s.label for s in profile.registry.negative_signals()]
        alerts += [p.description for p in profile.patterns]
        return alerts[:10]
    except ImportError:
        return _legacy_detect_patterns(db, user_id, snapshots)


def _legacy_detect_patterns(
    db: Session,
    user_id,
    snapshots: Optional[List[UserMetricSnapshot]] = None,
) -> List[str]:
    if snapshots is None:
        snapshots = get_user_metric_history(db, user_id, days=14)

    if not snapshots:
        return []

    alerts = []
    latest = snapshots[-1]

    # Dimension decline alerts
    if len(snapshots) >= 2:
        week_ago_idx = max(0, len(snapshots) - 7)
        older = snapshots[week_ago_idx]

        for dim_key in FCS_WEIGHTS:
            current_val = getattr(latest, dim_key, None)
            older_val = getattr(older, dim_key, None)
            if current_val is None or older_val is None:
                continue
            if older_val > 0.05:
                drop_pct = (older_val - current_val) / older_val * 100
                if drop_pct >= 15:
                    alerts.append(
                        f"{DIMENSION_META[dim_key]['label']} dropped "
                        f"{drop_pct:.0f}% this week"
                    )

    # 3-snapshot consecutive decline
    if len(snapshots) >= 3:
        last_three_fcs = [
            s.fcs_composite for s in snapshots[-3:]
            if s.fcs_composite is not None
        ]
        if len(last_three_fcs) == 3 and last_three_fcs[0] > last_three_fcs[1] > last_three_fcs[2]:
            alerts.append("FCS has declined for 3 consecutive check-ins")

    # BSI stress signal
    if latest.bsi_score is not None and latest.bsi_score < -30:
        alerts.append("BSI indicates significant stress-driven behavior changes")

    # BSI shock event
    if getattr(latest, "bsi_shock", False):
        alerts.append("⚡ Behavioral shift event — large single-session score swing detected")

    # Emergency readiness + stability both low
    er = getattr(latest, "emergency_readiness", None)
    cs = getattr(latest, "current_stability", None)
    if er is not None and cs is not None and er < 0.3 and cs < 0.4:
        alerts.append(
            "Emergency Readiness and Stability are both critically low — "
            "user is financially exposed"
        )

    # High FCS volatility
    if len(snapshots) >= 5:
        recent_fcs = [
            s.fcs_composite for s in snapshots[-5:]
            if s.fcs_composite is not None
        ]
        if len(recent_fcs) >= 5:
            mean_fcs = sum(recent_fcs) / len(recent_fcs)
            variance = sum((x - mean_fcs) ** 2 for x in recent_fcs) / len(recent_fcs)
            if variance > 100:
                alerts.append(
                    "FCS scores are fluctuating significantly — "
                    "possible instability or inconsistent check-in behavior"
                )

    # Positive momentum
    if len(snapshots) >= 3:
        last_three_fcs = [
            s.fcs_composite for s in snapshots[-3:]
            if s.fcs_composite is not None
        ]
        if (
            len(last_three_fcs) == 3
            and last_three_fcs[0] < last_three_fcs[1] < last_three_fcs[2]
        ):
            gain = last_three_fcs[2] - last_three_fcs[0]
            if gain >= 5:
                alerts.append(
                    f"Strong upward momentum: +{gain:.1f} pts over last 3 check-ins"
                )

    # All dimensions below 50
    dims = _extract_dimensions(latest)
    answered = {k: v for k, v in dims.items() if v is not None}
    if answered and all(v < 50 for v in answered.values()):
        alerts.append(
            "All answered dimensions are below 50% — user may need extra encouragement"
        )

    return alerts


# ══════════════════════════════════════════
#  3. PROACTIVE INSIGHTS
# ══════════════════════════════════════════

def generate_proactive_insights(db: Session, user_id) -> List[Dict]:
    """
    Generate coaching insights Grace can weave into conversation.
    Each insight has: type, priority (high/medium/low), message.
    """
    snapshots = get_user_metric_history(db, user_id, days=14)
    insights = []

    if not snapshots:
        insights.append({
            "type": "onboarding",
            "priority": "high",
            "message": (
                "New user with no check-in data. "
                "Make the first check-in feel valuable and low-pressure."
            ),
        })
        return insights

    latest = snapshots[-1]
    streak = compute_streak(snapshots)

    # ── Streak milestones ────────────────────────────────────────────────────
    if streak == 3:
        insights.append({"type": "streak", "priority": "medium",
            "message": "User hit a 3-day streak. Acknowledge the consistency."})
    elif streak == 7:
        insights.append({"type": "streak", "priority": "high",
            "message": "7-day streak! This is a real milestone — celebrate it."})
    elif streak >= 14:
        insights.append({"type": "streak", "priority": "high",
            "message": f"{streak}-day streak. Talk about compounding habits."})
    elif streak == 0 and len(snapshots) >= 3:
        insights.append({"type": "re_engagement", "priority": "medium",
            "message": "Streak broke. Welcome them back warmly, no guilt."})

    # ── Weakest dimension coaching ───────────────────────────────────────────
    dims = _extract_dimensions(latest)
    answered = {k: v for k, v in dims.items() if v is not None}
    if answered:
        weakest_key = min(answered, key=answered.get)
        weakest_val = answered[weakest_key]
        if weakest_val < 40:
            meta = DIMENSION_META[weakest_key]
            insights.append({
                "type": "dimension_focus",
                "priority": "high",
                "message": (
                    f"User's {meta['label']} is at {weakest_val}%. "
                    f"Coaching tip: {meta['tip']}"
                ),
            })

    # ── BSI behavioral shift ─────────────────────────────────────────────────
    if getattr(latest, "bsi_shock", False):
        insights.append({
            "type": "bsi_shock",
            "priority": "high",
            "message": (
                "⚡ Behavioral shift event detected this session. "
                "Large swing from previous FCS. Approach with curiosity — "
                "ask what changed this week."
            ),
        })
    elif latest.bsi_score is not None:
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

    # ── Emergency readiness alert ────────────────────────────────────────────
    er = getattr(latest, "emergency_readiness", None)
    if er is not None and er < 0.25:
        insights.append({
            "type": "emergency_readiness_low",
            "priority": "high",
            "message": (
                "Emergency Readiness is critically low (<25%). "
                "User is financially exposed. Gently introduce the importance "
                "of even a small buffer — even $50/week compounding."
            ),
        })

    # ── FCS milestone crossings ──────────────────────────────────────────────
    if latest.fcs_composite is not None:
        for threshold, label in [(70, "Strong"), (50, "Building")]:
            if latest.fcs_composite >= threshold and len(snapshots) >= 3:
                older = [
                    s.fcs_composite for s in snapshots[-4:-1]
                    if s.fcs_composite is not None
                ]
                if older and all(s < threshold for s in older):
                    insights.append({
                        "type": "milestone",
                        "priority": "high",
                        "message": (
                            f"User just crossed into {label} FCS territory "
                            f"({threshold}+)! Celebrate this — it's real progress."
                        ),
                    })

    return insights


# ══════════════════════════════════════════
#  4. CONVERSATION THEME DETECTION + LOGGING
# ══════════════════════════════════════════

def detect_conversation_themes(messages: List[Dict]) -> List[str]:
    try:
        from app.services.behavioral_engine import GraceNLPStream
        nlp = GraceNLPStream()
        user_text = " ".join(
            m.get("content", "")
            for m in messages if m.get("role") == "user"
        )
        themes = nlp.extract_themes(user_text)
        return [t["theme"] for t in themes]
    except ImportError:
        return _legacy_detect_themes(messages)


THEME_KEYWORDS = {
    "debt_stress":      ["debt", "owe", "credit card", "balance", "payment", "behind", "minimum"],
    "savings_goals":    ["save", "savings", "emergency fund", "rainy day", "put away", "set aside"],
    "income_concern":   ["paycheck", "salary", "raise", "income", "not enough", "underpaid", "hours"],
    "spending_guilt":   ["overspent", "impulse", "shouldn't have", "regret", "guilty", "blew"],
    "goal_setting":     ["goal", "plan", "target", "milestone", "want to", "trying to"],
    "confusion":        ["confused", "don't understand", "what does", "explain", "how does"],
    "celebration":      ["paid off", "milestone", "achieved", "proud", "progress", "hit my"],
    "anxiety":          ["stressed", "worried", "anxious", "scared", "overwhelmed", "panic"],
    "housing":          ["rent", "mortgage", "house", "apartment", "lease", "landlord"],
    "family":           ["kids", "family", "partner", "spouse", "childcare", "baby"],
    "emergency":        ["emergency", "unexpected", "broke down", "hospital", "car repair", "set back"],
}


def _legacy_detect_themes(messages: List[Dict]) -> List[str]:
    user_text = " ".join(
        m.get("content", "").lower()
        for m in messages if m.get("role") == "user"
    )
    return [
        theme for theme, keywords in THEME_KEYWORDS.items()
        if any(kw in user_text for kw in keywords)
    ]


def log_conversation_themes(db: Session, user_id, themes: List[str]):
    """Persist conversation themes. Deduplicates same-day entries."""
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
            raw_value=1,
            scale_max=1,
            normalized_value=1.0,
            checkin_date=now,
        )
        db.add(record)

    try:
        db.commit()
    except Exception:
        db.rollback()


# ══════════════════════════════════════════
#  5. INDEX TREND FIELDS
# ══════════════════════════════════════════

def compute_index_trend_fields(db: Session, segment: str = "national") -> Optional[Dict]:
    """
    Compute gci_slope_3d, gci_slope_7d, gci_volatility_7d, trend_direction.
    Call AFTER compute_daily_index() to populate DailyIndex trend columns.
    """
    history = get_index_history(db, segment=segment, days=10)

    if len(history) < 3:
        return None

    gci_values = [
        float(h.gf_rwi_composite) if h.gf_rwi_composite else 0.0
        for h in history
    ]

    result: Dict = {}

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
    result["trend_direction"] = "UP" if slope > 0.5 else ("DOWN" if slope < -0.5 else "FLAT")

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


# ══════════════════════════════════════════
#  6. SHARED UTILITIES
# ══════════════════════════════════════════

def compute_fcs_trend(snapshots: List[UserMetricSnapshot]) -> Optional[Dict]:
    if len(snapshots) < 3:
        return None

    fcs_values = [
        s.fcs_composite for s in snapshots[-7:]
        if s.fcs_composite is not None
    ]
    if len(fcs_values) < 3:
        return None

    slope = _ols_slope(fcs_values)

    if slope > 1.0:
        return {"direction": "UP", "description": f"improving ~{slope:.1f} pts/day"}
    elif slope < -1.0:
        return {"direction": "DOWN", "description": f"declining ~{abs(slope):.1f} pts/day"}
    else:
        return {"direction": "STABLE", "description": "holding steady"}


def compute_streak(snapshots: List[UserMetricSnapshot]) -> int:
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
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    return numerator / denominator if denominator != 0 else 0.0


def _extract_dimensions(snapshot: UserMetricSnapshot) -> Dict[str, Optional[int]]:
    """
    Extract all 5 locked FCS dimensions as integer percentages (0–100).
    Returns None for any dimension with no data.
    """
    result = {}
    for dim in FCS_WEIGHTS:
        val = getattr(snapshot, dim, None)
        result[dim] = round(val * 100) if val is not None else None
    return result


def _covered_dimensions(snapshot: UserMetricSnapshot) -> int:
    return sum(
        1 for dim in FCS_WEIGHTS
        if getattr(snapshot, dim, None) is not None
    )


def _get_user_name(db: Session, user_id) -> Optional[str]:
    try:
        from app.models import User
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return getattr(user, "first_name", None) or getattr(user, "name", None)
    except Exception:
        pass
    return None


def _get_days_active(db: Session, user_id) -> Optional[int]:
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
    index = get_latest_index(db)
    if index is None or index.user_count < 5:
        return None

    user_fcs = latest_snapshot.fcs_composite
    if user_fcs is None:
        return None

    platform_fcs = index.fcs_value
    diff = user_fcs - platform_fcs

    if abs(diff) < 3:
        position = "right around the platform average"
    elif diff > 0:
        position = f"{abs(diff):.0f} points above the platform average"
    else:
        position = f"{abs(diff):.0f} points below the platform average"

    return (
        f"Peer context: FCS is {position} "
        f"(platform avg: {platform_fcs:.1f}, {index.user_count} users)"
    )


def _get_recent_themes(db: Session, user_id) -> List[str]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    try:
        records = (
            db.query(CheckInResponse.question_id)
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
        return [
            r[0].replace("CONV-", "").replace("_", " ")
            for r in records
        ]
    except Exception:
        return []