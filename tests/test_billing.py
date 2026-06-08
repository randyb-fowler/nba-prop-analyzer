"""Tests for the pure Stripe-event → state-change logic (no Stripe, no DB)."""

from src.billing import apply_subscription_event


def test_checkout_completed_grants_pro():
    event = {
        "type": "checkout.session.completed",
        "data": {"object": {"client_reference_id": "5", "customer": "cus_123"}},
    }
    out = apply_subscription_event(event)
    assert out == {"user_id": 5, "customer_id": "cus_123", "is_pro": True}


def test_subscription_active_is_pro():
    event = {
        "type": "customer.subscription.updated",
        "data": {"object": {"customer": "cus_9", "status": "active"}},
    }
    assert apply_subscription_event(event)["is_pro"] is True


def test_subscription_canceled_status_revokes_pro():
    event = {
        "type": "customer.subscription.updated",
        "data": {"object": {"customer": "cus_9", "status": "canceled"}},
    }
    out = apply_subscription_event(event)
    assert out["is_pro"] is False and out["customer_id"] == "cus_9"


def test_subscription_deleted_revokes_pro():
    event = {
        "type": "customer.subscription.deleted",
        "data": {"object": {"customer": "cus_9"}},
    }
    assert apply_subscription_event(event)["is_pro"] is False


def test_unknown_event_ignored():
    assert apply_subscription_event({"type": "invoice.paid", "data": {"object": {}}}) is None


def test_checkout_without_reference_has_null_user():
    event = {
        "type": "checkout.session.completed",
        "data": {"object": {"customer": "cus_x"}},
    }
    out = apply_subscription_event(event)
    assert out["user_id"] is None and out["customer_id"] == "cus_x"
