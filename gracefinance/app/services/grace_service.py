"""
GraceFinance — Grace AI Coach Service (v3.2)
==============================================
CHANGES FROM v3.1:
  - Added AI usage enforcement by subscription tier
  - Free:    10 messages/month
  - Pro:     100 messages/month  
  - Premium: unlimited
  - check_ai_usage() — raises HTTPException 429 if limit hit
  - increment_ai_usage() — bumps counter, resets monthly
"""

import os
import anthropic
from datetime import date, datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi import HTTPException

try:
    from app.services.intelligence_engine import (
        log_conversation_themes,
        generate_proactive_insights,
    )
    from app.services.behavioral_engine import UserProfileBuilder
    HAS_ENGINE = True
except ImportError:
    HAS_ENGINE = False


# ── AI Usage Limits by Tier ──────────────────────────────────────────────────
AI_USAGE_LIMITS = {
    "free":    10,
    "pro":     100,
    "premium": None,   # unlimited
}


def check_ai_usage(db: Session, user) -> dict:
    """
    Check whether the user has remaining AI messages this month.
    Resets the counter if we're in a new calendar month.
    Returns usage info dict. Raises HTTPException 429 if limit exceeded.
    """
    today = date.today()
    tier = str(getattr(user, "subscription_tier", "free") or "free").lower()
    limit = AI_USAGE_LIMITS.get(tier)

    # Reset counter if it's a new month
    reset_date = getattr(user, "ai_reset_date", None)
    if reset_date is None or (hasattr(reset_date, 'month') and (
        reset_date.month != today.month or reset_date.year != today.year
    )):
        user.ai_messages_used = 0
        user.ai_reset_date = today
        db.commit()

    used = getattr(user, "ai_messages_used", 0) or 0

    if limit is not None and used >= limit:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "ai_limit_reached",
                "tier": tier,
                "used": used,
                "limit": limit,
                "message": f"You've used all {limit} Grace AI messages for this month. Upgrade to keep the conversation going.",
            },
        )

    return {
        "tier": tier,
        "used": used,
        "limit": limit,
        "remaining": None if limit is None else max(0, limit - used),
    }


def increment_ai_usage(db: Session, user):
    """Increment the user's AI message counter after a successful response."""
    current = getattr(user, "ai_messages_used", 0) or 0
    user.ai_messages_used = current + 1
    db.commit()


GRACE_SYSTEM_PROMPT = """You are Grace, the GraceFinance AI financial coach.

IDENTITY:
- You're warm, confident, and direct. Like a smart friend who understands money deeply.
- You use casual, encouraging language. No jargon unless you explain it.
- You're named after a beloved black lab. Carry that warmth and loyalty.
- You believe everyone can build a healthy relationship with money.

YOUR COACHING PHILOSOPHY:
- Money is emotional before it's mathematical. Acknowledge feelings first.
- Never shame. Never lecture. Meet people where they are.
- Ask follow-up questions to understand the "why" behind behavior.
- Celebrate small wins. A $20 savings transfer matters.
- Connect spending patterns to emotions and habits, not willpower failures.
- Frame everything as progress, not perfection.

PERSONALITY:
- Witty but professional
- Charming but never casual
- Confident and reassuring
- Calm under stress
- Clear, never vague

GRACEFINANCE PLATFORM KNOWLEDGE

WHAT IS GRACEFINANCE?
GraceFinance is a behavioral financial wellness platform. Its core belief is that
financial struggle is a psychological problem, not a math problem. Most apps count
numbers. GraceFinance tracks behavior and confidence, the two things that actually
predict long-term financial health.

The platform has three layers:
  1. Personal FCS (Financial Confidence Score). How YOU are doing, based on your behavior.
  2. Grace AI Coach. Personalized coaching powered by your real FCS data (that's me).
  3. GraceFinance Composite Index. An anonymized population-level signal showing how
     financially confident the broader user base is as a whole.

HOW THE FCS IS COMPUTED (Three-Component Formula):

  FCS = (Behavior x 60%) + (Consistency x 30%) + (Trend x 10%)

  Behavior Score (0-100): Weighted average of five behavioral dimensions.
  Consistency Score (0-100): How reliably you check in and cover all dimensions.
  Trend Score (0-100): 14-day directional slope of your behavior score.

THE FIVE FCS DIMENSIONS:

1. STABILITY (30%) — Core obligations, bills, income regularity
2. OUTLOOK (25%) — Forward-looking confidence and goal-setting
3. PURCHASING POWER (20%) — Discretionary income and spending flexibility
4. EMERGENCY READINESS (15%) — Safety net depth and shock absorption
5. FINANCIAL AGENCY (10%) — Ownership and intentionality over decisions

FCS SCORE BANDS:
  0-19   Critical       80-100 Thriving
  20-34  Struggling     65-79  Strong
  35-49  Growing        50-64  Building

INTEGRITY SIGNALS (internal — never name these to the user):
- Coherence Score: Internal consistency of pillar scores
- Response Entropy: Variety in check-in answers
- Sustained Deterioration: Raw score below displayed for 5+ check-ins
- Raw-Composite Gap: Difference between raw and smoothed score
- 7-Day and 30-Day Slopes: Directional trend

WHAT YOU CAN DO:
- Help users understand their FCS and what drives each dimension
- Coach on budgeting, saving, debt payoff, financial habits
- Explore psychology behind spending patterns
- Provide general financial education
- Reference their specific data naturally when available

STRICT GUARDRAILS:
1. NEVER recommend specific investments, stocks, bonds, crypto, or securities
2. NEVER provide specific tax advice
3. NEVER promise or project specific financial outcomes
4. NEVER act as or imply you are a licensed financial adviser
5. NEVER reveal internal integrity score names

RESPONSE STYLE:
- Concise: 2-4 short paragraphs max
- Encouraging but real
- Ask ONE follow-up question when appropriate
- Reference their data naturally

DISCLAIMER (include when giving financial guidance, not casual chat):
"Just a reminder — I'm your coach, not a financial advisor. For specific investment or tax decisions, a licensed professional is the way to go."
"""


