"""Webhook service for processing Stripe events."""
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Any, Dict, Optional

import stripe
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models.models import AuditLog, ProcessedWebhook, Store, Subscription
from ..observability import (
    log_billing_event,
    record_webhook_processed,
    record_webhook_received,
)

logger = logging.getLogger(__name__)


MAX_WEBHOOK_ATTEMPTS = 3
BACKOFF_SCHEDULE_SECONDS = (30, 120, 600)


@dataclass
class WebhookProcessingResult:
    outcome: str
    message: str
    status_code: int = 200
    store_id: Optional[str] = None
    generated_event_id: bool = False


def _backoff_for_attempt(attempt: int) -> int:
    if attempt <= 0:
        return BACKOFF_SCHEDULE_SECONDS[0]
    index = min(attempt - 1, len(BACKOFF_SCHEDULE_SECONDS) - 1)
    return BACKOFF_SCHEDULE_SECONDS[index]


class UnsupportedWebhookEventError(Exception):
    """Raised when a webhook event is not handled by the service."""

    def __init__(self, event_type: str) -> None:
        super().__init__(f"Unhandled webhook event '{event_type}'")
        self.event_type = event_type


def _to_dict(payload: Any) -> Dict[str, Any]:
    """Return a plain dict regardless of Stripe payload shape."""

    if hasattr(payload, "to_dict"):
        return payload.to_dict()
    if isinstance(payload, dict):
        return payload
    return dict(payload)


def _extract_customer_id(payload: Dict[str, Any]) -> str | None:
    """Extract the Stripe customer id from webhook payload."""

    customer = payload.get("customer")
    if not customer:
        return None
    if isinstance(customer, dict):
        return customer.get("id")
    return customer


def _coerce_timestamp(value: Any) -> datetime | None:
    """Convert Stripe timestamp (int/datetime) to aware datetime."""

    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    except (ValueError, TypeError):  # defensive
        return None


def _resolve_plan_tier(payload: Dict[str, Any], fallback: str = "starter") -> str:
    """Derive the plan tier from metadata, price, or plan descriptors."""

    metadata_plan = payload.get("metadata", {}).get("plan_tier")
    if metadata_plan:
        return metadata_plan

    price_id: str | None = None
    items = payload.get("items")
    if isinstance(items, dict):
        data = items.get("data") or []
        if data:
            first = data[0]
            if isinstance(first, dict):
                price = first.get("price")
                if isinstance(price, dict):
                    price_id = price.get("id")
                elif isinstance(price, str):
                    price_id = price

    mapping = {
        settings.stripe_price_id_starter: "starter",
        settings.stripe_price_id_pro: "pro",
        settings.stripe_price_id_plus: "plus",
    }
    if price_id and price_id in mapping:
        return mapping[price_id]

    plan = payload.get("plan")
    if isinstance(plan, dict):
        nickname = (plan.get("nickname") or "").lower()
        for tier in ("starter", "pro", "plus"):
            if tier in nickname:
                return tier
        product_metadata = plan.get("metadata") or {}
        tier_from_product = product_metadata.get("plan_tier")
        if tier_from_product:
            return tier_from_product

    return fallback


