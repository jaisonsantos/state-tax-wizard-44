# Analytics Overview API

The analytics API powers the dashboard KPI cards and recent fee decision feed. It aggregates fee telemetry, Prometheus counter snapshots, and audit log cursors into a single response so the frontend can render live metrics without stitching multiple endpoints together.

## Endpoint

```
GET /api/v1/analytics/overview
```

### Query parameters

| Name | Required | Description |
| ---- | -------- | ----------- |
| `store_id` | ✅ | UUID of the store whose analytics should be returned. Authorization is enforced via the caller's session. |
| `limit` | ❌ | Number of audit events to include in `recent_decisions.items`. Defaults to `5`. |
| `cursor` | ❌ | Cursor token returned by a previous response when more audit rows are available. When present, `page` semantics are ignored. |
| `window_days` | ❌ | Rolling number of days used to calculate KPI deltas. Defaults to `30` and accepts values between 7 and 90. |

### Response payload

```json
{
  "store_id": "1cc66e24-4e93-4c9e-bebd-8ff9690e33cd",
  "generated_at": "2025-01-24T14:02:11.821232+00:00",
  "window_start": "2024-12-25T14:02:11.821232+00:00",
  "window_end": "2025-01-24T14:02:11.821232+00:00",
  "metric_cards": [
    {
      "id": "fees_applied_30d",
      "title": "Fees Applied (30d)",
      "value": 1247,
      "formatted_value": "1,247",
      "delta": 112,
      "delta_percentage": 0.096,
      "trend": "up",
      "unit": "count",
      "insight": "Total successful fee applications across all jurisdictions."
    },
    {
      "id": "co_fee_total",
      "title": "CO Fees Total",
      "value": 284700,
      "formatted_value": "$2,847.00",
      "delta": -6100,
      "delta_percentage": -0.0209,
      "trend": "down",
      "unit": "currency_cents",
      "jurisdiction": "CO",
      "insight": "Gross Colorado fees collected in the last 30 days."
    }
  ],
  "recent_decisions": {
    "items": [
      {
        "id": "8d04bb7f-9c38-4bdf-9e0a-5a94c2e9b2e4",
        "occurred_at": "2025-01-24T13:57:02.114000+00:00",
        "order_id": "store_demo_1-ORDER-0042",
        "jurisdiction": "MN",
        "amount_cents": 50,
        "outcome": "applied",
        "reason_codes": ["MN_THRESHOLD_MET"]
      }
    ],
    "next_cursor": null
  },
  "counters": {
    "fees_applied_total": 5234,
    "fees_absorbed_total": 1489,
    "report_exports_total": 92
  }
}
```

### Notes

- `metric_cards` always includes percentage deltas relative to the preceding window so the frontend can render trend indicators without additional math.
- `recent_decisions.items` only surfaces `fee_apply` and `fee_reverse` audit events so the dashboard feed stays focused on fee decisions. Other audit types remain available through the `/api/v1/audit` endpoint.
- `recent_decisions.next_cursor` is `null` when the requested window has no additional audit rows. Pass the cursor value back to continue fetching history without an ever-increasing offset.
- `counters` contains Prometheus snapshot values pulled directly from the in-process collectors (`fees_applied_total`, `fees_absorbed_total`, and `report_exports_total`). This avoids scraping `/metrics` from the frontend.
- KPI totals and deltas in `metric_cards` come from transactional data, not the Prometheus counters, so deployments with multiple API instances continue to return consistent analytics.
- Successful responses increment the `analytics_dashboard_loaded_total{store_id="..."}` counter and emit a structured `analytics_dashboard_loaded` log entry for auditability. See [`docs/security/observability.md`](../security/observability.md) for field definitions.

### Error responses

- `401 Unauthorized` — The request is missing a valid `Authorization: Bearer <token>` header.
- `403 Forbidden` — The session does not have access to the requested `store_id`.
- `422 Unprocessable Entity` — Validation errors (e.g., missing `store_id` or an invalid cursor token).
- `500 Internal Server Error` — Unexpected failures while aggregating metrics or fetching audit logs. Check API logs for the co
rrelating `request_id`.
