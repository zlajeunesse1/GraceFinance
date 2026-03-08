"""
Index Router — Grace Financial Confidence Index (GFCI)
═══════════════════════════════════════════════════════
Endpoints:
  GET  /index/latest            → Current GFCI composite + pillar breakdown + contributor count
  GET  /index/history           → GFCI over time for trending
  POST /index/compute           → Manually trigger index computation (dev/admin)
  POST /index/reset             → Wipe index data and start fresh (dev only)
  POST /index/migrate-streak    → Add streak columns (run once, then remove)
  POST /index/reset-user-data   → Wipe all test data (dev only)
  GET  /index/methodology       → Public methodology documentation

Wired to: app/services/gfci_engine.py (v4 institutional engine)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc, func as sqlfunc, distinct

from app.database import get_db
from app.services.gfci_engine import (
    compute_daily_gfci,
    get_gfci_history,
)
from app.models.checkin import DailyIndex, CheckInResponse


router = APIRouter(prefix="/index", tags=["GFCI Index"])


@router.get("/latest")
def latest_index(
    segment: str = "national",
    db: Session = Depends(get_db),
):
    """Get the most recent GFCI composite, trend data, and contributor count."""
    index = (
        db.query(DailyIndex)
        .filter(DailyIndex.segment == segment)
        .order_by(desc(DailyIndex.computed_at))
        .first()
    )

    # Total unique users who have ever submitted a check-in
    contributor_count = (
        db.query(sqlfunc.count(distinct(CheckInResponse.user_id))).scalar() or 0
    )

    if not index:
        return {
            "published": False,
            "message": "No index data yet. Need check-ins from users first.",
            "gfci_composite": None,
            "contributors": contributor_count,
        }

    return {
        "published": True,
        "index_date": index.index_date.isoformat(),
        "segment": index.segment,
        "gfci_composite": index.gf_rwi_composite,
        "fcs_average": index.fcs_value,
        "user_count": index.user_count,
        "contributors": contributor_count,
        "trend_direction": index.trend_direction,
        "gci_slope_3d": index.gci_slope_3d,
        "gci_slope_7d": index.gci_slope_7d,
        "gci_volatility_7d": index.gci_volatility_7d,
    }


@router.get("/history")
def index_history(
    segment: str = "national",
    days: int = 30,
    db: Session = Depends(get_db),
):
    """Get GFCI history for the frontend trend chart."""
    data = get_gfci_history(db, segment, days)

    return {
        "segment": segment,
        "days": days,
        "data_points": [
            {
                "date": d.index_date.isoformat(),
                "gfci": d.gf_rwi_composite,
                "fcs": d.fcs_value,
                "users": d.user_count,
                "trend": d.trend_direction,
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
    Manually trigger GFCI computation.
    In production, this runs on a nightly scheduler (12:05 AM ET).
    For dev/testing, hit this endpoint to compute on demand.
    """
    index = compute_daily_gfci(db, segment)

    if not index:
        return {
            "message": "Could not compute index — no eligible user data.",
            "gfci_composite": None,
        }

    return {
        "message": "GFCI computed and saved",
        "gfci_composite": index.gf_rwi_composite,
        "fcs_average": index.fcs_value,
        "user_count": index.user_count,
        "trend_direction": index.trend_direction,
        "snapshot_id": str(index.id),
    }


@router.post("/reset")
def reset_index(
    db: Session = Depends(get_db),
):
    """Dev tool — wipe all daily_index rows and start fresh."""
    count = db.query(DailyIndex).count()
    db.query(DailyIndex).delete()
    db.commit()
    return {"message": f"Deleted {count} index rows. Ready for fresh compute."}


@router.post("/reset-user-data")
def reset_user_data(
    db: Session = Depends(get_db),
):
    """Dev tool — wipe all checkin responses, snapshots, index data, and reset streaks."""
    from app.models.checkin import UserMetricSnapshot
    from sqlalchemy import text
    r1 = db.query(CheckInResponse).delete()
    r2 = db.query(UserMetricSnapshot).delete()
    r3 = db.query(DailyIndex).delete()
    db.execute(text("UPDATE users SET current_streak = 0, last_checkin_date = NULL"))
    db.commit()
    return {"deleted": {"responses": r1, "snapshots": r2, "index_rows": r3}, "streak": "reset to 0"}


@router.post("/migrate-streak")
def migrate_streak(db: Session = Depends(get_db)):
    """Temporary: add streak columns to users table. Run once then remove."""
    from sqlalchemy import text
    results = []
    try:
        db.execute(text("ALTER TABLE users ADD COLUMN current_streak INTEGER NOT NULL DEFAULT 0"))
        db.commit()
        results.append("Added current_streak")
    except Exception as e:
        db.rollback()
        results.append(f"current_streak: {str(e)[:80]}")
    try:
        db.execute(text("ALTER TABLE users ADD COLUMN last_checkin_date TIMESTAMP WITH TIME ZONE"))
        db.commit()
        results.append("Added last_checkin_date")
    except Exception as e:
        db.rollback()
        results.append(f"last_checkin_date: {str(e)[:80]}")
    return {"results": results}


@router.get("/methodology")
def methodology():
    """Public methodology documentation for the GFCI."""
    return {
        "name": "Grace Financial Confidence Index (GFCI)",
        "version": "4.0",
        "description": (
            "A composite behavioral confidence indicator measuring real-time "
            "financial health across the GraceFinance user population. Built from "
            "daily behavioral check-ins measuring observable financial actions, "
            "not sentiment surveys."
        ),
        "scoring_engine": {
            "individual_score": "Financial Confidence Score (FCS)",
            "range": "0–100",
            "smoothing": "EMA α=0.15",
            "windows": {
                "30d": {"weight": 0.20, "role": "Recent behavioral signal"},
                "60d": {"weight": 0.35, "role": "Trend signal"},
                "90d": {"weight": 0.45, "role": "Baseline stability signal"},
            },
            "movement_caps": {
                "fcs_per_day": "±3 points",
                "pillar_per_day": "±2 points",
            },
            "pillars": {
                "current_stability": {"weight": 0.30, "signals": "Payment compliance, income predictability"},
                "future_outlook": {"weight": 0.25, "signals": "Saving actions, goal progress, debt trajectory"},
                "purchasing_power": {"weight": 0.20, "signals": "Consumption shifts, spending capacity"},
                "emergency_readiness": {"weight": 0.15, "signals": "Cushion building, liquidity, shock absorption"},
                "financial_agency": {"weight": 0.10, "signals": "Engagement, automation, proactive management"},
            },
        },
        "population_index": {
            "name": "GFCI",
            "aggregation": "Participation-weighted mean of individual FCS scores",
            "smoothing": "EMA α=0.10",
            "movement_cap": "±5 points per day",
            "minimum_users": 10,
            "stale_cutoff": "14 days",
        },
        "behavioral_shift_indicator": {
            "name": "BSI",
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
        "data_integrity": [
            "Outlier dampening (2σ threshold)",
            "Multi-window blending prevents single-day distortion",
            "Movement caps prevent artificial volatility",
            "Minimum participation thresholds for confident scores",
            "Consistency weighting rewards regular engagement",
        ],
        "computation_schedule": "Daily at 12:05 AM ET (05:05 UTC)",
    }