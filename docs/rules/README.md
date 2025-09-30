# Rule Management

The `scripts/update_rules.py` helper loads jurisdiction schedules from the
version-controlled files in this directory:

- `co_periods.csv` – Colorado rate schedule (version, effective window, rate).
- `mn_threshold.json` – Minnesota threshold and fee configuration.
- [`co.md`](co.md) – Decision table and reason codes for Colorado.
- [`mn.md`](mn.md) – Decision table and reason codes for Minnesota.

Run the script after updating either file:

```bash
poetry run python scripts/update_rules.py
```

Each change writes an `audit_logs` row with `action="rules.update"` so the ops
team can trace when schedules shift. When a new Colorado period starts, the
script also trims the previous window (`rules.window_adjust`) to avoid overlap
and ensures the latest window remains open-ended. A placeholder cron entry (see
`scripts/update_rules.py`) will be wired into the deployment pipeline to execute
 nightly.
