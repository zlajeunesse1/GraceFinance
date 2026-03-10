"""
GraceFinance — Profile Schemas
ProfileRead: response model (all fields)
ProfileUpdate: partial update (all optional, exclude_unset pattern)

v6: Added income, expenses, debt, goals, mission fields.
"""

from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class ProfileRead(BaseModel):
    """Full profile response — matches UserProfile model columns."""
    model_config = ConfigDict(from_attributes=True)

    display_name: Optional[str] = None
    timezone: str = "America/New_York"
    currency: str = "USD"

    # Financial snapshot
    income: Optional[float] = None
    expenses: Optional[float] = None
    debt: Optional[float] = None

    # Goals & mission
    goals: Optional[List[str]] = None
    mission: Optional[str] = None

    # Platform settings
    onboarding_completed: bool = False
    risk_style: Optional[str] = "balanced"

    # Metadata (read-only)
    profile_completion_score: int = 0


class ProfileUpdate(BaseModel):
    """
    Partial update — only provided fields are applied.
    Used with payload.model_dump(exclude_unset=True) in the router.
    """
    model_config = ConfigDict(extra="forbid")

    display_name: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    risk_style: Optional[str] = None

    # Financial snapshot
    income: Optional[float] = None
    expenses: Optional[float] = None
    debt: Optional[float] = None

    # Goals & mission
    goals: Optional[List[str]] = None
    mission: Optional[str] = None