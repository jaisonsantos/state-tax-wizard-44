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


def ensure_request_id(request_id: str | None) -> str:
    """Ensure every request has a stable identifier."""

    return request_id or str(uuid.uuid4())
