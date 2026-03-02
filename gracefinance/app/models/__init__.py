"""
GraceFinance Models — All SQLAlchemy models exported here.
FIXED: Debt / Transaction / Bill restored.
FIXED: CheckInResponse/UserMetricSnapshot imported from checkin.py (not models.py)
FIXED: UserProfile imported from profile.py (not models.py)
"""

# Core models
from app.models.models import (
    User,
    Debt,
    Transaction,
    Bill,
    SubscriptionTier,
    DebtType,
    TransactionCategory,
    BillStatus,
)

# Data Engine models (check-ins → metrics → index)
from app.models.checkin import (
    CheckInResponse,
    UserMetricSnapshot,
    DailyIndex,
    FCSDimension,
    ScaleType,
)

# User Profile
from app.models.profile import UserProfile

# Reward Loop models
from app.models.contribution_queue import IndexContributionEvent

# Social Feed (v2)
from app.models.feed import (
    FeedPost,
    FeedReaction,
    UserFeedSettings,
    FeedPostType,
    FeedVisibility,
    ReactionType,
)

__all__ = [
    "User",
    "Debt",
    "Transaction",
    "Bill",
    "SubscriptionTier",
    "DebtType",
    "TransactionCategory",
    "BillStatus",
    "CheckInResponse",
    "UserMetricSnapshot",
    "UserProfile",
    "DailyIndex",
    "FCSDimension",
    "ScaleType",
    "IndexContributionEvent",
    "FeedPost",
    "FeedReaction",
    "UserFeedSettings",
    "FeedPostType",
    "FeedVisibility",
    "ReactionType",
]