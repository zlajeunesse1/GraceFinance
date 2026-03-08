"""
Billing Router — supports monthly/yearly for Pro and Premium tiers.
"""

import stripe
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, SubscriptionTier
from app.schemas import CheckoutRequest, CheckoutResponse
from app.services.auth import get_current_user
from app.config import get_settings

settings = get_settings()
stripe.api_key = settings.stripe_secret_key

router = APIRouter(prefix="/billing", tags=["Billing"])


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
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = UUID(session["metadata"]["user_id"])
        tier = session["metadata"]["tier"]

        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.subscription_tier = SubscriptionTier(tier)
            user.stripe_subscription_id = session.get("subscription")
            db.commit()

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