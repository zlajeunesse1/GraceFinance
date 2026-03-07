"""
Question Bank — v5.0 (Predictive Behavioral Profiling)
═══════════════════════════════════════════════════════════
PHILOSOPHY:

  Every question captures a MEASURABLE FINANCIAL STATE.
  Over 30/60/90 days, responses build a behavioral profile
  that can power predictive modeling.

  The goal is NOT "how do you feel?" — it's "what is your
  financial reality right now?"

  Each answer plots a data point. Patterns across data points
  become predictive signals:
    - Stability dropping 3 days straight → payment risk
    - Agency rising while Outlook flat → behavior shift incoming
    - Emergency Readiness below 30 for 14 days → shock vulnerability

DESIGN PRINCIPLES:
  1. SCALED questions dominate (1-5, 1-10) — richer signal than yes/no
  2. Yes/No used ONLY for binary financial events (did it happen or not)
  3. ZERO overlap between daily FCS questions and weekly BSI questions
  4. Every question maps to a concrete, observable financial state
  5. Questions are worded for clarity — no ambiguity, no double-barrels

PILLAR WEIGHTS (locked):
  Stability         30%
  Outlook           25%
  Purchasing Power  20%
  Emergency Ready.  15%
  Financial Agency  10%

NORMALIZATION:
  Frontend sends raw_value as integer 1..scale_max.
  checkin_service normalizes: (raw - 1) / (scale_max - 1)
  Inverted questions flipped at normalization time.
"""

import random
from datetime import date, datetime, timezone
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

DIMENSION_META: Dict[str, Dict] = {
    "current_stability": {
        "label": "Stability",
        "weight": FCS_WEIGHTS["current_stability"],
        "description": "Predictability and consistency of your financial obligations and income.",
        "tip": "Set up autopay for recurring bills — consistency is the foundation of stability.",
    },
    "future_outlook": {
        "label": "Outlook",
        "weight": FCS_WEIGHTS["future_outlook"],
        "description": "Your forward financial trajectory based on actions you're taking now.",
        "tip": "One saving or investing action per week shifts your trajectory meaningfully over 90 days.",
    },
    "purchasing_power": {
        "label": "Purchasing Power",
        "weight": FCS_WEIGHTS["purchasing_power"],
        "description": "Your real-world spending capacity after obligations.",
        "tip": "Track whether you're downgrading purchases — it's an early signal of pressure.",
    },
    "emergency_readiness": {
        "label": "Emergency Readiness",
        "weight": FCS_WEIGHTS["emergency_readiness"],
        "description": "Your ability to absorb a financial shock without going backward.",
        "tip": "Auto-transfer even $10/week to a separate account. The habit matters more than the amount.",
    },
    "financial_agency": {
        "label": "Financial Agency",
        "weight": FCS_WEIGHTS["financial_agency"],
        "description": "Whether you're actively managing your finances or running on autopilot.",
        "tip": "Review your spending for 5 minutes this week. Awareness alone changes behavior.",
    },
}


# ══════════════════════════════════════════════════════════════
#  DAILY FCS QUESTIONS — BEHAVIORAL PROFILE BUILDERS
# ══════════════════════════════════════════════════════════════

