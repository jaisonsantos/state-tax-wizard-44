from __future__ import annotations

from datetime import date, timedelta
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import AuditLog
from app.observability import report_exports_total

LOGIN_PAYLOAD = {"email": "reports@example.com", "password": "secret"}


def authenticate(client: TestClient) -> tuple[str, str]:
    response = client.post("/api/auth/login", json=LOGIN_PAYLOAD)
    assert response.status_code == 200
    data = response.json()
    return data["token"], data["stores"][0]["id"]


def _date_range() -> tuple[str, str]:
    today = date.today()
    return today.isoformat(), (today + timedelta(days=1)).isoformat()


def test_report_exports_emit_audit_and_metrics(client: TestClient, db_session: Session) -> None:
    token, store_id = authenticate(client)
    headers = {"Authorization": f"Bearer {token}"}

    start, end = _date_range()

    counter = report_exports_total.labels(jurisdiction="CO", format="csv")
    before = counter._value.get()

    response = client.get(
        "/api/v1/reports/co/dr1786",
        params={"store_id": store_id, "from_date": start, "to_date": end},
        headers=headers,
    )
    assert response.status_code == 200

    after = counter._value.get()
    assert after == before + 1

    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "report_export")
        .order_by(AuditLog.ts.desc())
        .first()
    )
    assert audit is not None
    assert audit.actor == f"user:{LOGIN_PAYLOAD['email']}"
    assert audit.payload["report"] == "co_dr1786"
    assert audit.payload["format"] == "csv"
    assert audit.payload["outcome"] == "success"
    assert audit.payload["mime_type"] == "text/csv"


def test_mn_report_rejects_invalid_format(client: TestClient, db_session: Session) -> None:
    token, store_id = authenticate(client)
    headers = {"Authorization": f"Bearer {token}"}

    start, end = _date_range()

    response = client.get(
        "/api/v1/reports/mn/summary",
        params={
            "store_id": store_id,
            "from_date": start,
            "to_date": end,
            "format": "xlsx",
        },
        headers=headers,
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["detail"][0]["msg"].startswith("Unsupported format")

    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "report_export")
        .order_by(AuditLog.ts.desc())
        .first()
    )
    assert audit is not None
    assert audit.payload["store_id"] == store_id
    assert audit.payload["format"] == "xlsx"
    assert audit.payload["outcome"] == "failure"
    assert audit.payload["mime_type"] == "application/octet-stream"
    assert audit.payload["row_count"] == 0
    assert audit.payload["error"].startswith("Unsupported format")


def test_audit_endpoint_filters_report_exports(client: TestClient) -> None:
    token, store_id = authenticate(client)
    headers = {"Authorization": f"Bearer {token}"}

    start, end = _date_range()

    # Generate both CSV and JSON exports
    response_csv = client.get(
        "/api/v1/reports/mn/summary",
        params={
            "store_id": store_id,
            "from_date": start,
            "to_date": end,
            "format": "csv",
        },
        headers=headers,
    )
    assert response_csv.status_code == 200

    response_json = client.get(
        "/api/v1/reports/mn/summary",
        params={
            "store_id": store_id,
            "from_date": start,
            "to_date": end,
            "format": "json",
        },
        headers=headers,
    )
    assert response_json.status_code == 200
    assert "attachment" in response_json.headers["content-disposition"].lower()
    assert response_json.headers["content-disposition"].endswith(".json")

    response = client.get(
        "/api/v1/audit",
        params={
            "store_id": store_id,
            "limit": 10,
            "action": "report_export",
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    assert all(item["action"] == "report_export" for item in data["items"])
    assert {item["payload"]["format"] for item in data["items"]} >= {"csv", "json"}


def test_audit_endpoint_excludes_other_store_logs(
    client: TestClient, db_session: Session
) -> None:
    token, store_id = authenticate(client)
    headers = {"Authorization": f"Bearer {token}"}

    start, end = _date_range()

    # Generate one export for the authenticated store
    response = client.get(
        "/api/v1/reports/mn/summary",
        params={
            "store_id": store_id,
            "from_date": start,
            "to_date": end,
            "format": "csv",
        },
        headers=headers,
    )
    assert response.status_code == 200

    # Insert an audit record for a different store to ensure it is ignored
    other_store_id = str(uuid.uuid4())
    db_session.add(
        AuditLog(
            actor="user:other@example.com",
            action="report_export",
            payload={
                "store_id": other_store_id,
                "report": "mn_summary",
                "format": "csv",
                "outcome": "success",
            },
        )
    )
    db_session.commit()

    response = client.get(
        "/api/v1/audit",
        params={
            "store_id": store_id,
            "limit": 10,
            "action": "report_export",
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["payload"]["store_id"] == store_id
