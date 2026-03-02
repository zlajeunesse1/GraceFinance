# routers/checkin.py
# GraceFinance Daily Check-In API Routes
# FastAPI + SQLAlchemy + PostgreSQL

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta, datetime
from typing import List, Optional, Any
from pydantic import BaseModel

from app.database import get_db
from app.models.checkin import CheckinQuestion, CheckinAnswer, CheckinSession, CheckinStreak
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/checkin", tags=["checkin"])


# ═══════════════════════════════════════════
# PYDANTIC SCHEMAS
# ═══════════════════════════════════════════

class QuestionOut(BaseModel):
    id: str
    category: str
    type: str
    question: str
    subtitle: Optional[str] = None
    placeholder: Optional[str] = None
    max_characters: Optional[int] = None
    options: Optional[list] = None
    multi: bool = False
    min: Optional[int] = None
    max: Optional[int] = None
    labels: Optional[dict] = None
    color_range: Optional[list] = None
    scale_labels: Optional[dict] = None

    class Config:
        from_attributes = True


class AnswerIn(BaseModel):
    question_id: str
    answer:  Any  # string, number, or list
    timestamp: Optional[str] = None


class SubmitResponse(BaseModel):
    success: bool
    streak: int
    total_checkins: int
    wellness_score: int
    personality_type: Optional[str] = None
    insights: List[dict]
    milestone_hit: Optional[dict] = None


class StreakOut(BaseModel):
    current_streak: int
    longest_streak: int
    total_checkins: int
    last_checkin_date: Optional[str] = None
    personality_type: Optional[str] = None


class HistoryOut(BaseModel):
    date: str
    wellness_score: Optional[int]
    mood_label: Optional[str]
    mood_score: Optional[float]
    insights: Optional[list]


# ═══════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════

MILESTONES = [
    {"days": 3, "label": "3-Day Spark", "icon": "✨", "unlock": "Spending Pattern Snapshot"},
    {"days": 7, "label": "7-Day Flame", "icon": "🔥", "unlock": "Weekly Mood-Money Report"},
    {"days": 14, "label": "14-Day Blaze", "icon": "💎", "unlock": "Trigger Analysis Deep Dive"},
    {"days": 30, "label": "30-Day Legend", "icon": "👑", "unlock": "Monthly Financial Psychology Profile"},
    {"days": 60, "label": "60-Day Master", "icon": "🏆", "unlock": "Behavioral Pattern Predictions"},
    {"days": 90, "label": "90-Day Transcendent", "icon": "🌟", "unlock": "Full Financial Personality Evolution Map"},
]

PERSONALITY_TYPES = [
    {"id": "aware_builder", "name": "The Aware Builder", "icon": "🏗️", "desc": "You see the patterns and build on them", "min_score": 70},
    {"id": "mindful_grower", "name": "The Mindful Grower", "icon": "🌱", "desc": "You're planting seeds with every check-in", "min_score": 50},
    {"id": "brave_starter", "name": "The Brave Starter", "icon": "⚡", "desc": "Showing up takes courage — and you're here", "min_score": 30},
    {"id": "honest_explorer", "name": "The Honest Explorer", "icon": "🧭", "desc": "Self-honesty is the rarest financial skill", "min_score": 0},
]

MICRO_FEEDBACK = {
    "money_mindset": [
        "Self-awareness is your superpower. Most people never pause to reflect like this.",
        "You're already ahead — just by thinking about this.",
        "Your money mindset is evolving. That's rare.",
    ],
    "spending_habits": [
        "Naming your patterns is the first step to breaking them.",
        "No shame here — awareness creates change.",
        "Now you see it. That's where transformation starts.",
    ],
    "financial_confidence": [
        "Confidence grows through consistency, not perfection.",
        "Wherever you are today is the right starting point.",
        "Every check-in builds your financial self-trust.",
    ],
    "money_goals": [
        "Clear goals are magnetic — they pull your behavior toward them.",
        "Focus is everything. You just locked in.",
        "That clarity puts you in the top 10% of people your age.",
    ],
    "life_context": [
        "Context shapes everything. Thanks for being real.",
        "Your situation is unique — and so is your path forward.",
        "Understanding your environment is financial intelligence.",
    ],
    "money_stress": [
        "Naming stress takes away its power. You just did that.",
        "Stress is information, not failure. You're reading the signal.",
        "Most people carry this silently. You're processing it.",
    ],
}


