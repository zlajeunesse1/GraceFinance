"""
Index Router — GraceFinance Real World Index (GF-RWI) endpoints.

Endpoints:
  GET  /index/latest            → Current GF-RWI composite + sub-indices
  GET  /index/history           → GF-RWI over time for trending
  POST /index/compute           → Manually trigger index computation (admin/dev)
  GET  /index/methodology       → Public methodology documentation
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.index_engine_service import (
    compute_daily_index,
    get_latest_index,
    get_index_history,
)
from app.schemas.checkin_schemas import IndexOut, IndexHistory


router = APIRouter(prefix="/index", tags=["GF-RWI Index"])


@router.get("/latest")
def latest_index(
    segment: str = "national",
    db: Session = Depends(get_db),
):
    """Get the most recent GF-RWI composite and all sub-indices."""
    index = get_latest_index(db, segment)

    if not index:
        return {
            "message": "No index data yet. Complete some check-ins first!",
            "gf_rwi_composite": None,
        }

    return {
        "index_date": index.index_date.isoformat(),
        "segment": index.segment,
        "gf_rwi_composite": index.gf_rwi_composite,
        "fcs": {
            "composite": index.fcs_value,
            "current_stability": index.fcs_current_stability,
            "future_outlook": index.fcs_future_outlook,
            "purchasing_power": index.fcs_purchasing_power,
            "debt_pressure": index.fcs_debt_pressure,
            "financial_agency": index.fcs_financial_agency,
        },
        "bsi": index.bsi_value,
        "spi": index.spi_value,
        "user_count": index.user_count,
    }


@router.get("/history")
def index_history(
    segment: str = "national",
    days: int = 30,
    db: Session = Depends(get_db),
):
    """Get GF-RWI history for the frontend trend chart."""
    data = get_index_history(db, segment, days)

    return {
        "segment": segment,
        "days": days,
        "data_points": [
            {
                "date": d.index_date.isoformat(),
                "gf_rwi": d.gf_rwi_composite,
                "fcs": d.fcs_value,
                "bsi": d.bsi_value,
                "spi": d.spi_value,
                "users": d.user_count,
            }
            for d in data
        ],
    }


@router.post("/compute")
def trigger_compute(
    segment: str = "national",
    db: Session = Depends(get_db),
):
    """
    Manually trigger GF-RWI computation.
    In production, this runs on a nightly scheduler.
    For dev, hit this endpoint to compute on demand.
    """
    index = compute_daily_index(db, segment)

    return {
        "message": "GF-RWI computed and saved",
        "gf_rwi_composite": index.gf_rwi_composite,
        "fcs": index.fcs_value,
        "bsi": index.bsi_value,
        "user_count": index.user_count,
        "snapshot_id": str(index.id),
    }


@router.get("/methodology")
def methodology():
    """Public methodology documentation for the GF-RWI."""
    return {
        "name": "GraceFinance Real World Index (GF-RWI)",
        "version": "1.0",
        "description": (
            "A composite economic indicator measuring real-time financial health "
            "and purchasing experience of working Americans, built from daily "
            "behavioral check-ins rather than lagging government surveys."
        ),
        "sub_indices": {
            "FCS": {
                "name": "Financial Confidence Score",
                "weight": 0.60,
                "range": "0–100",
                "dimensions": {
                    "current_stability": {"weight": 0.30, "questions": 5},
                    "future_outlook": {"weight": 0.25, "questions": 4},
                    "purchasing_power": {"weight": 0.20, "questions": 4},
                    "debt_pressure": {"weight": 0.15, "questions": 3},
                    "financial_agency": {"weight": 0.10, "questions": 3},
                },
            },
            "BSI": {
                "name": "Behavioral Shift Indicator",
                "weight": 0.40,
                "range": "-100 to +100",
                "frequency": "Weekly (Sundays)",
                "patterns_tracked": [
                    "category_downgrading",
                    "credit_substitution",
                    "subscription_churn",
                    "delayed_purchasing",
                    "cash_hoarding",
                ],
            },
            "SPI": {
                "name": "Spending Pressure Index",
                "status": "Phase 2 — requires transaction data integration",
            },
        },
        "normalization": "Fixed logical bounds (MVP). Rolling 90-day planned for scale.",
        "computation_schedule": "Daily at 00:05 UTC",
    }