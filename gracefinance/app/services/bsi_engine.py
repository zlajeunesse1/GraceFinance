"""
BSI Engine v2 — Motivation-Aware Behavioral Shift Computation
═════════════════════════════════════════════════════════════
The BSI doesn't just track WHAT people do — it tracks WHY.

Each answer is a (trigger, motivation) pair:
  - trigger: Did the behavior happen? (yes/no)
  - motivation: WHY? (stress, positive, neutral, avoidance)

The motivation determines the score, the FCS dimension mapping,
and the coaching context. Same behavior, different motivation =
completely different score.

BSI Score: -100 to +100
  -100 = All five patterns firing, all stress-driven
     0 = No behavioral shift detected
  +100 = Active positive financial behavior across all patterns

File: app/services/bsi_engine.py
"""

import uuid
from datetime import datetime, timezone, timedelta, date
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func
from typing import Optional, Dict, List

from app.database import Base
from sqlalchemy import Column, String, Float, Integer, DateTime, Date
from sqlalchemy.dialects.postgresql import UUID, JSON

from app.services.bsi_questions import (
    BSI_QUESTIONS,
    MOTIVATION_LOOKUP,
    score_bsi_answer,
    get_dimension_reflection,
    PATTERN_LABELS,
)

EASTERN = ZoneInfo("America/New_York")


# ═══════════════════════════════════════════════════════════════
#  BSI WEEKLY RECORD MODEL
# ═══════════════════════════════════════════════════════════════

class BSIWeeklyRecord(Base):
    __tablename__ = "bsi_weekly_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)

    # Per-pattern scores (-1.0 to +1.0)
    subscription_churn_score = Column(Float, nullable=True)
    credit_substitution_score = Column(Float, nullable=True)
    deferred_spending_score = Column(Float, nullable=True)
    debt_accumulation_score = Column(Float, nullable=True)
    financial_avoidance_score = Column(Float, nullable=True)

    # Per-pattern signals
    subscription_churn_signal = Column(String(20), nullable=True)
    credit_substitution_signal = Column(String(20), nullable=True)
    deferred_spending_signal = Column(String(20), nullable=True)
    debt_accumulation_signal = Column(String(20), nullable=True)
    financial_avoidance_signal = Column(String(20), nullable=True)

    # Audit trail
    motivation_ids = Column(JSON, nullable=True)
    dimension_impacts = Column(JSON, nullable=True)

    # Composite
    bsi_composite = Column(Float, nullable=False, default=0.0)
    bsi_delta = Column(Float, nullable=True)

    # Pattern flags
    stress_patterns = Column(JSON, nullable=True)
    positive_patterns = Column(JSON, nullable=True)
    coaching_reflections = Column(JSON, nullable=True)

    # Metadata
    patterns_triggered = Column(Integer, default=0)
    checkin_count_this_week = Column(Integer, default=0)
    computed_at = Column(DateTime(timezone=True), server_default=func.now())


PATTERN_WEIGHTS = {
    "subscription_churn":   0.15,
    "credit_substitution":  0.25,
    "deferred_spending":    0.20,
    "debt_accumulation":    0.25,
    "financial_avoidance":  0.15,
}


