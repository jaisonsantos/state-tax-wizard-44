# Colorado Retail Delivery Fee Decision Table

Colorado's Retail Delivery Fee applies when taxable goods are shipped to an in
state destination. The decision table below captures how the engine responds to
various scenarios and the reason codes it emits.

| Scenario | Outcome | Reason codes | Notes |
| --- | --- | --- | --- |
| Store has CO disabled | `skipped` | `CO_DISABLED` | Store settings opt out of Colorado fees. |
| Destination missing state | `skipped` | `CO_DEST_MISSING_STATE` | Caller omitted the state field. |
| Destination outside CO | `skipped` | `CO_DEST_OUT_OF_STATE` | Destination not Colorado. |
| Pickup / curbside | `skipped` | `CO_DELIVERY_METHOD_EXEMPT` | Local pickup exempt. |
| Unsupported delivery method | `skipped` | `CO_DELIVERY_METHOD_EXEMPT`, `CO_UNSUPPORTED_DELIVERY_METHOD` | Delivery method other than ship/pickup/curbside. |
| No items and no shipping | `skipped` | `CO_NO_LINE_ITEMS`, `CO_NO_TAXABLE_ITEMS` | Empty order payload. |
| Shipping charge only | `skipped` | `CO_SHIPPING_ONLY`, `CO_NO_TAXABLE_ITEMS` | Shipping charged without items. |
| Clothing-only cart | `skipped` | `CO_CLOTHING_ONLY`, `CO_NO_TAXABLE_ITEMS` | Clothing is exempt. |
| Exempt-only cart | `skipped` | `CO_ITEMS_EXEMPT`, `CO_NO_TAXABLE_ITEMS` | All items flagged as exempt. |
| Mixed exempt clothing cart | `skipped` | `CO_MIXED_EXEMPT_ITEMS`, `CO_NO_TAXABLE_ITEMS` | No taxable merchandise present. |
| Taxable items present | `applied` | `CO_HAS_TAXABLE_ITEM` (+ `CO_MARKETPLACE_SOR` when applicable) | Fee line using `rate_cents`. |
| Rule missing for CO | `skipped` | `CO_RULE_NOT_FOUND` | Configuration absent in `rule_versions`. |

`rate_cents` comes from the active `RuleVersion`. The fee is marked as absorbed
when store settings enable absorb mode, and the same decision codes persist to
`order_fees` for reporting.
