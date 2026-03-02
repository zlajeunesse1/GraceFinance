"""
GraceFinance Routers — All API routers exported here.
CLEAN VERSION (Debt / Transaction / Bill routers removed)
"""

from app.routers.auth import router as auth_router
from app.routers.dashboard import router as dashboard_router
from app.routers.billing import router as billing_router
from app.routers.grace import router as grace_router

# Data Engine routers
from app.routers.checkins import router as checkins_router
from app.routers.index import router as index_router

# Reward Loop routers
from app.routers.me import router as me_router
from app.routers.index_summary import router as index_summary_router
from app.routers.sse import router as sse_router

# Social Feed (v2)
from app.routers.feed import router as feed_router