"""
Signal Registry
=================================
Central catalog of every behavioral signal the engine can detect.

Each signal has:
  - A unique key
  - The stream it comes from (checkin / pulse / nlp)
  - A weight for composite scoring
  - A polarity (positive / negative / neutral)
  - A human-readable label for Grace's coaching

This is the source of truth. When you add a new signal to any stream,
register it here first.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal
from enum import Enum


class SignalPolarity(str, Enum):
    POSITIVE = "positive"     # Good for the user (high confidence, streak, etc.)
    NEGATIVE = "negative"     # Bad for the user (stress spike, impulse spending)
    NEUTRAL = "neutral"       # Informational only (theme detected, no judgment)


class SignalSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Signal:
    """A single behavioral signal detected by any stream."""

    key: str                                    # Unique identifier
    stream: Literal["checkin", "pulse", "nlp"]  # Which stream produced it
    polarity: SignalPolarity                     # Good, bad, or neutral
    severity: SignalSeverity                     # How urgent
    value: float                                # Numeric value (0-100 scale)
    confidence: float                           # How confident we are (0-1)
    label: str                                  # Human-readable for Grace
    detail: str = ""                            # Extended explanation
    dimension: Optional[str] = None             # FCS dimension if applicable
    coaching_hook: str = ""                     # Suggested Grace coaching angle
    timestamp: Optional[str] = None             # When this was detected

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "stream": self.stream,
            "polarity": self.polarity.value,
            "severity": self.severity.value,
            "value": self.value,
            "confidence": self.confidence,
            "label": self.label,
            "detail": self.detail,
            "dimension": self.dimension,
            "coaching_hook": self.coaching_hook,
        }


class SignalRegistry:
    """
    Central registry that collects signals from all 3 streams
    and provides unified access for scoring and coaching.
    """

    def __init__(self):
        self._signals: List[Signal] = []

    def register(self, signal: Signal) -> None:
        """Add a signal to the registry."""
        self._signals.append(signal)

    def register_many(self, signals: List[Signal]) -> None:
        """Add multiple signals at once."""
        self._signals.extend(signals)

    def clear(self) -> None:
        """Reset for a new processing cycle."""
        self._signals.clear()

    # ----------------------------------------------------------
    #  QUERY METHODS
    # ----------------------------------------------------------

    def all(self) -> List[Signal]:
        """All signals, sorted by severity (critical first)."""
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        return sorted(
            self._signals,
            key=lambda s: severity_order.get(s.severity.value, 4),
        )

    def by_stream(self, stream: str) -> List[Signal]:
        """All signals from a specific stream."""
        return [s for s in self._signals if s.stream == stream]

    def by_polarity(self, polarity: SignalPolarity) -> List[Signal]:
        """All signals with a specific polarity."""
        return [s for s in self._signals if s.polarity == polarity]

    def by_severity(self, severity: SignalSeverity) -> List[Signal]:
        """All signals at a specific severity level."""
        return [s for s in self._signals if s.severity == severity]

    def by_dimension(self, dimension: str) -> List[Signal]:
        """All signals related to a specific FCS dimension."""
        return [s for s in self._signals if s.dimension == dimension]

    def negative_signals(self) -> List[Signal]:
        """All warning/concern signals, sorted by severity."""
        return [s for s in self.all() if s.polarity == SignalPolarity.NEGATIVE]

    def positive_signals(self) -> List[Signal]:
        """All positive/encouraging signals."""
        return [s for s in self.all() if s.polarity == SignalPolarity.POSITIVE]

    def critical_alerts(self) -> List[Signal]:
        """Only critical-severity signals — needs immediate coaching."""
        return self.by_severity(SignalSeverity.CRITICAL)

    def coaching_hooks(self) -> List[str]:
        """All coaching hooks from negative signals for Grace's context."""
        return [
            s.coaching_hook
            for s in self.negative_signals()
            if s.coaching_hook
        ]

    # ----------------------------------------------------------
    #  AGGREGATE METRICS
    # ----------------------------------------------------------

    def stream_health_score(self, stream: str) -> float:
        """
        Compute a 0-100 health score for a stream based on its signals.
        More positive signals + fewer negative = higher score.
        """
        stream_signals = self.by_stream(stream)
        if not stream_signals:
            return 50.0  # Neutral when no data

        positive_sum = sum(
            s.value * s.confidence
            for s in stream_signals
            if s.polarity == SignalPolarity.POSITIVE
        )
        negative_sum = sum(
            s.value * s.confidence
            for s in stream_signals
            if s.polarity == SignalPolarity.NEGATIVE
        )

        total_weight = sum(s.confidence for s in stream_signals)
        if total_weight == 0:
            return 50.0

        # Normalize: positive pushes toward 100, negative toward 0
        raw = (positive_sum - negative_sum) / total_weight
        # Map from [-100, 100] to [0, 100]
        return max(0.0, min(100.0, 50.0 + (raw / 2.0)))

    def overall_signal_count(self) -> Dict[str, int]:
        """Count signals by stream and polarity."""
        counts = {
            "total": len(self._signals),
            "checkin": len(self.by_stream("checkin")),
            "pulse": len(self.by_stream("pulse")),
            "nlp": len(self.by_stream("nlp")),
            "positive": len(self.positive_signals()),
            "negative": len(self.negative_signals()),
            "critical": len(self.critical_alerts()),
        }
        return counts

    def build_grace_briefing(self) -> str:
        """
        Build a concise text block for Grace's system prompt context.
        Prioritizes critical alerts, then negatives, then positives.
        """
        lines = []

        critical = self.critical_alerts()
        if critical:
            lines.append("[CRITICAL ALERTS]")
            for s in critical[:3]:
                lines.append(f"  ⚠ {s.label}: {s.detail}")
                if s.coaching_hook:
                    lines.append(f"    → Coach: {s.coaching_hook}")

        negatives = [
            s for s in self.negative_signals()
            if s.severity != SignalSeverity.CRITICAL
        ]
        if negatives:
            lines.append("[CONCERNS]")
            for s in negatives[:5]:
                lines.append(f"  • {s.label}: {s.detail}")
                if s.coaching_hook:
                    lines.append(f"    → Coach: {s.coaching_hook}")

        positives = self.positive_signals()
        if positives:
            lines.append("[STRENGTHS]")
            for s in positives[:3]:
                lines.append(f"  ✓ {s.label}: {s.detail}")

        return "\n".join(lines) if lines else "[No behavioral signals detected yet]"