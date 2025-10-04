from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.models.models import AuditLog, OrderFee, ProcessedNonce, RuleVersion, StoreSetting
from app.observability import rate_limit_throttles_total
from app.security.rate_limit import rate_limiter
from app.security.hmac import compute_signature


def _enable_hmac(db_session: Session, store_id: str, secret: str = "test-secret") -> str:
    store_settings = (
        db_session.query(StoreSetting).filter(StoreSetting.store_id == store_id).one()
    )
    store_settings.hmac_secret = secret
    store_settings.hmac_secret_rotated_at = datetime.now(timezone.utc)
    db_session.commit()
    return secret


def _create_rule_versions(db_session: Session) -> None:
    db_session.add(
        RuleVersion(
            jurisdiction="MN",
            version="MN-security",
            effective_from=datetime.now(timezone.utc) - timedelta(days=1),
            effective_to=None,
            params={"threshold_cents": 10000, "fee_cents": 50},
        )
    )
    db_session.add(
        RuleVersion(
            jurisdiction="CO",
            version="CO-security",
            effective_from=datetime.now(timezone.utc) - timedelta(days=1),
            effective_to=None,
            params={"rate_cents": 28},
        )
    )
    db_session.commit()


def _login(client: TestClient) -> tuple[str, str]:
    rate_limiter.reset()
    response = client.post(
        "/api/auth/login",
        json={"email": f"security-{uuid.uuid4()}@example.com", "password": "secret"},
    )
    payload = response.json()
    return payload["token"], payload["stores"][0]["id"]


