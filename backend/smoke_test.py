#!/usr/bin/env python
"""End-to-end smoke test against a running API instance."""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Tuple

import httpx

from app.security.hmac import compute_signature


API_BASE_URL = os.environ.get("SMOKE_API_BASE_URL", "http://localhost:8000/api")
SMOKE_METRICS_URL = os.environ.get("SMOKE_METRICS_URL")
SMOKE_EMAIL = os.environ.get("SMOKE_EMAIL", "smoke-tester@example.com")
SMOKE_PASSWORD = os.environ.get("SMOKE_PASSWORD", "change-me")
SMOKE_HMAC_SECRET = os.environ.get("SMOKE_HMAC_SECRET", "demo-hmac-secret")
BILLING_PLAN_FOR_CHECKOUT = os.environ.get("SMOKE_BILLING_PLAN", "pro")


class SmokeFailure(RuntimeError):
    """Raised when the smoke test detects a failure."""


def _raise_for_status(response: httpx.Response, context: str) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:  # pragma: no cover - runtime validation
        body = exc.response.text
        raise SmokeFailure(f"{context} failed: {exc.response.status_code} {body}") from exc


def _iso(dt: datetime) -> str:
    value = dt.replace(microsecond=0).isoformat()
    if value.endswith("+00:00"):
        return value[:-6] + "Z"
    return value


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


def _refresh_hmac_secret(
    client: httpx.Client,
    headers: Dict[str, str],
    store_id: str,
) -> str:
    """Rotate the HMAC secret so the smoke test always has the latest value."""

    response = client.post(
        f"{API_BASE_URL}/v1/stores/{store_id}/hmac/rotate",
        headers=headers,
        timeout=20.0,
    )
    _raise_for_status(response, "rotate HMAC secret")
    payload = response.json()
    secret = payload.get("hmac_secret")
    if not isinstance(secret, str) or len(secret) < 32:
        raise SmokeFailure("Rotate secret response missing hmac_secret")

    global SMOKE_HMAC_SECRET
    SMOKE_HMAC_SECRET = secret
    return secret


def quote_fees(
    client: httpx.Client, headers: Dict[str, str], payload: Dict[str, Any]
) -> Dict[str, Any]:
    response = client.post(
        f"{API_BASE_URL}/v1/fees/quote", json=payload, headers=headers, timeout=20.0
    )
    _raise_for_status(response, "quote")
    return response.json()


def _require_hmac_secret() -> str:
    secret = (SMOKE_HMAC_SECRET or "").strip()
    if not secret:
        raise SmokeFailure(
            "SMOKE_HMAC_SECRET must be set to validate HMAC-protected endpoints",
        )
    return secret


