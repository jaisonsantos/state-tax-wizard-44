"""HMAC helpers for request signing and replay protection."""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Mapping

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models.models import ProcessedNonce, StoreSetting
from ..observability import (
    hmac_replay_attempts_total,
    hmac_validation_failures_total,
    log_security_event,
)

HEADER_SIGNATURE = "x-rdf-signature"
HEADER_TIMESTAMP = "x-rdf-timestamp"
HEADER_NONCE = "x-rdf-nonce"


def compute_signature(secret: str, timestamp: str, nonce: str, body: bytes) -> str:
    """Return the lowercase hex digest for the canonical HMAC payload."""

    canonical = b"\n".join(
        (
            timestamp.encode("utf-8"),
            nonce.encode("utf-8"),
            body,
        )
    )
    digest = hmac.new(secret.encode("utf-8"), canonical, hashlib.sha256)
    return digest.hexdigest()


def _strip_prefix(signature: str) -> str:
    candidate = signature.strip()
    if candidate.lower().startswith("sha256="):
        candidate = candidate.split("=", 1)[1].strip()
    return candidate.lower()


def _parse_timestamp(raw: str) -> datetime:
    candidate = raw.strip()
    if not candidate:
        raise ValueError("Timestamp header was empty")

    normalised = candidate
    if normalised.endswith("Z"):
        normalised = normalised[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalised)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        # Fallback to Unix timestamp (seconds)
        try:
            return datetime.fromtimestamp(float(candidate), tz=timezone.utc)
        except ValueError as exc:  # pragma: no cover - defensive branch
            raise ValueError("Invalid timestamp format") from exc


def _raise_failure(store_id: str, status_code: int, code: str, message: str) -> None:
    hmac_validation_failures_total.labels(reason=code, store_id=store_id).inc()
    log_security_event(
        {
            "event": "hmac_validation_failed",
            "store_id": store_id,
            "code": code,
            "message": message,
        }
    )
    raise HTTPException(status_code=status_code, detail={"code": code, "message": message})


def _validate_nonce(db: Session, store_id: str, nonce: str, now: datetime) -> None:
    if not nonce:
        _raise_failure(store_id, 401, "missing_nonce", "Missing X-RDF-Nonce header")
    if len(nonce) > 128:
        _raise_failure(store_id, 401, "invalid_nonce", "Nonce exceeds maximum length of 128 characters")

    ttl_seconds = max(settings.hmac_replay_ttl_seconds, 1)
    expires_at = now + timedelta(seconds=ttl_seconds)

    db.query(ProcessedNonce).filter(ProcessedNonce.expires_at < now).delete(
        synchronize_session=False
    )

    record = ProcessedNonce(
        store_id=store_id,
        nonce=nonce,
        expires_at=expires_at,
    )
    db.add(record)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        hmac_replay_attempts_total.labels(store_id=store_id).inc()
        log_security_event(
            {
                "event": "hmac_replay_detected",
                "store_id": store_id,
                "nonce_preview": nonce[:8],
            }
        )
        _raise_failure(store_id, 409, "replay_detected", "Nonce was already processed")
    else:
        log_security_event(
            {
                "event": "hmac_nonce_recorded",
                "store_id": store_id,
                "nonce_preview": nonce[:8],
                "expires_at": expires_at.isoformat(),
            }
        )


def enforce_hmac(
    *,
    headers: Mapping[str, str],
    body: bytes,
    settings_model: StoreSetting | None,
    store_id: str,
    db: Session,
    now: datetime | None = None,
) -> None:
    """Validate the HMAC signature headers for a request."""

    secret = (settings_model.hmac_secret or "").strip() if settings_model else ""
    if not secret:
        return

    store_id_str = str(store_id)

    timestamp_header = headers.get(HEADER_TIMESTAMP)
    if not timestamp_header:
        _raise_failure(store_id_str, 401, "missing_timestamp", "Missing X-RDF-Timestamp header")

    nonce_header = headers.get(HEADER_NONCE)
    signature_header = headers.get(HEADER_SIGNATURE)
    if not signature_header:
        _raise_failure(store_id_str, 401, "missing_signature", "Missing X-RDF-Signature header")

    try:
        parsed_timestamp = _parse_timestamp(timestamp_header)
    except ValueError as exc:
        _raise_failure(store_id_str, 401, "invalid_timestamp", str(exc))

    current = now or datetime.now(timezone.utc)
    skew_seconds = abs((current - parsed_timestamp).total_seconds())
    if skew_seconds > settings.hmac_max_skew_seconds:
        _raise_failure(store_id_str, 401, "stale_timestamp", "Timestamp outside allowable window")

    nonce_value = nonce_header or ""
    _validate_nonce(db, store_id_str, nonce_value, current)

    expected = compute_signature(secret, parsed_timestamp.isoformat(), nonce_value, body)
    provided = _strip_prefix(signature_header)

    if not hmac.compare_digest(provided, expected):
        _raise_failure(store_id_str, 403, "invalid_signature", "HMAC signature mismatch")

    log_security_event(
        {
            "event": "hmac_validation_succeeded",
            "store_id": store_id_str,
            "timestamp": parsed_timestamp.isoformat(),
        }
    )