# ═══════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════

def get_today_day_set(db: Session) -> int:
    """Determine which question set to serve today (rotates daily)"""
    max_set = db.query(func.max(CheckinQuestion.day_set)).filter(
        CheckinQuestion.is_active == True
    ).scalar() or 0
    total_sets = max_set + 1
    day_num = (date.today() - date(2025, 1, 1)).days
    return day_num % total_sets


def calculate_wellness_score(questions: list, answers_map: dict) -> int:
    """Calculate 0-100 wellness score from answers"""
    points = 0
    max_points = 0

    for q in questions:
        answer = answers_map.get(q.id)
        if answer is None:
            continue

        if q.type == "emoji_select" and q.options:
            max_points += 10
            for opt in q.options:
                if opt.get("value") == answer:
                    points += opt.get("mood", 5)
                    break

        elif q.type in ("visual_slider", "scale"):
            max_points += 10
            points += int(answer) if isinstance(answer, (int, float)) else 5

        elif q.type == "multiple_choice":
            max_points += 10
            points += 7  # engagement credit

        elif q.type == "quick_tap":
            max_points += 10
            count = len(answer) if isinstance(answer, list) else 1
            points += min(count * 2, 10)

        elif q.type == "open_text":
            max_points += 10
            length = len(str(answer).strip()) if answer else 0
            points += 10 if length > 50 else (7 if length > 20 else (4 if length > 0 else 0))

    return round((points / max_points) * 100) if max_points > 0 else 50


def extract_mood(questions: list, answers_map: dict) -> tuple:
    """Extract mood label and score from emoji_select answers"""
    for q in questions:
        if q.type == "emoji_select" and q.options:
            answer = answers_map.get(q.id)
            if answer:
                for opt in q.options:
                    if opt.get("value") == answer:
                        return opt.get("label", "Neutral"), opt.get("mood", 5)
    return "Neutral", 5


def get_personality_type(score: int, total_checkins: int) -> dict:
    """Determine money personality based on score + consistency"""
    adjusted = score + min(total_checkins * 2, 20)
    for p in PERSONALITY_TYPES:
        if adjusted >= p["min_score"]:
            return p
    return PERSONALITY_TYPES[-1]


def generate_insights(questions: list, answers_map: dict) -> list:
    """Generate personalized completion insights"""
    insights = []
    mood_score = None
    confidence_score = None
    trigger_count = 0

    for q in questions:
        answer = answers_map.get(q.id)
        if answer is None:
            continue

        if q.type == "emoji_select" and q.options:
            for opt in q.options:
                if opt.get("value") == answer:
                    mood_score = opt.get("mood")
                    break

        if q.type in ("visual_slider", "scale") and q.id in ("confidence_scale", "future_self", "impulse_check"):
            confidence_score = int(answer) if isinstance(answer, (int, float)) else None

        if q.type in ("quick_tap", "multiple_choice") and isinstance(answer, list):
            trigger_count += len(answer)

    if mood_score is not None:
        if mood_score >= 7:
            insights.append({"icon": "🔥", "message": "You're in a strong headspace today. Financial decisions made from confidence tend to compound positively over time."})
        elif mood_score >= 4:
            insights.append({"icon": "🌱", "message": "You're in a balanced state — actually ideal for clear financial decisions. Neutral beats emotional every time."})
        else:
            insights.append({"icon": "💛", "message": "Tough days happen. Checking in instead of avoiding shows real financial maturity. Protect your energy today."})

    if confidence_score is not None:
        if confidence_score >= 7:
            insights.append({"icon": "📈", "message": "Your confidence is building momentum. People at your level typically see measurable improvement within 30 days."})
        elif confidence_score >= 4:
            insights.append({"icon": "🎯", "message": "You're in the growth zone — not comfortable, not panicking. This is exactly where breakthroughs happen."})
        else:
            insights.append({"icon": "🤝", "message": "Low confidence isn't permanent — it's a signal. Your awareness puts you miles ahead of where you were."})

    if trigger_count >= 5:
        insights.append({"icon": "🔍", "message": f"You identified {trigger_count} patterns — that level of self-awareness is uncommon. Each one you name loses power over you."})
    elif trigger_count >= 2:
        insights.append({"icon": "💡", "message": f"You spotted {trigger_count} patterns. Awareness is the first step — you're already building the muscle."})

    return insights


