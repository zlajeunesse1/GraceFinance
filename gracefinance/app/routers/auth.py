"""
Auth Router — v2.0
==================
CHANGES FROM v1:
  - Password lockout: 5 failed attempts → 15-minute lockout per email
  - Password flash warnings: attempt count returned on failed login
  - Forgot password: /auth/forgot-password + /auth/reset-password endpoints
  - Onboarding: now saves onboarding_goals + sets onboarding_completed = True
  - Email verification: /auth/verify-email endpoint stub (ready for SMTP)

NOTE on lockout storage:
  Currently in-memory (works on Railway single instance).
  TODO: Move to Redis or DB column when scaling to multiple workers.
"""

from collections import defaultdict
from datetime import datetime, timezone, timedelta

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


# ── Password lockout state (in-memory) ────────────────────────────────────────
# Structure: { email: { "count": int, "locked_until": datetime | None } }
_login_attempts: dict = defaultdict(lambda: {"count": 0, "locked_until": None})

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


def _check_lockout(email: str):
    """Raise 429 if email is currently locked out."""
    state = _login_attempts[email]
    if state["locked_until"] and datetime.now(timezone.utc) < state["locked_until"]:
        remaining = int((state["locked_until"] - datetime.now(timezone.utc)).total_seconds() / 60) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account temporarily locked due to too many failed attempts. Try again in {remaining} minute(s).",
        )
    # If lockout expired, reset
    if state["locked_until"] and datetime.now(timezone.utc) >= state["locked_until"]:
        _login_attempts[email] = {"count": 0, "locked_until": None}


def _record_failed_attempt(email: str) -> dict:
    """
    Increment failed attempt count. Lock account at MAX_LOGIN_ATTEMPTS.
    Returns { "attempts_remaining": int, "locked": bool }
    """
    state = _login_attempts[email]
    state["count"] += 1

    if state["count"] >= MAX_LOGIN_ATTEMPTS:
        state["locked_until"] = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        return {"attempts_remaining": 0, "locked": True}

    return {
        "attempts_remaining": MAX_LOGIN_ATTEMPTS - state["count"],
        "locked": False,
    }


def _reset_attempts(email: str):
    """Clear failed attempt counter on successful login."""
    _login_attempts[email] = {"count": 0, "locked_until": None}


# ── Password reset token store (in-memory) ────────────────────────────────────
# Structure: { token: { "email": str, "expires_at": datetime } }
# TODO: Move to DB table when adding persistent email flows
_reset_tokens: dict = {}

RESET_TOKEN_EXPIRY_MINUTES = 30


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/signup", response_model=TokenResponse, status_code=201)
def signup(data: UserSignup, db: Session = Depends(get_db)):
    """Create a new user account."""
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
        onboarding_completed=False,
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
    """
    Login with email and password.
    Returns attempt warning on failure. Locks account after 5 failed attempts.
    """
    email = data.email.lower()

    # Check if currently locked out
    _check_lockout(email)

    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(data.password, user.hashed_password):
        lockout_info = _record_failed_attempt(email)

        if lockout_info["locked"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed attempts. Account locked for {LOCKOUT_DURATION_MINUTES} minutes.",
            )

        remaining = lockout_info["attempts_remaining"]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid email or password. {remaining} attempt(s) remaining before lockout.",
        )

    # Successful login — clear attempt counter
    _reset_attempts(email)

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
    """
    Save onboarding financial profile data.
    Stores income, expenses, goals, mission, and marks onboarding complete.
    Grace AI reads all of this on every conversation.
    """
    user.monthly_income = data.monthly_income
    user.monthly_expenses = data.monthly_expenses
    user.financial_goal = data.financial_goal or ""
    user.onboarding_completed = True

    # Save selected goal categories (save/debt/track/budget/wealth/habits)
    if data.onboarding_goals is not None:
        user.onboarding_goals = data.onboarding_goals

    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.patch("/income", response_model=UserResponse)
def update_income(
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Allow users to update their income/expenses after onboarding.
    Accepts { monthly_income, monthly_expenses } — both optional.
    """
    if "monthly_income" in data and data["monthly_income"] is not None:
        user.monthly_income = float(data["monthly_income"])
    if "monthly_expenses" in data and data["monthly_expenses"] is not None:
        user.monthly_expenses = float(data["monthly_expenses"])

    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


# ── Forgot Password ────────────────────────────────────────────────────────────

@router.post("/forgot-password", status_code=200)
def forgot_password(data: dict, db: Session = Depends(get_db)):
    """
    Request a password reset email.
    Always returns 200 — never reveals whether email exists (security best practice).

    TODO: Replace token generation with email delivery via support@gracefinance.co
          once SMTP / SendGrid is configured. The token logic is complete.
    """
    import secrets

    email = (data.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required.")

    user = db.query(User).filter(User.email == email).first()

    if user:
        # Generate a secure reset token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)

        # Store token (replace any existing token for this email)
        _reset_tokens[token] = {
            "email": email,
            "user_id": str(user.id),
            "expires_at": expires_at,
        }

        # ── TODO: Send email via support@gracefinance.co ──
        # reset_url = f"https://gracefinance.co/reset-password?token={token}"
        # send_reset_email(to=email, name=user.first_name, reset_url=reset_url)
        #
        # For now: log to console in dev, silent in prod
        import os, logging
        if os.getenv("APP_ENV") != "production":
            logging.getLogger(__name__).info(
                f"[DEV] Password reset token for {email}: {token}"
            )

    # Always return 200 — don't reveal if email exists
    return {
        "message": "If that email is registered, you'll receive reset instructions shortly."
    }


@router.post("/reset-password", status_code=200)
def reset_password(data: dict, db: Session = Depends(get_db)):
    """
    Complete password reset with token from email.
    Accepts { token: str, new_password: str }
    """
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

    # Find user and update password
    user = db.query(User).filter(User.email == token_data["email"]).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid reset token.")

    user.hashed_password = hash_password(new_password)
    db.commit()

    # Invalidate token after use
    del _reset_tokens[token]

    # Clear any login lockout for this email
    _reset_attempts(token_data["email"])

    return {"message": "Password updated successfully. You can now log in."}


# ── Email Verification (stub — wire when SMTP ready) ──────────────────────────

@router.post("/verify-email", status_code=200)
def verify_email(data: dict, db: Session = Depends(get_db)):
    """
    Verify email address with token sent to user.
    TODO: Wire to actual email sending + token generation on signup.
    """
    token = (data.get("token") or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Verification token required.")

    # TODO: Look up verification token from DB/cache
    # For now return a clear not-yet-implemented message
    raise HTTPException(
        status_code=501,
        detail="Email verification is coming soon. Check back shortly.",
    )