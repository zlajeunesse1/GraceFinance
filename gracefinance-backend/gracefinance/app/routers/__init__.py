from .auth import router as auth_router
from .debts import router as debts_router
from .transactions import router as transactions_router
from .bills import router as bills_router
from .dashboard import router as dashboard_router
from .billing import router as billing_router
from .checkin import router as checkin_router
__all__ = [
    "auth_router",
    "debts_router",
    "transactions_router",
    "bills_router",
    "dashboard_router",
    "billing_router",
    "checkin_router",
]
