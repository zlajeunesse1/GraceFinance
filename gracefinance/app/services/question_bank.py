"""
Question Bank — v3.0 (Emergency Readiness Edition)
═══════════════════════════════════════════════════
CHANGES FROM v2.1:
  - LOCKED PILLARS: stability / outlook / purchasing_power /
                    emergency_readiness / financial_agency
  - debt_pressure REMOVED — replaced by emergency_readiness (ER-*)
  - FCS_WEIGHTS updated: emergency_readiness = 0.15
  - All DP-* questions retired; four new ER-* questions added
  - Normalization contract documented (frontend must send raw 1..scale_max)

REPLACES: app/services/question_bank.py
"""

import random
from datetime import date
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class CheckInQuestion:
    question_id: str
    question_text: str
    dimension: str
    scale_type: str          # "1-5" | "1-10" | "yes_no_scale"
    scale_max: int           # raw answer range top (raw answer is always 1..scale_max)
    low_label: str = "Low"
    high_label: str = "High"
    is_weekly: bool = False


# ══════════════════════════════════════════
#  LOCKED DIMENSION WEIGHTS  (must sum to 1.0)
# ══════════════════════════════════════════

FCS_WEIGHTS: Dict[str, float] = {
    "current_stability":    0.30,   # How secure you feel RIGHT NOW
    "future_outlook":       0.25,   # Where you think you're heading
    "purchasing_power":     0.20,   # Real-world spending strength
    "emergency_readiness":  0.15,   # Resilience & cushion
    "financial_agency":     0.10,   # Sense of control & intentionality
}

# Sanity check — never let this drift
assert abs(sum(FCS_WEIGHTS.values()) - 1.0) < 1e-9, "FCS_WEIGHTS must sum to 1.0"

# Human-readable dimension labels + coaching context
DIMENSION_META: Dict[str, Dict] = {
    "current_stability": {
        "label": "Stability",
        "weight": FCS_WEIGHTS["current_stability"],
        "description": "How secure you feel about your finances right now.",
        "tip": "Set up autopay for your biggest bills — knowing they're covered cuts daily stress immediately.",
        "icon": "🏛️",
    },
    "future_outlook": {
        "label": "Outlook",
        "weight": FCS_WEIGHTS["future_outlook"],
        "description": "How optimistic you are about where your finances are heading.",
        "tip": "Write down one financial goal you want to hit in 90 days. Clarity drives confidence.",
        "icon": "🔭",
    },
    "purchasing_power": {
        "label": "Purchasing Power",
        "weight": FCS_WEIGHTS["purchasing_power"],
        "description": "Whether your money feels like it goes as far as it used to.",
        "tip": "Track 3 grocery swaps this week. Small wins add up to big savings.",
        "icon": "💳",
    },
    "emergency_readiness": {
        "label": "Emergency Readiness",
        "weight": FCS_WEIGHTS["emergency_readiness"],
        "description": "How prepared you are to absorb a financial shock without going backward.",
        "tip": "Open a dedicated account and auto-transfer even $10/week. The habit matters more than the amount.",
        "icon": "🛡️",
    },
    "financial_agency": {
        "label": "Financial Agency",
        "weight": FCS_WEIGHTS["financial_agency"],
        "description": "Whether you feel empowered to improve your situation or stuck in place.",
        "tip": "List one skill you could develop in 6 months that would meaningfully increase your earning power.",
        "icon": "⚡",
    },
}


# ══════════════════════════════════════════════════════════════════
#  NORMALIZATION CONTRACT
#  Frontend always sends raw_value as integer 1..scale_max.
#  checkin_service normalizes via: (raw - 1) / (scale_max - 1)
#  This maps:  raw=1  → 0.0  (worst)
#              raw=max → 1.0  (best)
#
#  For yes_no_scale (scale_max = 5):
#    raw=1 = low_label answer (usually the NEGATIVE outcome)
#    raw=5 = high_label answer (usually the POSITIVE outcome)
#  Frontend maps the Yes/No tap to raw=1 or raw=5 accordingly.
# ══════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════
#  DAILY FCS QUESTIONS
# ══════════════════════════════════════════

