# Rule Management

The `scripts/update_rules.py` helper loads jurisdiction schedules from the
version-controlled files in this directory:

- `co_periods.csv` – Colorado rate schedule (version, effective window, rate).
- `mn_threshold.json` – Minnesota threshold and fee configuration.

Run the script after updating either file:

```bash
poetry run python scripts/update_rules.py
```

Each change writes an `audit_logs` row with `action="rules.update"` so the ops
team can trace when schedules shift. A placeholder cron entry (see
`scripts/update_rules.py`) will be wired into the deployment pipeline to execute
 nightly.
