"""
Pattern Detector
==================
Cross-stream pattern detection — finds "aha" moments where signals
from different streams corroborate each other.

This is what makes the engine more than the sum of its parts.
A single signal from one stream is data. The same signal confirmed
by two streams is intelligence.

CROSS-STREAM PATTERNS:
  - Check-in shows FCS drop + NLP detects stress language → Confirmed stress
  - Pulse shows impulse trend + NLP detects regret → Emotional spending loop
  - Check-in shows low Debt Pressure + NLP detects housing talk → Housing risk
  - Pulse shows positive momentum + NLP detects goals → Growth opportunity
  - All 3 streams show negative → Compound stress alert
"""

from typing import List, Dict, Optional
from dataclasses import dataclass

from .signal_registry import SignalRegistry, Signal, SignalPolarity, SignalSeverity
from .config import EngineConfig, DEFAULT_CONFIG


@dataclass
class CrossStreamPattern:
    """A pattern detected across multiple streams."""

    name: str
    description: str
    streams_involved: List[str]     # Which streams contributed
    contributing_signals: List[str]  # Signal keys that formed this pattern
    severity: SignalSeverity
    confidence: float               # Combined confidence (0-1)
    coaching_directive: str          # What Grace should do about this
    insight_for_user: str            # How to explain this to the user

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "streams_involved": self.streams_involved,
            "contributing_signals": self.contributing_signals,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "coaching_directive": self.coaching_directive,
            "insight_for_user": self.insight_for_user,
        }