def test_hmac_enforcement(client: TestClient, db_session: Session) -> None:
    token, store_id = _login(client)
    auth_header = {"Authorization": f"Bearer {token}"}
    _create_rule_versions(db_session)

    secret = _enable_hmac(db_session, store_id)

    original_skew = app_settings.hmac_max_skew_seconds
    original_ttl = app_settings.hmac_replay_ttl_seconds
    app_settings.hmac_max_skew_seconds = 300
    app_settings.hmac_replay_ttl_seconds = 60

    payload = {
        "store_id": store_id,
        "order_id": "hmac-test",
        "destination": {"state": "MN"},
        "delivery_method": "ship",
        "items": [
            {"sku": "SKU", "qty": 1, "unit_price_cents": 15000, "taxability": "taxable"}
        ],
        "shipping_amount_cents": 0,
    }

    try:
        # Missing signature
        unsigned_body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        unsigned_headers = dict(auth_header)
        timestamp = datetime.now(timezone.utc).isoformat()
        unsigned_headers.update(
            {
                "Content-Type": "application/json",
                "x-rdf-timestamp": timestamp,
                "x-rdf-nonce": uuid.uuid4().hex,
            }
        )
        missing = client.post("/api/v1/fees/apply", content=unsigned_body, headers=unsigned_headers)
        assert missing.status_code == 401
        assert missing.json()["detail"]["code"] == "missing_signature"

        # Invalid signature
        invalid_headers = dict(unsigned_headers)
        invalid_headers["x-rdf-signature"] = "not-a-valid-signature"
        invalid = client.post("/api/v1/fees/apply", content=unsigned_body, headers=invalid_headers)
        assert invalid.status_code == 403
        assert invalid.json()["detail"]["code"] == "invalid_signature"

        # Valid signature
        valid_headers = dict(auth_header)
        timestamp_iso = datetime.now(timezone.utc).isoformat()
        nonce_value = uuid.uuid4().hex
        signature = compute_signature(secret, timestamp_iso, nonce_value, unsigned_body)
        valid_headers.update(
            {
                "Content-Type": "application/json",
                "x-rdf-signature": signature,
                "x-rdf-timestamp": timestamp_iso,
                "x-rdf-nonce": nonce_value,
            }
        )
        success = client.post("/api/v1/fees/apply", content=unsigned_body, headers=valid_headers)
        assert success.status_code == 200
        response_body = success.json()
        assert response_body["success"] is True
        db_session.expire_all()
        assert (
            db_session.query(OrderFee).filter(OrderFee.order_id == "hmac-test").count() == 1
        )
        assert (
            db_session.query(ProcessedNonce)
            .filter(ProcessedNonce.store_id == store_id, ProcessedNonce.nonce == nonce_value)
            .count()
            == 1
        )

        # Prefixed signature format is also accepted
        prefixed_timestamp = datetime.now(timezone.utc).isoformat()
        prefixed_nonce = uuid.uuid4().hex
        prefixed_signature = compute_signature(secret, prefixed_timestamp, prefixed_nonce, unsigned_body)
        prefixed_headers = dict(auth_header)
        prefixed_headers.update(
            {
                "Content-Type": "application/json",
                "x-rdf-signature": f"sha256={prefixed_signature}",
                "x-rdf-timestamp": prefixed_timestamp,
                "x-rdf-nonce": prefixed_nonce,
            }
        )
        prefixed = client.post("/api/v1/fees/apply", content=unsigned_body, headers=prefixed_headers)
        assert prefixed.status_code == 200

        # Replay detection blocks duplicate nonce
        replay = client.post("/api/v1/fees/apply", content=unsigned_body, headers=valid_headers)
        assert replay.status_code == 409
        assert replay.json()["detail"]["code"] == "replay_detected"

        # Expired timestamp is rejected
        stale_headers = dict(valid_headers)
        stale_time = datetime.now(timezone.utc) - timedelta(seconds=app_settings.hmac_max_skew_seconds + 30)
        stale_timestamp = stale_time.isoformat()
        stale_signature = compute_signature(secret, stale_timestamp, uuid.uuid4().hex, unsigned_body)
        stale_headers.update(
            {
                "x-rdf-timestamp": stale_timestamp,
                "x-rdf-nonce": uuid.uuid4().hex,
                "x-rdf-signature": stale_signature,
            }
        )
        stale = client.post("/api/v1/fees/apply", content=unsigned_body, headers=stale_headers)
        assert stale.status_code == 401
        assert stale.json()["detail"]["code"] == "stale_timestamp"

        # Expired nonce entries are purged allowing reuse after TTL
        record = (
            db_session.query(ProcessedNonce)
            .filter(ProcessedNonce.store_id == store_id, ProcessedNonce.nonce == nonce_value)
            .one()
        )
        record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        db_session.add(record)
        db_session.commit()
        db_session.expire_all()

        fresh_timestamp = datetime.now(timezone.utc).isoformat()
        fresh_signature = compute_signature(secret, fresh_timestamp, nonce_value, unsigned_body)
        refreshed_headers = dict(auth_header)
        refreshed_headers.update(
            {
                "Content-Type": "application/json",
                "x-rdf-signature": fresh_signature,
                "x-rdf-timestamp": fresh_timestamp,
                "x-rdf-nonce": nonce_value,
            }
        )
        refreshed = client.post("/api/v1/fees/apply", content=unsigned_body, headers=refreshed_headers)
        assert refreshed.status_code == 200
    finally:
        app_settings.hmac_max_skew_seconds = original_skew
        app_settings.hmac_replay_ttl_seconds = original_ttl


def test_replay_detected_without_unique_index(client: TestClient, db_session: Session) -> None:
    token, store_id = _login(client)
    auth_header = {"Authorization": f"Bearer {token}"}
    _create_rule_versions(db_session)

    secret = _enable_hmac(db_session, store_id)

    payload = {
        "store_id": store_id,
        "order_id": "missing-index",
        "destination": {"state": "MN"},
        "delivery_method": "ship",
        "items": [
            {"sku": "SKU", "qty": 1, "unit_price_cents": 15000, "taxability": "taxable"}
        ],
        "shipping_amount_cents": 0,
    }

    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    timestamp_iso = datetime.now(timezone.utc).isoformat()
    nonce_value = uuid.uuid4().hex
    signature = compute_signature(secret, timestamp_iso, nonce_value, body)

    headers = dict(auth_header)
    headers.update(
        {
            "Content-Type": "application/json",
            "x-rdf-signature": signature,
            "x-rdf-timestamp": timestamp_iso,
            "x-rdf-nonce": nonce_value,
        }
    )

    success = client.post("/api/v1/fees/apply", content=body, headers=headers)
    assert success.status_code == 200

    db_session.execute(text("DROP INDEX IF EXISTS uq_processed_nonces_store_nonce"))
    db_session.commit()

    replay = client.post("/api/v1/fees/apply", content=body, headers=headers)
    assert replay.status_code == 409
    assert replay.json()["detail"]["code"] == "replay_detected"


