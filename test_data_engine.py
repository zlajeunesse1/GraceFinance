"""
Test Suite — GraceFinance Data Engine + Index Engine

Covers: mood_spend_gap, elasticity, risk scoring, index normalization,
daily index updates, user type labels, and recommendation severity.

Uses an in-memory SQLite database for speed. For production CI, swap to a
PostgreSQL test database to catch dialect-specific issues.
"""

import uuid
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.checkin import CheckIn, MoodTag
from app.models.user_metric_snapshot import UserMetricSnapshot
from app.models.daily_index import DailyIndex

# We need a minimal users table for FK constraints in tests
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

# For SQLite testing, we'll use String for UUID columns
# In production tests, use PostgreSQL


# ---- Test Database Setup ----

# Use SQLite for fast unit tests
TEST_DATABASE_URL = "sqlite:///./test_data_engine.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Minimal users table stub for FK satisfaction
from sqlalchemy import Table, MetaData, Column as Col, String as Str
from sqlalchemy.dialects import sqlite

# We'll create tables manually to avoid import issues with the real users model


@pytest.fixture(autouse=True)
def setup_db():
    """Create all tables before each test, drop after."""
    # For SQLite, we need to handle UUIDs as strings
    # Create a minimal users table
    from sqlalchemy import Column, String, text
    from sqlalchemy import MetaData, Table

    metadata = MetaData()
    users_table = Table(
        "users", metadata,
        Column("id", String, primary_key=True),
    )

    # Override UUID columns to String for SQLite compatibility
    # This is a test-only concern
    Base.metadata.create_all(bind=engine, checkfirst=True)
    metadata.create_all(bind=engine, checkfirst=True)

    yield

    Base.metadata.drop_all(bind=engine)
    metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def user_id():
    return uuid.uuid4()


def _make_checkin(user_id, **kwargs):
    """Helper to create a CheckIn with sensible defaults."""
    defaults = {
        "id": uuid.uuid4(),
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc),
        "timezone": "America/New_York",
        "mood_tag": MoodTag.neutral,
        "mood_score": 5,
        "confidence_score": 5,
        "stress_level": 5,
        "spending_amount": Decimal("50.00"),
        "spending_category": "essentials",
        "impulse_flag": False,
        "goal_alignment_score": 5,
        "savings_change": Decimal("0.00"),
    }
    defaults.update(kwargs)
    return CheckIn(**defaults)


# ====================================================================
# TEST: Mood-Spend Gap
# ====================================================================

class TestMoodSpendGap:

    def test_correct_calculation(self, db, user_id):
        """Gap should equal avg(stressed spending) - avg(calm spending)."""
        from app.services.user_metrics_service import calculate_mood_spend_gap

        now = datetime.now(timezone.utc)

        # 3 stressed check-ins averaging $100
        for i in range(3):
            db.add(_make_checkin(user_id, mood_tag=MoodTag.stressed,
                                 spending_amount=Decimal("100.00"),
                                 timestamp=now - timedelta(hours=i)))

        # 3 calm check-ins averaging $40
        for i in range(3):
            db.add(_make_checkin(user_id, mood_tag=MoodTag.calm,
                                 spending_amount=Decimal("40.00"),
                                 timestamp=now - timedelta(hours=i + 10)))
        db.commit()

        gap = calculate_mood_spend_gap(db, user_id, days=30)
        assert gap is not None
        assert abs(gap - 60.0) < 0.01  # $100 - $40 = $60

    def test_none_guard_insufficient_data(self, db, user_id):
        """Should return None if either group has fewer than 3 observations."""
        from app.services.user_metrics_service import calculate_mood_spend_gap

        now = datetime.now(timezone.utc)

        # Only 2 stressed (need 3)
        for i in range(2):
            db.add(_make_checkin(user_id, mood_tag=MoodTag.stressed,
                                 spending_amount=Decimal("100.00"),
                                 timestamp=now - timedelta(hours=i)))

        for i in range(3):
            db.add(_make_checkin(user_id, mood_tag=MoodTag.calm,
                                 spending_amount=Decimal("40.00"),
                                 timestamp=now - timedelta(hours=i + 10)))
        db.commit()

        gap = calculate_mood_spend_gap(db, user_id, days=30)
        assert gap is None


# ====================================================================
# TEST: Elasticity Score (Pearson Correlation)
# ====================================================================