DAILY_QUESTIONS: Dict[str, CheckInQuestion] = {

    # ── CURRENT STABILITY (30%) ─────────────────────────────────────────────
    # Goal: measure perceived security & stress today

    "CS-1": CheckInQuestion(
        "CS-1",
        "How confident are you that you can cover all your bills this month?",
        "current_stability", "1-5", 5,
        low_label="Not confident at all",
        high_label="Completely confident",
    ),
    "CS-2": CheckInQuestion(
        "CS-2",
        "If an unexpected $500 expense hit today, how stressed would that make you?",
        "current_stability", "1-10", 10,
        low_label="Not stressed at all",
        high_label="Completely overwhelmed",
        # NOTE: high raw = high stress = BAD — checkin_service handles inversion
        # via the `inverted` flag below
    ),
    "CS-3": CheckInQuestion(
        "CS-3",
        "How would you rate your overall financial stress level today?",
        "current_stability", "1-10", 10,
        low_label="No stress",
        high_label="Overwhelming stress",
        # Also inverted — high stress = low stability
    ),
    "CS-4": CheckInQuestion(
        "CS-4",
        "Did you have to choose between two necessary expenses this week?",
        "current_stability", "yes_no_scale", 5,
        low_label="Yes",     # Yes = bad → raw=1 → normalized=0.0
        high_label="No",     # No  = good → raw=5 → normalized=1.0
    ),
    "CS-5": CheckInQuestion(
        "CS-5",
        "How in control of your day-to-day finances do you feel right now?",
        "current_stability", "1-5", 5,
        low_label="Completely out of control",
        high_label="Fully in control",
    ),

    # ── FUTURE OUTLOOK (25%) ────────────────────────────────────────────────
    # Goal: capture forward-looking financial sentiment

    "FO-1": CheckInQuestion(
        "FO-1",
        "Looking 3 months ahead, do you think your financial situation will be better, the same, or worse?",
        "future_outlook", "1-5", 5,
        low_label="Much worse",
        high_label="Much better",
    ),
    "FO-2": CheckInQuestion(
        "FO-2",
        "How confident are you that your income will keep up with your expenses over the next 6 months?",
        "future_outlook", "1-10", 10,
        low_label="Not confident at all",
        high_label="Very confident",
    ),
    "FO-3": CheckInQuestion(
        "FO-3",
        "Do you feel like you're making progress toward your financial goals, or falling behind?",
        "future_outlook", "1-5", 5,
        low_label="Falling further behind",
        high_label="Strong progress",
    ),
    "FO-4": CheckInQuestion(
        "FO-4",
        "How optimistic are you about your personal financial trajectory right now?",
        "future_outlook", "1-10", 10,
        low_label="Very pessimistic",
        high_label="Very optimistic",
    ),

    # ── PURCHASING POWER (20%) ───────────────────────────────────────────────
    # Goal: measure real-world spending strength vs. cost pressures

    "PP-1": CheckInQuestion(
        "PP-1",
        "Compared to 6 months ago, does your paycheck feel like it goes further, the same, or not as far?",
        "purchasing_power", "1-5", 5,
        low_label="Much less far",
        high_label="Much further",
    ),
    "PP-2": CheckInQuestion(
        "PP-2",
        "Have you noticed prices going up on things you buy regularly?",
        "purchasing_power", "1-5", 5,
        low_label="Yes, significantly",
        high_label="No, prices feel stable",
    ),
    "PP-3": CheckInQuestion(
        "PP-3",
        "In the last month, have you switched to cheaper alternatives for things you normally buy?",
        "purchasing_power", "yes_no_scale", 5,
        low_label="Yes",    # Yes = stress signal → raw=1 → 0.0
        high_label="No",    # No  = stable → raw=5 → 1.0
    ),
    "PP-4": CheckInQuestion(
        "PP-4",
        "How fair do you feel your current cost of living is relative to your income?",
        "purchasing_power", "1-10", 10,
        low_label="Very unfair — barely covering basics",
        high_label="Very fair — income covers everything comfortably",
    ),

    # ── EMERGENCY READINESS (15%) ────────────────────────────────────────────
    # Goal: measure resilience, cushion depth, and shock-absorption capacity
    # Replaces: debt_pressure (DP-*)

    "ER-1": CheckInQuestion(
        "ER-1",
        "Do you currently have at least one month of living expenses saved as an emergency fund?",
        "emergency_readiness", "yes_no_scale", 5,
        low_label="No",    # No  = low readiness → raw=1 → 0.0
        high_label="Yes",  # Yes = good → raw=5 → 1.0
    ),
    "ER-2": CheckInQuestion(
        "ER-2",
        "If you lost your primary income today, how long could you cover your essential expenses?",
        "emergency_readiness", "1-5", 5,
        low_label="Less than a week",
        high_label="3 months or more",
    ),
    "ER-3": CheckInQuestion(
        "ER-3",
        "How prepared do you feel to handle a major unexpected expense right now?",
        "emergency_readiness", "1-10", 10,
        low_label="Completely unprepared",
        high_label="Fully prepared",
    ),
    "ER-4": CheckInQuestion(
        "ER-4",
        "Has an unexpected expense significantly disrupted your finances in the last 30 days?",
        "emergency_readiness", "yes_no_scale", 5,
        low_label="Yes — it set me back",  # Yes = negative → raw=1 → 0.0
        high_label="No — I absorbed it",   # No  = resilient → raw=5 → 1.0
    ),

    # ── FINANCIAL AGENCY (10%) ───────────────────────────────────────────────
    # Goal: measure sense of control, empowerment, and intentional action

    "FA-1": CheckInQuestion(
        "FA-1",
        "Do you believe you can meaningfully improve your financial situation in the next 6 months?",
        "financial_agency", "1-5", 5,
        low_label="No — completely stuck",
        high_label="Absolutely — already making moves",
    ),
    "FA-2": CheckInQuestion(
        "FA-2",
        "When you think about your finances, do you feel empowered or stuck?",
        "financial_agency", "1-10", 10,
        low_label="Completely stuck",
        high_label="Fully empowered",
    ),
    "FA-3": CheckInQuestion(
        "FA-3",
        "Compared to where you were financially 6 months ago, do you feel ahead or behind?",
        "financial_agency", "1-5", 5,
        low_label="Significantly behind",
        high_label="Significantly ahead",
    ),
    "FA-4": CheckInQuestion(
        "FA-4",
        "Have you taken at least one specific action in the last 7 days to improve your financial situation?",
        "financial_agency", "yes_no_scale", 5,
        low_label="No",    # No = low agency → raw=1 → 0.0
        high_label="Yes",  # Yes = active → raw=5 → 1.0
    ),
}


