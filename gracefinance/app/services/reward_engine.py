"""
GraceFinance Reward Engine
===========================
Computes the instant gratification payload after a check-in.

Layer A (Instant): This runs synchronously inside POST /checkins.

Responsibilities:
  1. Compute before/after score deltas per dimension
  2. Calculate and update streak
  3. Generate Grace mini-summary (deterministic, no API call)
  4. Pick the weakest dimension and a behavior nudge

Place at: app/services/reward_engine.py
"""

from datetime import datetime, date, timezone, timedelta
from typing import Optional, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, cast, Date

from app.models.checkin import CheckInResponse, UserMetricSnapshot
from app.services.checkin_service import FCS_WEIGHTS


# ============================================================
#  DIMENSION METADATA
# ============================================================

DIMENSION_META = {
    "current_stability": {
        "label": "Current Stability",
        "tips": [
            "Set up autopay for your biggest bills. Knowing they're covered reduces stress instantly.",
            "Review your bank balance right now. Just knowing the number builds stability.",
            "List your fixed monthly expenses. Clarity is the first step to control.",
        ],
    },
    "future_outlook": {
        "label": "Future Outlook",
        "tips": [
            "Write down one financial goal you want to hit in 90 days. Clarity drives confidence.",
            "Open a savings account and name it after your goal. Naming it makes it real.",
            "Set a calendar reminder to review your finances next Sunday. Consistency compounds.",
        ],
    },
    "purchasing_power": {
        "label": "Purchasing Power",
        "tips": [
            "Track 3 grocery swaps this week. Small wins add up to big savings.",
            "Compare one subscription you use least against what else that money could do.",
            "Before your next purchase over $30, wait 24 hours. The pause reveals the pattern.",
        ],
    },
    "emergency_readiness": {
        "label": "Emergency Readiness",
        "tips": [
            "Transfer $10 to savings today. The amount doesn't matter — the habit does.",
            "Calculate how many days your savings would cover if income stopped. Know your number.",
            "Set up a $25/week auto-transfer to a separate savings account. Automate the safety net.",
        ],
    },
    "financial_agency": {
        "label": "Financial Agency",
        "tips": [
            "List one skill you could monetize on the side. Ideas are the seed of income growth.",
            "Research what people in your role earn. Knowledge is negotiation power.",
            "Track every income source this month, even small ones. Awareness reveals opportunity.",
        ],
    },
}

MILESTONE_STREAKS = {7, 14, 21, 30, 60, 90, 100, 180, 365}

# ============================================================
#  GRACE MINI-SUMMARIES (deterministic, no API call needed)
# ============================================================

GRACE_SUMMARIES = {
    "big_improvement": [
        "Nice move. Your scores are climbing — that's not luck, that's you showing up.",
        "Something shifted. Whatever you did differently today, keep that energy.",
        "Your numbers are moving. GraceFinance is just the mirror — you're doing the work.",
    ],
    "steady": [
        "Consistency is underrated. You're holding steady, and that matters more than people think.",
        "No dramatic swings today — and that's actually a sign of financial maturity.",
        "Flat isn't boring. Flat is stable. Stable is how wealth gets built.",
    ],
    "small_dip": [
        "A small dip isn't a setback — it's information. Let's see what tomorrow brings.",
        "One rough day doesn't define your trajectory. You're still here, still checking in.",
        "Scores fluctuate. What doesn't fluctuate is the fact that you showed up today.",
    ],
    "milestone_streak": [
        "{streak} days in a row. Most people don't make it past day 3. You're built different.",
        "{streak}-day streak. That's not discipline — that's identity. You're a person who checks in.",
        "{streak} consecutive days. The compound effect of awareness is your unfair advantage.",
    ],
    "first_checkin": [
        "Welcome to GraceFinance. This first check-in just created your baseline — every future score builds from here.",
        "Day one. The hardest part is starting, and you just did it.",
    ],
}


def _pick_summary(scenario: str, streak: int = 0) -> str:
    """Pick a deterministic-ish summary based on today's date."""
    import hashlib

    summaries = GRACE_SUMMARIES.get(scenario, GRACE_SUMMARIES["steady"])
    today_str = date.today().isoformat()
    idx = int(hashlib.md5(today_str.encode()).hexdigest(), 16) % len(summaries)
    text = summaries[idx]
    return text.format(streak=streak) if "{streak}" in text else text


