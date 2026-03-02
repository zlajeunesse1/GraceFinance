"""
Progression Service — Computes behavioral unlock tiers from existing check-in data.

NO new database model needed. Tiers are computed dynamically from:
  - CheckInResponse count (total check-ins)
  - User.current_streak (consecutive days)
  - Distinct check-in dates (data points)

Philosophy: "Unlocked because you've built consistency" — not paywalls.

Drop this into: gracefinance/app/services/progression_service.py
"""

from datetime import datetime, timezone, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, and_

from app.models.checkin import CheckInResponse, UserMetricSnapshot


# ══════════════════════════════════════════
#  TIER DEFINITIONS
# ══════════════════════════════════════════
#
#  Each tier unlocks a specific behavioral insight layer.
#  requirement_type: "checkins" | "streak" | "data_points" | "compound"
#  compound = requires BOTH a checkin count AND a streak

TIERS = [
    {
        "id": "foundation",
        "name": "Foundation",
        "description": "Your FCS score and basic dashboard",
        "icon": "🏗️",
        "requirement_type": "checkins",
        "threshold": 1,
        "unlocks": ["fcs_score", "basic_dashboard", "grace_ai_chat"],
        "color": "#58A6FF",
    },
    {
        "id": "stability_insights",
        "name": "Stability Insights",
        "description": "Deep dive into your Current Stability dimension",
        "icon": "🛡️",
        "requirement_type": "checkins",
        "threshold": 5,
        "unlocks": ["stability_breakdown", "dimension_radar", "focus_area_tips"],
        "color": "#58A6FF",
    },
    {
        "id": "spending_psychology",
        "name": "Spending Psychology",
        "description": "Behavioral patterns behind your purchasing decisions",
        "icon": "🧠",
        "requirement_type": "streak",
        "threshold": 14,
        "unlocks": ["spending_patterns", "impulse_tracking", "bsi_insights"],
        "color": "#BC8CFF",
    },
    {
        "id": "behavioral_trends",
        "name": "Behavioral Trends",
        "description": "Advanced trend analysis across all dimensions",
        "icon": "📊",
        "requirement_type": "data_points",
        "threshold": 30,
        "unlocks": ["trend_analysis", "dimension_comparison", "weekly_report"],
        "color": "#D29922",
    },
    {
        "id": "debt_pressure",
        "name": "Debt Pressure Deep Dive",
        "description": "Stress-test your financial safety net",
        "icon": "🚨",
        "requirement_type": "streak",
        "threshold": 21,
        "unlocks": ["emergency_simulation", "safety_net_score", "crisis_playbook"],
        "color": "#F85149",
    },
    {
        "id": "full_index_access",
        "name": "Full Index Access",
        "description": "Complete GF-RWI breakdown with your personal benchmark",
        "icon": "🏆",
        "requirement_type": "compound",
        "threshold": {"checkins": 60, "streak": 30},
        "unlocks": ["full_gf_rwi", "personal_benchmark", "peer_comparison"],
        "color": "#3FB950",
    },
]


def get_user_progression(db: Session, user_id, current_streak: int = 0):
    """
    Compute the user's full progression status.

    Returns dict with:
      - tiers: list of tier objects with unlock status
      - total_checkins: int
      - current_streak: int
      - data_points: int (unique check-in days)
      - next_unlock: the closest locked tier with progress info
      - unlocked_features: flat list of all unlocked feature keys
    """

    # ── Count total check-in responses ──
    total_checkins = (
        db.query(func.count(CheckInResponse.id))
        .filter(CheckInResponse.user_id == user_id)
        .scalar() or 0
    )

    # ── Count unique check-in days (data points) ──
    data_points = (
        db.query(func.count(distinct(func.date(CheckInResponse.checkin_date))))
        .filter(CheckInResponse.user_id == user_id)
        .scalar() or 0
    )

    # ── Build tier status ──
    unlocked_features = []
    tier_results = []
    next_unlock = None

    for tier in TIERS:
        req = tier["requirement_type"]
        threshold = tier["threshold"]

        # Compute progress based on requirement type
        if req == "checkins":
            current_value = total_checkins
            progress = min(current_value / threshold, 1.0) if threshold > 0 else 1.0
            remaining = max(threshold - current_value, 0)
            remaining_label = f"{remaining} more check-in{'s' if remaining != 1 else ''}"

        elif req == "streak":
            current_value = current_streak
            progress = min(current_value / threshold, 1.0) if threshold > 0 else 1.0
            remaining = max(threshold - current_value, 0)
            remaining_label = f"{remaining} more day{'s' if remaining != 1 else ''} streak"

        elif req == "data_points":
            current_value = data_points
            progress = min(current_value / threshold, 1.0) if threshold > 0 else 1.0
            remaining = max(threshold - current_value, 0)
            remaining_label = f"{remaining} more data point{'s' if remaining != 1 else ''}"

        elif req == "compound":
            checkin_thresh = threshold["checkins"]
            streak_thresh = threshold["streak"]
            checkin_progress = min(total_checkins / checkin_thresh, 1.0)
            streak_progress = min(current_streak / streak_thresh, 1.0)
            progress = (checkin_progress + streak_progress) / 2
            current_value = {"checkins": total_checkins, "streak": current_streak}

            checkin_remaining = max(checkin_thresh - total_checkins, 0)
            streak_remaining = max(streak_thresh - current_streak, 0)
            parts = []
            if checkin_remaining > 0:
                parts.append(f"{checkin_remaining} check-in{'s' if checkin_remaining != 1 else ''}")
            if streak_remaining > 0:
                parts.append(f"{streak_remaining}-day streak")
            remaining_label = " + ".join(parts) if parts else "Complete!"
            remaining = checkin_remaining + streak_remaining
        else:
            progress = 0
            remaining = 0
            remaining_label = ""
            current_value = 0

        is_unlocked = progress >= 1.0

        tier_obj = {
            "id": tier["id"],
            "name": tier["name"],
            "description": tier["description"],
            "icon": tier["icon"],
            "color": tier["color"],
            "requirement_type": req,
            "threshold": threshold,
            "current_value": current_value,
            "progress": round(progress, 3),
            "is_unlocked": is_unlocked,
            "remaining": remaining,
            "remaining_label": remaining_label,
            "unlocks": tier["unlocks"],
        }

        if is_unlocked:
            unlocked_features.extend(tier["unlocks"])

        tier_results.append(tier_obj)

        # Track the NEXT unlock (closest locked tier by progress)
        if not is_unlocked and (next_unlock is None or progress > next_unlock["progress"]):
            next_unlock = tier_obj

    return {
        "tiers": tier_results,
        "total_checkins": total_checkins,
        "current_streak": current_streak,
        "data_points": data_points,
        "next_unlock": next_unlock,
        "unlocked_count": sum(1 for t in tier_results if t["is_unlocked"]),
        "total_tiers": len(tier_results),
        "unlocked_features": unlocked_features,
    }