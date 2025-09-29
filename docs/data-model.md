# Data Model Reference

This guide summarizes the relational schema created by Alembic migrations for
the Retail Delivery Fee service. All tables live in the primary PostgreSQL
schema.

## Entity overview

| Table | Purpose | Primary Key | Notable Columns | Relationships |
| ----- | ------- | ----------- | --------------- | -------------- |
| `stores` | Registered merchant storefronts. | `id` (`UUID`) | `platform`, `domain`, `country`, `state`, `created_at` | One-to-one with `store_settings`; one-to-many with `subscriptions`, `order_fees`; many-to-many with `users` via `user_stores`. |
| `store_settings` | Feature flags & labels controlling how fees render for a store. | `store_id` (`UUID`) | `enable_mn`, `enable_co`, `absorb_fee`, `label_override`, `plan` | Shares primary key with `stores` (`store_id` FK). |
| `rule_versions` | Jurisdiction-specific fee configuration with effective dating. | `id` (`INT`) | `jurisdiction`, `version`, `effective_from`, `effective_to`, `params` (`JSON`) | Read by fee service; independent table. |
| `order_fees` | Persisted fee lines applied to checkout orders. | `id` (`UUID`) | `store_id`, `order_id`, `jurisdiction`, `amount_cents`, `delivery_method`, `absorbed`, `rule_version`, `reason_codes` (`JSON`) | Many-to-one with `stores`; unique constraint on (`store_id`, `order_id`, `jurisdiction`). |
| `audit_logs` | Immutable audit trail of fee actions. | `id` (`UUID`) | `ts`, `actor`, `action`, `payload` (`JSON`) | Payload embeds `store_id` for filtering. |
| `subscriptions` | Billing/subscription metadata for stores. | `id` (`UUID`) | `provider`, `plan`, `status`, `trial_end`, `current_period_end` | Many-to-one with `stores`. |
| `users` | Authenticated operators of the SaaS product. | `id` (`UUID`) | `email`, `created_at` | Many-to-many with `stores` via `user_stores`. |
| `user_stores` | Join table linking users to stores they can manage. | Composite (`user_id`, `store_id`) | `created_at` | Foreign keys to `users.id` and `stores.id`; uniqueness enforced by PK. |

## Relationships

- **Stores ↔ Users**: Each user can access multiple stores and vice versa via
  `user_stores`. The login flow automatically ensures a demo store link exists.
- **Stores ↔ Settings/Subscriptions**: `store_settings` and `subscriptions`
  capture configuration and plan metadata for each store. They cascade on store
  creation.
- **Stores ↔ Order Fees/Audit Logs**: Orders applied through the API generate
  `order_fees` rows (enforced to one per jurisdiction) and corresponding
  `audit_logs` events with payload context.
- **Rule versions**: Queried during quote/apply to determine fee amounts. The
  `params` JSON stores jurisdiction-specific thresholds, rate cents, and
  exemptions to avoid schema churn.

## Seed expectations

Running `make seed` guarantees:

- Two demo stores (`store_demo_1` in MN and `store_demo_2` in CO) complete with
  settings and subscription rows.
- Current rule versions for Minnesota (`MN-2024`) and Colorado (`CO-2025H1`).
- Sample subscriptions to exercise billing reports.

These records enable the smoke test and manual QA scenarios without additional
setup.
