"""
GraceFinance Models — Core SQLAlchemy ORM models.
NOTE: CheckInResponse & UserMetricSnapshot live in checkin.py
NOTE: UserProfile lives in profile.py
"""

import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date, Text,
    ForeignKey, Numeric, Index,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


# ═══════════════════ ENUMS ═══════════════════

class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"


class DebtType(str, enum.Enum):
    CREDIT_CARD = "credit_card"
    CAR_LOAN = "car_loan"
    STUDENT_LOAN = "student_loan"
    PERSONAL_LOAN = "personal_loan"
    MORTGAGE = "mortgage"
    OTHER = "other"


class TransactionCategory(str, enum.Enum):
    INCOME = "Income"
    RENT = "Rent"
    FOOD = "Food"
    GAS = "Gas"
    CREDIT_CARDS = "Credit Cards"
    INSURANCE = "Insurance"
    PHONE_BILL = "Phone Bill"
    UTILITIES = "Utilities"
    PERSONAL = "Personal"
    OTHER = "Other"


class BillStatus(str, enum.Enum):
    PAID = "paid"
    UPCOMING = "upcoming"
    OVERDUE = "overdue"


# ═══════════════════ USER ═══════════════════

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), default="")

    email_verified = Column(Boolean, default=False, nullable=False)

    monthly_income = Column(Numeric(12, 2), default=0)
    monthly_expenses = Column(Numeric(12, 2), default=0)
    financial_goal = Column(Text, default="")

    onboarding_completed = Column(Boolean, default=False, nullable=False)
    onboarding_goals = Column(JSON, nullable=True)

    subscription_tier = Column(SQLEnum(SubscriptionTier), default=SubscriptionTier.FREE)
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_checkin_at = Column(DateTime(timezone=True), nullable=True)

    # ── Relationships (each defined ONCE) ──
    profile = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    checkin_responses = relationship(
        "CheckInResponse",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    metric_snapshots = relationship(
        "UserMetricSnapshot",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    debts = relationship(
        "Debt",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    transactions = relationship(
        "Transaction",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    bills = relationship(
        "Bill",
        back_populates="user",
        cascade="all, delete-orphan",
    )


# ═══════════════════ DEBT ═══════════════════

class Debt(Base):
    __tablename__ = "debts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(200), nullable=False)
    debt_type = Column(SQLEnum(DebtType), default=DebtType.OTHER)
    balance = Column(Numeric(12, 2), default=0)
    apr = Column(Float, default=0.0)
    min_payment = Column(Numeric(12, 2), default=0)
    credit_limit = Column(Numeric(12, 2), nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="debts")


# ═══════════════════ TRANSACTION ═══════════════════

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    date = Column(DateTime(timezone=True), nullable=False)
    description = Column(String(500), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    category = Column(SQLEnum(TransactionCategory), default=TransactionCategory.OTHER)
    is_need = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="transactions")


# ═══════════════════ BILL ═══════════════════

class Bill(Base):
    __tablename__ = "bills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(200), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    due_day = Column(Integer, nullable=False)
    status = Column(SQLEnum(BillStatus), default=BillStatus.UPCOMING)
    is_recurring = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="bills")