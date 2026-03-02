"""
Social Feed Models — GraceFinance Community Feed
═══════════════════════════════════════════════════
Auto-generated feed posts from user milestones.
No free-text posts = no moderation burden.

NEW FILE: app/models/feed.py
"""

import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float,
    ForeignKey, Index, Text, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class FeedPostType(str, enum.Enum):
    streak_milestone = "streak_milestone"
    dimension_improve = "dimension_improve"
    tier_advance = "tier_advance"
    goal_reached = "goal_reached"
    first_checkin = "first_checkin"
    weekly_win = "weekly_win"
    community_insight = "community_insight"
    xp_milestone = "xp_milestone"
    personality_evolved = "personality_evolved"


class FeedVisibility(str, enum.Enum):
    public = "public"
    tier_only = "tier_only"
    private = "private"


class ReactionType(str, enum.Enum):
    fire = "fire"
    clap = "clap"
    rocket = "rocket"
    heart = "heart"
    strong = "strong"


class FeedPost(Base):
    __tablename__ = "feed_posts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    post_type = Column(SQLEnum(FeedPostType), nullable=False)
    visibility = Column(SQLEnum(FeedVisibility), default=FeedVisibility.public)
    icon = Column(String(10), nullable=False)
    headline = Column(String(200), nullable=False)
    detail = Column(String(500), nullable=True)

    dimension = Column(String(50), nullable=True)
    tier_at_post = Column(String(20), nullable=True)
    numeric_value = Column(Float, nullable=True)

    reaction_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    reactions = relationship("FeedReaction", back_populates="post", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_feed_created", "created_at"),
        Index("ix_feed_user", "user_id"),
        Index("ix_feed_type", "post_type"),
        Index("ix_feed_visibility", "visibility"),
        Index("ix_feed_tier", "tier_at_post"),
    )


class FeedReaction(Base):
    __tablename__ = "feed_reactions"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("feed_posts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reaction_type = Column(SQLEnum(ReactionType), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    post = relationship("FeedPost", back_populates="reactions")

    __table_args__ = (
        Index("ix_reaction_unique", "post_id", "user_id", "reaction_type", unique=True),
    )


class UserFeedSettings(Base):
    __tablename__ = "user_feed_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    sharing_enabled = Column(Boolean, default=False)

    share_streaks = Column(Boolean, default=True)
    share_tier_changes = Column(Boolean, default=True)
    share_dimension_progress = Column(Boolean, default=True)
    share_goals = Column(Boolean, default=True)
    share_xp_milestones = Column(Boolean, default=True)

    show_tier_on_profile = Column(Boolean, default=True)
    show_scores_on_profile = Column(Boolean, default=False)
    display_name = Column(String(30), nullable=True)

    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))