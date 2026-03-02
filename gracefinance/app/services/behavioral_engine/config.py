"""
Behavioral Engine Configuration
=================================
Every threshold, weight, and tuning knob lives here.
Change behavior without touching logic.

When you have real user data, this is what you tune.
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class EngineConfig:
    """Central configuration for the 3-stream behavioral engine."""

    # ==========================================================
    #  STREAM WEIGHTS — How much each stream contributes to the
    #  composite behavioral score. Must sum to 1.0.
    # ==========================================================
    stream_weights: Dict[str, float] = field(default_factory=lambda: {
        "checkin": 0.50,    # Structured data — most reliable
        "pulse": 0.30,      # Pattern detection — high signal
        "nlp": 0.20,        # Conversation themes — supplementary
    })

    # ==========================================================
    #  STREAM 1: CHECK-IN THRESHOLDS
    #  Maps to your existing FCS_WEIGHTS in checkin_service.py
    # ==========================================================

    # Minimum responses needed for a valid daily FCS score
    min_responses_for_valid_fcs: int = 3

    # Score boundaries (0-100 scale)
    fcs_critical_threshold: float = 30.0      # Below = crisis coaching mode
    fcs_warning_threshold: float = 50.0       # Below = proactive nudges
    fcs_healthy_threshold: float = 70.0       # Above = positive reinforcement
    fcs_excellent_threshold: float = 85.0     # Above = celebrate + stretch goals

    # Dimension drop detection (percentage points)
    dimension_drop_alert: float = 15.0        # Single-day dimension drop
    dimension_drop_critical: float = 25.0     # Emergency-level drop

    # ==========================================================
    #  STREAM 2: BEHAVIORAL PULSE THRESHOLDS
    #  Pattern detection across check-in time series
    # ==========================================================

    # Trend detection windows (days)
    trend_window_short: int = 3               # Short-term trend
    trend_window_medium: int = 7              # Medium-term trend
    trend_window_long: int = 14               # Long-term trend

    # FCS decline detection
    fcs_decline_days: int = 3                 # Consecutive decline days to flag
    fcs_decline_min_drop: float = 5.0         # Min total drop over decline period

    # BSI thresholds
    bsi_stress_threshold: float = 60.0        # BSI above this = stress signal
    bsi_critical_threshold: float = 75.0      # BSI above this = high stress

    # Impulse spending
    impulse_rate_warning: float = 0.30        # 30%+ check-ins with impulse = warning
    impulse_rate_critical: float = 0.50       # 50%+ = critical

    # Mood-spend correlation
    mood_spend_gap_warning: float = 75.0      # $75+ more when stressed
    mood_spend_gap_critical: float = 200.0    # $200+ more when stressed

    # Variance/instability
    fcs_variance_warning: float = 12.0        # Std dev of FCS over 7 days
    fcs_variance_critical: float = 20.0       # Highly unstable

    # Streak thresholds
    streak_milestone_early: int = 3           # First milestone
    streak_milestone_weekly: int = 7          # Weekly milestone
    streak_milestone_biweekly: int = 14       # Two-week milestone
    streak_milestone_monthly: int = 30        # Monthly milestone

    # ==========================================================
    #  STREAM 3: NLP EXTRACTION CONFIG
    #  Rule-based keyword/theme detection from Grace conversations
    # ==========================================================

    # Minimum keyword matches to register a theme
    nlp_min_matches_for_theme: int = 1

    # Confidence boost per additional keyword match (0-1 scale)
    nlp_confidence_per_match: float = 0.25

    # Maximum confidence cap
    nlp_max_confidence: float = 1.0

    # Conversation recency weight (days)
    nlp_theme_recency_window: int = 7         # How far back themes stay relevant

    # ==========================================================
    #  COMPOSITE SCORING
    # ==========================================================

    # Minimum data points for reliable composite
    min_checkins_for_composite: int = 3
    min_pulse_days_for_composite: int = 3
    min_conversations_for_nlp: int = 1

    # When a stream has insufficient data, redistribute its weight
    redistribute_missing_weight: bool = True

    # ==========================================================
    #  INDEX FEEDER — Data quality for GF-RWI
    # ==========================================================

    # Minimum completion time (seconds) to trust a check-in
    min_completion_time_seconds: float = 15.0

    # Maximum completion time before suspecting AFK
    max_completion_time_seconds: float = 600.0

    # Response consistency — flag if all answers are identical
    flag_uniform_responses: bool = True

    # Minimum quality score (0-1) for index inclusion
    min_quality_score_for_index: float = 0.4

    # Quality score weights
    quality_weight_completion: float = 0.30   # Did they finish the check-in?
    quality_weight_time: float = 0.25         # Reasonable completion time?
    quality_weight_variance: float = 0.25     # Non-uniform answers?
    quality_weight_consistency: float = 0.20  # Consistent with their history?

    def validate(self) -> bool:
        """Verify config integrity."""
        weight_sum = sum(self.stream_weights.values())
        assert abs(weight_sum - 1.0) < 0.001, f"Stream weights must sum to 1.0, got {weight_sum}"

        quality_sum = (
            self.quality_weight_completion
            + self.quality_weight_time
            + self.quality_weight_variance
            + self.quality_weight_consistency
        )
        assert abs(quality_sum - 1.0) < 0.001, f"Quality weights must sum to 1.0, got {quality_sum}"

        return True


# Singleton default config — import this everywhere
DEFAULT_CONFIG = EngineConfig()