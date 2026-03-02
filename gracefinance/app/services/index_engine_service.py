"""
Index Engine Service — v2 (FCS Pillar Update)
══════════════════════════════════════════════
CHANGES FROM v1:
  - avg_er → avg_dp, avg_ia → avg_fa
  - fcs_er → fcs_dp, fcs_ia → fcs_fa in _save_index
  - fcs_debt_pressure → fcs_debt_pressure on DailyIndex
  - fcs_financial_agency → fcs_financial_agency on DailyIndex

REPLACES: app/services/index_engine_service.py
"""

from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, cast, Date, desc
from sqlalchemy.orm import Session

from app.models.checkin import UserMetricSnapshot, DailyIndex


FCS_WEIGHT = Decimal("0.60")
BSI_WEIGHT = Decimal("0.40")

TREND_UP_THRESHOLD = Decimal("0.5")
TREND_DOWN_THRESHOLD = Decimal("-0.5")


def compute_daily_index(db: Session, segment: str = "national") -> DailyIndex:
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    today_end = today_start + timedelta(days=1)

    latest_subq = (
        db.query(
            UserMetricSnapshot.user_id,
            func.max(UserMetricSnapshot.computed_at).label("latest"),
        )
        .filter(UserMetricSnapshot.computed_at >= today_start)
        .filter(UserMetricSnapshot.computed_at < today_end)
        .group_by(UserMetricSnapshot.user_id)
        .subquery()
    )

    snapshots = (
        db.query(UserMetricSnapshot)
        .join(
            latest_subq,
            (UserMetricSnapshot.user_id == latest_subq.c.user_id)
            & (UserMetricSnapshot.computed_at == latest_subq.c.latest),
        )
        .all()
    )

    if not snapshots:
        snapshots = _get_most_recent_snapshots(db)

    if not snapshots:
        return _save_index(db, today, segment, user_count=0)

    # Average FCS dimensions (UPDATED)
    n = len(snapshots)
    avg_cs = sum(float(s.current_stability or 0) for s in snapshots) / n
    avg_fo = sum(float(s.future_outlook or 0) for s in snapshots) / n
    avg_pp = sum(float(s.purchasing_power or 0) for s in snapshots) / n
    avg_dp = sum(float(s.debt_pressure or 0) for s in snapshots) / n       # was avg_er
    avg_fa = sum(float(s.financial_agency or 0) for s in snapshots) / n    # was avg_ia

    fcs_composite = sum(float(s.fcs_composite or 0) for s in snapshots) / n

    bsi_snapshots = [s for s in snapshots if s.bsi_score is not None]
    bsi_value = (
        sum(float(s.bsi_score) for s in bsi_snapshots) / len(bsi_snapshots)
        if bsi_snapshots
        else None
    )

    if bsi_value is not None:
        bsi_normalized = (bsi_value + 100) / 2
        gf_rwi = float(FCS_WEIGHT) * fcs_composite + float(BSI_WEIGHT) * bsi_normalized
    else:
        gf_rwi = fcs_composite

    slope_7d, volatility_7d = _compute_trend_metrics(db, segment)
    trend_direction = _classify_trend(slope_7d)

    return _save_index(
        db, today, segment,
        fcs_value=round(fcs_composite, 2),
        bsi_value=round(bsi_value, 2) if bsi_value is not None else None,
        gf_rwi=round(gf_rwi, 2),
        fcs_cs=round(avg_cs, 2),
        fcs_fo=round(avg_fo, 2),
        fcs_pp=round(avg_pp, 2),
        fcs_dp=round(avg_dp, 2),    # was fcs_er
        fcs_fa=round(avg_fa, 2),    # was fcs_ia
        user_count=n,
        checkin_volume=sum(s.checkin_count or 0 for s in snapshots),
        slope_7d=slope_7d,
        volatility_7d=volatility_7d,
        trend_direction=trend_direction,
    )


