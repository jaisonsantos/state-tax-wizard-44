# Minnesota Delivery Fee Decision Table

The Minnesota Road Improvement and Food Delivery Fee is assessed on taxable
shipments that meet the configured threshold. The table below summarizes the
engine outcomes and reason codes returned by `/api/v1/fees/quote` and
`/api/v1/fees/apply`.

| Scenario | Outcome | Reason codes | Notes |
| --- | --- | --- | --- |
| Store has MN disabled | `skipped` | `MN_DISABLED` | Store settings opt out of Minnesota fees. |
| Destination missing state | `skipped` | `MN_DEST_MISSING_STATE` | Caller omitted the state field. |
| Destination outside MN | `skipped` | `MN_DEST_OUT_OF_STATE` | Destination not Minnesota. |
| Pickup / curbside | `skipped` | `MN_BOPIS_EXEMPT` | Buy-online-pickup-in-store exempt. |
| Unsupported delivery method | `skipped` | `MN_DELIVERY_METHOD_EXEMPT`, `MN_UNSUPPORTED_DELIVERY_METHOD` | Delivery method other than ship/pickup/curbside. |
| No line items and no shipping | `skipped` | `MN_NO_LINE_ITEMS`, `MN_NO_TAXABLE_ITEMS` | Empty order payload. |
| Clothing-only cart | `skipped` | `MN_CLOTHING_ONLY`, `MN_NO_TAXABLE_ITEMS` | Clothing is exempt from the fee. |
| Exempt-only cart | `skipped` | `MN_TAX_EXEMPT_ORDER`, `MN_NO_TAXABLE_ITEMS` | All items flagged as exempt. |
| Mixed exempt clothing cart | `skipped` | `MN_MIXED_EXEMPT_ITEMS`, `MN_NO_TAXABLE_ITEMS` | No taxable merchandise present. |
| Taxable subtotal below threshold | `skipped` | `MN_UNDER_THRESHOLD`, `MN_TAXABLE_SUBTOTAL_UNDER_THRESHOLD` | Taxable subtotal + shipping below threshold. |
| Taxable subtotal at/above threshold | `applied` | `MN_THRESHOLD_MET` | Fee line of `fee_cents` added to the response. |
| Rule missing for MN | `skipped` | `MN_RULE_NOT_FOUND` | Configuration absent in `rule_versions`. |

`threshold_cents` and `fee_cents` are sourced from the active `RuleVersion`
record. Orders inherit the `absorbed` flag from store settings when a fee line
is applied.