def update_streak(db: Session, user_id: int) -> CheckinStreak:
    """Update or create streak record for user"""
    streak = db.query(CheckinStreak).filter(CheckinStreak.user_id == user_id).first()
    today = date.today()
    yesterday = today - timedelta(days=1)

    if not streak:
        streak = CheckinStreak(
            user_id=user_id,
            current_streak=1,
            longest_streak=1,
            total_checkins=1,
            last_checkin_date=today,
        )
        db.add(streak)
    else:
        if streak.last_checkin_date == today:
            # Already checked in today, don't double-count
            return streak

        if streak.last_checkin_date == yesterday:
            streak.current_streak += 1
        else:
            streak.current_streak = 1

        streak.total_checkins += 1
        streak.last_checkin_date = today

        if streak.current_streak > streak.longest_streak:
            streak.longest_streak = streak.current_streak

    return streak


def check_milestone(streak_count: int) -> Optional[dict]:
    """Check if user just hit a milestone"""
    for m in MILESTONES:
        if m["days"] == streak_count:
            return m
    return None


# ═══════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════

@router.get("/daily-questions", response_model=List[QuestionOut])
def get_daily_questions(
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_user),  # uncomment when auth ready
):
    """
    Serve today's check-in questions.
    Rotates through question sets daily.
    Returns empty list if user already completed today's check-in.
    """
    user_id = 2  # TODO: replace with current_user.id

    # Check if already completed today
    existing = db.query(CheckinSession).filter(
        CheckinSession.user_id == user_id,
        CheckinSession.session_date == date.today(),
    ).first()
    if existing:
        return []  # Frontend shows "already completed" state

    # Get today's question set
    day_set = get_today_day_set(db)

    questions = db.query(CheckinQuestion).filter(
        CheckinQuestion.day_set == day_set,
        CheckinQuestion.is_active == True,
    ).order_by(CheckinQuestion.sort_order).all()

    # Map DB fields to frontend expected format
    result = []
    for q in questions:
        out = QuestionOut(
            id=q.id,
            category=q.category,
            type=q.type,
            question=q.question,
            subtitle=q.subtitle,
            placeholder=q.placeholder,
            max_characters=q.max_characters,
            options=q.options,
            multi=q.multi or False,
            min=q.min_val,
            max=q.max_val,
            labels=q.labels,
            color_range=q.color_range,
            scale_labels=q.labels if q.type == "scale" else None,
        )
        result.append(out)

    return result