def _get_most_recent_snapshots(db: Session) -> list:
    latest_subq = (
        db.query(
            UserMetricSnapshot.user_id,
            func.max(UserMetricSnapshot.computed_at).label("latest"),
        )
        .group_by(UserMetricSnapshot.user_id)
        .subquery()
    )

    return (
        db.query(UserMetricSnapshot)
        .join(
            latest_subq,
            (UserMetricSnapshot.user_id == latest_subq.c.user_id)
            & (UserMetricSnapshot.computed_at == latest_subq.c.latest),
        )
        .all()
    )


def _save_index(
    db: Session,
    index_date: date,
    segment: str,
    fcs_value: float = 0,
    bsi_value: Optional[float] = None,
    gf_rwi: float = 0,
    fcs_cs: float = 0,
    fcs_fo: float = 0,
    fcs_pp: float = 0,
    fcs_dp: float = 0,    # was fcs_er
    fcs_fa: float = 0,    # was fcs_ia
    user_count: int = 0,
    checkin_volume: int = 0,
    slope_7d: Optional[float] = None,
    volatility_7d: Optional[float] = None,
    trend_direction: str = "FLAT",
    spi_value: Optional[float] = None,
) -> DailyIndex:

    existing = (
        db.query(DailyIndex)
        .filter(DailyIndex.index_date == index_date, DailyIndex.segment == segment)
        .first()
    )

    if existing:
        index = existing
    else:
        index = DailyIndex(index_date=index_date, segment=segment)
        db.add(index)

    index.fcs_value = fcs_value
    index.bsi_value = bsi_value
    index.spi_value = spi_value
    index.gf_rwi_composite = gf_rwi
    index.fcs_current_stability = fcs_cs
    index.fcs_future_outlook = fcs_fo
    index.fcs_purchasing_power = fcs_pp
    index.fcs_debt_pressure = fcs_dp          # was fcs_debt_pressure
    index.fcs_financial_agency = fcs_fa       # was fcs_financial_agency
    index.user_count = user_count
    index.checkin_volume = checkin_volume
    index.gci_slope_7d = slope_7d
    index.gci_volatility_7d = volatility_7d
    index.trend_direction = trend_direction
    index.computed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(index)
    return index


def _compute_trend_metrics(db: Session, segment: str) -> tuple:
    cutoff = date.today() - timedelta(days=7)

    recent = (
        db.query(DailyIndex)
        .filter(DailyIndex.segment == segment, DailyIndex.index_date >= cutoff)
        .order_by(DailyIndex.index_date.asc())
        .all()
    )

    if len(recent) < 3:
        return None, None

    values = [float(r.gf_rwi_composite) for r in recent]
    n = len(values)

    x = list(range(n))
    sum_x = sum(x)
    sum_y = sum(values)
    sum_xy = sum(xi * yi for xi, yi in zip(x, values))
    sum_x2 = sum(xi ** 2 for xi in x)

    denominator = n * sum_x2 - sum_x ** 2
    if denominator == 0:
        slope = 0.0
    else:
        slope = round((n * sum_xy - sum_x * sum_y) / denominator, 4)

    mean = sum_y / n
    variance = sum((v - mean) ** 2 for v in values) / n
    volatility = round(variance ** 0.5, 4)

    return slope, volatility


def _classify_trend(slope: Optional[float]) -> str:
    if slope is None:
        return "FLAT"
    if slope > float(TREND_UP_THRESHOLD):
        return "UP"
    if slope < float(TREND_DOWN_THRESHOLD):
        return "DOWN"
    return "FLAT"


def get_latest_index(db: Session, segment: str = "national") -> Optional[DailyIndex]:
    return (
        db.query(DailyIndex)
        .filter(DailyIndex.segment == segment)
        .order_by(desc(DailyIndex.index_date))
        .first()
    )


def get_index_history(
    db: Session, segment: str = "national", days: int = 30
) -> list[DailyIndex]:
    cutoff = date.today() - timedelta(days=days)

    return (
        db.query(DailyIndex)
        .filter(DailyIndex.segment == segment, DailyIndex.index_date >= cutoff)
        .order_by(DailyIndex.index_date.asc())
        .all()
    )