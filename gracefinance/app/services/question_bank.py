"""
Question Bank — v2.1 (Anchor Labels)
═════════════════════════════════════
CHANGES:
  - Added low_label and high_label to CheckInQuestion
  - Every question now has context-specific anchor text
  - yes_no_scale questions get "Yes" / "No" anchors
  - Frontend displays these instead of generic "Low" / "High"

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
    scale_type: str
    scale_max: int
    low_label: str = "Low"
    high_label: str = "High"
    is_weekly: bool = False


# ══════════════════════════════════════════
#  FCS WEIGHTS
# ══════════════════════════════════════════

FCS_WEIGHTS = {
    "current_stability":  0.30,
    "future_outlook":     0.25,
    "purchasing_power":   0.20,
    "debt_pressure":      0.15,
    "financial_agency":   0.10,
}


# ══════════════════════════════════════════
#  DIMENSION METADATA
# ══════════════════════════════════════════

DIMENSION_META = {
    "current_stability": {
        "label": "Current Stability",
        "weight": FCS_WEIGHTS["current_stability"],
        "tip": "Build a simple buffer — even $50 set aside reduces daily financial stress.",
        "description": "How secure you feel about your finances right now.",
    },
    "future_outlook": {
        "label": "Future Outlook",
        "weight": FCS_WEIGHTS["future_outlook"],
        "tip": "Write down one financial goal you want to hit in 90 days. Clarity drives confidence.",
        "description": "How optimistic you are about where your finances are heading.",
    },
    "purchasing_power": {
        "label": "Purchasing Power",
        "weight": FCS_WEIGHTS["purchasing_power"],
        "tip": "Track 3 grocery swaps this week. Small wins add up to big savings.",
        "description": "Whether your money feels like it goes as far as it used to.",
    },
    "debt_pressure": {
        "label": "Debt Pressure",
        "weight": FCS_WEIGHTS["debt_pressure"],
        "tip": "List every debt with its balance and rate. Visibility is the first step to control.",
        "description": "How much your debt is weighing on your daily financial decisions.",
    },
    "financial_agency": {
        "label": "Financial Agency",
        "weight": FCS_WEIGHTS["financial_agency"],
        "tip": "Take one small financial action today — even checking your balance counts as agency.",
        "description": "Whether you feel empowered to improve your situation or stuck in place.",
    },
}


# ══════════════════════════════════════════
#  DAILY FCS QUESTIONS
# ══════════════════════════════════════════

DAILY_QUESTIONS: Dict[str, CheckInQuestion] = {

    # ── Current Stability (30%) ──

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
        low_label="Not stressed",
        high_label="Extremely stressed",
    ),
    "CS-3": CheckInQuestion(
        "CS-3",
        "How would you rate your financial stress level today?",
        "current_stability", "1-10", 10,
        low_label="No stress",
        high_label="Overwhelming",
    ),
    "CS-4": CheckInQuestion(
        "CS-4",
        "Did you have to choose between two necessary expenses this week?",
        "current_stability", "yes_no_scale", 5,
        low_label="Yes",
        high_label="No",
    ),
    "CS-5": CheckInQuestion(
        "CS-5",
        "How in control of your finances do you feel today?",
        "current_stability", "1-5", 5,
        low_label="Not in control",
        high_label="Fully in control",
    ),

    # ── Future Outlook (25%) ──

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
        low_label="Not confident",
        high_label="Very confident",
    ),
    "FO-3": CheckInQuestion(
        "FO-3",
        "Do you feel like you're making progress toward your financial goals, or falling behind?",
        "future_outlook", "1-5", 5,
        low_label="Falling behind",
        high_label="Strong progress",
    ),
    "FO-4": CheckInQuestion(
        "FO-4",
        "How optimistic are you about the economy right now?",
        "future_outlook", "1-10", 10,
        low_label="Very pessimistic",
        high_label="Very optimistic",
    ),

    # ── Purchasing Power (20%) ──

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
        low_label="Yes, a lot",
        high_label="No, prices are stable",
    ),
    "PP-3": CheckInQuestion(
        "PP-3",
        "In the last month, have you switched to cheaper alternatives for things you normally buy?",
        "purchasing_power", "yes_no_scale", 5,
        low_label="Yes",
        high_label="No",
    ),
    "PP-4": CheckInQuestion(
        "PP-4",
        "How fair do you feel your current cost of living is relative to your income?",
        "purchasing_power", "1-10", 10,
        low_label="Very unfair",
        high_label="Very fair",
    ),

    # ── Debt Pressure (15%) ──

    "DP-1": CheckInQuestion(
        "DP-1",
        "How manageable do your monthly debt payments feel right now?",
        "debt_pressure", "1-5", 5,
        low_label="Suffocating",
        high_label="Very manageable",
    ),
    "DP-2": CheckInQuestion(
        "DP-2",
        "Over the last 30 days, have your total credit card balances gone up, stayed the same, or gone down?",
        "debt_pressure", "1-5", 5,
        low_label="Up significantly",
        high_label="Down significantly",
    ),
    "DP-3": CheckInQuestion(
        "DP-3",
        "Do you feel like you're making progress paying down debt, or just treading water?",
        "debt_pressure", "1-10", 10,
        low_label="Sinking deeper",
        high_label="Crushing it",
    ),
    "DP-4": CheckInQuestion(
        "DP-4",
        "In the last month, have you taken on any new debt (credit card, loan, BNPL) to cover regular expenses?",
        "debt_pressure", "yes_no_scale", 5,
        low_label="Yes",
        high_label="No",
    ),

    # ── Financial Agency (10%) ──

    "FA-1": CheckInQuestion(
        "FA-1",
        "Do you believe you can meaningfully improve your financial situation in the next 6 months?",
        "financial_agency", "1-5", 5,
        low_label="No, completely stuck",
        high_label="Absolutely, already on it",
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
        "Compared to other people your age, do you feel ahead, on track, or behind financially?",
        "financial_agency", "1-5", 5,
        low_label="Way behind",
        high_label="Way ahead",
    ),
    "FA-4": CheckInQuestion(
        "FA-4",
        "Have you taken a specific action in the last 7 days to improve your financial situation?",
        "financial_agency", "yes_no_scale", 5,
        low_label="No",
        high_label="Yes",
    ),
}


# ── Weekly Behavioral Crossover (BSI, Sundays) ──

WEEKLY_QUESTIONS: Dict[str, CheckInQuestion] = {
    "BX-1": CheckInQuestion(
        "BX-1",
        "This week, did you skip or downgrade something you normally buy to save money?",
        "category_downgrading", "yes_no_scale", 5,
        low_label="Yes",
        high_label="No",
        is_weekly=True,
    ),
    "BX-2": CheckInQuestion(
        "BX-2",
        "Did you use a credit card this week for something you would normally pay with cash or debit?",
        "credit_substitution", "yes_no_scale", 5,
        low_label="Yes",
        high_label="No",
        is_weekly=True,
    ),
    "BX-3": CheckInQuestion(
        "BX-3",
        "Did you cancel, pause, or skip any recurring subscription or service this week?",
        "subscription_churn", "yes_no_scale", 5,
        low_label="Yes",
        high_label="No",
        is_weekly=True,
    ),
    "BX-4": CheckInQuestion(
        "BX-4",
        "Did you delay a purchase you wanted because of financial uncertainty?",
        "delayed_purchasing", "yes_no_scale", 5,
        low_label="Yes",
        high_label="No",
        is_weekly=True,
    ),
    "BX-5": CheckInQuestion(
        "BX-5",
        "Are you holding onto more cash than usual because you're unsure about upcoming expenses?",
        "cash_hoarding", "yes_no_scale", 5,
        low_label="Yes",
        high_label="No",
        is_weekly=True,
    ),
}


# ── Dimension rotation map ──

DIMENSION_POOLS = {
    "current_stability": ["CS-1", "CS-2", "CS-3", "CS-4", "CS-5"],
    "future_outlook": ["FO-1", "FO-2", "FO-3", "FO-4"],
    "purchasing_power": ["PP-1", "PP-2", "PP-3", "PP-4"],
    "debt_pressure": ["DP-1", "DP-2", "DP-3", "DP-4"],
    "financial_agency": ["FA-1", "FA-2", "FA-3", "FA-4"],
}


# ══════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════

def get_daily_questions(user_id: int, target_date: date = None, count: int = 4) -> List[CheckInQuestion]:
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
    return target_date.weekday() == 6


def get_todays_questions(user_id: int, target_date: date = None) -> dict:
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