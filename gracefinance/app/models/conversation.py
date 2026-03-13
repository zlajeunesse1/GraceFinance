"""
GraceFinance — Conversation Storage Model
==========================================
Stores Grace AI chat messages for behavioral NLP extraction (Stream 3).
Lightweight: just user_id, role, content, timestamp.
Cascade-deletes with User.

Add to User model relationships:
    conversations = relationship("ConversationMessage", back_populates="user", cascade="all, delete-orphan")
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    role = Column(String(20), nullable=False)       # "user" or "assistant"
    content = Column(Text, nullable=False)
    session_id = Column(String(64), nullable=True)   # group messages by conversation session

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    user = relationship("User", back_populates="conversations")

    __table_args__ = (
        Index("ix_convo_user_created", "user_id", "created_at"),
        Index("ix_convo_session", "session_id"),
    )