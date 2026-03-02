"""
Feed Service — Auto-generates social feed posts from user milestones.
NEW FILE: app/services/feed_service.py
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.feed import (
    FeedPost, FeedReaction, UserFeedSettings,
    FeedPostType, FeedVisibility, ReactionType,
)
from app.models.checkin import UserMetricSnapshot
from app.services.question_bank import DIMENSION_META


TIERS = [
    {"name": "Rising",    "min_fcs": 0,   "icon": "📈"},
    {"name": "Building",  "min_fcs": 35,  "icon": "🏗️"},
    {"name": "Steady",    "min_fcs": 55,  "icon": "⚡"},
    {"name": "Thriving",  "min_fcs": 75,  "icon": "🏆"},
]

STREAK_MILESTONES = [7, 14, 30, 60, 90, 180, 365]


def get_tier(fcs_score: float) -> dict:
    tier = TIERS[0]
    for t in TIERS:
        if fcs_score >= t["min_fcs"]:
            tier = t
    return tier


def check_and_generate_posts(db: Session, user_id: int, user_name: str) -> List[FeedPost]:
    settings = _get_or_create_settings(db, user_id)
    if not settings.sharing_enabled:
        return []
    posts = []
    if settings.share_streaks:
        post = _check_streak_milestone(db, user_id, user_name)
        if post:
            posts.append(post)
    if settings.share_dimension_progress:
        posts.extend(_check_dimension_improvement(db, user_id, user_name))
    if settings.share_tier_changes:
        post = _check_tier_advance(db, user_id, user_name)
        if post:
            posts.append(post)
    post = _check_first_checkin(db, user_id, user_name)
    if post:
        posts.append(post)
    for post in posts:
        db.add(post)
    if posts:
        db.commit()
    return posts


def generate_community_insight(db: Session) -> Optional[FeedPost]:
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    snapshots = db.query(UserMetricSnapshot).filter(UserMetricSnapshot.computed_at >= week_ago).all()
    if len(snapshots) < 5:
        return None
    user_scores = {}
    for s in snapshots:
        if s.user_id not in user_scores:
            user_scores[s.user_id] = []
        user_scores[s.user_id].append(s.fcs_composite)
    improved = sum(1 for scores in user_scores.values() if len(scores) >= 2 and scores[-1] > scores[0])
    total = len(user_scores)
    if total < 3:
        return None
    pct = round((improved / total) * 100)
    post = FeedPost(user_id=None, post_type=FeedPostType.community_insight, visibility=FeedVisibility.public, icon="📊", headline=f"{pct}% of users improved their Financial Confidence this week", detail=f"Based on {total} active users.", numeric_value=float(pct))
    db.add(post)
    db.commit()
    return post


def get_feed(db: Session, user_id: int, limit: int = 20, offset: int = 0, tier_filter: Optional[str] = None) -> List[dict]:
    user_tier = _get_user_tier(db, user_id)
    posts = db.query(FeedPost).filter(FeedPost.visibility.in_([FeedVisibility.public, FeedVisibility.tier_only])).order_by(desc(FeedPost.created_at)).limit(limit + 10).offset(offset).all()
    result = []
    for post in posts:
        if post.visibility == FeedVisibility.tier_only and post.tier_at_post != user_tier:
            continue
        if tier_filter and post.tier_at_post != tier_filter:
            continue
        result.append({"id": post.id, "post_type": post.post_type.value, "icon": post.icon, "headline": post.headline, "detail": post.detail, "tier": post.tier_at_post, "dimension": post.dimension, "reactions": _get_reaction_summary(db, post.id), "user_reaction": _get_user_reaction(db, post.id, user_id), "created_at": post.created_at.isoformat(), "is_own": post.user_id == user_id})
        if len(result) >= limit:
            break
    return result


def toggle_reaction(db: Session, post_id: int, user_id: int, reaction_type: str) -> dict:
    rt = ReactionType(reaction_type)
    existing = db.query(FeedReaction).filter(FeedReaction.post_id == post_id, FeedReaction.user_id == user_id, FeedReaction.reaction_type == rt).first()
    if existing:
        db.delete(existing)
        _update_reaction_count(db, post_id, -1)
        db.commit()
        return {"action": "removed", "reaction": reaction_type}
    else:
        db.add(FeedReaction(post_id=post_id, user_id=user_id, reaction_type=rt))
        _update_reaction_count(db, post_id, 1)
        db.commit()
        return {"action": "added", "reaction": reaction_type}


def get_feed_settings(db: Session, user_id: int) -> UserFeedSettings:
    return _get_or_create_settings(db, user_id)


def update_feed_settings(db: Session, user_id: int, updates: dict) -> UserFeedSettings:
    settings = _get_or_create_settings(db, user_id)
    for key, value in updates.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    db.commit()
    db.refresh(settings)
    return settings


def _get_or_create_settings(db: Session, user_id: int) -> UserFeedSettings:
    settings = db.query(UserFeedSettings).filter(UserFeedSettings.user_id == user_id).first()
    if not settings:
        settings = UserFeedSettings(user_id=user_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def _get_user_tier(db: Session, user_id: int) -> str:
    latest = db.query(UserMetricSnapshot).filter(UserMetricSnapshot.user_id == user_id).order_by(desc(UserMetricSnapshot.computed_at)).first()
    if not latest or not latest.fcs_composite:
        return "Rising"
    return get_tier(latest.fcs_composite)["name"]


def _check_streak_milestone(db: Session, user_id: int, name: str) -> Optional[FeedPost]:
    from app.models import User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    current = getattr(user, 'current_streak', 0) or 0
    if current not in STREAK_MILESTONES:
        return None
    if db.query(FeedPost).filter(FeedPost.user_id == user_id, FeedPost.post_type == FeedPostType.streak_milestone, FeedPost.numeric_value == float(current)).first():
        return None
    icons = {7: "🔥", 14: "💎", 30: "👑", 60: "🏆", 90: "🌟", 180: "⭐", 365: "🎆"}
    return FeedPost(user_id=user_id, post_type=FeedPostType.streak_milestone, visibility=FeedVisibility.public, icon=icons.get(current, "🔥"), headline=f"{name} hit a {current}-day check-in streak", detail="Consistency is the foundation of financial growth.", tier_at_post=_get_user_tier(db, user_id), numeric_value=float(current))


def _check_dimension_improvement(db: Session, user_id: int, name: str) -> List[FeedPost]:
    posts = []
    month_ago = datetime.now(timezone.utc) - timedelta(days=30)
    snapshots = db.query(UserMetricSnapshot).filter(UserMetricSnapshot.user_id == user_id, UserMetricSnapshot.computed_at >= month_ago).order_by(UserMetricSnapshot.computed_at.asc()).all()
    if len(snapshots) < 2:
        return posts
    first, latest = snapshots[0], snapshots[-1]
    for dim_key, meta in DIMENSION_META.items():
        old_val = getattr(first, dim_key, None)
        new_val = getattr(latest, dim_key, None)
        if old_val is None or new_val is None or old_val == 0:
            continue
        pct = ((new_val - old_val) / old_val) * 100
        if pct >= 10:
            if not db.query(FeedPost).filter(FeedPost.user_id == user_id, FeedPost.post_type == FeedPostType.dimension_improve, FeedPost.dimension == dim_key, FeedPost.created_at >= month_ago).first():
                posts.append(FeedPost(user_id=user_id, post_type=FeedPostType.dimension_improve, visibility=FeedVisibility.public, icon="📈", headline=f"{name} improved their {meta['label']} by {pct:.0f}% this month", dimension=dim_key, tier_at_post=_get_user_tier(db, user_id), numeric_value=round(pct, 1)))
    return posts


def _check_tier_advance(db: Session, user_id: int, name: str) -> Optional[FeedPost]:
    snapshots = db.query(UserMetricSnapshot).filter(UserMetricSnapshot.user_id == user_id).order_by(desc(UserMetricSnapshot.computed_at)).limit(2).all()
    if len(snapshots) < 2 or not snapshots[0].fcs_composite or not snapshots[1].fcs_composite:
        return None
    current_tier = get_tier(snapshots[0].fcs_composite)
    previous_tier = get_tier(snapshots[1].fcs_composite)
    if current_tier["name"] == previous_tier["name"]:
        return None
    tier_order = [t["name"] for t in TIERS]
    if tier_order.index(current_tier["name"]) <= tier_order.index(previous_tier["name"]):
        return None
    return FeedPost(user_id=user_id, post_type=FeedPostType.tier_advance, visibility=FeedVisibility.public, icon=current_tier["icon"], headline=f"{name} advanced to {current_tier['name']}", detail=f"Moved up from {previous_tier['name']} — real progress.", tier_at_post=current_tier["name"])


def _check_first_checkin(db: Session, user_id: int, name: str) -> Optional[FeedPost]:
    from app.models import User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    if (getattr(user, 'current_streak', 0) or 0) != 1:
        return None
    if db.query(FeedPost).filter(FeedPost.user_id == user_id, FeedPost.post_type == FeedPostType.first_checkin).first():
        return None
    return FeedPost(user_id=user_id, post_type=FeedPostType.first_checkin, visibility=FeedVisibility.public, icon="👋", headline=f"{name} just started their GraceFinance journey", detail="Every journey starts with a single check-in.", tier_at_post="Rising")


def _get_reaction_summary(db: Session, post_id: int) -> dict:
    return {rt.value: count for rt, count in db.query(FeedReaction.reaction_type, func.count(FeedReaction.id)).filter(FeedReaction.post_id == post_id).group_by(FeedReaction.reaction_type).all()}


def _get_user_reaction(db: Session, post_id: int, user_id: int) -> Optional[str]:
    r = db.query(FeedReaction).filter(FeedReaction.post_id == post_id, FeedReaction.user_id == user_id).first()
    return r.reaction_type.value if r else None


def _update_reaction_count(db: Session, post_id: int, delta: int):
    post = db.query(FeedPost).filter(FeedPost.id == post_id).first()
    if post:
        post.reaction_count = max(0, (post.reaction_count or 0) + delta)