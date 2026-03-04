"""
GraceFinance API
Smarter Finance is Right Around the Corner™

Run locally:
    uvicorn main:app --reload --port 8000

API docs available at:
    http://localhost:8000/docs
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import engine, Base
from app.routers import (
    # Original routers
    auth_router,
    debts_router,
    transactions_router,
    bills_router,
    dashboard_router,
    billing_router,
    # Data Engine routers
    checkins_router,
    index_router,
)
# Grace AI Coach
from app.routers.grace import router as grace_router

settings = get_settings()

# Create database tables (use Alembic migrations in production)
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="GraceFinance API",
    description="Smarter Finance is Right Around the Corner™",
    version="1.1.0",
)

# ── Build allowed origins list dynamically ──
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
]

# Add FRONTEND_URL from env/settings if set
if settings.frontend_url:
    allowed_origins.append(settings.frontend_url)
    allowed_origins.append(settings.frontend_url.rstrip("/"))

# Add any Railway-provided URLs
railway_public_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
if railway_public_domain:
    allowed_origins.append("https://" + railway_public_domain)

# Hardcode your known production URLs as backup
allowed_origins.extend([
    "https://gracefinance-production.up.railway.app",
    "https://gracefinance.co",
    "https://www.gracefinance.co",
])

# Deduplicate
allowed_origins = list(set(o for o in allowed_origins if o))

# CORS — allow your React frontend to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Original Routers ──
app.include_router(auth_router)         # /auth/signup, /auth/login, /auth/me
app.include_router(debts_router)        # /debts/
app.include_router(transactions_router) # /transactions/
app.include_router(bills_router)        # /bills/
app.include_router(dashboard_router)    # /dashboard/
app.include_router(billing_router)      # /billing/checkout, /billing/webhook

# ── Data Engine Routers ──
app.include_router(checkins_router)     # /checkin/questions, /checkin/submit, /checkin/metrics
app.include_router(index_router)        # /index/latest, /index/history, /index/compute

# ── Grace AI Coach ──
app.include_router(grace_router)        # /grace/chat, /grace/intro


@app.get("/")
def root():
    return {
        "app": "GraceFinance",
        "tagline": "Smarter Finance is Right Around the Corner™",
        "version": "1.1.0",
        "docs": "/docs",
        "data_engine": {
            "checkin": "/checkin/questions",
            "index": "/index/latest",
            "methodology": "/index/methodology",
        },
        "coach": {
            "chat": "/grace/chat",
            "intro": "/grace/intro",
        },
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "engine": "active", "grace": "online"}