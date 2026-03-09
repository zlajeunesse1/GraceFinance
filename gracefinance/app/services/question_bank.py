"""
Question Bank — v6.3
═════════════════════
CHANGES FROM v6.2:
  - FIX #1 (CRITICAL): Replaced Python's hash() with hashlib.sha256 for
    question randomization seed. hash() uses PYTHONHASHSEED (randomized by
    default since Python 3.3), so a container restart mid-day would change
    which questions users see. sha256 is deterministic across restarts.
  - Added explanatory comment on INVERTED_QUESTION_IDS empty set.
"""

import random
import hashlib
from datetime import date, datetime, timezone
from dataclasses import dataclass
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


FCS_WEIGHTS: Dict[str, float] = {
    "current_stability":    0.30,
    "future_outlook":       0.25,
    "purchasing_power":     0.20,
    "emergency_readiness":  0.15,
    "financial_agency":     0.10,
}

assert abs(sum(FCS_WEIGHTS.values()) - 1.0) < 1e-9

DIMENSION_META: Dict[str, Dict] = {
    "current_stability": {
        "label": "Stability",
        "weight": FCS_WEIGHTS["current_stability"],
        "description": "Predictability and consistency of your financial obligations and income.",
        "tip": "Set up autopay for recurring bills. Consistency is the foundation of stability.",
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
        "tip": "Track whether you're downgrading purchases. It's an early signal of pressure.",
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
#  DAILY FCS QUESTIONS (62 core + 10 consistency traps = 72)
# ══════════════════════════════════════════════════════════════

DAILY_QUESTIONS: Dict[str, CheckInQuestion] = {

    # ── CURRENT STABILITY (12 + 2 traps) ─────────────────────────────────

    "CS-1": CheckInQuestion("CS-1",
        "How many of your bills and financial obligations are you confident you can cover this month?",
        "current_stability", "1-5", 5,
        low_label="Almost none", high_label="All of them"),
    "CS-2": CheckInQuestion("CS-2",
        "How predictable was your income over the last 30 days?",
        "current_stability", "1-5", 5,
        low_label="Highly unpredictable", high_label="Completely predictable"),
    "CS-3": CheckInQuestion("CS-3",
        "How often did unexpected expenses disrupt your budget this month?",
        "current_stability", "1-5", 5,
        low_label="Constantly", high_label="Never"),
    "CS-4": CheckInQuestion("CS-4",
        "How would you rate the overall order of your finances right now?",
        "current_stability", "1-10", 10,
        low_label="Complete chaos", high_label="Everything organized and tracked"),
    "CS-5": CheckInQuestion("CS-5",
        "Did you miss, pay late, or skip any bill or payment this month?",
        "current_stability", "yes_no_scale", 5,
        low_label="Yes, missed or late", high_label="No, all on time"),
    "CS-6": CheckInQuestion("CS-6",
        "How many days this week did you have a clear picture of your available cash?",
        "current_stability", "1-5", 5,
        low_label="0 days, no idea", high_label="Every day"),
    "CS-7": CheckInQuestion("CS-7",
        "How close are you to running out of money before your next paycheck or income?",
        "current_stability", "1-5", 5,
        low_label="Already ran out", high_label="Plenty of buffer remaining"),
    "CS-8": CheckInQuestion("CS-8",
        "How many sources of income do you currently have?",
        "current_stability", "1-5", 5,
        low_label="Zero or unstable", high_label="3 or more reliable sources"),
    "CS-9": CheckInQuestion("CS-9",
        "How confident are you that your housing payment is secure for the next 3 months?",
        "current_stability", "1-10", 10,
        low_label="Not confident at all", high_label="Completely secure"),
    "CS-10": CheckInQuestion("CS-10",
        "Did any recurring payment fail or bounce this month?",
        "current_stability", "yes_no_scale", 5,
        low_label="Yes, at least one failed", high_label="No, all went through"),
    "CS-11": CheckInQuestion("CS-11",
        "How often this week did you check your bank balance or financial accounts?",
        "current_stability", "1-5", 5,
        low_label="Never", high_label="Daily"),
    "CS-12": CheckInQuestion("CS-12",
        "How well do you know the exact amount of your fixed monthly expenses?",
        "current_stability", "1-10", 10,
        low_label="No idea", high_label="Know every dollar"),
    "CT-CS-1": CheckInQuestion("CT-CS-1",
        "If all your bills were due tomorrow, could you pay every one of them?",
        "current_stability", "1-5", 5,
        low_label="Definitely not", high_label="Yes, all of them"),
    "CT-CS-2": CheckInQuestion("CT-CS-2",
        "How much financial surprise have you dealt with this month?",
        "current_stability", "1-5", 5,
        low_label="Constant surprises", high_label="Nothing unexpected"),

    # ── FUTURE OUTLOOK (12 + 2 traps) ────────────────────────────────────

    "FO-1": CheckInQuestion("FO-1",
        "In the last 7 days, how much progress did you make toward a financial goal?",
        "future_outlook", "1-5", 5,
        low_label="No progress at all", high_label="Significant progress"),
    "FO-2": CheckInQuestion("FO-2",
        "Compared to 30 days ago, how would you describe your total debt?",
        "future_outlook", "1-5", 5,
        low_label="Much higher", high_label="Much lower"),
    "FO-3": CheckInQuestion("FO-3",
        "How many times this month did you put money into savings or investments?",
        "future_outlook", "1-5", 5,
        low_label="Zero times", high_label="4 or more times"),
    "FO-4": CheckInQuestion("FO-4",
        "How confident are you that your income will grow over the next 6 months?",
        "future_outlook", "1-10", 10,
        low_label="No chance of growth", high_label="Very confident, already taking action"),
    "FO-5": CheckInQuestion("FO-5",
        "Did you take any specific action this week to increase your future earning power?",
        "future_outlook", "yes_no_scale", 5,
        low_label="No", high_label="Yes"),
    "FO-6": CheckInQuestion("FO-6",
        "How many financial goals do you currently have written down or tracked?",
        "future_outlook", "1-5", 5,
        low_label="Zero", high_label="3 or more"),
    "FO-7": CheckInQuestion("FO-7",
        "How likely is it that your net worth will be higher 12 months from now?",
        "future_outlook", "1-10", 10,
        low_label="Very unlikely", high_label="Almost certain"),
    "FO-8": CheckInQuestion("FO-8",
        "Did you contribute to a retirement or investment account this month?",
        "future_outlook", "yes_no_scale", 5,
        low_label="No", high_label="Yes"),
    "FO-9": CheckInQuestion("FO-9",
        "How would you rate your progress on your most important financial goal this month?",
        "future_outlook", "1-10", 10,
        low_label="No progress or went backward", high_label="Major progress"),
    "FO-10": CheckInQuestion("FO-10",
        "Are you currently developing any skills that could increase your income?",
        "future_outlook", "yes_no_scale", 5,
        low_label="No", high_label="Yes"),
    "FO-11": CheckInQuestion("FO-11",
        "How would you rate your confidence in your career trajectory right now?",
        "future_outlook", "1-5", 5,
        low_label="Stagnant or declining", high_label="Growing rapidly"),
    "FO-12": CheckInQuestion("FO-12",
        "Compared to this time last year, is your financial situation better, the same, or worse?",
        "future_outlook", "1-5", 5,
        low_label="Much worse", high_label="Much better"),
    "CT-FO-1": CheckInQuestion("CT-FO-1",
        "Are you closer to your biggest financial goal than you were last month?",
        "future_outlook", "1-5", 5,
        low_label="Further away", high_label="Much closer"),
    "CT-FO-2": CheckInQuestion("CT-FO-2",
        "How would you describe your debt direction over the past month?",
        "future_outlook", "1-5", 5,
        low_label="Growing fast", high_label="Shrinking steadily"),

    # ── PURCHASING POWER (12 + 2 traps) ──────────────────────────────────

    "PP-1": CheckInQuestion("PP-1",
        "After covering all your essential expenses, how much financial breathing room do you have right now?",
        "purchasing_power", "1-10", 10,
        low_label="Zero, stretched to the limit", high_label="Plenty of room"),
    "PP-2": CheckInQuestion("PP-2",
        "How many times this week did you have to choose a cheaper alternative for something you normally buy?",
        "purchasing_power", "1-5", 5,
        low_label="5+ times, constantly downgrading", high_label="Never, buying what I need"),
    "PP-3": CheckInQuestion("PP-3",
        "Were you able to cover all essential expenses this week without using credit or borrowing?",
        "purchasing_power", "yes_no_scale", 5,
        low_label="No, had to borrow or use credit", high_label="Yes, covered everything"),
    "PP-4": CheckInQuestion("PP-4",
        "How would you rate your current cost of living relative to your income?",
        "purchasing_power", "1-10", 10,
        low_label="Income barely covers basics", high_label="Income comfortably covers everything"),
    "PP-5": CheckInQuestion("PP-5",
        "How many non-essential purchases did you make this week that you felt good about?",
        "purchasing_power", "1-5", 5,
        low_label="Zero, can't afford any", high_label="Several, without financial stress"),
    "PP-6": CheckInQuestion("PP-6",
        "Did you turn down a social invitation this week because of money?",
        "purchasing_power", "yes_no_scale", 5,
        low_label="Yes", high_label="No"),
    "PP-7": CheckInQuestion("PP-7",
        "How often this month did you worry about whether you could afford groceries?",
        "purchasing_power", "1-5", 5,
        low_label="Every week", high_label="Never"),
    "PP-8": CheckInQuestion("PP-8",
        "How much of your income goes to debt payments each month?",
        "purchasing_power", "1-10", 10,
        low_label="More than half", high_label="None or very little"),
    "PP-9": CheckInQuestion("PP-9",
        "Could you comfortably handle a $200 unplanned expense right now without stress?",
        "purchasing_power", "1-5", 5,
        low_label="Absolutely not", high_label="Easily, no stress"),
    "PP-10": CheckInQuestion("PP-10",
        "How often do you check prices before buying everyday items?",
        "purchasing_power", "1-5", 5,
        low_label="Always, every purchase", high_label="Rarely, don't need to"),
    "PP-11": CheckInQuestion("PP-11",
        "Did you use any buy-now-pay-later services this month?",
        "purchasing_power", "yes_no_scale", 5,
        low_label="Yes", high_label="No"),
    "PP-12": CheckInQuestion("PP-12",
        "How would you rate your ability to cover an unexpected car or home repair right now?",
        "purchasing_power", "1-10", 10,
        low_label="Could not cover it", high_label="Fully prepared"),
    "CT-PP-1": CheckInQuestion("CT-PP-1",
        "How tight is your budget right now after paying for essentials?",
        "purchasing_power", "1-5", 5,
        low_label="Extremely tight", high_label="Very comfortable"),
    "CT-PP-2": CheckInQuestion("CT-PP-2",
        "Have you had to borrow money or use credit for basics this week?",
        "purchasing_power", "yes_no_scale", 5,
        low_label="Yes", high_label="No"),

    # ── EMERGENCY READINESS (13 + 2 traps) ───────────────────────────────

    "ER-1": CheckInQuestion("ER-1",
        "If you lost your primary income today, how long could you cover essential expenses?",
        "emergency_readiness", "1-5", 5,
        low_label="Less than 1 week", high_label="3+ months"),
    "ER-2": CheckInQuestion("ER-2",
        "How prepared are you to handle a $500 unexpected expense right now without borrowing?",
        "emergency_readiness", "1-10", 10,
        low_label="Completely unprepared, would need to borrow", high_label="Fully prepared, cash available"),
    "ER-3": CheckInQuestion("ER-3",
        "Did you add any amount to an emergency fund or savings buffer this week?",
        "emergency_readiness", "yes_no_scale", 5,
        low_label="No", high_label="Yes"),
    "ER-4": CheckInQuestion("ER-4",
        "How would you rate the overall strength of your financial safety net right now?",
        "emergency_readiness", "1-10", 10,
        low_label="No safety net at all", high_label="Strong, could handle multiple shocks"),
    "ER-5": CheckInQuestion("ER-5",
        "In the last 30 days, did an unexpected expense significantly set you back financially?",
        "emergency_readiness", "yes_no_scale", 5,
        low_label="Yes, it set me back", high_label="No, handled it or nothing came up"),
    "ER-6": CheckInQuestion("ER-6",
        "Do you have health insurance or a plan to cover a medical emergency?",
        "emergency_readiness", "yes_no_scale", 5,
        low_label="No coverage", high_label="Yes, covered"),
    "ER-7": CheckInQuestion("ER-7",
        "How many months of essential expenses do you have saved in accessible accounts?",
        "emergency_readiness", "1-5", 5,
        low_label="Less than 1 week", high_label="6+ months"),
    "ER-8": CheckInQuestion("ER-8",
        "If a major appliance broke today, could you replace it without going into debt?",
        "emergency_readiness", "1-5", 5,
        low_label="Definitely not", high_label="Yes, comfortably"),
    "ER-9": CheckInQuestion("ER-9",
        "How quickly could you access $1,000 in cash if you needed it tomorrow?",
        "emergency_readiness", "1-10", 10,
        low_label="Could not access it", high_label="Immediately available"),
    "ER-10": CheckInQuestion("ER-10",
        "Did you dip into savings or emergency funds for non-emergency spending this month?",
        "emergency_readiness", "yes_no_scale", 5,
        low_label="Yes", high_label="No"),
    "ER-11": CheckInQuestion("ER-11",
        "How confident are you that you could handle two unexpected expenses in the same month?",
        "emergency_readiness", "1-10", 10,
        low_label="Not at all confident", high_label="Completely confident"),
    "ER-12": CheckInQuestion("ER-12",
        "Do you have someone you could borrow money from in a genuine emergency?",
        "emergency_readiness", "yes_no_scale", 5,
        low_label="No one", high_label="Yes, reliable support"),
    "ER-13": CheckInQuestion("ER-13",
        "How would you rate your preparedness for a job loss or income reduction?",
        "emergency_readiness", "1-5", 5,
        low_label="Completely unprepared", high_label="Well prepared with a plan"),
    "CT-ER-1": CheckInQuestion("CT-ER-1",
        "If a $500 bill showed up today, would you need to borrow to pay it?",
        "emergency_readiness", "yes_no_scale", 5,
        low_label="Yes, would need to borrow", high_label="No, I have the cash"),
    "CT-ER-2": CheckInQuestion("CT-ER-2",
        "How many weeks could you survive financially if you stopped working today?",
        "emergency_readiness", "1-5", 5,
        low_label="Less than 1 week", high_label="12+ weeks"),

    # ── FINANCIAL AGENCY (13 + 2 traps) ──────────────────────────────────

    "FA-1": CheckInQuestion("FA-1",
        "How many minutes this week did you spend actively managing your finances?",
        "financial_agency", "1-5", 5,
        low_label="0 minutes", high_label="30+ minutes"),
    "FA-2": CheckInQuestion("FA-2",
        "How many of your recurring bills and savings are automated right now?",
        "financial_agency", "1-5", 5,
        low_label="None, all manual", high_label="All automated"),
    "FA-3": CheckInQuestion("FA-3",
        "Did you take at least one deliberate action this week to improve your financial position?",
        "financial_agency", "yes_no_scale", 5,
        low_label="No", high_label="Yes"),
    "FA-4": CheckInQuestion("FA-4",
        "How clear is your financial plan for the next 90 days?",
        "financial_agency", "1-10", 10,
        low_label="No plan at all", high_label="Detailed plan with specific targets"),
    "FA-5": CheckInQuestion("FA-5",
        "Did you learn something new about personal finance, investing, or money management this week?",
        "financial_agency", "yes_no_scale", 5,
        low_label="No", high_label="Yes"),
    "FA-6": CheckInQuestion("FA-6",
        "Do you use any tools or apps to track your spending or budget?",
        "financial_agency", "yes_no_scale", 5,
        low_label="No", high_label="Yes"),
    "FA-7": CheckInQuestion("FA-7",
        "How often do you review your bank and credit card statements?",
        "financial_agency", "1-5", 5,
        low_label="Never", high_label="Weekly or more"),
    "FA-8": CheckInQuestion("FA-8",
        "Did you negotiate any price, rate, or fee this month?",
        "financial_agency", "yes_no_scale", 5,
        low_label="No", high_label="Yes"),
    "FA-9": CheckInQuestion("FA-9",
        "How proactive are you about finding ways to reduce your monthly expenses?",
        "financial_agency", "1-10", 10,
        low_label="Not proactive at all", high_label="Constantly optimizing"),
    "FA-10": CheckInQuestion("FA-10",
        "Do you have a written budget or spending plan for this month?",
        "financial_agency", "yes_no_scale", 5,
        low_label="No", high_label="Yes"),
    "FA-11": CheckInQuestion("FA-11",
        "How many financial accounts do you actively monitor?",
        "financial_agency", "1-5", 5,
        low_label="Zero", high_label="4 or more"),
    "FA-12": CheckInQuestion("FA-12",
        "Did you compare prices or shop around before a purchase over $50 this week?",
        "financial_agency", "yes_no_scale", 5,
        low_label="No", high_label="Yes"),
    "FA-13": CheckInQuestion("FA-13",
        "How confident are you in your ability to make smart financial decisions right now?",
        "financial_agency", "1-10", 10,
        low_label="Not confident at all", high_label="Very confident"),
    "CT-FA-1": CheckInQuestion("CT-FA-1",
        "How much time did you spend reviewing your finances in the past 7 days?",
        "financial_agency", "1-5", 5,
        low_label="None at all", high_label="More than 30 minutes"),
    "CT-FA-2": CheckInQuestion("CT-FA-2",
        "Did you make any proactive financial decision this week?",
        "financial_agency", "yes_no_scale", 5,
        low_label="No", high_label="Yes"),
}


# No questions currently require runtime inversion.
# All negative-framed questions (e.g., CS-3 "How often did unexpected expenses disrupt...")
# have their scale direction pre-flipped via low_label/high_label at the question level.
# If a future question needs 5=bad and 1=good, add its ID here and normalize_answer()
# in checkin_service.py will flip it automatically.
INVERTED_QUESTION_IDS = set()


# ══════════════════════════════════════════
#  TEMPORAL SCOPE TAGS
# ══════════════════════════════════════════

QUESTION_TEMPORAL_SCOPE: Dict[str, str] = {
    "CS-1": "month", "CS-2": "month", "CS-3": "month", "CS-4": "general",
    "CS-5": "month", "CS-6": "week", "CS-7": "general", "CS-8": "general",
    "CS-9": "general", "CS-10": "month", "CS-11": "week", "CS-12": "general",
    "CT-CS-1": "general", "CT-CS-2": "month",
    "FO-1": "week", "FO-2": "month", "FO-3": "month", "FO-4": "general",
    "FO-5": "week", "FO-6": "general", "FO-7": "general", "FO-8": "month",
    "FO-9": "month", "FO-10": "general", "FO-11": "general", "FO-12": "general",
    "CT-FO-1": "month", "CT-FO-2": "month",
    "PP-1": "general", "PP-2": "week", "PP-3": "week", "PP-4": "general",
    "PP-5": "week", "PP-6": "week", "PP-7": "month", "PP-8": "month",
    "PP-9": "general", "PP-10": "general", "PP-11": "month", "PP-12": "general",
    "CT-PP-1": "general", "CT-PP-2": "week",
    "ER-1": "general", "ER-2": "general", "ER-3": "week", "ER-4": "general",
    "ER-5": "month", "ER-6": "general", "ER-7": "general", "ER-8": "general",
    "ER-9": "general", "ER-10": "month", "ER-11": "general", "ER-12": "general",
    "ER-13": "general", "CT-ER-1": "general", "CT-ER-2": "general",
    "FA-1": "week", "FA-2": "general", "FA-3": "week", "FA-4": "general",
    "FA-5": "week", "FA-6": "general", "FA-7": "general", "FA-8": "month",
    "FA-9": "general", "FA-10": "month", "FA-11": "general", "FA-12": "week",
    "FA-13": "general", "CT-FA-1": "week", "CT-FA-2": "week",
}


# ══════════════════════════════════════════
#  WEEKLY BSI QUESTIONS (kept for future use, not served in daily flow)
# ══════════════════════════════════════════

WEEKLY_QUESTIONS: Dict[str, CheckInQuestion] = {
    "BX-1": CheckInQuestion("BX-1",
        "Did you cancel or pause any recurring subscription this week?",
        "subscription_churn", "yes_no_scale", 5,
        low_label="Yes, cut something", high_label="No, kept everything", is_weekly=True),
    "BX-2": CheckInQuestion("BX-2",
        "Did you use a credit card this week for something you would normally pay with cash or debit?",
        "credit_substitution", "yes_no_scale", 5,
        low_label="Yes, shifted to credit", high_label="No, paid normally", is_weekly=True),
    "BX-3": CheckInQuestion("BX-3",
        "Did you put off a planned purchase this week because you weren't sure you could afford it?",
        "deferred_spending", "yes_no_scale", 5,
        low_label="Yes, delayed it", high_label="No, bought as planned", is_weekly=True),
    "BX-4": CheckInQuestion("BX-4",
        "Did you take on any new debt this week?",
        "debt_accumulation", "yes_no_scale", 5,
        low_label="Yes, added debt", high_label="No, no new debt", is_weekly=True),
    "BX-5": CheckInQuestion("BX-5",
        "Did you actively avoid checking your bank balance or financial accounts this week?",
        "financial_avoidance", "yes_no_scale", 5,
        low_label="Yes, avoided looking", high_label="No, stayed engaged", is_weekly=True),
}


# ══════════════════════════════════════════
#  DIMENSION ROTATION POOLS
# ══════════════════════════════════════════

DIMENSION_POOLS: Dict[str, List[str]] = {
    "current_stability":   ["CS-1", "CS-2", "CS-3", "CS-4", "CS-5", "CS-6", "CS-7", "CS-8", "CS-9", "CS-10", "CS-11", "CS-12", "CT-CS-1", "CT-CS-2"],
    "future_outlook":      ["FO-1", "FO-2", "FO-3", "FO-4", "FO-5", "FO-6", "FO-7", "FO-8", "FO-9", "FO-10", "FO-11", "FO-12", "CT-FO-1", "CT-FO-2"],
    "purchasing_power":    ["PP-1", "PP-2", "PP-3", "PP-4", "PP-5", "PP-6", "PP-7", "PP-8", "PP-9", "PP-10", "PP-11", "PP-12", "CT-PP-1", "CT-PP-2"],
    "emergency_readiness": ["ER-1", "ER-2", "ER-3", "ER-4", "ER-5", "ER-6", "ER-7", "ER-8", "ER-9", "ER-10", "ER-11", "ER-12", "ER-13", "CT-ER-1", "CT-ER-2"],
    "financial_agency":    ["FA-1", "FA-2", "FA-3", "FA-4", "FA-5", "FA-6", "FA-7", "FA-8", "FA-9", "FA-10", "FA-11", "FA-12", "FA-13", "CT-FA-1", "CT-FA-2"],
}


# ══════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════

def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _deterministic_seed(user_id, target_date) -> int:
    """
    FIX #1 (CRITICAL): Deterministic seed for question selection.

    Uses SHA-256 instead of Python's hash(). Python's hash() is randomized
    via PYTHONHASHSEED by default (since 3.3), so a container restart mid-day
    would change which questions a user sees — potentially different from the
    questions they already answered in the GET /questions call.

    SHA-256 is deterministic regardless of process restarts, platform, or
    Python version.
    """
    raw = f"{user_id}:{target_date.isoformat()}"
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return int(digest, 16)


def get_daily_questions(user_id, target_date=None, count=5):
    if target_date is None:
        target_date = _utc_today()

    seed = _deterministic_seed(user_id, target_date)
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


def get_weekly_questions():
    return list(WEEKLY_QUESTIONS.values())


def is_weekly_checkin_day(target_date=None) -> bool:
    """
    Always returns False — weekly BSI questions are disabled from the daily flow.
    Users always get exactly 5 questions. Clean, consistent, no Sunday surprise.
    Re-enable when a dedicated BSI prompt or separate flow is built.
    """
    return False


def get_todays_questions(user_id, target_date=None):
    if target_date is None:
        target_date = _utc_today()

    daily = get_daily_questions(user_id, target_date)

    return {
        "date": target_date.isoformat(),
        "daily_questions": daily,
        "weekly_questions": [],   # BSI disabled — always empty
        "is_weekly_day": False,
    }