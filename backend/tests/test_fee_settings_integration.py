from datetime import datetime, timedelta, timezone
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import AuditLog, OrderFee, RuleVersion, StoreSetting
from app.security.rate_limit import rate_limiter

MN_DEFAULT_LABEL = "Road Improvement and Food Delivery Fee (MN)"
CO_DEFAULT_LABEL = "Retail Delivery Fee (CO)"


def _create_rule_versions(db_session: Session) -> None:
    db_session.add(
        RuleVersion(
            jurisdiction="MN",
            version="MN-test",
            effective_from=datetime.now(timezone.utc) - timedelta(days=1),
            effective_to=None,
            params={"threshold_cents": 10000, "fee_cents": 50},
        )
    )
    db_session.add(
        RuleVersion(
            jurisdiction="CO",
            version="CO-test",
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
        json={"email": f"fee-settings-{uuid.uuid4()}@example.com", "password": "secret"},
    )
    payload = response.json()
    return payload["token"], payload["stores"][0]["id"]


def test_disable_mn_skips_fee(client: TestClient, db_session: Session) -> None:
    token, store_id = _login(client)
    auth_header = {"Authorization": f"Bearer {token}"}
    _create_rule_versions(db_session)

    settings = (
        db_session.query(StoreSetting).filter(StoreSetting.store_id == store_id).one()
    )
    settings.enable_mn = False
    db_session.commit()

    payload = {
        "store_id": store_id,
        "destination": {"state": "MN"},
        "delivery_method": "ship",
        "items": [
            {"sku": "SKU-1", "qty": 1, "unit_price_cents": 12000, "taxability": "taxable"}
        ],
        "shipping_amount_cents": 0,
    }

    quote = client.post("/api/v1/fees/quote", json=payload, headers=auth_header)
    assert quote.status_code == 200
    quote_body = quote.json()
    assert quote_body["lines"] == []
    mn_decision = next(d for d in quote_body["decisions"] if d["jurisdiction"] == "MN")
    assert mn_decision["outcome"] == "skipped"
    assert "MN_DISABLED" in mn_decision["reason_codes"]

    apply_payload = dict(payload, order_id="order-mn-disabled")
    apply = client.post("/api/v1/fees/apply", json=apply_payload, headers=auth_header)
    assert apply.status_code == 200
    apply_body = apply.json()
    assert apply_body["lines"] == []
    assert apply_body["absorbed"] is False
    assert db_session.query(OrderFee).count() == 0


def test_disable_co_skips_fee(client: TestClient, db_session: Session) -> None:
    token, store_id = _login(client)
    auth_header = {"Authorization": f"Bearer {token}"}
    _create_rule_versions(db_session)

    settings = (
        db_session.query(StoreSetting).filter(StoreSetting.store_id == store_id).one()
    )
    settings.enable_co = False
    db_session.commit()

    payload = {
        "store_id": store_id,
        "destination": {"state": "CO"},
        "delivery_method": "ship",
        "items": [
            {"sku": "SKU-CO", "qty": 1, "unit_price_cents": 1000, "taxability": "taxable"}
        ],
        "shipping_amount_cents": 0,
    }

    quote = client.post("/api/v1/fees/quote", json=payload, headers=auth_header)
    assert quote.status_code == 200
    quote_body = quote.json()
    assert quote_body["lines"] == []
    co_decision = next(d for d in quote_body["decisions"] if d["jurisdiction"] == "CO")
    assert co_decision["outcome"] == "skipped"
    assert "CO_DISABLED" in co_decision["reason_codes"]

    apply_payload = dict(payload, order_id="order-co-disabled")
    apply = client.post("/api/v1/fees/apply", json=apply_payload, headers=auth_header)
    assert apply.status_code == 200
    apply_body = apply.json()
    assert apply_body["lines"] == []
    assert apply_body["absorbed"] is False
    assert db_session.query(OrderFee).count() == 0


def test_absorb_fee_marks_lines_and_audit(client: TestClient, db_session: Session) -> None:
    token, store_id = _login(client)
    auth_header = {"Authorization": f"Bearer {token}"}
    _create_rule_versions(db_session)

    settings = (
        db_session.query(StoreSetting).filter(StoreSetting.store_id == store_id).one()
    )
    settings.absorb_fee = True
    db_session.commit()

    payload = {
        "store_id": store_id,
        "order_id": "order-absorb",
        "destination": {"state": "MN"},
        "delivery_method": "ship",
        "items": [
            {"sku": "SKU-absorb", "qty": 1, "unit_price_cents": 12000, "taxability": "taxable"}
        ],
        "shipping_amount_cents": 0,
    }

    quote = client.post(
        "/api/v1/fees/quote",
        json={k: v for k, v in payload.items() if k != "order_id"},
        headers=auth_header,
    )
    assert quote.status_code == 200
    quote_body = quote.json()
    assert quote_body["absorbed"] is True
    assert quote_body["lines"]
    assert all(line["absorbed"] is True for line in quote_body["lines"])
    assert {line["display_name"] for line in quote_body["lines"]} == {MN_DEFAULT_LABEL}

    apply = client.post("/api/v1/fees/apply", json=payload, headers=auth_header)
    assert apply.status_code == 200
    apply_body = apply.json()
    assert apply_body["lines"]
    assert all(line["absorbed"] is True for line in apply_body["lines"])
    assert {line["display_name"] for line in apply_body["lines"]} == {MN_DEFAULT_LABEL}
    order_fee = db_session.query(OrderFee).one()
    assert order_fee.absorbed is True
    assert order_fee.display_name == MN_DEFAULT_LABEL

    audit_entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "fee_apply")
        .order_by(AuditLog.ts.desc())
        .first()
    )
    assert audit_entry is not None
    assert audit_entry.action == "fee_apply"
    assert audit_entry.payload["absorbed"] is True
    assert audit_entry.payload["lines"]
    assert all(line["absorbed"] is True for line in audit_entry.payload["lines"])
    assert all(line["display_name"] == MN_DEFAULT_LABEL for line in audit_entry.payload["lines"])


