from __future__ import annotations

from typing import Tuple

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import config
from app.models.models import Store


def _login(client: TestClient) -> Tuple[str, list[dict[str, str]]]:
    response = client.post(
        "/api/auth/login",
        json={"email": "integrations@example.com", "password": "secret"},
    )
    response.raise_for_status()
    payload = response.json()
    return payload["token"], payload["stores"]


def test_status_reflects_feature_flags(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    token, stores = _login(client)
    store_id = stores[0]["id"]

    monkeypatch.setattr(config.settings, "integrations_shopify_enabled", True, raising=False)
    monkeypatch.setattr(config.settings, "integrations_woo_enabled", False, raising=False)

    response = client.get(
        "/api/v1/integrations/status",
        params={"store_id": store_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    statuses = {item["provider"]: item for item in payload["providers"]}
    assert statuses["shopify"]["enabled"] is True
    assert statuses["shopify"]["status"] in {"connected", "disconnected"}
    assert statuses["woocommerce"]["enabled"] is False
    assert statuses["woocommerce"]["status"] == "disabled"


def test_install_requires_feature_flag(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    token, stores = _login(client)
    store_id = stores[0]["id"]

    monkeypatch.setattr(config.settings, "integrations_shopify_enabled", False, raising=False)

    response = client.post(
        "/api/v1/integrations/providers/shopify/install",
        params={"store_id": store_id},
        json={"store_domain": "example-store.myshopify.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "integration_disabled"


def test_install_updates_store_platform(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    token, stores = _login(client)
    # Prefer the second store if available to avoid clobbering the default Shopify demo
    target_store_id = stores[-1]["id"] if len(stores) > 1 else stores[0]["id"]

    monkeypatch.setattr(config.settings, "integrations_woo_enabled", True, raising=False)

    response = client.post(
        "/api/v1/integrations/providers/woocommerce/install",
        params={"store_id": target_store_id},
        json={
            "store_domain": "demo-woo-store.example.com",
            "external_shop_id": "woo-123",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["connected"] is True
    assert payload["status"] == "connected"

    store = db_session.query(Store).filter(Store.id == target_store_id).one()
    assert store.platform == "woo"
    assert store.domain == "demo-woo-store.example.com"

