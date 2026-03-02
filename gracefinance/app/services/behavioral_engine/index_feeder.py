"""
Index Feeder
==============
Clean, validated data pipeline from the behavioral engine into the GF-RWI.

THIS IS THE MOAT.

Every check-in gets a quality score before it touches the index.
Bad data gets filtered. Good data gets weighted by quality.
The result: an index that institutions can actually trust.

QUALITY SCORING:
  - Completion: Did they answer enough questions?
  - Time: Did they spend a reasonable amount of time?
  - Variance: Are their answers non-uniform (not all 5s)?
  - Consistency: Are answers consistent with their recent history?

FEEDING PIPELINE:
  1. User completes check-in
  2. Behavioral engine processes all 3 streams
  3. Index feeder scores data quality
  4. Only quality data enters the index computation
  5. Data is weighted by quality score in aggregation

Plugs into your EXISTING:
  - index_engine_service.compute_daily_index()
  - DailyIndex model (no new migrations)
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from statistics import mean, stdev
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from app.models.checkin import CheckInResponse, UserMetricSnapshot, DailyIndex

from .config import EngineConfig, DEFAULT_CONFIG
from .user_profile import UserBehavioralProfile


class QualityScore:
    """Represents the quality assessment of a single check-in."""

    def __init__(
        self,
        user_id: int,
        checkin_date,
        completion_score: float,
        time_score: float,
        variance_score: float,
        consistency_score: float,
        config: EngineConfig = DEFAULT_CONFIG,
    ):
        self.user_id = user_id
        self.checkin_date = checkin_date
        self.completion_score = completion_score
        self.time_score = time_score
        self.variance_score = variance_score
        self.consistency_score = consistency_score
        self.config = config

    @property
    def composite(self) -> float:
        """Weighted quality composite (0-1)."""
        return (
            self.completion_score * self.config.quality_weight_completion
            + self.time_score * self.config.quality_weight_time
            + self.variance_score * self.config.quality_weight_variance
            + self.consistency_score * self.config.quality_weight_consistency
        )

    @property
    def passes_threshold(self) -> bool:
        """Does this check-in meet minimum quality for index inclusion?"""
        return self.composite >= self.config.min_quality_score_for_index

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "checkin_date": str(self.checkin_date),
            "completion_score": round(self.completion_score, 3),
            "time_score": round(self.time_score, 3),
            "variance_score": round(self.variance_score, 3),
            "consistency_score": round(self.consistency_score, 3),
            "composite": round(self.composite, 3),
            "passes_threshold": self.passes_threshold,
        }


class IndexFeeder:
    """
    Validates and quality-scores check-in data before it enters the GF-RWI.
    """

    def __init__(self, config: EngineConfig = DEFAULT_CONFIG):
        self.config = config

    def score_checkin_quality(
        self, db: Session, user_id: int, checkin_date=None
    ) -> QualityScore:
        """
        Score the quality of a user's check-in for a given date.

        Args:
            db: Database session
            user_id: User to evaluate
            checkin_date: Date to evaluate (defaults to today)

        Returns:
            QualityScore with individual and composite scores
        """
        if checkin_date is None:
            checkin_date = datetime.now(timezone.utc).date()

        # Get today's responses
        responses = self._get_responses(db, user_id, checkin_date)

        # 1. Completion Score — did they answer enough questions?
        completion = self._score_completion(responses)

        # 2. Time Score — reasonable completion time?
        time_score = self._score_time(responses)

        # 3. Variance Score — non-uniform answers?
        variance = self._score_variance(responses)

        # 4. Consistency Score — consistent with recent history?
        consistency = self._score_consistency(db, user_id, responses)

        return QualityScore(
            user_id=user_id,
            checkin_date=checkin_date,
            completion_score=completion,
            time_score=time_score,
            variance_score=variance,
            consistency_score=consistency,
            config=self.config,
        )

    def get_index_eligible_snapshots(
        self, db: Session, target_date=None
    ) -> List[Tuple[UserMetricSnapshot, float]]:
        """
        Get all user snapshots that pass quality threshold for index computation.

        Returns list of (snapshot, quality_weight) tuples.
        Higher quality data gets more weight in the index.
        """
        if target_date is None:
            target_date = datetime.now(timezone.utc).date()

        # Get all snapshots for the target date
        snapshots = (
            db.query(UserMetricSnapshot)
            .filter(UserMetricSnapshot.snapshot_date == target_date)
            .all()
        )

        eligible = []
        for snapshot in snapshots:
            quality = self.score_checkin_quality(db, snapshot.user_id, target_date)

            if quality.passes_threshold:
                # Weight = quality composite (higher quality = more influence)
                eligible.append((snapshot, quality.composite))

        return eligible

    def compute_quality_weighted_index(
        self, db: Session, target_date=None
    ) -> Optional[Dict]:
        """
        Compute a quality-weighted daily index.

        This is the upgraded version of compute_daily_index() that
        weights each user's contribution by their data quality.

        Returns:
            Dict with index values, or None if insufficient data.
        """
        eligible = self.get_index_eligible_snapshots(db, target_date)

        if not eligible:
            return None

        total_weight = sum(weight for _, weight in eligible)
        if total_weight == 0:
            return None

        # Quality-weighted averages for each component
        weighted_fcs = 0.0
        weighted_bsi = 0.0
        bsi_weight = 0.0

        dim_sums = {
            "current_stability": 0.0,
            "future_outlook": 0.0,
            "purchasing_power": 0.0,
            "debt_pressure": 0.0,
            "financial_freedom": 0.0,
        }
        dim_weights = {k: 0.0 for k in dim_sums}

        for snapshot, quality_weight in eligible:
            if snapshot.fcs_composite is not None:
                weighted_fcs += float(snapshot.fcs_composite) * quality_weight

            if snapshot.bsi_score is not None:
                weighted_bsi += float(snapshot.bsi_score) * quality_weight
                bsi_weight += quality_weight

            # Dimensions
            for dim_key in dim_sums:
                val = getattr(snapshot, f"dim_{dim_key}", None)
                if val is not None:
                    dim_sums[dim_key] += float(val) * quality_weight
                    dim_weights[dim_key] += quality_weight

        # Compute weighted averages
        avg_fcs = weighted_fcs / total_weight
        avg_bsi = (weighted_bsi / bsi_weight) if bsi_weight > 0 else None

        # GF-RWI composite: 60% FCS + 40% BSI (inverted, since high BSI = bad)
        if avg_bsi is not None:
            # BSI is stress-based, so invert for index (100 - BSI)
            gci_value = 0.60 * avg_fcs + 0.40 * (100 - avg_bsi)
        else:
            gci_value = avg_fcs

        avg_dims = {}
        for dim_key in dim_sums:
            if dim_weights[dim_key] > 0:
                avg_dims[dim_key] = dim_sums[dim_key] / dim_weights[dim_key]
            else:
                avg_dims[dim_key] = None

        return {
            "date": target_date or datetime.now(timezone.utc).date(),
            "gci_value": round(gci_value, 4),
            "avg_fcs": round(avg_fcs, 4),
            "avg_bsi": round(avg_bsi, 4) if avg_bsi else None,
            "dimensions": {k: round(v, 4) if v else None for k, v in avg_dims.items()},
            "user_count": len(eligible),
            "total_submitted": len(
                (db.query(UserMetricSnapshot)
                 .filter(UserMetricSnapshot.snapshot_date == (target_date or datetime.now(timezone.utc).date()))
                 .all())
            ),
            "quality_filtered_count": len(eligible),
            "avg_quality_score": round(total_weight / len(eligible), 4),
        }

    # ----------------------------------------------------------
    #  QUALITY SCORING COMPONENTS
    # ----------------------------------------------------------

    def _score_completion(self, responses: List[CheckInResponse]) -> float:
        """
        Score based on how many questions were answered.
        Full credit at min_responses_for_valid_fcs, partial below.
        """
        # Filter out conversation themes
        real_responses = [
            r for r in responses
            if r.dimension != "conversation_theme"
        ]
        count = len(real_responses)
        target = self.config.min_responses_for_valid_fcs

        if count >= target:
            return 1.0
        elif count == 0:
            return 0.0
        else:
            return count / target

    def _score_time(self, responses: List[CheckInResponse]) -> float:
        """
        Score based on completion time (estimated from timestamps).
        Too fast = not thoughtful. Too slow = AFK.
        """
        if not responses:
            return 0.5  # Neutral when no timing data

        # Estimate time from first to last response timestamp
        timestamps = []
        for r in responses:
            if hasattr(r, "created_at") and r.created_at:
                timestamps.append(r.created_at)

        if len(timestamps) < 2:
            return 0.7  # Give benefit of the doubt

        time_span = (max(timestamps) - min(timestamps)).total_seconds()

        if time_span < self.config.min_completion_time_seconds:
            # Too fast — probably rushing
            return max(0.1, time_span / self.config.min_completion_time_seconds)
        elif time_span > self.config.max_completion_time_seconds:
            # Too slow — probably AFK
            return max(0.3, 1.0 - (time_span - self.config.max_completion_time_seconds) / 1800)
        else:
            # Goldilocks zone
            return 1.0

    def _score_variance(self, responses: List[CheckInResponse]) -> float:
        """
        Score based on answer variance.
        All identical answers = suspicious. Some spread = thoughtful.
        """
        if not responses:
            return 0.5

        # Extract numeric answers
        numeric_vals = []
        for r in responses:
            if r.dimension == "conversation_theme":
                continue
            try:
                numeric_vals.append(float(r.answer_value))
            except (ValueError, TypeError):
                continue

        if len(numeric_vals) < 2:
            return 0.7

        # Check if all values are identical
        if len(set(numeric_vals)) == 1:
            if self.config.flag_uniform_responses:
                return 0.1  # Very suspicious
            return 0.3

        # Some variance is good
        val_stdev = stdev(numeric_vals) if len(numeric_vals) >= 2 else 0
        val_range = max(numeric_vals) - min(numeric_vals)

        if val_range <= 1:
            return 0.3  # Almost no spread
        elif val_stdev < 0.5:
            return 0.5  # Very low variance
        elif val_stdev > 3.5:
            return 0.7  # High variance (could be erratic, but still engagement)
        else:
            return 1.0  # Healthy variance

    def _score_consistency(
        self, db: Session, user_id: int, responses: List[CheckInResponse]
    ) -> float:
        """
        Score based on consistency with recent history.
        Wildly different from usual patterns = possible noise.
        Small changes = normal. Moderate changes = expected.
        """
        if not responses:
            return 0.5

        # Get recent history (last 7 days)
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        history = (
            db.query(UserMetricSnapshot)
            .filter(
                and_(
                    UserMetricSnapshot.user_id == user_id,
                    UserMetricSnapshot.snapshot_date >= cutoff.date(),
                )
            )
            .all()
        )

        if len(history) < 2:
            return 0.8  # New users get benefit of the doubt

        # Compare today's FCS-relevant answers to historical average
        historical_fcs = [
            float(h.fcs_composite) for h in history
            if h.fcs_composite is not None
        ]

        if not historical_fcs:
            return 0.8

        hist_mean = mean(historical_fcs)
        hist_std = stdev(historical_fcs) if len(historical_fcs) >= 2 else 10.0

        # Get today's numeric answers average as proxy
        today_vals = []
        for r in responses:
            if r.dimension == "conversation_theme":
                continue
            try:
                today_vals.append(float(r.answer_value))
            except (ValueError, TypeError):
                continue

        if not today_vals:
            return 0.7

        today_avg = mean(today_vals)

        # How many standard deviations away from their mean?
        if hist_std == 0:
            hist_std = 5.0  # Prevent division by zero

        z_score = abs(today_avg - (hist_mean / 10)) / (hist_std / 10)  # Normalize scales

        if z_score <= 1.5:
            return 1.0   # Normal variation
        elif z_score <= 2.5:
            return 0.7   # Unusual but plausible
        elif z_score <= 3.5:
            return 0.4   # Very unusual
        else:
            return 0.2   # Extreme outlier

    # ----------------------------------------------------------
    #  HELPERS
    # ----------------------------------------------------------

    def _get_responses(
        self, db: Session, user_id: int, checkin_date
    ) -> List[CheckInResponse]:
        """Get all check-in responses for a user on a given date."""
        return (
            db.query(CheckInResponse)
            .filter(
                and_(
                    CheckInResponse.user_id == user_id,
                    CheckInResponse.checkin_date == checkin_date,
                )
            )
            .all()
        )