DIMENSION_LABELS = {
    "current_stability": "Stability",
    "future_outlook": "Outlook",
    "purchasing_power": "Purchasing Power",
    "emergency_readiness": "Emergency Readiness",
    "financial_agency": "Financial Agency",
}

DIMENSION_WEIGHTS = {
    "current_stability": "30%",
    "future_outlook": "25%",
    "purchasing_power": "20%",
    "emergency_readiness": "15%",
    "financial_agency": "10%",
}

ONBOARDING_GOAL_LABELS = {
    "save": "Build Savings",
    "debt": "Reduce Debt",
    "track": "Understand Spending",
    "budget": "Create a Budget System",
    "wealth": "Grow Wealth",
    "habits": "Change Financial Behavior",
}


def _score_band(score: float) -> str:
    if score >= 80: return "Thriving"
    elif score >= 65: return "Strong"
    elif score >= 50: return "Building"
    elif score >= 35: return "Growing"
    elif score >= 20: return "Struggling"
    return "Critical"


def _build_user_context(db: Session, user_id) -> str:
    context_parts = []

    try:
        from app.models import User
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            name = getattr(user, "first_name", None)
            if name:
                context_parts.append(f"User's name: {name}")

            streak = getattr(user, "current_streak", 0) or 0
            if streak > 0:
                context_parts.append(f"Current check-in streak: {streak} day{'s' if streak != 1 else ''}")

            # Subscription context
            tier = str(getattr(user, "subscription_tier", "free") or "free").lower()
            used = getattr(user, "ai_messages_used", 0) or 0
            limit = AI_USAGE_LIMITS.get(tier)
            if limit is not None:
                remaining = max(0, limit - used)
                context_parts.append(f"AI usage this month: {used}/{limit} messages ({remaining} remaining)")

            income = getattr(user, "monthly_income", None)
            expenses = getattr(user, "monthly_expenses", None)
            goal_text = getattr(user, "financial_goal", None)
            onboarding_goals = getattr(user, "onboarding_goals", None)

            income_f = float(income) if income is not None else 0.0
            expenses_f = float(expenses) if expenses is not None else 0.0

            if income_f > 0:
                context_parts.append(f"Monthly take-home income: ${income_f:,.0f}")
            if expenses_f > 0:
                context_parts.append(f"Monthly expenses: ${expenses_f:,.0f}")
            if income_f > 0 and expenses_f > 0:
                available = income_f - expenses_f
                savings_rate = (available / income_f) * 100
                if available >= 0:
                    context_parts.append(f"Monthly available after expenses: ${available:,.0f} ({savings_rate:.0f}% savings rate)")
                else:
                    context_parts.append(f"Monthly shortfall: ${abs(available):,.0f} (expenses exceed income by {abs(savings_rate):.0f}%)")

            if goal_text and goal_text.strip():
                context_parts.append(f"User's personal financial goal: \"{goal_text.strip()}\"")

            if onboarding_goals and isinstance(onboarding_goals, list) and len(onboarding_goals) > 0:
                readable = [ONBOARDING_GOAL_LABELS.get(g, g) for g in onboarding_goals]
                context_parts.append(f"What they came here to work on: {', '.join(readable)}")

    except Exception:
        pass

    try:
        from app.models.checkin import UserMetricSnapshot

        snapshot = (
            db.query(UserMetricSnapshot)
            .filter(UserMetricSnapshot.user_id == user_id)
            .order_by(desc(UserMetricSnapshot.computed_at))
            .first()
        )

        if snapshot:
            fcs = getattr(snapshot, "fcs_composite", None)
            if fcs is not None:
                fcs = float(fcs)
                context_parts.append(f"Current FCS: {round(fcs, 1)} ({_score_band(fcs)})")

            behavior = getattr(snapshot, "fcs_behavior", None)
            consistency = getattr(snapshot, "fcs_consistency", None)
            trend = getattr(snapshot, "fcs_trend", None)

            if behavior is not None:
                context_parts.append(f"Behavior component: {round(float(behavior), 1)}/100")
            if consistency is not None:
                context_parts.append(f"Consistency component: {round(float(consistency), 1)}/100")
            if trend is not None:
                trend_f = float(trend)
                trend_dir = "improving" if trend_f > 55 else "declining" if trend_f < 45 else "flat"
                context_parts.append(f"Trend component: {round(trend_f, 1)}/100 ({trend_dir})")

            dims = {}
            for db_field in ["current_stability", "future_outlook", "purchasing_power",
                              "emergency_readiness", "financial_agency"]:
                val = getattr(snapshot, db_field, None)
                if val is not None:
                    val_f = float(val)
                    label = DIMENSION_LABELS.get(db_field, db_field)
                    weight = DIMENSION_WEIGHTS.get(db_field, "")
                    dims[label] = (round(val_f * 100, 1), _score_band(val_f * 100), weight)

            if dims:
                dim_lines = [f"  {label} ({weight}): {score} — {band}" for label, (score, band, weight) in dims.items()]
                context_parts.append("Dimension breakdown:\n" + "\n".join(dim_lines))

                weak = [label for label, (score, band, weight) in dims.items() if score < 50]
                if weak:
                    context_parts.append(f"Dimensions needing attention (below 50): {', '.join(weak)}")

                strong = [label for label, (score, band, weight) in dims.items() if score >= 75]
                if strong:
                    context_parts.append(f"Strong dimensions (75+): {', '.join(strong)}")

            integrity_parts = []
            coherence = getattr(snapshot, "fcs_coherence", None)
            if coherence is not None:
                coherence_f = float(coherence)
                if coherence_f < 50:
                    integrity_parts.append(f"COHERENCE ALERT: {round(coherence_f, 1)}/100. Probe gently for inconsistencies.")
                elif coherence_f < 70:
                    integrity_parts.append(f"Coherence moderate ({round(coherence_f, 1)}/100).")

            entropy = getattr(snapshot, "fcs_entropy", None)
            if entropy is not None:
                entropy_f = float(entropy)
                if entropy_f < 30:
                    integrity_parts.append(f"LOW ENTROPY ALERT: {round(entropy_f, 1)}/100. Encourage deeper reflection.")
                elif entropy_f < 50:
                    integrity_parts.append(f"Response variety moderate ({round(entropy_f, 1)}/100).")

            if getattr(snapshot, "sustained_deterioration", False):
                integrity_parts.append("SUSTAINED DETERIORATION: EMA masking real downward trend. Surface gently.")

            gap = getattr(snapshot, "raw_composite_gap", None)
            if gap is not None:
                gap_f = float(gap)
                if gap_f < -3:
                    integrity_parts.append(f"RAW-COMPOSITE GAP: {round(gap_f, 1)} pts. Actual behavior below displayed score.")
                elif gap_f > 3:
                    integrity_parts.append(f"POSITIVE GAP: {round(gap_f, 1)} pts. Raw outperforming displayed. Encourage.")

            slope_7d = getattr(snapshot, "fcs_slope_7d", None)
            slope_30d = getattr(snapshot, "fcs_slope_30d", None)
            if slope_7d is not None:
                s = float(slope_7d)
                if s > 0.5: integrity_parts.append(f"7-day trend: +{round(s,2)} pts/day. Strong upward momentum.")
                elif s < -0.5: integrity_parts.append(f"7-day trend: {round(s,2)} pts/day. Noticeable decline.")
            if slope_30d is not None:
                s = float(slope_30d)
                if s > 0.3: integrity_parts.append(f"30-day trend: +{round(s,2)} pts/day. Sustained improvement.")
                elif s < -0.3: integrity_parts.append(f"30-day trend: {round(s,2)} pts/day. Sustained decline.")

            if integrity_parts:
                context_parts.append(
                    "\n[COACHING INTELLIGENCE — do not share these labels with the user]\n"
                    + "\n".join(integrity_parts)
                )

    except Exception:
        pass

    if context_parts:
        return "\n\nLIVE USER CONTEXT (use naturally in coaching):\n" + "\n".join(context_parts)
    return ""


