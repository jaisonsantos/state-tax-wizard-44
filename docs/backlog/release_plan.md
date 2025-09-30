# MVP Release Plan — Iterative Milestones

This plan sequences the backlog epics into achievable increments. Each
milestone is expected to take 1–2 sprints (2 weeks) depending on team size and
must satisfy the Definition of Done outlined in `iteration_checklist.md` before
closing.

## Milestone 0 — Foundations (Week 0)
- ✅ Epic 01 complete (`docs/environment.md`, `docs/data-model.md`,
  `docs/observability.md`, and `make smoke`).
- Establish engineering rituals (code review checklist referencing backlog).

## Milestone 1 — Secure Core APIs (Weeks 1–2)
- Deliver Epic 02 (auth/tenant enforcement).
- ✅ Store settings integration (Epic 03) live via `/v1/stores/{id}/settings`, and MN/CO reason codes expanded in July 2024 rollout.
- Update frontend (Epic 05) for store selector to leverage new auth claims.
- ✅ Session management hardened: JWTs now persist to `session_tokens`, `/api/auth/logout` revokes active sessions, and the frontend exposes an account menu for explicit sign-out.

## Milestone 2 — Reporting Confidence (Weeks 3–4)
- ✅ Finish Epic 03 remaining scope (rule updater, metrics, docs) — delivered via `scripts/update_rules.py`, latency histogram labels, and updated MN/CO tables.
- ✅ Epic 04 telemetry and UX polished: report exports now emit audit logs/metrics, the reports page surfaces live history without unsupported formats, and Playwright/download smokes are wired behind an opt-in flag.
- Update QA checklist (Epic 10 partial) to cover reporting cases.

## Milestone 3 — Frontend Polish & Analytics (Weeks 5–6)
- Complete Epic 05 (settings persistence, dashboard metrics, UX polish).
- Extend Epic 10 with Playwright smoke suite covering new flows.

## Milestone 4 — Security & Billing Readiness (Weeks 7–8)
- Implement Epic 08 (HMAC, rate limiting, secrets playbook).
- Kick off Epic 07 (Stripe integration) focusing on customer creation and
  checkout flows.

## Milestone 5 — Integrations Alpha (Weeks 9–10)
- Build WooCommerce plugin (Epic 06 partial) and internal testing guide.
- Ship Shopify POC (Epic 06 partial) for partner feedback.
- Expand QA checklist with integration scenarios (Epic 10).

## Milestone 6 — Lifecycle & Monetization (Weeks 11–12)
- Finish Epic 07 (webhooks, entitlements enforcement).
- Complete Epic 09 (refunds, reversals, reporting alignment).
- Harden security monitoring (Epic 08 logging counters).

## Milestone 7 — Launch Readiness (Weeks 13–14)
- Finalize Epic 06 remaining scope (packaging, docs).
- Close Epic 10 (dependency scanning, release automation).
- Conduct full release dry-run using smoke + e2e + QA checklist and archive the
  results per the exit review checklist.

Each milestone should conclude with a stakeholder review, demo, and update to
these documents noting completion status.
