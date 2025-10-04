from datetime import datetime, timezone
import uuid

import pytest

from app.models.models import OrderFee, Store, StoreSetting, WebhookEvent
from app.services.taxo_webhook_service import TaxoWebhookService


def _create_store(db_session, *, webhook_active: bool, endpoint: str | None, secret: str | None) -> tuple[Store, StoreSetting]:
    store = Store(
        id=uuid.uuid4(),
        name="webhook store",
        platform="shopify",
        domain="example.myshopify.com",
        country="US",
    )
    db_session.add(store)
    db_session.commit()
    db_session.refresh(store)

    settings = StoreSetting(
        store_id=store.id,
        enable_mn=True,
        enable_co=True,
        absorb_fee=False,
        label_override="Delivery Fee",
        webhook_active=webhook_active,
        webhook_endpoint=endpoint,
        hmac_secret=secret,
        webhook_events=["fee.applied", "report.ready", "hmac.rotated"],
    )
    db_session.add(settings)
    db_session.commit()
    db_session.refresh(settings)
    return store, settings


def _build_order_fee(store_id: uuid.UUID) -> OrderFee:
    return OrderFee(
        store_id=store_id,
        order_id="order-123",
        jurisdiction="MN",
        amount_cents=50,
        delivery_method="ship",
        absorbed=False,
        rule_version="v1",
        reason_codes=["MN_THRESHOLD_MET"],
        status="applied",
        applied_at=datetime.now(timezone.utc),
    )


def test_dispatch_fee_applied_success(monkeypatch: pytest.MonkeyPatch, db_session) -> None:
    store, settings = _create_store(
        db_session,
        webhook_active=True,
        endpoint="https://merchant.example/webhooks",
        secret="test-secret",
    )

    order_fee = _build_order_fee(store.id)
    db_session.add(order_fee)
    db_session.flush()

    queued = TaxoWebhookService.queue_fee_applied(
        db_session,
        store_id=str(store.id),
        request_id="req-fee",
        order_fee=order_fee,
        absorbed=False,
        delivery_method="ship",
        source_of_remittance="merchant",
    )
    assert queued is not None
    db_session.commit()

    captured: dict[str, object] = {}

    class _StubResponse:
        def __init__(self, status_code: int = 200, text: str = "") -> None:
            self.status_code = status_code
            self.text = text

    class _StubClient:
        def __init__(self, *args, **kwargs):
            captured["timeout"] = kwargs.get("timeout")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url: str, content: bytes | None = None, headers: dict | None = None):
            captured["url"] = url
            captured["content"] = content
            captured["headers"] = headers or {}
            return _StubResponse()

    monkeypatch.setattr("app.services.taxo_webhook_service.httpx.Client", _StubClient)

    TaxoWebhookService.dispatch_events(
        db_session,
        str(store.id),
        [queued],
        settings_model=settings,
    )
    db_session.commit()

    event = db_session.query(WebhookEvent).filter(WebhookEvent.event_id == queued.event_id).one()
    assert event.status == "delivered"
    assert event.attempts == 1
    assert captured["url"] == settings.webhook_endpoint
    headers = captured["headers"]
    assert headers["X-Taxo-Event"] == "fee.applied"
    assert headers["X-Taxo-Event-Id"] == queued.event_id


def test_dispatch_skipped_when_disabled(db_session) -> None:
    store, settings = _create_store(
        db_session,
        webhook_active=False,
        endpoint="https://merchant.example/webhooks",
        secret="test-secret",
    )

    queued = TaxoWebhookService.queue_fee_skipped(
        db_session,
        store_id=str(store.id),
        order_id="order-123",
        jurisdiction="MN",
        reason_codes=["MN_THRESHOLD_NOT_MET"],
        request_id="req-skip",
    )
    assert queued is not None
    db_session.commit()

    TaxoWebhookService.dispatch_events(
        db_session,
        str(store.id),
        [queued],
        settings_model=settings,
    )
    db_session.commit()

    event = db_session.query(WebhookEvent).filter(WebhookEvent.event_id == queued.event_id).one()
    assert event.status == "skipped"
    assert event.dead_letter is False
    assert event.attempts == 0


