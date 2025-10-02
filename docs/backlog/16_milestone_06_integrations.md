# Milestone 6 — Platform Integrations Alpha

_[← Milestone 5 — Billing](15_milestone_05_billing.md) • [Milestone 7 — Webhooks →](17_milestone_07_webhooks.md)_

## Stage Validation Summary

- **Backend fee endpoints ready**: `/v1/fees/quote` and `/v1/fees/apply` accept structured payloads with item details ([`backend/app/routers/fees.py`](../../backend/app/routers/fees.py)).
- **Security foundation in place**: HMAC verification and rate limiting protect API endpoints (Milestone 4).
- **Audit logging captures decisions**: All fee operations logged with full context ([`backend/app/services/audit_repository.py`](../../backend/app/services/audit_repository.py)).
- **Remaining gap**: No WooCommerce plugin or Shopify app exists; integrations only tested via Postman/API.

## Next Development Objective

Deliver **WooCommerce Plugin** and **Shopify App POC** to enable native checkout fee injection, providing real merchant value and validating API contracts against production e-commerce flows.

## Implementation Plan

### 1. WooCommerce Plugin Foundation

- Create directory structure `integrations/woocommerce/`:

  ```
  woocommerce/
  ├── state-tax-wizard.php          # Main plugin file
  ├── includes/
  │   ├── class-fee-calculator.php  # API client for /v1/fees/quote
  │   ├── class-order-sync.php      # Persist via /v1/fees/apply
  │   ├── class-settings.php        # Admin settings page
  │   └── class-logger.php          # Local logging wrapper
  ├── admin/
  │   ├── settings-page.php         # WordPress admin UI
  │   └── logs-page.php             # View last 50 fee decisions
  ├── assets/
  │   ├── css/admin.css
  │   └── js/admin.js
  ├── tests/
  │   └── test-fee-calculator.php   # PHPUnit tests
  ├── README.md                     # Installation & configuration
  └── package.sh                    # Build distributable ZIP
  ```
- **Main Plugin File** (`state-tax-wizard.php`):
  - Plugin header (Name, Version, Author, WP compatibility 6.0+).
  - Register activation hook to create `wp_tax_wizard_logs` table.
  - Hook into `woocommerce_cart_calculate_fees` for cart fees.
  - Hook into `woocommerce_checkout_order_processed` for order persistence.
- **Fee Calculator Class**:
  - `get_quote($cart_items, $delivery_address)`: Calls `/v1/fees/quote` with HMAC signature.
  - Transforms WooCommerce cart item array to API schema.
  - Returns fee amount and reason codes or null if not applicable.
- **Order Sync Class**:
  - `apply_fee($order_id)`: Calls `/v1/fees/apply` after order completion.
  - Stores API response in order meta for audit trail.
  - Logs success/failure to `wp_tax_wizard_logs`.

### 2. WooCommerce Admin Settings

- Create WordPress admin menu: "State Tax Wizard" under WooCommerce.
- Settings page fields:
  - API Base URL (default: `https://api.statetaxwizard.com`).
  - Store ID (UUID from State Tax Wizard dashboard).
  - HMAC Secret (generated in State Tax Wizard settings).
  - Enabled Jurisdictions: Checkboxes for MN, CO.
  - Absorb Fee: Toggle (if enabled, fee shown as "Tax" instead of separate line).
  - Custom Label: Text field (default: "Retail Delivery Fee").
- Save settings to WordPress options API: `wp_options` table.
- Settings validation: Test API connectivity on save.
- **Logs Page**:
  - Display last 50 fee calculations from `wp_tax_wizard_logs`.
  - Columns: Timestamp, Order ID, Jurisdiction, Fee Amount, Status, Reason Codes.
  - Pagination and search by Order ID.
  - "View Details" button shows full API request/response JSON.

### 3. WooCommerce Fee Injection

- Hook: `add_action('woocommerce_cart_calculate_fees', 'inject_retail_delivery_fee', 10)`.
- Logic:
  - Check if delivery address matches enabled jurisdictions (MN zip >= 55000, CO enabled).
  - Call `FeeCalculator::get_quote()` with cart items.
  - If fee applicable, add via `WC()->cart->add_fee($label, $amount, true)`.
  - If absorb fee enabled, add as `$taxable = true` to bundle into tax display.
  - Cache quote for 5 minutes to avoid duplicate API calls during checkout flow.
