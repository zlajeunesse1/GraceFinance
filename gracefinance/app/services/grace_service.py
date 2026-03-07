"""
GraceFinance — Grace AI Coach Service (v3.0)
==============================================
CHANGES FROM v2.2:
  - Full v5.1 audit signals injected into user context:
    * Three-component FCS breakdown (behavior, consistency, trend)
    * Cross-dimensional coherence score
    * Response entropy (gaming detection)
    * Sustained deterioration flag
    * Raw-composite gap (EMA masking detection)
    * 7-day and 30-day slopes
  - Grace becomes smarter per user over time:
    * Low coherence → Grace probes contradictions
    * Low entropy → Grace varies her questions
    * Sustained deterioration → Grace surfaces the hidden trend
    * Widening gap → Grace calls out the divergence
  - System prompt updated with three-component formula knowledge
  - Context builder uses UserMetricSnapshot directly (no legacy FCSSnapshot)
"""

import os
import anthropic
from sqlalchemy.orm import Session
from sqlalchemy import desc

# Graceful imports
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
    This is what you're actually doing with money right now.

  Consistency Score (0-100): How reliably you check in and cover all dimensions.
    Checking in 7 days a week across all 5 pillars = 100.
    Sporadic check-ins = lower score.
    This rewards showing up, but does NOT inflate the behavior score.

  Trend Score (0-100): 14-day directional slope of your behavior score.
    50 = flat. Above 50 = improving. Below 50 = declining.
    This captures momentum. Are you getting better or worse?

THE FIVE FCS DIMENSIONS:

1. STABILITY (30% of Behavior Score)
   How consistently you meet core financial obligations.
   What moves it: On-time bills, income regularity, avoiding overdrafts.
   Coaching: Low Stability is always the first problem to solve. Everything else
   is noise until the foundation holds.

2. OUTLOOK (25% of Behavior Score)
   Forward-looking financial confidence and goal-setting behavior.
   What moves it: Goal progress, planning, expressed optimism.
   Coaching: Outlook responds powerfully to small wins. Low Outlook often
   means shame or hopelessness. Meet it with empathy first.

3. PURCHASING POWER (20% of Behavior Score)
   Discretionary income and spending flexibility after obligations.
   What moves it: Spending headroom, ability to absorb surprise costs.
   Coaching: Low Purchasing Power is often structural (income vs costs)
   but sometimes behavioral (lifestyle creep). Understanding which one matters.

4. EMERGENCY READINESS (15% of Behavior Score)
   Financial safety net depth and shock absorption capacity.
   What moves it: Savings cushion, active contributions, preparedness.
   Coaching: Building an emergency fund is often the highest-leverage habit
   change available. Even $500 changes the psychology.

5. FINANCIAL AGENCY (10% of Behavior Score)
   Ownership and intentionality over financial decisions.
   What moves it: Active management, learning, deliberate choices.
   Coaching: Agency increases when people feel seen and capable. Never
   suggest someone is a victim of their choices.

FCS SCORE BANDS:
  0-19   Critical       Immediate attention needed
  20-34  Struggling     Foundation is shaky
  35-49  Growing        In the arena, showing up
  50-64  Building       Real progress, some fragility
  65-79  Strong         Solid foundation
  80-100 Thriving       Financially confident and resilient

INTEGRITY SIGNALS (use these to coach smarter):

  Coherence Score (0-100): How internally consistent are the user's pillar scores?
    High coherence = believable, consistent data.
    Low coherence = contradictory signals. Example: claiming high stability
    but zero emergency readiness. When you see low coherence, gently probe
    the contradiction. "Your stability looks solid but your emergency readiness
    is lagging. What's happening there?"

  Response Entropy (0-100): How varied are the user's check-in answers?
    High entropy = honest, varied responses (good).
    Low entropy = same answers every day (potential disengagement or gaming).
    When you see low entropy, encourage deeper reflection. "I notice your
    answers have been pretty consistent lately. Has anything actually changed
    in your financial life this week?"

  Sustained Deterioration: True when the raw score has been below the
    displayed score for 5+ consecutive check-ins. This means the EMA
    smoothing is masking a real downward trend. When this flag is True,
    surface it directly but gently. "Your score looks stable on the surface,
    but I'm seeing some signals underneath that suggest things might be
    tightening. Want to talk about what's changed recently?"

  Raw-Composite Gap: The difference between the raw daily score and the
    smoothed displayed score. A growing negative gap means the user's
    actual behavior is declining faster than the score shows.

  7-Day and 30-Day Slopes: The directional trend of the FCS over time.
    Negative slope = declining. Positive = improving. Use these to
    contextualize coaching. "Your 7-day trend is pointing up. Whatever
    you changed this week is working."

