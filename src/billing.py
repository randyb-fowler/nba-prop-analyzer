"""Stripe billing: Checkout (subscribe), webhook (grant/revoke Pro), Portal.

Runs in Stripe test mode until live keys are set. The subscription-state logic
is factored into the pure `apply_subscription_event` so it can be unit-tested
without Stripe or a database. If Stripe isn't configured, the routes report 503
and the rest of the app keeps working.
"""

import os

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from src.db import User, get_db
from src.auth import get_current_user

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:8000").rstrip("/")
STRIPE_CONFIGURED = bool(STRIPE_SECRET_KEY and STRIPE_PRICE_ID)

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

router = APIRouter(prefix="/api/billing", tags=["billing"])

_ACTIVE_STATUSES = {"active", "trialing"}


def apply_subscription_event(event: dict) -> dict | None:
    """Translate a Stripe event into a normalized state change, or None to ignore.

    Returns {"user_id": int|None, "customer_id": str|None, "is_pro": bool}.
    """
    event_type = event.get("type")
    obj = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        ref = obj.get("client_reference_id")
        return {
            "user_id": int(ref) if ref else None,
            "customer_id": obj.get("customer"),
            "is_pro": True,
        }
    if event_type == "customer.subscription.updated":
        return {
            "user_id": None,
            "customer_id": obj.get("customer"),
            "is_pro": obj.get("status") in _ACTIVE_STATUSES,
        }
    if event_type == "customer.subscription.deleted":
        return {"user_id": None, "customer_id": obj.get("customer"), "is_pro": False}
    return None


def _require_login(user: User | None) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in first.")
    return user


@router.post("/checkout")
def checkout(user: User | None = Depends(get_current_user)):
    """Create a Stripe Checkout session for the Pro subscription."""
    if not STRIPE_CONFIGURED:
        raise HTTPException(status_code=503, detail="Billing is not configured yet.")
    user = _require_login(user)
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            success_url=f"{APP_BASE_URL}/?upgraded=1",
            cancel_url=f"{APP_BASE_URL}/",
            client_reference_id=str(user.id),
            customer=user.stripe_customer_id or None,
            customer_email=None if user.stripe_customer_id else user.email,
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Stripe error: {e}")


@router.post("/portal")
def portal(user: User | None = Depends(get_current_user)):
    """Open the Stripe Billing Portal to manage/cancel the subscription."""
    if not STRIPE_CONFIGURED:
        raise HTTPException(status_code=503, detail="Billing is not configured yet.")
    user = _require_login(user)
    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No subscription to manage yet.")
    try:
        session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=f"{APP_BASE_URL}/",
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Stripe error: {e}")


@router.post("/webhook")
async def webhook(request: Request, db=Depends(get_db)):
    """Receive Stripe events and grant/revoke Pro accordingly."""
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook secret not configured.")
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid webhook: {e}")

    instr = apply_subscription_event(event)
    if not instr:
        return {"ignored": True}

    user = None
    if instr.get("user_id"):
        user = db.get(User, instr["user_id"])
    if user is None and instr.get("customer_id"):
        user = db.scalar(select(User).where(User.stripe_customer_id == instr["customer_id"]))

    if user:
        user.is_pro = instr["is_pro"]
        if instr.get("customer_id"):
            user.stripe_customer_id = instr["customer_id"]
        db.commit()

    return {"ok": True}