DAILY_QUESTIONS: Dict[str, CheckInQuestion] = {

    # ── CURRENT STABILITY (30%) ─────────────────────────────────────────────

    "CS-1": CheckInQuestion(
        "CS-1",
        "How many of your bills and financial obligations are you confident you can cover this month?",
        "current_stability", "1-5", 5,
        low_label="Almost none",
        high_label="All of them",
    ),
    "CS-2": CheckInQuestion(
        "CS-2",
        "How predictable was your income over the last 30 days?",
        "current_stability", "1-5", 5,
        low_label="Highly unpredictable",
        high_label="Completely predictable",
    ),
    "CS-3": CheckInQuestion(
        "CS-3",
        "How often did unexpected expenses disrupt your budget this month?",
        "current_stability", "1-5", 5,
        low_label="Constantly",
        high_label="Never",
    ),
    "CS-4": CheckInQuestion(
        "CS-4",
        "How would you rate the overall order of your finances right now?",
        "current_stability", "1-10", 10,
        low_label="Complete chaos",
        high_label="Everything organized and tracked",
    ),
    "CS-5": CheckInQuestion(
        "CS-5",
        "Did you miss, pay late, or skip any bill or payment this month?",
        "current_stability", "yes_no_scale", 5,
        low_label="Yes — missed or late",
        high_label="No — all on time",
    ),
    "CS-6": CheckInQuestion(
        "CS-6",
        "How many days this week did you have a clear picture of your available cash?",
        "current_stability", "1-5", 5,
        low_label="0 days — no idea",
        high_label="Every day",
    ),

    # ── FUTURE OUTLOOK (25%) ────────────────────────────────────────────────

    "FO-1": CheckInQuestion(
        "FO-1",
        "In the last 7 days, how much progress did you make toward a financial goal?",
        "future_outlook", "1-5", 5,
        low_label="No progress at all",
        high_label="Significant progress",
    ),
    "FO-2": CheckInQuestion(
        "FO-2",
        "Compared to 30 days ago, how would you describe your total debt?",
        "future_outlook", "1-5", 5,
        low_label="Much higher",
        high_label="Much lower",
    ),
    "FO-3": CheckInQuestion(
        "FO-3",
        "How many times this month did you put money into savings or investments?",
        "future_outlook", "1-5", 5,
        low_label="Zero times",
        high_label="4 or more times",
    ),
    "FO-4": CheckInQuestion(
        "FO-4",
        "How confident are you that your income will grow over the next 6 months?",
        "future_outlook", "1-10", 10,
        low_label="No chance of growth",
        high_label="Very confident — already taking action",
    ),
    "FO-5": CheckInQuestion(
        "FO-5",
        "Did you take any specific action this week to increase your future earning power?",
        "future_outlook", "yes_no_scale", 5,
        low_label="No",
        high_label="Yes",
    ),

    # ── PURCHASING POWER (20%) ───────────────────────────────────────────────

    "PP-1": CheckInQuestion(
        "PP-1",
        "After covering all your essential expenses, how much financial breathing room do you have right now?",
        "purchasing_power", "1-10", 10,
        low_label="Zero — stretched to the limit",
        high_label="Plenty of room",
    ),
    "PP-2": CheckInQuestion(
        "PP-2",
        "How many times this week did you have to choose a cheaper alternative for something you normally buy?",
        "purchasing_power", "1-5", 5,
        low_label="5+ times — constantly downgrading",
        high_label="Never — buying what I need",
    ),
    "PP-3": CheckInQuestion(
        "PP-3",
        "Were you able to cover all essential expenses this week without using credit or borrowing?",
        "purchasing_power", "yes_no_scale", 5,
        low_label="No — had to borrow or use credit",
        high_label="Yes — covered everything",
    ),
    "PP-4": CheckInQuestion(
        "PP-4",
        "How would you rate your current cost of living relative to your income?",
        "purchasing_power", "1-10", 10,
        low_label="Income barely covers basics",
        high_label="Income comfortably covers everything",
    ),
    "PP-5": CheckInQuestion(
        "PP-5",
        "How many non-essential purchases did you make this week that you felt good about?",
        "purchasing_power", "1-5", 5,
        low_label="Zero — can't afford any",
        high_label="Several — without financial stress",
    ),

    # ── EMERGENCY READINESS (15%) ────────────────────────────────────────────

    "ER-1": CheckInQuestion(
        "ER-1",
        "If you lost your primary income today, how long could you cover essential expenses?",
        "emergency_readiness", "1-5", 5,
        low_label="Less than 1 week",
        high_label="3+ months",
    ),
    "ER-2": CheckInQuestion(
        "ER-2",
        "How prepared are you to handle a $500 unexpected expense right now without borrowing?",
        "emergency_readiness", "1-10", 10,
        low_label="Completely unprepared — would need to borrow",
        high_label="Fully prepared — cash available",
    ),
    "ER-3": CheckInQuestion(
        "ER-3",
        "Did you add any amount to an emergency fund or savings buffer this week?",
        "emergency_readiness", "yes_no_scale", 5,
        low_label="No",
        high_label="Yes",
    ),
    "ER-4": CheckInQuestion(
        "ER-4",
        "How would you rate the overall strength of your financial safety net right now?",
        "emergency_readiness", "1-10", 10,
        low_label="No safety net at all",
        high_label="Strong — could handle multiple shocks",
    ),
    "ER-5": CheckInQuestion(
        "ER-5",
        "In the last 30 days, did an unexpected expense significantly set you back financially?",
        "emergency_readiness", "yes_no_scale", 5,
        low_label="Yes — it set me back",
        high_label="No — handled it or nothing came up",
    ),

    # ── FINANCIAL AGENCY (10%) ───────────────────────────────────────────────

    "FA-1": CheckInQuestion(
        "FA-1",
        "How many minutes this week did you spend actively managing your finances? (reviewing, planning, optimizing)",
        "financial_agency", "1-5", 5,
        low_label="0 minutes",
        high_label="30+ minutes",
    ),
    "FA-2": CheckInQuestion(
        "FA-2",
        "How many of your recurring bills and savings are automated right now?",
        "financial_agency", "1-5", 5,
        low_label="None — all manual",
        high_label="All automated",
    ),
    "FA-3": CheckInQuestion(
        "FA-3",
        "Did you take at least one deliberate action this week to improve your financial position?",
        "financial_agency", "yes_no_scale", 5,
        low_label="No",
        high_label="Yes",
    ),
    "FA-4": CheckInQuestion(
        "FA-4",
        "How clear is your financial plan for the next 90 days?",
        "financial_agency", "1-10", 10,
        low_label="No plan at all",
        high_label="Detailed plan with specific targets",
    ),
    "FA-5": CheckInQuestion(
        "FA-5",
        "Did you learn something new about personal finance, investing, or money management this week?",
        "financial_agency", "yes_no_scale", 5,
        low_label="No",
        high_label="Yes",
    ),
}