def test_rate_limit_per_token_route(client: TestClient, db_session: Session) -> None:
    token, store_id = _login(client)
    auth_header = {"Authorization": f"Bearer {token}"}
    _create_rule_versions(db_session)

    original_limit = rate_limiter.limit
    rate_limiter.limit = 2
    rate_limiter.reset()
    try:
        metric = rate_limit_throttles_total.labels(route="quote")
        before = metric._value.get()
        payload = {
            "store_id": store_id,
            "destination": {"state": "MN"},
            "delivery_method": "ship",
            "items": [
                {
                    "sku": "SKU",
                    "qty": 1,
                    "unit_price_cents": 15000,
                    "taxability": "taxable",
                }
            ],
            "shipping_amount_cents": 0,
        }

        first = client.post("/api/v1/fees/quote", json=payload, headers=auth_header)
        assert first.status_code == 200
        second = client.post("/api/v1/fees/quote", json=payload, headers=auth_header)
        assert second.status_code == 200
        third = client.post("/api/v1/fees/quote", json=payload, headers=auth_header)
        assert third.status_code == 429
        detail = third.json()["detail"]
        assert detail["route"] == "quote"
        after = metric._value.get()
        assert after == before + 1
    finally:
        rate_limiter.limit = original_limit
        rate_limiter.reset()


def test_hmac_accepts_iso_timestamp_with_z_suffix(client: TestClient, db_session: Session) -> None:
    token, store_id = _login(client)
    auth_header = {"Authorization": f"Bearer {token}"}
    _create_rule_versions(db_session)
    secret = _enable_hmac(db_session, store_id)

    payload = {
        "store_id": store_id,
        "order_id": "hmac-z-test",
        "destination": {"state": "MN"},
        "delivery_method": "ship",
        "items": [
            {"sku": "SKU", "qty": 1, "unit_price_cents": 15000, "taxability": "taxable"}
        ],
        "shipping_amount_cents": 0,
    }

    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    timestamp_z = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    nonce_value = uuid.uuid4().hex
    signature = compute_signature(secret, timestamp_z, nonce_value, body)

    headers = {
        **auth_header,
        "Content-Type": "application/json",
        "x-rdf-timestamp": timestamp_z,
        "x-rdf-nonce": nonce_value,
        "x-rdf-signature": signature,
    }

    response = client.post("/api/v1/fees/apply", content=body, headers=headers)
    assert response.status_code == 200


def test_hmac_accepts_epoch_timestamp(client: TestClient, db_session: Session) -> None:
    token, store_id = _login(client)
    auth_header = {"Authorization": f"Bearer {token}"}
    _create_rule_versions(db_session)
    secret = _enable_hmac(db_session, store_id)

    payload = {
        "store_id": store_id,
        "order_id": "hmac-epoch-test",
        "destination": {"state": "MN"},
        "delivery_method": "ship",
        "items": [
            {"sku": "SKU", "qty": 1, "unit_price_cents": 15000, "taxability": "taxable"}
        ],
        "shipping_amount_cents": 0,
    }

    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    timestamp_epoch = str(int(datetime.now(timezone.utc).timestamp()))
    nonce_value = uuid.uuid4().hex
    signature = compute_signature(secret, timestamp_epoch, nonce_value, body)

    headers = {
        **auth_header,
        "Content-Type": "application/json",
        "x-rdf-timestamp": timestamp_epoch,
        "x-rdf-nonce": nonce_value,
        "x-rdf-signature": signature,
    }

    response = client.post("/api/v1/fees/apply", content=body, headers=headers)
    assert response.status_code == 200