class PatternDetector:
    """
    Finds cross-stream patterns that individual streams can't see alone.
    """

    def __init__(self, config: EngineConfig = DEFAULT_CONFIG):
        self.config = config

    def detect(self, registry: SignalRegistry) -> List[CrossStreamPattern]:
        """
        Run all cross-stream pattern detectors.
        Returns patterns found, sorted by severity.
        """
        patterns: List[CrossStreamPattern] = []

        patterns.extend(self._detect_confirmed_stress(registry))
        patterns.extend(self._detect_emotional_spending_loop(registry))
        patterns.extend(self._detect_housing_risk(registry))
        patterns.extend(self._detect_growth_opportunity(registry))
        patterns.extend(self._detect_compound_stress(registry))
        patterns.extend(self._detect_say_do_gap(registry))
        patterns.extend(self._detect_recovery_signal(registry))

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        patterns.sort(key=lambda p: severity_order.get(p.severity.value, 4))

        return patterns

    # ----------------------------------------------------------
    #  PATTERN: CONFIRMED STRESS
    #  Check-in FCS drop/low + NLP stress language
    # ----------------------------------------------------------

    def _detect_confirmed_stress(self, registry: SignalRegistry) -> List[CrossStreamPattern]:
        """FCS data + conversation language both show stress."""
        patterns = []

        # Check-in signals: FCS low or declining
        checkin_stress = [
            s for s in registry.by_stream("checkin")
            if s.key in ("fcs_critical", "fcs_warning", "bsi_critical", "bsi_elevated")
        ]

        # NLP signals: stress-related themes
        nlp_stress = [
            s for s in registry.by_stream("nlp")
            if s.key in ("nlp_debt_stress", "nlp_income_anxiety", "nlp_crisis_language",
                         "nlp_sentiment_negative")
        ]

        if checkin_stress and nlp_stress:
            combined_confidence = min(
                0.95,
                max(s.confidence for s in checkin_stress) * 0.6
                + max(s.confidence for s in nlp_stress) * 0.4,
            )

            contributing = [s.key for s in checkin_stress + nlp_stress]

            patterns.append(CrossStreamPattern(
                name="confirmed_financial_stress",
                description="Both check-in data and conversation language confirm financial stress.",
                streams_involved=["checkin", "nlp"],
                contributing_signals=contributing,
                severity=SignalSeverity.HIGH,
                confidence=combined_confidence,
                coaching_directive=(
                    "This is confirmed stress — not just a bad day. "
                    "Lead with empathy. Help them identify the single biggest pressure point "
                    "and build one action step around it."
                ),
                insight_for_user=(
                    "Your check-ins and our conversations both show you're under financial pressure right now. "
                    "That's real, and it's okay to feel it. Let's focus on the one thing that would give you "
                    "the most relief."
                ),
            ))

        return patterns

    # ----------------------------------------------------------
    #  PATTERN: EMOTIONAL SPENDING LOOP
    #  Pulse shows impulse trend + NLP shows regret/awareness
    # ----------------------------------------------------------

    def _detect_emotional_spending_loop(self, registry: SignalRegistry) -> List[CrossStreamPattern]:
        """Impulse spending pattern + conversation reveals awareness/regret."""
        patterns = []

        pulse_impulse = [
            s for s in registry.by_stream("pulse")
            if s.key in ("impulse_critical", "impulse_warning", "mood_spend_critical", "mood_spend_warning")
        ]

        nlp_impulse = [
            s for s in registry.by_stream("nlp")
            if s.key in ("nlp_impulse_awareness",)
        ]

        if pulse_impulse and nlp_impulse:
            patterns.append(CrossStreamPattern(
                name="emotional_spending_loop",
                description="User shows impulse spending patterns AND is talking about it — they're aware but stuck.",
                streams_involved=["pulse", "nlp"],
                contributing_signals=[s.key for s in pulse_impulse + nlp_impulse],
                severity=SignalSeverity.HIGH,
                confidence=0.85,
                coaching_directive=(
                    "They already know impulse spending is a problem. Don't tell them what they already know. "
                    "Instead, help them build a specific system: 24-hour rule, spending pause, or "
                    "redirect strategy. Make it concrete and achievable."
                ),
                insight_for_user=(
                    "I can see you're already aware of the impulse spending pattern — that self-awareness "
                    "is actually the hardest part. Let's turn that awareness into a system that works for you."
                ),
            ))

        return patterns

    # ----------------------------------------------------------
    #  PATTERN: HOUSING RISK
    #  Low Debt Pressure + housing conversation
    # ----------------------------------------------------------

    def _detect_housing_risk(self, registry: SignalRegistry) -> List[CrossStreamPattern]:
        """Low safety net + active housing concerns in conversation."""
        patterns = []

        dim_signals = [
            s for s in registry.by_stream("checkin")
            if s.dimension == "debt_pressure"
            and s.polarity == SignalPolarity.NEGATIVE
        ]

        housing_nlp = [
            s for s in registry.by_stream("nlp")
            if s.key == "nlp_housing_pressure"
        ]

        if dim_signals and housing_nlp:
            patterns.append(CrossStreamPattern(
                name="housing_vulnerability",
                description="Low Debt Pressure combined with active housing pressure concerns.",
                streams_involved=["checkin", "nlp"],
                contributing_signals=[s.key for s in dim_signals + housing_nlp],
                severity=SignalSeverity.HIGH,
                confidence=0.80,
                coaching_directive=(
                    "Housing + no safety net is a vulnerable combination. "
                    "Help them build even a small emergency buffer. $50/week matters. "
                    "Don't overwhelm with the full picture."
                ),
                insight_for_user=(
                    "I notice housing costs are on your mind, and your emergency cushion is thin right now. "
                    "Let's build a small buffer to give you breathing room."
                ),
            ))

        return patterns

    # ----------------------------------------------------------
    #  PATTERN: GROWTH OPPORTUNITY
    #  Positive momentum + goals expressed
    # ----------------------------------------------------------

    def _detect_growth_opportunity(self, registry: SignalRegistry) -> List[CrossStreamPattern]:
        """User is improving AND expressing goals — time to push."""
        patterns = []

        momentum = [
            s for s in registry.by_stream("pulse")
            if s.key in ("fcs_momentum_positive", "fcs_weekly_surge")
        ]

        goals = [
            s for s in registry.by_stream("nlp")
            if s.key in ("nlp_goal_detected", "nlp_savings_goals", "nlp_positive_momentum")
        ]

        if momentum and goals:
            patterns.append(CrossStreamPattern(
                name="growth_window",
                description="User has positive momentum AND is expressing goals — prime coaching moment.",
                streams_involved=["pulse", "nlp"],
                contributing_signals=[s.key for s in momentum + goals],
                severity=SignalSeverity.MEDIUM,
                confidence=0.85,
                coaching_directive=(
                    "This is the golden coaching moment. They're improving AND motivated. "
                    "Help them set a specific, time-bound goal. Push them slightly beyond "
                    "what they think they can do."
                ),
                insight_for_user=(
                    "You're on a roll — your numbers are improving and you're clearly motivated. "
                    "This is the perfect time to lock in a bigger goal. What would make you really proud "
                    "to accomplish in the next 30 days?"
                ),
            ))

        return patterns

    # ----------------------------------------------------------
    #  PATTERN: COMPOUND STRESS
    #  All 3 streams showing negative signals
    # ----------------------------------------------------------

    def _detect_compound_stress(self, registry: SignalRegistry) -> List[CrossStreamPattern]:
        """Negative signals from all 3 streams — full-spectrum stress."""
        patterns = []

        checkin_neg = [
            s for s in registry.by_stream("checkin")
            if s.polarity == SignalPolarity.NEGATIVE
        ]
        pulse_neg = [
            s for s in registry.by_stream("pulse")
            if s.polarity == SignalPolarity.NEGATIVE
        ]
        nlp_neg = [
            s for s in registry.by_stream("nlp")
            if s.polarity == SignalPolarity.NEGATIVE
        ]

        if checkin_neg and pulse_neg and nlp_neg:
            total_neg = len(checkin_neg) + len(pulse_neg) + len(nlp_neg)
            if total_neg >= 5:
                patterns.append(CrossStreamPattern(
                    name="compound_stress",
                    description="All 3 data streams show negative signals — this person needs support.",
                    streams_involved=["checkin", "pulse", "nlp"],
                    contributing_signals=[
                        s.key for s in (checkin_neg[:2] + pulse_neg[:2] + nlp_neg[:2])
                    ],
                    severity=SignalSeverity.CRITICAL,
                    confidence=0.90,
                    coaching_directive=(
                        "Full-spectrum stress. Every data source confirms they're struggling. "
                        "Do NOT overload with advice. Pick the ONE most impactful thing and "
                        "help them focus exclusively on that. Everything else can wait."
                    ),
                    insight_for_user=(
                        "I can see things are tough across the board right now. "
                        "Instead of trying to fix everything at once, let's pick the one thing "
                        "that would make the biggest difference and start there."
                    ),
                ))

        return patterns

    # ----------------------------------------------------------
    #  PATTERN: SAY-DO GAP
    #  NLP shows positive goals but check-in/pulse show no improvement
    # ----------------------------------------------------------

    def _detect_say_do_gap(self, registry: SignalRegistry) -> List[CrossStreamPattern]:
        """User talks positively but data doesn't show improvement."""
        patterns = []

        positive_talk = [
            s for s in registry.by_stream("nlp")
            if s.key in ("nlp_goal_detected", "nlp_savings_goals", "nlp_positive_momentum",
                         "nlp_budget_planning", "nlp_sentiment_positive")
        ]

        negative_data = [
            s for s in registry.by_stream("checkin")
            if s.polarity == SignalPolarity.NEGATIVE
            and s.severity in (SignalSeverity.HIGH, SignalSeverity.CRITICAL)
        ]

        declining_trend = [
            s for s in registry.by_stream("pulse")
            if s.key in ("fcs_decline_streak", "fcs_declining")
        ]

        if positive_talk and (negative_data or declining_trend):
            patterns.append(CrossStreamPattern(
                name="say_do_gap",
                description="User expresses positive intentions but data shows declining patterns.",
                streams_involved=["nlp", "checkin", "pulse"],
                contributing_signals=[
                    s.key for s in positive_talk[:2] + negative_data[:2] + declining_trend[:1]
                ],
                severity=SignalSeverity.MEDIUM,
                confidence=0.70,
                coaching_directive=(
                    "Delicate territory. They WANT to improve but actions aren't matching intentions. "
                    "Don't call out the gap directly — instead, help them identify the smallest "
                    "possible next step. Reduce friction to action."
                ),
                insight_for_user=(
                    "I love your energy and goals. Let's make sure we're building small, "
                    "daily habits that move the needle. What's one thing you could do today "
                    "that takes less than 5 minutes?"
                ),
            ))

        return patterns

    # ----------------------------------------------------------
    #  PATTERN: RECOVERY SIGNAL
    #  Previous stress signals + current improvement
    # ----------------------------------------------------------

    def _detect_recovery_signal(self, registry: SignalRegistry) -> List[CrossStreamPattern]:
        """Detect when a previously stressed user is bouncing back."""
        patterns = []

        # Positive momentum from pulse
        momentum = [
            s for s in registry.by_stream("pulse")
            if s.key in ("fcs_momentum_positive", "fcs_weekly_surge")
        ]

        # Strong streak
        streak = [
            s for s in registry.by_stream("pulse")
            if s.key in ("streak_weekly", "streak_biweekly", "streak_monthly")
        ]

        # But still some checkin concerns (recovering FROM something)
        some_concern = [
            s for s in registry.by_stream("checkin")
            if s.polarity == SignalPolarity.NEGATIVE
            and s.severity in (SignalSeverity.MEDIUM, SignalSeverity.LOW)
        ]

        if momentum and streak and some_concern:
            patterns.append(CrossStreamPattern(
                name="recovery_in_progress",
                description="User is actively recovering from financial stress — improving despite challenges.",
                streams_involved=["pulse", "checkin"],
                contributing_signals=[
                    s.key for s in momentum[:1] + streak[:1] + some_concern[:1]
                ],
                severity=SignalSeverity.LOW,
                confidence=0.80,
                coaching_directive=(
                    "They're in recovery mode — improving but not out of the woods. "
                    "Celebrate the progress loudly. Point to specific metrics that improved. "
                    "Help them see their own resilience."
                ),
                insight_for_user=(
                    "You're bouncing back. The numbers show real improvement, and your consistency "
                    "is what's driving it. Keep going — you're building something solid."
                ),
            ))

        return patterns

    def build_pattern_context(self, patterns: List[CrossStreamPattern]) -> str:
        """
        Build a text block for Grace's system prompt with detected patterns.
        """
        if not patterns:
            return ""

        lines = ["\n[CROSS-STREAM BEHAVIORAL PATTERNS]"]
        for p in patterns[:4]:  # Top 4 patterns max
            lines.append(f"\n  Pattern: {p.name}")
            lines.append(f"  Severity: {p.severity.value}")
            lines.append(f"  Confidence: {p.confidence:.0%}")
            lines.append(f"  Directive: {p.coaching_directive}")
            lines.append(f"  User insight: {p.insight_for_user}")

        return "\n".join(lines)