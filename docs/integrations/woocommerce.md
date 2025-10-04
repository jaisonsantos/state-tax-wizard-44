# WooCommerce Integration Guide

This guide explains how to configure the State Tax Wizard WooCommerce plugin, validate the integration, and capture observability evidence.

## Prerequisites
- WordPress 6.0+
- WooCommerce 7.0+
- PHP 8.0+
- State Tax Wizard credentials (store ID, HMAC secret)
- Feature flag `INTEGRATIONS_WOO_ENABLED=true` in the API environment

## Installation
1. Generate the plugin package:
   ```bash
   make woocommerce-build
   ```
   The ZIP is written to `integrations/woocommerce/dist/`.
2. In WordPress, navigate to **Plugins → Add New → Upload Plugin** and upload the ZIP.
3. Activate the plugin and open **WooCommerce → Settings → State Tax Wizard**.
4. Provide the following values:
   - **API Base URL** (e.g., `https://api.statetaxwizard.com`)
   - **Store ID** (from the State Tax Wizard dashboard)
   - **HMAC Secret** (rotate from `/billing` → **Rotate HMAC secret**)
   - Enable jurisdictions (MN/CO) and optional label override.
5. Save changes. The plugin stores configuration in the `stw_settings` option and logs activity via the built-in logger.

## Validation
- Run PHPUnit tests locally:
  ```bash
  make woocommerce-test
  ```
- Execute the API smoke to confirm status counters increment:
  ```bash
  make integrations-smoke
  ```
- Verify the WooCommerce provider entry is `connected`:
  ```bash
  curl -s "${API_BASE_URL}/api/v1/integrations/status?store_id=<STORE_ID>" \
    -H "Authorization: Bearer <token>" | jq '.providers[] | select(.provider=="woocommerce")'
  ```
- Inspect `/metrics` for:
  ```text
  integrations_requests_total{provider="woocommerce",route="status"} > 0
  integrations_errors_total{provider="woocommerce",reason="disabled"}
  ```

## Operations
- Logs: **WooCommerce → State Tax Wizard** shows the last 50 events (nonce previews only).
- Packaging: re-run `make woocommerce-build` for new releases; the script zips source + assets without vendor dependencies.
- Uninstall: deactivate the plugin; the backend retains audit logs (`integration_install` entries).

## Troubleshooting
| Symptom | Cause | Resolution |
| --- | --- | --- |
| Fee not applied in cart | Missing credentials | Confirm API base URL, store ID, and HMAC secret are populated. |
| `integration_disabled` from API | Feature flag disabled | Set `INTEGRATIONS_WOO_ENABLED=true` and restart the API service. |
| `invalid_signature` response | Clock skew or stale secret | Ensure the server uses NTP and rotate the secret via `/billing`. |
| Logs empty | Plugin never executed | Add products, ensure checkout flow uses shipping, verify plugin activated. |

Refer to `docs/security/hmac.md` for canonical signing details and nonce retention rules.