def test_reason_codes_for_threshold_and_taxability(
    client: TestClient, db_session: Session
) -> None:
    token, store_id = _login(client)
    auth_header = {"Authorization": f"Bearer {token}"}
    _create_rule_versions(db_session)

    mn_payload = {
        "store_id": store_id,
        "destination": {"state": "MN"},
        "delivery_method": "ship",
        "items": [
            {"sku": "SKU-small", "qty": 1, "unit_price_cents": 1000, "taxability": "taxable"}
        ],
        "shipping_amount_cents": 0,
    }

    mn_quote = client.post("/api/v1/fees/quote", json=mn_payload, headers=auth_header)
    assert mn_quote.status_code == 200
    mn_body = mn_quote.json()
    assert mn_body["lines"] == []
    mn_decision = next(d for d in mn_body["decisions"] if d["jurisdiction"] == "MN")
    assert mn_decision["outcome"] == "skipped"
    assert "MN_UNDER_THRESHOLD" in mn_decision["reason_codes"]
    assert "MN_TAXABLE_SUBTOTAL_UNDER_THRESHOLD" in mn_decision["reason_codes"]

    co_payload = {
        "store_id": store_id,
        "destination": {"state": "CO"},
        "delivery_method": "ship",
        "items": [
            {"sku": "SKU-exempt", "qty": 1, "unit_price_cents": 1000, "taxability": "exempt"}
        ],
        "shipping_amount_cents": 0,
    }

    co_quote = client.post("/api/v1/fees/quote", json=co_payload, headers=auth_header)
    assert co_quote.status_code == 200
    co_body = co_quote.json()
    assert co_body["lines"] == []
    co_decision = next(d for d in co_body["decisions"] if d["jurisdiction"] == "CO")
    assert co_decision["outcome"] == "skipped"
    assert "CO_NO_TAXABLE_ITEMS" in co_decision["reason_codes"]
    assert "CO_ITEMS_EXEMPT" in co_decision["reason_codes"]


def test_reason_codes_for_exempt_edge_cases(
    client: TestClient, db_session: Session
) -> None:
    token, store_id = _login(client)
    auth_header = {"Authorization": f"Bearer {token}"}
    _create_rule_versions(db_session)

    clothing_payload = {
        "store_id": store_id,
        "destination": {"state": "MN"},
        "delivery_method": "ship",
        "items": [
            {"sku": "CLOTH-1", "qty": 1, "unit_price_cents": 2000, "taxability": "clothing"}
        ],
        "shipping_amount_cents": 0,
    }
    mn_quote = client.post("/api/v1/fees/quote", json=clothing_payload, headers=auth_header)
    assert mn_quote.status_code == 200
    mn_decision = next(
        d for d in mn_quote.json()["decisions"] if d["jurisdiction"] == "MN"
    )
    assert mn_decision["outcome"] == "skipped"
    assert "MN_CLOTHING_ONLY" in mn_decision["reason_codes"]
    assert "MN_NO_TAXABLE_ITEMS" in mn_decision["reason_codes"]

    co_shipping_only = {
        "store_id": store_id,
        "destination": {"state": "CO"},
        "delivery_method": "ship",
        "items": [],
        "shipping_amount_cents": 500,
    }

    co_quote = client.post("/api/v1/fees/quote", json=co_shipping_only, headers=auth_header)
    assert co_quote.status_code == 200
    co_decision = next(
        d for d in co_quote.json()["decisions"] if d["jurisdiction"] == "CO"
    )
    assert co_decision["outcome"] == "skipped"
    assert "CO_SHIPPING_ONLY" in co_decision["reason_codes"]
    assert "CO_NO_TAXABLE_ITEMS" in co_decision["reason_codes"]


