"""
Grace Router — AI Financial Coach endpoints.

Place this file at: app/routers/grace.py

Endpoints:
  POST /grace/chat  → Send message(s), get Grace's response + usage info
  GET  /grace/intro  → Get Grace's introduction for new users
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models import User
from app.services.auth import get_current_user
from app.services.grace_service import chat_with_grace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/grace", tags=["Grace AI Coach"])


def _ensure_ai_columns(db: Session):
    """Auto-create AI usage columns if they don't exist yet."""
    try:
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_messages_used INTEGER DEFAULT 0"))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_reset_date DATE"))
        db.commit()
    except Exception:
        db.rollback()


# ── Schemas ───────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str
    content: str


class GraceChatRequest(BaseModel):
    messages: list[ChatMessage]


class UsageInfo(BaseModel):
    used: int
    limit: Optional[int]
    remaining: Optional[int]
    tier: str


class GraceChatResponse(BaseModel):
    response: str
    usage: Optional[UsageInfo] = None


class GraceIntroResponse(BaseModel):
    greeting: str
    suggestions: list[str]


# ── Endpoints ─────────────────────────────────────────

@router.post("/chat", response_model=GraceChatResponse)
def chat(
    payload: GraceChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Send messages to Grace, get her response powered by Claude + real FCS data."""

    # Ensure columns exist (safe to run every time — IF NOT EXISTS)
    _ensure_ai_columns(db)

    if not payload.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    messages = [{"role": m.role, "content": m.content} for m in payload.messages]

    try:
        # Now passes full user object — returns {response, usage}
        result = chat_with_grace(db, user, messages)
    except HTTPException:
        raise  # 429 limit reached — pass through as-is
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Grace chat error: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Grace is unavailable: {str(e)}")

    return GraceChatResponse(
        response=result["response"],
        usage=UsageInfo(**result["usage"]),
    )


@router.get("/intro", response_model=GraceIntroResponse)
def get_intro(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get Grace's intro greeting and suggested conversation starters."""
    from app.services.grace_service import get_grace_intro
    return GraceIntroResponse(**get_grace_intro(db, user.id))