from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import (
    UserSignup, UserLogin, UserResponse, UserOnboarding, TokenResponse
)
from app.services.auth import (
    hash_password, verify_password, create_access_token, get_current_user
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=TokenResponse, status_code=201)
def signup(data: UserSignup, db: Session = Depends(get_db)):
    """Create a new user account."""
    # Check if email already exists
    existing = db.query(User).filter(User.email == data.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=data.email.lower(),
        hashed_password=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name or "",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """Login with email and password."""
    user = db.query(User).filter(User.email == data.email.lower()).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    """Get current authenticated user profile."""
    return UserResponse.model_validate(user)


@router.put("/onboarding", response_model=UserResponse)
def complete_onboarding(
    data: UserOnboarding,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save onboarding financial profile data."""
    user.monthly_income = data.monthly_income
    user.monthly_expenses = data.monthly_expenses
    user.financial_goal = data.financial_goal
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)