# ── INVERTED QUESTIONS ───────────────────────────────────────────────────────
# These questions are phrased so high raw value = WORSE outcome.
# checkin_service flips normalization: score = 1 - ((raw-1)/(scale_max-1))
INVERTED_QUESTION_IDS = {
    "CS-2",  # high stress score = bad
    "CS-3",  # high stress = bad
}


# ══════════════════════════════════════════
#  WEEKLY BEHAVIORAL CROSSOVER (BSI)
#  Runs on Sundays. Feeds BSI score only — not FCS dimensions.
# ══════════════════════════════════════════

WEEKLY_QUESTIONS: Dict[str, CheckInQuestion] = {
    "BX-1": CheckInQuestion(
        "BX-1",
        "This week, did you skip or downgrade something you normally buy to save money?",
        "category_downgrading", "yes_no_scale", 5,
        low_label="Yes", high_label="No", is_weekly=True,
    ),
    "BX-2": CheckInQuestion(
        "BX-2",
        "Did you use a credit card this week for something you would normally pay with cash or debit?",
        "credit_substitution", "yes_no_scale", 5,
        low_label="Yes", high_label="No", is_weekly=True,
    ),
    "BX-3": CheckInQuestion(
        "BX-3",
        "Did you cancel, pause, or skip any recurring subscription or service this week?",
        "subscription_churn", "yes_no_scale", 5,
        low_label="Yes", high_label="No", is_weekly=True,
    ),
    "BX-4": CheckInQuestion(
        "BX-4",
        "Did you delay a purchase you wanted because of financial uncertainty?",
        "delayed_purchasing", "yes_no_scale", 5,
        low_label="Yes", high_label="No", is_weekly=True,
    ),
    "BX-5": CheckInQuestion(
        "BX-5",
        "Are you holding onto more cash than usual because you're unsure about upcoming expenses?",
        "cash_hoarding", "yes_no_scale", 5,
        low_label="Yes", high_label="No", is_weekly=True,
    ),
}


# ══════════════════════════════════════════
#  DIMENSION ROTATION POOLS
# ══════════════════════════════════════════

DIMENSION_POOLS: Dict[str, List[str]] = {
    "current_stability":   ["CS-1", "CS-2", "CS-3", "CS-4", "CS-5"],
    "future_outlook":      ["FO-1", "FO-2", "FO-3", "FO-4"],
    "purchasing_power":    ["PP-1", "PP-2", "PP-3", "PP-4"],
    "emergency_readiness": ["ER-1", "ER-2", "ER-3", "ER-4"],
    "financial_agency":    ["FA-1", "FA-2", "FA-3", "FA-4"],
}


# ══════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════

def get_daily_questions(
    user_id, target_date: date = None, count: int = 5
) -> List[CheckInQuestion]:
    """
    Returns `count` questions — one per dimension by default (count=5).
    Deterministically seeded by user_id + date so the same user
    sees the same questions on the same day across sessions.
    """
    if target_date is None:
        target_date = date.today()

    seed = hash(f"{user_id}:{target_date.isoformat()}")
    rng = random.Random(seed)

    dimensions = list(DIMENSION_POOLS.keys())
    rng.shuffle(dimensions)

    selected = []
    for i in range(count):
        dim = dimensions[i % len(dimensions)]
        pool = DIMENSION_POOLS[dim]
        qid = rng.choice(pool)
        selected.append(DAILY_QUESTIONS[qid])

    return selected


def get_weekly_questions() -> List[CheckInQuestion]:
    return list(WEEKLY_QUESTIONS.values())


def is_weekly_checkin_day(target_date: date = None) -> bool:
    if target_date is None:
        target_date = date.today()
    return target_date.weekday() == 6  # Sunday


def get_todays_questions(user_id, target_date: date = None) -> dict:
    if target_date is None:
        target_date = date.today()

    daily = get_daily_questions(user_id, target_date)
    result = {
        "date": target_date.isoformat(),
        "daily_questions": daily,
        "weekly_questions": [],
        "is_weekly_day": False,
    }

    if is_weekly_checkin_day(target_date):
        result["weekly_questions"] = get_weekly_questions()
        result["is_weekly_day"] = True

    return result