def _serialise_payload(payload: Dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()


def _signed_headers(
    base_headers: Dict[str, str],
    body: bytes,
    *,
    timestamp: str | None = None,
    nonce: str | None = None,
) -> Tuple[Dict[str, str], str, str]:
    secret = _require_hmac_secret()
    timestamp_value = timestamp or datetime.now(timezone.utc).isoformat()
    nonce_value = nonce or uuid.uuid4().hex
    signature = compute_signature(secret, timestamp_value, nonce_value, body)
    headers = dict(base_headers)
    headers.update(
        {
            "Content-Type": "application/json",
            "X-RDF-Timestamp": timestamp_value,
            "X-RDF-Nonce": nonce_value,
            "X-RDF-Signature": signature,
        }
    )
    return headers, timestamp_value, nonce_value


def apply_fees(
    client: httpx.Client,
    headers: Dict[str, str],
    store_id: str,
    order_id: str,
    state: str,
    *,
    return_meta: bool = False,
) -> Dict[str, Any] | Tuple[Dict[str, Any], Dict[str, Any]]:
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
    body = _serialise_payload(payload)
    signed_headers, timestamp, nonce = _signed_headers(headers, body)
    response = client.post(
        f"{API_BASE_URL}/v1/fees/apply",
        data=body,
        headers=signed_headers,
        timeout=20.0,
    )
    _raise_for_status(response, "apply")
    data = response.json()
    if not data.get("success"):
        raise SmokeFailure("apply response did not mark success")
    if not data.get("lines"):
        raise SmokeFailure("apply response missing fee lines")
    if return_meta:
        return data, {
            "headers": signed_headers,
            "timestamp": timestamp,
            "nonce": nonce,
            "body": body,
            "payload": payload,
        }
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
    now = datetime.now(timezone.utc)
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


def _handle_billing_unconfigured(response: httpx.Response) -> bool:
    if response.status_code != 503:
        return False

    try:
        payload = response.json()
    except ValueError:
        return False

    detail = payload.get("detail")
    if isinstance(detail, dict) and detail.get("code") == "billing_unconfigured":
        print("⚠ SKIP: Stripe billing not configured (billing_unconfigured returned).")
        return True
    return False


def run_billing_only_smoke() -> Dict[str, Any]:
    with httpx.Client() as client:
        login_payload = login(client)
        store_id = login_payload["stores"][0]["id"]
        headers = {"Authorization": f"Bearer {login_payload['token']}"}

        entitlements_response = client.get(
            f"{API_BASE_URL}/v1/billing/entitlements",
            params={"store_id": store_id},
            headers=headers,
            timeout=20.0,
        )
        if _handle_billing_unconfigured(entitlements_response):
            return {"skipped": True}
        _raise_for_status(entitlements_response, "entitlements")
        entitlements = entitlements_response.json()

        usage_response = client.get(
            f"{API_BASE_URL}/v1/billing/usage",
            params={"store_id": store_id},
            headers=headers,
            timeout=20.0,
        )
        if _handle_billing_unconfigured(usage_response):
            return {"skipped": True}
        _raise_for_status(usage_response, "usage")
        usage = usage_response.json()

        checkout_response = client.post(
            f"{API_BASE_URL}/v1/billing/create-checkout-session",
            params={"store_id": store_id},
            headers=headers,
            json={
                "plan_tier": BILLING_PLAN_FOR_CHECKOUT,
                "success_url": "https://example.com/billing/success",
                "cancel_url": "https://example.com/billing/cancel",
            },
            timeout=30.0,
        )
        if _handle_billing_unconfigured(checkout_response):
            return {"skipped": True}
        _raise_for_status(checkout_response, "create checkout session")
        checkout_payload = checkout_response.json()

        portal_response = client.post(
            f"{API_BASE_URL}/v1/billing/create-portal-session",
            params={"store_id": store_id, "return_url": "https://example.com/billing"},
            headers=headers,
            timeout=30.0,
        )
        if _handle_billing_unconfigured(portal_response):
            return {"skipped": True}
        _raise_for_status(portal_response, "create portal session")
        portal_payload = portal_response.json()

    print("Billing smoke completed successfully.")
    print(f"Plan: {entitlements['plan']} status={entitlements['status']}")
    print(
        "Usage: "
        f"{usage['transactions_used']}/"
        f"{usage.get('transactions_limit') or 'unlimited'} transactions"
    )
    print(f"Checkout session id: {checkout_payload.get('session_id')}")
    print(f"Portal URL prefix: {portal_payload.get('portal_url', '')[:32]}")

    return {
        "entitlements": entitlements,
        "usage": usage,
        "checkout": checkout_payload,
        "portal": portal_payload,
    }


def run_full_smoke() -> Dict[str, Any]:
    with httpx.Client() as client:
        login_payload = login(client)
        store_id = login_payload["stores"][0]["id"]
        headers = {"Authorization": f"Bearer {login_payload['token']}"}

        _refresh_hmac_secret(client, headers, store_id)

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


def run_security_only_smoke() -> Dict[str, Any]:
    with httpx.Client() as client:
        global SMOKE_HMAC_SECRET
        login_payload = login(client)
        store_id = login_payload["stores"][0]["id"]
        headers = {"Authorization": f"Bearer {login_payload['token']}"}

        _refresh_hmac_secret(client, headers, store_id)

        base_order_id = "smoke-security-order"
        payload = {
            "store_id": store_id,
            "order_id": base_order_id,
            "destination": {"state": "CO"},
            "delivery_method": "ship",
            "items": [
                {
                    "sku": "SMOKE-CO-1",
                    "qty": 1,
                    "unit_price_cents": 15000,
                    "taxability": "taxable",
                }
            ],
            "shipping_amount_cents": 750,
        }
        body = _serialise_payload(payload)
        signed_headers, timestamp, nonce = _signed_headers(headers, body)
        response = client.post(
            f"{API_BASE_URL}/v1/fees/apply",
            data=body,
            headers=signed_headers,
            timeout=20.0,
        )
        _raise_for_status(response, "apply")
        apply_result = response.json()
        if not apply_result.get("success") or not apply_result.get("lines"):
            raise SmokeFailure("apply response missing expected content")
        meta = {
            "headers": signed_headers,
            "body": body,
            "timestamp": timestamp,
            "nonce": nonce,
        }


        replay_headers, _, _ = _signed_headers(
            headers,
            meta["body"],
            timestamp=meta["timestamp"],
            nonce=meta["nonce"],
        )

        replay_response = client.post(
            f"{API_BASE_URL}/v1/fees/apply",
            data=meta["body"],
            headers=replay_headers,
            timeout=20.0,
        )
        if replay_response.status_code not in (200, 409):
            raise SmokeFailure(
                "Expected idempotent replay handling, got "
                f"{replay_response.status_code}: {replay_response.text}"
            )
        if replay_response.status_code == 200:
            replay_payload = replay_response.json()
            if not replay_payload.get("lines"):
                raise SmokeFailure(
                    "Replay returned 200 but missing lines: "
                    f"{replay_response.text}"
                )
        else:
            replay_payload = replay_response.json()
            if replay_payload.get("detail", {}).get("code") != "replay_detected":
                raise SmokeFailure(
                    "Replay 409 missing expected code: "
                    f"{replay_response.text}"
                )

        stale_headers, _, _ = _signed_headers(
            headers,
            meta["body"],
            timestamp=(datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat(),
            nonce=uuid.uuid4().hex,
        )
        stale_response = client.post(
            f"{API_BASE_URL}/v1/fees/apply",
            data=meta["body"],
            headers=stale_headers,
            timeout=20.0,
        )
        if stale_response.status_code != 401:
            raise SmokeFailure(
                "Expected 401 for stale timestamp, got "
                f"{stale_response.status_code}: {stale_response.text}"
            )

        throttle_payload = {
            "store_id": store_id,
            "destination": {"state": "CO"},
            "delivery_method": "ship",
            "items": [
                {"sku": "RATE-LIMIT", "qty": 1, "unit_price_cents": 1000, "taxability": "taxable"}
            ],
            "shipping_amount_cents": 0,
        }

        throttle_detail: Dict[str, Any] | None = None
        for attempt in range(1, 181):
            quote_response = client.post(
                f"{API_BASE_URL}/v1/fees/quote",
                json=throttle_payload,
                headers=headers,
                timeout=20.0,
            )
            if quote_response.status_code == 429:
                throttle_detail = quote_response.json()
                break
            if quote_response.status_code != 200:
                raise SmokeFailure(
                    "Unexpected status during throttle probe: "
                    f"{quote_response.status_code} {quote_response.text}"
                )

        if not throttle_detail:
            raise SmokeFailure("Unable to trigger rate limit within 180 attempts")
        detail_payload = throttle_detail.get("detail", {}) if isinstance(throttle_detail, dict) else {}
        route_value = throttle_detail.get("route") or detail_payload.get("route")
        if route_value != "quote":
            raise SmokeFailure(f"Throttle detail missing route: {throttle_detail}")

        rotate_response = client.post(
            f"{API_BASE_URL}/v1/stores/{store_id}/hmac/rotate",
            headers=headers,
            timeout=20.0,
        )
        _raise_for_status(rotate_response, "rotate HMAC secret")
        rotation_payload = rotate_response.json()
        new_secret = rotation_payload.get("hmac_secret")
        if not isinstance(new_secret, str) or len(new_secret) < 32:
            raise SmokeFailure("Rotate secret response missing hmac_secret")

        new_timestamp = datetime.now(timezone.utc).isoformat()
        new_nonce = uuid.uuid4().hex
        old_signature = compute_signature(
            _require_hmac_secret(),
            new_timestamp,
            new_nonce,
            meta["body"],
        )
        invalid_headers = dict(headers)
        invalid_headers.update(
            {
                "Content-Type": "application/json",
                "X-RDF-Timestamp": new_timestamp,
                "X-RDF-Nonce": new_nonce,
                "X-RDF-Signature": old_signature,
            }
        )
        invalid_after_rotation = client.post(
            f"{API_BASE_URL}/v1/fees/apply",
            data=meta["body"],
            headers=invalid_headers,
            timeout=20.0,
        )
        if invalid_after_rotation.status_code != 403:
            raise SmokeFailure(
                "Old secret should fail after rotation, got "
                f"{invalid_after_rotation.status_code}: {invalid_after_rotation.text}"
            )
        detail_body = invalid_after_rotation.json().get("detail", {})
        if detail_body.get("code") != "invalid_signature":
            raise SmokeFailure(
                f"Expected invalid_signature after rotation, received {detail_body}"
            )

        SMOKE_HMAC_SECRET = new_secret

        rotated_apply = apply_fees(
            client,
            headers,
            store_id,
            f"{base_order_id}-rotated",
            "CO",
        )

        metrics_snapshot = fetch_metrics(client)

        def _require_counter(metric: str, required_labels: dict[str, str]) -> float:
            for raw in metrics_snapshot.splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or not line.startswith(metric):
                    continue
                try:
                    left, value_str = line.rsplit(" ", 1)
                    value = float(value_str)
                except ValueError:  # pragma: no cover - defensive branch
                    continue

                if "{" in left and "}" in left:
                    labels_str = left[left.find("{") + 1 : left.rfind("}")]
                    observed: dict[str, str] = {}
                    for pair in labels_str.split(","):
                        if "=" not in pair:
                            continue
                        key, raw_val = pair.split("=", 1)
                        observed[key.strip()] = raw_val.strip().strip('"')
                    matches = all(observed.get(k) == v for k, v in required_labels.items())
                else:
                    matches = not required_labels

                if matches:
                    return value

            want = ",".join(f'{k}="{v}"' for k, v in required_labels.items())
            raise SmokeFailure(
                f"Metrics missing {metric} with labels {{{want}}}:\n{metrics_snapshot}"
            )

        stale_counter = _require_counter(
            "hmac_validation_failures_total",
            {"reason": "stale_timestamp", "store_id": store_id},
        )
        replay_counter = _require_counter(
            "hmac_replay_attempts_total",
            {"store_id": store_id},
        )
        throttle_counter = _require_counter(
            "rate_limit_throttles_total",
            {"route": "quote"},
        )

        if stale_counter <= 0:
            raise SmokeFailure("Stale timestamp counter did not increment")
        if replay_counter <= 0:
            raise SmokeFailure("Replay counter did not increment")
        if throttle_counter <= 0:
            raise SmokeFailure("Rate limit counter did not increment")

    print("Security smoke completed successfully.")
    print(f"Initial apply lines: {len(apply_result['lines'])}")
    print("Replay attempt rejected with 409.")
    print("Stale timestamp rejected with 401.")
    print("Rate limiter throttled quote traffic as expected.")
    print("HMAC secret rotation generated a new secret and invalidated the previous one.")
    print(
        "Metrics confirmed: "
        f"hmac_validation_failures_total(stale_timestamp)={stale_counter}, "
        f"hmac_replay_attempts_total={replay_counter}, "
        f"rate_limit_throttles_total={throttle_counter}"
    )

    return {
        "apply": apply_result,
        "replay_status": replay_response.status_code,
        "stale_status": stale_response.status_code,
        "throttle_detail": throttle_detail,
        "rotated_apply": rotated_apply,
        "rotation_payload": rotation_payload,
        "metrics": metrics_snapshot,
        "stale_counter": stale_counter,
        "replay_counter": replay_counter,
        "throttle_counter": throttle_counter,
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
    parser.add_argument(
        "--security-only",
        action="store_true",
        help="Only execute HMAC validation smoke checks",
    )
    parser.add_argument(
        "--billing-only",
        action="store_true",
        help="Only execute billing subscription validation",
    )
    parsed_args = parser.parse_args()

    try:
        selected = [
            flag
            for flag in (
                parsed_args.analytics_only,
                parsed_args.reports_only,
                parsed_args.security_only,
                parsed_args.billing_only,
            )
            if flag
        ]
        if len(selected) > 1:
            raise SmokeFailure("Choose at most one focused smoke option")
        if parsed_args.analytics_only:
            run_analytics_only_smoke()
        elif parsed_args.security_only:
            run_security_only_smoke()
        elif parsed_args.reports_only:
            run_reports_only_smoke()
        elif parsed_args.billing_only:
            run_billing_only_smoke()
        else:
            run_full_smoke()
    except SmokeFailure as exc:
        print(f"SMOKE FAILURE: {exc}", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPError as exc:
        print(f"HTTP error during smoke test: {exc}", file=sys.stderr)
        sys.exit(1)
