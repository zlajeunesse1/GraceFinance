from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app.models import User, Transaction
from app.schemas import TransactionCreate, TransactionResponse
from app.services.auth import get_current_user
from app.services.finance import categorize_transaction, is_need

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("/", response_model=list[TransactionResponse])
def list_transactions(
    days: int = Query(30, description="Number of days to look back"),
    limit: int = Query(50, description="Max transactions to return"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get recent transactions for the current user."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == user.id, Transaction.date >= cutoff)
        .order_by(Transaction.date.desc())
        .limit(limit)
        .all()
    )

    return [TransactionResponse.model_validate(t) for t in transactions]


@router.post("/", response_model=TransactionResponse, status_code=201)
def create_transaction(
    data: TransactionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add a new transaction.
    If no category is provided, auto-categorizes using the GraceFinance engine
    (ported from your Streamlit categorize() function).
    """
    # Auto-categorize if not provided
    category = data.category or categorize_transaction(data.description)

    transaction = Transaction(
        user_id=user.id,
        date=data.date,
        description=data.description,
        amount=data.amount,
        category=category,
        is_need=is_need(category),
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return TransactionResponse.model_validate(transaction)


@router.post("/bulk", response_model=list[TransactionResponse], status_code=201)
def create_transactions_bulk(
    transactions: list[TransactionCreate],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Bulk import transactions (useful for CSV uploads or Plaid sync).
    Auto-categorizes each transaction.
    """
    created = []
    for data in transactions:
        category = data.category or categorize_transaction(data.description)
        txn = Transaction(
            user_id=user.id,
            date=data.date,
            description=data.description,
            amount=data.amount,
            category=category,
            is_need=is_need(category),
        )
        db.add(txn)
        created.append(txn)

    db.commit()
    for txn in created:
        db.refresh(txn)

    return [TransactionResponse.model_validate(t) for t in created]


@router.delete("/{transaction_id}", status_code=204)
def delete_transaction(
    transaction_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a transaction."""
    txn = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == user.id)
        .first()
    )
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(txn)
    db.commit()
