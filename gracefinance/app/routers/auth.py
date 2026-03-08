"""
Auth Router — v3.0
==================
ADDED:
  - Email verification on signup via support@gracefinance.co
  - 18+ age gate on signup (date_of_birth required)
  - Login blocks unverified accounts with clear message
  - Forgot/reset password now sends real email
  - /auth/verify-email fully wired
"""

import secrets
from collections import defaultdict
from datetime import datetime, date, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.models import User
from app.schemas import (
    UserSignup, UserLogin, UserResponse, UserOnboarding, TokenResponse
)
from app.services.auth import (
    hash_password, verify_password, create_access_token, get_current_user
)
from app.services.email_service import send_verification_email, send_password_reset_email

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Auto-migrate new columns on startup ──────────────────────────────────────
def _ensure_columns(db: Session):
    """Safe to run every startup — IF NOT EXISTS guards prevent errors."""
    try:
        stmts = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_token VARCHAR(128)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_token_expires_at TIMESTAMPTZ",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS date_of_birth DATE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_messages_used INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_reset_date DATE",
            "CREATE INDEX IF NOT EXISTS ix_users_verification_token ON users(verification_token)",
        ]
        for stmt in stmts:
            db.execute(text(stmt))
        db.commit()
    except Exception:
        db.rollback()


# ── Lockout ───────────────────────────────────────────────────────────────────
_login_attempts: dict = defaultdict(lambda: {"count": 0, "locked_until": None})
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


def _check_lockout(email: str):
    state = _login_attempts[email]
    if state["locked_until"] and datetime.now(timezone.utc) < state["locked_until"]:
        remaining = int((state["locked_until"] - datetime.now(timezone.utc)).total_seconds() / 60) + 1
        raise HTTPException(status_code=429, detail=f"Account temporarily locked. Try again in {remaining} minute(s).")
    if state["locked_until"] and datetime.now(timezone.utc) >= state["locked_until"]:
        _login_attempts[email] = {"count": 0, "locked_until": None}


def _record_failed_attempt(email: str) -> dict:
    state = _login_attempts[email]
    state["count"] += 1
    if state["count"] >= MAX_LOGIN_ATTEMPTS:
        state["locked_until"] = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        return {"attempts_remaining": 0, "locked": True}
    return {"attempts_remaining": MAX_LOGIN_ATTEMPTS - state["count"], "locked": False}


def _reset_attempts(email: str):
    _login_attempts[email] = {"count": 0, "locked_until": None}


# ── Reset tokens ──────────────────────────────────────────────────────────────
_reset_tokens: dict = {}
RESET_TOKEN_EXPIRY_MINUTES = 30
VERIFY_TOKEN_EXPIRY_HOURS = 24


# ── Helpers ───────────────────────────────────────────────────────────────────