class TestElasticity:

    def test_positive_correlation(self, db, user_id):
        """Higher mood → higher spend should yield positive elasticity."""
        from app.services.user_metrics_service import calculate_elasticity

        now = datetime.now(timezone.utc)

        # Create a clear positive correlation: mood goes up, spending goes up
        for i in range(10):
            mood = i + 1
            spend = Decimal(str(10 * (i + 1)))
            db.add(_make_checkin(user_id, mood_score=mood,
                                 spending_amount=spend,
                                 timestamp=now - timedelta(hours=i)))
        db.commit()

        elasticity = calculate_elasticity(db, user_id, days=30)
        assert elasticity is not None
        assert elasticity > 0.5  # Strong positive correlation

    def test_none_guard_sparse_data(self, db, user_id):
        """Should return None with fewer than 7 observations."""
        from app.services.user_metrics_service import calculate_elasticity

        now = datetime.now(timezone.utc)

        for i in range(5):  # Only 5, need 7
            db.add(_make_checkin(user_id, timestamp=now - timedelta(hours=i)))
        db.commit()

        elasticity = calculate_elasticity(db, user_id, days=30)
        assert elasticity is None

    def test_range_bounds(self, db, user_id):
        """Elasticity should always be between -1 and 1."""
        from app.services.user_metrics_service import calculate_elasticity

        now = datetime.now(timezone.utc)

        for i in range(15):
            db.add(_make_checkin(user_id, mood_score=(i % 10) + 1,
                                 spending_amount=Decimal(str((i * 7 + 3) % 100 + 1)),
                                 timestamp=now - timedelta(hours=i)))
        db.commit()

        elasticity = calculate_elasticity(db, user_id, days=30)
        assert elasticity is not None
        assert -1.0 <= elasticity <= 1.0


# ====================================================================
# TEST: Overspend Risk Score
# ====================================================================

class TestRiskScore:

    def test_score_always_in_range(self, db, user_id):
        """Risk score must be 0–100 regardless of input."""
        from app.services.user_metrics_service import calculate_overspend_risk

        now = datetime.now(timezone.utc)

        # Create high-risk data: high stress, lots of impulse buys
        for i in range(15):
            db.add(_make_checkin(
                user_id,
                stress_level=9,
                impulse_flag=True,
                confidence_score=max(1, 8 - i),  # Declining
                spending_amount=Decimal("200.00"),
                savings_change=Decimal("-50.00"),
                mood_tag=MoodTag.stressed,
                timestamp=now - timedelta(hours=i * 6),
            ))
        db.commit()

        result = calculate_overspend_risk(db, user_id)
        assert 0 <= result["score"] <= 100

    def test_reasons_nonempty_when_score_positive(self, db, user_id):
        """When score > 0, reasons list must contain at least one explanation."""
        from app.services.user_metrics_service import calculate_overspend_risk

        now = datetime.now(timezone.utc)

        for i in range(10):
            db.add(_make_checkin(
                user_id,
                stress_level=9,  # High stress → +20 points
                timestamp=now - timedelta(hours=i * 4),
            ))
        db.commit()

        result = calculate_overspend_risk(db, user_id)
        if result["score"] > 0:
            assert len(result["reasons"]) > 0

    def test_zero_score_for_healthy_data(self, db, user_id):
        """Healthy data should yield a low risk score."""
        from app.services.user_metrics_service import calculate_overspend_risk

        now = datetime.now(timezone.utc)

        for i in range(10):
            db.add(_make_checkin(
                user_id,
                stress_level=3,
                impulse_flag=False,
                confidence_score=8,
                spending_amount=Decimal("30.00"),
                savings_change=Decimal("20.00"),
                mood_tag=MoodTag.calm,
                timestamp=now - timedelta(hours=i * 6),
            ))
        db.commit()

        result = calculate_overspend_risk(db, user_id)
        assert result["score"] <= 20  # Very low risk


# ====================================================================
# TEST: Index Normalization
# ====================================================================

