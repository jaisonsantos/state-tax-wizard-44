from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import AuditLog, OrderFee, RuleVersion, Store, User
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


def test_fee_apply_idempotent(client: TestClient, db_session: Session):
    login = client.post(
        "/api/auth/login",
        json={"email": "apply@example.com", "password": "secret"},
    ).json()
    store_id = login["stores"][0]["id"]

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

    first = client.post("/api/v1/fees/apply", json=payload)
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["success"] is True
    assert first_body["lines"]
    assert first_body["lines"][0]["jurisdiction"] == "MN"

    order_fee_count = db_session.query(OrderFee).count()
    audit_count = db_session.query(AuditLog).count()
    assert order_fee_count == len(first_body["lines"])
    assert audit_count == 1

    second = client.post("/api/v1/fees/apply", json=payload)
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["success"] is True
    assert len(second_body["lines"]) == len(first_body["lines"])
    for returned, initial in zip(second_body["lines"], first_body["lines"]):
        assert returned["jurisdiction"] == initial["jurisdiction"]
        assert returned["amount_cents"] == initial["amount_cents"]
        assert returned["rule_version"] == initial["rule_version"]
        assert returned["reason_codes"] == initial["reason_codes"]
    assert db_session.query(OrderFee).count() == order_fee_count
    assert db_session.query(AuditLog).count() == audit_count


def test_seed_script_creates_store_and_rules(db_session: Session):
    seed_database()

    stores = db_session.query(Store).count()
    mn_rules = db_session.query(RuleVersion).filter(RuleVersion.jurisdiction == "MN").count()
    co_rules = db_session.query(RuleVersion).filter(RuleVersion.jurisdiction == "CO").count()

    assert stores >= 1
    assert mn_rules >= 1
    assert co_rules >= 1
