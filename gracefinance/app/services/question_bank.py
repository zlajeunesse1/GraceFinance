"""
Question Bank — v4.0 (Institutional Behavioral Edition)
═══════════════════════════════════════════════════════════
PHILOSOPHY CHANGE FROM v3.0:

  v3 questions measured SENTIMENT: "How stressed are you?"
  v4 questions measure BEHAVIOR:   "Did you miss a payment?"

  This aligns with the GraceFinance institutional mandate:
  behavioral financial data, not opinion surveys.

  Every question now asks about a CONCRETE ACTION or
  OBSERVABLE FINANCIAL STATE — not a feeling.

PILLAR ALIGNMENT (unchanged):
  Stability         30%   Payment compliance, income predictability
  Outlook           25%   Saving actions, goal progress, debt trajectory
  Purchasing Power  20%   Consumption shifts, self-sufficiency
  Emergency Ready.  15%   Cushion building, liquidity, shock absorption
  Financial Agency  10%   Engagement, automation, proactive management

NORMALIZATION CONTRACT:
  Frontend sends raw_value as integer 1..scale_max.
  checkin_service normalizes: (raw - 1) / (scale_max - 1)
  Inverted questions flipped at normalization time.
"""

import random
from datetime import date
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class CheckInQuestion:
    question_id: str
    question_text: str
    dimension: str
    scale_type: str          # "1-5" | "1-10" | "yes_no_scale"
    scale_max: int
    low_label: str = "Low"
    high_label: str = "High"
    is_weekly: bool = False


# ══════════════════════════════════════════
#  LOCKED DIMENSION WEIGHTS  (must sum to 1.0)
# ══════════════════════════════════════════

FCS_WEIGHTS: Dict[str, float] = {
    "current_stability":    0.30,
    "future_outlook":       0.25,
    "purchasing_power":     0.20,
    "emergency_readiness":  0.15,
    "financial_agency":     0.10,
}

assert abs(sum(FCS_WEIGHTS.values()) - 1.0) < 1e-9, "FCS_WEIGHTS must sum to 1.0"

# Human-readable dimension labels + coaching context
DIMENSION_META: Dict[str, Dict] = {
    "current_stability": {
        "label": "Stability",
        "weight": FCS_WEIGHTS["current_stability"],
        "description": "Predictability and consistency of your financial obligations and income.",
        "tip": "Set up autopay for recurring bills — consistency is the foundation of stability.",
        "icon": "🏛️",
    },
    "future_outlook": {
        "label": "Outlook",
        "weight": FCS_WEIGHTS["future_outlook"],
        "description": "Your forward financial trajectory based on actions you're taking now.",
        "tip": "One saving or investing action per week shifts your trajectory meaningfully over 90 days.",
        "icon": "🔭",
    },
    "purchasing_power": {
        "label": "Purchasing Power",
        "weight": FCS_WEIGHTS["purchasing_power"],
        "description": "Your real-world spending capacity after obligations.",
        "tip": "Track whether you're downgrading purchases — it's an early signal of pressure.",
        "icon": "💳",
    },
    "emergency_readiness": {
        "label": "Emergency Readiness",
        "weight": FCS_WEIGHTS["emergency_readiness"],
        "description": "Your ability to absorb a financial shock without going backward.",
        "tip": "Auto-transfer even $10/week to a separate account. The habit matters more than the amount.",
        "icon": "🛡️",
    },
    "financial_agency": {
        "label": "Financial Agency",
        "weight": FCS_WEIGHTS["financial_agency"],
        "description": "Whether you're actively managing your finances or running on autopilot.",
        "tip": "Review your spending for 5 minutes this week. Awareness alone changes behavior.",
        "icon": "⚡",
    },
}


# ══════════════════════════════════════════
#  DAILY FCS QUESTIONS — BEHAVIORAL SIGNALS
# ══════════════════════════════════════════

