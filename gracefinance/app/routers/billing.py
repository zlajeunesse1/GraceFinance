"""
Billing Router — v1.1
=====================
CHANGES:
  FIX #2 (CRITICAL): Stripe webhook now has idempotency protection.
    Tracks processed event IDs in memory to prevent replay attacks.
    A replayed webhook can't upgrade/downgrade a user twice.

Supports monthly/yearly for Pro and Premium tiers.
"""

import stripe
import logging
from uuid import UUID
from collections import OrderedDict
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, SubscriptionTier
from app.schemas import CheckoutRequest, CheckoutResponse
from app.services.auth import get_current_user
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
stripe.api_key = settings.stripe_secret_key

router = APIRouter(prefix="/billing", tags=["Billing"])


# ── Webhook idempotency: track processed event IDs ──────────────────────────
# Uses an OrderedDict as a bounded LRU cache. Thread-safe via lock.
# In production at scale, replace with Redis SET with TTL.
_processed_events_lock = Lock()
_processed_events: OrderedDict = OrderedDict()
MAX_PROCESSED_EVENTS = 10000  # Keep last 10k event IDs in memory


def _is_event_processed(event_id: str) -> bool:
    """Check if we've already processed this Stripe event."""
    with _processed_events_lock:
        return event_id in _processed_events


def _mark_event_processed(event_id: str):
    """Mark a Stripe event as processed. Evicts oldest if cache is full."""
    with _processed_events_lock:
        _processed_events[event_id] = True
        # Evict oldest entries if we exceed the cache size
        while len(_processed_events) > MAX_PROCESSED_EVENTS:
            _processed_events.popitem(last=False)


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout_session(
    data: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session for subscription upgrade."""
    price_map = {
        ("pro", "monthly"):      settings.stripe_price_pro_monthly,
        ("pro", "yearly"):       settings.stripe_price_pro_yearly,
        ("premium", "monthly"):  settings.stripe_price_premium_monthly,
        ("premium", "yearly"):   settings.stripe_price_premium_yearly,
    }

    interval = getattr(data, "interval", "monthly") or "monthly"
    price_id = price_map.get((data.tier, interval))
    if not price_id:
        raise HTTPException(status_code=400, detail="Invalid tier or interval")

    if not user.stripe_customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            name=f"{user.first_name} {user.last_name}",
            metadata={"gracefinance_user_id": str(user.id)},
        )
        user.stripe_customer_id = customer.id
        db.commit()

    session = stripe.checkout.Session.create(
        customer=user.stripe_customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=f"{settings.frontend_url}/dashboard?upgraded=true",
        cancel_url=f"{settings.frontend_url}/dashboard?upgraded=false",
        metadata={"user_id": str(user.id), "tier": data.tier, "interval": interval},
    )

    return CheckoutResponse(checkout_url=session.url)


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Stripe webhook events.

    FIX: Idempotency check — if we've already processed this event ID,
    return 200 immediately without re-processing. Prevents replay attacks
    and duplicate tier changes from webhook retries.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook")

    # ── Idempotency: skip already-processed events ───────────────────────
    event_id = event.get("id")
    if event_id and _is_event_processed(event_id):
        logger.info(f"Stripe webhook: skipping duplicate event {event_id}")
        return {"status": "already_processed"}

    # ── Process the event ────────────────────────────────────────────────
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        user_id_str = metadata.get("user_id")
        tier = metadata.get("tier")

        if user_id_str and tier:
            try:
                user_id = UUID(user_id_str)
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user.subscription_tier = SubscriptionTier(tier)
                    user.stripe_subscription_id = session.get("subscription")
                    db.commit()
                    logger.info(f"User {user_id} upgraded to {tier}")
            except (ValueError, Exception) as e:
                logger.error(f"Webhook checkout.session.completed failed: {e}")

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        user = (
            db.query(User)
            .filter(User.stripe_subscription_id == subscription["id"])
            .first()
        )
        if user:
            user.subscription_tier = SubscriptionTier.FREE
            user.stripe_subscription_id = None
            db.commit()
            logger.info(f"User {user.id} downgraded to FREE (subscription cancelled)")

    # ── Mark as processed ────────────────────────────────────────────────
    if event_id:
        _mark_event_processed(event_id)

    return {"status": "ok"}


@router.get("/portal-url")
def get_billing_portal(
    user: User = Depends(get_current_user),
):
    """Generate a Stripe Customer Portal URL for subscription management."""
    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account found")

    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{settings.frontend_url}/dashboard",
    )

    return {"url": session.url}