def test_default_labels_when_override_blank(
    client: TestClient, db_session: Session
) -> None:
    token, store_id = _login(client)
    auth_header = {"Authorization": f"Bearer {token}"}
    _create_rule_versions(db_session)

    settings = (
        db_session.query(StoreSetting).filter(StoreSetting.store_id == store_id).one()
    )
    settings.label_override = "   "
    db_session.commit()

    mn_payload = {
        "store_id": store_id,
        "destination": {"state": "MN"},
        "delivery_method": "ship",
        "items": [
            {"sku": "SKU", "qty": 1, "unit_price_cents": 12000, "taxability": "taxable"}
        ],
        "shipping_amount_cents": 0,
    }
    mn_quote = client.post("/api/v1/fees/quote", json=mn_payload, headers=auth_header)
    assert mn_quote.status_code == 200
    mn_body = mn_quote.json()
    assert mn_body["lines"]
    assert {line["display_name"] for line in mn_body["lines"]} == {MN_DEFAULT_LABEL}

    co_payload = {
        "store_id": store_id,
        "destination": {"state": "CO"},
        "delivery_method": "ship",
        "items": [
            {"sku": "CO", "qty": 1, "unit_price_cents": 5000, "taxability": "taxable"}
        ],
        "shipping_amount_cents": 0,
        "source_of_remittance": "merchant",
    }
    co_quote = client.post("/api/v1/fees/quote", json=co_payload, headers=auth_header)
    assert co_quote.status_code == 200
    co_body = co_quote.json()
    assert co_body["lines"]
    assert {line["display_name"] for line in co_body["lines"]} == {CO_DEFAULT_LABEL}


def test_apply_rehydrates_persisted_label(
    client: TestClient, db_session: Session
) -> None:
    token, store_id = _login(client)
    auth_header = {"Authorization": f"Bearer {token}"}
    _create_rule_versions(db_session)

    settings = (
        db_session.query(StoreSetting).filter(StoreSetting.store_id == store_id).one()
    )
    settings.label_override = "Checkout Fee"
    db_session.commit()

    payload = {
        "store_id": store_id,
        "order_id": "rehydrate-1",
        "destination": {"state": "CO"},
        "delivery_method": "ship",
        "items": [
            {"sku": "CO-1", "qty": 1, "unit_price_cents": 2000, "taxability": "taxable"}
        ],
        "shipping_amount_cents": 0,
    }

    first_apply = client.post("/api/v1/fees/apply", json=payload, headers=auth_header)
    assert first_apply.status_code == 200
    first_body = first_apply.json()
    assert first_body["lines"]
    assert {line["display_name"] for line in first_body["lines"]} == {"Checkout Fee"}

    settings.label_override = "Changed Label"
    db_session.commit()

    second_apply = client.post("/api/v1/fees/apply", json=payload, headers=auth_header)
    assert second_apply.status_code == 200
    second_body = second_apply.json()
    assert second_body["lines"]
    assert {line["display_name"] for line in second_body["lines"]} == {"Checkout Fee"}

    stored_fee = db_session.query(OrderFee).filter(OrderFee.order_id == "rehydrate-1").one()
    assert stored_fee.display_name == "Checkout Fee"


def test_co_marketplace_reason_code_and_persistence(
    client: TestClient, db_session: Session
) -> None:
    token, store_id = _login(client)
    auth_header = {"Authorization": f"Bearer {token}"}
    _create_rule_versions(db_session)

    payload = {
        "store_id": store_id,
        "order_id": "marketplace-1",
        "destination": {"state": "CO"},
        "delivery_method": "ship",
        "items": [
            {"sku": "CO-MKT", "qty": 1, "unit_price_cents": 4000, "taxability": "taxable"}
        ],
        "shipping_amount_cents": 0,
        "source_of_remittance": "marketplace",
    }

    quote = client.post(
        "/api/v1/fees/quote", json={k: v for k, v in payload.items() if k != "order_id"}, headers=auth_header
    )
    assert quote.status_code == 200
    quote_body = quote.json()
    assert quote_body["lines"]
    co_line = next(line for line in quote_body["lines"] if line["jurisdiction"] == "CO")
    assert "CO_MARKETPLACE_SOR" in co_line["reason_codes"]

    apply = client.post("/api/v1/fees/apply", json=payload, headers=auth_header)
    assert apply.status_code == 200
    apply_body = apply.json()
    co_apply_line = next(line for line in apply_body["lines"] if line["jurisdiction"] == "CO")
    assert "CO_MARKETPLACE_SOR" in co_apply_line["reason_codes"]
    assert apply_body["absorbed"] is False

    order_fee = db_session.query(OrderFee).filter(OrderFee.order_id == "marketplace-1").one()
    assert "CO_MARKETPLACE_SOR" in order_fee.reason_codes
    assert order_fee.source_of_remittance == "marketplace"

    audit_entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "fee_apply")
        .order_by(AuditLog.ts.desc())
        .first()
    )
    assert audit_entry is not None
    assert audit_entry.payload["source_of_remittance"] == "marketplace"