HOW TO USE INTEGRITY SIGNALS:
- Never tell the user their "coherence score" or "entropy score" directly.
  These are internal signals for your coaching intelligence.
- Use them to shape your questions, not your statements.
- Low coherence → ask probing questions about contradictions.
- Low entropy → encourage deeper reflection on recent changes.
- Sustained deterioration → surface the hidden trend with empathy.
- Positive slopes → reinforce the momentum.
- Negative slopes → acknowledge the difficulty without catastrophizing.

WHAT YOU CAN DO:
- Help users understand their FCS score and what drives each dimension.
- Coach on budgeting, saving, debt payoff, and building financial habits.
- Explore the psychology behind spending. Stress spending, retail therapy, avoidance.
- Provide general financial education and literacy.
- Help set realistic, achievable money goals.
- When you have their data, reference specific numbers naturally.
- Use integrity signals to ask smarter, more targeted questions.

STRICT GUARDRAILS:
1. NEVER recommend specific investments, stocks, bonds, crypto, or securities.
2. NEVER provide specific tax advice or suggest tax strategies.
3. NEVER promise or project specific financial outcomes or returns.
4. NEVER act as or imply you are a fiduciary or licensed financial adviser.
5. NEVER share or reference other users' specific data.
6. NEVER reveal internal integrity scores (coherence, entropy) by name.
7. If asked about investing specifics: "I focus on building your financial foundation. For investment advice, I'd recommend a licensed financial advisor."
8. If user seems in genuine crisis (eviction, can't afford food/medicine), gently suggest 211.org or local resources while staying supportive.

RESPONSE STYLE:
- Concise: 2-4 short paragraphs max for most messages.
- Encouraging but real. Don't be fake-positive.
- Ask ONE follow-up question when appropriate.
- Reference their data naturally. "Your stability score jumped this week" not "According to your data..."
- Use simple analogies for financial concepts.

DISCLAIMER (include naturally when giving financial guidance, not for casual chat):
"Just a reminder. I'm your coach, not a financial advisor. For specific investment or tax decisions, a licensed professional is the way to go."
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


def _score_band(score: float) -> str:
    if score >= 80:
        return "Thriving"
    elif score >= 65:
        return "Strong"
    elif score >= 50:
        return "Building"
    elif score >= 35:
        return "Growing"
    elif score >= 20:
        return "Struggling"
    return "Critical"


def _build_user_context(db: Session, user_id) -> str:
    """
    Build rich user context from the latest UserMetricSnapshot.
    Includes all v5.1 audit signals for intelligent coaching.
    """
    context_parts = []

    # User name
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
    except Exception:
        pass

    # Latest snapshot with all audit signals
    try:
        from app.models.checkin import UserMetricSnapshot, CheckInResponse
        from sqlalchemy import func, and_
        from datetime import datetime, timezone, timedelta

        snapshot = (
            db.query(UserMetricSnapshot)
            .filter(UserMetricSnapshot.user_id == user_id)
            .order_by(desc(UserMetricSnapshot.computed_at))
            .first()
        )

        if snapshot:
            # Three-component breakdown
            fcs = getattr(snapshot, "fcs_composite", None)
            if fcs is not None:
                fcs = float(fcs)
                band = _score_band(fcs)
                context_parts.append(f"Current FCS: {round(fcs, 1)} ({band})")

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

            # Five dimensions
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
                dim_lines = [
                    f"  {label} ({weight}): {score} — {band}"
                    for label, (score, band, weight) in dims.items()
                ]
                context_parts.append("Dimension breakdown:\n" + "\n".join(dim_lines))

                weak = [label for label, (score, band, weight) in dims.items() if score < 50]
                if weak:
                    context_parts.append(f"Dimensions needing attention (below 50): {', '.join(weak)}")

                strong = [label for label, (score, band, weight) in dims.items() if score >= 75]
                if strong:
                    context_parts.append(f"Strong dimensions (75+): {', '.join(strong)}")

            # Integrity signals (internal coaching intelligence)
            integrity_parts = []

            coherence = getattr(snapshot, "fcs_coherence", None)
            if coherence is not None:
                coherence_f = float(coherence)
                if coherence_f < 50:
                    integrity_parts.append(f"COHERENCE ALERT: Score is {round(coherence_f, 1)}/100. User's pillar scores are internally contradictory. Probe gently for inconsistencies.")
                elif coherence_f < 70:
                    integrity_parts.append(f"Coherence is moderate ({round(coherence_f, 1)}/100). Some dimensional inconsistency detected.")

            entropy = getattr(snapshot, "fcs_entropy", None)
            if entropy is not None:
                entropy_f = float(entropy)
                if entropy_f < 30:
                    integrity_parts.append(f"LOW ENTROPY ALERT: Score is {round(entropy_f, 1)}/100. User gives very similar answers every day. Encourage deeper reflection and varied self-assessment.")
                elif entropy_f < 50:
                    integrity_parts.append(f"Response variety is moderate ({round(entropy_f, 1)}/100). Could benefit from more reflective check-ins.")

            deterioration = getattr(snapshot, "sustained_deterioration", False)
            if deterioration:
                integrity_parts.append("SUSTAINED DETERIORATION: Raw score has been below displayed score for 5+ consecutive check-ins. The EMA smoothing is masking a real downward trend. Surface this gently but directly.")

            gap = getattr(snapshot, "raw_composite_gap", None)
            if gap is not None:
                gap_f = float(gap)
                if gap_f < -3:
                    integrity_parts.append(f"RAW-COMPOSITE GAP: {round(gap_f, 1)} points. The user's actual daily behavior is significantly below their displayed smoothed score. The trend is worse than it appears.")
                elif gap_f > 3:
                    integrity_parts.append(f"POSITIVE GAP: {round(gap_f, 1)} points. User's raw behavior is outperforming their displayed score. The improvement hasn't fully shown up yet. Encourage them.")

            slope_7d = getattr(snapshot, "fcs_slope_7d", None)
            slope_30d = getattr(snapshot, "fcs_slope_30d", None)
            if slope_7d is not None:
                slope_7d_f = float(slope_7d)
                if slope_7d_f > 0.5:
                    integrity_parts.append(f"7-day trend: +{round(slope_7d_f, 2)} pts/day. Strong upward momentum this week.")
                elif slope_7d_f < -0.5:
                    integrity_parts.append(f"7-day trend: {round(slope_7d_f, 2)} pts/day. Noticeable decline this week.")
            if slope_30d is not None:
                slope_30d_f = float(slope_30d)
                if slope_30d_f > 0.3:
                    integrity_parts.append(f"30-day trend: +{round(slope_30d_f, 2)} pts/day. Sustained improvement over the past month.")
                elif slope_30d_f < -0.3:
                    integrity_parts.append(f"30-day trend: {round(slope_30d_f, 2)} pts/day. Sustained decline over the past month.")

            if integrity_parts:
                context_parts.append(
                    "\n[COACHING INTELLIGENCE — do not share these labels with the user]\n"
                    + "\n".join(integrity_parts)
                )

            # Check-in count
            checkin_count = getattr(snapshot, "checkin_count", 0)
            if checkin_count:
                context_parts.append(f"Total responses in scoring window: {checkin_count}")

    except Exception:
        pass

    if context_parts:
        return (
            "\n\nLIVE USER CONTEXT (use naturally in coaching):\n"
            + "\n".join(context_parts)
        )
    return ""


def chat_with_grace(db: Session, user_id, messages: list[dict]) -> str:
    """
    Send a conversation to Claude with full platform knowledge + live user context.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set.")

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

    if HAS_ENGINE:
        try:
            profile = UserProfileBuilder().build(db, user_id, messages)
            if profile.nlp_themes:
                theme_names = [t["theme"] for t in profile.nlp_themes]
                log_conversation_themes(db, user_id, theme_names)
        except Exception:
            pass

    return response_text


def get_grace_intro(db: Session, user_id) -> dict:
    """Generate a personalized intro for the Grace chat page."""
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
        "I just overspent. Help me think through it.",
        "What does my FCS score actually mean?",
        "Help me set a realistic money goal",
    ]

    # Personalize suggestions based on latest snapshot
    try:
        from app.models.checkin import UserMetricSnapshot

        snapshot = (
            db.query(UserMetricSnapshot)
            .filter(UserMetricSnapshot.user_id == user_id)
            .order_by(desc(UserMetricSnapshot.computed_at))
            .first()
        )

        if snapshot:
            deterioration = getattr(snapshot, "sustained_deterioration", False)
            if deterioration:
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