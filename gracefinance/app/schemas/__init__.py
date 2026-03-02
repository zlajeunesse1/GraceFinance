from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models.models import SubscriptionTier, DebtType, TransactionCategory, BillStatus


# ============ AUTH SCHEMAS ============

class UserSignup(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: Optional[str] = ""


class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


# ============ USER SCHEMAS ============

class UserResponse(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    monthly_income: float
    monthly_expenses: float
    financial_goal: str
    subscription_tier: SubscriptionTier
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserOnboarding(BaseModel):
    monthly_income: float
    monthly_expenses: float
    financial_goal: str


# ============ DEBT SCHEMAS ============

class DebtCreate(BaseModel):
    name: str
    debt_type: DebtType = DebtType.CREDIT_CARD
    balance: float
    apr: float
    min_payment: float = 0.0
    credit_limit: Optional[float] = None


class DebtResponse(BaseModel):
    id: UUID
    name: str
    debt_type: DebtType
    balance: float
    apr: float
    min_payment: float
    credit_limit: Optional[float]
    is_active: bool
    utilization: Optional[float] = None

    class Config:
        from_attributes = True


class DebtUpdate(BaseModel):
    name: Optional[str] = None
    balance: Optional[float] = None
    apr: Optional[float] = None
    min_payment: Optional[float] = None
    credit_limit: Optional[float] = None


# ============ TRANSACTION SCHEMAS ============

class TransactionCreate(BaseModel):
    date: datetime
    description: str
    amount: float
    category: Optional[TransactionCategory] = None


class TransactionResponse(BaseModel):
    id: UUID
    date: datetime
    description: str
    amount: float
    category: TransactionCategory
    is_need: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ BILL SCHEMAS ============

class BillCreate(BaseModel):
    name: str
    amount: float
    due_day: int
    category: str = "other"
    is_recurring: bool = True


class BillResponse(BaseModel):
    id: UUID
    name: str
    amount: float
    due_day: int
    category: str
    status: BillStatus
    is_recurring: bool

    class Config:
        from_attributes = True


class BillUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    due_day: Optional[int] = None
    status: Optional[BillStatus] = None


# ============ DASHBOARD SCHEMAS ============

class DashboardResponse(BaseModel):
    user: UserResponse
    debts: list[DebtResponse]
    bills: list[BillResponse]
    recent_transactions: list[TransactionResponse]

    total_debt: float
    available_monthly: float
    savings_rate: float
    credit_utilization: float
    debt_free_months: Optional[int]
    accelerated_months: Optional[int]
    needs_spend: float
    personal_spend: float

    avalanche_allocations: list[dict]


class AvalancheAllocation(BaseModel):
    name: str
    apr: float
    payment: float
    stage: str
    balance_after: float


# ============ STRIPE SCHEMAS ============

class CheckoutRequest(BaseModel):
    tier: str


class CheckoutResponse(BaseModel):
    checkout_url: str


# Resolve forward reference
TokenResponse.model_rebuild()