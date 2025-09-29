from datetime import date, datetime, timedelta
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import RuleVersion

LOGIN_PAYLOAD = {"email": "reports@example.com", "password": "secret"}


def authenticate(client: TestClient):
    response = client.post("/api/auth/login", json=LOGIN_PAYLOAD)
    assert response.status_code == 200
    data = response.json()
    token = data["token"]
    store_id = data["stores"][0]["id"]
    return token, store_id


def ensure_mn_rule(db_session: Session):
    exists = (
        db_session.query(RuleVersion)
        .filter(RuleVersion.jurisdiction == "MN")
        .first()
        is not None
    )
    if not exists:
        db_session.add(
            RuleVersion(
                jurisdiction="MN",
                version=f"MN-test-{uuid.uuid4()}",
                effective_from=datetime.utcnow() - timedelta(days=1),
                effective_to=None,
                params={"threshold_cents": 10000, "fee_cents": 50},
            )
        )
        db_session.commit()


def test_mn_summary_json_empty_dataset(client: TestClient, db_session: Session):
    token, store_id = authenticate(client)
    ensure_mn_rule(db_session)

    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    response = client.get(
        "/api/v1/reports/mn/summary",
        params={
            "store_id": store_id,
            "from_date": today,
            "to_date": tomorrow,
            "format": "json",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["store_id"] == store_id
    assert payload["fee_total_cents"] == 0
    assert payload["tx_count_threshold_met"] == 0
    assert payload["absorbed_count"] == 0
    assert payload["shown_count"] == 0
    assert payload["period"]["from"]
    assert payload["period"]["to"]


def test_mn_summary_json_with_data(client: TestClient, db_session: Session):
    token, store_id = authenticate(client)
    ensure_mn_rule(db_session)

    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    apply_payload = {
        "store_id": store_id,
        "order_id": "order-json-1",
        "destination": {"state": "MN"},
        "delivery_method": "ship",
        "items": [
            {
                "sku": "SKU-MN",
                "qty": 1,
                "unit_price_cents": 12000,
                "taxability": "taxable",
            }
        ],
        "shipping_amount_cents": 0,
    }

    apply_response = client.post(
        "/api/v1/fees/apply",
        json=apply_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert apply_response.status_code == 200

    response = client.get(
        "/api/v1/reports/mn/summary",
        params={
            "store_id": store_id,
            "from_date": today,
            "to_date": tomorrow,
            "format": "json",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["fee_total_cents"] > 0
    assert payload["tx_count_threshold_met"] >= 1
    assert payload["shown_count"] >= 1
