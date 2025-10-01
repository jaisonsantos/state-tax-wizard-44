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
| `report_exports_total` | Counter | `jurisdiction`, `format` | Counts report exports emitted by `ReportService` so dashboards can trend CSV vs JSON demand per jurisdiction. |
| `auth_events_total` | Counter | `event` | Tracks authentication lifecycle activity (`login`, `logout`) to confirm session churn and spot unexpected spikes. |
| `analytics_dashboard_loaded_total` | Counter | `store_id` | Increments when `/v1/analytics/overview` responds successfully so ops teams can monitor dashboard traffic by store. |
| `hmac_validation_failures_total` | Counter | `reason`, `store_id` | Counts request signing failures segmented by failure reason (missing signature, stale timestamp, invalid signature). |
| `hmac_replay_attempts_total` | Counter | `store_id` | Tracks replay attempts detected by nonce validation to highlight potential abuse. |
| `rate_limit_throttles_total` | Counter | `route` | Counts how often the distributed rate limiter rejects requests for each API route. |

Scrape `/metrics` from the API container or <http://localhost:8000/metrics> when
running locally.

Report exports only increment `report_exports_total` on successful downloads, but
failure cases (such as unsupported formats) still emit `log_report_event`
entries and audit rows so compliance teams can trace every attempt.

## Structured application logs

Structured logs are emitted via `observability.log_fee_event`,
`observability.log_report_event`, `observability.log_analytics_event`, `observability.log_security_event`, and `observability.log_auth_event` as JSON messages to dedicated loggers. Each invocation includes contextual fields useful
for tracing user behavior. Fee
application and reversal flows publish events through the `fee` logger so
downstream systems can reconcile adjustments. Report exports stream to the
`report` logger, giving compliance and analytics tooling visibility into which
jurisdictions and formats operators are downloading.

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

### Report export schema

| Field | Example | Notes |
| ----- | ------- | ----- |
| `event` | `"report_export"` | Identifies the log as a report export event. |
| `store_id` | `"1cc66e24-4e93-4c9e-bebd-8ff9690e33cd"` | UUID associated with the export. |
| `report` | `"co_dr1786"` | Report identifier (`co_dr1786` or `mn_summary`). |
| `format` | `"csv"` | Export format supplied by the client. |
| `from_date` | `"2024-01-01T00:00:00+00:00"` | Start of the requested range. |
| `to_date` | `"2024-01-31T23:59:59+00:00"` | End of the requested range. |
| `row_count` | `12` | Count of fee rows used to build the export (0 when seeded demo data is returned). |
| `outcome` | `"success"` | `success` on a clean download; `failure` when an error is raised. |
| `error` | `"Unsupported format 'xlsx'"` | Present only when `outcome=failure`. |

### Auth event schema

| Field | Example | Notes |
| ----- | ------- | ----- |
| `event` | `"login"` or `"logout"` | Distinguishes sign-in vs sign-out actions. |
| `subject` | `"ops@example.com"` | Email address embedded in the JWT. |
| `user_id` | `"4e021a16-65b5-4ad0-9ad7-673d6b4d9c4d"` | UUID of the authenticated user. |
| `session_id` | `"5f3f5d3c-3d81-4a20-8a6c-5f7b2b2c871e"` | Identifier of the `session_tokens` row tied to the token. |
| `jti` | `"a3c45846-31d0-47a8-bc47-542d68c30cb8"` | Present on login events to mirror the JWT claim. |

### Security event schema

| Field | Example | Notes |
| ----- | ------- | ----- |
| `event` | `"hmac_validation_failed"` | Event types include `hmac_validation_failed`, `hmac_validation_succeeded`, `hmac_replay_detected`, `hmac_nonce_recorded`, and `rate_limit_throttle`. |
| `store_id` | `"1cc66e24-4e93-4c9e-bebd-8ff9690e33cd"` | UUID for the store associated with the signed request. |
| `code` | `"stale_timestamp"` | Failure-specific reason code mirrored in API responses. |
| `nonce_preview` | `"abc123ef"` | First eight characters of the nonce for debugging without leaking the full value. |
| `timestamp` | `"2025-03-15T18:02:14+00:00"` | Present on successful validations. |
| `expires_at` | `"2025-03-15T18:12:14+00:00"` | Present on nonce recording events to indicate TTL. |
| `retry_after_seconds` | `12` | Present on `rate_limit_throttle` events to indicate when a client can retry safely. |

```json
{
  "event": "hmac_validation_failed",
  "store_id": "1cc66e24-4e93-4c9e-bebd-8ff9690e33cd",
  "code": "replay_detected",
  "nonce_preview": "6f19c8e1"
}
```

```json
{
  "event": "hmac_validation_succeeded",
  "store_id": "1cc66e24-4e93-4c9e-bebd-8ff9690e33cd",
  "timestamp": "2025-03-15T18:02:14+00:00"
}
```

### Analytics dashboard schema

| Field | Example | Notes |
| ----- | ------- | ----- |
| `event` | `"analytics_dashboard_loaded"` | Identifies the log as an analytics dashboard response. |
| `store_id` | `"1cc66e24-4e93-4c9e-bebd-8ff9690e33cd"` | UUID associated with the analytics snapshot. |
| `metric_cards` | `5` | Number of KPI cards returned in the payload. |
| `feed_length` | `6` | Count of recent fee decisions included in the feed. |
| `next_cursor` | `null` | Cursor token when more audit rows are available. |
| `duration_ms` | `42.8` | Response time in milliseconds for generating the overview. |
| `request_id` | `"8df6bf0a-d3f4-4ba5-b2cf-e2f02f3af0a0"` | Request correlation identifier used across the stack. |

Logs stream to STDOUT from the API container and can be tailed with
`make logs-api`. Use a log aggregation tool (e.g., CloudWatch, Loki) in hosted
environments to ingest these JSON lines. Filter on the `report` logger or the
`event` field to isolate export activity.

## Audit logs

In addition to streaming logs, each quote/apply operation persists an
`audit_logs` row containing the full request context. Access the audit history
through `GET /api/v1/audit?store_id=<uuid>` or directly from the `audit_logs`
table for compliance reviews. The smoke tests now cover `/v1/analytics/overview`
via `make analytics-smoke` so counter snapshots are validated alongside the
reporting flows.