def _calculate_age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/signup", response_model=TokenResponse, status_code=201)
def signup(data: UserSignup, db: Session = Depends(get_db)):
    """
    Create account. Requires:
      - Unique email
      - date_of_birth (must be 18+)
    Sends verification email immediately after signup.
    """
    _ensure_columns(db)

    # ── 18+ age check ────────────────────────────────────────────────────────
    dob = getattr(data, "date_of_birth", None)
    if dob is None:
        raise HTTPException(status_code=400, detail="Date of birth is required.")
    if _calculate_age(dob) < 18:
        raise HTTPException(status_code=400, detail="You must be 18 or older to use GraceFinance.")

    # ── Duplicate check ──────────────────────────────────────────────────────
    existing = db.query(User).filter(User.email == data.email.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered.")

    # ── Create user ──────────────────────────────────────────────────────────
    verify_token = secrets.token_urlsafe(32)
    verify_expires = datetime.now(timezone.utc) + timedelta(hours=VERIFY_TOKEN_EXPIRY_HOURS)

    user = User(
        email=data.email.lower(),
        hashed_password=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name or "",
        date_of_birth=dob,
        email_verified=False,
        verification_token=verify_token,
        verification_token_expires_at=verify_expires,
        onboarding_completed=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # ── Send verification email (non-blocking — never crashes signup) ────────
    send_verification_email(
        to=user.email,
        first_name=user.first_name,
        token=verify_token,
    )

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """Login. Blocks unverified accounts and locked accounts."""
    email = data.email.lower()
    _check_lockout(email)

    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(data.password, user.hashed_password):
        lockout_info = _record_failed_attempt(email)
        if lockout_info["locked"]:
            raise HTTPException(status_code=429, detail=f"Too many failed attempts. Account locked for {LOCKOUT_DURATION_MINUTES} minutes.")
        remaining = lockout_info["attempts_remaining"]
        raise HTTPException(status_code=401, detail=f"Invalid email or password. {remaining} attempt(s) remaining before lockout.")

    # ── Block unverified accounts ─────────────────────────────────────────────
    if not user.email_verified:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email before logging in. Check your inbox for a link from support@gracefinance.co.",
        )

    _reset_attempts(email)
    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    return UserResponse.model_validate(user)


@router.put("/onboarding", response_model=UserResponse)
def complete_onboarding(
    data: UserOnboarding,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.monthly_income = data.monthly_income
    user.monthly_expenses = data.monthly_expenses
    user.financial_goal = data.financial_goal or ""
    user.onboarding_completed = True
    if data.onboarding_goals is not None:
        user.onboarding_goals = data.onboarding_goals
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.patch("/income", response_model=UserResponse)
def update_income(data: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if "monthly_income" in data and data["monthly_income"] is not None:
        user.monthly_income = float(data["monthly_income"])
    if "monthly_expenses" in data and data["monthly_expenses"] is not None:
        user.monthly_expenses = float(data["monthly_expenses"])
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/verify-email", status_code=200)
def verify_email(data: dict, db: Session = Depends(get_db)):
    """Verify email with token from signup email link."""
    token = (data.get("token") or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Verification token required.")

    user = db.query(User).filter(User.verification_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link.")

    if user.verification_token_expires_at and datetime.now(timezone.utc) > user.verification_token_expires_at:
        raise HTTPException(status_code=400, detail="Verification link expired. Please request a new one.")

    user.email_verified = True
    user.verification_token = None
    user.verification_token_expires_at = None
    db.commit()

    return {"message": "Email verified. You can now log in to GraceFinance."}


@router.post("/resend-verification", status_code=200)
def resend_verification(data: dict, db: Session = Depends(get_db)):
    """Resend verification email. Always returns 200."""
    email = (data.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email required.")

    user = db.query(User).filter(User.email == email).first()
    if user and not user.email_verified:
        token = secrets.token_urlsafe(32)
        user.verification_token = token
        user.verification_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=VERIFY_TOKEN_EXPIRY_HOURS)
        db.commit()
        send_verification_email(to=user.email, first_name=user.first_name, token=token)

    return {"message": "If that email is registered and unverified, a new link has been sent."}


@router.post("/forgot-password", status_code=200)
def forgot_password(data: dict, db: Session = Depends(get_db)):
    """Request password reset. Always returns 200."""
    email = (data.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required.")

    user = db.query(User).filter(User.email == email).first()
    if user:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)
        _reset_tokens[token] = {"email": email, "user_id": str(user.id), "expires_at": expires_at}
        send_password_reset_email(to=user.email, first_name=user.first_name, token=token)

    return {"message": "If that email is registered, you'll receive reset instructions shortly."}


@router.post("/reset-password", status_code=200)
def reset_password(data: dict, db: Session = Depends(get_db)):
    token = (data.get("token") or "").strip()
    new_password = data.get("new_password") or ""

    if not token or not new_password:
        raise HTTPException(status_code=400, detail="Token and new password are required.")
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    token_data = _reset_tokens.get(token)
    if not token_data:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")
    if datetime.now(timezone.utc) > token_data["expires_at"]:
        del _reset_tokens[token]
        raise HTTPException(status_code=400, detail="Reset token has expired. Please request a new one.")

    user = db.query(User).filter(User.email == token_data["email"]).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid reset token.")

    user.hashed_password = hash_password(new_password)
    db.commit()
    del _reset_tokens[token]
    _reset_attempts(token_data["email"])

    return {"message": "Password updated successfully. You can now log in."}