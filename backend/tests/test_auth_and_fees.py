from datetime import datetime, timedelta
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.models import (
    AuditLog,
    OrderFee,
    RuleVersion,
    SessionToken,
    Store,
    StoreSetting,
    User,
)
from app.observability import auth_events_total
from seed_data import seed_database


def test_login_creates_user_and_seed_store(client: TestClient, db_session: Session):
    response = client.post(
        "/api/auth/login",
        json={"email": "new-user@example.com", "password": "secret"},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["user"]["email"] == "new-user@example.com"
    assert len(payload["stores"]) >= 1

    user = db_session.query(User).filter(User.email == "new-user@example.com").first()
    assert user is not None

    sessions = (
        db_session.query(SessionToken)
        .join(User)
        .filter(User.email == "new-user@example.com")
        .all()
    )
    assert len(sessions) == 1
    assert sessions[0].revoked_at is None

    seed_store = db_session.query(Store).filter(Store.name == "store_demo_1").first()
    assert seed_store is not None
    assert seed_store in user.stores


def test_me_returns_user_profile(client: TestClient):
    login = client.post(
        "/api/auth/login",
        json={"email": "profile@example.com", "password": "secret"},
    ).json()

    token = login["token"]
    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

    data = response.json()
    assert data["user"]["email"] == "profile@example.com"
    assert isinstance(data["stores"], list)
    assert len(data["stores"]) >= 1
    assert "session" in data
    if data["session"]:
        assert data["session"]["store_scope"]


def _create_rule_versions(db_session: Session):
    db_session.add(
        RuleVersion(
            jurisdiction="MN",
            version="MN-test",
            effective_from=datetime.utcnow() - timedelta(days=1),
            effective_to=None,
            params={"threshold_cents": 10000, "fee_cents": 50},
        )
    )
    db_session.add(
        RuleVersion(
            jurisdiction="CO",
            version="CO-test",
            effective_from=datetime.utcnow() - timedelta(days=1),
            effective_to=None,
            params={"rate_cents": 28},
        )
    )
    db_session.commit()


def _login_and_get_store(client: TestClient):
    login = client.post(
        "/api/auth/login",
        json={"email": f"store-user-{uuid.uuid4()}@example.com", "password": "secret"},
    ).json()
    return login["token"], login["stores"][0]["id"]


def test_logout_revokes_session_and_metrics(client: TestClient, db_session: Session) -> None:
    login_metric = auth_events_total.labels(event="login")
    logout_metric = auth_events_total.labels(event="logout")
    login_before = login_metric._value.get()
    logout_before = logout_metric._value.get()

    payload = client.post(
        "/api/auth/login",
        json={"email": "logout@example.com", "password": "secret"},
    ).json()

    token = payload["token"]
    email = payload["user"]["email"]

    session = (
        db_session.query(SessionToken)
        .join(User)
        .filter(User.email == email)
        .one()
    )
    assert session.revoked_at is None

    logout_response = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_response.status_code == 204

    db_session.refresh(session)
    assert session.revoked_at is not None
    assert session.revoked_reason == "user_logout"

    unauthorized = client.get(
        "/api/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert unauthorized.status_code == 401

    assert login_metric._value.get() == login_before + 1
    assert logout_metric._value.get() == logout_before + 1


def test_fee_apply_idempotent(client: TestClient, db_session: Session):
    token, store_id = _login_and_get_store(client)
    auth_header = {"Authorization": f"Bearer {token}"}

    _create_rule_versions(db_session)

    payload = {
        "store_id": store_id,
        "order_id": "order-123",
        "destination": {"state": "MN"},
        "delivery_method": "ship",
        "items": [
            {"sku": "SKU-1", "qty": 1, "unit_price_cents": 12000, "taxability": "taxable"}
        ],
        "shipping_amount_cents": 500,
    }

    first = client.post("/api/v1/fees/apply", json=payload, headers=auth_header)
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["success"] is True
    assert first_body["lines"]
    assert first_body["lines"][0]["jurisdiction"] == "MN"
    assert first_body["absorbed"] is False
    assert any(decision["outcome"] == "applied" for decision in first_body["decisions"])

    order_fee_count = db_session.query(OrderFee).count()
    audit_count = db_session.query(AuditLog).count()
    assert order_fee_count == len(first_body["lines"])
    assert audit_count == 1

    second = client.post("/api/v1/fees/apply", json=payload, headers=auth_header)
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["success"] is True
    assert len(second_body["lines"]) == len(first_body["lines"])
    assert second_body["decisions"] == first_body["decisions"]
    assert db_session.query(OrderFee).count() == order_fee_count
    assert db_session.query(AuditLog).count() == audit_count


def test_quote_reflects_store_settings_and_absorb(client: TestClient, db_session: Session):
    token, store_id = _login_and_get_store(client)
    _create_rule_versions(db_session)

    setting = db_session.query(StoreSetting).filter(StoreSetting.store_id == store_id).first()
    setting.absorb_fee = True
    setting.enable_co = False
    db_session.add(setting)
    db_session.commit()

    payload = {
        "store_id": store_id,
        "destination": {"state": "MN"},
        "delivery_method": "ship",
        "items": [
            {"sku": "SKU-apply", "qty": 1, "unit_price_cents": 12000, "taxability": "taxable"}
        ],
        "shipping_amount_cents": 0,
    }

    response = client.post(
        "/api/v1/fees/quote",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["absorbed"] is True
    assert all(line["absorbed"] is True for line in body["lines"])
    mn_decision = next(d for d in body["decisions"] if d["jurisdiction"] == "MN")
    assert mn_decision["outcome"] == "applied"
    co_decision = next(d for d in body["decisions"] if d["jurisdiction"] == "CO")
    assert "CO_DISABLED" in co_decision["reason_codes"]


def test_quote_reason_codes_for_exemptions(client: TestClient, db_session: Session):
    token, store_id = _login_and_get_store(client)
    _create_rule_versions(db_session)

    payload = {
        "store_id": store_id,
        "destination": {"state": "MN"},
        "delivery_method": "ship",
        "items": [
            {"sku": "SKU-small", "qty": 1, "unit_price_cents": 1000, "taxability": "taxable"}
        ],
        "shipping_amount_cents": 0,
    }

    response = client.post(
        "/api/v1/fees/quote",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    mn_decision = next(d for d in body["decisions"] if d["jurisdiction"] == "MN")
    assert mn_decision["outcome"] == "skipped"
    assert "MN_UNDER_THRESHOLD" in mn_decision["reason_codes"]


def test_expired_token_rejected(client: TestClient, db_session: Session):
    _, store_id = _login_and_get_store(client)
    _create_rule_versions(db_session)

    expired_token = create_access_token(
        email="expired@example.com",
        stores=[store_id],
        expires_delta=timedelta(seconds=-1),
    )

    payload = {
        "store_id": store_id,
        "destination": {"state": "MN"},
        "delivery_method": "ship",
        "items": [
            {"sku": "SKU-expired", "qty": 1, "unit_price_cents": 12000, "taxability": "taxable"}
        ],
        "shipping_amount_cents": 0,
    }

    response = client.post(
        "/api/v1/fees/quote",
        json=payload,
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401


def test_seed_script_creates_store_and_rules(db_session: Session):
    seed_database()

    stores = db_session.query(Store).count()
    mn_rules = db_session.query(RuleVersion).filter(RuleVersion.jurisdiction == "MN").count()
    co_rules = db_session.query(RuleVersion).filter(RuleVersion.jurisdiction == "CO").count()

    assert stores >= 1
    assert mn_rules >= 1
    assert co_rules >= 1
