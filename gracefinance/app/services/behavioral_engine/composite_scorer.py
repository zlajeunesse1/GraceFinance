"""
Composite Scorer
==================
Merges signals from all 3 streams into a unified behavioral profile.

This is the single number that represents a user's overall financial
behavioral health — think of it as a "behavioral credit score" that
combines what they reported (check-in), what patterns show (pulse),
and what they said (NLP).

The composite feeds:
  - Grace's coaching intensity calibration
  - The GF-RWI index (via index_feeder.py)
  - Dashboard risk indicators
  - Proactive notification triggers
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field

from .signal_registry import SignalRegistry, Signal, SignalPolarity, SignalSeverity
from .config import EngineConfig, DEFAULT_CONFIG


@dataclass
class CompositeResult:
    """Result of composite scoring across all 3 streams."""

    # Overall score (0-100)
    composite_score: float

    # Per-stream scores (0-100)
    checkin_score: float
    pulse_score: float
    nlp_score: float

    # Stream weights used (may differ from config if a stream has no data)
    weights_used: Dict[str, float]

    # Risk classification
    risk_level: str  # "low", "medium", "high", "critical"

    # Signal summary
    total_signals: int
    critical_count: int
    negative_count: int
    positive_count: int

    # Coaching intensity recommendation (1-5)
    coaching_intensity: int

    # Top concerns for Grace
    top_concerns: List[str] = field(default_factory=list)

    # Top strengths for Grace
    top_strengths: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "composite_score": round(self.composite_score, 2),
            "checkin_score": round(self.checkin_score, 2),
            "pulse_score": round(self.pulse_score, 2),
            "nlp_score": round(self.nlp_score, 2),
            "weights_used": self.weights_used,
            "risk_level": self.risk_level,
            "total_signals": self.total_signals,
            "critical_count": self.critical_count,
            "negative_count": self.negative_count,
            "positive_count": self.positive_count,
            "coaching_intensity": self.coaching_intensity,
            "top_concerns": self.top_concerns,
            "top_strengths": self.top_strengths,
        }


class CompositeScorer:
    """
    Merges all 3 streams into a single behavioral health score.
    Handles missing streams gracefully by redistributing weights.
    """

    def __init__(self, config: EngineConfig = DEFAULT_CONFIG):
        self.config = config

    def score(self, registry: SignalRegistry) -> CompositeResult:
        """
        Compute the composite behavioral score from all registered signals.

        Args:
            registry: SignalRegistry populated by all 3 streams.

        Returns:
            CompositeResult with scores, risk level, and coaching guidance.
        """
        # Compute per-stream scores
        checkin_score = registry.stream_health_score("checkin")
        pulse_score = registry.stream_health_score("pulse")
        nlp_score = registry.stream_health_score("nlp")

        # Determine effective weights (handle missing streams)
        weights = self._compute_effective_weights(registry)

        # Weighted composite
        composite = (
            checkin_score * weights["checkin"]
            + pulse_score * weights["pulse"]
            + nlp_score * weights["nlp"]
        )

        # Signal counts
        counts = registry.overall_signal_count()

        # Risk classification
        risk_level = self._classify_risk(composite, registry)

        # Coaching intensity (1-5)
        coaching_intensity = self._compute_coaching_intensity(
            composite, risk_level, registry
        )

        # Extract top concerns and strengths
        top_concerns = [
            s.label for s in registry.negative_signals()[:5]
        ]
        top_strengths = [
            s.label for s in registry.positive_signals()[:3]
        ]

        return CompositeResult(
            composite_score=composite,
            checkin_score=checkin_score,
            pulse_score=pulse_score,
            nlp_score=nlp_score,
            weights_used=weights,
            risk_level=risk_level,
            total_signals=counts["total"],
            critical_count=counts["critical"],
            negative_count=counts["negative"],
            positive_count=counts["positive"],
            coaching_intensity=coaching_intensity,
            top_concerns=top_concerns,
            top_strengths=top_strengths,
        )

    def _compute_effective_weights(self, registry: SignalRegistry) -> Dict[str, float]:
        """
        Compute effective weights, redistributing from empty streams.

        If a stream has no signals, its weight gets redistributed
        proportionally to streams that do have signals.
        """
        base_weights = self.config.stream_weights.copy()

        if not self.config.redistribute_missing_weight:
            return base_weights

        active_streams = {}
        inactive_weight = 0.0

        for stream, weight in base_weights.items():
            if registry.by_stream(stream):
                active_streams[stream] = weight
            else:
                inactive_weight += weight

        if not active_streams:
            # No data from any stream — return equal weights
            return {"checkin": 0.34, "pulse": 0.33, "nlp": 0.33}

        if inactive_weight > 0:
            # Redistribute proportionally
            active_total = sum(active_streams.values())
            for stream in active_streams:
                active_streams[stream] += (
                    inactive_weight * (active_streams[stream] / active_total)
                )

        # Fill in zeros for inactive streams
        result = {s: 0.0 for s in base_weights}
        result.update(active_streams)

        return result

    def _classify_risk(self, composite: float, registry: SignalRegistry) -> str:
        """
        Classify overall risk level based on composite score + signal severity.

        Risk is elevated by:
          - Low composite score
          - Presence of critical signals
          - High ratio of negative to positive signals
        """
        critical_count = len(registry.critical_alerts())
        negative_count = len(registry.negative_signals())

        # Critical signals override composite score
        if critical_count >= 2:
            return "critical"
        if critical_count >= 1 and composite < 40:
            return "critical"

        # Score-based classification
        if composite < 25:
            return "critical"
        elif composite < 40:
            return "high"
        elif composite < 55:
            if negative_count >= 5:
                return "high"
            return "medium"
        elif composite < 70:
            return "medium" if negative_count >= 3 else "low"
        else:
            return "low"

    def _compute_coaching_intensity(
        self, composite: float, risk_level: str, registry: SignalRegistry
    ) -> int:
        """
        Determine how intensely Grace should coach this user.

        1 = Light touch (celebrate, maintain)
        2 = Supportive (gentle nudges, encouragement)
        3 = Active (specific tips, action items)
        4 = Intensive (daily check-ins, structured plans)
        5 = Crisis (empathy-first, minimal advice, resource referrals)
        """
        if risk_level == "critical":
            return 5
        elif risk_level == "high":
            return 4
        elif risk_level == "medium":
            # Check for specific escalation signals
            has_crisis_language = any(
                s.key == "nlp_crisis_urgent" for s in registry.all()
            )
            return 4 if has_crisis_language else 3
        elif risk_level == "low" and composite >= 80:
            return 1
        else:
            return 2