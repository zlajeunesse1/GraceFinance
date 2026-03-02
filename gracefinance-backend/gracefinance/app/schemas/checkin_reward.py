"""
Reward Loop Schemas — Pydantic models for the reward endpoints.

Place at: app/schemas/checkin_reward.py
"""

from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime, date


class ScoreDelta(BaseModel):
    before: float
    after: float
    direction: str  # "up" | "down" | "flat"


class BehaviorNudge(BaseModel):
    dimension: str
    label: str
    tip: str


class ContributionStatus(BaseModel):
    status: str  # "queued" | "counted" | "pending"
    message: str
    next_update_window: str  # "later today" | "tomorrow morning"


class CheckinReward(BaseModel):
    streak: int
    streak_is_milestone: bool
    grace_summary: str
    deltas: Dict[str, ScoreDelta]
    weakest_dimension: Optional[str] = None
    behavior_nudge: Optional[BehaviorNudge] = None
    contribution: ContributionStatus


class CheckinResponse(BaseModel):
    checkin_id: str
    message: str
    reward: CheckinReward


class TodayStatus(BaseModel):
    has_checked_in_today: bool
    streak: int
    latest_fcs: Optional[float] = None
    fcs_trend: Optional[str] = None  # "up" | "down" | "flat"
    dimension_scores: Optional[Dict[str, float]] = None
    weakest_dimension: Optional[str] = None
    checkin_count_total: int
    contribution_status: Optional[str] = None  # "queued" | "counted" | None
    last_checkin_at: Optional[datetime] = None
