from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict

import stripe
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Store, Subscription
from app.services import stripe_service
from app.services.entitlement_service import EntitlementService
from app.services.webhook_service import WebhookService


def _login(client: TestClient) -> tuple[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"email": "billing-tester@example.com", "password": "secret"},
    )
    response.raise_for_status()
    body = response.json()
    return body["token"], body["stores"][0]["id"]


def test_entitlements_returns_503_when_stripe_unconfigured(
    client: TestClient, monkeypatch
) -> None:
    token, store_id = _login(client)
    monkeypatch.setattr(settings, "stripe_secret_key", None, raising=False)
    monkeypatch.setattr(stripe, "api_key", None, raising=False)

    response = client.get(
        f"/api/v1/billing/entitlements?store_id={store_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload["detail"]["code"] == "billing_unconfigured"


def _configure_billing(monkeypatch) -> None:
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_dummy", raising=False)
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test", raising=False)
    monkeypatch.setattr(settings, "stripe_price_id_starter", "price_starter", raising=False)
    monkeypatch.setattr(settings, "stripe_price_id_pro", "price_pro", raising=False)
    monkeypatch.setattr(settings, "stripe_price_id_plus", "price_plus", raising=False)
    monkeypatch.setattr(settings, "stripe_price_id_e10k", "price_e10k", raising=False)
    monkeypatch.setattr(settings, "stripe_price_id_e25k", "price_e25k", raising=False)
    monkeypatch.setattr(settings, "stripe_price_id_e50k", "price_e50k", raising=False)
    monkeypatch.setattr(stripe, "api_key", "sk_test_dummy", raising=False)


def test_entitlements_and_usage_success(client: TestClient, monkeypatch, db_session: Session) -> None:
    token, store_id = _login(client)
    _configure_billing(monkeypatch)

    store = db_session.query(Store).filter(Store.id == store_id).first()
    assert store is not None
    subscription = (
        db_session.query(Subscription)
        .filter(Subscription.store_id == store_id)
        .first()
    )
    if subscription is None:
        subscription = Subscription(
            store_id=store_id,
            provider="stripe",
            plan="starter",
            plan_tier="starter",
            status="active",
            current_period_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            current_period_end=datetime(2025, 1, 31, tzinfo=timezone.utc),
        )
        db_session.add(subscription)
    else:
        subscription.status = "active"
        subscription.plan_tier = "starter"
        subscription.current_period_start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        subscription.current_period_end = datetime(2025, 1, 31, tzinfo=timezone.utc)
    db_session.commit()

    entitlements_response = client.get(
        f"/api/v1/billing/entitlements?store_id={store_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert entitlements_response.status_code == 200
    entitlements_payload = entitlements_response.json()
    assert entitlements_payload["plan"] == "starter"
    assert "features" in entitlements_payload
    assert entitlements_payload["limits"]["transactions_per_month"] == 100
    assert entitlements_payload["warn_threshold_pct"] == 80
    assert "stripe_prices_configured" in entitlements_payload

    usage_response = client.get(
        f"/api/v1/billing/usage?store_id={store_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert usage_response.status_code == 200
    usage_payload = usage_response.json()
    assert usage_payload["plan"] == "starter"
    assert "transactions_used" in usage_payload
    assert "period_start" in usage_payload
    assert "warn_threshold_pct" in usage_payload
    assert "warnings" in usage_payload


def test_checkout_session_uses_service_and_returns_payload(
    client: TestClient, monkeypatch
) -> None:
    token, store_id = _login(client)
    _configure_billing(monkeypatch)

    def fake_checkout_session(**_: Any) -> Dict[str, Any]:
        return {"session_id": "cs_test", "url": "https://checkout.example"}

    monkeypatch.setattr(
        stripe_service.StripeService,
        "create_checkout_session",
        staticmethod(fake_checkout_session),
    )

    response = client.post(
        f"/api/v1/billing/create-checkout-session?store_id={store_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "plan_tier": "pro",
            "success_url": "https://app.example/success",
            "cancel_url": "https://app.example/cancel",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "cs_test"
    assert payload["url"] == "https://checkout.example"


def test_checkout_session_rejects_unknown_plan(
    client: TestClient, monkeypatch
) -> None:
    token, store_id = _login(client)
    _configure_billing(monkeypatch)

    mutated_limits = EntitlementService.PLAN_LIMITS.copy()
    mutated_limits.pop("enterprise_e10k", None)
    monkeypatch.setattr(EntitlementService, "PLAN_LIMITS", mutated_limits, raising=False)
    monkeypatch.setattr(
        EntitlementService,
        "ENTERPRISE_PLAN_KEYS",
        {key for key in EntitlementService.ENTERPRISE_PLAN_KEYS if key != "enterprise_e10k"},
        raising=False,
    )

    response = client.post(
        f"/api/v1/billing/create-checkout-session?store_id={store_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "plan_tier": "enterprise_e10k",
            "success_url": "https://app.example/success",
            "cancel_url": "https://app.example/cancel",
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["detail"]["code"] == "unsupported_plan_tier"


def test_portal_session_returns_url(client: TestClient, monkeypatch) -> None:
    token, store_id = _login(client)
    _configure_billing(monkeypatch)

    def fake_portal_session(**_: Any) -> Dict[str, Any]:
        return {"portal_url": "https://portal.example", "portal_session_id": "ps_test"}

    monkeypatch.setattr(
        stripe_service.StripeService,
        "create_portal_session",
        staticmethod(fake_portal_session),
    )

    response = client.post(
        f"/api/v1/billing/create-portal-session?store_id={store_id}&return_url=https://app.example/return",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["portal_url"] == "https://portal.example"
    assert payload["portal_session_id"] == "ps_test"


def test_portal_session_returns_400_when_customer_missing(
    client: TestClient, monkeypatch, db_session: Session
) -> None:
    token, store_id = _login(client)
    _configure_billing(monkeypatch)

    def fake_portal_session(**_: Any) -> Dict[str, Any]:
        raise stripe_service.StripeCustomerMissingError("missing customer")

    monkeypatch.setattr(
        stripe_service.StripeService,
        "create_portal_session",
        staticmethod(fake_portal_session),
    )

    response = client.post(
        f"/api/v1/billing/create-portal-session?store_id={store_id}&return_url=https://app.example/return",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "stripe_customer_missing"


def test_webhook_invalid_signature_returns_400(client: TestClient, monkeypatch) -> None:
    _configure_billing(monkeypatch)
    def raise_signature_error(*_args: Any, **_kwargs: Any):
        raise stripe.error.SignatureVerificationError("bad", "sig")

    monkeypatch.setattr(stripe.Webhook, "construct_event", staticmethod(raise_signature_error))

    response = client.post(
        "/api/v1/billing/webhooks/stripe",
        content=json.dumps({"id": "evt_test"}),
        headers={"stripe-signature": "invalid"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid signature"


def test_webhook_processes_known_event(client: TestClient, monkeypatch) -> None:
    _configure_billing(monkeypatch)

    event = {
        "type": "customer.subscription.created",
        "data": {"object": {"id": "sub_test", "customer": "cus_test"}},
    }

    processed = {}

    def fake_construct_event(payload, signature, secret):
        assert signature == "sig_test"
        assert secret == "whsec_test"
        return event

    def fake_process_subscription_created(db: Session, evt: Dict[str, Any]):
        processed["called"] = True
        processed["event_id"] = evt["data"]["object"]["id"]

    monkeypatch.setattr(stripe.Webhook, "construct_event", staticmethod(fake_construct_event))
    monkeypatch.setattr(
        WebhookService,
        "process_subscription_created",
        staticmethod(fake_process_subscription_created),
    )

    response = client.post(
        "/api/v1/billing/webhooks/stripe",
        content=json.dumps({"id": "evt_test"}),
        headers={"stripe-signature": "sig_test"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert processed["called"] is True
    assert processed["event_id"] == "sub_test"
