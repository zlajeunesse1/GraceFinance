from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Debt
from app.schemas import DebtCreate, DebtResponse, DebtUpdate
from app.services.auth import get_current_user

router = APIRouter(prefix="/debts", tags=["Debts"])


@router.get("/", response_model=list[DebtResponse])
def list_debts(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all active debts for the current user."""
    debts = (
        db.query(Debt)
        .filter(Debt.user_id == user.id, Debt.is_active == True)
        .order_by(Debt.apr.desc())  # Highest APR first (avalanche order)
        .all()
    )

    result = []
    for debt in debts:
        resp = DebtResponse.model_validate(debt)
        if debt.credit_limit and debt.credit_limit > 0:
            resp.utilization = round(debt.balance / debt.credit_limit * 100, 1)
        result.append(resp)

    return result


@router.post("/", response_model=DebtResponse, status_code=201)
def create_debt(
    data: DebtCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a new debt."""
    debt = Debt(
        user_id=user.id,
        name=data.name,
        debt_type=data.debt_type,
        balance=data.balance,
        apr=data.apr,
        min_payment=data.min_payment,
        credit_limit=data.credit_limit,
    )
    db.add(debt)
    db.commit()
    db.refresh(debt)

    resp = DebtResponse.model_validate(debt)
    if debt.credit_limit and debt.credit_limit > 0:
        resp.utilization = round(debt.balance / debt.credit_limit * 100, 1)
    return resp


@router.put("/{debt_id}", response_model=DebtResponse)
def update_debt(
    debt_id: int,
    data: DebtUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an existing debt (e.g., new balance after payment)."""
    debt = (
        db.query(Debt)
        .filter(Debt.id == debt_id, Debt.user_id == user.id)
        .first()
    )
    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found")

    if data.name is not None:
        debt.name = data.name
    if data.balance is not None:
        debt.balance = data.balance
    if data.apr is not None:
        debt.apr = data.apr
    if data.min_payment is not None:
        debt.min_payment = data.min_payment
    if data.credit_limit is not None:
        debt.credit_limit = data.credit_limit

    db.commit()
    db.refresh(debt)

    resp = DebtResponse.model_validate(debt)
    if debt.credit_limit and debt.credit_limit > 0:
        resp.utilization = round(debt.balance / debt.credit_limit * 100, 1)
    return resp


@router.delete("/{debt_id}", status_code=204)
def delete_debt(
    debt_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft-delete a debt (marks inactive)."""
    debt = (
        db.query(Debt)
        .filter(Debt.id == debt_id, Debt.user_id == user.id)
        .first()
    )
    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found")

    debt.is_active = False
    db.commit()