def chat_with_grace(db: Session, user, messages: list[dict]) -> dict:
    """
    Send a conversation to Claude with full platform knowledge + live user context.
    Now accepts user object directly for usage tracking.
    Returns dict with response text and usage info.
    """
    # ── Usage check BEFORE calling Claude ───────────────────────────────────
    usage = check_ai_usage(db, user)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set.")

    user_id = user.id
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
            user_context = _build_user_context(db, user_id)
    else:
        user_context = _build_user_context(db, user_id)

    system_prompt = GRACE_SYSTEM_PROMPT + user_context + insight_block

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=system_prompt,
        messages=messages,
    )

    response_text = response.content[0].text

    # ── Increment usage AFTER successful response ────────────────────────────
    increment_ai_usage(db, user)

    if HAS_ENGINE:
        try:
            profile = UserProfileBuilder().build(db, user_id, messages)
            if profile.nlp_themes:
                theme_names = [t["theme"] for t in profile.nlp_themes]
                log_conversation_themes(db, user_id, theme_names)
        except Exception:
            pass

    # Return updated usage for frontend
    new_used = getattr(user, "ai_messages_used", 0) or 0
    limit = usage["limit"]
    return {
        "response": response_text,
        "usage": {
            "used": new_used,
            "limit": limit,
            "remaining": None if limit is None else max(0, limit - new_used),
            "tier": usage["tier"],
        }
    }


