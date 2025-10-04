# Observability Playbook

This playbook consolidates the production monitoring strategy for State Tax Wizard once the webhooks slice is deployed.

## 1. Dashboards

Create a Grafana dashboard (or equivalent) with the following panels:

- **Webhook Throughput** – `rate(webhooks_received_total{provider="stripe"}[5m])` grouped by `event`. Highlights unexpected drops or spikes.
- **Webhook Outcomes** – stacked bar chart of `increase(webhooks_processed_total{provider="stripe"}[5m])` split by `outcome` (`processed`, `duplicate`, `retry`, `dead_letter`). Alerts when `dead_letter` increments.
- **Webhook Latency (p95)** – `histogram_quantile(0.95, sum(rate(webhook_processing_latency_ms_bucket{provider="stripe"}[5m])) by (le))` to ensure processing stays under 500 ms.
- **Integration Traffic** – `rate(integrations_requests_total{provider!=""}[5m])` by provider/route for WooCommerce and Shopify connectors.
- **Billing Counters** – timeseries for `billing_events_total` and `checkout_sessions_created_total` to correlate subscription activity with webhook spikes.
- **Error Overview** – table of `increase(integrations_errors_total[5m])` and `increase(webhooks_processed_total{outcome="retry"}[5m])` to surface integration or webhook issues.

Store the dashboard JSON export under your monitoring repo and link it in the runbook once created.

## 2. Alerts

Recommended Prometheus alert rules:

```yaml
- alert: WebhookDeadLetterBurst
  expr: increase(webhooks_processed_total{provider="stripe",outcome="dead_letter"}[10m]) > 0
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Stripe webhook moved to DLQ"
    description: "Check processed_webhooks table and replay via POST /api/v1/billing/webhooks/stripe/replay/{event_id}."

- alert: WebhookIngestionGap
  expr: rate(webhooks_received_total{provider="stripe"}[10m]) == 0
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "No Stripe webhooks received"
    description: "Verify Stripe CLI/listener, credentials, and event subscriptions."

- alert: IntegrationErrorSpike
  expr: increase(integrations_errors_total[5m]) > 5
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Integration errors observed"
    description: "Consult WooCommerce/Shopify logs and /metrics for route/ reason labels."
```

## 3. Processed Webhooks Retention

`processed_webhooks` persists every event for traceability. Configure a weekly job (SQL or Celery/cron) to delete rows older than 30 days that are `status = 'processed'` and `dead_letter = false`. Suggested SQL:

```sql
DELETE FROM processed_webhooks
 WHERE status = 'processed'
   AND dead_letter = false
   AND processed_at < NOW() - INTERVAL '30 days';
```

Document the job in your infrastructure repository and expose metrics for deletions if possible.

## 4. Runbook Updates

- **Replay procedure:** Use the docs in `docs/billing/stripe.md` to replay events via CLI/cURL. Record replay attempts in ticketing tools.
- **Incident escalation:** Update `docs/security/incident-response.md` to include webhook-specific responders and troubleshooting steps (alerts above, DLQ query).
- **Evidence capture:** Archive `webhooks_smoke.txt`, `metrics_dump.txt`, and `api_logs.txt` with every certification run to prove metrics and DLQ behaviour.

## 5. Additional Monitoring Hooks

- Emit structured log events (`webhook_processed`) already include `outcome`. Ship logs to your SIEM with filters for `outcome = dead_letter`.
- Consider adding tracing spans if you adopt OpenTelemetry — instrument the webhook handler and subscription service to measure DB latency during bursts.

With dashboards, alerts, retention, and runbooks in place, Milestone 8 can focus on production readiness without rediscovering the webhook plumbing.
