#!/usr/bin/env python
"""End-to-end smoke test against a running API instance."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict

import httpx


API_BASE_URL = os.environ.get("SMOKE_API_BASE_URL", "http://localhost:8000/api")
SMOKE_METRICS_URL = os.environ.get("SMOKE_METRICS_URL")
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


def update_settings(
    client: httpx.Client,
    headers: Dict[str, str],
    store_id: str,
    *,
    enable_mn: bool,
    enable_co: bool,
    absorb_fee: bool,
) -> Dict[str, Any]:
    payload = {
        "enable_mn": enable_mn,
        "enable_co": enable_co,
        "absorb_fee": absorb_fee,
        "label_override": "Delivery Fee",
    }
    response = client.put(
        f"{API_BASE_URL}/v1/stores/{store_id}/settings",
        json=payload,
        headers=headers,
        timeout=20.0,
    )
    _raise_for_status(response, "settings update")
    return response.json()


def quote_fees(
    client: httpx.Client, headers: Dict[str, str], payload: Dict[str, Any]
) -> Dict[str, Any]:
    response = client.post(
        f"{API_BASE_URL}/v1/fees/quote", json=payload, headers=headers, timeout=20.0
    )
    _raise_for_status(response, "quote")
    return response.json()


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


def fetch_audit(
    client: httpx.Client,
    headers: Dict[str, str],
    store_id: str,
    *,
    action: str | None = None,
    limit: int = 5,
) -> Dict[str, Any]:
    params = {"store_id": store_id, "limit": limit}
    if action:
        params["action"] = action

    response = client.get(
        f"{API_BASE_URL}/v1/audit",
        params=params,
        headers=headers,
        timeout=20.0,
    )
    _raise_for_status(response, "audit fetch")
    data = response.json()
    if not data.get("items"):
        raise SmokeFailure("audit endpoint returned no items")
    if action and not any(item.get("action") == action for item in data.get("items", [])):
        raise SmokeFailure(f"audit endpoint returned no '{action}' entries")
    return data


def fetch_reports(
    client: httpx.Client, headers: Dict[str, str], store_id: str, *, verify_audit: bool = False
) -> Dict[str, Any]:
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
    for key in ("tx_count_threshold_met", "fee_total_cents", "absorbed_count", "shown_count"):
        if key not in summary:
            raise SmokeFailure(f"mn summary missing {key}")

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

    audit_snapshot: Dict[str, Any] | None = None
    if verify_audit:
        audit_snapshot = fetch_audit(
            client,
            headers,
            store_id,
            action="report_export",
            limit=10,
        )

    return audit_snapshot or {}

def _metrics_url() -> str:
    if SMOKE_METRICS_URL:
        return SMOKE_METRICS_URL

    base = API_BASE_URL.rstrip("/")
    if base.endswith("/api"):
        return f"{base[:-4]}/metrics"
    return f"{base}/metrics"


def fetch_metrics(client: httpx.Client) -> str:
    response = client.get(_metrics_url(), timeout=20.0)
    _raise_for_status(response, "metrics")
    text = response.text
    if "decision_latency_ms" not in text:
        raise SmokeFailure("metrics missing decision_latency_ms")
    return text


def fetch_analytics(
    client: httpx.Client, headers: Dict[str, str], store_id: str
) -> Dict[str, Any]:
    response = client.get(
        f"{API_BASE_URL}/v1/analytics/overview",
        params={"store_id": store_id, "limit": 5},
        headers=headers,
        timeout=20.0,
    )
    _raise_for_status(response, "analytics overview")
    data = response.json()
    if not data.get("metric_cards"):
        raise SmokeFailure("analytics overview returned no metric cards")
    if "recent_decisions" not in data:
        raise SmokeFailure("analytics overview missing recent_decisions feed")
    return data


def run_full_smoke() -> Dict[str, Any]:
    with httpx.Client() as client:
        login_payload = login(client)
        store_id = login_payload["stores"][0]["id"]
        headers = {"Authorization": f"Bearer {login_payload['token']}"}

        update_settings(client, headers, store_id, enable_mn=False, enable_co=True, absorb_fee=False)

        mn_payload = {
            "store_id": store_id,
            "destination": {"state": "MN"},
            "delivery_method": "ship",
            "items": [
                {"sku": "SMOKE-MN-1", "qty": 1, "unit_price_cents": 12500, "taxability": "taxable"}
            ],
            "shipping_amount_cents": 500,
        }
        mn_quote = quote_fees(client, headers, mn_payload)
        if mn_quote.get("lines"):
            raise SmokeFailure("MN quote returned fee lines while disabled")

        update_settings(client, headers, store_id, enable_mn=True, enable_co=True, absorb_fee=True)

        co_payload = {
            "store_id": store_id,
            "destination": {"state": "CO"},
            "delivery_method": "ship",
            "items": [
                {"sku": "SMOKE-CO-1", "qty": 1, "unit_price_cents": 1000, "taxability": "taxable"}
            ],
            "shipping_amount_cents": 0,
            "source_of_remittance": "merchant",
        }
        quote_result = quote_fees(client, headers, co_payload)
        if not quote_result.get("lines"):
            raise SmokeFailure("CO quote returned no lines when enabled")
        if not all(line.get("absorbed") for line in quote_result["lines"]):
            raise SmokeFailure("CO quote lines not marked absorbed")

        apply_mn = apply_fees(client, headers, store_id, "smoke-order-mn", "MN")
        apply_co = apply_fees(client, headers, store_id, "smoke-order-co", "CO")
        audit_result = fetch_audit(client, headers, store_id)
        report_audit = fetch_reports(client, headers, store_id, verify_audit=True)
        analytics_snapshot = fetch_analytics(client, headers, store_id)
        metrics_text = fetch_metrics(client)

    print("Smoke test completed successfully.")
    print(f"MN quote lines (disabled): {len(mn_quote['lines'])}")
    print(f"MN apply lines: {len(apply_mn['lines'])}")
    print(f"CO apply lines: {len(apply_co['lines'])}")
    print(f"Audit events fetched: {len(audit_result['items'])}")
    print(f"Report export audits: {len(report_audit.get('items', []))}")
    print(
        "Analytics cards: "
        f"{', '.join(card['id'] for card in analytics_snapshot.get('metric_cards', [])[:3])}"
    )
    print(f"Metrics sample: {metrics_text.splitlines()[0]}")

    return {
        "mn_quote": mn_quote,
        "mn_apply": apply_mn,
        "co_apply": apply_co,
        "audit": audit_result,
        "report_audit": report_audit,
        "analytics": analytics_snapshot,
        "metrics": metrics_text,
    }


def run_reports_only_smoke() -> Dict[str, Any]:
    with httpx.Client() as client:
        login_payload = login(client)
        store_id = login_payload["stores"][0]["id"]
        headers = {"Authorization": f"Bearer {login_payload['token']}"}

        audit_snapshot = fetch_reports(client, headers, store_id, verify_audit=True)

    print("Report export smoke completed successfully.")
    print(f"Report export audits: {len(audit_snapshot.get('items', []))}")

    return {"report_audit": audit_snapshot}


def run_analytics_only_smoke() -> Dict[str, Any]:
    with httpx.Client() as client:
        login_payload = login(client)
        store_id = login_payload["stores"][0]["id"]
        headers = {"Authorization": f"Bearer {login_payload['token']}"}

        overview = fetch_analytics(client, headers, store_id)

    print("Analytics overview smoke completed successfully.")
    print(f"Metric cards returned: {len(overview.get('metric_cards', []))}")
    print(
        "Recent decisions fetched: "
        f"{len(overview.get('recent_decisions', {}).get('items', []))}"
    )

    return {"analytics": overview}


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    parser = argparse.ArgumentParser(description="State Tax Wizard smoke tests")
    parser.add_argument(
        "--reports-only",
        action="store_true",
        help="Only execute report export validations",
    )
    parser.add_argument(
        "--analytics-only",
        action="store_true",
        help="Only execute analytics overview validation",
    )
    parsed_args = parser.parse_args()

    try:
        if parsed_args.analytics_only and parsed_args.reports_only:
            raise SmokeFailure("Choose either --reports-only or --analytics-only")
        if parsed_args.analytics_only:
            run_analytics_only_smoke()
        elif parsed_args.reports_only:
            run_reports_only_smoke()
        else:
            run_full_smoke()
    except SmokeFailure as exc:
        print(f"SMOKE FAILURE: {exc}", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPError as exc:
        print(f"HTTP error during smoke test: {exc}", file=sys.stderr)
        sys.exit(1)
