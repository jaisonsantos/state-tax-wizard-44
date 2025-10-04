from __future__ import annotations

import json
import pytest
import stripe

from app.core import config
from app.models.models import ProcessedWebhook
from app.services import webhook_service


@pytest.fixture(autouse=True)
def configure_webhook_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "stripe_webhook_secret", "whsec_test", raising=False)


def _build_subscription_event(store_id: str) -> dict:
    return {
        "id": "evt_smoke_sub_created",
        "type": "customer.subscription.created",
        "data": {
            "object": {
                "id": "sub_smoke",
                "customer": "cus_smoke",
                "metadata": {"store_id": store_id},
                "status": "active",
                "items": {
                    "data": [
                        {
                            "price": {"id": config.settings.stripe_price_id_pro or "price_pro"},
                        }
                    ]
                },
                "current_period_start": 1_700_000_000,
                "current_period_end": 1_700_086_400,
                "cancel_at_period_end": False,
            }
        },
    }


def test_webhook_endpoint_processes_event(client, db_session, monkeypatch: pytest.MonkeyPatch) -> None:
    login_response = client.post(
        "/api/auth/login",
        json={"email": "webhook@example.com", "password": "secret"},
    )
    login_response.raise_for_status()
    store_id = login_response.json()["stores"][0]["id"]

    event = _build_subscription_event(store_id)
    monkeypatch.setattr(stripe.Webhook, "construct_event", lambda payload, header, secret: event)

    response = client.post(
        "/api/v1/billing/webhooks/stripe",
        content=json.dumps(event),
        headers={"stripe-signature": "t=1,v1=dummy"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "processed"

    processed = (
        db_session.query(ProcessedWebhook)
        .filter(ProcessedWebhook.event_id == event["id"])
        .one()
    )
    assert processed.status == "processed"
    assert str(processed.store_id) == store_id

    # Duplicate delivery should be acknowledged without reprocessing
    response_dup = client.post(
        "/api/v1/billing/webhooks/stripe",
        content=json.dumps(event),
        headers={"stripe-signature": "t=1,v1=dummy"},
    )
    assert response_dup.status_code == 200
    assert response_dup.json()["status"] == "duplicate"


def test_webhook_endpoint_handles_invalid_signature(client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        stripe.Webhook,
        "construct_event",
        lambda payload, header, secret: (_ for _ in ()).throw(stripe.error.SignatureVerificationError("bad", "sig")),
    )

    response = client.post(
        "/api/v1/billing/webhooks/stripe",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=bad"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid signature"


def test_webhook_replay_endpoint(db_session, client, monkeypatch: pytest.MonkeyPatch) -> None:
    login_response = client.post(
        "/api/auth/login",
        json={"email": "replay@example.com", "password": "secret"},
    )
    login_response.raise_for_status()
    body = login_response.json()
    store_id = body["stores"][0]["id"]
    token = body["token"]

    event = _build_subscription_event(store_id)
    monkeypatch.setattr(stripe.Webhook, "construct_event", lambda payload, header, secret: event)

    # Force failure by raising from dispatch and reduce max attempts to 1 so record enters DLQ.
    monkeypatch.setattr(webhook_service, "MAX_WEBHOOK_ATTEMPTS", 1, raising=False)
    monkeypatch.setattr(
        webhook_service.WebhookService,
        "_dispatch_stripe_event",
        lambda db, event_type, payload: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    response = client.post(
        "/api/v1/billing/webhooks/stripe",
        content=json.dumps(event),
        headers={"stripe-signature": "t=1,v1=dummy"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "dead_letter"

    # Replay with successful dispatch
    monkeypatch.setattr(
        webhook_service.WebhookService,
        "_dispatch_stripe_event",
        lambda db, event_type, payload: store_id,
    )

    replay_response = client.post(
        f"/api/v1/billing/webhooks/stripe/replay/{event['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert replay_response.status_code == 200
    assert replay_response.json()["status"] == "processed"
