"""
Index Router — Grace Financial Confidence Index (GFCI)
═══════════════════════════════════════════════════════
v2.3 — SECURITY FIX: Admin endpoints now require authentication

CHANGES FROM v2.2:
  - /index/reset, /index/reset-user-data, /index/migrate-streak now
    require JWT auth + admin email whitelist. Previously had ZERO auth —
    anyone could wipe production data with a single POST.
  - /index/compute now requires JWT auth (any verified user).
  - /index/latest, /index/history, /index/methodology remain public.

Endpoints:
  GET  /index/latest            → Public — current GFCI composite
  GET  /index/history           → Public — GFCI over time
  GET  /index/methodology       → Public — methodology documentation
  POST /index/compute           → Auth required — trigger index computation
  POST /index/reset             → ADMIN ONLY — wipe index data
  POST /index/reset-user-data   → ADMIN ONLY — wipe ALL test data
  POST /index/migrate-streak    → ADMIN ONLY — add streak columns
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func as sqlfunc, distinct

from app.database import get_db
from app.models import User
from app.services.auth import get_current_user
from app.services.gfci_engine import (
    compute_daily_gfci,
    get_gfci_history,
    get_active_contributor_count,
    get_index_confidence_tier,
)
from app.models.checkin import DailyIndex, CheckInResponse


router = APIRouter(prefix="/index", tags=["GFCI Index"])

# ── Admin whitelist — only these emails can access destructive endpoints ──
ADMIN_EMAILS = {"zaclajeunesse1@gmail.com"}


def _require_admin(user: User):
    """Raise 403 if the user is not in the admin whitelist."""
    if user.email not in ADMIN_EMAILS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )


# ══════════════════════════════════════════
#  PUBLIC ENDPOINTS (no auth required)
# ══════════════════════════════════════════

@router.get("/latest")
def latest_index(
    segment: str = "national",
    db: Session = Depends(get_db),
):
    """Get the most recent GFCI composite, trend data, and active contributor count."""
    index = (
        db.query(DailyIndex)
        .filter(DailyIndex.segment == segment)
        .order_by(desc(DailyIndex.computed_at))
        .first()
    )

    contributor_count = get_active_contributor_count(db)

    if not index:
        return {
            "published": False,
            "confidence_tier": "preview",
            "message": "No index data yet. Need check-ins from users first.",
            "gfci_composite": None,
            "contributors": contributor_count,
        }

    tier = get_index_confidence_tier(index.user_count)

    return {
        "published": True,
        "confidence_tier": tier,
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
            "smoothing": "EMA α=0.15 (adaptive for new users)",
            "windows": {
                "30d": {"weight": 0.20, "role": "Recent behavioral signal"},
                "60d": {"weight": 0.35, "role": "Trend signal"},
                "90d": {"weight": 0.45, "role": "Baseline stability signal"},
            },
            "movement_caps": {
                "fcs_per_day": "±3 points (adaptive: up to ±10 for new users)",
                "pillar_per_day": "±2 points (adaptive: up to ±15 for new users)",
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
            "confidence_tiers": {
                "preview": "< 50 active users",
                "beta": "50–199 active users",
                "published": "200+ active users",
            },
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
            "Adaptive movement caps (responsive early, stable at maturity)",
            "Minimum participation thresholds for confident scores",
            "Consistency weighting rewards regular engagement",
            "Daily upsert prevents duplicate index entries",
        ],
        "computation_schedule": "Daily at 12:05 AM ET (05:05 UTC) + real-time after each check-in",
    }


# ══════════════════════════════════════════
#  AUTHENTICATED ENDPOINTS
# ══════════════════════════════════════════

@router.post("/compute")
def trigger_compute(
    segment: str = "national",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Manually trigger GFCI computation.
    Requires authentication (any verified user).
    In production, this runs on a nightly scheduler (12:05 AM ET).
    """
    index = compute_daily_gfci(db, segment)

    if not index:
        return {
            "message": "Could not compute index — no eligible user data.",
            "gfci_composite": None,
        }

    return {
        "message": "GFCI computed and saved",
        "confidence_tier": get_index_confidence_tier(index.user_count),
        "gfci_composite": index.gf_rwi_composite,
        "fcs_average": index.fcs_value,
        "user_count": index.user_count,
        "trend_direction": index.trend_direction,
        "snapshot_id": str(index.id),
    }


# ══════════════════════════════════════════
#  ADMIN-ONLY ENDPOINTS
# ══════════════════════════════════════════

@router.post("/reset")
def reset_index(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """ADMIN ONLY — wipe all daily_index rows and start fresh."""
    _require_admin(user)

    count = db.query(DailyIndex).count()
    db.query(DailyIndex).delete()
    db.commit()
    return {"message": f"Deleted {count} index rows. Ready for fresh compute."}


@router.post("/reset-user-data")
def reset_user_data(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """ADMIN ONLY — wipe all checkin responses, snapshots, index data, and reset streaks."""
    _require_admin(user)

    from app.models.checkin import UserMetricSnapshot
    from sqlalchemy import text
    r1 = db.query(CheckInResponse).delete()
    r2 = db.query(UserMetricSnapshot).delete()
    r3 = db.query(DailyIndex).delete()
    db.execute(text("UPDATE users SET current_streak = 0, last_checkin_date = NULL"))
    db.commit()
    return {"deleted": {"responses": r1, "snapshots": r2, "index_rows": r3}, "streak": "reset to 0"}


@router.post("/migrate-streak")
def migrate_streak(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """ADMIN ONLY — add streak columns to users table. Run once then remove."""
    _require_admin(user)

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