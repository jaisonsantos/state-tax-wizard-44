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
| `decision_latency_ms` | Histogram | _none_ | Measures time spent calculating fees in the `/v1/fees/apply` route. Buckets are Prometheus defaults for histograms. |

Scrape `/metrics` from the API container or <http://localhost:8000/metrics> when
running locally.

## Structured application logs

Structured logs are emitted via `observability.log_fee_event` as JSON messages to
the `fee` logger. Each invocation includes contextual fields useful for tracing
user behavior.

### Schema

| Field | Example | Notes |
| ----- | ------- | ----- |
| `event` | `"fee_apply"` | Event type (currently only `fee_apply`). |
| `request_id` | `"5bf08d4d-a121-4b47-a81b-6cde5b0c33af"` | Propagated from `X-Request-ID` header if provided; otherwise generated per request. |
| `store_id` | `"1cc66e24-4e93-4c9e-bebd-8ff9690e33cd"` | UUID of the merchant store associated with the fee. |
| `order_id` | `"smoke-order-mn"` | Checkout order identifier supplied by the client. |
| `jurisdiction` | `"MN"` | Taxing jurisdiction for the applied fee. |
| `amount_cents` | `50` | Fee amount stored in cents. |
| `reason_codes` | `["MN_THRESHOLD_MET"]` | Decision codes associated with the fee line. |
| `delivery_method` | `"ship"` | Delivery method from the request payload. |

### Sample payload

```json
{
  "event": "fee_apply",
  "request_id": "a2c6467f-6c3d-4dc2-95da-f5b46f5b46cd",
  "store_id": "1cc66e24-4e93-4c9e-bebd-8ff9690e33cd",
  "order_id": "demo-123",
  "jurisdiction": "MN",
  "amount_cents": 50,
  "reason_codes": ["MN_THRESHOLD_MET"],
  "delivery_method": "ship"
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
