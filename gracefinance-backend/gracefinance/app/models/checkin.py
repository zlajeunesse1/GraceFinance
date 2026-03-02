# models/checkin.py
# GraceFinance Daily Check-In Database Models
# SQLAlchemy + PostgreSQL

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class CheckinQuestion(Base):
    """Master question bank - all possible check-in questions"""
    __tablename__ = "checkin_questions"

    id = Column(String(50), primary_key=True)  # e.g. 'mood_open', 'spend_trigger'
    category = Column(String(50), nullable=False)  # money_mindset, spending_habits, etc.
    type = Column(String(30), nullable=False)  # emoji_select, quick_tap, visual_slider, multiple_choice, open_text, scale
    question = Column(Text, nullable=False)
    subtitle = Column(Text, nullable=True)
    placeholder = Column(Text, nullable=True)  # for open_text
    max_characters = Column(Integer, nullable=True)  # for open_text
    options = Column(JSON, nullable=True)  # array of options (format depends on type)
    multi = Column(Boolean, default=False)  # allow multi-select
    min_val = Column(Integer, nullable=True)  # for slider/scale
    max_val = Column(Integer, nullable=True)  # for slider/scale
    labels = Column(JSON, nullable=True)  # for slider: {1: "Low", 5: "Mid", 10: "High"}
    color_range = Column(JSON, nullable=True)  # for slider: ["#f87171", "#fbbf24", "#34d399"]
    day_set = Column(Integer, nullable=False)  # which daily rotation set (0, 1, 2, ...)
    sort_order = Column(Integer, default=0)  # order within the set
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    answers = relationship("CheckinAnswer", back_populates="question")


class CheckinAnswer(Base):
    """Individual answer to a check-in question"""
    __tablename__ = "checkin_answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_id = Column(String(50), ForeignKey("checkin_questions.id"), nullable=False)
    answer = Column(JSON, nullable=False)  # string, number, or array depending on type
    mood_score = Column(Float, nullable=True)  # extracted mood score (1-10) if applicable
    session_date = Column(Date, nullable=False)  # which day this belongs to
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    question = relationship("CheckinQuestion", back_populates="answers")
    user = relationship("User", back_populates="checkin_answers")


class CheckinSession(Base):
    """One completed daily check-in session"""
    __tablename__ = "checkin_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_date = Column(Date, nullable=False, index=True)
    day_set = Column(Integer, nullable=False)  # which question set was served
    wellness_score = Column(Integer, nullable=True)  # calculated 0-100
    mood_label = Column(String(30), nullable=True)  # e.g. "Stressed", "Powerful"
    mood_score = Column(Float, nullable=True)  # numeric mood 1-10
    insights = Column(JSON, nullable=True)  # generated insights stored for history
    completed_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="checkin_sessions")


class CheckinStreak(Base):
    """Tracks user's streak and milestones"""
    __tablename__ = "checkin_streaks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    total_checkins = Column(Integer, default=0)
    last_checkin_date = Column(Date, nullable=True)
    personality_type = Column(String(50), nullable=True)  # e.g. 'aware_builder'
    personality_updated_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="checkin_streak")
