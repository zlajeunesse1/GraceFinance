"""
Stream 1: Check-In Stream
===========================
Processes structured daily check-in responses into behavioral signals.

Reads from your EXISTING:
  - UserMetricSnapshot (FCS score, 5 dimensions, BSI)
  - CheckInResponse (raw answers)
  - checkin_service.FCS_WEIGHTS

Produces signals for:
  - FCS score level (critical / warning / healthy / excellent)
  - Individual dimension health
  - Dimension drops vs previous day
  - BSI stress level
  - Response quality indicators
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.models.checkin import UserMetricSnapshot, CheckInResponse
from app.services.checkin_service import FCS_WEIGHTS

from .signal_registry import Signal, SignalPolarity, SignalSeverity
from .config import EngineConfig, DEFAULT_CONFIG


# Dimension metadata for readable labels
DIMENSION_LABELS = {
    "current_stability": "Current Stability",
    "future_outlook": "Future Outlook",
    "purchasing_power": "Purchasing Power",
    "debt_pressure": "Debt Pressure",
    "financial_freedom": "Financial Freedom",
}


class CheckinStream:
    """
    Stream 1: Converts structured check-in data into behavioral signals.
    Runs after every check-in submission.
    """

    def __init__(self, config: EngineConfig = DEFAULT_CONFIG):
        self.config = config

    def process(self, db: Session, user_id: int) -> List[Signal]:
        """
        Main entry point. Reads latest snapshot + history,
        produces all check-in-derived signals.
        """
        signals: List[Signal] = []

        # Get latest snapshot
        latest = self._get_latest_snapshot(db, user_id)
        if not latest:
            return signals

        # Get previous day's snapshot for comparison
        previous = self._get_previous_snapshot(db, user_id, latest.snapshot_date)

        # 1. FCS Level Signal
        signals.append(self._score_fcs_level(latest))

        # 2. Individual Dimension Signals
        signals.extend(self._score_dimensions(latest))

        # 3. Dimension Drop Detection (vs previous day)
        if previous:
            signals.extend(self._detect_dimension_drops(latest, previous))

        # 4. BSI Stress Signal
        if latest.bsi_score is not None:
            signals.append(self._score_bsi(latest))

        # 5. Response Completeness Signal
        signals.append(self._score_completeness(db, user_id, latest.snapshot_date))

        return signals

    # ----------------------------------------------------------
    #  FCS LEVEL
    # ----------------------------------------------------------

    def _score_fcs_level(self, snapshot: UserMetricSnapshot) -> Signal:
        """Classify overall FCS score into a signal."""
        fcs = float(snapshot.fcs_composite)

        if fcs < self.config.fcs_critical_threshold:
            return Signal(
                key="fcs_critical",
                stream="checkin",
                polarity=SignalPolarity.NEGATIVE,
                severity=SignalSeverity.CRITICAL,
                value=fcs,
                confidence=0.95,
                label="Financial confidence is critically low",
                detail=f"FCS score is {fcs:.1f}/100 — below the {self.config.fcs_critical_threshold} crisis threshold.",
                coaching_hook="Open with empathy. Acknowledge this is hard. Focus on ONE small win they can achieve today.",
            )
        elif fcs < self.config.fcs_warning_threshold:
            return Signal(
                key="fcs_warning",
                stream="checkin",
                polarity=SignalPolarity.NEGATIVE,
                severity=SignalSeverity.MEDIUM,
                value=fcs,
                confidence=0.90,
                label="Financial confidence needs attention",
                detail=f"FCS score is {fcs:.1f}/100 — below the warning threshold.",
                coaching_hook="Identify the weakest dimension and give one actionable tip for it.",
            )
        elif fcs >= self.config.fcs_excellent_threshold:
            return Signal(
                key="fcs_excellent",
                stream="checkin",
                polarity=SignalPolarity.POSITIVE,
                severity=SignalSeverity.LOW,
                value=fcs,
                confidence=0.90,
                label="Financial confidence is excellent",
                detail=f"FCS score is {fcs:.1f}/100 — outstanding.",
                coaching_hook="Celebrate this. Then suggest a stretch goal to keep momentum.",
            )
        else:
            return Signal(
                key="fcs_healthy",
                stream="checkin",
                polarity=SignalPolarity.POSITIVE,
                severity=SignalSeverity.LOW,
                value=fcs,
                confidence=0.85,
                label="Financial confidence is healthy",
                detail=f"FCS score is {fcs:.1f}/100 — solid foundation.",
                coaching_hook="Reinforce what's working. Identify next growth area.",
            )

    # ----------------------------------------------------------
    #  INDIVIDUAL DIMENSIONS
    # ----------------------------------------------------------

    def _score_dimensions(self, snapshot: UserMetricSnapshot) -> List[Signal]:
        """Score each FCS dimension independently."""
        signals = []

        dimensions = {
            "current_stability": snapshot.dim_current_stability,
            "future_outlook": snapshot.dim_future_outlook,
            "purchasing_power": snapshot.dim_purchasing_power,
            "debt_pressure": snapshot.dim_debt_pressure,
            "financial_freedom": snapshot.dim_financial_freedom,
        }

        for dim_key, value in dimensions.items():
            if value is None:
                continue

            score = float(value)
            label = DIMENSION_LABELS.get(dim_key, dim_key)
            weight = FCS_WEIGHTS.get(dim_key, 0.20)

            if score < 30:
                signals.append(Signal(
                    key=f"dim_{dim_key}_critical",
                    stream="checkin",
                    polarity=SignalPolarity.NEGATIVE,
                    severity=SignalSeverity.HIGH,
                    value=score,
                    confidence=0.90,
                    label=f"{label} is critically low ({score:.0f}/100)",
                    detail=f"{label} scored {score:.0f}/100 (weight: {weight:.0%} of FCS).",
                    dimension=dim_key,
                    coaching_hook=f"Focus coaching on {label}. This is dragging their FCS down the most.",
                ))
            elif score < 50:
                signals.append(Signal(
                    key=f"dim_{dim_key}_low",
                    stream="checkin",
                    polarity=SignalPolarity.NEGATIVE,
                    severity=SignalSeverity.MEDIUM,
                    value=score,
                    confidence=0.85,
                    label=f"{label} needs work ({score:.0f}/100)",
                    detail=f"{label} scored {score:.0f}/100.",
                    dimension=dim_key,
                    coaching_hook=f"Suggest one specific action to improve {label}.",
                ))
            elif score >= 80:
                signals.append(Signal(
                    key=f"dim_{dim_key}_strong",
                    stream="checkin",
                    polarity=SignalPolarity.POSITIVE,
                    severity=SignalSeverity.LOW,
                    value=score,
                    confidence=0.85,
                    label=f"{label} is a strength ({score:.0f}/100)",
                    detail=f"{label} scored {score:.0f}/100 — above average.",
                    dimension=dim_key,
                    coaching_hook=f"Acknowledge {label} as a strength. Use it to build confidence in weaker areas.",
                ))

        return signals

    # ----------------------------------------------------------
    #  DIMENSION DROP DETECTION
    # ----------------------------------------------------------

    def _detect_dimension_drops(
        self, current: UserMetricSnapshot, previous: UserMetricSnapshot
    ) -> List[Signal]:
        """Detect significant single-day drops in any dimension."""
        signals = []

        dim_pairs = [
            ("current_stability", current.dim_current_stability, previous.dim_current_stability),
            ("future_outlook", current.dim_future_outlook, previous.dim_future_outlook),
            ("purchasing_power", current.dim_purchasing_power, previous.dim_purchasing_power),
            ("debt_pressure", current.dim_debt_pressure, previous.dim_debt_pressure),
            ("financial_freedom", current.dim_financial_freedom, previous.dim_financial_freedom),
        ]

        for dim_key, curr_val, prev_val in dim_pairs:
            if curr_val is None or prev_val is None:
                continue

            curr = float(curr_val)
            prev = float(prev_val)
            drop = prev - curr
            label = DIMENSION_LABELS.get(dim_key, dim_key)

            if drop >= self.config.dimension_drop_critical:
                signals.append(Signal(
                    key=f"dim_{dim_key}_crash",
                    stream="checkin",
                    polarity=SignalPolarity.NEGATIVE,
                    severity=SignalSeverity.CRITICAL,
                    value=drop,
                    confidence=0.95,
                    label=f"{label} crashed {drop:.0f} points in one day",
                    detail=f"{label} dropped from {prev:.0f} to {curr:.0f} ({drop:.0f}pt drop).",
                    dimension=dim_key,
                    coaching_hook=f"Something happened with {label}. Ask what changed. Lead with empathy.",
                ))
            elif drop >= self.config.dimension_drop_alert:
                signals.append(Signal(
                    key=f"dim_{dim_key}_drop",
                    stream="checkin",
                    polarity=SignalPolarity.NEGATIVE,
                    severity=SignalSeverity.HIGH,
                    value=drop,
                    confidence=0.85,
                    label=f"{label} dropped {drop:.0f} points",
                    detail=f"{label} went from {prev:.0f} to {curr:.0f}.",
                    dimension=dim_key,
                    coaching_hook=f"Gently explore why {label} dipped. Don't alarm them.",
                ))

        return signals

    # ----------------------------------------------------------
    #  BSI STRESS
    # ----------------------------------------------------------

    def _score_bsi(self, snapshot: UserMetricSnapshot) -> Signal:
        """Score BSI stress level."""
        bsi = float(snapshot.bsi_score)

        if bsi >= self.config.bsi_critical_threshold:
            return Signal(
                key="bsi_critical",
                stream="checkin",
                polarity=SignalPolarity.NEGATIVE,
                severity=SignalSeverity.CRITICAL,
                value=bsi,
                confidence=0.90,
                label="Behavioral stress is critically high",
                detail=f"BSI score is {bsi:.1f}/100 — well above normal.",
                coaching_hook="Their behavior shows high stress. Don't lecture. Ask how they're feeling first.",
            )
        elif bsi >= self.config.bsi_stress_threshold:
            return Signal(
                key="bsi_elevated",
                stream="checkin",
                polarity=SignalPolarity.NEGATIVE,
                severity=SignalSeverity.MEDIUM,
                value=bsi,
                confidence=0.85,
                label="Behavioral stress is elevated",
                detail=f"BSI score is {bsi:.1f}/100 — above the stress threshold.",
                coaching_hook="Stress is building. Help them identify one stress-spending trigger.",
            )
        else:
            return Signal(
                key="bsi_normal",
                stream="checkin",
                polarity=SignalPolarity.POSITIVE,
                severity=SignalSeverity.LOW,
                value=bsi,
                confidence=0.80,
                label="Behavioral stress is manageable",
                detail=f"BSI score is {bsi:.1f}/100 — within normal range.",
            )

    # ----------------------------------------------------------
    #  RESPONSE COMPLETENESS
    # ----------------------------------------------------------

    def _score_completeness(
        self, db: Session, user_id: int, snapshot_date
    ) -> Signal:
        """Check if user answered enough questions for reliable scoring."""
        count = (
            db.query(CheckInResponse)
            .filter(
                and_(
                    CheckInResponse.user_id == user_id,
                    CheckInResponse.checkin_date == snapshot_date,
                    CheckInResponse.dimension != "conversation_theme",
                )
            )
            .count()
        )

        if count >= self.config.min_responses_for_valid_fcs:
            return Signal(
                key="checkin_complete",
                stream="checkin",
                polarity=SignalPolarity.POSITIVE,
                severity=SignalSeverity.LOW,
                value=min(100.0, (count / self.config.min_responses_for_valid_fcs) * 100),
                confidence=0.95,
                label=f"Check-in complete ({count} responses)",
                detail=f"User answered {count} questions today.",
            )
        else:
            return Signal(
                key="checkin_incomplete",
                stream="checkin",
                polarity=SignalPolarity.NEUTRAL,
                severity=SignalSeverity.LOW,
                value=(count / self.config.min_responses_for_valid_fcs) * 100,
                confidence=0.70,
                label=f"Check-in incomplete ({count}/{self.config.min_responses_for_valid_fcs})",
                detail="Partial data — FCS score may be less reliable today.",
                coaching_hook="Encourage them to complete tomorrow's check-in fully.",
            )

    # ----------------------------------------------------------
    #  HELPERS
    # ----------------------------------------------------------

    def _get_latest_snapshot(
        self, db: Session, user_id: int
    ) -> Optional[UserMetricSnapshot]:
        """Get the most recent metric snapshot."""
        return (
            db.query(UserMetricSnapshot)
            .filter(UserMetricSnapshot.user_id == user_id)
            .order_by(desc(UserMetricSnapshot.snapshot_date))
            .first()
        )

    def _get_previous_snapshot(
        self, db: Session, user_id: int, current_date
    ) -> Optional[UserMetricSnapshot]:
        """Get the snapshot before the current one."""
        return (
            db.query(UserMetricSnapshot)
            .filter(
                and_(
                    UserMetricSnapshot.user_id == user_id,
                    UserMetricSnapshot.snapshot_date < current_date,
                )
            )
            .order_by(desc(UserMetricSnapshot.snapshot_date))
            .first()
        )