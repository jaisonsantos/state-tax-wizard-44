from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import OrderFee, RuleVersion, StoreSetting
from app.security.rate_limit import rate_limiter


def _create_rule_versions(db_session: Session) -> None:
    db_session.add(
        RuleVersion(
            jurisdiction="MN",
            version="MN-security",
            effective_from=datetime.utcnow() - timedelta(days=1),
            effective_to=None,
            params={"threshold_cents": 10000, "fee_cents": 50},
        )
    )
    db_session.add(
        RuleVersion(
            jurisdiction="CO",
            version="CO-security",
            effective_from=datetime.utcnow() - timedelta(days=1),
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

    settings = db_session.query(StoreSetting).filter(StoreSetting.store_id == store_id).one()
    settings.hmac_secret = "test-secret"
    db_session.commit()

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

    # Missing signature
    missing = client.post("/api/v1/fees/apply", json=payload, headers=auth_header)
    assert missing.status_code == 401

    # Invalid signature
    body = json.dumps(payload).encode()
    invalid_headers = dict(auth_header)
    invalid_headers.update({
        "Content-Type": "application/json",
        "x-rdf-signature": "not-a-valid-signature",
    })
    invalid = client.post("/api/v1/fees/apply", data=body, headers=invalid_headers)
    assert invalid.status_code == 403

    # Valid signature
    valid_headers = dict(auth_header)
    valid_headers.update({
        "Content-Type": "application/json",
        "x-rdf-signature": hmac.new(settings.hmac_secret.encode(), body, hashlib.sha256).hexdigest(),
    })
    success = client.post("/api/v1/fees/apply", data=body, headers=valid_headers)
    assert success.status_code == 200
    response_body = success.json()
    assert response_body["success"] is True
    assert db_session.query(OrderFee).filter(OrderFee.order_id == "hmac-test").count() == 1


def test_rate_limit_per_token_route(client: TestClient, db_session: Session) -> None:
    token, store_id = _login(client)
    auth_header = {"Authorization": f"Bearer {token}"}
    _create_rule_versions(db_session)

    original_limit = rate_limiter.limit
    rate_limiter.limit = 2
    rate_limiter.reset()
    try:
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
    finally:
        rate_limiter.limit = original_limit
        rate_limiter.reset()
