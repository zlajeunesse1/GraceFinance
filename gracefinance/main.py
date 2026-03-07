"""
GraceFinance API
Smarter Finance is Right Around the Corner™

Run locally:
    uvicorn main:app --reload --port 8000

API docs available at:
    http://localhost:8000/docs
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
from app.routers.legal_routes import router as legal_router
from app.routers import me_router

settings = get_settings()

# Create tables (use Alembic migrations in production)
Base.metadata.create_all(bind=engine)

# ── App initialization ──
is_prod = settings.app_env == "production"

app = FastAPI(
    title="GraceFinance API",
    description="Smarter Finance is Right Around the Corner™",
    version="4.0.0",
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

# ── Grace AI Coach ──
app.include_router(grace_router)

# ── User Profile ──
app.include_router(profile_router)

# ── User Metrics ──
app.include_router(me_router)

# ── Social Feed ──
app.include_router(feed_router)

# ── Migration (temporary — remove after running) ──


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
        },
        "coach": {
            "chat": "/grace/chat",
            "intro": "/grace/intro",
        },
        "profile": "/api/profile",
        "feed": "/feed/",
        "legal": {
            "terms": "/legal/terms",
            "privacy": "/legal/privacy",
            "refund": "/legal/refund",
        },
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "engine": "active", "grace": "online", "feed": "active"}