def _get_week_bounds(target_date=None):
    if target_date is None:
        target_date = datetime.now(EASTERN).date()
    days_since_monday = target_date.weekday()
    week_start = target_date - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def compute_bsi(db: Session, user_id, answers: List[Dict]) -> BSIWeeklyRecord:
    """
    Compute BSI from weekly behavioral answers with motivation layer.

    answers: list of dicts:
        { "question_id": "BX-1", "triggered": True, "motivation_id": "BX-1-B" }
    """
    week_start, week_end = _get_week_bounds()

    existing = (
        db.query(BSIWeeklyRecord)
        .filter(and_(BSIWeeklyRecord.user_id == user_id, BSIWeeklyRecord.week_start == week_start))
        .first()
    )

    scored = []
    motivation_ids = {}
    for answer in answers:
        qid = answer["question_id"]
        triggered = answer.get("triggered", False)
        motivation_id = answer.get("motivation_id")
        result = score_bsi_answer(qid, triggered, motivation_id)
        result["question_id"] = qid
        scored.append(result)
        if motivation_id:
            motivation_ids[qid] = motivation_id

    weighted_sum = 0.0
    total_weight = 0.0
    pattern_scores = {}
    pattern_signals = {}
    dimension_impacts = {}
    stress_patterns = []
    positive_patterns = []
    coaching_reflections = []
    patterns_triggered = 0

    for s in scored:
        pattern = s["pattern"]
        if pattern == "unknown":
            continue

        weight = PATTERN_WEIGHTS.get(pattern, 0.2)
        weighted_sum += s["score"] * weight
        total_weight += weight
        pattern_scores[pattern] = s["score"]
        pattern_signals[pattern] = s["signal"]

        if s.get("triggered"):
            patterns_triggered += 1

        dim = s.get("maps_to_dimension")
        if dim:
            if dim not in dimension_impacts:
                dimension_impacts[dim] = []
            dimension_impacts[dim].append({
                "pattern": pattern, "score": s["score"],
                "signal": s["signal"], "coaching_tag": s.get("coaching_tag", ""),
            })

        label = PATTERN_LABELS.get(pattern, pattern)
        if s["signal"] in ("stress", "avoidance"):
            stress_patterns.append({
                "pattern": pattern, "label": label, "score": round(s["score"], 2),
                "signal": s["signal"], "coaching_tag": s.get("coaching_tag", ""), "dimension": dim,
            })
        elif s["signal"] == "positive":
            positive_patterns.append({
                "pattern": pattern, "label": label, "score": round(s["score"], 2),
                "coaching_tag": s.get("coaching_tag", ""), "dimension": dim,
            })

    bsi_composite = (weighted_sum / total_weight * 100) if total_weight > 0 else 0.0
    bsi_composite = max(-100, min(100, round(bsi_composite, 2)))

    for dim, impacts in dimension_impacts.items():
        for impact in impacts:
            reflection = get_dimension_reflection(
                dimension=dim, signal=impact["signal"],
                pattern_label=PATTERN_LABELS.get(impact["pattern"], impact["pattern"]),
            )
            if reflection:
                coaching_reflections.append({
                    "dimension": dim, "pattern": impact["pattern"],
                    "signal": impact["signal"], "reflection": reflection,
                })

    dim_scores = {}
    for dim, impacts in dimension_impacts.items():
        scores = [i["score"] for i in impacts]
        dim_scores[dim] = round(sum(scores) / len(scores), 3) if scores else 0

    prev_week_start = week_start - timedelta(days=7)
    previous = (
        db.query(BSIWeeklyRecord)
        .filter(and_(BSIWeeklyRecord.user_id == user_id, BSIWeeklyRecord.week_start == prev_week_start))
        .first()
    )
    bsi_delta = round(bsi_composite - previous.bsi_composite, 2) if previous else None

    from app.models.checkin import CheckInResponse
    week_start_dt = datetime.combine(week_start, datetime.min.time()).replace(tzinfo=timezone.utc)
    week_end_dt = datetime.combine(week_end + timedelta(days=1), datetime.min.time()).replace(tzinfo=timezone.utc)
    checkin_count = (
        db.query(func.count(CheckInResponse.id))
        .filter(and_(CheckInResponse.user_id == user_id, CheckInResponse.checkin_date >= week_start_dt, CheckInResponse.checkin_date < week_end_dt))
        .scalar() or 0
    )

    record = existing if existing else BSIWeeklyRecord(user_id=user_id, week_start=week_start, week_end=week_end)

    record.subscription_churn_score = pattern_scores.get("subscription_churn")
    record.credit_substitution_score = pattern_scores.get("credit_substitution")
    record.deferred_spending_score = pattern_scores.get("deferred_spending")
    record.debt_accumulation_score = pattern_scores.get("debt_accumulation")
    record.financial_avoidance_score = pattern_scores.get("financial_avoidance")
    record.subscription_churn_signal = pattern_signals.get("subscription_churn")
    record.credit_substitution_signal = pattern_signals.get("credit_substitution")
    record.deferred_spending_signal = pattern_signals.get("deferred_spending")
    record.debt_accumulation_signal = pattern_signals.get("debt_accumulation")
    record.financial_avoidance_signal = pattern_signals.get("financial_avoidance")
    record.motivation_ids = motivation_ids
    record.dimension_impacts = dim_scores
    record.bsi_composite = bsi_composite
    record.bsi_delta = bsi_delta
    record.stress_patterns = stress_patterns
    record.positive_patterns = positive_patterns
    record.coaching_reflections = coaching_reflections
    record.patterns_triggered = patterns_triggered
    record.checkin_count_this_week = checkin_count
    record.computed_at = datetime.now(timezone.utc)

    if not existing:
        db.add(record)

    try:
        from app.models.checkin import UserMetricSnapshot
        latest_snapshot = (
            db.query(UserMetricSnapshot)
            .filter(UserMetricSnapshot.user_id == user_id)
            .order_by(desc(UserMetricSnapshot.computed_at))
            .first()
        )
        if latest_snapshot:
            latest_snapshot.bsi_score = bsi_composite
    except Exception:
        pass

    db.commit()
    return record


