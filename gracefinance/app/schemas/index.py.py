"""
Index Router — Platform-wide GraceFinance index endpoints.

GET /index/latest — most recent DailyIndex
GET /index/history — time-series for charting
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.daily_index import DailyIndex
from app.schemas.index import IndexLatestResponse, IndexHistoryResponse, IndexHistoryItem

router = APIRouter(prefix="/index", tags=["platform-index"])

RANGE_MAP = {
    "30d": 30,
    "6m": 180,
    "1y": 365,
}


@router.get("/latest", response_model=IndexLatestResponse)
def get_latest_index(db: Session = Depends(get_db)):
    """Returns the most recent DailyIndex row."""
    row = db.query(DailyIndex).order_by(desc(DailyIndex.date)).first()

    if row is None:
        # Return neutral defaults if no index data exists yet
        return IndexLatestResponse(
            date=date.today(),
            csi=50.0,
            dpi=50.0,
            frs=50.0,
            gci=50.0,
            checkin_volume=0,
            platform_mood=None,
            platform_stress=None,
            impulse_rate=None,
            gci_slope_3d=None,
            gci_slope_7d=None,
            gci_volatility_7d=None,
            trend_direction=None,
        )

    return IndexLatestResponse(
        date=row.date,
        csi=row.csi_close,
        dpi=row.dpi_close,
        frs=row.frs_close,
        gci=row.gci_close,
        checkin_volume=row.checkin_volume,
        platform_mood=row.avg_mood_score,
        platform_stress=row.avg_stress_level,
        impulse_rate=row.impulse_rate,
        gci_slope_3d=row.gci_slope_3d,
        gci_slope_7d=row.gci_slope_7d,
        gci_volatility_7d=row.gci_volatility_7d,
        trend_direction=row.trend_direction,
    )


@router.get("/history", response_model=IndexHistoryResponse)
def get_index_history(
    range: str = Query(default="30d", regex="^(30d|6m|1y)$"),
    db: Session = Depends(get_db),
):
    """Returns DailyIndex rows for the requested range, shaped for time-series charting."""
    days = RANGE_MAP.get(range, 30)
    cutoff = date.today() - timedelta(days=days)

    rows = db.query(DailyIndex).filter(
        DailyIndex.date >= cutoff,
    ).order_by(DailyIndex.date).all()

    return IndexHistoryResponse(
        data=[
            IndexHistoryItem(
                date=r.date,
                csi=r.csi_close,
                dpi=r.dpi_close,
                frs=r.frs_close,
                gci=r.gci_close,
                gci_slope_7d=r.gci_slope_7d,
                gci_volatility_7d=r.gci_volatility_7d,
                trend_direction=r.trend_direction,
            )
            for r in rows
        ],
        range=range,
    )