# ── INVERTED QUESTIONS ───────────────────────────────────────────────────────
INVERTED_QUESTION_IDS = set()


# ══════════════════════════════════════════
#  WEEKLY BEHAVIORAL CROSSOVER (BSI)
# ══════════════════════════════════════════

WEEKLY_QUESTIONS: Dict[str, CheckInQuestion] = {
    "BX-1": CheckInQuestion(
        "BX-1",
        "Did you cancel or pause any recurring subscription this week?",
        "subscription_churn", "yes_no_scale", 5,
        low_label="Yes — cut something", high_label="No — kept everything",
        is_weekly=True,
    ),
    "BX-2": CheckInQuestion(
        "BX-2",
        "Did you use a credit card this week for something you would normally pay with cash or debit?",
        "credit_substitution", "yes_no_scale", 5,
        low_label="Yes — shifted to credit", high_label="No — paid normally",
        is_weekly=True,
    ),
    "BX-3": CheckInQuestion(
        "BX-3",
        "Did you put off a planned purchase this week because you weren't sure you could afford it?",
        "deferred_spending", "yes_no_scale", 5,
        low_label="Yes — delayed it", high_label="No — bought as planned",
        is_weekly=True,
    ),
    "BX-4": CheckInQuestion(
        "BX-4",
        "Did you take on any new debt this week? (credit card balance, loan, buy-now-pay-later)",
        "debt_accumulation", "yes_no_scale", 5,
        low_label="Yes — added debt", high_label="No — no new debt",
        is_weekly=True,
    ),
    "BX-5": CheckInQuestion(
        "BX-5",
        "Did you actively avoid checking your bank balance or financial accounts this week?",
        "financial_avoidance", "yes_no_scale", 5,
        low_label="Yes — avoided looking", high_label="No — stayed engaged",
        is_weekly=True,
    ),
}


# ══════════════════════════════════════════
#  DIMENSION ROTATION POOLS
# ══════════════════════════════════════════

DIMENSION_POOLS: Dict[str, List[str]] = {
    "current_stability":   ["CS-1", "CS-2", "CS-3", "CS-4", "CS-5", "CS-6"],
    "future_outlook":      ["FO-1", "FO-2", "FO-3", "FO-4", "FO-5"],
    "purchasing_power":    ["PP-1", "PP-2", "PP-3", "PP-4", "PP-5"],
    "emergency_readiness": ["ER-1", "ER-2", "ER-3", "ER-4", "ER-5"],
    "financial_agency":    ["FA-1", "FA-2", "FA-3", "FA-4", "FA-5"],
}


# ══════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════

def _utc_today() -> date:
    """Single source of truth for 'today' — always UTC."""
    return datetime.now(timezone.utc).date()


def get_daily_questions(
    user_id, target_date: date = None, count: int = 5
) -> List[CheckInQuestion]:
    """
    Returns `count` questions — one per dimension by default.
    Deterministically seeded by user_id + date so the same user
    sees the same questions on the same day across sessions,
    but different questions each day.
    """
    if target_date is None:
        target_date = _utc_today()

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
        target_date = _utc_today()
    return target_date.weekday() == 6  # Sunday


def get_todays_questions(user_id, target_date: date = None) -> dict:
    if target_date is None:
        target_date = _utc_today()

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