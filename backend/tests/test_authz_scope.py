import uuid

from fastapi.testclient import TestClient


LOGIN_PAYLOAD = {"email": "authz@example.com", "password": "secret"}


def authenticate(client: TestClient):
    response = client.post("/api/auth/login", json=LOGIN_PAYLOAD)
    assert response.status_code == 200
    data = response.json()
    token = data["token"]
    store_id = data["stores"][0]["id"]
    return token, store_id


def test_fee_apply_requires_authorization(client: TestClient):
    payload = {
        "store_id": str(uuid.uuid4()),
        "order_id": "order-unauth",
        "destination": {"state": "MN"},
        "delivery_method": "ship",
        "items": [
            {
                "sku": "SKU-1",
                "qty": 1,
                "unit_price_cents": 12000,
                "taxability": "taxable",
            }
        ],
        "shipping_amount_cents": 0,
    }

    response = client.post("/api/v1/fees/apply", json=payload)
    assert response.status_code == 401


def test_audit_forbidden_for_unlinked_store(client: TestClient):
    token, store_id = authenticate(client)
    other_store_id = str(uuid.uuid4())

    response = client.get(
        "/api/v1/audit",
        params={"store_id": other_store_id, "page": 1, "limit": 10},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_fee_quote_succeeds_for_linked_store(client: TestClient):
    token, store_id = authenticate(client)

    payload = {
        "store_id": store_id,
        "destination": {"state": "MN"},
        "delivery_method": "ship",
        "items": [
            {
                "sku": "SKU-OK",
                "qty": 1,
                "unit_price_cents": 12000,
                "taxability": "taxable",
            }
        ],
        "shipping_amount_cents": 500,
    }

    response = client.post(
        "/api/v1/fees/quote",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decided"] is True
    assert isinstance(body.get("lines"), list)
