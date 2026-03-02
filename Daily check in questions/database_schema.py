"""
GraceFinance Daily Check-In Database Schema
PostgreSQL tables for storing user responses and generating insights
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, ForeignKey, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class UserCheckInResponse(Base):
    """
    Stores individual question responses from daily check-ins
    """
    __tablename__ = "user_checkin_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    question_id = Column(String(20), nullable=False, index=True)  # e.g., "MS001"
    question_category = Column(String(50), nullable=False, index=True)  # e.g., "money_stress"
    
    # Flexible answer storage
    answer_text = Column(Text, nullable=True)  # For open text
    answer_numeric = Column(Integer, nullable=True)  # For scales and numeric
    answer_choice = Column(String(200), nullable=True)  # For multiple choice
    answer_boolean = Column(Boolean, nullable=True)  # For yes/no
    
    # Metadata
    answered_at = Column(DateTime, default=datetime.utcnow, index=True)
    session_id = Column(String(50), nullable=True)  # Groups questions answered in one session
    
    # Relationships
    user = relationship("User", back_populates="checkin_responses")
    
    def __repr__(self):
        return f"<CheckInResponse(user={self.user_id}, question={self.question_id})>"


class UserStressTrend(Base):
    """
    Aggregated stress trend data for faster analytics
    Calculated daily from responses
    """
    __tablename__ = "user_stress_trends"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    
    # Stress metrics (1-10 scale)
    average_stress = Column(Float, nullable=True)
    money_anxiety = Column(Float, nullable=True)
    bill_stress = Column(Float, nullable=True)
    
    # Confidence metrics (1-10 scale)
    financial_confidence = Column(Float, nullable=True)
    control_feeling = Column(Float, nullable=True)
    
    # Top concerns (JSON array)
    top_concerns = Column(JSON, nullable=True)  # ["Paying rent", "Not saving enough"]
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="stress_trends")


class UserFinancialProfile(Base):
    """
    User's financial context and life stage
    Used for question personalization
    """
    __tablename__ = "user_financial_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Life stage
    life_stage = Column(String(50), nullable=True)  # "young_professional", "homeowner", etc.
    
    # Current situation
    employment_status = Column(String(50), nullable=True)
    housing_status = Column(String(50), nullable=True)  # "renting", "owning", etc.
    has_dependents = Column(Boolean, default=False)
    
    # Financial state
    has_emergency_fund = Column(Boolean, default=False)
    has_debt = Column(Boolean, default=False)
    primary_goal = Column(String(100), nullable=True)
    
    # Behavioral flags (updated based on responses)
    high_stress_user = Column(Boolean, default=False)  # Recent stress scores > 7
    goal_focused = Column(Boolean, default=False)  # Regularly engages with goal questions
    avoids_checking_balance = Column(Boolean, default=False)
    emotional_spender = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="financial_profile")


class CheckInInsight(Base):
    """
    Auto-generated insights based on check-in patterns
    """
    __tablename__ = "checkin_insights"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Insight details
    insight_type = Column(String(50), nullable=False)  # "positive_trend", "pattern_detected", etc.
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    emoji = Column(String(10), nullable=True)
    
    # Action
    action_button_text = Column(String(100), nullable=True)
    action_route = Column(String(100), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_read = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=True)  # Some insights are time-sensitive
    
    user = relationship("User", back_populates="checkin_insights")


class QuestionRotationLog(Base):
    """
    Tracks which questions were shown to users
    Ensures variety and prevents repetition
    """
    __tablename__ = "question_rotation_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    question_id = Column(String(20), nullable=False, index=True)
    shown_at = Column(DateTime, default=datetime.utcnow, index=True)
    was_answered = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="question_rotation_logs")


# Add these relationships to your existing User model:
"""
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    # ... your existing User fields ...
    
    # Relationships
    checkin_responses = relationship("UserCheckInResponse", back_populates="user")
    stress_trends = relationship("UserStressTrend", back_populates="user")
    financial_profile = relationship("UserFinancialProfile", back_populates="user", uselist=False)
    checkin_insights = relationship("CheckInInsight", back_populates="user")
    question_rotation_logs = relationship("QuestionRotationLog", back_populates="user")
"""


# SQL for creating indexes (run after tables are created)
CREATE_INDEXES_SQL = """
-- Indexes for fast queries
CREATE INDEX idx_responses_user_date ON user_checkin_responses(user_id, answered_at DESC);
CREATE INDEX idx_responses_category ON user_checkin_responses(question_category);
CREATE INDEX idx_stress_trends_user_date ON user_stress_trends(user_id, date DESC);
CREATE INDEX idx_insights_active ON checkin_insights(user_id, is_active, is_read);
CREATE INDEX idx_rotation_recent ON question_rotation_logs(user_id, shown_at DESC);

-- Index for finding high stress users (for support outreach)
CREATE INDEX idx_profiles_high_stress ON user_financial_profiles(high_stress_user) WHERE high_stress_user = true;
"""


# Analytics queries
ANALYTICS_QUERIES = {
    "get_stress_trend": """
        SELECT date, average_stress, money_anxiety
        FROM user_stress_trends
        WHERE user_id = :user_id
        AND date >= NOW() - INTERVAL '30 days'
        ORDER BY date ASC;
    """,
    
    "get_top_concerns": """
        SELECT answer_choice as concern, COUNT(*) as frequency
        FROM user_checkin_responses
        WHERE user_id = :user_id
        AND question_id IN ('MS002', 'MS007')  -- Worry questions
        AND answered_at >= NOW() - INTERVAL '30 days'
        GROUP BY answer_choice
        ORDER BY frequency DESC
        LIMIT 3;
    """,
    
    "calculate_confidence_score": """
        SELECT AVG(answer_numeric) as avg_confidence
        FROM user_checkin_responses
        WHERE user_id = :user_id
        AND question_category = 'financial_confidence'
        AND answered_at >= NOW() - INTERVAL '30 days';
    """,
    
    "detect_stress_pattern": """
        SELECT 
            EXTRACT(DAY FROM answered_at) as day_of_month,
            AVG(answer_numeric) as avg_stress
        FROM user_checkin_responses
        WHERE user_id = :user_id
        AND question_category = 'money_stress'
        AND question_id LIKE 'MS%'
        AND answered_at >= NOW() - INTERVAL '90 days'
        GROUP BY EXTRACT(DAY FROM answered_at)
        HAVING AVG(answer_numeric) >= 7
        ORDER BY avg_stress DESC;
    """,
    
    "recently_shown_questions": """
        SELECT DISTINCT question_id
        FROM question_rotation_logs
        WHERE user_id = :user_id
        AND shown_at >= NOW() - INTERVAL '30 days'
        ORDER BY shown_at DESC;
    """
}