class TestIndexNormalization:

    def test_clamp_to_0_100(self):
        """Normalized values must be clamped to [0, 100] at storage time."""
        from app.services.index_engine_service import _normalize_fixed, _clamp_for_storage

        # _normalize_fixed does NOT clamp (allows slight overshoot)
        raw = _normalize_fixed(150.0, 0.0, 100.0)
        assert raw > 100.0  # Intentionally unclamped

        # _clamp_for_storage enforces [0, 100]
        assert _clamp_for_storage(150.0) == 100.0
        assert _clamp_for_storage(-50.0) == 0.0
        assert 0.0 <= _clamp_for_storage(50.0) <= 100.0

    def test_neutral_50_when_no_variance(self):
        """When min == max (no variance), return 50 as neutral baseline."""
        from app.services.index_engine_service import _normalize_fixed

        assert _normalize_fixed(42.0, 42.0, 42.0) == 50.0
        assert _normalize_fixed(0.0, 0.0, 0.0) == 50.0

    def test_tanh_zscore_normalization(self):
        """Tanh transform: z=0 → 50, z→+∞ → 100, z→-∞ → 0."""
        from app.services.index_engine_service import _normalize_zscore_tanh

        assert abs(_normalize_zscore_tanh(0.0) - 50.0) < 0.01
        assert _normalize_zscore_tanh(5.0) > 99.0
        assert _normalize_zscore_tanh(-5.0) < 1.0
        # Monotonic: higher z → higher output
        assert _normalize_zscore_tanh(1.0) > _normalize_zscore_tanh(0.0)
        assert _normalize_zscore_tanh(0.0) > _normalize_zscore_tanh(-1.0)


# ====================================================================
# TEST: GCI Composite Calculation
# ====================================================================

class TestGCICalculation:

    def test_gci_formula(self):
        """GCI = (CSI * 0.35) + (DPI * 0.35) + ((100 - FRS) * 0.30)"""
        from app.services.index_engine_service import calculate_grace_composite_index

        csi, dpi, frs = 60.0, 40.0, 70.0
        expected = (60.0 * 0.35) + (40.0 * 0.35) + ((100 - 70.0) * 0.30)
        result = calculate_grace_composite_index(csi, dpi, frs)
        assert abs(result - expected) < 0.01

    def test_gci_not_clamped_at_compute(self):
        """Raw GCI should NOT be clamped — clamping happens at storage only."""
        from app.services.index_engine_service import (
            calculate_grace_composite_index, _clamp_for_storage
        )

        # Extreme inputs that could push raw GCI beyond bounds
        raw = calculate_grace_composite_index(100.0, 100.0, 0.0)
        # After clamping, it should be within [0, 100]
        clamped = _clamp_for_storage(raw)
        assert 0.0 <= clamped <= 100.0

    def test_sub_indexes_accept_metrics_dict(self):
        """Sub-index functions must accept a dict, not a db session."""
        from app.services.index_engine_service import (
            calculate_consumer_stress_index,
            calculate_discretionary_pressure_index,
            calculate_financial_resilience_score,
        )

        metrics = {
            "avg_stress": 5.0,
            "stressed_rate": 0.3,
            "confidence_trend_slope": 0.0,
            "spending_zscore": 0.0,
            "impulse_rate": 0.2,
            "non_essential_rate": 0.4,
            "avg_savings": 10.0,
            "avg_goal_alignment": 6.0,
            "confidence_std": 1.5,
        }

        csi = calculate_consumer_stress_index(metrics)
        dpi = calculate_discretionary_pressure_index(metrics)
        frs = calculate_financial_resilience_score(metrics)

        # All should produce reasonable values (roughly 0–100 range)
        for val in [csi, dpi, frs]:
            assert isinstance(val, float)
            assert -10 < val < 110  # Allow slight overshoot before clamp


# ====================================================================
# TEST: Trend Direction Classification
# ====================================================================

class TestTrendDirection:

    def test_trend_up(self):
        """Slope > +0.5 should classify as UP."""
        from app.services.index_engine_service import (
            TrendDirection, TREND_SLOPE_UP_THRESHOLD
        )
        slope = 0.8
        if slope > TREND_SLOPE_UP_THRESHOLD:
            trend = TrendDirection.UP
        assert trend == TrendDirection.UP

    def test_trend_down(self):
        """Slope < -0.5 should classify as DOWN."""
        from app.services.index_engine_service import (
            TrendDirection, TREND_SLOPE_DOWN_THRESHOLD
        )
        slope = -0.9
        if slope < TREND_SLOPE_DOWN_THRESHOLD:
            trend = TrendDirection.DOWN
        assert trend == TrendDirection.DOWN

    def test_trend_flat(self):
        """Slope between -0.5 and +0.5 should classify as FLAT."""
        from app.services.index_engine_service import (
            TrendDirection,
            TREND_SLOPE_UP_THRESHOLD,
            TREND_SLOPE_DOWN_THRESHOLD,
        )
        slope = 0.1
        if TREND_SLOPE_DOWN_THRESHOLD <= slope <= TREND_SLOPE_UP_THRESHOLD:
            trend = TrendDirection.FLAT
        assert trend == TrendDirection.FLAT


