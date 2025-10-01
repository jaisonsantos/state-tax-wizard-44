from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import AuditLog, OrderFee, RuleVersion
from app.security.rate_limit import rate_limiter


def _create_rule_versions(db_session: Session) -> None:
    db_session.add(
        RuleVersion(
            jurisdiction="MN",
            version="MN-reversal",
            effective_from=datetime.now(timezone.utc) - timedelta(days=1),
            effective_to=None,
            params={"threshold_cents": 10000, "fee_cents": 50},
        )
    )
    db_session.add(
        RuleVersion(
            jurisdiction="CO",
            version="CO-reversal",
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
        json={"email": f"reverse-{uuid.uuid4()}@example.com", "password": "secret"},
    )
    payload = response.json()
    return payload["token"], payload["stores"][0]["id"]


def test_reversal_cancellation_refunds_fee(
    client: TestClient, db_session: Session
) -> None:
    token, store_id = _login(client)
    auth_header = {"Authorization": f"Bearer {token}"}
    _create_rule_versions(db_session)

    apply_payload = {
        "store_id": store_id,
        "order_id": "mn-cancel",
        "destination": {"state": "MN"},
        "delivery_method": "ship",
        "items": [
            {"sku": "MN", "qty": 1, "unit_price_cents": 20000, "taxability": "taxable"}
        ],
        "shipping_amount_cents": 0,
    }

    apply_response = client.post("/api/v1/fees/apply", json=apply_payload, headers=auth_header)
    assert apply_response.status_code == 200
    order_fee = db_session.query(OrderFee).filter(OrderFee.order_id == "mn-cancel").one()
    assert order_fee.status == "applied"

    reverse_payload = {
        "store_id": store_id,
        "order_id": "mn-cancel",
        "reason": "DELIVERY_CANCELLED",
    }
    reverse_response = client.post(
        "/api/v1/fees/reverse", json=reverse_payload, headers=auth_header
    )
    assert reverse_response.status_code == 200
    reverse_body = reverse_response.json()
    assert reverse_body["refunded_amount_cents"] == order_fee.amount_cents
    assert reverse_body["reversed_jurisdictions"] == ["MN"]

    db_session.refresh(order_fee)
    assert order_fee.status == "reversed"
    assert order_fee.reversal_reason == "DELIVERY_CANCELLED"
    assert order_fee.reversed_at is not None

    now = datetime.now(timezone.utc)
    params = {
        "store_id": store_id,
        "from_date": (now - timedelta(days=1)).isoformat(),
        "to_date": (now + timedelta(days=1)).isoformat(),
        "format": "json",
    }
    mn_report = client.get("/api/v1/reports/mn/summary", params=params, headers=auth_header)
    assert mn_report.status_code == 200
    summary = mn_report.json()
    assert summary["tx_count_threshold_met"] == 0
    assert summary["fee_total_cents"] == -order_fee.amount_cents
    assert summary["absorbed_count"] == 0
    assert summary["shown_count"] == 0

    audit_entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "fee_reverse")
        .order_by(AuditLog.ts.desc())
        .first()
    )
    assert audit_entry is not None
    assert audit_entry.payload["reason"] == "DELIVERY_CANCELLED"
    assert audit_entry.payload["refunded_amount_cents"] == order_fee.amount_cents


def test_reversal_return_logs_without_refund(
    client: TestClient, db_session: Session
) -> None:
    token, store_id = _login(client)
    auth_header = {"Authorization": f"Bearer {token}"}
    _create_rule_versions(db_session)

    apply_payload = {
        "store_id": store_id,
        "order_id": "mn-return",
        "destination": {"state": "MN"},
        "delivery_method": "ship",
        "items": [
            {"sku": "MN", "qty": 1, "unit_price_cents": 20000, "taxability": "taxable"}
        ],
        "shipping_amount_cents": 0,
    }
    client.post("/api/v1/fees/apply", json=apply_payload, headers=auth_header)

    reverse_payload = {
        "store_id": store_id,
        "order_id": "mn-return",
        "reason": "RETURN_POST_DELIVERY",
    }
    reverse_response = client.post(
        "/api/v1/fees/reverse", json=reverse_payload, headers=auth_header
    )
    assert reverse_response.status_code == 200
    reverse_body = reverse_response.json()
    assert reverse_body["refunded_amount_cents"] == 0
    assert reverse_body["reversed_jurisdictions"] == []

    order_fee = db_session.query(OrderFee).filter(OrderFee.order_id == "mn-return").one()
    assert order_fee.status == "applied"
    assert order_fee.reversal_reason == "RETURN_POST_DELIVERY"

    audit_entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "fee_reverse")
        .order_by(AuditLog.ts.desc())
        .first()
    )
    assert audit_entry is not None
    assert audit_entry.payload["reason"] == "RETURN_POST_DELIVERY"
    assert audit_entry.payload["refunded_amount_cents"] == 0
