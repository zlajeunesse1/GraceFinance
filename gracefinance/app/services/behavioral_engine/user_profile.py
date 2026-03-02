"""
User Profile Builder
======================
Orchestrates all 3 streams, the composite scorer, and pattern detector
into a complete behavioral profile for a single user.

This is the main entry point that the rest of your app calls.
Replace direct calls to individual streams with this.

USAGE:
    from app.services.behavioral_engine import UserProfileBuilder

    builder = UserProfileBuilder()
    profile = builder.build(db, user_id, messages=conversation_messages)

    # For Grace's context:
    grace_context = profile.to_grace_context()

    # For the dashboard API:
    dashboard_data = profile.to_dict()

    # For index feeding:
    index_data = profile.for_index()
"""

from datetime import datetime, timezone
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from sqlalchemy.orm import Session

from .config import EngineConfig, DEFAULT_CONFIG
from .signal_registry import SignalRegistry
from .stream_checkin import CheckinStream
from .stream_pulse import BehavioralPulseStream
from .stream_nlp import GraceNLPStream
from .composite_scorer import CompositeScorer, CompositeResult
from .pattern_detector import PatternDetector, CrossStreamPattern


@dataclass
class UserBehavioralProfile:
    """Complete behavioral profile for a single user at a point in time."""

    user_id: int
    generated_at: str

    # Composite result
    composite: CompositeResult

    # Cross-stream patterns
    patterns: List[CrossStreamPattern]

    # Full signal registry (for deep inspection)
    registry: SignalRegistry

    # NLP themes detected (for conversation logging)
    nlp_themes: List[Dict]

    def to_dict(self) -> dict:
        """Full profile for API / dashboard."""
        return {
            "user_id": self.user_id,
            "generated_at": self.generated_at,
            "composite": self.composite.to_dict(),
            "patterns": [p.to_dict() for p in self.patterns],
            "signal_summary": self.registry.overall_signal_count(),
            "nlp_themes": self.nlp_themes,
        }

    def to_grace_context(self) -> str:
        """
        Build a complete context block for Grace's system prompt.
        Combines signal briefing + pattern context + coaching intensity.
        """
        lines = []

        # Coaching intensity header
        intensity_labels = {
            1: "LIGHT TOUCH — celebrate wins, maintain momentum",
            2: "SUPPORTIVE — gentle nudges, encouragement",
            3: "ACTIVE COACHING — specific tips, action items",
            4: "INTENSIVE — structured plans, daily focus",
            5: "CRISIS MODE — empathy first, minimal advice, listen",
        }
        intensity = self.composite.coaching_intensity
        lines.append(f"\n[COACHING MODE: Level {intensity} — {intensity_labels.get(intensity, 'Active')}]")
        lines.append(f"[COMPOSITE BEHAVIORAL SCORE: {self.composite.composite_score:.1f}/100]")
        lines.append(f"[RISK LEVEL: {self.composite.risk_level.upper()}]")

        # Signal briefing
        briefing = self.registry.build_grace_briefing()
        if briefing:
            lines.append(f"\n{briefing}")

        # Cross-stream patterns
        pattern_detector = PatternDetector()
        pattern_context = pattern_detector.build_pattern_context(self.patterns)
        if pattern_context:
            lines.append(pattern_context)

        # Top concerns and strengths summary
        if self.composite.top_concerns:
            lines.append("\n[TOP CONCERNS TO ADDRESS]")
            for c in self.composite.top_concerns[:3]:
                lines.append(f"  • {c}")

        if self.composite.top_strengths:
            lines.append("\n[STRENGTHS TO LEVERAGE]")
            for s in self.composite.top_strengths[:3]:
                lines.append(f"  ✓ {s}")

        return "\n".join(lines)

    def for_index(self) -> Dict:
        """
        Extract data needed for GF-RWI index computation.
        Used by index_feeder.py.
        """
        return {
            "user_id": self.user_id,
            "composite_score": self.composite.composite_score,
            "checkin_score": self.composite.checkin_score,
            "pulse_score": self.composite.pulse_score,
            "nlp_score": self.composite.nlp_score,
            "risk_level": self.composite.risk_level,
            "signal_count": self.composite.total_signals,
            "critical_count": self.composite.critical_count,
            "generated_at": self.generated_at,
        }


class UserProfileBuilder:
    """
    Orchestrator that runs all 3 streams and assembles the profile.
    This is what the rest of your app imports and calls.
    """

    def __init__(self, config: EngineConfig = DEFAULT_CONFIG):
        self.config = config
        self.checkin_stream = CheckinStream(config)
        self.pulse_stream = BehavioralPulseStream(config)
        self.nlp_stream = GraceNLPStream(config)
        self.composite_scorer = CompositeScorer(config)
        self.pattern_detector = PatternDetector(config)

    def build(
        self,
        db: Session,
        user_id: int,
        messages: Optional[List[Dict[str, str]]] = None,
    ) -> UserBehavioralProfile:
        """
        Build a complete behavioral profile for a user.

        Args:
            db: Database session
            user_id: The user to profile
            messages: Optional Grace conversation messages for NLP stream.
                      If None, NLP stream is skipped (weight redistributed).

        Returns:
            UserBehavioralProfile with all scores, patterns, and coaching context.
        """
        # Fresh registry for this processing cycle
        registry = SignalRegistry()

        # ---- STREAM 1: CHECK-IN ----
        checkin_signals = self.checkin_stream.process(db, user_id)
        registry.register_many(checkin_signals)

        # ---- STREAM 2: BEHAVIORAL PULSE ----
        pulse_signals = self.pulse_stream.process(db, user_id)
        registry.register_many(pulse_signals)

        # ---- STREAM 3: NLP (if conversation provided) ----
        nlp_themes = []
        if messages:
            nlp_signals = self.nlp_stream.process(messages)
            registry.register_many(nlp_signals)

            # Extract themes for conversation logging
            user_text = " ".join(
                m["content"] for m in messages
                if m.get("role") == "user" and m.get("content")
            )
            if user_text:
                nlp_themes = self.nlp_stream.extract_themes(user_text)

        # ---- COMPOSITE SCORING ----
        composite = self.composite_scorer.score(registry)

        # ---- CROSS-STREAM PATTERN DETECTION ----
        patterns = self.pattern_detector.detect(registry)

        return UserBehavioralProfile(
            user_id=user_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            composite=composite,
            patterns=patterns,
            registry=registry,
            nlp_themes=nlp_themes,
        )

    def build_quick(self, db: Session, user_id: int) -> UserBehavioralProfile:
        """
        Quick profile without NLP stream (for non-conversation contexts
        like dashboard loads, notification triggers, etc.)
        """
        return self.build(db, user_id, messages=None)