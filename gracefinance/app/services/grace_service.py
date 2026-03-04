"""
GraceFinance — Grace AI Coach Service (v2.1)
==============================================
Works immediately with or without the behavioral engine.
Falls back to basic context if engine modules aren't deployed.

Changes from v2:
  - Graceful import fallback for behavioral_engine + intelligence_engine
  - Removed paw emoji from intro greeting
  - Basic user context pulled directly from DB when engine unavailable
"""

import os
import anthropic
from sqlalchemy.orm import Session

# ── Graceful imports — engine may not be deployed yet ──
try:
    from app.services.intelligence_engine import (
        log_conversation_themes,
        generate_proactive_insights,
    )
    from app.services.behavioral_engine import UserProfileBuilder
    HAS_ENGINE = True
except ImportError:
    HAS_ENGINE = False


GRACE_SYSTEM_PROMPT = """You are Grace, the GraceFinance AI financial coach.

IDENTITY:
- You're warm, confident, and direct — like a smart friend who understands money deeply.
- You use casual, encouraging language. No jargon unless you explain it.
- You're named after a beloved black lab — carry that warmth and loyalty.
- You believe everyone can build a healthy relationship with money.

YOUR COACHING PHILOSOPHY:
- Money is emotional before it's mathematical. Acknowledge feelings first.
- Never shame. Never lecture. Meet people where they are.
- Ask follow-up questions to understand the "why" behind behavior.
- Celebrate small wins — a $20 savings transfer matters.
- Connect spending patterns to emotions and habits, not willpower failures.
- Frame everything as progress, not perfection.

PERSONALITY:
- Witty but professional
- Charming but never casual
- Confident and reassuring
- Calm under stress
- Clear, never vague

WHAT YOU CAN DO:
- Help users understand their FCS score and what drives each dimension.
- Coach on budgeting, saving, debt payoff, and building financial habits.
- Explore the psychology behind spending — stress spending, retail therapy, avoidance.
- Provide general financial education and literacy.
- Help set realistic, achievable money goals.
- When you have their data, reference specific numbers naturally.

STRICT GUARDRAILS:
1. NEVER recommend specific investments, stocks, bonds, crypto, or securities.
2. NEVER provide specific tax advice or suggest tax strategies.
3. NEVER promise or project specific financial outcomes or returns.
4. NEVER act as or imply you are a fiduciary or licensed financial adviser.
5. NEVER share or reference other users' specific data.
6. If asked about investing specifics: "I focus on building your financial foundation — for investment advice, I'd recommend a licensed financial advisor."
7. If user seems in genuine crisis (eviction, can't afford food/medicine), gently suggest 211.org or local resources while staying supportive.

RESPONSE STYLE:
- Concise: 2-4 short paragraphs max for most messages.
- Encouraging but real. Don't be fake-positive.
- Ask ONE follow-up question when appropriate.
- Reference their data naturally — "Your stability score jumped this week" not "According to your data..."
- Use simple analogies for financial concepts.

DISCLAIMER (include naturally when giving financial guidance, skip for casual chat):
"Just a reminder — I'm your coach, not a financial advisor. For specific investment or tax decisions, a licensed professional is the way to go."
"""


