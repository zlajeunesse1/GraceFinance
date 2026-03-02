"""
Grace Router — AI Financial Coach endpoints.

Place this file at: app/routers/grace.py

Endpoints:
  POST /grace/chat  → Send message(s), get Grace's response
  GET  /grace/intro  → Get Grace's introduction for new users
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import User
from app.services.auth import get_current_user
from app.services.grace_service import chat_with_grace


router = APIRouter(prefix="/grace", tags=["Grace AI Coach"])


# ── Schemas ───────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class GraceChatRequest(BaseModel):
    messages: list[ChatMessage]


class GraceChatResponse(BaseModel):
    response: str


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

    if not payload.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    # Convert to list of dicts for the service
    messages = [{"role": m.role, "content": m.content} for m in payload.messages]

    try:
        response_text = chat_with_grace(db, user.id, messages)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Grace is unavailable: {str(e)}")

    return GraceChatResponse(response=response_text)


@router.get("/intro", response_model=GraceIntroResponse)
def get_intro(user: User = Depends(get_current_user)):
    """Get Grace's intro greeting and suggested conversation starters."""

    name = user.first_name if hasattr(user, "first_name") and user.first_name else "there"

    return GraceIntroResponse(
        greeting=(
            f"Hey {name}, I'm Grace \U0001F43E "
            "I'm your financial coach — here to help you understand your "
            "relationship with money, not judge it. "
            "There's no wrong question. What's on your mind?"
        ),
        suggestions=[
            "Why do I stress about money even when I'm okay?",
            "How do I start building an emergency fund?",
            "I just overspent — help me not feel terrible",
            "What does my FCS score actually mean?",
            "Help me set a realistic money goal",
        ],
    )