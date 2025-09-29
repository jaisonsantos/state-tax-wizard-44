from datetime import datetime, timedelta
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import RuleVersion
from app.security.rate_limit import rate_limiter


def _login(client: TestClient):
    rate_limiter.reset()
    response = client.post(
        "/api/auth/login",
        json={"email": f"rules-{uuid.uuid4()}@example.com", "password": "secret"},
    )
    payload = response.json()
    return payload["token"], payload["stores"][0]["id"]


def test_rules_endpoint_lists_versions(client: TestClient, db_session: Session) -> None:
    token, _ = _login(client)
    now = datetime.utcnow()

    db_session.add_all(
        [
            RuleVersion(
                jurisdiction="MN",
                version="MN-2023",
                effective_from=now - timedelta(days=400),
                effective_to=now - timedelta(days=200),
                params={"threshold_cents": 10000, "fee_cents": 50},
            ),
            RuleVersion(
                jurisdiction="MN",
                version="MN-2024",
                effective_from=now - timedelta(days=10),
                effective_to=None,
                params={"threshold_cents": 10000, "fee_cents": 50},
            ),
            RuleVersion(
                jurisdiction="CO",
                version="CO-2024H2",
                effective_from=now - timedelta(days=5),
                effective_to=None,
                params={"rate_cents": 28},
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        "/api/v1/rules",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    rules = payload["rules"]
    assert any(rule["version"] == "MN-2023" for rule in rules)
    latest_mn = next(rule for rule in rules if rule["version"] == "MN-2024")
    assert latest_mn["is_latest"] is True
    assert latest_mn["params"]["threshold_cents"] == 10000