DAILY_QUESTIONS: Dict[str, CheckInQuestion] = {

    # ── CURRENT STABILITY (30%) ─────────────────────────────────────────────
    # Behavioral signals: payment compliance, income predictability, account health

    "CS-1": CheckInQuestion(
        "CS-1",
        "Did you pay all your bills on time this week?",
        "current_stability", "yes_no_scale", 5,
        low_label="No — missed or late",
        high_label="Yes — all on time",
    ),
    "CS-2": CheckInQuestion(
        "CS-2",
        "Did you experience any unexpected expenses this week?",
        "current_stability", "yes_no_scale", 5,
        low_label="Yes — unexpected hit",
        high_label="No — everything expected",
        # INVERTED: Yes = disruption = bad
    ),
    "CS-3": CheckInQuestion(
        "CS-3",
        "Did your income arrive when expected this pay period?",
        "current_stability", "yes_no_scale", 5,
        low_label="No — delayed or short",
        high_label="Yes — on time and full",
    ),
    "CS-4": CheckInQuestion(
        "CS-4",
        "How many days this week did you check your bank balance or financial accounts?",
        "current_stability", "1-5", 5,
        low_label="0 days",
        high_label="5+ days",
    ),
    "CS-5": CheckInQuestion(
        "CS-5",
        "Did you overdraft, use overdraft protection, or bounce a payment this month?",
        "current_stability", "yes_no_scale", 5,
        low_label="Yes",
        high_label="No",
        # INVERTED: Yes = account stress = bad
    ),

    # ── FUTURE OUTLOOK (25%) ────────────────────────────────────────────────
    # Behavioral signals: saving actions, goal progress, debt trajectory

    "FO-1": CheckInQuestion(
        "FO-1",
        "Did you make a contribution to savings or investments this week?",
        "future_outlook", "yes_no_scale", 5,
        low_label="No",
        high_label="Yes",
    ),
    "FO-2": CheckInQuestion(
        "FO-2",
        "Did you set, review, or make progress on a financial goal this week?",
        "future_outlook", "yes_no_scale", 5,
        low_label="No",
        high_label="Yes",
    ),
    "FO-3": CheckInQuestion(
        "FO-3",
        "Did you take any action to increase your income this month? (side work, negotiation, upskilling)",
        "future_outlook", "yes_no_scale", 5,
        low_label="No",
        high_label="Yes",
    ),
    "FO-4": CheckInQuestion(
        "FO-4",
        "Compared to 30 days ago, is your total debt balance lower, the same, or higher?",
        "future_outlook", "1-5", 5,
        low_label="Much higher",
        high_label="Much lower",
    ),

    # ── PURCHASING POWER (20%) ───────────────────────────────────────────────
    # Behavioral signals: consumption shifts, spending capacity, self-sufficiency

    "PP-1": CheckInQuestion(
        "PP-1",
        "Did you have to skip or reduce a regular purchase this week to save money?",
        "purchasing_power", "yes_no_scale", 5,
        low_label="Yes — had to cut back",
        high_label="No — bought what I needed",
        # INVERTED: Yes = pressure signal
    ),
    "PP-2": CheckInQuestion(
        "PP-2",
        "Did you switch to a cheaper brand or alternative for something you regularly buy?",
        "purchasing_power", "yes_no_scale", 5,
        low_label="Yes — downgraded",
        high_label="No — same as usual",
        # INVERTED: Yes = purchasing pressure
    ),
    "PP-3": CheckInQuestion(
        "PP-3",
        "Were you able to cover all essential expenses this week without borrowing?",
        "purchasing_power", "yes_no_scale", 5,
        low_label="No — had to borrow or use credit",
        high_label="Yes — covered everything",
    ),
    "PP-4": CheckInQuestion(
        "PP-4",
        "Did you delay any planned purchase because of financial uncertainty?",
        "purchasing_power", "yes_no_scale", 5,
        low_label="Yes — delayed",
        high_label="No — on track",
        # INVERTED: Yes = deferral signal
    ),

    # ── EMERGENCY READINESS (15%) ────────────────────────────────────────────
    # Behavioral signals: cushion building, liquidity, shock absorption

    "ER-1": CheckInQuestion(
        "ER-1",
        "Did you add any money to an emergency fund or savings account this week?",
        "emergency_readiness", "yes_no_scale", 5,
        low_label="No",
        high_label="Yes",
    ),
    "ER-2": CheckInQuestion(
        "ER-2",
        "Could you cover a $500 unexpected expense today without borrowing?",
        "emergency_readiness", "yes_no_scale", 5,
        low_label="No",
        high_label="Yes",
    ),
    "ER-3": CheckInQuestion(
        "ER-3",
        "How many months of essential expenses do you currently have saved?",
        "emergency_readiness", "1-5", 5,
        low_label="Less than 1 week",
        high_label="3+ months",
    ),
    "ER-4": CheckInQuestion(
        "ER-4",
        "Did an unexpected expense significantly disrupt your budget this month?",
        "emergency_readiness", "yes_no_scale", 5,
        low_label="Yes — it set me back",
        high_label="No — absorbed it fine",
        # INVERTED: Yes = low resilience
    ),

    # ── FINANCIAL AGENCY (10%) ───────────────────────────────────────────────
    # Behavioral signals: engagement, automation, proactive management

    "FA-1": CheckInQuestion(
        "FA-1",
        "Did you review your budget, spending, or financial plan this week?",
        "financial_agency", "yes_no_scale", 5,
        low_label="No",
        high_label="Yes",
    ),
    "FA-2": CheckInQuestion(
        "FA-2",
        "Did you take a specific action to improve your financial situation this week?",
        "financial_agency", "yes_no_scale", 5,
        low_label="No",
        high_label="Yes",
    ),
    "FA-3": CheckInQuestion(
        "FA-3",
        "Did you research a financial product, investment, or money strategy this week?",
        "financial_agency", "yes_no_scale", 5,
        low_label="No",
        high_label="Yes",
    ),
    "FA-4": CheckInQuestion(
        "FA-4",
        "Did you automate any bill payment, savings transfer, or investment contribution this month?",
        "financial_agency", "yes_no_scale", 5,
        low_label="No",
        high_label="Yes",
    ),
}


# ── INVERTED QUESTIONS ───────────────────────────────────────────────────────
# These questions are phrased so answering "Yes" = NEGATIVE financial signal.
# checkin_service flips normalization: score = 1 - ((raw-1)/(scale_max-1))

INVERTED_QUESTION_IDS = {
    "CS-2",  # unexpected expenses = bad
    "CS-5",  # overdraft = bad
    "PP-1",  # skipping purchases = pressure
    "PP-2",  # downgrading = pressure
    "PP-4",  # delaying purchases = pressure
    "ER-4",  # disrupted budget = bad
}


# ══════════════════════════════════════════
#  WEEKLY BEHAVIORAL CROSSOVER (BSI)
#  Runs on Sundays. Feeds BSI score only — not FCS.
# ══════════════════════════════════════════

WEEKLY_QUESTIONS: Dict[str, CheckInQuestion] = {
    "BX-1": CheckInQuestion(
        "BX-1",
        "Did you skip or downgrade a regular purchase this week to save money?",
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
    Returns `count` questions — one per dimension by default.
    Deterministically seeded by user_id + date for consistency.
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