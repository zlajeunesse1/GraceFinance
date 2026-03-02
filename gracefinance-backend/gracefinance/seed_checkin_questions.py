# scripts/seed_checkin_questions.py
# Run once to populate the checkin_questions table
# Usage: python -m scripts.seed_checkin_questions

from app.database import SessionLocal
from app.models.checkin import CheckinQuestion
# Create tables if they don't exist


QUESTIONS = [
    # ═══════════════════════════════════════
    # DAY SET 0
    # ═══════════════════════════════════════
    {
        "id": "d0_mood",
        "category": "money_mindset",
        "type": "emoji_select",
        "question": "How's your money energy today?",
        "subtitle": "No wrong answers — just check in with yourself.",
        "options": [
            {"emoji": "😤", "label": "Stressed", "value": "stressed", "mood": 2},
            {"emoji": "😟", "label": "Anxious", "value": "anxious", "mood": 3},
            {"emoji": "😐", "label": "Neutral", "value": "neutral", "mood": 5},
            {"emoji": "😌", "label": "Calm", "value": "calm", "mood": 7},
            {"emoji": "💪", "label": "Powerful", "value": "powerful", "mood": 9},
        ],
        "day_set": 0,
        "sort_order": 0,
    },
    {
        "id": "d0_triggers",
        "category": "spending_habits",
        "type": "quick_tap",
        "question": "What usually triggers you to spend?",
        "subtitle": "Pick all that hit home. Most people have 2-3.",
        "options": [
            {"label": "Boredom", "icon": "📱"},
            {"label": "Stress relief", "icon": "😮‍💨"},
            {"label": "Social pressure", "icon": "👥"},
            {"label": "Reward / treat myself", "icon": "🎁"},
            {"label": "Convenience", "icon": "⚡"},
            {"label": "Fear of missing out", "icon": "😰"},
            {"label": "Habit / autopilot", "icon": "🔄"},
            {"label": "Emotional comfort", "icon": "🫂"},
        ],
        "multi": True,
        "day_set": 0,
        "sort_order": 1,
    },
    {
        "id": "d0_confidence",
        "category": "financial_confidence",
        "type": "visual_slider",
        "question": "How confident do you feel about your finances right now?",
        "subtitle": "Slide to where feels honest.",
        "min_val": 1,
        "max_val": 10,
        "labels": {"1": "Barely hanging on", "5": "Getting there", "10": "Fully in control"},
        "color_range": ["#f87171", "#fbbf24", "#34d399"],
        "day_set": 0,
        "sort_order": 2,
    },
    {
        "id": "d0_goals",
        "category": "money_goals",
        "type": "multiple_choice",
        "question": "What financial wins are you chasing this month?",
        "subtitle": "Select all that apply — ambition is welcome here.",
        "options": [
            "Save a specific amount",
            "Stop impulse buying",
            "Pay off a debt",
            "Start investing",
            "Build an emergency fund",
            "Stick to my budget",
        ],
        "multi": True,
        "day_set": 0,
        "sort_order": 3,
    },
    {
        "id": "d0_reflection",
        "category": "money_mindset",
        "type": "open_text",
        "question": "What's one money belief you grew up with that still affects you?",
        "subtitle": "This is just for you. There's no judgment here.",
        "placeholder": 'e.g. "Money doesn\'t grow on trees" or "Rich people are greedy"...',
        "max_characters": 300,
        "day_set": 0,
        "sort_order": 4,
    },

    # ═══════════════════════════════════════
    # DAY SET 1
    # ═══════════════════════════════════════
    {
        "id": "d1_mood",
        "category": "money_mindset",
        "type": "emoji_select",
        "question": "What's your vibe with money today?",
        "subtitle": "Quick gut check — go with your first instinct.",
        "options": [
            {"emoji": "😩", "label": "Overwhelmed", "value": "overwhelmed", "mood": 2},
            {"emoji": "🤔", "label": "Uncertain", "value": "uncertain", "mood": 4},
            {"emoji": "😊", "label": "Hopeful", "value": "hopeful", "mood": 6},
            {"emoji": "🔥", "label": "Motivated", "value": "motivated", "mood": 8},
            {"emoji": "🧘", "label": "At peace", "value": "at_peace", "mood": 9},
        ],
        "day_set": 1,
        "sort_order": 0,
    },
    {
        "id": "d1_yesterday",
        "category": "spending_habits",
        "type": "multiple_choice",
        "question": "Think about yesterday — which of these happened?",
        "subtitle": "Autopilot spending is the #1 wealth killer. Pick all that apply.",
        "options": [
            "Bought something I didn't really need",
            "Spent to make myself feel better",
            "Bought something because it was on sale",
            "Was pretty intentional with spending",
            "Didn't spend anything",
        ],
        "multi": True,
        "day_set": 1,
        "sort_order": 1,
    },
    {
        "id": "d1_future_self",
        "category": "financial_confidence",
        "type": "visual_slider",
        "question": "How connected do you feel to your future self financially?",
        "subtitle": "Research shows this is the #1 predictor of saving behavior.",
        "min_val": 1,
        "max_val": 10,
        "labels": {"1": "Future me? Don't know her", "5": "Starting to think ahead", "10": "Building for that person daily"},
        "color_range": ["#f87171", "#fbbf24", "#34d399"],
        "day_set": 1,
        "sort_order": 2,
    },
    {
        "id": "d1_money_convo",
        "category": "life_context",
        "type": "quick_tap",
        "question": "Who do you talk to about money? (Be honest)",
        "subtitle": "Financial isolation is real. Most people pick 0-1.",
        "options": [
            {"label": "Partner / spouse", "icon": "💑"},
            {"label": "Parents", "icon": "👨‍👩‍👦"},
            {"label": "Close friend", "icon": "🤝"},
            {"label": "Financial advisor", "icon": "📊"},
            {"label": "Online community", "icon": "💻"},
            {"label": "Nobody", "icon": "🤐"},
        ],
        "multi": True,
        "day_set": 1,
        "sort_order": 3,
    },
    {
        "id": "d1_one_thing",
        "category": "money_goals",
        "type": "open_text",
        "question": "If you could change ONE thing about your financial life right now, what would it be?",
        "subtitle": "Be specific — specificity is power.",
        "placeholder": 'e.g. "I want to stop checking my bank account with dread"...',
        "max_characters": 300,
        "day_set": 1,
        "sort_order": 4,
    },

    # ═══════════════════════════════════════
    # DAY SET 2
    # ═══════════════════════════════════════
    {
        "id": "d2_mood",
        "category": "money_mindset",
        "type": "emoji_select",
        "question": "Money check-in — where are you at today?",
        "subtitle": "Your relationship with money shifts daily. Track it.",
        "options": [
            {"emoji": "😔", "label": "Guilty", "value": "guilty", "mood": 2},
            {"emoji": "😬", "label": "Avoiding it", "value": "avoiding", "mood": 3},
            {"emoji": "🙂", "label": "Stable", "value": "stable", "mood": 6},
            {"emoji": "😎", "label": "Confident", "value": "confident", "mood": 8},
            {"emoji": "🚀", "label": "Unstoppable", "value": "unstoppable", "mood": 10},
        ],
        "day_set": 2,
        "sort_order": 0,
    },
    {
        "id": "d2_impulse",
        "category": "spending_habits",
        "type": "visual_slider",
        "question": "How strong is your impulse control this week?",
        "subtitle": "Willpower fluctuates — that's normal. The goal is awareness.",
        "min_val": 1,
        "max_val": 10,
        "labels": {"1": "Everything tempts me", "5": "Hit or miss", "10": "Locked in"},
        "color_range": ["#f87171", "#fbbf24", "#34d399"],
        "day_set": 2,
        "sort_order": 1,
    },
    {
        "id": "d2_money_story",
        "category": "money_mindset",
        "type": "multiple_choice",
        "question": "Which of these sound like your inner voice about money?",
        "subtitle": "Your money story drives 90% of your decisions. Pick all that resonate.",
        "options": [
            "I'll never have enough",
            "Money is hard to make and easy to lose",
            "I'm getting better with money every day",
            "I deserve to spend on what makes me happy",
            "Money is a tool and I'm learning to use it",
        ],
        "multi": True,
        "day_set": 2,
        "sort_order": 2,
    },
    {
        "id": "d2_drains",
        "category": "money_stress",
        "type": "quick_tap",
        "question": "What's draining your financial energy right now?",
        "subtitle": "Name it to tame it. Pick what resonates.",
        "options": [
            {"label": "Debt pressure", "icon": "⛓️"},
            {"label": "Not earning enough", "icon": "📉"},
            {"label": "No savings buffer", "icon": "🕳️"},
            {"label": "Partner disagreements", "icon": "💔"},
            {"label": "Comparison to others", "icon": "👀"},
            {"label": "Unclear goals", "icon": "🌫️"},
            {"label": "Subscription creep", "icon": "💸"},
            {"label": "Actually doing okay", "icon": "✅"},
        ],
        "multi": True,
        "day_set": 2,
        "sort_order": 3,
    },
    {
        "id": "d2_gratitude",
        "category": "financial_confidence",
        "type": "open_text",
        "question": "Name one financial thing you're grateful for right now — no matter how small.",
        "subtitle": "Gratitude rewires your brain toward abundance. This matters more than you think.",
        "placeholder": 'e.g. "I have a steady paycheck" or "I didn\'t overdraft this month"...',
        "max_characters": 300,
        "day_set": 2,
        "sort_order": 4,
    },
]


def seed():
    db = SessionLocal()
    try:
        # Clear existing questions (optional - remove if you want to preserve edits)
        db.query(CheckinQuestion).delete()

        for q_data in QUESTIONS:
            question = CheckinQuestion(**q_data)
            db.add(question)

        db.commit()
        print(f"✅ Seeded {len(QUESTIONS)} check-in questions across 3 daily sets")
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding questions: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
