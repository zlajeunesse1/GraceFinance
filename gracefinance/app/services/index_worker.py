"""
GraceFinance Index Worker - FIXED
==================================
Updated to handle UUID primary keys and prevent IntegrityErrors.
FIXED: Function definition order to resolve Pylance "not defined" errors.
FIXED: Added get_cached_index(), start_scheduler(), stop_scheduler().
"""

import logging
import uuid
from datetime import datetime, date, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.database import SessionLocal
from app.models.contribution_queue import IndexContributionEvent
from app.models.checkin import DailyIndex

logger = logging.getLogger("gracefinance.index_worker")

# ============================================================
#  CACHE & HELPERS
# ============================================================

_index_cache = {
    "gci": None,
    "fcs": None,
    "bsi": None,
    "spi": None,
    "trend_direction": None,
    "last_updated_at": None,
    "contributors_today": 0,
    "data_quality_score": None,
}


def get_cached_index() -> dict:
    """Public accessor for the in-memory index cache."""
    return dict(_index_cache)


def _refresh_cache(db, today):
    """Refreshes the in-memory cache with the latest DailyIndex data."""
    latest = (
        db.query(DailyIndex)
        .filter(
            and_(
                DailyIndex.index_date == today,
                DailyIndex.segment == "national",
            )
        )
        .first()
    )
    if latest:
        _index_cache["gci"] = float(latest.gf_rwi_composite) if latest.gf_rwi_composite else None
        _index_cache["trend_direction"] = latest.trend_direction
        _index_cache["last_updated_at"] = latest.computed_at.isoformat() if latest.computed_at else None

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


def _compute_trend(db, today, current_gci):
    """Performs trend analysis and updates the DailyIndex."""
    rows = (
        db.query(DailyIndex.index_date, DailyIndex.gf_rwi_composite)
        .filter(
            and_(
                DailyIndex.index_date >= today - timedelta(days=7),
                DailyIndex.segment == "national",
            )
        )
        .order_by(DailyIndex.index_date)
        .all()
    )

    if len(rows) < 2:
        return

    values = [float(r.gf_rwi_composite) for r in rows]
    trend = "UP" if values[-1] > values[0] else "DOWN"

    today_row = (
        db.query(DailyIndex)
        .filter(and_(DailyIndex.index_date == today, DailyIndex.segment == "national"))
        .first()
    )
    if today_row:
        today_row.trend_direction = trend
        db.flush()


def _fallback_raw_computation(db, today, now):
    """Refined raw aggregation to ensure DailyIndex creation with UUIDs."""
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
        return None

    n = len(all_today)
    avg_fcs = sum(float(e.fcs_composite or 0) for e in all_today) / n
    fcs_value = avg_fcs * 100

    existing = (
        db.query(DailyIndex)
        .filter(and_(DailyIndex.index_date == today, DailyIndex.segment == "national"))
        .first()
    )

    if existing:
        existing.fcs_value = round(fcs_value, 2)
        existing.gf_rwi_composite = round(fcs_value, 2)
        existing.user_count = n
        existing.computed_at = now
        db.flush()
        return existing
    else:
        new_index = DailyIndex(
            index_date=today,
            segment="national",
            fcs_value=round(fcs_value, 2),
            gf_rwi_composite=round(fcs_value, 2),
            user_count=n,
            computed_at=now,
        )
        db.add(new_index)
        db.flush()
        return new_index


# ============================================================
#  MAIN WORKER JOB
# ============================================================

def process_contribution_queue():
    db = SessionLocal()
    try:
        today = date.today()

        # 1. Claim pending events
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
            logger.info("Index worker: no pending contributions.")
            _refresh_cache(db, today)
            return

        logger.info(f"Index worker: processing {len(pending)} contributions.")

        # Mark for processing
        for event in pending:
            event.status = "processing"
        db.flush()

        # 2. Finalize status before heavy math
        now = datetime.now(timezone.utc)
        for event in pending:
            event.status = "counted"
            event.processed_at = now
        db.flush()

        # 3. Compute index (Routes to Quality or Fallback)
        try:
            from app.services.data_quality import compute_weighted_index
            index = compute_weighted_index(db, segment="national")

            if not index:
                logger.warning("Index worker: compute_weighted_index returned None, falling back.")
                index = _fallback_raw_computation(db, today, now)
        except (ImportError, Exception) as e:
            logger.warning(f"Quality pipeline failed or missing ({e}), using raw computation.")
            index = _fallback_raw_computation(db, today, now)

        # 4. Process Trends
        if index:
            gf_rwi = float(index.gf_rwi_composite) if index.gf_rwi_composite else 0.0
            _compute_trend(db, today, gf_rwi)

            # 5. Compute Behavioral Engine trends
            try:
                from app.services.intelligence_engine import compute_index_trend_fields
                compute_index_trend_fields(db, segment="national")
                logger.info("Index worker: intelligence engine trend fields computed.")
            except (ImportError, Exception):
                pass

        db.commit()
        _refresh_cache(db, today)

    except Exception as e:
        db.rollback()
        logger.error(f"Index worker failed: {e}", exc_info=True)
        db.query(IndexContributionEvent).filter(
            IndexContributionEvent.status == "processing"
        ).update({"status": "pending"})
        db.commit()
    finally:
        db.close()


# ============================================================
#  SCHEDULER
# ============================================================

_scheduler = None


def start_scheduler():
    """Start the background scheduler for index processing."""
    global _scheduler
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        _scheduler = BackgroundScheduler()
        _scheduler.add_job(process_contribution_queue, "interval", minutes=15)
        _scheduler.start()
        logger.info("Index worker scheduler started.")
    except ImportError:
        logger.warning(
            "apscheduler not installed — index worker will not run automatically. "
            "Install with: pip install apscheduler"
        )


def stop_scheduler():
    """Shut down the background scheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        logger.info("Index worker scheduler stopped.")
