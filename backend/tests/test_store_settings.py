import uuid

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import AuditLog, StoreSetting


def _login(client: TestClient) -> tuple[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"email": f"settings-{uuid.uuid4()}@example.com", "password": "secret"},
    )
    body = response.json()
    return body["token"], body["stores"][0]["id"]


def test_get_store_settings_returns_seed_values(client: TestClient):
    token, store_id = _login(client)

    response = client.get(
        f"/api/v1/stores/{store_id}/settings",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["store_id"] == store_id
    assert payload["enable_mn"] is True
    assert payload["enable_co"] is True
    assert payload["absorb_fee"] is False
    assert payload["label_override"] == "Delivery Fee"
    assert payload["webhook_active"] is False
    assert payload["webhook_endpoint"] is None
    assert payload["webhook_events"] == []


def test_update_store_settings_persists_and_audits(client: TestClient, db_session: Session):
    token, store_id = _login(client)

    update_payload = {
        "enable_mn": False,
        "enable_co": True,
        "absorb_fee": True,
        "label_override": "Handling Surcharge ",
        "webhook_active": True,
        "webhook_endpoint": "https://merchant.example.com/taxo-webhooks",
        "webhook_events": ["fee.applied", "report.ready", "hmac.rotated"],
    }

    response = client.put(
        f"/api/v1/stores/{store_id}/settings",
        json=update_payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["enable_mn"] is False
    assert payload["enable_co"] is True
    assert payload["absorb_fee"] is True
    assert payload["label_override"] == "Handling Surcharge"
    assert payload["webhook_active"] is True
    assert payload["webhook_endpoint"] == "https://merchant.example.com/taxo-webhooks"
    assert set(payload["webhook_events"]) == {"fee.applied", "report.ready", "hmac.rotated"}

    settings = db_session.query(StoreSetting).filter(StoreSetting.store_id == store_id).first()
    assert settings is not None
    assert settings.enable_mn is False
    assert settings.absorb_fee is True
    assert settings.label_override == "Handling Surcharge"
    assert settings.webhook_active is True
    assert settings.webhook_endpoint == "https://merchant.example.com/taxo-webhooks"
    assert set(settings.webhook_events or []) == {"fee.applied", "report.ready", "hmac.rotated"}

    audit_entry = db_session.query(AuditLog).order_by(AuditLog.ts.desc()).first()
    assert audit_entry is not None
    assert audit_entry.action == "store_settings.update"
    assert audit_entry.payload["store_id"] == store_id
