# Billing API Reference

## Overview

The Billing API manages subscription lifecycle, usage tracking, checkout/portal flows, and Stripe webhook ingestion. When Stripe credentials are not configured the API responds with `503` and `detail.code = "billing_unconfigured"`; the frontend, smoke tests, and Newman collection treat this as a skipped run.

## Endpoints

### `GET /v1/billing/entitlements`

Returns the current plan tier, feature entitlements, and Stripe metadata for a store.

| Query parameter | Type | Required | Description |
| --------------- | ---- | -------- | ----------- |
| `store_id` | UUID | ✅ | Target store identifier |

**Response `200 OK`**

```json
{
  "plan": "pro",
  "provider": "stripe",
  "status": "active",
  "trial_ends_at": null,
  "cancel_at_period_end": false,
  "current_period_start": "2025-01-01T00:00:00+00:00",
  "current_period_end": "2025-02-01T00:00:00+00:00",
  "features": [
    "basic_reports",
    "advanced_reports",
    "fee_calculation",
    "analytics_dashboard"
  ],
  "limits": {
    "transactions_per_month": 10000,
    "advanced_reports": true,
    "analytics_dashboard": true,
    "integrations": false
  }
}
```

**Error responses**

| Status | Payload |
| ------ | ------- |
| `401 Unauthorized` | Missing/invalid bearer token |
| `403 Forbidden` | Authenticated user not scoped to the store |
| `503 Service Unavailable` | `{ "detail": { "code": "billing_unconfigured", "message": "Stripe integration not configured" } }` |

---

### `GET /v1/billing/usage`

Returns usage metrics for the store's current billing period.

**Query parameters**: same as the entitlements endpoint.

**Response `200 OK`**

```json
{
  "plan": "pro",
  "status": "active",
  "transactions_used": 4523,
  "transactions_limit": 10000,
  "unlimited": false,
  "percentage_used": 45.23,
  "period_start": "2025-10-01T00:00:00+00:00",
  "period_end": "2025-11-01T00:00:00+00:00"
}
```

Errors mirror `/v1/billing/entitlements`, including graceful `503 billing_unconfigured` responses when Stripe is not configured.

---

### `POST /v1/billing/create-checkout-session`

Creates a Stripe Checkout session for subscription upgrades.

| Query parameter | Type | Required | Description |
| --------------- | ---- | -------- | ----------- |
| `store_id` | UUID | ✅ | Store initiating the upgrade |

**Request body**

```json
{
  "plan_tier": "pro",
  "success_url": "https://app.example.com/billing/success",
  "cancel_url": "https://app.example.com/billing"
}
```

**Response `200 OK`**

```json
{
  "session_id": "cs_test_a1B2c3",
  "url": "https://checkout.stripe.com/pay/cs_test_a1B2c3"
}
```

**Error responses**

- `400 Bad Request` — unsupported plan tier.
- `401/403` — auth failures, as above.
- `503 Service Unavailable` — Stripe credentials or price IDs missing.

---

### `POST /v1/billing/create-portal-session`

Opens the Stripe Customer Portal for self-service plan management.

| Query parameter | Type | Required | Description |
| --------------- | ---- | -------- | ----------- |
| `store_id` | UUID | ✅ | Store requesting the portal session |
| `return_url` | URL | ✅ | Destination after the customer exits the portal |

**Response `200 OK`**

```json
{
  "portal_url": "https://billing.stripe.com/p/session/test123",
  "portal_session_id": "ps_test_123"
}
```

**Error responses**

| Status | Payload |
| ------ | ------- |
| `400 Bad Request` | `{ "detail": { "code": "stripe_customer_missing", "message": "Stripe customer not configured for this store" } }` |
| `401/403` | Auth failures (missing or unauthorised bearer token) |
| `503 Service Unavailable` | `{ "detail": { "code": "billing_unconfigured", "message": "Stripe integration not configured" } }` |

---

### `POST /v1/billing/webhooks/stripe`

Receives Stripe billing events. The handler verifies the `Stripe-Signature` header with `STRIPE_WEBHOOK_SECRET`, persists the payload in `processed_webhooks`, and routes the event to the appropriate lifecycle handler. Idempotency is enforced per `event_id`; duplicates return `status = "duplicate"` without reprocessing.

**Headers**

| Header | Required | Description |
| --- | --- | --- |
| `stripe-signature` | ✅ | Stripe signing secret formatted as `t=<timestamp>,v1=<signature>` |

**Request body (example)**

```json
{
  "id": "evt_123",
  "type": "customer.subscription.created",
  "data": {
    "object": {
      "id": "sub_123",
      "customer": "cus_123",
      "metadata": {
        "store_id": "{{store_id}}"
      },
      "status": "active",
      "current_period_start": 1700000000,
      "current_period_end": 1700086400,
      "cancel_at_period_end": false,
      "items": {
        "data": [
          {
            "price": {"id": "{{stripe_price_id_pro}}"}
          }
        ]
      }
    }
  }
}
```

**Responses**

| Status | Payload | Scenario |
| --- | --- | --- |
| `200 OK` | `{ "status": "processed", "event_id": "evt_123", "store_id": "..." }` | Event processed successfully |
| `200 OK` | `{ "status": "duplicate", ... }` | Event was already processed (`processed_webhooks.status = processed`) |
| `200 OK` | `{ "status": "dead_letter", ... }` | Event exceeded retries and is parked in the DLQ pending replay |
| `202 Accepted` | `{ "status": "retry", ... }` | Temporary failure recorded; Stripe will retry |
| `400 Bad Request` | `Invalid payload` | Malformed JSON (`webhook_invalid_payload`) |
| `400 Bad Request` | `Invalid signature` | Signature mismatch |

The service increments `webhooks_received_total{provider="stripe",event}` for every delivery and records outcomes/latency via `webhooks_processed_total` and `webhook_processing_latency_ms`. Subscription and invoice handlers continue to update `subscriptions`, emit audit logs, and raise `billing_events_total` entries.

---

### `POST /v1/billing/webhooks/stripe/replay/{event_id}`

Replays a previously recorded Stripe event (typically one marked `dead_letter`). Requires a valid bearer token; the authenticated operator must have access to the associated store.

| Path parameter | Type | Description |
| --- | --- | --- |
| `event_id` | string | Stripe event identifier (e.g., `evt_123`) |

**Response `200 OK`**

```json
{
  "status": "processed",
  "event_id": "evt_123",
  "store_id": "4fa0b8f7-7c1a-4f35-a8a1-9fdb3f3e4a02"
}
```

**Error responses**

| Status | Payload |
| --- | --- |
| `401/403` | Missing/unauthorised bearer token |
| `404 Not Found` | `{ "detail": "Webhook event not found" }` |

Replay updates the existing `processed_webhooks` record (`status = processed`, `dead_letter = false`) and emits the same metrics/logs as a live delivery.

---

## Metrics

Billing surfaces the following Prometheus metrics:

- `billing_events_total{event}` — counts webhook and API events (checkout created, portal session, unconfigured skips, invalid signatures).
- `checkout_sessions_created_total{plan_tier}` — increments whenever a Checkout session is created successfully.
- `entitlement_denials_total{feature,plan}` — increments when plan restrictions prevent access (feature gating or transaction limits).

These appear in `/metrics` alongside existing security and fee counters and are captured in `docs/certification/EVIDENCE/metrics_dump.txt`.
