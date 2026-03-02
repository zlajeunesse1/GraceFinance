"""
Stream 3: Grace NLP Stream
=============================
Rule-based keyword and theme extraction from Grace conversations.
100% Python regex and keyword matching — ZERO extra API calls.

This stream extracts behavioral signals from what users SAY to Grace,
not just what they answer in check-ins. People reveal things in
conversation they'd never put in a structured form.

EXTRACTION METHODS:
  - Keyword matching (weighted, case-insensitive)
  - Phrase detection (multi-word patterns)
  - Sentiment polarity (positive/negative financial language)
  - Topic classification (debt, savings, income, housing, etc.)
  - Urgency detection (crisis language patterns)
  - Goal extraction (what they want to achieve)

All rule-based. No ML models. No API calls. Runs in <10ms.
"""

import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone

from .signal_registry import Signal, SignalPolarity, SignalSeverity
from .config import EngineConfig, DEFAULT_CONFIG


# =============================================================
#  THEME LEXICONS
#  Each theme has keywords with weights. Higher weight = stronger signal.
#  These are the "rules" in rule-based extraction.
# =============================================================

THEME_LEXICONS: Dict[str, Dict[str, float]] = {
    "debt_stress": {
        # Single words
        "debt": 1.0, "owe": 0.9, "loan": 0.8, "credit card": 1.0,
        "balance": 0.6, "interest": 0.7, "payment": 0.6, "minimum": 0.7,
        "collection": 1.0, "collector": 1.0, "overdue": 0.9, "late fee": 0.9,
        "behind": 0.5, "underwater": 0.9, "drowning": 0.8,
        # Phrases
        "can't pay": 1.0, "can't afford": 0.9, "falling behind": 0.9,
        "maxed out": 1.0, "over limit": 0.9, "student loan": 0.8,
        "medical bill": 0.9, "pay off": 0.7, "debt free": 0.5,
    },
    "income_anxiety": {
        "paycheck": 0.6, "income": 0.5, "salary": 0.5, "wages": 0.5,
        "hours": 0.4, "overtime": 0.5, "raise": 0.5, "promotion": 0.5,
        "fired": 1.0, "laid off": 1.0, "layoff": 1.0, "job loss": 1.0,
        "unemployed": 1.0, "underemployed": 0.8, "side hustle": 0.6,
        "gig": 0.5, "not enough": 0.7, "paycheck to paycheck": 1.0,
        "can't make ends meet": 1.0, "barely getting by": 0.9,
    },
    "savings_goals": {
        "save": 0.6, "saving": 0.7, "savings": 0.7, "emergency fund": 0.9,
        "rainy day": 0.7, "nest egg": 0.7, "put away": 0.6,
        "set aside": 0.6, "retirement": 0.7, "401k": 0.8, "ira": 0.7,
        "invest": 0.7, "investing": 0.7, "compound": 0.6,
        "financial freedom": 0.9, "wealth": 0.6, "build wealth": 0.9,
    },
    "housing_pressure": {
        "rent": 0.7, "mortgage": 0.8, "landlord": 0.6, "lease": 0.6,
        "eviction": 1.0, "evict": 1.0, "housing": 0.6, "apartment": 0.5,
        "house": 0.5, "home": 0.4, "move": 0.4, "moving": 0.4,
        "down payment": 0.8, "closing costs": 0.8, "homebuyer": 0.7,
        "property tax": 0.7, "rent increase": 0.9, "can't afford rent": 1.0,
        "first time buyer": 0.8, "pre-approval": 0.8,
    },
    "impulse_awareness": {
        "impulse": 0.9, "regret": 0.8, "shouldn't have": 0.8,
        "buyer's remorse": 1.0, "splurge": 0.8, "treat myself": 0.6,
        "retail therapy": 0.9, "couldn't resist": 0.8, "temptation": 0.7,
        "weakness": 0.6, "guilty": 0.8, "guilty pleasure": 0.7,
        "amazon": 0.5, "online shopping": 0.7, "cart": 0.4,
        "deal": 0.4, "sale": 0.4, "discount": 0.4,
    },
    "family_financial_stress": {
        "kids": 0.5, "children": 0.5, "child care": 0.8, "daycare": 0.8,
        "childcare": 0.8, "family": 0.4, "partner": 0.4, "spouse": 0.5,
        "argue about money": 1.0, "fight about money": 1.0,
        "child support": 0.9, "alimony": 0.9, "divorce": 0.8,
        "school": 0.4, "tuition": 0.8, "college fund": 0.8,
        "baby": 0.5, "pregnant": 0.6, "formula": 0.5, "diapers": 0.5,
    },
    "positive_momentum": {
        "progress": 0.7, "proud": 0.8, "accomplished": 0.8,
        "paid off": 0.9, "debt free": 1.0, "milestone": 0.8,
        "goal": 0.5, "achieved": 0.8, "on track": 0.8,
        "improving": 0.7, "better": 0.5, "finally": 0.6,
        "breakthrough": 0.9, "turning point": 0.9, "momentum": 0.8,
        "streak": 0.6, "consistent": 0.7, "discipline": 0.7,
    },
    "crisis_language": {
        "desperate": 1.0, "hopeless": 1.0, "scared": 0.9,
        "terrified": 1.0, "panic": 1.0, "panicking": 1.0,
        "don't know what to do": 1.0, "no way out": 1.0,
        "rock bottom": 1.0, "breaking point": 1.0, "crisis": 0.9,
        "emergency": 0.8, "help me": 0.7, "overwhelmed": 0.8,
        "can't breathe": 0.9, "losing everything": 1.0,
        "about to lose": 0.9, "shut off": 0.8, "disconnected": 0.7,
    },
    "budget_planning": {
        "budget": 0.8, "budgeting": 0.8, "plan": 0.5, "planning": 0.5,
        "track": 0.5, "tracking": 0.6, "spreadsheet": 0.6,
        "categories": 0.5, "allocate": 0.7, "envelope": 0.7,
        "50/30/20": 0.9, "zero based": 0.9, "cash flow": 0.8,
        "monthly budget": 0.9, "weekly budget": 0.8, "spending plan": 0.9,
    },
}


