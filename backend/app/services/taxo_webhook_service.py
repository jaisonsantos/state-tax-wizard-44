"""Outgoing webhook service for Taxo events."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Sequence

import httpx
from sqlalchemy.orm import Session

from ..models.models import (
    OrderFee,
    StoreSetting,
    WebhookDeliveryAttempt,
    WebhookEvent,
)
from ..observability import (
    log_webhook_delivery,
    record_outgoing_webhook_dead_letter,
    record_outgoing_webhook_delivery,
    record_outgoing_webhook_failure,
)
from ..security.hmac import compute_signature


BACKOFF_SCHEDULE_SECONDS = (60, 300, 3600, 21600, 86400)


@dataclass
class QueuedEvent:
    """Represents an event queued for delivery."""

    event_id: str
    event_type: str


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _canonical_payload(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class TaxoWebhookService:
    """Service responsible for queuing and delivering Taxo webhook events."""

    @staticmethod
    def queue_fee_applied(
        db: Session,
        *,
        store_id: str,
        request_id: str,
        order_fee: OrderFee,
        absorbed: bool,
        delivery_method: str,
        source_of_remittance: str | None,
    ) -> QueuedEvent | None:
        event_id = f"fee.applied:{order_fee.id}"
        payload = {
            "id": event_id,
            "type": "fee.applied",
            "version": 1,
            "occurred_at": (order_fee.applied_at or _now()).astimezone(timezone.utc).isoformat(),
            "store_id": str(store_id),
            "data": {
                "order_id": order_fee.order_id,
                "jurisdiction": order_fee.jurisdiction,
                "amount_cents": order_fee.amount_cents,
                "delivery_method": delivery_method,
                "reason_codes": list(order_fee.reason_codes or []),
                "absorbed": absorbed,
                "source_of_remittance": source_of_remittance,
                "fee_id": str(order_fee.id),
            },
            "meta": {
                "request_id": request_id,
            },
        }

        return TaxoWebhookService._queue_event(
            db,
            store_id=store_id,
            event_id=event_id,
            event_type="fee.applied",
            payload=payload,
        )

    @staticmethod
    def queue_fee_skipped(
        db: Session,
        *,
        store_id: str,
        order_id: str,
        jurisdiction: str,
        reason_codes: Iterable[str],
        request_id: str,
    ) -> QueuedEvent | None:
        stable_key = _stable_hash(f"{store_id}:{order_id}:{jurisdiction}")
        event_id = f"fee.skipped:{stable_key[:32]}"
        payload = {
            "id": event_id,
            "type": "fee.skipped",
            "version": 1,
            "occurred_at": _now().isoformat(),
            "store_id": str(store_id),
            "data": {
                "order_id": order_id,
                "jurisdiction": jurisdiction,
                "reason_codes": list(reason_codes),
            },
            "meta": {
                "request_id": request_id,
            },
        }

        return TaxoWebhookService._queue_event(
            db,
            store_id=store_id,
            event_id=event_id,
            event_type="fee.skipped",
            payload=payload,
        )

    @staticmethod
    def queue_report_ready(
        db: Session,
        *,
        store_id: str,
        report: str,
        fmt: str,
        from_date: datetime,
        to_date: datetime,
        row_count: int,
        download_path: str,
        request_id: str,
    ) -> QueuedEvent | None:
        stable_key = _stable_hash(
            f"{store_id}:{report}:{fmt}:{from_date.isoformat()}:{to_date.isoformat()}"
        )
        event_id = f"report.ready:{stable_key[:40]}"
        payload = {
            "id": event_id,
            "type": "report.ready",
            "version": 1,
            "occurred_at": _now().isoformat(),
            "store_id": str(store_id),
            "data": {
                "report": report,
                "format": fmt,
                "from_date": from_date.astimezone(timezone.utc).isoformat(),
                "to_date": to_date.astimezone(timezone.utc).isoformat(),
                "row_count": row_count,
                "download_path": download_path,
            },
            "meta": {
                "request_id": request_id,
            },
        }

        return TaxoWebhookService._queue_event(
            db,
            store_id=store_id,
            event_id=event_id,
            event_type="report.ready",
            payload=payload,
        )

    @staticmethod
    def queue_hmac_rotated(
        db: Session,
        *,
        store_id: str,
        rotated_at: datetime,
        previous_rotated_at: datetime | None,
        actor: str,
    ) -> QueuedEvent | None:
        event_id = f"hmac.rotated:{store_id}:{rotated_at.isoformat()}"
        payload = {
            "id": event_id,
            "type": "hmac.rotated",
            "version": 1,
            "occurred_at": rotated_at.astimezone(timezone.utc).isoformat(),
            "store_id": str(store_id),
            "data": {
                "rotated_by": actor,
                "rotated_at": rotated_at.astimezone(timezone.utc).isoformat(),
                "previous_rotated_at": previous_rotated_at.astimezone(timezone.utc).isoformat()
                if previous_rotated_at
                else None,
            },
        }

        return TaxoWebhookService._queue_event(
            db,
            store_id=store_id,
            event_id=event_id,
            event_type="hmac.rotated",
            payload=payload,
        )

    @staticmethod
    def _queue_event(
        db: Session,
        *,
        store_id: str,
        event_id: str,
        event_type: str,
        payload: dict,
    ) -> QueuedEvent | None:
        existing = (
            db.query(WebhookEvent)
            .filter(WebhookEvent.event_id == event_id)
            .first()
        )

        if existing:
            existing.payload = payload
            existing.status = "pending"
            existing.dead_letter = False
            existing.next_retry_at = None
            existing.last_error = None
            db.flush()
            return QueuedEvent(event_id=existing.event_id, event_type=existing.event_type)

        event = WebhookEvent(
            store_id=uuid.UUID(str(store_id)),
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            status="pending",
        )
        db.add(event)
        db.flush()
        return QueuedEvent(event_id=event.event_id, event_type=event.event_type)

    @staticmethod
    def dispatch_events(
        db: Session,
        store_id: str,
        events: Sequence[QueuedEvent],
        *,
        settings_model: StoreSetting | None = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        if not events:
            return

        if settings_model is None:
            settings_model = (
                db.query(StoreSetting)
                .filter(StoreSetting.store_id == store_id)
                .first()
            )

        if not TaxoWebhookService._is_webhook_enabled(settings_model):
            for queued in events:
                stored = (
                    db.query(WebhookEvent)
                    .filter(WebhookEvent.event_id == queued.event_id)
                    .first()
                )
                if stored:
                    stored.status = "skipped"
                    stored.last_error = "webhook disabled"
                    stored.dead_letter = False
                    stored.next_retry_at = None
            db.flush()
            return

        secret = (settings_model.hmac_secret or "").strip()
        endpoint = (settings_model.webhook_endpoint or "").strip()

        if not secret:
            for queued in events:
                stored = (
                    db.query(WebhookEvent)
                    .filter(WebhookEvent.event_id == queued.event_id)
                    .first()
                )
                if stored:
                    TaxoWebhookService._record_configuration_failure(
                        stored,
                        reason="missing_hmac_secret",
                        message="missing_hmac_secret",
                    )
            db.flush()
            return

        if not endpoint:
            for queued in events:
                stored = (
                    db.query(WebhookEvent)
                    .filter(WebhookEvent.event_id == queued.event_id)
                    .first()
                )
                if stored:
                    TaxoWebhookService._record_configuration_failure(
                        stored,
                        reason="missing_endpoint",
                        message="missing_endpoint",
                    )
            db.flush()
            return

        with httpx.Client(timeout=timeout_seconds) as client:
            for queued in events:
                stored = (
                    db.query(WebhookEvent)
                    .filter(WebhookEvent.event_id == queued.event_id)
                    .first()
                )
                if not stored:
                    continue
                TaxoWebhookService._deliver_event(
                    db,
                    client=client,
                    event=stored,
                    endpoint=endpoint,
                    secret=secret,
                )
        db.flush()

    @staticmethod
    def _deliver_event(
        db: Session,
        *,
        client: httpx.Client,
        event: WebhookEvent,
        endpoint: str,
        secret: str,
    ) -> None:
        now = _now()
        attempt_number = event.attempts + 1
        payload_bytes = _canonical_payload(event.payload)
        timestamp = now.isoformat()
        nonce = uuid.uuid4().hex
        signature = compute_signature(secret, timestamp, nonce, payload_bytes)

        headers = {
            "Content-Type": "application/json",
            "X-Taxo-Timestamp": timestamp,
            "X-Taxo-Nonce": nonce,
            "X-Taxo-Signature": signature,
            "X-Taxo-Event": event.event_type,
            "X-Taxo-Event-Id": event.event_id,
        }

        start = now
        status_code: int | None = None
        error_message: str | None = None

        failure_reason: str | None = None
        try:
            response = client.post(endpoint, content=payload_bytes, headers=headers)
            status_code = response.status_code
            if 200 <= response.status_code < 300:
                event.status = "delivered"
                event.dead_letter = False
                event.next_retry_at = None
                event.last_error = None
                event.delivered_at = now
                event.attempts = attempt_number
            else:
                error_message = response.text[:512]
                failure_reason = f"http_{status_code}" if status_code else "http_error"
                dead_lettered = TaxoWebhookService._mark_failure(event, error_message, now)
                if dead_lettered:
                    record_outgoing_webhook_dead_letter(event.event_type)
        except httpx.HTTPError as exc:
            error_message = str(exc)[:512]
            failure_reason = "network_error"
            dead_lettered = TaxoWebhookService._mark_failure(event, error_message, now)
            if dead_lettered:
                record_outgoing_webhook_dead_letter(event.event_type)
        finally:
            elapsed_ms = int((_now() - start).total_seconds() * 1000)
            attempt_log = WebhookDeliveryAttempt(
                event=event,
                attempt=attempt_number,
                response_status=status_code,
                error_message=error_message,
                duration_ms=elapsed_ms,
            )
            db.add(attempt_log)
            record_outgoing_webhook_delivery(
                event.event_type,
                event.status,
                elapsed_ms / 1000.0,
            )
            if failure_reason:
                record_outgoing_webhook_failure(event.event_type, failure_reason)
            log_payload = {
                "event": event.event_type,
                "event_id": event.event_id,
                "status": event.status,
                "attempt": attempt_number,
                "status_code": status_code,
                "dead_letter": event.dead_letter,
                "error": error_message,
            }
            if failure_reason:
                log_payload["failure_reason"] = failure_reason
            log_webhook_delivery(log_payload)

    @staticmethod
    def _mark_failure(
        event: WebhookEvent, error_message: str | None, now: datetime
    ) -> bool:
        event.status = "pending"
        event.attempts += 1
        event.last_error = error_message
        schedule_index = min(event.attempts - 1, len(BACKOFF_SCHEDULE_SECONDS) - 1)
        next_interval = BACKOFF_SCHEDULE_SECONDS[schedule_index]
        event.next_retry_at = now + timedelta(seconds=next_interval)
        if event.attempts >= len(BACKOFF_SCHEDULE_SECONDS):
            event.status = "dead_letter"
            event.dead_letter = True
            event.next_retry_at = None
            return True
        return False

    @staticmethod
    def _record_configuration_failure(
        event: WebhookEvent, *, reason: str, message: str
    ) -> None:
        event.status = "failed"
        event.last_error = message
        event.dead_letter = False
        event.next_retry_at = None
        event.delivered_at = None
        record_outgoing_webhook_failure(event.event_type, reason)
        record_outgoing_webhook_delivery(event.event_type, "failed", 0.0)
        log_webhook_delivery(
            {
                "event": event.event_type,
                "event_id": event.event_id,
                "status": event.status,
                "attempt": event.attempts,
                "dead_letter": event.dead_letter,
                "error": message,
                "failure_reason": reason,
            }
        )

    @staticmethod
    def _is_webhook_enabled(settings_model: StoreSetting | None) -> bool:
        if not settings_model:
            return False
        if not settings_model.webhook_active:
            return False
        endpoint = (settings_model.webhook_endpoint or "").strip()
        if not endpoint:
            return False
        return True
