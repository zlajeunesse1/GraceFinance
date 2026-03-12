"""
GraceFinance API
Smarter Finance is Right Around the Corner™

Run locally:
    uvicorn main:app --reload --port 8000

API docs available at:
    http://localhost:8000/docs

FIX #11 (MEDIUM): Scheduler jobs now log errors instead of silently swallowing them.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import get_settings
from app.database import engine, Base, SessionLocal
from app.routers import (
    auth_router,
    dashboard_router,
    billing_router,
    checkins_router,
    index_router,
    feed_router,
)
from app.routers.grace import router as grace_router
from app.routers.profile import router as profile_router
from app.routers.preferences import router as preferences_router
from app.routers.legal_routes import router as legal_router
from app.routers.export import router as export_router
from app.routers import me_router
from app.services.daily_emails import send_daily_engagement_emails
from app.services.gfci_engine import compute_daily_gfci
from app.services.weekly_report import send_weekly_reports
from app.routers.bsi_router import router as bsi_router

logger = logging.getLogger("gracefinance")

settings = get_settings()

# Create tables (use Alembic migrations in production)
Base.metadata.create_all(bind=engine)


# ── Scheduled Jobs ────────────────────────────────────────────────────────────

def scheduled_index_compute():
    """Recompute GF-RWI daily — safety net so the index never goes stale."""
    db = SessionLocal()
    try:
        compute_daily_gfci(db)
        db.commit()
        logger.info("Scheduled GFCI compute completed successfully")
    except Exception as e:
        db.rollback()
        logger.error(f"Scheduled GFCI compute failed: {e}", exc_info=True)
    finally:
        db.close()


def scheduled_daily_emails():
    """Wrapper for daily engagement emails with its own DB session."""
    try:
        send_daily_engagement_emails()
        logger.info("Daily engagement emails sent successfully")
    except Exception as e:
        logger.error(f"Daily engagement emails failed: {e}", exc_info=True)


def scheduled_weekly_reports():
    """Wrapper for weekly reports with error handling."""
    try:
        send_weekly_reports()
        logger.info("Weekly reports sent successfully")
    except Exception as e:
        logger.error(f"Weekly reports failed: {e}", exc_info=True)


# ── App initialization ──
is_prod = settings.app_env == "production"

app = FastAPI(
    title="GraceFinance API",
    description="Smarter Finance is Right Around the Corner™",
    version="4.0.0",
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
)

# ── Scheduler — all times in UTC ─────────────────────────────────────────────
scheduler = BackgroundScheduler()

# Daily engagement emails — 8:00 AM EST (13:00 UTC)
scheduler.add_job(
    scheduled_daily_emails,
    "cron",
    hour=13,
    minute=0,
    id="daily_engagement_email",
    replace_existing=True,
)

# Daily index recompute — 12:05 AM EST (05:05 UTC)
scheduler.add_job(
    scheduled_index_compute,
    "cron",
    hour=5,
    minute=5,
    id="daily_index_compute",
    replace_existing=True,
)

# Weekly personalized reports — Sunday 6:00 PM EST (23:00 UTC)
scheduler.add_job(
    scheduled_weekly_reports,
    "cron",
    day_of_week="sun",
    hour=23,
    minute=0,
    id="weekly_reports",
    replace_existing=True,
)

scheduler.start()

# ── CORS — explicit origins only, no wildcards ──
allowed_origins = [settings.frontend_url]

if not is_prod:
    allowed_origins.extend([
        "http://localhost:3000",
        "http://localhost:5173",
    ])

if settings.app_domain:
    allowed_origins.append(f"https://{settings.app_domain}")
    allowed_origins.append(f"https://www.{settings.app_domain}")

# Support additional origins from env (comma-separated)
extra_origins = getattr(settings, "extra_cors_origins", None)
if extra_origins:
    allowed_origins.extend([o.strip() for o in extra_origins.split(",") if o.strip()])

# Always include known deployment domains
allowed_origins.extend([
    "https://gracefinance.co",
    "https://www.gracefinance.co",
    "https://gracefinance-frontend.pages.dev",
])

allowed_origins = list(set(filter(None, allowed_origins)))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Core Routers ──
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(billing_router)

# ── Data Engine ──
app.include_router(checkins_router)
app.include_router(index_router)

# ── Behavioral Shift Indicator ──
app.include_router(bsi_router)

# ── Grace AI Coach ──
app.include_router(grace_router)

# ── User Profile ──
app.include_router(profile_router)

# ── User Preferences ──
app.include_router(preferences_router)

# ── User Metrics ──
app.include_router(me_router)

# ── Social Feed ──
app.include_router(feed_router)

# ── Data Export ──
app.include_router(export_router)

# ── Legal Pages ──
app.include_router(legal_router)


@app.get("/")
def root():
    return {
        "app": "GraceFinance",
        "tagline": "Smarter Finance is Right Around the Corner™",
        "version": "4.0.0",
        "docs": "/docs" if not is_prod else None,
        "data_engine": {
            "checkin": "/checkin/questions",
            "index": "/index/latest",
            "bsi": "/bsi/questions",
        },
        "coach": {
            "chat": "/grace/chat",
            "intro": "/grace/intro",
        },
        "profile": "/api/profile",
        "preferences": "/api/profile/preferences",
        "feed": "/feed/",
        "export": {
            "checkins": "/api/export/checkins",
            "fcs_trend": "/api/export/fcs-trend",
        },
        "legal": {
            "terms": "/legal/terms",
            "privacy": "/legal/privacy",
            "refund": "/legal/refund",
        },
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "engine": "active", "grace": "online", "feed": "active"}