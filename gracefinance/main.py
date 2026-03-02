"""
GraceFinance API
Smarter Finance is Right Around the Corner™

Run locally:
    uvicorn main:app --reload --port 8000

API docs available at:
    http://localhost:8000/docs

v2 UPDATE: Added social feed router
FIXED: Added dashboard_router to imports
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import engine, Base
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
from app.routers import me_router, index_summary_router, sse_router
from app.services.index_worker import start_scheduler, stop_scheduler

settings = get_settings()

# Create tables (use Alembic migrations in production)
Base.metadata.create_all(bind=engine)

# ── App initialization ──
is_prod = settings.app_env == "production"

app = FastAPI(
    title="GraceFinance API",
    description="Smarter Finance is Right Around the Corner™",
    version="2.0.0",
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
)

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

allowed_origins = list(set(allowed_origins))

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

# ── Grace AI Coach ──
app.include_router(grace_router)

# ── User Profile ──
app.include_router(profile_router)

# ── Reward Loop ──
app.include_router(me_router)
app.include_router(index_summary_router)
app.include_router(sse_router)

# ── Social Feed (NEW v2) ──
app.include_router(feed_router)


@app.get("/")
def root():
    return {
        "app": "GraceFinance",
        "tagline": "Smarter Finance is Right Around the Corner™",
        "version": "2.0.0",
        "docs": "/docs" if not is_prod else None,
        "data_engine": {
            "checkin": "/checkin/questions",
            "index": "/index/latest",
        },
        "coach": {
            "chat": "/grace/chat",
            "intro": "/grace/intro",
        },
        "profile": "/api/profile",
        "feed": "/feed/",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "engine": "active", "grace": "online", "feed": "active"}


@app.on_event("startup")
def on_startup():
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    stop_scheduler()