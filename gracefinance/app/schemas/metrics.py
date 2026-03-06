from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DimensionScores(BaseModel):
    stability: Optional[float] = None        # 0–100
    outlook: Optional[float] = None
    purchasing_power: Optional[float] = None
    emergency_readiness: Optional[float] = None
    financial_agency: Optional[float] = None

class UserMetricsSnapshot(BaseModel):
    fcs_total: Optional[float] = None        # 0–100, null until first check-in
    dimensions: DimensionScores
    streak_count: Optional[int] = None
    checkins_this_week: Optional[int] = None
    last_checkin_at: Optional[datetime] = None
    delta_vs_last: Optional[float] = None
    updated_at: datetime

    class Config:
        from_attributes = True