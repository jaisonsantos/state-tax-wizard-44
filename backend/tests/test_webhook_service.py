"""Tests for WebhookService subscription handlers."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import stripe

from app.core.config import settings
from app.models.models import Store, Subscription
from app.services.webhook_service import WebhookService


class DummyStripeObject(dict):
    """Simple helper that mimics StripeObject.to_dict."""

    def to_dict(self):
        return dict(self)


@pytest.fixture(autouse=True)
def reset_stripe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(stripe, "api_key", "sk_test_dummy", raising=False)
    monkeypatch.setattr(settings, "stripe_price_id_starter", "price_starter", raising=False)
    monkeypatch.setattr(settings, "stripe_price_id_pro", "price_pro", raising=False)
    monkeypatch.setattr(settings, "stripe_price_id_plus", "price_plus", raising=False)


def test_subscription_created_hydrates_missing_periods(monkeypatch: pytest.MonkeyPatch, db_session) -> None:
    store = Store(
        id=uuid.uuid4(),
        name="Demo Store",
        platform="shopify",
        domain="demo.example",
        country="US",
        stripe_customer_id="cus_real",
    )
    db_session.add(store)
    db_session.commit()

    # Payload without period dates triggers retrieval
    event = {
        "data": {
            "object": DummyStripeObject(
        {
            "id": "sub_test",
            "customer": "cus_real",
            "status": "active",
            "items": {
                "data": [
                    {
                        "price": {"id": "price_pro"},
                    }
                ]
            },
            "cancel_at_period_end": False,
        }
            )
        }
    }

    hydrated = DummyStripeObject(
        {
            "id": "sub_test",
            "customer": "cus_real",
            "status": "active",
            "items": {
                "data": [
                    {
                        "price": {"id": "price_pro"},
                    }
                ]
            },
            "current_period_start": 1_700_000_000,
            "current_period_end": 1_700_864_000,
            "trial_end": None,
            "cancel_at_period_end": False,
        }
    )

    monkeypatch.setattr(stripe.Subscription, "retrieve", lambda _: hydrated)

    WebhookService.process_subscription_created(db_session, event)

    subscription = (
        db_session.query(Subscription)
        .filter(Subscription.stripe_subscription_id == "sub_test")
        .one()
    )
    assert subscription.plan_tier == "pro"
    start = subscription.current_period_start
    end = subscription.current_period_end
    assert start is not None and int(start.replace(tzinfo=timezone.utc).timestamp()) == 1_700_000_000
    assert end is not None and int(end.replace(tzinfo=timezone.utc).timestamp()) == 1_700_864_000
    assert subscription.stripe_customer_id == "cus_real"
    db_session.refresh(store)
    assert store.stripe_subscription_id == "sub_test"


def test_subscription_updated_upserts_when_missing(monkeypatch: pytest.MonkeyPatch, db_session) -> None:
    store = Store(
        id=uuid.uuid4(),
        name="Demo Store",
        platform="woo",
        domain="demo-woo.example",
        country="US",
        stripe_customer_id="cus_upsert",
    )
    db_session.add(store)
    db_session.commit()

    event = {
        "data": {
            "object": DummyStripeObject(
        {
            "id": "sub_missing",
            "customer": {"id": "cus_upsert"},
            "status": "trialing",
            "items": {
                "data": [
                    {
                        "price": {"id": "price_starter"},
                    }
                ]
            },
            "cancel_at_period_end": False,
        }
            )
        }
    }

    hydrated = DummyStripeObject(
        {
            "id": "sub_missing",
            "customer": "cus_upsert",
            "status": "active",
            "items": {
                "data": [
                    {
                        "price": {"id": "price_starter"},
                    }
                ]
            },
            "current_period_start": 1_700_000_000,
            "current_period_end": 1_700_432_000,
            "cancel_at_period_end": False,
        }
    )
    monkeypatch.setattr(stripe.Subscription, "retrieve", lambda _: hydrated)

    WebhookService.process_subscription_updated(db_session, event)

    subscription = (
        db_session.query(Subscription)
        .filter(Subscription.stripe_subscription_id == "sub_missing")
        .one()
    )
    assert subscription.status == "active"
    assert subscription.plan_tier == "starter"
    start = subscription.current_period_start
    assert start is not None and int(start.replace(tzinfo=timezone.utc).timestamp()) == 1_700_000_000
    db_session.refresh(store)
    assert store.stripe_subscription_id == "sub_missing"
