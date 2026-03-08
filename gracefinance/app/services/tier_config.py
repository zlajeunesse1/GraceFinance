"""
Tier Configuration — Single Source of Truth
════════════════════════════════════════════
Every feature gate across the platform references this file.
Update tiers HERE and they propagate everywhere.

Pricing:
  Free     — $0/mo
  Pro      — $9.99/mo  | $8.25/mo billed yearly ($99/yr, save ~$21)
  Premium  — $29.99/mo | $25.00/mo billed yearly ($299.99/yr, save ~$60)
"""

from enum import Enum
from typing import Optional


class Tier(str, Enum):
    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"


# ── Grace AI Message Limits ──────────────────────────────────────────────────
AI_MESSAGE_LIMITS: dict[str, Optional[int]] = {
    "free": 10,
    "pro": 100,
    "premium": None,  # unlimited
}

# ── FCS History Depth (days) ─────────────────────────────────────────────────
FCS_HISTORY_LIMITS: dict[str, int] = {
    "free": 7,
    "pro": 90,
    "premium": 365,
}

# ── Feature Access Matrix ────────────────────────────────────────────────────
# True = unlocked at this tier
FEATURE_ACCESS: dict[str, dict[str, bool]] = {
    # ── Available to ALL tiers ──
    "daily_checkin":            {"free": True,  "pro": True,  "premium": True},
    "fcs_composite_score":      {"free": True,  "pro": True,  "premium": True},
    "fcs_5_dimension_breakdown":{"free": True,  "pro": True,  "premium": True},
    "gracefinance_index":       {"free": True,  "pro": True,  "premium": True},
    "grace_ai_chat":            {"free": True,  "pro": True,  "premium": True},

    # ── Pro+ ──
    "fcs_trend_history":        {"free": False, "pro": True,  "premium": True},
    "data_export_csv":          {"free": False, "pro": True,  "premium": True},
    "data_export_pdf":          {"free": False, "pro": True,  "premium": True},
    "behavioral_trend_insights":{"free": False, "pro": True,  "premium": True},
    "priority_support":         {"free": False, "pro": True,  "premium": True},

    # ── Premium Only ──
    "advanced_analytics":       {"free": False, "pro": False, "premium": True},
    "bsi_insights":             {"free": False, "pro": False, "premium": True},
    "early_access":             {"free": False, "pro": False, "premium": True},
}


def has_feature(tier: str, feature: str) -> bool:
    """Check if a tier has access to a specific feature."""
    tier = tier.lower()
    feat = FEATURE_ACCESS.get(feature, {})
    return feat.get(tier, False)


def get_ai_limit(tier: str) -> Optional[int]:
    """Get the AI message limit for a tier. None = unlimited."""
    return AI_MESSAGE_LIMITS.get(tier.lower(), 10)


def get_history_days(tier: str) -> int:
    """Get the max FCS history depth for a tier."""
    return FCS_HISTORY_LIMITS.get(tier.lower(), 7)


# ── Tier Display Info (for API responses & frontend) ─────────────────────────
TIER_DISPLAY = {
    "free": {
        "name": "Free",
        "price_monthly": 0,
        "price_yearly": 0,
        "tagline": "Get started with financial awareness",
        "ai_label": "10 messages / month",
        "features": [
            "Daily Financial Confidence Score",
            "5-dimension breakdown",
            "Daily check-ins",
            "10 Grace AI messages/month",
            "GraceFinance Index access",
        ],
    },
    "pro": {
        "name": "Pro",
        "price_monthly": 9.99,
        "price_yearly": 99.00,
        "tagline": "For people serious about building better habits",
        "ai_label": "100 messages / month",
        "features": [
            "Everything in Free",
            "100 Grace AI messages/month",
            "FCS trend history (90 days)",
            "Behavioral trend insights",
            "Data export (CSV & PDF)",
            "Priority support",
        ],
    },
    "premium": {
        "name": "Premium",
        "price_monthly": 29.99,
        "price_yearly": 299.99,
        "tagline": "Full access. No limits. Total financial clarity.",
        "ai_label": "Unlimited",
        "features": [
            "Everything in Pro",
            "Unlimited Grace AI messages",
            "Advanced behavioral analytics",
            "BSI insights & pattern detection",
            "Full FCS history (365 days)",
            "Early access to new features",
        ],
    },
}