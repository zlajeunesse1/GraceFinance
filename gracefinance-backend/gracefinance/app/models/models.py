from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text,
    ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


# ============ ENUMS ============

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


# ============ MODELS ============

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), default="")

    # Financial profile (from onboarding)
    monthly_income = Column(Float, default=0.0)
    monthly_expenses = Column(Float, default=0.0)
    financial_goal = Column(Text, default="")

    # Subscription
    subscription_tier = Column(
        SQLEnum(SubscriptionTier), default=SubscriptionTier.FREE
    )
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    debts = relationship("Debt", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    bills = relationship("Bill", back_populates="user", cascade="all, delete-orphan")
    checkin_answers = relationship("CheckinAnswer", back_populates="user")
    checkin_sessions = relationship("CheckinSession", back_populates="user")
    checkin_streak = relationship("CheckinStreak", back_populates="user", uselist=False)


class Debt(Base):
    __tablename__ = "debts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    name = Column(String(200), nullable=False)  # "Credit One Visa"
    debt_type = Column(SQLEnum(DebtType), default=DebtType.CREDIT_CARD)
    balance = Column(Float, nullable=False)
    apr = Column(Float, nullable=False)  # Stored as decimal: 0.29 = 29%
    min_payment = Column(Float, default=0.0)
    credit_limit = Column(Float, nullable=True)  # Only for credit cards
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="debts")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    date = Column(DateTime(timezone=True), nullable=False)
    description = Column(String(500), nullable=False)
    amount = Column(Float, nullable=False)  # Negative = expense, Positive = income
    category = Column(SQLEnum(TransactionCategory), default=TransactionCategory.OTHER)
    is_need = Column(Boolean, default=False)  # True = need, False = personal/want

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="transactions")


class Bill(Base):
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    name = Column(String(200), nullable=False)
    amount = Column(Float, nullable=False)
    due_day = Column(Integer, nullable=False)  # Day of month (1-31)
    category = Column(String(100), default="other")
    status = Column(SQLEnum(BillStatus), default=BillStatus.UPCOMING)
    is_recurring = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="bills")
