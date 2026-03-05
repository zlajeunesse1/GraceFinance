"""
GraceFinance — CheckIn Models v3.0
═══════════════════════════════════
CHANGES FROM v2:
  - UserMetricSnapshot.debt_pressure → emergency_readiness
  - UserMetricSnapshot.fcs_raw added (pre-EMA score)
  - UserMetricSnapshot.fcs_confidence added (data coverage %)
  - UserMetricSnapshot.bsi_shock added (shock detection flag)
  - FCSDimension enum updated to match locked pillars
  - DailyIndex trend columns preserved

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
    """Locked FCS pillars — do not add/remove without a migration."""
    current_stability    = "current_stability"
    future_outlook       = "future_outlook"
    purchasing_power     = "purchasing_power"
    emergency_readiness  = "emergency_readiness"   # was: debt_pressure
    financial_agency     = "financial_agency"


class ScaleType(str, enum.Enum):
    scale_1_5      = "1-5"
    scale_1_10     = "1-10"
    yes_no_scale   = "yes_no_scale"


# ═══════════════════ CHECK-IN RESPONSE ═══════════════════

class CheckInResponse(Base):
    """
    One row per question answered per session.
    normalized_value is ALWAYS 0.0–1.0 using (raw-1)/(scale_max-1).
    Inverted questions are flipped at save time in checkin_service.
    """
    __tablename__ = "checkin_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    question_id      = Column(String(20), nullable=False)    # e.g. "CS-1", "ER-3"
    dimension        = Column(String(50), nullable=False)    # e.g. "current_stability"
    raw_value        = Column(Integer, nullable=False)
    scale_max        = Column(Integer, nullable=False, default=5)
    normalized_value = Column(Float, nullable=True)          # 0.0–1.0

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
    """
    Computed after each check-in session.
    Stores both raw FCS and EMA-smoothed FCS for full data transparency.
    Institutional use: fcs_raw for real-time signal, fcs_composite for trend.
    """
    __tablename__ = "user_metric_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── 5 Locked FCS Dimensions (0.0–1.0 averages) ──────────────────────────
    current_stability   = Column(Float, nullable=True)
    future_outlook      = Column(Float, nullable=True)
    purchasing_power    = Column(Float, nullable=True)
    emergency_readiness = Column(Float, nullable=True)   # replaces debt_pressure
    financial_agency    = Column(Float, nullable=True)

    # ── FCS Scores ────────────────────────────────────────────────────────────
    fcs_raw        = Column(Float, nullable=True)   # today's weighted composite (0–100), pre-EMA
    fcs_composite  = Column(Float, nullable=True)   # EMA-smoothed score (0–100) — use for display
    fcs_confidence = Column(Float, nullable=False, default=0.0)  # data coverage % (0–100)

    # ── Behavioral Shift ──────────────────────────────────────────────────────
    bsi_score  = Column(Float, nullable=True)              # -100 to +100
    bsi_shock  = Column(Boolean, nullable=False, default=False)  # True if swing > threshold

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
    """
    GF-RWI community index. One row per segment per day.
    Aggregated from all users' fcs_composite scores.
    """
    __tablename__ = "daily_index"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    index_date   = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    segment      = Column(String(50), nullable=False, default="national")

    fcs_value         = Column(Float, nullable=False)
    gf_rwi_composite  = Column(Float, nullable=False, default=0.0)
    user_count        = Column(Integer, nullable=False, default=0)
    computed_at       = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Trend fields (populated by intelligence_engine.compute_index_trend_fields)
    trend_direction    = Column(String(10), nullable=True)   # UP / DOWN / FLAT
    gci_slope_3d       = Column(Float, nullable=True)
    gci_slope_7d       = Column(Float, nullable=True)
    gci_volatility_7d  = Column(Float, nullable=True)

    __table_args__ = (
        Index("ix_daily_index_date_segment", "index_date", "segment"),
    )