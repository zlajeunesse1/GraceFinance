"""
BSI Router v2 — Weekly Behavioral Shift Check-In with Motivation Layer
══════════════════════════════════════════════════════════════════════
Each question is a two-step flow:
  1. Trigger: "Did this behavior happen?" (yes/no)
  2. Motivation: "Why?" (only shown if yes)

The motivation determines the score — same action with different
intent gets a completely different BSI reading.

Endpoints:
  GET  /bsi/questions       → Get this week's BSI questions + motivation options
  POST /bsi/submit          → Submit answers (trigger + motivation pairs)
  GET  /bsi/latest          → User's most recent BSI + coaching reflections
  GET  /bsi/history         → BSI trend over time
  GET  /bsi/population      → Population-level BSI (Premium only)

File: app/routers/bsi_router.py
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from zoneinfo import ZoneInfo

from app.database import get_db
from app.models import User
from app.services.auth import get_current_user
from app.services.tier_gate import require_feature
from app.services.bsi_engine import (
    compute_bsi,
    get_latest_bsi,
    get_user_bsi_history,
    has_completed_bsi_this_week,
    compute_population_bsi,
)
from app.services.bsi_questions import get_bsi_questions

EASTERN = ZoneInfo("America/New_York")

router = APIRouter(prefix="/bsi", tags=["BSI — Behavioral Shift Indicator"])


# ── Schemas ──────────────────────────────────────────────────

class BSIAnswer(BaseModel):
    question_id: str          # "BX-1"
    triggered: bool           # Did the behavior happen?
    motivation_id: Optional[str] = None  # "BX-1-B" (only if triggered=True)

class BSISubmitPayload(BaseModel):
    answers: List[BSIAnswer]


# ──────────────────────────────────────────
#  GET BSI QUESTIONS
# ──────────────────────────────────────────

@router.get("/questions")
def get_questions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Serve this week's BSI questions with motivation options.
    Available Friday through Sunday. One submission per week.

    Returns trigger questions + motivation follow-ups for each pattern.
    Frontend shows motivations conditionally (only when trigger = yes).
    """
    now_et = datetime.now(EASTERN)
    weekday = now_et.weekday()

    if has_completed_bsi_this_week(db, user.id):
        return {
            "available": False,
            "already_completed": True,
            "questions": [],
            "message": "You've already completed this week's behavioral check-in.",
        }

    # BSI available Friday (4) through Sunday (6)
    if weekday < 4:
        days_until_friday = 4 - weekday
        return {
            "available": False,
            "already_completed": False,
            "questions": [],
            "message": f"Your weekly behavioral check-in opens on Friday.",
            "opens_in_days": days_until_friday,
            "day_of_week": now_et.strftime("%A"),
        }

    questions = get_bsi_questions()

    return {
        "available": True,
        "already_completed": False,
        "questions": questions,
        "question_count": len(questions),
        "message": "5 quick questions about your behavior this week. Each one has a follow-up if you answer yes.",
        "estimated_time": "60-90 seconds",
    }


# ──────────────────────────────────────────
#  SUBMIT BSI ANSWERS
# ──────────────────────────────────────────

