# Security Incident Response Playbook

This playbook outlines the steps operators should follow when responding to
security events discovered in metrics, logs, or customer reports. It builds on
the observability signals in [`docs/security/observability.md`](observability.md)
and assumes Milestones 3–5 are deployed.

## Roles & communication

| Role | Responsibilities |
| --- | --- |
| Incident commander | Coordinates response, keeps the timeline, and escalates decisions. |
| Engineering lead | Performs technical triage, implements remediations, and restores service. |
| Support liaison | Communicates updates to affected merchants and records customer impact. |
| Security analyst | Reviews audit logs, metrics, and determines containment scope. |

Document the responders in your on-call rota and ensure contact methods are
available in your paging system.

## Detection signals

Monitor the following counters and logs via Prometheus and centralized logging:

- `hmac_validation_failures_total{reason}` – spikes indicate signature errors,
  stale timestamps, or tampering. 【F:backend/app/security/hmac.py†L96-L169】
- `hmac_replay_attempts_total{store_id}` – duplicates within the replay TTL. 【F:backend/app/security/hmac.py†L96-L169】
- `rate_limit_throttles_total{route}` plus `rate_limit_throttle` events in the
  security logger – highlight abuse or runaway integrations. 【F:backend/app/security/rate_limit.py†L34-L116】
- Billing logs with `event="billing_unconfigured"` – Stripe credentials missing
  or revoked. 【F:backend/app/routers/billing.py†L19-L84】
- Audit log actions `store_secret.rotated`, `auth.logout`, and `fee_reverse`
  – confirm authorised rotation and reversal activity. 【F:backend/app/models/models.py†L57-L170】

## Response scenarios

### Compromised HMAC secret

1. **Containment** – Rotate the affected store's secret immediately via the UI or
   API. 【F:src/pages/Settings.tsx†L210-L288】
2. **Block abuse** – Verify rate limiter status (`rate_limit_throttles_total`) to
   ensure malicious clients are throttled while the new secret propagates.
3. **Audit** – Review recent `AuditLog` entries for suspicious apply requests or
   reversals. 【F:backend/app/services/analytics_service.py†L19-L128】
4. **Notify** – Inform the merchant to update their integration with the new
   secret and confirm rotation timestamp in the UI.
5. **Post-incident** – Document the event in the incident log and capture a
   lessons-learned summary referencing counter evidence.

### Replay or automation abuse

1. Inspect the offending store ID from `hmac_replay_attempts_total` or
   `rate_limit_throttles_total` counters.
2. Check `/v1/fees/apply` logs for repeated payloads and confirm the 409/429
   responses are present.
3. Communicate retry/backoff expectations to the integration owner.
4. Consider temporarily lowering rate limits via environment configuration if
 abuse persists (e.g., `RATE_LIMIT_LIMIT`).

### Webhook DLQ / latency alerts

1. **Alert triggers**
   - `increase(webhooks_processed_total{outcome="dead_letter"}[10m]) > 0`
   - `histogram_quantile(0.95, rate(webhook_processing_latency_ms_bucket{provider="stripe"}[5m])) > 0.5`
2. **First response**
   - Query `processed_webhooks` for `dead_letter = true` and capture `event_id`,
     `last_error`, and `attempts`.
   - Replay via `POST /api/v1/billing/webhooks/stripe/replay/{event_id}` or
     Stripe CLI if the API is unavailable.
   - Inspect Stripe status page and recent deploys for external causes.
3. **Remediation**
   - If retries continue failing, capture logs (`webhook_processed` events) and
     escalate to the on-call engineer per the rotation table.
   - After resolution, run `make webhooks-smoke` to validate the path end-to-end
     and attach `webhooks_smoke.txt` to the incident ticket.

### Stripe credential revocation

1. `billing_unconfigured` errors indicate missing or invalid keys. Update the
   Stripe secret via your secrets manager and redeploy. 【F:backend/app/services/stripe_service.py†L15-L220】
2. Replay webhook events using the Stripe CLI to ensure successful verification.
3. Communicate downtime or degraded billing functionality to stakeholders.
4. Verify the Billing smoke test passes or emits the expected skip message after
   remediation. 【F:docs/certification/EVIDENCE/billing_smoke.txt†L1-L1】

## Post-incident checklist

- [ ] Capture start/end timestamps, impact summary, and remediation steps.
- [ ] Link metrics/log screenshots or evidence files under
      `docs/certification/EVIDENCE/`.
- [ ] File follow-up tasks in the backlog (e.g., rate-limit tuning, alert
      thresholds).
- [ ] Review and update this playbook if new scenarios were uncovered.

## Preventive actions

- Regularly execute `make security-smoke` and `make billing-smoke` to validate
  guardrails in lower environments. 【F:Makefile†L50-L106】
- Keep secrets rotation procedures up to date as described in
  [`docs/security/secrets.md`](secrets.md).
- Ensure on-call engineers can access Prometheus and log aggregation tools before
  incidents occur.
