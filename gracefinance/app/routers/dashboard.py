from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app.models import User, Debt, Transaction, Bill
from app.schemas import (
    DashboardResponse, UserResponse, DebtResponse,
    TransactionResponse, BillResponse
)
from app.services.auth import get_current_user
from app.services.finance import (
    calculate_avalanche, months_to_debt_free,
    calculate_credit_utilization, calculate_spending_breakdown
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/", response_model=DashboardResponse)
def get_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    The main dashboard endpoint.
    Returns everything the React frontend needs in a single API call:
    user profile, debts, bills, recent transactions, and all calculated metrics.
    """

    # Fetch user's data
    debts = (
        db.query(Debt)
        .filter(Debt.user_id == user.id, Debt.is_active == True)
        .order_by(Debt.apr.desc())
        .all()
    )

    bills = (
        db.query(Bill)
        .filter(Bill.user_id == user.id)
        .order_by(Bill.due_day)
        .all()
    )

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == user.id, Transaction.date >= cutoff)
        .order_by(Transaction.date.desc())
        .limit(50)
        .all()
    )

    # ============ CALCULATIONS (your Python logic) ============

    # Available monthly
    available = user.monthly_income - user.monthly_expenses

    # Savings rate
    savings_rate = (
        (available / user.monthly_income * 100) if user.monthly_income > 0 else 0
    )

    # Total debt
    total_debt = sum(d.balance for d in debts)

    # Prepare debt dicts for calculation functions
    debt_dicts = [
        {
            "name": d.name,
            "balance": d.balance,
            "apr": d.apr,
            "min_payment": d.min_payment,
            "credit_limit": d.credit_limit,
        }
        for d in debts
    ]

    # Avalanche allocation
    available_for_debt = max(available, 0)
    avalanche_result = calculate_avalanche(debt_dicts, available_for_debt)

    # Debt-free timeline
    debt_free = months_to_debt_free(debt_dicts, available_for_debt)
    accelerated = int(debt_free * 0.7) if debt_free else None

    # Credit utilization
    credit_info = calculate_credit_utilization(debt_dicts)

    # Spending breakdown
    txn_dicts = [
        {"amount": t.amount, "category": t.category}
        for t in transactions
    ]
    spending = calculate_spending_breakdown(txn_dicts)

    # ============ BUILD RESPONSE ============

    debt_responses = []
    for d in debts:
        resp = DebtResponse.model_validate(d)
        if d.credit_limit and d.credit_limit > 0:
            resp.utilization = round(d.balance / d.credit_limit * 100, 1)
        debt_responses.append(resp)

    return DashboardResponse(
        user=UserResponse.model_validate(user),
        debts=debt_responses,
        bills=[BillResponse.model_validate(b) for b in bills],
        recent_transactions=[
            TransactionResponse.model_validate(t) for t in transactions
        ],
        total_debt=round(total_debt, 2),
        available_monthly=round(available, 2),
        savings_rate=round(savings_rate, 1),
        credit_utilization=credit_info["overall"],
        debt_free_months=debt_free,
        accelerated_months=accelerated,
        needs_spend=spending["needs"],
        personal_spend=spending["personal"],
        avalanche_allocations=avalanche_result["allocations"],
    )
