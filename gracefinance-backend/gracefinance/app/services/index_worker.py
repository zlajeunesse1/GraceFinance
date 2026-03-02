"""
GraceFinance Index Worker
==========================
Background job that consumes the contribution queue and
updates the DailyIndex on a schedule.

Uses APScheduler (pure Python, no Redis/Celery required).
For production scale, swap to Celery + Redis.

Setup:
  - Import `start_scheduler()` in main.py
  - Call it on app startup
  - Worker runs every hour (configurable)

Place at: app/services/index_worker.py
"""

import logging
from datetime import datetime, date, timezone
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.database import SessionLocal
from app.models.contribution_queue import IndexContributionEvent
from app.models.checkin import DailyIndex

logger = logging.getLogger("gracefinance.index_worker")


# ============================================================
#  CACHE: In-memory last-published index (for SSE/polling)
# ============================================================

_index_cache = {
    "gci": None,
    "csi": None,
    "dpi": None,
    "frs": None,
    "trend_direction": None,
    "last_updated_at": None,
    "contributors_today": 0,
}


def get_cached_index() -> dict:
    """Return the last-published index from memory. No DB hit."""
    return dict(_index_cache)


def invalidate_cache():
    """Force cache refresh on next read."""
    _index_cache["last_updated_at"] = None


# ============================================================
#  MAIN WORKER JOB
# ============================================================

