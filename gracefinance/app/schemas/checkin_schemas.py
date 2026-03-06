"""
Schemas for check-in questions, responses, metrics, and the GF-RWI index.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Union
from datetime import datetime, date
from uuid import UUID


# ══════════════════════════════════════════
#  CHECK-IN QUESTION SCHEMAS (served to frontend)
# ══════════════════════════════════════════

class QuestionOut(BaseModel):
    question_id: str
    question_text: str
    dimension: str
    scale_type: str       # "1-5", "1-10", "yes_no_scale"
    scale_max: int
    low_label: str = "Low"
    high_label: str = "High"
    is_weekly: bool = False


class TodaysQuestionsOut(BaseModel):
    date: str
    daily_questions: List[QuestionOut]
    weekly_questions: List[QuestionOut]
    is_weekly_day: bool
    already_completed: bool = False


# ══════════════════════════════════════════
#  CHECK-IN RESPONSE SCHEMAS (received from frontend)
# ══════════════════════════════════════════

class SingleAnswer(BaseModel):
    question_id: str          # e.g. "CS-1", "BX-3"
    raw_value: int = Field(ge=1)  # user's answer


class CheckInSubmit(BaseModel):
    answers: List[SingleAnswer]


class CheckInResponseOut(BaseModel):
    question_id: str
    dimension: str
    raw_value: int
    normalized_value: float
    checkin_date: datetime

    class Config:
        from_attributes = True


class CheckInSubmitResult(BaseModel):
    message: str
    responses_saved: int
    fcs_snapshot: Optional[float] = None


# ══════════════════════════════════════════
#  USER METRIC SCHEMAS
# ══════════════════════════════════════════

class UserMetricOut(BaseModel):
    computed_at: datetime
    current_stability: Optional[float] = None
    future_outlook: Optional[float] = None
    purchasing_power: Optional[float] = None
    emergency_readiness: Optional[float] = None
    financial_agency: Optional[float] = None
    fcs_composite: Optional[float] = None
    bsi_score: Optional[float] = None
    checkin_count: int = 0

    class Config:
        from_attributes = True


class UserMetricHistory(BaseModel):
    user_id: Union[UUID, str]

    snapshots: List[UserMetricOut]


# ══════════════════════════════════════════
#  INDEX SCHEMAS (GF-RWI)
# ══════════════════════════════════════════

class IndexOut(BaseModel):
    index_date: datetime
    segment: str
    gf_rwi_composite: float
    fcs_value: float
    fcs_current_stability: float
    fcs_future_outlook: float
    fcs_purchasing_power: float
    fcs_emergency_readiness: float
    fcs_financial_agency: float
    bsi_value: Optional[float] = None
    spi_value: Optional[float] = None
    user_count: int

    class Config:
        from_attributes = True


class IndexHistory(BaseModel):
    segment: str
    data_points: List[IndexOut]