def compute_reward(
    db: Session,
    user_id,
    new_snapshot: UserMetricSnapshot,
    previous_snapshot: Optional[UserMetricSnapshot],
) -> dict:
    """
    Compute the full reward payload for a check-in.

    Called synchronously after save_responses() and compute_user_snapshot().
    Returns a dict matching the CheckinReward schema.
    """

    # -- 1. Streak calculation --
    streak, is_milestone = _compute_streak(db, user_id)

    # -- 2. Score deltas --
    deltas = _compute_deltas(new_snapshot, previous_snapshot)

    # -- 3. Overall direction for Grace summary --
    fcs_delta = deltas.get("fcs_composite", {})
    direction = fcs_delta.get("direction", "flat")

    if streak == 1 and previous_snapshot is None:
        scenario = "first_checkin"
    elif is_milestone:
        scenario = "milestone_streak"
    elif direction == "up" and abs(fcs_delta.get("after", 0) - fcs_delta.get("before", 0)) > 0.03:
        scenario = "big_improvement"
    elif direction == "down":
        scenario = "small_dip"
    else:
        scenario = "steady"

    grace_summary = _pick_summary(scenario, streak)

    # -- 4. Weakest dimension + nudge --
    weakest_dim, nudge = _pick_nudge(new_snapshot)

    return {
        "streak": streak,
        "streak_is_milestone": is_milestone,
        "grace_summary": grace_summary,
        "deltas": deltas,
        "weakest_dimension": weakest_dim,
        "behavior_nudge": nudge,
    }


# ============================================================
#  INTERNAL HELPERS
# ============================================================

def _compute_streak(db: Session, user_id) -> Tuple[int, bool]:
    """
    Compute streak from check-in history.
    Returns (streak_count, is_milestone).
    """
    today = date.today()

    checkin_dates = (
        db.query(func.distinct(cast(CheckInResponse.checkin_date, Date)))
        .filter(CheckInResponse.user_id == user_id)
        .order_by(cast(CheckInResponse.checkin_date, Date).desc())
        .limit(400)
        .all()
    )

    dates = sorted([row[0] for row in checkin_dates], reverse=True)

    if not dates:
        return 1, (1 in MILESTONE_STREAKS)

    streak = 1
    for i in range(len(dates) - 1):
        if dates[i] == today and i == 0:
            continue
        expected_prev = dates[i] - timedelta(days=1)
        if i + 1 < len(dates) and dates[i + 1] == expected_prev:
            streak += 1
        else:
            break

    if dates[0] != today:
        if dates[0] == today - timedelta(days=1):
            streak = 1
            for i in range(len(dates) - 1):
                if dates[i] - timedelta(days=1) == dates[i + 1]:
                    streak += 1
                else:
                    break
            streak += 1
        else:
            streak = 1

    is_milestone = streak in MILESTONE_STREAKS
    return streak, is_milestone


def _compute_deltas(
    new_snap: UserMetricSnapshot,
    prev_snap: Optional[UserMetricSnapshot],
) -> Dict[str, dict]:
    """Compute before/after/direction for each dimension + composite."""
    dims = [
        "fcs_composite",
        "current_stability",
        "future_outlook",
        "purchasing_power",
        "emergency_readiness",
        "financial_agency",
    ]

    deltas = {}
    for dim in dims:
        after_val = float(getattr(new_snap, dim, 0) or 0)
        before_val = float(getattr(prev_snap, dim, 0) or 0) if prev_snap else 0.0

        diff = after_val - before_val
        if abs(diff) < 0.005:
            direction = "flat"
        elif diff > 0:
            direction = "up"
        else:
            direction = "down"

        deltas[dim] = {
            "before": round(before_val, 4),
            "after": round(after_val, 4),
            "direction": direction,
        }

    return deltas


def _pick_nudge(snapshot: UserMetricSnapshot) -> Tuple[Optional[str], Optional[dict]]:
    """Find the weakest dimension and return a nudge for it."""
    dims = [
        "current_stability", "future_outlook", "purchasing_power",
        "emergency_readiness", "financial_agency",
    ]

    weakest_dim = None
    weakest_val = 2.0

    for dim in dims:
        val = float(getattr(snapshot, dim, 0) or 0)
        if val < weakest_val:
            weakest_val = val
            weakest_dim = dim

    if weakest_dim and weakest_dim in DIMENSION_META:
        import hashlib
        meta = DIMENSION_META[weakest_dim]
        tips = meta["tips"]
        today_str = date.today().isoformat()
        idx = int(hashlib.md5((today_str + weakest_dim).encode()).hexdigest(), 16) % len(tips)
        return weakest_dim, {
            "dimension": weakest_dim,
            "label": meta["label"],
            "tip": tips[idx],
        }

    return None, None