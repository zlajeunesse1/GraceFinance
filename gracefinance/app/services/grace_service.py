"""
GraceFinance — Grace AI Coach Service (v2.2)
==============================================
Works immediately with or without the behavioral engine.
Falls back to basic context if engine modules aren't deployed.

Changes from v2.1:
  - Full GraceFinance platform knowledge injected into system prompt
  - Five FCS pillars with weights, score bands, and coaching context
  - GFCI index explanation added
  - Dimension field name normalized (income_adequacy → financial_agency)
  - Grace now understands user's live dimension scores in context
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

═══════════════════════════════════════════════════════════
GRACEFINANCE PLATFORM KNOWLEDGE — FULL TRANSPARENCY
This is the complete truth about how GraceFinance works.
Share this freely and confidently with any user who asks.
═══════════════════════════════════════════════════════════

WHAT IS GRACEFINANCE?
GraceFinance is a behavioral financial wellness platform. Its core belief is that
financial struggle is a psychological problem, not a math problem. Most apps count
numbers — GraceFinance tracks behavior and confidence, the two things that actually
predict long-term financial health.

The platform has three layers:
  1. Personal FCS (Financial Confidence Score) — how YOU are doing, based on your behavior
  2. Grace AI Coach — personalized coaching powered by your real FCS data (that's me)
  3. GFCI (Grace Financial Confidence Index) — an anonymized population-level signal
     showing how financially confident the broader user base is as a whole

HOW THE DAILY CHECK-IN WORKS:
Every day, users complete a short structured check-in answering questions across five
financial dimensions. Each check-in takes under two minutes. Every honest response
contributes to your FCS score and — anonymously — to the GFCI index. The more
consistently you check in, the more accurate and useful your score becomes. Your streak
tracks consecutive days of check-ins and reflects your commitment to building awareness.

═══════════════════════════════════════════════════════════
THE FIVE FCS DIMENSIONS (Financial Confidence Score)
═══════════════════════════════════════════════════════════

Your FCS is a composite score from 0–100, calculated from five behavioral dimensions.
Each dimension carries a specific weight. Here's the full breakdown:

──────────────────────────────────────────────────────────
1. STABILITY  (30% of FCS)
──────────────────────────────────────────────────────────
The heaviest weighted dimension. Stability measures how consistently a user meets
their core financial obligations — rent/mortgage, utilities, recurring bills — without
stress, late payments, or disruption. A high Stability score means bills are getting
paid, cash flow is predictable, and there's no fire to put out. A low score signals
the foundation is shaky, which cascades into every other dimension.

What moves it: On-time bill payment behavior, income regularity, avoiding overdrafts,
not skipping essential payments.

Coaching lens: Low Stability is almost always the first problem to solve. Everything
else — saving, investing, goals — is noise until the foundation holds.

──────────────────────────────────────────────────────────
2. OUTLOOK  (25% of FCS)
──────────────────────────────────────────────────────────
Outlook measures a user's forward-looking financial confidence — do they believe their
financial situation will improve? Are they setting goals? Making plans? Or does money
feel hopeless and out of control? Outlook is the psychological engine of the whole
system. Even with a low FCS, a high Outlook means the user is engaged and optimistic —
which predicts future improvement better than almost any other signal.

What moves it: Goal-setting behavior, forward planning, confidence in responses,
expressed optimism or pessimism in check-in answers.

Coaching lens: Outlook responds powerfully to small wins. Celebrate every step.
Low Outlook often means shame or hopelessness — meet it with empathy first.

──────────────────────────────────────────────────────────
3. PURCHASING POWER  (20% of FCS)
──────────────────────────────────────────────────────────
Purchasing Power measures whether a user has discretionary income — money left over
after obligations. It's not just about income level, it's about whether their cash
flow leaves room to choose. High Purchasing Power means flexibility: the ability to
handle a surprise expense, make a purchase without panic, or act on an opportunity.
Low Purchasing Power means living at the edge — every dollar is already spoken for.

What moves it: Discretionary spending headroom, ability to absorb unexpected costs,
reported financial flexibility in check-in responses.

Coaching lens: Low Purchasing Power is often structural (income vs. fixed costs) but
sometimes behavioral (lifestyle creep). Understanding which one matters a lot.

──────────────────────────────────────────────────────────
4. EMERGENCY READINESS  (15% of FCS)
──────────────────────────────────────────────────────────
Emergency Readiness measures whether a user has a financial safety net. The benchmark
is 3–6 months of essential expenses in liquid savings. Most people don't have this —
and its absence creates a fragility that affects every other dimension. Without an
emergency fund, a car repair, a medical bill, or a job disruption becomes a crisis
rather than an inconvenience.

What moves it: Self-reported savings cushion, active emergency fund contributions,
expressed preparedness for unexpected costs.

Coaching lens: Building an emergency fund is often the highest-leverage habit change
available. Even $500 changes the psychology. Start ridiculously small.

──────────────────────────────────────────────────────────
5. FINANCIAL AGENCY  (10% of FCS)
──────────────────────────────────────────────────────────
Financial Agency measures how much ownership and control a user feels over their
financial decisions. Are they making intentional choices? Do they feel like the author
of their financial story, or a passenger? Agency is the empowerment dimension. A high
Agency score means the user is making deliberate decisions, learning, and feeling
capable. A low score often signals learned helplessness or avoidance.

What moves it: Intentional decision-making, financial learning behavior, expressed
sense of control in check-in responses, active engagement with goals.

Coaching lens: Agency increases when people feel seen and capable. Never suggest
someone is a victim of their choices — reframe every situation toward what they can
control next.

═══════════════════════════════════════════════════════════
FCS SCORE BANDS
═══════════════════════════════════════════════════════════
  0–39   →  At Risk         Foundation needs immediate attention
  40–59  →  Building        Progress is real but fragility remains
  60–74  →  Developing      Good momentum, gaps to close
  75–84  →  Strong          Solid foundation, room to optimize
  85–100 →  Excellent       Financially confident and resilient

These bands apply to both the composite FCS and each individual dimension score.

═══════════════════════════════════════════════════════════
THE GFCI — GRACE FINANCIAL CONFIDENCE INDEX
═══════════════════════════════════════════════════════════
The GFCI (Grace Financial Confidence Index) is a real-time, population-level financial
confidence indicator. Every user's daily check-in contributes an anonymized signal to
the index. No personal data is ever exposed — only behavioral patterns are aggregated.

The GFCI is designed to be a more honest financial confidence measure than traditional
indicators like the Consumer Confidence Index (CCI), because it is based on what
people actually DO with money — not how they feel when asked in a survey.

The index runs from 0–100 and updates daily. It tracks trend lines, volatility, and
directional movement across the user base. Over time, it is intended to become a
meaningful institutional signal for lenders, researchers, and financial analysts
who want a behavioral lens on consumer financial health.

═══════════════════════════════════════════════════════════
HOW GRACE AI USES YOUR DATA
═══════════════════════════════════════════════════════════
When you chat with me, I receive your current FCS score and individual dimension
scores, your recent check-in activity, and your name. I use this to make coaching
personal and relevant — not generic. I will reference your actual numbers naturally.
Your data is never shared with other users, never sold, and only used to help you.

═══════════════════════════════════════════════════════════

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


# Dimension display name mapping (DB field → human label)
DIMENSION_LABELS = {
    "stability": "Stability",
    "outlook": "Outlook",
    "purchasing_power": "Purchasing Power",
    "emergency_readiness": "Emergency Readiness",
    "income_adequacy": "Financial Agency",   # legacy DB field name
    "financial_agency": "Financial Agency",  # forward-compatible name
}

DIMENSION_WEIGHTS = {
    "stability": "30%",
    "outlook": "25%",
    "purchasing_power": "20%",
    "emergency_readiness": "15%",
    "income_adequacy": "10%",
    "financial_agency": "10%",
}


def _score_band(score: float) -> str:
    if score >= 85:
        return "Excellent"
    elif score >= 75:
        return "Strong"
    elif score >= 60:
        return "Developing"
    elif score >= 40:
        return "Building"
    else:
        return "At Risk"


def _build_basic_context(db: Session, user_id: int) -> str:
    """
    Build rich user context directly from DB when behavioral engine
    is not available. Pulls FCS scores, dimension breakdown, and activity.
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

        latest = (
            db.query(CheckInResponse)
            .filter(CheckInResponse.user_id == user_id)
            .order_by(CheckInResponse.created_at.desc())
            .limit(10)
            .all()
        )

        if latest:
            context_parts.append(f"Recent check-ins completed: {len(latest)}")
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
                band = _score_band(fcs)
                context_parts.append(
                    f"Current FCS score: {round(fcs, 1)} ({band})"
                )

            # Pull all five dimension scores
            dims = {}
            for db_field in ["stability", "outlook", "purchasing_power",
                              "emergency_readiness", "income_adequacy", "financial_agency"]:
                val = getattr(snapshot, db_field, None)
                if val is not None:
                    label = DIMENSION_LABELS.get(db_field, db_field)
                    weight = DIMENSION_WEIGHTS.get(db_field, "")
                    dims[label] = (round(val, 1), _score_band(val), weight)

            if dims:
                dim_lines = [
                    f"  • {label} ({weight}): {score} — {band}"
                    for label, (score, band, weight) in dims.items()
                ]
                context_parts.append(
                    "Dimension breakdown:\n" + "\n".join(dim_lines)
                )

                # Flag weak dimensions so Grace can proactively address them
                weak = [
                    label for label, (score, band, weight) in dims.items()
                    if score < 60
                ]
                if weak:
                    context_parts.append(
                        f"Dimensions needing attention (score < 60): {', '.join(weak)}"
                    )

                strong = [
                    label for label, (score, band, weight) in dims.items()
                    if score >= 75
                ]
                if strong:
                    context_parts.append(
                        f"Strong dimensions (score ≥ 75): {', '.join(strong)}"
                    )
    except Exception:
        pass

    if context_parts:
        return (
            "\n\n══════════════════════════════════════\n"
            "LIVE USER CONTEXT (use naturally in coaching)\n"
            "══════════════════════════════════════\n"
            + "\n".join(context_parts)
            + "\n══════════════════════════════════════"
        )
    return ""


def chat_with_grace(db: Session, user_id: int, messages: list[dict]) -> str:
    """
    Send a conversation to Claude with full platform knowledge + live user context.
    Falls back to basic context if behavioral engine isn't deployed.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set. Add it to your environment variables.")

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
            user_context = _build_basic_context(db, user_id)
    else:
        user_context = _build_basic_context(db, user_id)

    system_prompt = GRACE_SYSTEM_PROMPT + user_context + insight_block

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=system_prompt,
        messages=messages,
    )

    response_text = response.content[0].text

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