def test_security_logs_do_not_expose_secrets(
    client: TestClient, db_session: Session, caplog
) -> None:
    token, store_id = _login(client)
    auth_header = {"Authorization": f"Bearer {token}"}
    _create_rule_versions(db_session)
    secret = _enable_hmac(db_session, store_id, secret="log-guard-secret")

    payload = {
        "store_id": store_id,
        "order_id": "hmac-log-test",
        "destination": {"state": "MN"},
        "delivery_method": "ship",
        "items": [
            {"sku": "SKU", "qty": 1, "unit_price_cents": 15000, "taxability": "taxable"}
        ],
        "shipping_amount_cents": 0,
    }

    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    timestamp_iso = datetime.now(timezone.utc).isoformat()
    nonce_value = uuid.uuid4().hex
    invalid_signature = "deadbeef"

    headers = {
        **auth_header,
        "Content-Type": "application/json",
        "x-rdf-timestamp": timestamp_iso,
        "x-rdf-nonce": nonce_value,
        "x-rdf-signature": invalid_signature,
    }

    caplog.set_level("INFO", logger="security")
    response = client.post("/api/v1/fees/apply", content=body, headers=headers)
    assert response.status_code == 403
    log_output = "\n".join(record.getMessage() for record in caplog.records)
    assert log_output
    assert "hmac_validation_failed" in log_output
    assert secret not in log_output
    assert invalid_signature not in log_output


def test_secret_rotation_invalidates_previous_signatures(
    client: TestClient, db_session: Session
) -> None:
    token, store_id = _login(client)
    auth_header = {"Authorization": f"Bearer {token}"}
    _create_rule_versions(db_session)

    original_secret = _enable_hmac(db_session, store_id, secret="rotate-old-secret")

    payload = {
        "store_id": store_id,
        "order_id": "rotate-test-order",
        "destination": {"state": "CO"},
        "delivery_method": "ship",
        "items": [
            {"sku": "SKU", "qty": 1, "unit_price_cents": 15000, "taxability": "taxable"}
        ],
        "shipping_amount_cents": 0,
    }

    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    timestamp = datetime.now(timezone.utc).isoformat()
    nonce = uuid.uuid4().hex
    signature = compute_signature(original_secret, timestamp, nonce, body)
    signed_headers = {
        **auth_header,
        "Content-Type": "application/json",
        "x-rdf-timestamp": timestamp,
        "x-rdf-nonce": nonce,
        "x-rdf-signature": signature,
    }

    first_apply = client.post("/api/v1/fees/apply", content=body, headers=signed_headers)
    assert first_apply.status_code == 200

    rotate_response = client.post(
        f"/api/v1/stores/{store_id}/hmac/rotate",
        headers=auth_header,
    )
    assert rotate_response.status_code == 200
    rotation_payload = rotate_response.json()
    assert rotation_payload["store_id"] == store_id
    new_secret = rotation_payload["hmac_secret"]
    assert isinstance(new_secret, str) and len(new_secret) >= 40
    assert rotation_payload["rotated_at"]

    db_session.expire_all()
    settings = (
        db_session.query(StoreSetting)
        .filter(StoreSetting.store_id == store_id)
        .one()
    )
    assert settings.hmac_secret == new_secret
    assert settings.hmac_secret_rotated_at is not None

    audit_entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "store_secret.rotated")
        .order_by(AuditLog.ts.desc())
        .first()
    )
    assert audit_entry is not None
    assert audit_entry.payload.get("store_id") == store_id
    assert "hmac_secret" not in audit_entry.payload

    replay_with_old_secret = client.post(
        "/api/v1/fees/apply",
        content=body,
        headers=signed_headers,
    )
    assert replay_with_old_secret.status_code == 403
    assert replay_with_old_secret.json()["detail"]["code"] == "invalid_signature"

    refreshed_timestamp = datetime.now(timezone.utc).isoformat()
    refreshed_nonce = uuid.uuid4().hex
    refreshed_signature = compute_signature(
        new_secret,
        refreshed_timestamp,
        refreshed_nonce,
        body,
    )
    refreshed_headers = {
        **auth_header,
        "Content-Type": "application/json",
        "x-rdf-timestamp": refreshed_timestamp,
        "x-rdf-nonce": refreshed_nonce,
        "x-rdf-signature": refreshed_signature,
    }

    refreshed_apply = client.post(
        "/api/v1/fees/apply",
        content=body,
        headers=refreshed_headers,
    )
    assert refreshed_apply.status_code == 200