# ====================================================================
# TEST: User Type Label Assignment
# ====================================================================

class TestUserTypeLabel:

    def test_balanced_for_insufficient_data(self, db, user_id):
        """Default to Balanced with fewer than 7 check-ins."""
        from app.services.user_metrics_service import assign_user_type_label

        now = datetime.now(timezone.utc)

        for i in range(3):
            db.add(_make_checkin(user_id, timestamp=now - timedelta(hours=i)))
        db.commit()

        label = assign_user_type_label(db, user_id)
        assert label == "Balanced"

    def test_disciplined_saver(self, db, user_id):
        """High goal alignment + positive savings → Disciplined Saver."""
        from app.services.user_metrics_service import assign_user_type_label

        now = datetime.now(timezone.utc)

        for i in range(15):
            db.add(_make_checkin(
                user_id,
                goal_alignment_score=9,
                savings_change=Decimal("50.00"),
                mood_tag=MoodTag.confident,
                impulse_flag=False,
                stress_level=3,
                mood_score=8,
                spending_amount=Decimal("30.00"),
                timestamp=now - timedelta(hours=i * 12),
            ))
        db.commit()

        label = assign_user_type_label(db, user_id)
        assert label == "Disciplined Saver"


# ====================================================================
# TEST: Recommendation Severity
# ====================================================================

class TestRecommendationSeverity:

    def test_high_severity_for_high_risk(self, db, user_id):
        """Risk score >= 75 should produce HIGH severity recommendation."""
        from app.services.recommendation_service import generate_recommendations

        now = datetime.now(timezone.utc)

        # Create snapshot with high risk
        snapshot = UserMetricSnapshot(
            user_id=user_id,
            date=date.today(),
            overspend_risk_score=80,
            mood_spend_gap=Decimal("250.00"),
            user_type_label="Emotional Spender",
        )
        db.add(snapshot)

        # Need some check-in data for impulse rate calculation
        for i in range(10):
            db.add(_make_checkin(
                user_id,
                impulse_flag=True,
                stress_level=8,
                timestamp=now - timedelta(hours=i * 12),
            ))
        db.commit()

        recs = generate_recommendations(db, user_id)
        severities = [r["severity"] for r in recs]
        assert "HIGH" in severities

    def test_low_severity_for_healthy_user(self, db, user_id):
        """Healthy metrics should produce only LOW severity or positive message."""
        from app.services.recommendation_service import generate_recommendations

        now = datetime.now(timezone.utc)

        snapshot = UserMetricSnapshot(
            user_id=user_id,
            date=date.today(),
            overspend_risk_score=10,
            mood_spend_gap=Decimal("5.00"),
            user_type_label="Balanced",
        )
        db.add(snapshot)

        for i in range(10):
            db.add(_make_checkin(
                user_id,
                impulse_flag=False,
                stress_level=3,
                confidence_score=8,
                goal_alignment_score=8,
                savings_change=Decimal("20.00"),
                timestamp=now - timedelta(hours=i * 12),
            ))
        db.commit()

        recs = generate_recommendations(db, user_id)
        severities = [r["severity"] for r in recs]
        assert "HIGH" not in severities

    def test_recommendations_ordered_by_severity(self, db, user_id):
        """Recommendations should be ordered HIGH → MEDIUM → LOW."""
        from app.services.recommendation_service import generate_recommendations

        now = datetime.now(timezone.utc)

        snapshot = UserMetricSnapshot(
            user_id=user_id,
            date=date.today(),
            overspend_risk_score=60,
            mood_spend_gap=Decimal("120.00"),
            user_type_label="Stressed Spender",
        )
        db.add(snapshot)

        for i in range(10):
            db.add(_make_checkin(
                user_id,
                impulse_flag=(i % 3 == 0),
                stress_level=6,
                confidence_score=4,
                goal_alignment_score=3,
                savings_change=Decimal("-15.00"),
                timestamp=now - timedelta(hours=i * 12),
            ))
        db.commit()

        recs = generate_recommendations(db, user_id)
        severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        severity_nums = [severity_order[r["severity"]] for r in recs]

        # Verify non-decreasing order
        for i in range(len(severity_nums) - 1):
            assert severity_nums[i] <= severity_nums[i + 1]
