# Integrations Support Playbook

Guidance for diagnosing and resolving WooCommerce/Shopify integration issues.

## Contact Roles
- **Support engineer:** first-responder, gathers logs, confirms configuration.
- **Integrations lead:** escalates complex API or plugin defects.
- **Platform engineer:** reviews `/metrics`, feature flags, and database integrity.

## Common Issues
| Symptom | Likely Cause | Resolution |
| --- | --- | --- |
| `integration_disabled` HTTP 503 | Feature flag disabled | Set `INTEGRATIONS_WOO_ENABLED` or `INTEGRATIONS_SHOPIFY_ENABLED` to `true` and restart the API service. |
| `invalid_signature` from `/v1/fees/apply` | Stale HMAC secret or clock skew | Rotate secret via Settings → Rotate HMAC secret; confirm system clocks use NTP. |
| No fee line in cart (WooCommerce) | Missing configuration | Ensure API Base URL, Store ID, and HMAC secret are populated in the plugin settings page. |
| Shopify webhook `401` | Secret mismatch | Update `SHOPIFY_WEBHOOK_SECRET`, redeploy app, and replay event. |
| Metrics show provider errors | High error rate in `integrations_errors_total` | Inspect `api` logs (`integration_install`, `integration_request_failed`). Review plugin/app logs for payload anomalies. |

## Diagnostics
1. Check `/api/v1/integrations/status?store_id=<id>` for provider state (`connected`, `disabled`, `disconnected`).
2. Tail API logs (search for `integration_install` or `nonce_preview`) ensuring secrets remain masked.
3. Review `/metrics` for:
   ```
   integrations_requests_total{provider="shopify",route="status"}
   integrations_errors_total{provider="woocommerce",reason="disabled"}
   ```
4. For WooCommerce, inspect **WooCommerce → State Tax Wizard** logs for recent entries.
5. For Shopify, check application logs (proxy + webhook) and confirm environment variables are present.

## Escalation Matrix
1. Support engineer triages and documents reproduction steps in the ticket.
2. If API returns 5xx or database inconsistencies, escalate to platform engineer with request IDs and audit log extracts.
3. For plugin-specific issues (PHP/JS errors), engage integrations lead who owns the respective codebase.
4. Communicate status updates to the merchant at least every 2 hours during incidents.

## Post-Incident Checklist
- [ ] Capture `integrations_requests_total` / `integrations_errors_total` deltas around the incident window.
- [ ] Attach sanitized logs (200 lines max) to the ticket.
- [ ] Update `docs/integrations/testing.md` if new regression scenarios are identified.
- [ ] Consider rotating HMAC secrets if there is any indication of compromise.
