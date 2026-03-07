"""
GraceFinance — CheckIn Models v4.0
═══════════════════════════════════
CHANGES FROM v3:
  - UserMetricSnapshot.fcs_behavior added (behavior component 0-100)
  - UserMetricSnapshot.fcs_consistency added (consistency component 0-100)
  - UserMetricSnapshot.fcs_trend added (trend component 0-100)
  - UserMetricSnapshot.fcs_slope_7d added (7-day composite slope)
  - UserMetricSnapshot.fcs_slope_30d added (30-day composite slope)

Place at: app/models/checkin.py
"""

import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    Enum as SQLEnum, ForeignKey, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


# ═══════════════════ ENUMS ═══════════════════

class FCSDimension(str, enum.Enum):
    current_stability    = "current_stability"
    future_outlook       = "future_outlook"
    purchasing_power     = "purchasing_power"
    emergency_readiness  = "emergency_readiness"
    financial_agency     = "financial_agency"


class ScaleType(str, enum.Enum):
    scale_1_5      = "1-5"
    scale_1_10     = "1-10"
    yes_no_scale   = "yes_no_scale"


# ═══════════════════ CHECK-IN RESPONSE ═══════════════════

class CheckInResponse(Base):
    __tablename__ = "checkin_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    question_id      = Column(String(20), nullable=False)
    dimension        = Column(String(50), nullable=False)
    raw_value        = Column(Integer, nullable=False)
    scale_max        = Column(Integer, nullable=False, default=5)
    normalized_value = Column(Float, nullable=True)

    checkin_date     = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    user = relationship("User", back_populates="checkin_responses")

    __table_args__ = (
        Index("ix_checkin_user_date", "user_id", "checkin_date"),
        Index("ix_checkin_dimension", "dimension"),
    )


# ═══════════════════ USER METRIC SNAPSHOT ═══════════════════

class UserMetricSnapshot(Base):
    __tablename__ = "user_metric_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── 5 Locked FCS Dimensions (0.0-1.0 averages) ──────────────────────────
    current_stability   = Column(Float, nullable=True)
    future_outlook      = Column(Float, nullable=True)
    purchasing_power    = Column(Float, nullable=True)
    emergency_readiness = Column(Float, nullable=True)
    financial_agency    = Column(Float, nullable=True)

    # ── Three-Component FCS Formula (v5) ─────────────────────────────────────
    fcs_behavior    = Column(Float, nullable=True)   # behavior component (0-100)
    fcs_consistency = Column(Float, nullable=True)   # consistency component (0-100)
    fcs_trend       = Column(Float, nullable=True)   # trend component (0-100)

    # ── FCS Scores ────────────────────────────────────────────────────────────
    fcs_raw        = Column(Float, nullable=True)    # three-component composite pre-EMA
    fcs_composite  = Column(Float, nullable=True)    # EMA-smoothed score (display)
    fcs_confidence = Column(Float, nullable=False, default=0.0)

    # ── Per-User Drift Detection ─────────────────────────────────────────────
    fcs_slope_7d   = Column(Float, nullable=True)    # 7-day slope of fcs_composite
    fcs_slope_30d  = Column(Float, nullable=True)    # 30-day slope of fcs_composite

    # ── Behavioral Shift ──────────────────────────────────────────────────────
    bsi_score  = Column(Float, nullable=True)
    bsi_shock  = Column(Boolean, nullable=False, default=False)

    # ── Meta ──────────────────────────────────────────────────────────────────
    checkin_count = Column(Integer, default=0)
    computed_at   = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    user = relationship("User", back_populates="metric_snapshots")

    __table_args__ = (
        Index("ix_snapshot_user_computed", "user_id", "computed_at"),
    )


# ═══════════════════ DAILY INDEX ═══════════════════

class DailyIndex(Base):
    __tablename__ = "daily_index"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    index_date   = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    segment      = Column(String(50), nullable=False, default="national")

    fcs_value         = Column(Float, nullable=False)
    gf_rwi_composite  = Column(Float, nullable=False, default=0.0)
    user_count        = Column(Integer, nullable=False, default=0)
    computed_at       = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    trend_direction    = Column(String(10), nullable=True)
    gci_slope_3d       = Column(Float, nullable=True)
    gci_slope_7d       = Column(Float, nullable=True)
    gci_volatility_7d  = Column(Float, nullable=True)

    __table_args__ = (
        Index("ix_daily_index_date_segment", "index_date", "segment"),
    )