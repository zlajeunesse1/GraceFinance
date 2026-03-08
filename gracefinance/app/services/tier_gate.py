"""
Tier Gate — Backend feature gating utility.
════════════════════════════════════════════
Usage in any router:

    from app.services.tier_gate import require_feature, gate_history_depth

    @router.get("/checkin/metrics")
    def get_metrics(days: int = 30, user = Depends(get_current_user)):
        days = gate_history_depth(user, days)  # caps based on tier
        ...

    @router.get("/api/export/checkins")
    def export_checkins(user = Depends(get_current_user)):
        require_feature(user, "data_export_csv")  # raises 403 if Free
        ...
"""

from fastapi import HTTPException, status
from app.services.tier_config import has_feature, get_history_days, get_ai_limit, TIER_DISPLAY


def _user_tier(user) -> str:
    """Safely extract tier string from user object."""
    return str(getattr(user, "subscription_tier", "free") or "free").lower()


def require_feature(user, feature: str) -> None:
    """
    Raise HTTP 403 if the user's tier doesn't include this feature.
    Returns None (passthrough) if access is granted.
    """
    tier = _user_tier(user)

    if not has_feature(tier, feature):
        # Find the cheapest tier that HAS this feature
        upgrade_to = None
        for check_tier in ["pro", "premium"]:
            if has_feature(check_tier, feature):
                upgrade_to = check_tier
                break

        tier_info = TIER_DISPLAY.get(upgrade_to, {})
        price = tier_info.get("price_monthly", "")

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "feature_locked",
                "feature": feature,
                "current_tier": tier,
                "required_tier": upgrade_to,
                "message": f"This feature requires {upgrade_to.title()} (${price}/mo). Upgrade to unlock.",
            },
        )


def gate_history_depth(user, requested_days: int) -> int:
    """
    Cap the requested history depth to what the user's tier allows.
    Free: 7 days, Pro: 90 days, Premium: 365 days.
    Returns the capped value silently — no error thrown.
    """
    tier = _user_tier(user)
    max_days = get_history_days(tier)
    return min(requested_days, max_days)


def check_feature(user, feature: str) -> bool:
    """
    Soft check — returns True/False without raising.
    Use for conditional UI responses (e.g., showing locked badges).
    """
    return has_feature(_user_tier(user), feature)