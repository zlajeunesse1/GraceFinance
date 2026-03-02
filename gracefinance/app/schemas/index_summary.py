"""
Index Summary Schemas — Pydantic models for the index summary endpoint.

Place at: app/schemas/index_summary.py
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date


class IndexCurrent(BaseModel):
    date: date
    gci: float
    csi: float
    dpi: float
    frs: float
    trend_direction: Optional[str] = None
    gci_slope_7d: Optional[float] = None


class UserContribution(BaseModel):
    status: str
    counted_in: Optional[str] = None
    expected_direction: Optional[str] = None


class ChangelogEntry(BaseModel):
    metric: str
    delta: float
    direction: str


class IndexSummaryResponse(BaseModel):
    current: Optional[IndexCurrent] = None
    last_updated_at: Optional[datetime] = None
    next_update_window: str
    user_contribution: UserContribution
    changelog: List[ChangelogEntry]
    active_contributors_today: int