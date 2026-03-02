import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    Enum as SQLEnum, ForeignKey, Index, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base

# ============ ENUMS ============

class FCSDimension(str, enum.Enum):
    current_stability = "current_stability"
    future_outlook = "future_outlook"
    purchasing_power = "purchasing_power"
    debt_pressure = "debt_pressure"
    financial_agency = "financial_agency"


class ScaleType(str, enum.Enum):
    scale_1_5 = "1-5"
    scale_1_10 = "1-10"
    yes_no_scale = "yes_no_scale"


# ============ MODELS ============

class CheckInResponse(Base):
    __tablename__ = "checkin_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    question_id = Column(String(10), nullable=False)
    dimension = Column(String(30), nullable=False)
    raw_value = Column(Integer, nullable=False)
    scale_max = Column(Integer, nullable=False, default=5)
    normalized_value = Column(Float, nullable=True)

    checkin_date = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="checkin_responses")


class UserMetricSnapshot(Base):
    """Stores the insights calculated after check-in questions."""
    __tablename__ = "user_metric_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    fcs_composite = Column(Float, nullable=True)
    current_stability = Column(Float, nullable=True)
    future_outlook = Column(Float, nullable=True)
    purchasing_power = Column(Float, nullable=True)
    debt_pressure = Column(Float, nullable=True)
    financial_agency = Column(Float, nullable=True)
    bsi_score = Column(Float, nullable=True)
    checkin_count = Column(Integer, default=0)

    computed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="metric_snapshots")


class DailyIndex(Base):
    __tablename__ = "daily_index"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    index_date = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    segment = Column(String(50), nullable=False, default="national")

    fcs_value = Column(Float, nullable=False)
    gf_rwi_composite = Column(Float, nullable=False, default=0.0)
    user_count = Column(Integer, nullable=False, default=0)
    computed_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    trend_direction = Column(String(10), nullable=True)