# Minnesota Summary Report

The `/v1/reports/mn/summary` endpoint returns a compact JSON payload used by the
ops dashboard and monthly filings. The response always includes the following
fields:

```json
{
  "tx_count_threshold_met": 0,
  "fee_total_cents": 0,
  "absorbed_count": 0,
  "shown_count": 0
}
```

- `tx_count_threshold_met` – net count of transactions that triggered the MN
  fee. Reversals subtract from the total so cancelled orders no longer count.
- `fee_total_cents` – total fee amount after subtracting any reversals.
- `absorbed_count` – number of applied fees hidden from the shopper. Reversals
  decrease this tally if the original fee was absorbed.
- `shown_count` – visible fee lines after accounting for reversals.

When CSV output is requested (`format=csv`) the response matches the golden
files in `backend/tests/fixtures/reports/`, ensuring contract stability for
partner integrations.
