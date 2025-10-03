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

Ingests Stripe webhooks. Requests are verified with `stripe.Webhook.construct_event` using `STRIPE_WEBHOOK_SECRET`.

- Successful processing always returns `200 OK` (Stripe handles retries on non-2xx responses).
- Signature failures return `400` with `detail = "Invalid signature"` and increment `billing_events_total{event="webhook_invalid_signature"}`.
- Unknown event types log `billing_events_total{event="webhook_ignored"}`.

**Supported events**

- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.paid`
- `invoice.payment_failed`

Each handler updates the `subscriptions` table, records an audit log, and keeps Prometheus counters (`billing_events_total`, `checkout_sessions_created_total`, `entitlement_denials_total`) in sync.

---

## Metrics

Billing surfaces the following Prometheus metrics:

- `billing_events_total{event}` — counts webhook and API events (checkout created, portal session, unconfigured skips, invalid signatures).
- `checkout_sessions_created_total{plan_tier}` — increments whenever a Checkout session is created successfully.
- `entitlement_denials_total{feature,plan}` — increments when plan restrictions prevent access (feature gating or transaction limits).

These appear in `/metrics` alongside existing security and fee counters and are captured in `docs/certification/EVIDENCE/metrics_dump.txt`.