def _build_basic_context(db: Session, user_id: int) -> str:
    """
    Build basic user context directly from DB when behavioral engine
    is not available. Pulls FCS scores and user info.
    """
    context_parts = []

    try:
        from app.models import User
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            name = getattr(user, "first_name", None)
            if name:
                context_parts.append(f"User's name: {name}")
    except Exception:
        pass

    try:
        from app.models import CheckInResponse
        from sqlalchemy import func

        # Get latest check-in data
        latest = (
            db.query(CheckInResponse)
            .filter(CheckInResponse.user_id == user_id)
            .order_by(CheckInResponse.created_at.desc())
            .limit(10)
            .all()
        )

        if latest:
            context_parts.append(f"User has completed {len(latest)} recent check-ins.")
    except Exception:
        pass

    try:
        from app.models import FCSSnapshot

        snapshot = (
            db.query(FCSSnapshot)
            .filter(FCSSnapshot.user_id == user_id)
            .order_by(FCSSnapshot.computed_at.desc())
            .first()
        )

        if snapshot:
            fcs = getattr(snapshot, "fcs_composite", None)
            if fcs is not None:
                context_parts.append(f"Current FCS score: {round(fcs, 1)}")

            # Pull dimension scores if available
            dims = {}
            for dim_name in ["stability", "outlook", "purchasing_power", "emergency_readiness", "income_adequacy"]:
                val = getattr(snapshot, dim_name, None)
                if val is not None:
                    dims[dim_name] = round(val, 1)
            if dims:
                dim_str = ", ".join(f"{k}: {v}" for k, v in dims.items())
                context_parts.append(f"Dimension scores: {dim_str}")
    except Exception:
        pass

    if context_parts:
        return "\n\n[USER CONTEXT]\n" + "\n".join(context_parts)
    return ""


def chat_with_grace(db: Session, user_id: int, messages: list[dict]) -> str:
    """
    Send a conversation to Claude with intelligence context.
    Falls back to basic context if behavioral engine isn't deployed.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set. Add it to your environment variables.")

    # Build context — use engine if available, otherwise basic DB query
    user_context = ""
    insight_block = ""

    if HAS_ENGINE:
        try:
            profile = UserProfileBuilder().build(db, user_id, messages)
            user_context = profile.to_grace_context()

            insights = generate_proactive_insights(db, user_id)
            if insights:
                high_priority = [i for i in insights if i.get("priority") == "high"]
                if high_priority:
                    insight_block = (
                        "\n\n[PROACTIVE COACHING OPPORTUNITIES]\n"
                        + "\n".join(f"  - {ins['message']}" for ins in high_priority[:3])
                    )
        except Exception:
            # Engine exists but errored — fall back to basic
            user_context = _build_basic_context(db, user_id)
    else:
        user_context = _build_basic_context(db, user_id)

    # Assemble system prompt
    system_prompt = GRACE_SYSTEM_PROMPT + user_context + insight_block

    # Call Claude
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=system_prompt,
        messages=messages,
    )

    response_text = response.content[0].text

    # Log themes if engine available
    if HAS_ENGINE:
        try:
            profile = UserProfileBuilder().build(db, user_id, messages)
            if profile.nlp_themes:
                theme_names = [t["theme"] for t in profile.nlp_themes]
                log_conversation_themes(db, user_id, theme_names)
        except Exception:
            pass

    return response_text


def get_grace_intro(db: Session, user_id: int) -> dict:
    """
    Generate a personalized intro for the Grace chat page.
    """
    user_name = None
    try:
        from app.models import User
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user_name = getattr(user, "first_name", None)
    except Exception:
        pass

    name_str = user_name if user_name else "there"

    # Get insights if engine available
    suggestions = [
        "Why do I stress about money even when I'm okay?",
        "How do I start building an emergency fund?",
        "I just overspent — help me think through it",
        "What does my FCS score actually mean?",
        "Help me set a realistic money goal",
    ]

    if HAS_ENGINE:
        try:
            insights = generate_proactive_insights(db, user_id)
            insight_types = [i["type"] for i in insights]

            if "behavioral_stress" in insight_types:
                suggestions.insert(0, "I'm feeling financially overwhelmed right now")
            if "milestone" in insight_types:
                suggestions.insert(0, "I hit a new milestone — what's next?")
            if "streak" in insight_types:
                suggestions.insert(0, "I've been consistent — how do I keep going?")

            suggestions = suggestions[:5]
        except Exception:
            pass

    return {
        "greeting": f"Hey {name_str}, I'm Grace — your financial coach. What's on your mind?",
        "subtitle": "Powered by your real FCS data",
        "suggestions": suggestions,
    }