- Error handling:
  - If API unreachable, log warning, skip fee (fail open to avoid blocking checkout).
  - Display admin notice if API credentials invalid.

### 4. WooCommerce Order Persistence

- Hook: `add_action('woocommerce_checkout_order_processed', 'persist_fee_order', 10, 1)`.
- Logic:
  - Extract order ID, items, final fee amount, customer address.
  - Call `/v1/fees/apply` with order data + HMAC signature.
  - Store API `order_fee_id` in order meta: `_tax_wizard_fee_id`.
  - If API call fails, retry up to 3 times with exponential backoff.
  - Log failure to `wp_tax_wizard_logs` and WooCommerce error log.
- Admin order view:
  - Display "State Tax Wizard Fee" line item with link to logs page.
  - Show API response status and timestamp.

### 5. WooCommerce Testing & Packaging

- **PHPUnit Tests** (`tests/test-fee-calculator.php`):
  - Mock WooCommerce cart items and API responses.
  - Test quote parsing, HMAC signature generation, error handling.
  - Validate settings sanitization and validation.
- **Manual Testing Checklist**:
  - Install plugin on WooCommerce test site (WP 6.0+, WC 8.0+).
  - Configure settings with staging API credentials.
  - Add products to cart, verify fee appears in cart totals.
  - Complete checkout, confirm order persisted to State Tax Wizard API.
  - Check logs page displays order history.
  - Test error scenarios (invalid HMAC, API timeout, non-applicable state).
- **Packaging Script** (`package.sh`):

  ```bash
  #!/bin/bash
  rm -rf dist/
  mkdir -p dist/state-tax-wizard
  rsync -av --exclude='tests' --exclude='node_modules' --exclude='.git' . dist/state-tax-wizard/
  cd dist && zip -r state-tax-wizard-v1.0.0.zip state-tax-wizard/
  ```
  - Produces distributable ZIP for WordPress plugin directory or manual install.
  - Version number sourced from plugin header.

### 6. Shopify App Foundation

- Create directory structure `integrations/shopify/`:

  ```
  shopify/
  ├── app/
  │   ├── routes/
  │   │   ├── app.proxy.tsx       # App proxy endpoint
  │   │   ├── webhooks.orders.tsx # Order webhook handler
  │   │   └── auth.callback.tsx   # OAuth flow
  │   ├── services/
  │   │   ├── fee-service.ts      # API client for State Tax Wizard
  │   │   └── shopify-client.ts   # Shopify Admin API client
  │   └── utils/
  │       ├── hmac.ts             # HMAC signature generation
  │       └── config.ts           # Environment variables
  ├── public/
  ├── shopify.app.toml            # Shopify CLI config
  ├── package.json
  ├── README.md
  └── .env.example
  ```
- **Technology Stack**: Remix + Prisma + Shopify Polaris (or Node.js/Express alternative).
- **App Proxy Endpoint** (`/apps/tax-wizard/quote`):
  - Receives cart data from Shopify Online Store via liquid theme integration.
  - Calls `/v1/fees/quote` with cart items and delivery address.
  - Returns JSON with fee amount and label.
  - Liquid theme displays fee in cart summary.

### 7. Shopify Product-Fee Injection

- **Approach**: Since Shopify doesn't support dynamic fees via app proxy at checkout (requires Shopify Plus for Checkout Extensions), use "Fee Product" method:
  - App creates hidden product "Retail Delivery Fee" in merchant's store.
  - App proxy endpoint calculates fee via `/v1/fees/quote`.
  - JavaScript injects fee product into cart at calculated price.
  - Customer sees fee as line item during checkout.
- **Alternative (Shopify Plus Only)**: Checkout UI Extension with dynamic fee calculation.
- Document limitation in README: "Standard Shopify accounts require fee displayed as product line item; Shopify Plus merchants can use native fee extensions."

### 8. Shopify Webhook Handler

