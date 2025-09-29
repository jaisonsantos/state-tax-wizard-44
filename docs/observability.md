# Observability Catalog

This document tracks the metrics, logs, and endpoints that surface system
health for the Retail Delivery Fee platform.

## Endpoints

| Endpoint | Description |
| -------- | ----------- |
| `GET /healthz` | Basic liveness probe exposed by the FastAPI service. |
| `GET /metrics` | Prometheus exposition format with the metrics listed below. |

## Prometheus metrics

All metrics are defined in `backend/app/observability.py`.

| Metric | Type | Labels | Description |
| ------ | ---- | ------ | ----------- |
| `fees_applied_total` | Counter | `jurisdiction` | Counts the number of successful fee application events per jurisdiction. Incremented for each `order_fee` row created. |
| `fees_absorbed_total` | Counter | `jurisdiction` | Tracks how often fees are marked as absorbed (hidden from the shopper) and increments whenever an absorbed line is persisted. |
| `decision_latency_ms` | Histogram | `route`, `jurisdiction`, `outcome` | Measures time spent calculating quote/apply decisions per API route (`quote` or `apply`), jurisdiction, and outcome (applied vs skipped). |

Scrape `/metrics` from the API container or <http://localhost:8000/metrics> when
running locally.

## Structured application logs

Structured logs are emitted via `observability.log_fee_event` as JSON messages to
the `fee` logger. Each invocation includes contextual fields useful for tracing
user behavior. Both fee application and reversal flows publish events through
this helper so downstream systems can reconcile adjustments.

### Schema

| Field | Example | Notes |
| ----- | ------- | ----- |
| `event` | `"fee_apply"` | Event type (`fee_apply` or `fee_reverse`). |
| `request_id` | `"5bf08d4d-a121-4b47-a81b-6cde5b0c33af"` | Propagated from `X-Request-ID` header if provided; otherwise generated per request. |
| `store_id` | `"1cc66e24-4e93-4c9e-bebd-8ff9690e33cd"` | UUID of the merchant store associated with the fee. |
| `order_id` | `"smoke-order-mn"` | Checkout order identifier supplied by the client. |
| `jurisdiction` | `"MN"` | Taxing jurisdiction for the applied fee. |
| `amount_cents` | `50` | Fee amount stored in cents. |
| `reason_codes` | `["MN_THRESHOLD_MET"]` | Decision codes associated with the fee line. |
| `delivery_method` | `"ship"` | Delivery method from the request payload. |
| `subject` | `"ops@example.com"` | Authenticated user (JWT subject) performing the action. |
| `absorbed` | `false` | Indicates whether the fee is hidden from the shopper. |
| `status` | `"reversed"` | Present on reversal events to capture the persisted order fee status. |
| `reversal_reason` | `"DELIVERY_CANCELLED"` | Present on reversal events describing why the refund occurred. |

### Sample payloads

```json
{
  "event": "fee_apply",
  "request_id": "a2c6467f-6c3d-4dc2-95da-f5b46f5b46cd",
  "store_id": "1cc66e24-4e93-4c9e-bebd-8ff9690e33cd",
  "order_id": "demo-123",
  "jurisdiction": "MN",
  "amount_cents": 50,
  "reason_codes": ["MN_THRESHOLD_MET"],
  "delivery_method": "ship",
  "subject": "ops@example.com",
  "absorbed": false
}
```

```json
{
  "event": "fee_reverse",
  "request_id": "2a5803f5-f8b7-4db8-8a2e-4db8e6db1f5f",
  "store_id": "1cc66e24-4e93-4c9e-bebd-8ff9690e33cd",
  "order_id": "demo-123",
  "jurisdiction": "CO",
  "amount_cents": 29,
  "status": "reversed",
  "reversal_reason": "DELIVERY_CANCELLED",
  "subject": "ops@example.com"
}
```

Logs stream to STDOUT from the API container and can be tailed with
`make logs-api`. Use a log aggregation tool (e.g., CloudWatch, Loki) in hosted
environments to ingest these JSON lines.

## Audit logs

In addition to streaming logs, each quote/apply operation persists an
`audit_logs` row containing the full request context. Access the audit history
through `GET /api/v1/audit?store_id=<uuid>` or directly from the `audit_logs`
table for compliance reviews. The smoke test ensures at least one audit event is
present after setup.
