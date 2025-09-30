from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from seed_data import seed_database


def authenticate(client: TestClient) -> tuple[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"email": "analytics@example.com", "password": "secret"},
    )
    response.raise_for_status()
    payload = response.json()
    return payload["token"], payload["stores"][0]["id"]


def test_analytics_overview_returns_metrics(client: TestClient, db_session: Session) -> None:
    seed_database()

    token, store_id = authenticate(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        "/api/v1/analytics/overview",
        params={"store_id": store_id, "limit": 5},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()

    assert data["store_id"] == store_id
    assert data["metric_cards"]
    assert any(card["id"] == "fees_applied_30d" for card in data["metric_cards"])
    assert "recent_decisions" in data
    assert data["recent_decisions"]["items"]
    assert "next_cursor" in data["recent_decisions"]
    assert "counters" in data

    next_cursor = data["recent_decisions"]["next_cursor"]
    if next_cursor:
        paged = client.get(
            "/api/v1/analytics/overview",
            params={"store_id": store_id, "cursor": next_cursor, "limit": 3},
            headers=headers,
        )
        assert paged.status_code == 200
        follow = paged.json()
        assert follow["recent_decisions"]["items"]
        assert follow["recent_decisions"]["items"][0]["id"] != data["recent_decisions"]["items"][0]["id"]
