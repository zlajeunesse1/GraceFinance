"""
Auth Service — JWT + Password utilities.

FIX #3 (CRITICAL): get_current_user() now checks email_verified.
    Unverified users get HTTP 403. Endpoints that need to work before
    verification (e.g., resend-verification) should use get_any_user().
FIX #13 (MEDIUM): JWT now includes a 'type' claim ('access') to
    future-proof against token confusion if refresh tokens are added.
"""

import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config import get_settings
from app.database import get_db
from app.models.models import User

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def hash_password(password: str) -> str:
    pre_hashed = hashlib.sha256(password.encode()).hexdigest()
    return pwd_context.hash(pre_hashed)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pre_hashed = hashlib.sha256(plain_password.encode()).hexdigest()
    return pwd_context.verify(pre_hashed, hashed_password)


def create_access_token(user_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "access",  # FIX #13: token type claim for future-proofing
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def _extract_user_from_token(
    credentials: HTTPAuthorizationCredentials,
    db: Session,
) -> User:
    """
    Internal helper: decode JWT and return User object.
    Does NOT check email_verified — callers decide verification policy.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        # FIX #13: Validate token type if present (backward-compatible
        # with tokens issued before this change that lack the claim)
        token_type = payload.get("type")
        if token_type is not None and token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        user_id = uuid.UUID(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency: extracts and validates the JWT, returns the User object.

    FIX #3 (CRITICAL): Now enforces email_verified. Unverified users
    receive HTTP 403 and cannot access any protected endpoint.

    For endpoints that need to work before verification (e.g.,
    resend-verification, verification callback), use get_any_user() instead.
    """
    user = _extract_user_from_token(credentials, db)

    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please check your inbox and verify your email.",
        )

    return user


def get_any_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency: Same as get_current_user but does NOT require email_verified.

    Use this ONLY for endpoints that must work before verification:
      - POST /auth/resend-verification
      - GET  /auth/verify-email
      - GET  /auth/me (so frontend can check verification status)

    All other endpoints should use get_current_user().
    """
    return _extract_user_from_token(credentials, db)