class WebhookService:
    """Service for processing Stripe webhook events."""

    @staticmethod
    def handle_stripe_event(
        db: Session, event: Dict[str, Any], *, force: bool = False
    ) -> WebhookProcessingResult:
        event_payload = _to_dict(event)
        generated_event_id = False
        raw_event_id = event_payload.get("id")
        event_id = raw_event_id or (
            event_payload.get("data", {})
            .get("object", {})
            .get("id")
        )
        if not event_id:
            # Fallback to a generated ID so the event can be processed once.
            event_id = event_payload["id"] = f"evt-generated-{uuid.uuid4().hex}"
            generated_event_id = True
        elif raw_event_id is None:
            generated_event_id = True

        event_type = event_payload.get("type", "unknown")
        record_webhook_received("stripe", event_type)
        started_at = perf_counter()

        processed = (
            db.query(ProcessedWebhook)
            .filter(ProcessedWebhook.event_id == event_id)
            .first()
        )

        if not processed:
            processed = ProcessedWebhook(
                provider="stripe",
                event_id=event_id,
                event_type=event_type,
                payload=event_payload,
                status="pending",
            )
            db.add(processed)
            db.commit()
            db.refresh(processed)
        else:
            processed.event_type = event_type
            processed.payload = event_payload
            db.commit()
            db.refresh(processed)

        if processed.dead_letter and not force:
            duration_ms = (perf_counter() - started_at) * 1000
            record_webhook_processed("stripe", event_type, "dead_letter", duration_ms)
            return WebhookProcessingResult(
                outcome="dead_letter",
                message="Event is in dead letter queue; replay required.",
                generated_event_id=generated_event_id,
            )

        if processed.status == "processed" and not force:
            duration_ms = (perf_counter() - started_at) * 1000
            record_webhook_processed("stripe", event_type, "duplicate", duration_ms)
            return WebhookProcessingResult(
                outcome="duplicate",
                message="Event already processed.",
                generated_event_id=generated_event_id,
            )

        if force:
            processed.dead_letter = False
            processed.status = "pending"
            processed.attempts = 0
            processed.last_error = None
            processed.next_retry_at = None
            db.commit()
            db.refresh(processed)

        try:
            store_id = WebhookService._dispatch_stripe_event(db, event_type, event_payload)
            processed.status = "processed"
            processed.dead_letter = False
            processed.last_error = None
            processed.attempts = (processed.attempts or 0) + 1
            processed.processed_at = datetime.now(timezone.utc)
            processed.next_retry_at = None
            processed.updated_at = datetime.now(timezone.utc)
            if store_id:
                processed.store_id = store_id
            db.commit()

            duration_ms = (perf_counter() - started_at) * 1000
            record_webhook_processed("stripe", event_type, "processed", duration_ms)
            return WebhookProcessingResult(
                outcome="processed",
                message="Event processed",
                store_id=store_id,
                generated_event_id=generated_event_id,
            )
        except UnsupportedWebhookEventError as exc:
            db.rollback()
            processed = (
                db.query(ProcessedWebhook)
                .filter(ProcessedWebhook.event_id == event_id)
                .first()
            )
            if processed:
                processed.status = "skipped"
                processed.dead_letter = False
                processed.attempts = (processed.attempts or 0) + 1
                processed.last_error = None
                processed.processed_at = datetime.now(timezone.utc)
                processed.next_retry_at = None
                processed.updated_at = datetime.now(timezone.utc)
                db.commit()

            duration_ms = (perf_counter() - started_at) * 1000
            record_webhook_processed("stripe", event_type, "skipped", duration_ms)
            return WebhookProcessingResult(
                outcome="skipped",
                message=str(exc),
                generated_event_id=generated_event_id,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            db.rollback()
            processed = (
                db.query(ProcessedWebhook)
                .filter(ProcessedWebhook.event_id == event_id)
                .first()
            )
            attempts = 1
            if processed:
                attempts = (processed.attempts or 0) + 1
                processed.attempts = attempts
                processed.last_error = str(exc)
                processed.status = "dead_letter" if attempts >= MAX_WEBHOOK_ATTEMPTS else "failed"
                processed.dead_letter = attempts >= MAX_WEBHOOK_ATTEMPTS
                processed.next_retry_at = datetime.now(timezone.utc) + timedelta(
                    seconds=_backoff_for_attempt(attempts)
                )
                processed.updated_at = datetime.now(timezone.utc)
                db.commit()

            duration_ms = (perf_counter() - started_at) * 1000
            outcome = "dead_letter" if attempts >= MAX_WEBHOOK_ATTEMPTS else "retry"
            record_webhook_processed("stripe", event_type, outcome, duration_ms)

            if attempts >= MAX_WEBHOOK_ATTEMPTS:
                return WebhookProcessingResult(
                    outcome="dead_letter",
                    message="Event moved to dead letter queue after repeated failures.",
                    generated_event_id=generated_event_id,
                )

            return WebhookProcessingResult(
                outcome="retry",
                message="Temporary failure. Event will be retried.",
                status_code=202,
                generated_event_id=generated_event_id,
            )

    @staticmethod
    def replay_stripe_event(db: Session, event_id: str) -> Optional[WebhookProcessingResult]:
        record = (
            db.query(ProcessedWebhook)
            .filter(ProcessedWebhook.event_id == event_id)
            .first()
        )
        if not record:
            return None

        payload = record.payload or {}
        payload["id"] = event_id
        payload.setdefault("type", record.event_type)
        return WebhookService.handle_stripe_event(db, payload, force=True)

    @staticmethod
    def _dispatch_stripe_event(
        db: Session, event_type: str, event: Dict[str, Any]
    ) -> Optional[str]:
        if event_type == "customer.subscription.created":
            return WebhookService.process_subscription_created(db, event)
        if event_type == "customer.subscription.updated":
            return WebhookService.process_subscription_updated(db, event)
        if event_type == "customer.subscription.deleted":
            return WebhookService.process_subscription_deleted(db, event)
        if event_type in {"invoice.payment_succeeded", "invoice.paid"}:
            return WebhookService.process_invoice_paid(db, event)
        if event_type == "invoice.payment_failed":
            return WebhookService.process_invoice_payment_failed(db, event)

        raise UnsupportedWebhookEventError(event_type)

    @staticmethod
    def process_subscription_created(db: Session, event: dict) -> Optional[str]:
        """Process subscription.created event.
        
        Args:
            db: Database session
            event: Stripe event object
        """
        try:
            payload = _to_dict(event["data"]["object"])
            subscription_id = payload.get("id")
            if not subscription_id:
                logger.error("subscription.created missing subscription id")
                return

            if not payload.get("current_period_start") or not payload.get("current_period_end"):
                try:
                    payload = _to_dict(stripe.Subscription.retrieve(subscription_id))
                except stripe.error.StripeError as exc:  # pragma: no cover - network failure
                    logger.error("Unable to hydrate subscription %s: %s", subscription_id, exc)
                    return

            customer_id = _extract_customer_id(payload)
            if not customer_id:
                logger.error("subscription.created missing customer id")
                return

            store = (
                db.query(Store)
                .filter(Store.stripe_customer_id == customer_id)
                .first()
            )
            if not store:
                metadata_store = payload.get("metadata", {}).get("store_id")
                if metadata_store:
                    store = db.query(Store).filter(Store.id == metadata_store).first()
            if not store:
                logger.error("Store not found for customer %s", customer_id)
                return

            plan_tier = _resolve_plan_tier(payload)

            subscription = (
                db.query(Subscription)
                .filter(Subscription.stripe_subscription_id == subscription_id)
                .first()
            )
            if not subscription:
                subscription = (
                    db.query(Subscription)
                    .filter(Subscription.store_id == store.id)
                    .first()
                )
            if not subscription:
                subscription = Subscription(store_id=store.id, provider="stripe")
                db.add(subscription)

            subscription.plan = plan_tier
            subscription.plan_tier = plan_tier
            subscription.stripe_subscription_id = subscription_id
            subscription.stripe_customer_id = customer_id
            subscription.status = payload.get("status", "active")
            subscription.current_period_start = _coerce_timestamp(
                payload.get("current_period_start") or payload.get("billing_cycle_anchor")
            )
            subscription.current_period_end = _coerce_timestamp(payload.get("current_period_end"))
            subscription.cancel_at_period_end = bool(payload.get("cancel_at_period_end", False))
            subscription.trial_end = _coerce_timestamp(payload.get("trial_end"))
            subscription.updated_at = datetime.now(timezone.utc)

            if not store.stripe_customer_id:
                store.stripe_customer_id = customer_id
            store.stripe_subscription_id = subscription_id

            audit_log = AuditLog(
                actor="stripe_webhook",
                action="stripe_webhook",
                payload={
                    "store_id": str(store.id),
                    "event_type": "subscription.created",
                    "subscription_id": subscription_id,
                    "plan_tier": plan_tier,
                    "status": payload.get("status", "active"),
                },
            )
            db.add(audit_log)

            db.commit()

            log_billing_event(
                "subscription_created",
                store_id=str(store.id),
                plan_tier=plan_tier,
                subscription_id=subscription_id,
            )

            logger.info("Processed subscription.created for store %s", store.id)
            return str(store.id)

        except Exception as exc:  # pragma: no cover - defensive guard
            logger.error("Error processing subscription.created: %s", exc)
            db.rollback()
            raise
    
    @staticmethod
    def process_subscription_updated(db: Session, event: dict) -> Optional[str]:
        """Process subscription.updated event.
        
        Args:
            db: Database session
            event: Stripe event object
        """
        try:
            payload = _to_dict(event["data"]["object"])
            subscription_id = payload.get("id")
            if not subscription_id:
                logger.error("subscription.updated missing subscription id")
                return

            if not payload.get("current_period_start") or not payload.get("current_period_end"):
                try:
                    payload = _to_dict(stripe.Subscription.retrieve(subscription_id))
                except stripe.error.StripeError as exc:  # pragma: no cover
                    logger.error("Unable to hydrate subscription %s: %s", subscription_id, exc)
                    return

            subscription = (
                db.query(Subscription)
                .filter(Subscription.stripe_subscription_id == subscription_id)
                .first()
            )

            if not subscription:
                customer_id = _extract_customer_id(payload)
                store = None
                if customer_id:
                    store = (
                        db.query(Store)
                        .filter(Store.stripe_customer_id == customer_id)
                        .first()
                    )
                if not store:
                    metadata_store = payload.get("metadata", {}).get("store_id")
                    if metadata_store:
                        store = db.query(Store).filter(Store.id == metadata_store).first()
                if not store:
                    logger.error("Store not found for subscription %s", subscription_id)
                    return
                subscription = Subscription(store_id=store.id, provider="stripe")
                db.add(subscription)
            else:
                store = db.query(Store).filter(Store.id == subscription.store_id).first()

            plan_tier = _resolve_plan_tier(payload, subscription.plan_tier or "starter")
            old_status = subscription.status
            subscription.plan = plan_tier
            subscription.plan_tier = plan_tier
            subscription.status = payload.get("status", subscription.status or "active")
            subscription.stripe_subscription_id = subscription_id
            subscription.stripe_customer_id = _extract_customer_id(payload) or subscription.stripe_customer_id
            subscription.current_period_start = _coerce_timestamp(
                payload.get("current_period_start") or payload.get("billing_cycle_anchor")
            )
            subscription.current_period_end = _coerce_timestamp(payload.get("current_period_end"))
            subscription.cancel_at_period_end = bool(payload.get("cancel_at_period_end", False))
            subscription.trial_end = _coerce_timestamp(payload.get("trial_end"))
            subscription.updated_at = datetime.now(timezone.utc)

            if store:
                if subscription.stripe_customer_id and not store.stripe_customer_id:
                    store.stripe_customer_id = subscription.stripe_customer_id
                store.stripe_subscription_id = subscription_id

            audit_log = AuditLog(
                actor="stripe_webhook",
                action="stripe_webhook",
                payload={
                    "store_id": str(subscription.store_id),
                    "event_type": "subscription.updated",
                    "subscription_id": subscription_id,
                    "old_status": old_status,
                    "new_status": subscription.status,
                    "cancel_at_period_end": subscription.cancel_at_period_end,
                },
            )
            db.add(audit_log)

            db.commit()

            log_billing_event(
                "subscription_updated",
                store_id=str(subscription.store_id),
                old_status=old_status,
                new_status=subscription.status,
            )

            logger.info("Processed subscription.updated for subscription %s", subscription_id)
            return str(subscription.store_id)

        except Exception as exc:  # pragma: no cover
            logger.error("Error processing subscription.updated: %s", exc)
            db.rollback()
            raise
    
    @staticmethod
    def process_subscription_deleted(db: Session, event: dict) -> Optional[str]:
        """Process subscription.deleted event.
        
        Args:
            db: Database session
            event: Stripe event object
        """
        try:
            subscription_obj = event["data"]["object"]
            subscription_id = subscription_obj["id"]
            
            # Find subscription
            subscription = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == subscription_id
            ).first()
            
            if not subscription:
                logger.error(f"Subscription not found: {subscription_id}")
                return
            
            # Update status to canceled
            subscription.status = "canceled"
            subscription.updated_at = datetime.now(timezone.utc)
            
            # Create audit log
            audit_log = AuditLog(
                actor="stripe_webhook",
                action="stripe_webhook",
                payload={
                    "store_id": str(subscription.store_id),
                    "event_type": "subscription.deleted",
                    "subscription_id": subscription_id,
                },
            )
            db.add(audit_log)
            
            db.commit()
            
            log_billing_event(
                "subscription_deleted",
                store_id=str(subscription.store_id),
                subscription_id=subscription_id
            )
            
            logger.info(f"Processed subscription.deleted for subscription {subscription_id}")
            return str(subscription.store_id)
            
        except Exception as e:
            logger.error(f"Error processing subscription.deleted: {e}")
            db.rollback()
            raise
    
    @staticmethod
    def process_invoice_paid(db: Session, event: dict) -> Optional[str]:
        """Process invoice.paid event.
        
        Args:
            db: Database session
            event: Stripe event object
        """
        try:
            invoice_obj = event["data"]["object"]
            subscription_id = invoice_obj.get("subscription")
            
            if not subscription_id:
                return
            
            # Find subscription
            subscription = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == subscription_id
            ).first()
            
            if not subscription:
                logger.error(f"Subscription not found: {subscription_id}")
                return
            
            # Update billing period
            if invoice_obj.get("period_start") and invoice_obj.get("period_end"):
                subscription.current_period_start = datetime.fromtimestamp(
                    invoice_obj["period_start"], tz=timezone.utc
                )
                subscription.current_period_end = datetime.fromtimestamp(
                    invoice_obj["period_end"], tz=timezone.utc
                )
                subscription.updated_at = datetime.now(timezone.utc)
            
            # Create audit log
            audit_log = AuditLog(
                actor="stripe_webhook",
                action="stripe_webhook",
                payload={
                    "store_id": str(subscription.store_id),
                    "event_type": "invoice.paid",
                    "invoice_id": invoice_obj["id"],
                    "subscription_id": subscription_id,
                    "amount_paid": invoice_obj.get("amount_paid", 0) / 100,
                },
            )
            db.add(audit_log)
            
            db.commit()
            
            log_billing_event(
                "invoice_paid",
                store_id=str(subscription.store_id),
                subscription_id=subscription_id,
                amount=invoice_obj.get("amount_paid", 0) / 100
            )
            
            logger.info(f"Processed invoice.paid for subscription {subscription_id}")
            return str(subscription.store_id)
            
        except Exception as e:
            logger.error(f"Error processing invoice.paid: {e}")
            db.rollback()
            raise
    
    @staticmethod
    def process_invoice_payment_failed(db: Session, event: dict) -> Optional[str]:
        """Process invoice.payment_failed event.
        
        Args:
            db: Database session
            event: Stripe event object
        """
        try:
            invoice_obj = event["data"]["object"]
            subscription_id = invoice_obj.get("subscription")
            
            if not subscription_id:
                return
            
            # Find subscription
            subscription = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == subscription_id
            ).first()
            
            if not subscription:
                logger.error(f"Subscription not found: {subscription_id}")
                return
            
            # Create audit log
            audit_log = AuditLog(
                actor="stripe_webhook",
                action="stripe_webhook",
                payload={
                    "store_id": str(subscription.store_id),
                    "event_type": "invoice.payment_failed",
                    "invoice_id": invoice_obj["id"],
                    "subscription_id": subscription_id,
                    "attempt_count": invoice_obj.get("attempt_count", 0),
                },
            )
            db.add(audit_log)
            
            db.commit()
            
            log_billing_event(
                "invoice_payment_failed",
                store_id=str(subscription.store_id),
                subscription_id=subscription_id
            )
            
            logger.warning(f"Payment failed for subscription {subscription_id}")
            return str(subscription.store_id)
            
        except Exception as e:
            logger.error(f"Error processing invoice.payment_failed: {e}")
            db.rollback()
            raise