@router.post("/submit-answers", response_model=SubmitResponse)
def submit_answers(
    answers: List[AnswerIn],
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_user),
):
    """
    Submit completed check-in answers.
    Calculates wellness score, updates streak, generates insights.
    """
    user_id = 2  # TODO: replace with current_user.id
    today = date.today()

    # Prevent duplicate submissions
    existing = db.query(CheckinSession).filter(
        CheckinSession.user_id == user_id,
        CheckinSession.session_date == today,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already completed today's check-in")

    # Get the questions that were answered
    question_ids = [a.question_id for a in answers]
    questions = db.query(CheckinQuestion).filter(
        CheckinQuestion.id.in_(question_ids)
    ).all()

    # Build answers map
    answers_map = {a.question_id: a.answer for a in answers}

    # Save individual answers
    for a in answers:
        q = next((q for q in questions if q.id == a.question_id), None)
        mood_score = None

        # Extract mood score for emoji_select questions
        if q and q.type == "emoji_select" and q.options:
            for opt in q.options:
                if opt.get("value") == a.answer:
                    mood_score = opt.get("mood")
                    break

        db_answer = CheckinAnswer(
            user_id=user_id,
            question_id=a.question_id,
            answer=a.answer,
            mood_score=mood_score,
            session_date=today,
        )
        db.add(db_answer)

    # Calculate scores
    wellness_score = calculate_wellness_score(questions, answers_map)
    mood_label, mood_score = extract_mood(questions, answers_map)
    insights = generate_insights(questions, answers_map)

    # Update streak
    streak = update_streak(db, user_id)
    personality = get_personality_type(wellness_score, streak.total_checkins)
    streak.personality_type = personality["id"]

    # Check for milestone
    milestone_hit = check_milestone(streak.current_streak)

    # Get day_set for this session
    day_set = get_today_day_set(db)

    # Save session
    session = CheckinSession(
        user_id=user_id,
        session_date=today,
        day_set=day_set,
        wellness_score=wellness_score,
        mood_label=mood_label,
        mood_score=mood_score,
        insights=insights,
    )
    db.add(session)
    db.commit()

    return SubmitResponse(
        success=True,
        streak=streak.current_streak,
        total_checkins=streak.total_checkins,
        wellness_score=wellness_score,
        personality_type=personality["id"],
        insights=insights,
        milestone_hit=milestone_hit,
    )


@router.get("/streak", response_model=StreakOut)
def get_streak(
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_user),
):
    """Get current user's streak info"""
    user_id = 2  # TODO: replace with current_user.id

    streak = db.query(CheckinStreak).filter(CheckinStreak.user_id == user_id).first()
    if not streak:
        return StreakOut(current_streak=0, longest_streak=0, total_checkins=0)

    # Check if streak is still active (didn't miss yesterday)
    if streak.last_checkin_date and streak.last_checkin_date < date.today() - timedelta(days=1):
        streak.current_streak = 0
        db.commit()

    return StreakOut(
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        total_checkins=streak.total_checkins,
        last_checkin_date=str(streak.last_checkin_date) if streak.last_checkin_date else None,
        personality_type=streak.personality_type,
    )


@router.get("/history", response_model=List[HistoryOut])
def get_history(
    days: int = 30,
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_user),
):
    """Get check-in history for mood trends and comparison"""
    user_id = 2  # TODO: replace with current_user.id
    cutoff = date.today() - timedelta(days=days)

    sessions = db.query(CheckinSession).filter(
        CheckinSession.user_id == user_id,
        CheckinSession.session_date >= cutoff,
    ).order_by(CheckinSession.session_date.desc()).all()

    return [
        HistoryOut(
            date=str(s.session_date),
            wellness_score=s.wellness_score,
            mood_label=s.mood_label,
            mood_score=s.mood_score,
            insights=s.insights,
        )
        for s in sessions
    ]


@router.get("/yesterday")
def get_yesterday_data(
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_user),
):
    """Get yesterday's check-in for today vs yesterday comparison"""
    user_id = 2  # TODO: replace with current_user.id
    yesterday = date.today() - timedelta(days=1)

    session = db.query(CheckinSession).filter(
        CheckinSession.user_id == user_id,
        CheckinSession.session_date == yesterday,
    ).first()

    if not session:
        return {"found": False}

    return {
        "found": True,
        "date": str(session.session_date),
        "wellness_score": session.wellness_score,
        "mood_label": session.mood_label,
        "mood_score": session.mood_score,
    }
