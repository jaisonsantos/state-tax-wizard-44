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

# Track decision latency in milliseconds
decision_latency_ms = Histogram(
    "decision_latency_ms",
    "Time spent deciding fees in milliseconds",
    ["operation", "jurisdiction", "outcome"],
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


def ensure_request_id(request_id: str | None) -> str:
    """Ensure every request has a stable identifier."""

    return request_id or str(uuid.uuid4())
