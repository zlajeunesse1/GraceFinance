"""
Stream 2: Behavioral Pulse
============================
Rule-based pattern detection across check-in time series.
This is where the engine gets smart — detecting trends, correlations,
and behavioral shifts that users can't see themselves.

Reads from your EXISTING:
  - UserMetricSnapshot (time series of FCS + dimensions)
  - CheckInResponse (raw answers for impulse/mood/spend analysis)

Detects:
  - FCS decline streaks (3+ days down)
  - Dimension instability (high variance)
  - Impulse spending rate trends
  - Mood-spend correlation (stress → overspend)
  - Positive momentum (improving trends)
  - Streak health (engagement consistency)
  - Weekend vs weekday behavioral shifts
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from decimal import Decimal
from statistics import mean, stdev
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from app.models.checkin import UserMetricSnapshot, CheckInResponse

from .signal_registry import Signal, SignalPolarity, SignalSeverity
from .config import EngineConfig, DEFAULT_CONFIG


class BehavioralPulseStream:
    """
    Stream 2: Analyzes behavioral patterns over time.
    Runs after each check-in or on-demand for Grace context building.
    """

    def __init__(self, config: EngineConfig = DEFAULT_CONFIG):
        self.config = config

    def process(self, db: Session, user_id: int) -> List[Signal]:
        """
        Main entry point. Analyzes check-in history for patterns.
        Returns behavioral signals detected.
        """
        signals: List[Signal] = []

        # Load time series data
        snapshots = self._get_snapshot_history(
            db, user_id, days=self.config.trend_window_long
        )
        if len(snapshots) < self.config.min_pulse_days_for_composite:
            return [Signal(
                key="pulse_insufficient_data",
                stream="pulse",
                polarity=SignalPolarity.NEUTRAL,
                severity=SignalSeverity.LOW,
                value=len(snapshots),
                confidence=0.50,
                label=f"Only {len(snapshots)} days of data — need {self.config.min_pulse_days_for_composite}+ for patterns",
                detail="Keep checking in daily. Patterns will emerge in a few days.",
                coaching_hook="Encourage daily check-ins. The more data, the better the coaching gets.",
            )]

        # Run all pattern detectors
        signals.extend(self._detect_fcs_decline(snapshots))
        signals.extend(self._detect_fcs_instability(snapshots))
        signals.extend(self._detect_positive_momentum(snapshots))
        signals.extend(self._detect_impulse_trends(db, user_id))
        signals.extend(self._detect_mood_spend_correlation(db, user_id))
        signals.extend(self._detect_streak_health(snapshots))
        signals.extend(self._detect_weekday_weekend_shift(db, user_id))

        return signals

    # ----------------------------------------------------------
    #  FCS DECLINE DETECTION
    # ----------------------------------------------------------

    def _detect_fcs_decline(self, snapshots: List[UserMetricSnapshot]) -> List[Signal]:
        """Detect consecutive days of FCS decline."""
        signals = []
        if len(snapshots) < self.config.fcs_decline_days:
            return signals

        # Check last N days for consecutive decline
        recent = snapshots[: self.config.fcs_decline_days]
        fcs_values = [float(s.fcs_composite) for s in recent if s.fcs_composite is not None]

        if len(fcs_values) < self.config.fcs_decline_days:
            return signals

        # Check if each day is lower than the previous
        consecutive_declines = 0
        for i in range(len(fcs_values) - 1):
            if fcs_values[i] < fcs_values[i + 1]:  # Newest first
                consecutive_declines += 1
            else:
                break

        total_drop = fcs_values[-1] - fcs_values[0] if consecutive_declines > 0 else 0

        if consecutive_declines >= self.config.fcs_decline_days and abs(total_drop) >= self.config.fcs_decline_min_drop:
            signals.append(Signal(
                key="fcs_decline_streak",
                stream="pulse",
                polarity=SignalPolarity.NEGATIVE,
                severity=SignalSeverity.HIGH,
                value=abs(total_drop),
                confidence=0.90,
                label=f"FCS has dropped {abs(total_drop):.1f} points over {consecutive_declines} days",
                detail=f"Financial confidence went from {fcs_values[-1]:.1f} → {fcs_values[0]:.1f} over {consecutive_declines} consecutive days.",
                coaching_hook="Multi-day decline is concerning. Help them identify what changed. Don't pile on — find one stabilizer.",
            ))
        elif consecutive_declines >= 2:
            signals.append(Signal(
                key="fcs_declining",
                stream="pulse",
                polarity=SignalPolarity.NEGATIVE,
                severity=SignalSeverity.MEDIUM,
                value=abs(total_drop),
                confidence=0.75,
                label=f"FCS trending down ({consecutive_declines} days)",
                detail=f"Dropped {abs(total_drop):.1f} points over {consecutive_declines} days.",
                coaching_hook="Early decline signal. Proactively check in about what's happening.",
            ))

        return signals

    # ----------------------------------------------------------
    #  FCS INSTABILITY
    # ----------------------------------------------------------

    def _detect_fcs_instability(self, snapshots: List[UserMetricSnapshot]) -> List[Signal]:
        """Detect high variance in FCS scores (emotional volatility)."""
        signals = []

        # Use 7-day window
        window = snapshots[: self.config.trend_window_medium]
        fcs_values = [float(s.fcs_composite) for s in window if s.fcs_composite is not None]

        if len(fcs_values) < 3:
            return signals

        fcs_stdev = stdev(fcs_values)

        if fcs_stdev >= self.config.fcs_variance_critical:
            signals.append(Signal(
                key="fcs_highly_unstable",
                stream="pulse",
                polarity=SignalPolarity.NEGATIVE,
                severity=SignalSeverity.HIGH,
                value=fcs_stdev,
                confidence=0.85,
                label=f"Financial confidence is highly unstable (±{fcs_stdev:.1f} points)",
                detail=f"FCS swings of ±{fcs_stdev:.1f} over 7 days. Range: {min(fcs_values):.0f}–{max(fcs_values):.0f}.",
                coaching_hook="Big swings suggest reactive financial behavior. Help build consistency routines.",
            ))
        elif fcs_stdev >= self.config.fcs_variance_warning:
            signals.append(Signal(
                key="fcs_unstable",
                stream="pulse",
                polarity=SignalPolarity.NEGATIVE,
                severity=SignalSeverity.MEDIUM,
                value=fcs_stdev,
                confidence=0.75,
                label=f"FCS showing some volatility (±{fcs_stdev:.1f})",
                detail=f"Moderate swings over the past week.",
                coaching_hook="Some instability. Worth exploring what days feel different.",
            ))

        return signals

    # ----------------------------------------------------------
    #  POSITIVE MOMENTUM
    # ----------------------------------------------------------

    def _detect_positive_momentum(self, snapshots: List[UserMetricSnapshot]) -> List[Signal]:
        """Detect improving FCS trends — celebrate wins."""
        signals = []
        if len(snapshots) < 3:
            return signals

        recent_3 = [float(s.fcs_composite) for s in snapshots[:3] if s.fcs_composite is not None]
        if len(recent_3) < 3:
            return signals

        # Check for 3-day improvement (newest first, so values should be increasing)
        if recent_3[0] > recent_3[1] > recent_3[2]:
            gain = recent_3[0] - recent_3[2]
            signals.append(Signal(
                key="fcs_momentum_positive",
                stream="pulse",
                polarity=SignalPolarity.POSITIVE,
                severity=SignalSeverity.LOW,
                value=gain,
                confidence=0.80,
                label=f"3-day positive momentum (+{gain:.1f} points)",
                detail=f"FCS improved from {recent_3[2]:.1f} → {recent_3[0]:.1f} over 3 days.",
                coaching_hook="Celebrate this progress! Ask what they're doing differently.",
            ))

        # Check 7-day trend
        if len(snapshots) >= 7:
            recent_7 = [float(s.fcs_composite) for s in snapshots[:7] if s.fcs_composite is not None]
            if len(recent_7) >= 7:
                week_gain = recent_7[0] - recent_7[-1]
                if week_gain >= 10:
                    signals.append(Signal(
                        key="fcs_weekly_surge",
                        stream="pulse",
                        polarity=SignalPolarity.POSITIVE,
                        severity=SignalSeverity.MEDIUM,
                        value=week_gain,
                        confidence=0.85,
                        label=f"Strong weekly improvement (+{week_gain:.1f} points)",
                        detail=f"FCS up {week_gain:.1f} points over the past week. Major progress.",
                        coaching_hook="This is a big deal. Make them feel it. Reinforce the behaviors that got them here.",
                    ))

        return signals

    # ----------------------------------------------------------
    #  IMPULSE SPENDING TRENDS
    # ----------------------------------------------------------

    def _detect_impulse_trends(self, db: Session, user_id: int) -> List[Signal]:
        """Analyze impulse spending frequency over recent check-ins."""
        signals = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=14)

        # Count total check-in days and impulse-flagged days
        responses = (
            db.query(
                CheckInResponse.checkin_date,
                CheckInResponse.answer_value,
            )
            .filter(
                and_(
                    CheckInResponse.user_id == user_id,
                    CheckInResponse.dimension == "behavioral_shift",
                    CheckInResponse.checkin_date >= cutoff.date(),
                )
            )
            .all()
        )

        if not responses:
            return signals

        # Count days with impulse flags
        days_with_impulse = set()
        total_days = set()
        for r in responses:
            total_days.add(r.checkin_date)
            try:
                if float(r.answer_value) >= 7:  # High impulse score
                    days_with_impulse.add(r.checkin_date)
            except (ValueError, TypeError):
                continue

        if not total_days:
            return signals

        impulse_rate = len(days_with_impulse) / len(total_days)

        if impulse_rate >= self.config.impulse_rate_critical:
            signals.append(Signal(
                key="impulse_critical",
                stream="pulse",
                polarity=SignalPolarity.NEGATIVE,
                severity=SignalSeverity.HIGH,
                value=impulse_rate * 100,
                confidence=0.90,
                label=f"Impulse spending is dominant ({impulse_rate:.0%} of days)",
                detail=f"{len(days_with_impulse)} of {len(total_days)} days had impulse spending flags.",
                coaching_hook="Impulse spending is a pattern, not a slip. Explore the triggers without judgment.",
            ))
        elif impulse_rate >= self.config.impulse_rate_warning:
            signals.append(Signal(
                key="impulse_warning",
                stream="pulse",
                polarity=SignalPolarity.NEGATIVE,
                severity=SignalSeverity.MEDIUM,
                value=impulse_rate * 100,
                confidence=0.80,
                label=f"Impulse spending trending up ({impulse_rate:.0%} of days)",
                detail=f"Impulse flags on {len(days_with_impulse)} of {len(total_days)} recent days.",
                coaching_hook="Suggest the 24-hour rule: wait a day before any unplanned purchase over $20.",
            ))

        return signals

    # ----------------------------------------------------------
    #  MOOD-SPEND CORRELATION
    # ----------------------------------------------------------

    def _detect_mood_spend_correlation(self, db: Session, user_id: int) -> List[Signal]:
        """Detect if user spends more when stressed."""
        signals = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=14)

        # Get mood scores and spending amounts from check-in responses
        mood_responses = (
            db.query(CheckInResponse.checkin_date, CheckInResponse.answer_value)
            .filter(
                and_(
                    CheckInResponse.user_id == user_id,
                    CheckInResponse.dimension.in_(["current_stability", "future_outlook"]),
                    CheckInResponse.checkin_date >= cutoff.date(),
                )
            )
            .all()
        )

        spending_responses = (
            db.query(CheckInResponse.checkin_date, CheckInResponse.answer_value)
            .filter(
                and_(
                    CheckInResponse.user_id == user_id,
                    CheckInResponse.dimension == "purchasing_power",
                    CheckInResponse.checkin_date >= cutoff.date(),
                )
            )
            .all()
        )

        if not mood_responses or not spending_responses:
            return signals

        # Build daily averages
        mood_by_day = {}
        for r in mood_responses:
            try:
                val = float(r.answer_value)
                if r.checkin_date not in mood_by_day:
                    mood_by_day[r.checkin_date] = []
                mood_by_day[r.checkin_date].append(val)
            except (ValueError, TypeError):
                continue

        spend_by_day = {}
        for r in spending_responses:
            try:
                val = float(r.answer_value)
                if r.checkin_date not in spend_by_day:
                    spend_by_day[r.checkin_date] = []
                spend_by_day[r.checkin_date].append(val)
            except (ValueError, TypeError):
                continue

        # Compare high-mood days vs low-mood days spending
        low_mood_spend = []
        high_mood_spend = []

        for day in mood_by_day:
            if day not in spend_by_day:
                continue
            avg_mood = mean(mood_by_day[day])
            avg_spend = mean(spend_by_day[day])

            if avg_mood <= 4:  # Low mood / high stress
                low_mood_spend.append(avg_spend)
            elif avg_mood >= 7:  # Good mood
                high_mood_spend.append(avg_spend)

        if low_mood_spend and high_mood_spend:
            gap = mean(low_mood_spend) - mean(high_mood_spend)

            if gap >= self.config.mood_spend_gap_critical:
                signals.append(Signal(
                    key="mood_spend_critical",
                    stream="pulse",
                    polarity=SignalPolarity.NEGATIVE,
                    severity=SignalSeverity.HIGH,
                    value=gap,
                    confidence=0.85,
                    label=f"Stress spending is significant (+{gap:.0f} pts on bad days)",
                    detail=f"Spending scores are {gap:.1f} points higher on stressed days vs calm days.",
                    coaching_hook="Stress is costing them. Help them see the pattern without blame.",
                ))
            elif gap >= self.config.mood_spend_gap_warning:
                signals.append(Signal(
                    key="mood_spend_warning",
                    stream="pulse",
                    polarity=SignalPolarity.NEGATIVE,
                    severity=SignalSeverity.MEDIUM,
                    value=gap,
                    confidence=0.75,
                    label=f"Mood-linked spending detected (+{gap:.0f} pts on stressed days)",
                    detail=f"Spending edges up on low-mood days.",
                    coaching_hook="Ask if they notice spending differently when stressed. Build awareness.",
                ))

        return signals

    # ----------------------------------------------------------
    #  STREAK HEALTH
    # ----------------------------------------------------------

    def _detect_streak_health(self, snapshots: List[UserMetricSnapshot]) -> List[Signal]:
        """Analyze check-in streak for engagement signals."""
        signals = []
        if not snapshots:
            return signals

        # Count consecutive days from most recent
        streak = 0
        today = datetime.now(timezone.utc).date()

        for i, snapshot in enumerate(snapshots):
            expected_date = today - timedelta(days=i)
            if snapshot.snapshot_date == expected_date:
                streak += 1
            else:
                break

        # Streak milestones
        if streak >= self.config.streak_milestone_monthly:
            signals.append(Signal(
                key="streak_monthly",
                stream="pulse",
                polarity=SignalPolarity.POSITIVE,
                severity=SignalSeverity.HIGH,
                value=streak,
                confidence=0.95,
                label=f"🔥 {streak}-day check-in streak!",
                detail=f"A full month of daily engagement. Top-tier commitment.",
                coaching_hook="This is elite. Celebrate hard. They're in the top percentile of users.",
            ))
        elif streak >= self.config.streak_milestone_biweekly:
            signals.append(Signal(
                key="streak_biweekly",
                stream="pulse",
                polarity=SignalPolarity.POSITIVE,
                severity=SignalSeverity.MEDIUM,
                value=streak,
                confidence=0.90,
                label=f"{streak}-day streak — two weeks strong",
                detail=f"Consistent engagement for {streak} days.",
                coaching_hook="Two weeks is when habits stick. Reinforce this milestone.",
            ))
        elif streak >= self.config.streak_milestone_weekly:
            signals.append(Signal(
                key="streak_weekly",
                stream="pulse",
                polarity=SignalPolarity.POSITIVE,
                severity=SignalSeverity.LOW,
                value=streak,
                confidence=0.85,
                label=f"{streak}-day streak — one week!",
                detail=f"First full week of daily check-ins.",
                coaching_hook="First week done. Acknowledge the consistency.",
            ))
        elif streak >= self.config.streak_milestone_early:
            signals.append(Signal(
                key="streak_early",
                stream="pulse",
                polarity=SignalPolarity.POSITIVE,
                severity=SignalSeverity.LOW,
                value=streak,
                confidence=0.80,
                label=f"{streak}-day streak building",
                detail=f"Early momentum — {streak} consecutive days.",
            ))
        elif streak == 0:
            # Missed today — check when they last checked in
            if snapshots:
                days_since = (today - snapshots[0].snapshot_date).days
                if days_since >= 3:
                    signals.append(Signal(
                        key="streak_broken_long",
                        stream="pulse",
                        polarity=SignalPolarity.NEGATIVE,
                        severity=SignalSeverity.MEDIUM,
                        value=days_since,
                        confidence=0.85,
                        label=f"No check-in in {days_since} days",
                        detail=f"Last check-in was {days_since} days ago.",
                        coaching_hook="Welcome them back without guilt. 'Good to see you' energy.",
                    ))

        return signals

    # ----------------------------------------------------------
    #  WEEKDAY vs WEEKEND BEHAVIORAL SHIFT
    # ----------------------------------------------------------

    def _detect_weekday_weekend_shift(self, db: Session, user_id: int) -> List[Signal]:
        """Detect if financial behavior shifts on weekends."""
        signals = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=28)

        snapshots = (
            db.query(UserMetricSnapshot)
            .filter(
                and_(
                    UserMetricSnapshot.user_id == user_id,
                    UserMetricSnapshot.snapshot_date >= cutoff.date(),
                )
            )
            .all()
        )

        if len(snapshots) < 7:
            return signals

        weekday_fcs = []
        weekend_fcs = []

        for s in snapshots:
            if s.fcs_composite is None:
                continue
            # Monday=0, Sunday=6
            if s.snapshot_date.weekday() >= 5:
                weekend_fcs.append(float(s.fcs_composite))
            else:
                weekday_fcs.append(float(s.fcs_composite))

        if weekday_fcs and weekend_fcs:
            weekday_avg = mean(weekday_fcs)
            weekend_avg = mean(weekend_fcs)
            gap = weekday_avg - weekend_avg

            if gap >= 10:
                signals.append(Signal(
                    key="weekend_dip",
                    stream="pulse",
                    polarity=SignalPolarity.NEGATIVE,
                    severity=SignalSeverity.MEDIUM,
                    value=gap,
                    confidence=0.75,
                    label=f"Financial confidence drops on weekends (−{gap:.0f} pts)",
                    detail=f"Weekday avg: {weekday_avg:.0f} → Weekend avg: {weekend_avg:.0f}.",
                    coaching_hook="Weekend spending or stress pattern. Help them plan weekends better.",
                ))
            elif gap <= -10:
                signals.append(Signal(
                    key="weekday_dip",
                    stream="pulse",
                    polarity=SignalPolarity.NEGATIVE,
                    severity=SignalSeverity.MEDIUM,
                    value=abs(gap),
                    confidence=0.75,
                    label=f"Financial confidence drops on weekdays (−{abs(gap):.0f} pts)",
                    detail=f"Weekend avg: {weekend_avg:.0f} → Weekday avg: {weekday_avg:.0f}.",
                    coaching_hook="Work stress may be driving financial anxiety. Explore the connection.",
                ))

        return signals

    # ----------------------------------------------------------
    #  HELPERS
    # ----------------------------------------------------------

    def _get_snapshot_history(
        self, db: Session, user_id: int, days: int
    ) -> List[UserMetricSnapshot]:
        """Get snapshot history, most recent first."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return (
            db.query(UserMetricSnapshot)
            .filter(
                and_(
                    UserMetricSnapshot.user_id == user_id,
                    UserMetricSnapshot.snapshot_date >= cutoff.date(),
                )
            )
            .order_by(desc(UserMetricSnapshot.snapshot_date))
            .all()
        )