"""
Bills Router — FIXED: UUID path parameters (was int, would crash on UUID PKs)
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Bill
from app.schemas import BillCreate, BillResponse, BillUpdate
from app.services.auth import get_current_user

router = APIRouter(prefix="/bills", tags=["Bills"])


@router.get("/", response_model=list[BillResponse])
def list_bills(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all bills for the current user, ordered by due date."""
    bills = (
        db.query(Bill)
        .filter(Bill.user_id == user.id)
        .order_by(Bill.due_day)
        .all()
    )
    return [BillResponse.model_validate(b) for b in bills]


@router.post("/", response_model=BillResponse, status_code=201)
def create_bill(
    data: BillCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a new recurring bill."""
    bill = Bill(
        user_id=user.id,
        name=data.name,
        amount=data.amount,
        due_day=data.due_day,
        category=data.category,
        is_recurring=data.is_recurring,
    )
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return BillResponse.model_validate(bill)


@router.put("/{bill_id}", response_model=BillResponse)
def update_bill(
    bill_id: UUID,                                    # ← was int
    data: BillUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a bill (amount, status, due date)."""
    bill = (
        db.query(Bill)
        .filter(Bill.id == bill_id, Bill.user_id == user.id)
        .first()
    )
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    if data.name is not None:
        bill.name = data.name
    if data.amount is not None:
        bill.amount = data.amount
    if data.due_day is not None:
        bill.due_day = data.due_day
    if data.status is not None:
        bill.status = data.status

    db.commit()
    db.refresh(bill)
    return BillResponse.model_validate(bill)


@router.delete("/{bill_id}", status_code=204)
def delete_bill(
    bill_id: UUID,                                    # ← was int
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a bill."""
    bill = (
        db.query(Bill)
        .filter(Bill.id == bill_id, Bill.user_id == user.id)
        .first()
    )
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    db.delete(bill)
    db.commit()