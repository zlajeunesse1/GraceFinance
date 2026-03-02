"""
DailyIndex Model — Platform-wide aggregated index values.

One row per calendar date. Contains CSI, DPI, FRS, GCI, supporting stats,
and trend/volatility metrics for the GCI headline number.

Updated nightly via scheduled job — never inline with user check-ins.
"""

import uuid
import enum

from sqlalchemy import Column, Integer, Numeric, String, Date, Enum, Index as SQLIndex, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base



class TrendDirectionEnum(str, enum.Enum):
    """GCI trend classification. Stored as string in DB for readability."""
    UP = "UP"
    DOWN = "DOWN"
    FLAT = "FLAT"


class DailyIndex(Base):
    __tablename__ = "daily_indexes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(Date, nullable=False)

    # Sub-indexes (0–100)
    csi_close = Column(Numeric(5, 2), nullable=False)
    dpi_close = Column(Numeric(5, 2), nullable=False)
    frs_close = Column(Numeric(5, 2), nullable=False)
    gci_close = Column(Numeric(5, 2), nullable=False)

    # Supporting stats
    checkin_volume = Column(Integer, nullable=False, default=0)
    avg_mood_score = Column(Numeric(4, 2), nullable=True)
    avg_stress_level = Column(Numeric(4, 2), nullable=True)
    impulse_rate = Column(Numeric(5, 4), nullable=True)  # Percentage as decimal

    # --- GCI Trend Metrics (added in v1.1) ---
    # OLS slope of GCI over last 3 days. Units: GCI points per day.
    gci_slope_3d = Column(Numeric(7, 4), nullable=True)
    # OLS slope of GCI over last 7 days. Units: GCI points per day.
    gci_slope_7d = Column(Numeric(7, 4), nullable=True)
    # Population std dev of GCI over last 7 days. Units: GCI points.
    gci_volatility_7d = Column(Numeric(7, 4), nullable=True)
    # Trend classification derived from gci_slope_7d.
    # UP (slope > +0.5), DOWN (slope < -0.5), FLAT (else).
    trend_direction = Column(String(10), nullable=True, default="FLAT")

    __table_args__ = (
        UniqueConstraint("date", name="uq_daily_index_date"),
        SQLIndex("ix_daily_index_date", "date"),
    )

    def __repr__(self):
        return (
            f"<DailyIndex date={self.date} GCI={self.gci_close} "
            f"trend={self.trend_direction}>"
        )
