"""
GraceFinance — Grace AI Coach Service (v2)
============================================
Now powered by the 3-Stream Behavioral Engine.
Every response is informed by the full data picture.

Flow:
  1. User sends message
  2. Behavioral engine runs all 3 streams (check-in + pulse + NLP)
  3. Context + proactive insights injected into Grace's system prompt
  4. Claude responds with full awareness of user's financial state
  5. Conversation themes detected and logged back into user profile
  6. Next time user talks to Grace, she remembers what they discussed

Place at: app/services/grace_service.py (replaces v1)
"""

import os
import anthropic
from sqlalchemy.orm import Session

from app.services.intelligence_engine import (
    log_conversation_themes,
    generate_proactive_insights,
)
from app.services.behavioral_engine import UserProfileBuilder


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
- When pattern alerts are flagged, weave them into conversation.
- If peer comparison data is available, use it to motivate (never shame).
- When you know their recent conversation topics, show continuity.

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

PROACTIVE COACHING:
- If you see pattern alerts in the context, address them naturally.
- If a dimension dropped, ask about it gently.
- If they're on a streak, acknowledge it without being over-the-top.
- If BSI shows contraction, be extra empathetic about spending pressure.
- If they discussed a topic recently, show you remember.

DISCLAIMER (include naturally when giving financial guidance, skip for casual chat):
"Just a reminder — I'm your coach, not a financial advisor. For specific investment or tax decisions, a licensed professional is the way to go."
"""


def chat_with_grace(db: Session, user_id: int, messages: list[dict]) -> str:
    """
    Send a conversation to Claude with full intelligence context.

    Args:
        db: Database session
        user_id: Current user's ID
        messages: Conversation history [{"role": "user"|"assistant", "content": "..."}]

    Returns:
        Grace's response text
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set. Add it to your .env file.")

    # 1. Build full context from behavioral engine (3-stream)
    profile = UserProfileBuilder().build(db, user_id, messages)
    user_context = profile.to_grace_context()

    # 2. Get proactive insights for Grace to weave in
    insights = generate_proactive_insights(db, user_id)
    insight_block = ""
    if insights:
        high_priority = [i for i in insights if i["priority"] == "high"]
        if high_priority:
            insight_block = (
                "\n\n[PROACTIVE COACHING OPPORTUNITIES — weave naturally, don't force]\n"
                + "\n".join(f"  - {ins['message']}" for ins in high_priority[:3])
            )

    # 3. Assemble the full system prompt
    system_prompt = GRACE_SYSTEM_PROMPT + user_context + insight_block

    # 4. Call Claude
    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        system=system_prompt,
        messages=messages,
    )

    response_text = response.content[0].text

    # 5. Log conversation themes from behavioral engine's NLP stream
    try:
        if profile.nlp_themes:
            theme_names = [t["theme"] for t in profile.nlp_themes]
            log_conversation_themes(db, user_id, theme_names)
    except Exception:
        pass  # Never let theme logging break the response

    return response_text


def get_grace_intro(db: Session, user_id: int) -> dict:
    """
    Generate a personalized intro for the Grace chat page.
    Uses intelligence engine context to customize greeting and suggestions.
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

    # Get insights to customize suggestion chips
    insights = generate_proactive_insights(db, user_id)
    insight_types = [i["type"] for i in insights]

    # Base suggestion chips
    suggestions = [
        "Why do I stress about money even when I'm okay?",
        "How do I start building an emergency fund?",
        "I just overspent — help me not feel terrible",
        "What does my FCS score actually mean?",
        "Help me set a realistic money goal",
    ]

    # Customize chips based on insights
    if "behavioral_stress" in insight_types:
        suggestions.insert(0, "I'm feeling financially overwhelmed right now")
    if "milestone" in insight_types:
        suggestions.insert(0, "I hit a new milestone — what's next?")
    if "streak" in insight_types:
        suggestions.insert(0, "I've been consistent — how do I keep going?")

    # Keep top 5
    suggestions = suggestions[:5]

    return {
        "greeting": f"Hey {name_str}, I'm Grace 🐾",
        "subtitle": "Your financial coach — powered by your real FCS data",
        "suggestions": suggestions,
    }