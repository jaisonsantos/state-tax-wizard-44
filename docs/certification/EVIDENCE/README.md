# Evidence Directory

This directory stores artefacts captured while validating Milestones 4 (Security) and 5 (Billing/Stripe).

## Structure

### Core artefacts

| File | Description |
| ---- | ----------- |
| `api_logs.txt` | Container logs from the latest `docker compose up` run (includes Alembic output). |
| `migrate.txt` | Transcript from `make migrate`. |
| `pytest.txt` | Result of `docker compose exec -T api pytest -q`. |
| `analytics_smoke.txt` | Output from `make analytics-smoke`. |
| `reports_smoke.txt` | Output from `make reports-smoke`. |
| `security_smoke.txt` | Output from `make security-smoke`. |
| `billing_smoke.txt` | Output from `make billing-smoke` (shows PASS or `⚠ SKIP: billing_unconfigured`). |
| _`newman_billing.txt`_ | _(Optional)_ Newman execution log for the Billing folder. Capture manually when Stripe credentials are configured; the file remains ignored by git by default. |
| `metrics_dump.txt` | Filtered `/metrics` snapshot highlighting fee, security, rate-limit, and billing counters. |

### Screenshots (`screens/`)

- `billing.png` — Billing page showing plan, usage meter, and upgrade CTA.
- `settings-hmac.png` — Settings page highlighting HMAC rotation controls.

## Usage

All evidence files are refreshed via the standard validation sequence:

```sh
make up
make migrate
make analytics-smoke reports-smoke security-smoke billing-smoke
curl -s http://localhost:8000/metrics > docs/certification/EVIDENCE/metrics_dump.txt
```

Screenshots are produced with Playwright against the running frontend (see `scripts/run-playwright.mjs` or the ad-hoc spec used during certification).

Use these artefacts when assembling PRs, certification packs, or audit summaries.