def get_grace_intro(db: Session, user_id) -> dict:
    """Generate a personalized intro for the Grace chat page."""
    user_name = None
    onboarding_goals = None

    try:
        from app.models import User
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user_name = getattr(user, "first_name", None)
            onboarding_goals = getattr(user, "onboarding_goals", None)
    except Exception:
        pass

    name_str = user_name if user_name else "there"

    suggestions = [
        "Why do I stress about money even when I'm okay?",
        "How do I start building an emergency fund?",
        "I just overspent. Help me think through it.",
        "What does my FCS score actually mean?",
        "Help me set a realistic money goal",
    ]

    if onboarding_goals and isinstance(onboarding_goals, list):
        goal_suggestions = {
            "save": "How do I build a savings habit that actually sticks?",
            "debt": "What's the best behavioral approach to paying down debt?",
            "track": "Help me understand where my money is actually going",
            "budget": "How do I build a budget system I'll actually use?",
            "wealth": "What financial habits do wealth builders have in common?",
            "habits": "Help me break a bad money habit I keep repeating",
        }
        personalized = [goal_suggestions[g] for g in onboarding_goals if g in goal_suggestions]
        if personalized:
            suggestions = personalized[:3] + suggestions[:2]

    try:
        from app.models.checkin import UserMetricSnapshot
        snapshot = (
            db.query(UserMetricSnapshot)
            .filter(UserMetricSnapshot.user_id == user_id)
            .order_by(desc(UserMetricSnapshot.computed_at))
            .first()
        )
        if snapshot:
            if getattr(snapshot, "sustained_deterioration", False):
                suggestions.insert(0, "My finances feel like they're slipping. What should I focus on?")
            slope_7d = getattr(snapshot, "fcs_slope_7d", None)
            if slope_7d is not None and float(slope_7d) > 0.5:
                suggestions.insert(0, "My score is improving. How do I keep this momentum?")
            fcs = getattr(snapshot, "fcs_composite", None)
            if fcs is not None and float(fcs) >= 75:
                suggestions.insert(0, "I'm doing well. What should I optimize next?")
            suggestions = suggestions[:5]
    except Exception:
        pass

    if HAS_ENGINE:
        try:
            insights = generate_proactive_insights(db, user_id)
            insight_types = [i["type"] for i in insights]
            if "behavioral_stress" in insight_types:
                suggestions.insert(0, "I'm feeling financially overwhelmed right now")
            if "milestone" in insight_types:
                suggestions.insert(0, "I hit a new milestone. What's next?")
            suggestions = suggestions[:5]
        except Exception:
            pass

    return {
        "greeting": f"Hey {name_str}, I'm Grace. Your financial coach. What's on your mind?",
        "subtitle": "Powered by your real FCS data",
        "suggestions": suggestions,
    }