def get_user_bsi_history(db: Session, user_id, weeks: int = 12) -> List[BSIWeeklyRecord]:
    cutoff = datetime.now(EASTERN).date() - timedelta(weeks=weeks)
    return (
        db.query(BSIWeeklyRecord)
        .filter(and_(BSIWeeklyRecord.user_id == user_id, BSIWeeklyRecord.week_start >= cutoff))
        .order_by(BSIWeeklyRecord.week_start.asc())
        .all()
    )


def get_latest_bsi(db: Session, user_id) -> Optional[BSIWeeklyRecord]:
    return (
        db.query(BSIWeeklyRecord)
        .filter(BSIWeeklyRecord.user_id == user_id)
        .order_by(desc(BSIWeeklyRecord.week_start))
        .first()
    )


def has_completed_bsi_this_week(db: Session, user_id) -> bool:
    week_start, _ = _get_week_bounds()
    count = (
        db.query(func.count(BSIWeeklyRecord.id))
        .filter(and_(BSIWeeklyRecord.user_id == user_id, BSIWeeklyRecord.week_start == week_start))
        .scalar() or 0
    )
    return count > 0


def compute_population_bsi(db: Session) -> Dict:
    week_start, _ = _get_week_bounds()
    records = db.query(BSIWeeklyRecord).filter(BSIWeeklyRecord.week_start == week_start).all()

    if not records:
        return {"population_bsi": None, "user_count": 0, "patterns": {}}

    composites = [r.bsi_composite for r in records]
    pop_bsi = round(sum(composites) / len(composites), 2)

    pattern_data = {}
    for pattern in PATTERN_WEIGHTS:
        scores = []
        signals = {"stress": 0, "positive": 0, "neutral": 0, "avoidance": 0, "stable": 0}
        for r in records:
            val = getattr(r, f"{pattern}_score", None)
            sig = getattr(r, f"{pattern}_signal", None)
            if val is not None:
                scores.append(val)
            if sig and sig in signals:
                signals[sig] += 1
        if scores:
            total = len(scores)
            avg = round(sum(scores) / total, 3)
            stress_pct = round((signals["stress"] + signals["avoidance"]) / total * 100, 1)
            pattern_data[pattern] = {
                "average": avg, "label": PATTERN_LABELS[pattern],
                "signal": "stress" if avg < -0.15 else "positive" if avg > 0.15 else "neutral",
                "respondents": total, "stress_driven_pct": stress_pct,
                "signal_breakdown": signals,
            }

    prev_week_start = week_start - timedelta(days=7)
    prev_records = db.query(BSIWeeklyRecord).filter(BSIWeeklyRecord.week_start == prev_week_start).all()
    pop_delta = None
    if prev_records:
        prev_avg = sum(r.bsi_composite for r in prev_records) / len(prev_records)
        pop_delta = round(pop_bsi - prev_avg, 2)

    return {
        "population_bsi": pop_bsi, "population_delta": pop_delta,
        "user_count": len(records), "week": week_start.isoformat(),
        "patterns": pattern_data,
    }