# =============================================================
#  SENTIMENT PATTERNS
#  Financial-specific positive/negative language
# =============================================================

NEGATIVE_FINANCIAL_PATTERNS = [
    r"\bcan'?t afford\b", r"\bnot enough\b", r"\brunning out\b",
    r"\bbroke\b", r"\bstruggling?\b", r"\bstress(?:ed|ful|ing)?\b",
    r"\banxious\b", r"\banxiety\b", r"\bworr(?:y|ied|ying)\b",
    r"\bfrustrat(?:ed|ing)\b", r"\boverwhelm(?:ed|ing)\b",
    r"\bscar(?:ed|y)\b", r"\bhopeless\b", r"\bgave up\b",
]

POSITIVE_FINANCIAL_PATTERNS = [
    r"\bsaved\b", r"\bpaid off\b", r"\bon track\b",
    r"\bconfident\b", r"\bproud\b", r"\bexcited\b",
    r"\bprogress\b", r"\bimproving\b", r"\bgetting better\b",
    r"\bgoal\b", r"\bachiev(?:ed|ing)\b", r"\bmilestone\b",
    r"\bcelebrat(?:e|ing)\b", r"\bfree\b", r"\bstable\b",
]


class GraceNLPStream:
    """
    Stream 3: Extracts behavioral signals from Grace conversation text.
    Pure rule-based. Zero API calls.
    """

    def __init__(self, config: EngineConfig = DEFAULT_CONFIG):
        self.config = config
        # Pre-compile regex patterns
        self._neg_patterns = [re.compile(p, re.IGNORECASE) for p in NEGATIVE_FINANCIAL_PATTERNS]
        self._pos_patterns = [re.compile(p, re.IGNORECASE) for p in POSITIVE_FINANCIAL_PATTERNS]

    def process(self, messages: List[Dict[str, str]]) -> List[Signal]:
        """
        Main entry point. Extracts signals from conversation messages.

        Args:
            messages: List of {"role": "user"|"assistant", "content": "..."} dicts.
                      Only user messages are analyzed.

        Returns:
            List of behavioral signals detected in the conversation.
        """
        # Only analyze user messages
        user_text = " ".join(
            msg["content"] for msg in messages
            if msg.get("role") == "user" and msg.get("content")
        )

        if not user_text.strip():
            return []

        signals: List[Signal] = []

        # 1. Theme Detection
        signals.extend(self._detect_themes(user_text))

        # 2. Financial Sentiment
        signals.extend(self._detect_sentiment(user_text))

        # 3. Urgency/Crisis Detection
        signals.extend(self._detect_urgency(user_text))

        # 4. Goal Extraction
        signals.extend(self._detect_goals(user_text))

        return signals

    def extract_themes(self, text: str) -> List[Dict[str, float]]:
        """
        Public method for theme extraction only (used by intelligence_engine
        for conversation theme logging).

        Returns list of {"theme": name, "confidence": score} dicts.
        """
        text_lower = text.lower()
        themes = []

        for theme_name, keywords in THEME_LEXICONS.items():
            matches = 0
            total_weight = 0.0

            for keyword, weight in keywords.items():
                if keyword.lower() in text_lower:
                    matches += 1
                    total_weight += weight

            if matches >= self.config.nlp_min_matches_for_theme:
                confidence = min(
                    self.config.nlp_max_confidence,
                    matches * self.config.nlp_confidence_per_match,
                )
                themes.append({
                    "theme": theme_name,
                    "confidence": confidence,
                    "matches": matches,
                    "weight": total_weight,
                })

        # Sort by weight (strongest signal first)
        themes.sort(key=lambda t: t["weight"], reverse=True)
        return themes

    # ----------------------------------------------------------
    #  THEME DETECTION
    # ----------------------------------------------------------

    def _detect_themes(self, text: str) -> List[Signal]:
        """Detect conversational themes via keyword matching."""
        signals = []
        themes = self.extract_themes(text)

        theme_signal_map = {
            "debt_stress": {
                "polarity": SignalPolarity.NEGATIVE,
                "severity": SignalSeverity.HIGH,
                "label": "Debt stress detected in conversation",
                "coaching_hook": "They're talking about debt. Listen first, then help prioritize.",
            },
            "income_anxiety": {
                "polarity": SignalPolarity.NEGATIVE,
                "severity": SignalSeverity.HIGH,
                "label": "Income anxiety detected in conversation",
                "coaching_hook": "Income worry is foundational. Validate the fear, then explore options.",
            },
            "savings_goals": {
                "polarity": SignalPolarity.POSITIVE,
                "severity": SignalSeverity.LOW,
                "label": "Savings goals discussed",
                "coaching_hook": "They're thinking about savings. Fan this flame — set a specific target.",
            },
            "housing_pressure": {
                "polarity": SignalPolarity.NEGATIVE,
                "severity": SignalSeverity.MEDIUM,
                "label": "Housing cost pressure detected",
                "coaching_hook": "Housing is likely their biggest expense. Help them see options.",
            },
            "impulse_awareness": {
                "polarity": SignalPolarity.NEUTRAL,
                "severity": SignalSeverity.MEDIUM,
                "label": "Impulse spending awareness in conversation",
                "coaching_hook": "They're already aware of impulse patterns. Build on that awareness.",
            },
            "family_financial_stress": {
                "polarity": SignalPolarity.NEGATIVE,
                "severity": SignalSeverity.MEDIUM,
                "label": "Family financial pressure detected",
                "coaching_hook": "Family financial stress is heavy. Acknowledge the responsibility they carry.",
            },
            "positive_momentum": {
                "polarity": SignalPolarity.POSITIVE,
                "severity": SignalSeverity.MEDIUM,
                "label": "Positive financial momentum in conversation",
                "coaching_hook": "They're feeling good. Reinforce whatever behavior is driving this.",
            },
            "crisis_language": {
                "polarity": SignalPolarity.NEGATIVE,
                "severity": SignalSeverity.CRITICAL,
                "label": "Financial crisis language detected",
                "coaching_hook": "This person may be in crisis. Lead with pure empathy. No advice yet — just listen.",
            },
            "budget_planning": {
                "polarity": SignalPolarity.POSITIVE,
                "severity": SignalSeverity.LOW,
                "label": "Budget planning discussion",
                "coaching_hook": "They want to plan. Help them build a realistic budget that fits their life.",
            },
        }

        for theme in themes:
            theme_name = theme["theme"]
            if theme_name not in theme_signal_map:
                continue

            meta = theme_signal_map[theme_name]
            signals.append(Signal(
                key=f"nlp_{theme_name}",
                stream="nlp",
                polarity=meta["polarity"],
                severity=meta["severity"],
                value=theme["weight"] * 10,  # Scale to 0-100ish
                confidence=theme["confidence"],
                label=meta["label"],
                detail=f"Detected {theme['matches']} keyword matches for '{theme_name.replace('_', ' ')}'.",
                coaching_hook=meta["coaching_hook"],
            ))

        return signals

    # ----------------------------------------------------------
    #  FINANCIAL SENTIMENT
    # ----------------------------------------------------------

    def _detect_sentiment(self, text: str) -> List[Signal]:
        """Detect overall financial sentiment from language patterns."""
        signals = []

        neg_count = sum(1 for p in self._neg_patterns if p.search(text))
        pos_count = sum(1 for p in self._pos_patterns if p.search(text))

        total = neg_count + pos_count
        if total == 0:
            return signals

        neg_ratio = neg_count / total
        pos_ratio = pos_count / total

        if neg_ratio >= 0.7 and neg_count >= 3:
            signals.append(Signal(
                key="nlp_sentiment_negative",
                stream="nlp",
                polarity=SignalPolarity.NEGATIVE,
                severity=SignalSeverity.MEDIUM,
                value=neg_ratio * 100,
                confidence=min(0.9, neg_count * 0.15),
                label="Conversation tone is heavily negative about finances",
                detail=f"{neg_count} negative vs {pos_count} positive financial language patterns.",
                coaching_hook="Their language is heavy. Match their energy first, then slowly shift toward solutions.",
            ))
        elif pos_ratio >= 0.7 and pos_count >= 3:
            signals.append(Signal(
                key="nlp_sentiment_positive",
                stream="nlp",
                polarity=SignalPolarity.POSITIVE,
                severity=SignalSeverity.LOW,
                value=pos_ratio * 100,
                confidence=min(0.9, pos_count * 0.15),
                label="Conversation tone is positive about finances",
                detail=f"{pos_count} positive vs {neg_count} negative financial language patterns.",
                coaching_hook="Positive energy. Use this momentum for goal-setting.",
            ))

        return signals

    # ----------------------------------------------------------
    #  URGENCY / CRISIS DETECTION
    # ----------------------------------------------------------

    def _detect_urgency(self, text: str) -> List[Signal]:
        """Detect crisis-level language requiring immediate empathetic response."""
        signals = []

        urgency_patterns = [
            (r"\bdon'?t know what to do\b", 1.0),
            (r"\bno way out\b", 1.0),
            (r"\blosing everything\b", 1.0),
            (r"\babout to lose\b", 0.9),
            (r"\bdesper(?:ate|ation)\b", 0.9),
            (r"\brock bottom\b", 1.0),
            (r"\bbreaking point\b", 1.0),
            (r"\bpanic(?:king)?\b", 0.8),
            (r"\bterrified\b", 0.9),
            (r"\bhopeless\b", 1.0),
        ]

        total_urgency = 0.0
        match_count = 0

        for pattern, weight in urgency_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                total_urgency += weight
                match_count += 1

        if match_count >= 2 or total_urgency >= 1.5:
            signals.append(Signal(
                key="nlp_crisis_urgent",
                stream="nlp",
                polarity=SignalPolarity.NEGATIVE,
                severity=SignalSeverity.CRITICAL,
                value=min(100, total_urgency * 50),
                confidence=min(0.95, match_count * 0.3),
                label="URGENT: User may be in financial crisis",
                detail=f"{match_count} crisis language patterns detected.",
                coaching_hook="PRIORITY: Full empathy mode. No tips, no advice. Just be present and acknowledge their pain.",
            ))

        return signals

    # ----------------------------------------------------------
    #  GOAL EXTRACTION
    # ----------------------------------------------------------

    def _detect_goals(self, text: str) -> List[Signal]:
        """Detect when users express financial goals."""
        signals = []

        goal_patterns = [
            (r"\bwant to (?:save|pay off|buy|invest|build|start)\b", "aspiration"),
            (r"\bgoal is\b", "stated_goal"),
            (r"\btrying to\b", "active_pursuit"),
            (r"\bplanning to\b", "planned"),
            (r"\bhope to\b", "aspiration"),
            (r"\bneed to (?:save|pay|budget|cut)\b", "necessity"),
            (r"\bby (?:end of|next) (?:year|month|week)\b", "time_bound"),
        ]

        goal_types = set()
        for pattern, goal_type in goal_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                goal_types.add(goal_type)

        if goal_types:
            is_time_bound = "time_bound" in goal_types
            signals.append(Signal(
                key="nlp_goal_detected",
                stream="nlp",
                polarity=SignalPolarity.POSITIVE,
                severity=SignalSeverity.MEDIUM if is_time_bound else SignalSeverity.LOW,
                value=len(goal_types) * 20,
                confidence=min(0.85, len(goal_types) * 0.25),
                label="User expressed financial goals",
                detail=f"Goal patterns detected: {', '.join(goal_types)}.",
                coaching_hook="They have goals. Help them make it SMART: Specific, Measurable, Achievable, Relevant, Time-bound.",
            ))

        return signals