- **Webhook Event**: `orders/create`.
- Endpoint: `/webhooks/orders` with HMAC verification (Shopify signature, not State Tax Wizard).
- Logic:
  - Parse order JSON, extract items, delivery address, fee product line item.
  - Call `/v1/fees/apply` with order data + State Tax Wizard HMAC signature.
  - Store `order_fee_id` in Shopify order metafields via Admin API.
  - Return 200 immediately to acknowledge webhook.
- Idempotency: Check if order already processed via metafield before calling `/apply`.

### 9. Shopify App Setup Documentation

- **README.md** (`integrations/shopify/README.md`):
  - Prerequisites: Shopify Partner account, Node.js 18+.
  - Local development setup with Shopify CLI (`shopify app dev`).
  - Environment variables: `SHOPIFY_API_KEY`, `SHOPIFY_API_SECRET`, `STATE_TAX_WIZARD_API_URL`, `STATE_TAX_WIZARD_STORE_ID`, `STATE_TAX_WIZARD_HMAC_SECRET`.
  - OAuth flow: Install app on test store.
  - Webhook registration: Use Shopify Admin API or CLI.
  - Theme integration: Liquid snippet for app proxy script.
- **Merchant Setup Guide**:
  - Install app from Shopify App Store (future) or custom app (now).
  - Configure State Tax Wizard credentials in app settings page.
  - Add liquid code to `cart.liquid` theme file (one-line include).
  - Test checkout with Minnesota/Colorado addresses.

### 10. Integration SDK & Shared Helpers

- Create `integrations/sdk/` directory:

  ```
  sdk/
  ├── typescript/
  │   ├── src/
  │   │   ├── client.ts         # API client with HMAC
  │   │   ├── types.ts          # Shared TypeScript types
  │   │   └── validators.ts     # Payload validation
  │   ├── package.json
  │   └── README.md
  └── python/
      ├── tax_wizard_sdk/
      │   ├── client.py
      │   ├── hmac.py
      │   └── models.py
      ├── setup.py
      └── README.md
  ```
- **TypeScript SDK**:
  - `TaxWizardClient` class with methods: `quote(items, address)`, `apply(order)`.
  - HMAC signature generation and timestamp/nonce handling.
  - Typed request/response interfaces matching backend schemas.
  - Export as npm package `@statetaxwizard/sdk`.
- **Python SDK**:
  - Similar structure for WooCommerce plugin or custom integrations.
  - Publish to PyPI as `state-tax-wizard-sdk`.
- **Usage Examples**:
  - Document in `integrations/sdk/examples/` with sample code for common scenarios.

### 11. Integration Testing

- **WooCommerce CI** (`.github/workflows/woocommerce.yml`):
  - Lint PHP code (`phpcs`, `phpstan`).
  - Run PHPUnit tests against WooCommerce test framework.
  - Build distributable ZIP and attach to CI run artifacts.
- **Shopify CI** (`.github/workflows/shopify.yml`):
  - Lint TypeScript (`eslint`, `tsc`).
  - Run Jest tests for API client and webhook handlers.
  - Build app and validate Shopify CLI config.
- **End-to-End Validation**:
  - Manual testing checklist in `docs/integrations/testing.md`.
  - Record screen capture of cart fee injection and order sync.
  - Store video in repo or link to cloud storage for milestone review.

### 12. Documentation & Enablement

- Create `docs/integrations/` directory:
  - `woocommerce.md`: Installation, configuration, troubleshooting.
  - `shopify.md`: Setup guide, webhook configuration, theme integration.
  - `hmac-client-examples.md`: Sample HMAC signature code (PHP, JS, Python).
  - `testing.md`: QA scenarios for both platforms.
- Update `docs/api/fees.md`:
  - Add "Integration Payloads" section with sample requests from WooCommerce/Shopify.
  - Document expected field mappings (WC product → API item, Shopify variant → SKU).
- Update `docs/backlog/README.md`:
  - Link to Epic 06 completion status.
  - Note WooCommerce alpha available for testing, Shopify POC functional.

### 13. Operations & Support

- Extend `docs/security/environment.md`:
  - Document integration-specific environment variables.
  - Note CORS configuration if frontend integrations call API directly.
