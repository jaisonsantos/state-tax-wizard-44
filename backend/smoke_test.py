#!/usr/bin/env python
"""End-to-end smoke test against a running API instance."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict

import httpx


API_BASE_URL = os.environ.get("SMOKE_API_BASE_URL", "http://localhost:8000/api")
SMOKE_EMAIL = os.environ.get("SMOKE_EMAIL", "smoke-tester@example.com")
SMOKE_PASSWORD = os.environ.get("SMOKE_PASSWORD", "change-me")


class SmokeFailure(RuntimeError):
    """Raised when the smoke test detects a failure."""


def _raise_for_status(response: httpx.Response, context: str) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:  # pragma: no cover - runtime validation
        body = exc.response.text
        raise SmokeFailure(f"{context} failed: {exc.response.status_code} {body}") from exc


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat() + "Z"


def login(client: httpx.Client) -> Dict[str, Any]:
    response = client.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": SMOKE_EMAIL, "password": SMOKE_PASSWORD},
        timeout=20.0,
    )
    _raise_for_status(response, "login")
    data = response.json()
    if not data.get("token"):
        raise SmokeFailure("login succeeded but token missing")
    if not data.get("stores"):
        raise SmokeFailure("login succeeded but no stores returned")
    return data


def quote_fees(client: httpx.Client, headers: Dict[str, str], store_id: str) -> Dict[str, Any]:
    payload = {
        "store_id": store_id,
        "destination": {"state": "MN"},
        "delivery_method": "ship",
        "items": [
            {"sku": "SMOKE-MN-1", "qty": 1, "unit_price_cents": 12500, "taxability": "taxable"}
        ],
        "shipping_amount_cents": 500,
    }
    response = client.post(f"{API_BASE_URL}/v1/fees/quote", json=payload, headers=headers, timeout=20.0)
    _raise_for_status(response, "quote")
    data = response.json()
    if not data.get("lines"):
        raise SmokeFailure("quote returned no fee lines")
    return data


def apply_fees(
    client: httpx.Client,
    headers: Dict[str, str],
    store_id: str,
    order_id: str,
    state: str,
) -> Dict[str, Any]:
    payload = {
        "store_id": store_id,
        "order_id": order_id,
        "destination": {"state": state},
        "delivery_method": "ship",
        "items": [
            {"sku": f"SMOKE-{state}-1", "qty": 1, "unit_price_cents": 15000, "taxability": "taxable"}
        ],
        "shipping_amount_cents": 750,
    }
    response = client.post(
        f"{API_BASE_URL}/v1/fees/apply",
        json=payload,
        headers=headers,
        timeout=20.0,
    )
    _raise_for_status(response, "apply")
    data = response.json()
    if not data.get("success"):
        raise SmokeFailure("apply response did not mark success")
    if not data.get("lines"):
        raise SmokeFailure("apply response missing fee lines")
    return data


def fetch_audit(client: httpx.Client, headers: Dict[str, str], store_id: str) -> Dict[str, Any]:
    response = client.get(
        f"{API_BASE_URL}/v1/audit",
        params={"store_id": store_id, "limit": 5},
        headers=headers,
        timeout=20.0,
    )
    _raise_for_status(response, "audit fetch")
    data = response.json()
    if not data.get("items"):
        raise SmokeFailure("audit endpoint returned no items")
    return data


def fetch_reports(client: httpx.Client, headers: Dict[str, str], store_id: str) -> None:
    now = datetime.utcnow()
    from_date = _iso(now - timedelta(days=1))
    to_date = _iso(now + timedelta(days=1))

    # MN summary in JSON for easier validation
    response = client.get(
        f"{API_BASE_URL}/v1/reports/mn/summary",
        params={"store_id": store_id, "from_date": from_date, "to_date": to_date, "format": "json"},
        headers=headers,
        timeout=30.0,
    )
    _raise_for_status(response, "mn report")
    summary = response.json()
    if "fee_total_cents" not in summary:
        raise SmokeFailure("mn summary missing totals")

    # Colorado DR-1786 CSV
    response = client.get(
        f"{API_BASE_URL}/v1/reports/co/dr1786",
        params={"store_id": store_id, "from_date": from_date, "to_date": to_date},
        headers=headers,
        timeout=30.0,
    )
    _raise_for_status(response, "co report")
    if "Transaction Date" not in response.text:
        raise SmokeFailure("co report missing CSV header")


def main() -> None:
    with httpx.Client() as client:
        login_payload = login(client)
        store_id = login_payload["stores"][0]["id"]
        headers = {"Authorization": f"Bearer {login_payload['token']}"}

        quote_result = quote_fees(client, headers, store_id)
        apply_mn = apply_fees(client, headers, store_id, "smoke-order-mn", "MN")
        apply_co = apply_fees(client, headers, store_id, "smoke-order-co", "CO")
        audit_result = fetch_audit(client, headers, store_id)
        fetch_reports(client, headers, store_id)

    print("Smoke test completed successfully.")
    print(f"MN quote lines: {len(quote_result['lines'])}")
    print(f"MN apply lines: {len(apply_mn['lines'])}")
    print(f"CO apply lines: {len(apply_co['lines'])}")
    print(f"Audit events fetched: {len(audit_result['items'])}")


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    try:
        main()
    except SmokeFailure as exc:
        print(f"SMOKE FAILURE: {exc}", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPError as exc:
        print(f"HTTP error during smoke test: {exc}", file=sys.stderr)
        sys.exit(1)
