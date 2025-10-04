# Platform Onboarding Playbook

This guide explains how the DeliveryFee Router UI orchestrates Shopify and WooCommerce integrations and how to validate the end-to-end flow in a local environment.

## Prerequisites

- Run `docker-compose up` so the FastAPI backend and Vite frontend are available.
- Seed demo data with `make migrate && make seed` so `store_demo_1` (Shopify) and `store_demo_3` (WooCommerce) exist.
- Feature flags `INTEGRATIONS_SHOPIFY_ENABLED` and `INTEGRATIONS_WOO_ENABLED` must be `true` (defaults in `.env.example`).
- Log in to the web app (`http://localhost:8080/login`) using the seeded credentials listed in `README.md`.

## How the onboarding UI works

1. **Store selection** – the `AuthProvider` stores the active store ID. All integration calls require this ID.
2. **Status check** – when `/onboarding` loads, the page calls `GET /api/v1/integrations/status?store_id=<STORE_ID>` and renders provider badges (Connected, Action required, or Disabled).
3. **Install action** – clicking **Install Shopify App** or **Mark WooCommerce Installed** issues `POST /api/v1/integrations/providers/<provider>/install?store_id=<STORE_ID>`. The backend updates the `stores.platform` column and records an audit log entry (`integration_install`).
4. **Settings sync** – after a successful install, the UI refreshes the status call and the Settings page will now show the connector as connected. The Next Steps buttons deep-link into the Settings playground or Dashboard.
5. **Plan display** – `/settings` now resolves the current billing plan via the active subscription (same value returned by `GET /api/v1/billing/entitlements`). The UI capitalises this slug (e.g. `pro` → `Pro`).

## Shopify end-to-end validation

1. Navigate to `/onboarding` and ensure the Shopify card shows **Action required**.
2. Click **Install Shopify App**. The toast "Integration connected" should appear.
3. Visit `/settings#integrations` and confirm the Shopify badge is **connected**. The API log will contain an `integration_install` audit entry.
4. Confirm the plan banner says `Current plan: Pro` when using the seeded `store_demo_3` (which has a Pro subscription).
5. Use the Next Steps buttons:
   - **Configure Rules** → scrolls to the fee toggle card.
   - **Test Integration** → jumps to the Rules Playground.
   - **View Dashboard** → opens `/dashboard`.

## WooCommerce end-to-end validation

1. On `/onboarding`, verify the WooCommerce card reflects the current status.
2. Click **Mark WooCommerce Installed** to register the connector (mirrors the Shopify flow).
3. Confirm `/settings#integrations` shows the WooCommerce connector as connected and the audit log contains a matching entry.
4. Trigger a test calculation from the Rules Playground to ensure the store can call `/api/v1/fees/quote` and `/api/v1/fees/apply` without HMAC issues.

## Troubleshooting checklist

- **"Integration unavailable" toast** – ensure the corresponding feature flag is enabled and restart the backend.
- **Plan still shows Starter** – verify the `subscriptions` table for the store has the expected `plan_tier`; `GET /api/v1/billing/entitlements` should mirror the UI.
- **Buttons do not navigate** – confirm the browser URL includes the hash fragment (`#fee-rules` or `#rules-playground`). React Router will scroll to the matching card IDs in `Settings.tsx`.

Collect screenshots or CLI output while executing these steps to attach to certification evidence when required.
