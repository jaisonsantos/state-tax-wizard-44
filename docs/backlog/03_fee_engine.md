# Epic 03 — Fee Engine, Quote & Apply APIs

## Context
The fee engine is the core differentiator. It must evaluate Minnesota and
Colorado delivery fees, support idempotent application, and emit rich audit
trails. The MVP already implements the basic logic but needs hardening and
extensibility.

## Current Status
- ✅ `POST /api/v1/fees/quote` calculates MN/CO fees with seeded rule versions.
- ✅ `POST /api/v1/fees/apply` persists fees idempotently per jurisdiction.
- ✅ Audit logs capture fee application events with request payloads.
- ✅ Rule management automated via `scripts/update_rules.py`, including Colorado window reconciliation and Minnesota change auditing.
- ✅ Reason codes expanded to cover exemptions, marketplace remittance, and no-taxable edge cases across MN/CO.
- ✅ Absorb fee settings persist through store settings endpoints and drive fee absorption.
- ✅ API honors `store_settings` toggles, returns granular reason codes (including
  exemptions), and surfaces an `absorbed` flag for hidden fees.
- ✅ `decision_latency_ms` histogram labels decisions by route, jurisdiction, and outcome for observability dashboards.

## Acceptance Criteria
1. **Rule Version Service**: Background job or CLI to ingest new CO periods and
   flag MN changes. Rules endpoint exposes `effective_from`/`effective_to` and
   `is_latest` boolean.
2. **Settings Integration**: `/api/v1/fees/quote` honors `store_settings`
   toggles (enable_mn, enable_co, absorb_fee) and returns `absorbed` flag when
   fees should be hidden from the shopper.
3. **Reason Code Expansion**: Quote response enumerates explicit reasons for
   exemptions (e.g., `MN_UNDER_THRESHOLD`, `CO_NO_TAXABLE_ITEMS`).
4. **Latency Metrics**: `decision_latency_ms` histogram records both quote and
   apply durations with labels for jurisdiction and outcome (applied/skipped).
5. **Documentation**: Decision tables for MN and CO (mirroring QA matrix) live
   under `docs/rules/` with examples.

## Deliverables
- Updated services (`services/fees.py`, etc.) and schemas for new fields.
- Migration if new columns required (e.g., storing absorb flag in `order_fees`).
- CLI/cron script for rule ingestion (`scripts/update_rules.py`).
- Documentation in `docs/rules/mn.md` and `docs/rules/co.md`.

## Validation
- Unit tests covering each branch of the decision tables.
- End-to-end test ensuring absorb_fee true hides line items but still persists.
- Observability validated via `curl /metrics` showing updated histograms.

## Definition of Done
- Rule ingestion job scheduled (or documented manual run) with fixtures proving
  a new Colorado period flows from database → quote/apply → reports. ✅ (Documented via the July 2024 CO window import using `scripts/update_rules.py`.)
- Absorb fee behavior recorded in audit logs and persisted in `order_fees`
  schema, with migrations reviewed and rolled out. ✅
- Reason code catalog updated in documentation and surfaced in frontend/API
  schema with contract tests guarding against regressions. ✅
- Metrics dashboard updated to include jurisdiction/outcome labels for
  `decision_latency_ms`, and smoke tests confirm counters increment. ✅
- Epic status annotated with the date/time of the last rule refresh validation. ✅ Updated July 2024 following the CO-2025H1 schedule load.

## Dependencies
- Requires Epic 02 authorization to ensure store-specific settings are respected.
- Coordinates with Epic 05 (frontend) to display new reason codes and absorb
  behavior.
