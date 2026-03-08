"""
BSI Question Bank v2 — Behavioral Shift Questions with Motivation Layer
═══════════════════════════════════════════════════════════════════════
Each behavioral pattern has:
  1. A trigger question (did the behavior happen?)
  2. A motivation follow-up (WHY did it happen?)

The motivation determines:
  - Whether the behavior is a STRESS signal or a POSITIVE signal
  - Which FCS dimension it maps back to
  - What coaching context Grace receives
  - How it scores in the BSI composite

This is the engine that makes GraceFinance's behavioral data
institutional-grade. We don't just track WHAT people do —
we track WHY they do it. Nobody else has this.

File: app/services/bsi_questions.py
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class MotivationOption:
    """A single 'why' option with its scoring implications."""
    id: str
    text: str
    signal: str            # "stress", "positive", "neutral", "avoidance"
    score_modifier: float  # -1.0 (max stress) to +1.0 (max positive)
    maps_to_dimension: str # Which FCS dimension this reflects
    coaching_tag: str      # Short tag for Grace's context


@dataclass
class BSIQuestion:
    """A behavioral trigger question with conditional motivation follow-ups."""
    question_id: str
    pattern: str              # subscription_churn, credit_substitution, etc.
    trigger_text: str         # The yes/no behavioral question
    trigger_type: str         # "yes_no" or "frequency"
    motivations_if_yes: List[MotivationOption]   # Follow-ups if behavior happened
    motivations_if_no: Optional[List[MotivationOption]] = None  # Optional: why NOT
    pattern_label: str = ""
    pattern_description: str = ""


# ═══════════════════════════════════════════════════════════════
#  PATTERN 1: SUBSCRIPTION CHURN
#  Signal: Are they cutting recurring costs?
#  Key insight: WHY determines if it's stress or optimization
# ═══════════════════════════════════════════════════════════════

SUBSCRIPTION_CHURN = BSIQuestion(
    question_id="BX-1",
    pattern="subscription_churn",
    pattern_label="Subscription Churn",
    pattern_description="Canceling or downgrading recurring services",
    trigger_text="Did you cancel, pause, or downgrade any recurring subscription or service this week?",
    trigger_type="yes_no",
    motivations_if_yes=[
        MotivationOption(
            id="BX-1-A",
            text="I can't afford it right now",
            signal="stress",
            score_modifier=-0.8,
            maps_to_dimension="current_stability",
            coaching_tag="cost_pressure",
        ),
        MotivationOption(
            id="BX-1-B",
            text="I'm cleaning up expenses I don't actually use",
            signal="positive",
            score_modifier=0.7,
            maps_to_dimension="financial_agency",
            coaching_tag="intentional_optimization",
        ),
        MotivationOption(
            id="BX-1-C",
            text="I'm cutting back to save for something specific",
            signal="positive",
            score_modifier=0.8,
            maps_to_dimension="future_outlook",
            coaching_tag="goal_directed_saving",
        ),
        MotivationOption(
            id="BX-1-D",
            text="I felt anxious about how much I'm spending",
            signal="avoidance",
            score_modifier=-0.4,
            maps_to_dimension="emergency_readiness",
            coaching_tag="spending_anxiety",
        ),
    ],
)


# ═══════════════════════════════════════════════════════════════
#  PATTERN 2: CREDIT SUBSTITUTION
#  Signal: Are they shifting from cash/debit to credit?
#  Key insight: Strategic vs desperate credit usage
# ═══════════════════════════════════════════════════════════════

CREDIT_SUBSTITUTION = BSIQuestion(
    question_id="BX-2",
    pattern="credit_substitution",
    pattern_label="Credit Substitution",
    pattern_description="Using credit for purchases normally paid with cash or debit",
    trigger_text="Did you use a credit card this week for something you would normally pay with cash or debit?",
    trigger_type="yes_no",
    motivations_if_yes=[
        MotivationOption(
            id="BX-2-A",
            text="Cash was tight — I needed to bridge the gap",
            signal="stress",
            score_modifier=-0.9,
            maps_to_dimension="current_stability",
            coaching_tag="cash_flow_pressure",
        ),
        MotivationOption(
            id="BX-2-B",
            text="I'm using a rewards or cash-back card strategically",
            signal="positive",
            score_modifier=0.6,
            maps_to_dimension="financial_agency",
            coaching_tag="strategic_credit_use",
        ),
        MotivationOption(
            id="BX-2-C",
            text="A big or unexpected expense came up",
            signal="neutral",
            score_modifier=-0.3,
            maps_to_dimension="emergency_readiness",
            coaching_tag="unplanned_expense",
        ),
        MotivationOption(
            id="BX-2-D",
            text="I wasn't really thinking about it",
            signal="avoidance",
            score_modifier=-0.5,
            maps_to_dimension="financial_agency",
            coaching_tag="autopilot_spending",
        ),
    ],
)


# ═══════════════════════════════════════════════════════════════
#  PATTERN 3: DEFERRED SPENDING
#  Signal: Are they putting off purchases they'd normally make?
#  Key insight: Strategic delay vs avoidance vs can't afford
# ═══════════════════════════════════════════════════════════════

DEFERRED_SPENDING = BSIQuestion(
    question_id="BX-3",
    pattern="deferred_spending",
    pattern_label="Deferred Spending",
    pattern_description="Delaying planned or routine purchases",
    trigger_text="Did you put off buying something this week that you'd normally purchase?",
    trigger_type="yes_no",
    motivations_if_yes=[
        MotivationOption(
            id="BX-3-A",
            text="I genuinely can't afford it right now",
            signal="stress",
            score_modifier=-0.9,
            maps_to_dimension="purchasing_power",
            coaching_tag="purchasing_inability",
        ),
        MotivationOption(
            id="BX-3-B",
            text="I'm being more intentional about what I spend on",
            signal="positive",
            score_modifier=0.7,
            maps_to_dimension="financial_agency",
            coaching_tag="intentional_delay",
        ),
        MotivationOption(
            id="BX-3-C",
            text="I'm waiting for a better deal or the right time",
            signal="positive",
            score_modifier=0.5,
            maps_to_dimension="purchasing_power",
            coaching_tag="strategic_timing",
        ),
        MotivationOption(
            id="BX-3-D",
            text="I felt guilty or anxious about spending",
            signal="avoidance",
            score_modifier=-0.6,
            maps_to_dimension="emergency_readiness",
            coaching_tag="spending_guilt",
        ),
    ],
)


# ═══════════════════════════════════════════════════════════════
#  PATTERN 4: DEBT ACCUMULATION
#  Signal: Are they taking on new debt?
#  Key insight: Leveraged investment vs survival borrowing
# ═══════════════════════════════════════════════════════════════

DEBT_ACCUMULATION = BSIQuestion(
    question_id="BX-4",
    pattern="debt_accumulation",
    pattern_label="Debt Accumulation",
    pattern_description="Taking on new debt or increasing existing balances",
    trigger_text="Did you take on any new debt or increase an existing balance this week?",
    trigger_type="yes_no",
    motivations_if_yes=[
        MotivationOption(
            id="BX-4-A",
            text="I had to cover essential expenses I couldn't afford",
            signal="stress",
            score_modifier=-1.0,
            maps_to_dimension="current_stability",
            coaching_tag="survival_borrowing",
        ),
        MotivationOption(
            id="BX-4-B",
            text="I'm investing in something that will pay off (education, business, etc.)",
            signal="positive",
            score_modifier=0.3,
            maps_to_dimension="future_outlook",
            coaching_tag="strategic_leverage",
        ),
        MotivationOption(
            id="BX-4-C",
            text="A medical or emergency expense forced it",
            signal="neutral",
            score_modifier=-0.5,
            maps_to_dimension="emergency_readiness",
            coaching_tag="emergency_debt",
        ),
        MotivationOption(
            id="BX-4-D",
            text="I made an impulse purchase I couldn't fully cover",
            signal="avoidance",
            score_modifier=-0.7,
            maps_to_dimension="financial_agency",
            coaching_tag="impulse_debt",
        ),
    ],
)


# ═══════════════════════════════════════════════════════════════
#  PATTERN 5: FINANCIAL AVOIDANCE
#  Signal: Are they disengaging from their finances?
#  Key insight: This is the most damaging pattern because it
#  compounds everything else. Avoidance makes every other
#  stress pattern worse.
# ═══════════════════════════════════════════════════════════════

FINANCIAL_AVOIDANCE = BSIQuestion(
    question_id="BX-5",
    pattern="financial_avoidance",
    pattern_label="Financial Avoidance",
    pattern_description="Disengaging from or avoiding financial awareness",
    trigger_text="Did you actively avoid checking your bank balance, bills, or financial accounts this week?",
    trigger_type="yes_no",
    motivations_if_yes=[
        MotivationOption(
            id="BX-5-A",
            text="I'm afraid of what I'll see",
            signal="stress",
            score_modifier=-0.9,
            maps_to_dimension="current_stability",
            coaching_tag="fear_avoidance",
        ),
        MotivationOption(
            id="BX-5-B",
            text="I've been too busy — life got in the way",
            signal="neutral",
            score_modifier=-0.2,
            maps_to_dimension="financial_agency",
            coaching_tag="time_pressure",
        ),
        MotivationOption(
            id="BX-5-C",
            text="I feel overwhelmed and don't know where to start",
            signal="stress",
            score_modifier=-0.8,
            maps_to_dimension="financial_agency",
            coaching_tag="financial_overwhelm",
        ),
        MotivationOption(
            id="BX-5-D",
            text="I checked earlier in the week and felt fine about it",
            signal="positive",
            score_modifier=0.4,
            maps_to_dimension="financial_agency",
            coaching_tag="confident_pause",
        ),
    ],
)


# ═══════════════════════════════════════════════════════════════
#  MASTER REGISTRY
# ═══════════════════════════════════════════════════════════════

BSI_QUESTIONS: Dict[str, BSIQuestion] = {
    "BX-1": SUBSCRIPTION_CHURN,
    "BX-2": CREDIT_SUBSTITUTION,
    "BX-3": DEFERRED_SPENDING,
    "BX-4": DEBT_ACCUMULATION,
    "BX-5": FINANCIAL_AVOIDANCE,
}

# Quick lookup: motivation_id → MotivationOption
MOTIVATION_LOOKUP: Dict[str, MotivationOption] = {}
for q in BSI_QUESTIONS.values():
    for m in q.motivations_if_yes:
        MOTIVATION_LOOKUP[m.id] = m


def get_bsi_questions() -> List[Dict]:
    """
    Return BSI questions formatted for the frontend.
    Each question includes its trigger + motivation options.
    """
    output = []
    for qid, q in BSI_QUESTIONS.items():
        output.append({
            "question_id": q.question_id,
            "pattern": q.pattern,
            "pattern_label": q.pattern_label,
            "trigger_text": q.trigger_text,
            "trigger_type": q.trigger_type,
            "motivations": [
                {
                    "id": m.id,
                    "text": m.text,
                    # Don't expose signal/score to frontend — that's internal
                }
                for m in q.motivations_if_yes
            ],
        })
    return output


def score_bsi_answer(question_id: str, triggered: bool, motivation_id: Optional[str] = None) -> Dict:
    """
    Score a single BSI answer.

    Returns:
        {
            "pattern": str,
            "triggered": bool,
            "score": float (-1.0 to 1.0),
            "signal": str,
            "maps_to_dimension": str,
            "coaching_tag": str,
        }
    """
    question = BSI_QUESTIONS.get(question_id)
    if not question:
        return {"pattern": "unknown", "triggered": False, "score": 0.0, "signal": "neutral"}

    if not triggered:
        # Behavior didn't happen — stable signal
        return {
            "pattern": question.pattern,
            "triggered": False,
            "score": 0.5,  # Mild positive — absence of stress behavior
            "signal": "stable",
            "maps_to_dimension": None,
            "coaching_tag": "no_shift",
        }

    # Behavior happened — score based on motivation
    if motivation_id:
        motivation = MOTIVATION_LOOKUP.get(motivation_id)
        if motivation:
            return {
                "pattern": question.pattern,
                "triggered": True,
                "score": motivation.score_modifier,
                "signal": motivation.signal,
                "maps_to_dimension": motivation.maps_to_dimension,
                "coaching_tag": motivation.coaching_tag,
            }

    # Triggered but no motivation selected — default mild stress
    return {
        "pattern": question.pattern,
        "triggered": True,
        "score": -0.3,
        "signal": "unknown",
        "maps_to_dimension": None,
        "coaching_tag": "unspecified_shift",
    }


# ═══════════════════════════════════════════════════════════════
#  DIMENSION REFLECTION MAP
#  When BSI detects a shift, it reflects back to FCS dimensions.
#  This creates the feedback loop that makes scores feel personal.
# ═══════════════════════════════════════════════════════════════

DIMENSION_REFLECTION = {
    "current_stability": {
        "stress_coaching": [
            "Your stability took a hit this week — {pattern_label} is a sign that your financial foundation needs attention.",
            "The pressure you're feeling on basic obligations is real. Stability is the hardest dimension to rebuild, but it starts with knowing where you stand.",
        ],
        "positive_coaching": [
            "Your stability is holding strong. The fact that {pattern_label} isn't driven by pressure shows your foundation is solid.",
        ],
    },
    "future_outlook": {
        "stress_coaching": [
            "Your outlook shifted this week. When {pattern_label} is stress-driven, it can feel like you're losing ground on the future. You're not — you're just navigating a moment.",
        ],
        "positive_coaching": [
            "You're making moves toward your future. {pattern_label} driven by goal-setting is one of the strongest signals of financial growth.",
        ],
    },
    "purchasing_power": {
        "stress_coaching": [
            "Your purchasing power is under pressure. {pattern_label} shows your spending capacity is tightening. Focus on what you can control this week.",
        ],
        "positive_coaching": [
            "Your purchasing power is stable. You're making spending decisions from a position of choice, not necessity.",
        ],
    },
    "emergency_readiness": {
        "stress_coaching": [
            "Your safety net absorbed some pressure this week. {pattern_label} driven by anxiety means your cushion feels thin. Even small deposits help rebuild confidence.",
        ],
        "positive_coaching": [
            "Your emergency readiness is in a good place. The absence of panic-driven behavior is a strong signal.",
        ],
    },
    "financial_agency": {
        "stress_coaching": [
            "You pulled back from active financial management this week. {pattern_label} on autopilot erodes agency over time. Even 5 minutes of review can shift this.",
        ],
        "positive_coaching": [
            "You're in the driver's seat. {pattern_label} driven by intentionality shows real financial agency — the hardest dimension to build.",
        ],
    },
}


def get_dimension_reflection(dimension: str, signal: str, pattern_label: str) -> str:
    """
    Get a coaching reflection that connects BSI behavior to FCS dimension.
    This is what makes the weekly report feel personal.
    """
    reflections = DIMENSION_REFLECTION.get(dimension, {})

    if signal in ("stress", "avoidance"):
        templates = reflections.get("stress_coaching", [])
    else:
        templates = reflections.get("positive_coaching", [])

    if not templates:
        return ""

    import random
    template = random.choice(templates)
    return template.format(pattern_label=pattern_label)