@router.post("/submit")
def submit_bsi(
    payload: BSISubmitPayload,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Submit weekly BSI answers with motivation layer.

    Each answer includes:
      - question_id: "BX-1"
      - triggered: true/false (did the behavior happen?)
      - motivation_id: "BX-1-B" (why — only required if triggered=true)
    """
    if not payload.answers:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No answers provided.")

    if has_completed_bsi_this_week(db, user.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already completed this week's behavioral check-in.")

    # Validate: triggered answers should have motivation_id
    for a in payload.answers:
        if a.triggered and not a.motivation_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Question {a.question_id}: behavior was triggered but no motivation selected.",
            )

    # Build answer dicts for engine
    answers = [
        {
            "question_id": a.question_id,
            "triggered": a.triggered,
            "motivation_id": a.motivation_id,
        }
        for a in payload.answers
    ]

    record = compute_bsi(db, user.id, answers)

    return {
        "message": "Behavioral check-in saved",
        "bsi_composite": record.bsi_composite,
        "bsi_delta": record.bsi_delta,
        "interpretation": _interpret_bsi(record.bsi_composite),
        "patterns_triggered": record.patterns_triggered,
        "stress_patterns": record.stress_patterns or [],
        "positive_patterns": record.positive_patterns or [],
        "coaching_reflections": record.coaching_reflections or [],
        "dimension_impacts": record.dimension_impacts or {},
        "week": record.week_start.isoformat(),
    }


# ──────────────────────────────────────────
#  GET LATEST BSI
# ──────────────────────────────────────────

@router.get("/latest")
def latest_bsi(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = get_latest_bsi(db, user.id)

    if not record:
        return {
            "has_data": False,
            "message": "Complete your first weekly behavioral check-in to see your BSI.",
        }

    return {
        "has_data": True,
        "bsi_composite": record.bsi_composite,
        "bsi_delta": record.bsi_delta,
        "interpretation": _interpret_bsi(record.bsi_composite),
        "week": record.week_start.isoformat(),
        "patterns_triggered": record.patterns_triggered,
        "stress_patterns": record.stress_patterns or [],
        "positive_patterns": record.positive_patterns or [],
        "coaching_reflections": record.coaching_reflections or [],
        "dimension_impacts": record.dimension_impacts or {},
        "patterns": {
            "subscription_churn": {"score": record.subscription_churn_score, "signal": record.subscription_churn_signal},
            "credit_substitution": {"score": record.credit_substitution_score, "signal": record.credit_substitution_signal},
            "deferred_spending": {"score": record.deferred_spending_score, "signal": record.deferred_spending_signal},
            "debt_accumulation": {"score": record.debt_accumulation_score, "signal": record.debt_accumulation_signal},
            "financial_avoidance": {"score": record.financial_avoidance_score, "signal": record.financial_avoidance_signal},
        },
        "computed_at": record.computed_at.isoformat() if record.computed_at else None,
    }


# ──────────────────────────────────────────
#  BSI HISTORY
# ──────────────────────────────────────────

@router.get("/history")
def bsi_history(
    weeks: int = 12,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    records = get_user_bsi_history(db, user.id, weeks)

    return {
        "user_id": str(user.id),
        "weeks_requested": weeks,
        "data_points": [
            {
                "week": r.week_start.isoformat(),
                "bsi": r.bsi_composite,
                "delta": r.bsi_delta,
                "patterns_triggered": r.patterns_triggered,
                "stress_count": len(r.stress_patterns) if r.stress_patterns else 0,
                "positive_count": len(r.positive_patterns) if r.positive_patterns else 0,
                "dimension_impacts": r.dimension_impacts or {},
                "checkins": r.checkin_count_this_week,
            }
            for r in records
        ],
    }


# ──────────────────────────────────────────
#  POPULATION BSI (Premium only)
# ──────────────────────────────────────────

@router.get("/population")
def population_bsi(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Population-level BSI with motivation breakdown.
    Premium only. Shows what % of each pattern is stress-driven vs positive.
    This is the behavioral intelligence product.
    """
    require_feature(user, "bsi_insights")
    return compute_population_bsi(db)


# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════

def _interpret_bsi(score: float) -> dict:
    if score >= 50:
        return {"band": "Strong Positive", "emoji": "↑", "message": "Your financial behavior is actively improving. You're making intentional moves."}
    elif score >= 20:
        return {"band": "Mild Positive", "emoji": "↗", "message": "Slight positive shift. Your habits are trending in the right direction."}
    elif score >= -20:
        return {"band": "Stable", "emoji": "→", "message": "No major behavioral shifts this week. Holding steady."}
    elif score >= -50:
        return {"band": "Mild Stress", "emoji": "↘", "message": "Early signs of financial stress in your behavior. Worth paying attention to."}
    else:
        return {"band": "Elevated Stress", "emoji": "↓", "message": "Multiple stress patterns active. Your behavior suggests financial pressure is building."}