def process_contribution_queue():
    """
    Main scheduled job. Runs every hour (or on demand).

    1. Claim all pending events → "processing"
    2. Re-run index aggregation for today
    3. Mark events as "counted"
    4. Update the in-memory cache
    """
    db: Session = SessionLocal()
    try:
        today = date.today()

        # -- 1. Claim pending events --
        pending = (
            db.query(IndexContributionEvent)
            .filter(
                and_(
                    IndexContributionEvent.status == "pending",
                    IndexContributionEvent.checkin_date == today,
                )
            )
            .all()
        )

        if not pending:
            logger.info("Index worker: no pending contributions to process.")
            _refresh_cache(db, today)
            return

        logger.info(f"Index worker: processing {len(pending)} contributions.")

        # Mark as processing
        for event in pending:
            event.status = "processing"
        db.flush()

        # -- 2. Recompute today's DailyIndex --
        # Pull ALL counted + processing contributions for today
        all_today = (
            db.query(IndexContributionEvent)
            .filter(
                and_(
                    IndexContributionEvent.checkin_date == today,
                    IndexContributionEvent.status.in_(["processing", "counted"]),
                )
            )
            .all()
        )

        if not all_today:
            logger.warning("Index worker: no contributions to aggregate.")
            db.rollback()
            return

        # Aggregate scores
        n = len(all_today)
        avg_stability = sum(float(e.current_stability or 0) for e in all_today) / n
        avg_outlook = sum(float(e.future_outlook or 0) for e in all_today) / n
        avg_purchasing = sum(float(e.purchasing_power or 0) for e in all_today) / n
        avg_emergency = sum(float(e.emergency_readiness or 0) for e in all_today) / n
        avg_income = sum(float(e.income_adequacy or 0) for e in all_today) / n
        avg_fcs = sum(float(e.fcs_composite or 0) for e in all_today) / n
        avg_bsi = sum(float(e.bsi_score or 0) for e in all_today) / n

        # Compute sub-indexes (simplified — your index_engine_service has the real formulas)
        # CSI: Consumer Stress Index — higher stress = higher CSI
        # Using inverse of stability + emergency as stress proxy
        csi = ((1 - avg_stability) * 0.5 + (1 - avg_emergency) * 0.5) * 100

        # DPI: Discretionary Pressure Index
        dpi = ((1 - avg_purchasing) * 0.6 + (1 - avg_income) * 0.4) * 100

        # FRS: Financial Resilience Score (higher = more resilient)
        frs = (avg_stability * 0.3 + avg_emergency * 0.3 + avg_outlook * 0.2 + avg_income * 0.2) * 100

        # GCI: Grace Composite Index
        gci = (csi * 0.35) + (dpi * 0.35) + ((100 - frs) * 0.30)
        gci = max(0, min(100, gci))

        # -- 3. Upsert today's DailyIndex row --
        existing = (
            db.query(DailyIndex)
            .filter(DailyIndex.date == today)
            .first()
        )

        now = datetime.now(timezone.utc)

        if existing:
            existing.csi_close = round(csi, 2)
            existing.dpi_close = round(dpi, 2)
            existing.frs_close = round(frs, 2)
            existing.gci_close = round(gci, 2)
            existing.checkin_volume = n
            existing.updated_at = now
        else:
            new_index = DailyIndex(
                date=today,
                csi_close=round(csi, 2),
                dpi_close=round(dpi, 2),
                frs_close=round(frs, 2),
                gci_close=round(gci, 2),
                checkin_volume=n,
            )
            db.add(new_index)

        # -- 4. Mark events as counted --
        for event in pending:
            event.status = "counted"
            event.processed_at = now
        db.flush()

        # -- 5. Compute trend direction --
        _compute_trend(db, today, gci)

        db.commit()

        # -- 6. Update cache --
        _refresh_cache(db, today)

        logger.info(
            f"Index worker: updated DailyIndex for {today}. "
            f"GCI={gci:.2f}, contributors={n}"
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Index worker failed: {e}", exc_info=True)
        # Mark processing events back to pending for retry
        try:
            db.query(IndexContributionEvent).filter(
                IndexContributionEvent.status == "processing"
            ).update({"status": "pending"})
            db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


def _compute_trend(db: Session, today: date, current_gci: float):
    """Compute 7-day slope and trend direction for today's index."""
    from datetime import timedelta

    # Get last 7 days of GCI
    rows = (
        db.query(DailyIndex.date, DailyIndex.gci_close)
        .filter(DailyIndex.date >= today - timedelta(days=7))
        .order_by(DailyIndex.date)
        .all()
    )

    if len(rows) < 2:
        return

    # Simple OLS slope
    values = [float(r.gci_close) for r in rows]
    n = len(values)
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    slope_7d = numerator / denominator if denominator != 0 else 0

    # Volatility (std dev)
    variance = sum((v - y_mean) ** 2 for v in values) / n
    volatility = variance ** 0.5

    # Trend direction
    if slope_7d > 0.1:
        trend = "UP"
    elif slope_7d < -0.1:
        trend = "DOWN"
    else:
        trend = "FLAT"

    # Update today's row
    today_row = db.query(DailyIndex).filter(DailyIndex.date == today).first()
    if today_row:
        today_row.gci_slope_7d = round(slope_7d, 4)
        today_row.gci_volatility_7d = round(volatility, 4)
        today_row.trend_direction = trend
        db.flush()


def _refresh_cache(db: Session, today: date):
    """Refresh the in-memory cache from the latest DailyIndex row."""
    latest = db.query(DailyIndex).filter(DailyIndex.date == today).first()
    if latest:
        _index_cache["gci"] = float(latest.gci_close) if latest.gci_close else None
        _index_cache["csi"] = float(latest.csi_close) if latest.csi_close else None
        _index_cache["dpi"] = float(latest.dpi_close) if latest.dpi_close else None
        _index_cache["frs"] = float(latest.frs_close) if latest.frs_close else None
        _index_cache["trend_direction"] = latest.trend_direction
        _index_cache["last_updated_at"] = (
            latest.updated_at.isoformat() if hasattr(latest, "updated_at") and latest.updated_at
            else datetime.now(timezone.utc).isoformat()
        )

    # Count today's contributors
    count = (
        db.query(func.count(IndexContributionEvent.id))
        .filter(
            and_(
                IndexContributionEvent.checkin_date == today,
                IndexContributionEvent.status == "counted",
            )
        )
        .scalar()
    )
    _index_cache["contributors_today"] = count or 0


# ============================================================
#  SCHEDULER SETUP (call from main.py)
# ============================================================

_scheduler = None


def start_scheduler():
    """Start the APScheduler background job. Call once on app startup."""
    global _scheduler

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        logger.warning(
            "APScheduler not installed. Index updates will only run manually. "
            "Install with: pip install apscheduler"
        )
        return

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        process_contribution_queue,
        "interval",
        hours=1,
        id="index_worker",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),  # Run immediately on startup
    )
    _scheduler.start()
    logger.info("Index worker scheduler started. Running every 1 hour.")


def stop_scheduler():
    """Gracefully shut down the scheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("Index worker scheduler stopped.")
