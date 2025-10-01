# Retail Delivery Fee MVP — Backlog Overview

This directory organizes the product backlog for the Retail Delivery Fee MVP.
It translates the high-level technical brief into incremental epics and
acceptance criteria so that work can be planned and delivered in iterations.

## Structure

| File | Description |
| --- | --- |
| `01_foundation.md` | Cross-cutting foundations: environment, data model, observability |
| `02_auth_and_tenant.md` | Authentication, authorization, and tenant scoping |
| `03_fee_engine.md` | Rule engine, quote/apply APIs, and audit logging |
| `04_reporting.md` | CSV/JSON report generation and validation tooling (see [`docs/reports/co_dr1786.md`](../reports/co_dr1786.md)) |
| `05_frontend.md` | React front-end experiences (dashboard, settings, reports, etc.) |
| `06_integrations.md` | Shopify and WooCommerce integrations |
| `07_billing.md` | Billing and entitlements (Stripe roadmap) |
| `08_security.md` | Security hardening (HMAC, rate limiting, key rotation) |
| `09_webhooks_and_reversals.md` | Order lifecycle webhooks, refunds, cancellations |
| `10_quality.md` | QA matrices, automated testing, CI/CD enhancements |
| `iteration_checklist.md` | Incremental delivery guidelines & Definition of Done |
| `release_plan.md` | Suggested milestone sequencing and dependencies |
| `milestone_02_next_steps.md` | Milestone 2 closure summary plus the entry plan for Milestone 3 (Frontend polish & analytics) |
| `milestone_03_frontend_polish.md` | Milestone 3 kickoff plan covering analytics endpoints, dashboard polish, and supporting checklists |
| `milestone_04_security.md` | Milestone 4 — Security & Rate Limiting (HMAC, replay, throttling, secrets, logging) |
| `milestone_05_billing.md` | Milestone 5 — Billing & Stripe Integration (checkout/portal, webhooks, entitlements) |
| `milestone_06_integrations.md` | Milestone 6 — Platform Integrations Alpha (Woo plugin, Shopify POC, SDK) |
| `milestone_07_webhooks.md` | Milestone 7 — Webhooks & Order Lifecycle (reversals, idempotency, reporting) |
| `milestone_08_launch.md` | Milestone 8 — Production Readiness & Launch |

Each epic file contains:

1. **Context** – Why the epic matters and how it ties to the MVP scope.
2. **Current status** – What exists in the codebase today.
3. **Acceptance criteria** – Detailed, testable outcomes for completion.
4. **Deliverables** – Concrete artifacts (endpoints, UI, docs) expected.
5. **Validation** – How we will prove the epic is done (manual + automated).
6. **Dependencies** – Blocking relationships across epics.

Use this backlog as the single source of truth when planning sprints or
incremental deliveries. Combine the epic-specific acceptance criteria with the
shared checklist in `iteration_checklist.md` to verify each slice is production
ready before marking it complete.