def test_dispatch_missing_secret_marks_failed(monkeypatch: pytest.MonkeyPatch, db_session) -> None:
    store, settings = _create_store(
        db_session,
        webhook_active=True,
        endpoint="https://merchant.example/webhooks",
        secret=None,
    )

    order_fee = _build_order_fee(store.id)
    db_session.add(order_fee)
    db_session.flush()

    queued = TaxoWebhookService.queue_fee_applied(
        db_session,
        store_id=str(store.id),
        request_id="req-missing-secret",
        order_fee=order_fee,
        absorbed=False,
        delivery_method="ship",
        source_of_remittance="merchant",
    )
    assert queued is not None
    db_session.commit()

    failures: list[tuple[str, str]] = []
    deliveries: list[tuple[str, str, float]] = []
    logs: list[dict[str, object]] = []

    monkeypatch.setattr(
        "app.services.taxo_webhook_service.record_outgoing_webhook_failure",
        lambda event, reason: failures.append((event, reason)),
    )
    monkeypatch.setattr(
        "app.services.taxo_webhook_service.record_outgoing_webhook_delivery",
        lambda event, status, duration: deliveries.append((event, status, duration)),
    )
    monkeypatch.setattr(
        "app.services.taxo_webhook_service.log_webhook_delivery",
        lambda payload: logs.append(payload),
    )

    TaxoWebhookService.dispatch_events(
        db_session,
        str(store.id),
        [queued],
        settings_model=settings,
    )
    db_session.commit()

    event = db_session.query(WebhookEvent).filter(WebhookEvent.event_id == queued.event_id).one()
    assert event.status == "failed"
    assert event.last_error == "missing_hmac_secret"
    assert failures == [(event.event_type, "missing_hmac_secret")]
    assert deliveries == [(event.event_type, "failed", 0.0)]
    assert logs and logs[0]["failure_reason"] == "missing_hmac_secret"


def test_dispatch_http_error_records_failure(monkeypatch: pytest.MonkeyPatch, db_session) -> None:
    store, settings = _create_store(
        db_session,
        webhook_active=True,
        endpoint="https://merchant.example/webhooks",
        secret="test-secret",
    )

    order_fee = _build_order_fee(store.id)
    db_session.add(order_fee)
    db_session.flush()

    queued = TaxoWebhookService.queue_fee_applied(
        db_session,
        store_id=str(store.id),
        request_id="req-http-error",
        order_fee=order_fee,
        absorbed=False,
        delivery_method="ship",
        source_of_remittance="merchant",
    )
    assert queued is not None
    db_session.commit()

    failures: list[tuple[str, str]] = []
    deliveries: list[tuple[str, str, float]] = []
    dead_letters: list[str] = []
    logs: list[dict[str, object]] = []

    class _StubResponse:
        def __init__(self, status_code: int = 500, text: str = "boom") -> None:
            self.status_code = status_code
            self.text = text

    class _ErrorClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url: str, content: bytes | None = None, headers: dict | None = None):
            return _StubResponse()

    monkeypatch.setattr("app.services.taxo_webhook_service.httpx.Client", _ErrorClient)
    monkeypatch.setattr(
        "app.services.taxo_webhook_service.record_outgoing_webhook_failure",
        lambda event, reason: failures.append((event, reason)),
    )
    monkeypatch.setattr(
        "app.services.taxo_webhook_service.record_outgoing_webhook_delivery",
        lambda event, status, duration: deliveries.append((event, status, duration)),
    )
    monkeypatch.setattr(
        "app.services.taxo_webhook_service.record_outgoing_webhook_dead_letter",
        lambda event: dead_letters.append(event),
    )
    monkeypatch.setattr(
        "app.services.taxo_webhook_service.log_webhook_delivery",
        lambda payload: logs.append(payload),
    )

    TaxoWebhookService.dispatch_events(
        db_session,
        str(store.id),
        [queued],
        settings_model=settings,
    )
    db_session.commit()

    event = db_session.query(WebhookEvent).filter(WebhookEvent.event_id == queued.event_id).one()
    assert event.status == "pending"
    assert event.dead_letter is False
    assert event.last_error == "boom"
    assert failures == [(event.event_type, "http_500")]
    assert deliveries and deliveries[0][1] == "pending"
    assert not dead_letters
    assert logs and logs[0]["failure_reason"] == "http_500"
