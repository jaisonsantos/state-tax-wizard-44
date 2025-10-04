"""Shared observability primitives (metrics & logging)."""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict

from prometheus_client import Counter, Histogram

fees_applied_total = Counter(
    "fees_applied_total",
    "Total number of fee applications processed",
    ["jurisdiction"],
)

fees_absorbed_total = Counter(
    "fees_absorbed_total",
    "Count of fees absorbed instead of shown to shoppers",
    ["jurisdiction"],
)

report_exports_total = Counter(
    "report_exports_total",
    "Total number of report exports generated",
    ["jurisdiction", "format"],
)

auth_events_total = Counter(
    "auth_events_total",
    "Total number of authentication lifecycle events",
    ["event"],
)

analytics_dashboard_loaded_total = Counter(
    "analytics_dashboard_loaded_total",
    "Number of analytics dashboard responses served",
    ["store_id"],
)

hmac_validation_failures_total = Counter(
    "hmac_validation_failures_total",
    "Count of failed HMAC validation attempts",
    ["reason", "store_id"],
)

hmac_replay_attempts_total = Counter(
    "hmac_replay_attempts_total",
    "Count of replayed HMAC nonce attempts",
    ["store_id"],
)

rate_limit_throttles_total = Counter(
    "rate_limit_throttles_total",
    "Count of requests throttled by the rate limiter",
    ["route"],
)

billing_events_total = Counter(
    "billing_events_total",
    "Count of billing lifecycle events",
    ["event"],
)

checkout_sessions_created_total = Counter(
    "checkout_sessions_created_total",
    "Number of Stripe Checkout sessions created",
    ["plan_tier"],
)

entitlement_denials_total = Counter(
    "entitlement_denials_total",
    "Count of entitlement denials by feature and plan",
    ["feature", "plan"],
)

integrations_requests_total = Counter(
    "integrations_requests_total",
    "Total number of integration API requests processed",
    ["provider", "route"],
)

integrations_errors_total = Counter(
    "integrations_errors_total",
    "Count of integration related errors by provider and reason",
    ["provider", "reason"],
)

webhooks_received_total = Counter(
    "webhooks_received_total",
    "Count of incoming webhook events grouped by provider and event type",
    ["provider", "event"],
)

webhooks_processed_total = Counter(
    "webhooks_processed_total",
    "Count of processed webhook events grouped by provider, event type, and outcome",
    ["provider", "event", "outcome"],
)

webhooks_delivery_total = Counter(
    "webhooks_delivery_total",
    "Count of outgoing webhook delivery attempts grouped by event and status",
    ["event", "status"],
)

webhooks_delivery_seconds = Histogram(
    "webhooks_delivery_seconds",
    "Duration of outgoing webhook deliveries in seconds",
    ["event"],
)

webhooks_failed_total = Counter(
    "webhooks_failed_total",
    "Count of outgoing webhook delivery failures grouped by event and reason",
    ["event", "reason"],
)

webhooks_dead_letter_total = Counter(
    "webhooks_dead_letter_total",
    "Count of outgoing webhook events moved to the dead letter queue",
    ["event"],
)

# Track webhook processing latency in milliseconds
webhook_processing_latency_ms = Histogram(
    "webhook_processing_latency_ms",
    "Webhook processing duration in milliseconds",
    ["provider", "event"],
)

# Track decision latency in milliseconds
decision_latency_ms = Histogram(
    "decision_latency_ms",
    "Time spent deciding fees in milliseconds",
    ["route", "jurisdiction", "outcome"],
)


def setup_logging() -> None:
    """Configure a simple JSON-friendly logger."""

    root = logging.getLogger()
    if root.handlers:
        # Already configured
        return

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def log_fee_event(event: Dict[str, Any]) -> None:
    """Emit a structured fee event log."""

    logger = logging.getLogger("fee")
    logger.info(json.dumps(event, default=str))


def log_report_event(event: Dict[str, Any]) -> None:
    """Emit a structured report export event log."""

    logger = logging.getLogger("report")
    logger.info(json.dumps(event, default=str))


def log_auth_event(event: Dict[str, Any]) -> None:
    """Emit a structured authentication lifecycle event log."""

    logger = logging.getLogger("auth")
    logger.info(json.dumps(event, default=str))


def log_analytics_event(event: Dict[str, Any]) -> None:
    """Emit a structured analytics dashboard log."""

    logger = logging.getLogger("analytics")
    logger.info(json.dumps(event, default=str))


def log_security_event(event: Dict[str, Any]) -> None:
    """Emit a structured security log entry."""

    logger = logging.getLogger("security")
    logger.info(json.dumps(event, default=str))


def log_webhook_delivery(event: Dict[str, Any]) -> None:
    """Emit a structured outgoing webhook delivery log."""

    logger = logging.getLogger("webhook")
    logger.info(json.dumps(event, default=str))


def log_billing_event(event: str, **kwargs) -> None:
    """Emit a structured billing event log."""
    from datetime import datetime, timezone

    billing_events_total.labels(event=event).inc()
    logger = logging.getLogger("billing")
    logger.info(json.dumps({
        "event": event,
        **kwargs,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, default=str))


def ensure_request_id(request_id: str | None) -> str:
    """Ensure every request has a stable identifier."""

    return request_id or str(uuid.uuid4())


def record_integration_request(provider: str, route: str) -> None:
    """Increment integration request counter with normalized labels."""

    integrations_requests_total.labels(provider=provider, route=route).inc()


def record_integration_error(provider: str, reason: str) -> None:
    """Increment integration error counter for observability dashboards."""

    integrations_errors_total.labels(provider=provider, reason=reason).inc()


def record_webhook_received(provider: str, event: str) -> None:
    """Increment counter when a webhook notification arrives."""

    webhooks_received_total.labels(provider=provider, event=event).inc()


def record_webhook_processed(provider: str, event: str, outcome: str, duration_ms: float) -> None:
    """Track webhook processing outcome and latency."""

    webhooks_processed_total.labels(provider=provider, event=event, outcome=outcome).inc()
    webhook_processing_latency_ms.labels(provider=provider, event=event).observe(duration_ms)


def record_outgoing_webhook_delivery(event: str, status: str, duration_seconds: float) -> None:
    """Record metrics for outgoing webhook deliveries."""

    webhooks_delivery_total.labels(event=event, status=status).inc()
    webhooks_delivery_seconds.labels(event=event).observe(duration_seconds)


def record_outgoing_webhook_failure(event: str, reason: str) -> None:
    """Record metrics for outgoing webhook delivery failures."""

    webhooks_failed_total.labels(event=event, reason=reason).inc()


def record_outgoing_webhook_dead_letter(event: str) -> None:
    """Record metrics when a webhook event is moved to the DLQ."""

    webhooks_dead_letter_total.labels(event=event).inc()