- Create support playbook `docs/integrations/support.md`:
  - Common issues: HMAC mismatch, API timeout, incorrect address parsing.
  - Debugging: Enable WooCommerce debug log, Shopify webhook replay.
  - Escalation: When to investigate backend vs plugin/app issue.
- Monitoring:
  - Prometheus counter `integration_requests_total` by platform (woocommerce/shopify).
  - Alert on high error rate from specific integration.

## Deliverable Checklist

| Area | Tasks | Owners |
| --- | --- | --- |
| WooCommerce | Plugin code, settings page, fee injection, order sync | Integration team |
| Shopify | Remix app, app proxy, webhook handler, OAuth flow | Integration team |
| SDK | TypeScript/Python clients with HMAC helpers | Integration team |
| Testing | PHPUnit tests, Jest tests, manual QA checklist | QA team |
| Documentation | Setup guides, API examples, troubleshooting | Tech writing |
| CI/CD | Workflow for linting/testing integrations, ZIP packaging | DevOps team |
| Support | Playbook, monitoring, escalation procedures | Support team |

## Exit Criteria Checklist

- [ ] WooCommerce plugin code complete with fee calculator and order sync.
- [ ] WooCommerce admin settings page functional with API validation.
- [ ] WooCommerce logs page displays last 50 fee decisions.
- [ ] WooCommerce fee injection works in cart and checkout.
- [ ] WooCommerce order persistence calls `/v1/fees/apply` successfully.
- [ ] WooCommerce PHPUnit tests pass, distributable ZIP created.
- [ ] Shopify app proxy endpoint calculates quotes via API.
- [ ] Shopify webhook handler processes orders and stores metafields.
- [ ] Shopify OAuth flow allows merchant installation.
- [ ] Integration SDK (TypeScript/Python) published with documentation.
- [ ] CI workflows lint and test both integrations.
- [ ] End-to-end demo video recorded for WooCommerce and Shopify.
- [ ] Documentation covers installation, configuration, and troubleshooting.
- [ ] Postman collection includes integration payload examples.
- [ ] Monitoring dashboards track integration-specific metrics.
- [ ] Support playbook covers common integration issues.

## Integration Validation Scenarios

1. **WooCommerce Quote**: Add products to cart with MN address → Fee appears in cart totals.
2. **WooCommerce Apply**: Complete checkout → Order synced to API, fee logged.
3. **WooCommerce Error Handling**: API timeout → Checkout completes without fee, error logged.
4. **WooCommerce Settings**: Invalid HMAC secret → Admin notice displayed.
5. **Shopify Quote**: App proxy calculates fee → JavaScript injects fee product into cart.
6. **Shopify Webhook**: Order created → Webhook triggers `/v1/fees/apply`, metafield set.
7. **Shopify Idempotency**: Duplicate webhook → Second call skipped via metafield check.
8. **SDK Usage**: TypeScript SDK generates valid HMAC → API accepts request.

## Rollout Plan

1. **Week 11 Day 1-2**: WooCommerce plugin foundation and fee calculator.
2. **Week 11 Day 3-4**: WooCommerce admin settings and order sync.
3. **Week 11 Day 5**: WooCommerce testing and packaging.
4. **Week 12 Day 1-2**: Shopify app foundation and app proxy.
5. **Week 12 Day 3**: Shopify webhook handler and metafield storage.
6. **Week 12 Day 4**: Integration SDK (TypeScript/Python) and examples.
7. **Week 12 Day 5**: CI workflows, documentation, demo recording.

## Dependencies

- Requires Milestone 4 completion (HMAC verification ready).
- Requires Milestone 5 partial (entitlements for gating integration features).
- Access to WooCommerce test site and Shopify Partner account.

## Success Metrics

- **WooCommerce Adoption**: >10 merchants install plugin during alpha.
- **Shopify POC**: >3 Shopify stores complete test checkout flow.
- **API Reliability**: >99% of integration requests succeed.
- **Support Tickets**: <10% of installations require troubleshooting assistance.

Document completion of each checklist item with PR links, demo video links, and alpha tester feedback attached to milestone closure notes.
