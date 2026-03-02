"""
GraceFinance 3-Stream Behavioral Engine
=========================================
Core data intelligence powering user coaching + GF-RWI institutional data.

THREE STREAMS (all pure Python, zero extra API costs):
  1. CHECK-IN STREAM   — Structured daily responses → FCS dimension scores
  2. BEHAVIORAL PULSE  — Rule-based pattern detection across time series
  3. GRACE NLP STREAM  — Keyword/theme extraction from Grace conversations

PLACEMENT: app/services/behavioral_engine/

IMPORTS FROM YOUR EXISTING CODE:
  - app.models.checkin (CheckInResponse, UserMetricSnapshot, DailyIndex)
  - app.services.checkin_service (FCS_WEIGHTS, get_user_metric_history)
  - app.services.index_engine_service (get_latest_index)
  - app.services.question_bank (QUESTION_BANK)
"""

from .config import EngineConfig
from .signal_registry import SignalRegistry, Signal
from .stream_checkin import CheckinStream
from .stream_pulse import BehavioralPulseStream
from .stream_nlp import GraceNLPStream
from .composite_scorer import CompositeScorer
from .pattern_detector import PatternDetector
from .user_profile import UserProfileBuilder
from .index_feeder import IndexFeeder

__all__ = [
    "EngineConfig",
    "SignalRegistry",
    "Signal",
    "CheckinStream",
    "BehavioralPulseStream",
    "GraceNLPStream",
    "CompositeScorer",
    "PatternDetector",
    "UserProfileBuilder",
    "IndexFeeder",
]