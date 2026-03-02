"""
IndexContributionEvent — Append-only event log for the index pipeline.

Every check-in enqueues one event. The background worker consumes
pending events and rolls them into the DailyIndex.

Place at: app/models/contribution_queue.py
"""

from sqlalchemy import (
    Column, Integer, String, Numeric, DateTime, Date, ForeignKey, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone

from app.database import Base


class IndexContributionEvent(Base):
    __tablename__ = "index_contribution_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    checkin_date = Column(Date, nullable=False)

    # Snapshot of user's scores at time of check-in
    fcs_composite = Column(Numeric(7, 2), nullable=False)
    current_stability = Column(Numeric(7, 2), nullable=True)
    future_outlook = Column(Numeric(7, 2), nullable=True)
    purchasing_power = Column(Numeric(7, 2), nullable=True)
    debt_pressure = Column(Numeric(7, 2), nullable=True)
    financial_agency = Column(Numeric(7, 2), nullable=True)
    bsi_score = Column(Numeric(7, 2), nullable=True)

    # Processing status: "pending" | "processing" | "counted" | "failed"
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    processed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_contrib_queue_status", "status"),
        Index("ix_contrib_queue_user_date", "user_id", "checkin_date", unique=True),
    )
