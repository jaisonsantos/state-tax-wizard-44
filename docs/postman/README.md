# Postman & Newman Collection Guide

This guide explains how to run the State Tax Wizard API collection from Postman or Newman so you can validate the HTTP surface area alongside automated checks.

## Prerequisites

- Running instance of the backend (e.g., via `make dev` or `uvicorn backend.app.main:app --reload`).
- Postman Desktop/CLI **or** Node.js 18+ with [`newman`](https://www.npmjs.com/package/newman) installed globally:

  ```sh
  npm install --global newman
  ```
- Network access from your workstation to the API host defined in `{{base_url}}`.

## Environment variables

The collection expects the following collection variables:

| Variable | Purpose | Default |
| --- | --- | --- |
| `base_url` | Root URL for the API | `http://localhost:8000` |
| `token` | JWT captured after authenticating | _set by login script_ |
| `store_id` | Active store for fee scenarios | _set by login script_ |
| `evidence_dir` | Directory where Newman should write report artifacts | _optional_; used to echo artifact paths into the CI logs |
| `hmac_secret` | Shared secret used to sign `/v1/fees/apply` requests; auto-updated by the rotation request | `demo-hmac-secret` (matches seed data) |
| `hmac_timestamp_override` | Forces a specific timestamp for negative tests | _optional_ |
| `hmac_nonce_override` | Forces a specific nonce to simulate replays | _optional_ |
| `billing_plan_tier` | Plan tier used by the Billing folder (starter/pro/plus) | `pro` |

When running in Postman, set `base_url` manually if your API is not on `localhost`. The login request will automatically populate `token` and `store_id` via the test script. For Newman, you can override defaults with an environment JSON file or `--env-var` flags.

## Execution order

1. **Auth / Login** — generates a JWT and seeds the collection variables.
2. **Monitoring** requests — confirm health checks and metrics respond without authentication.
3. **Protected endpoints** — run quote/apply/audit/report requests after the login step so the `Authorization` header is populated.
4. **Fees / Rotate HMAC secret** — optionally rotate the secret after validating `Apply fees`; the test script captures the one-time `hmac_secret` response and updates collection variables.
5. **Analytics** — call **Analytics / Overview** to capture KPI cards, cursor metadata, and Prometheus counter snapshots. When `evidence_dir` is set the test logs `analytics-overview.json` so artifacts can be archived.
6. **Reports & billing** — use the previously captured `store_id` to scope report generation and billing previews. Reports assert attachment filenames for deterministic downloads, while the Billing folder exercises entitlements, usage, checkout, portal, and webhook samples. When Stripe credentials are missing the tests emit `BILLING_SKIPPED=true` and exit gracefully.
7. **Auth / Logout** — revoke the active session when you finish to validate the new `/api/auth/logout` endpoint and clear cached `token`/`store_id` variables for the next run.

Running requests in this sequence ensures dependent variables are always available for downstream calls. The **Analytics** folder exercises `/v1/analytics/overview` and the **Reports** folder includes CSV and JSON variants with test scripts that assert the `Content-Type` header matches the requested format and echo the evidence directory so Newman artifacts can be archived.

## Evidence logging & automation

When executing the collection in CI, set `--env-var evidence_dir=<path>` so the analytics and report scripts can log where JSON/CSV payloads are stored. Each test writes a message such as `evidence_path=<dir>/analytics-overview.json` or `evidence_path=<dir>/mn-summary.json` to the Newman console for traceability. The logout script also removes `token` and `store_id`, which keeps chained Newman jobs from accidentally reusing stale credentials. The same variable can point to an artifact directory inside your CI workspace.

## Negative checks

To validate error handling, exercise at least the following scenarios after a successful login run:
- Re-run a protected request (e.g., **Fees / Quote**) with the `Authorization` header removed to confirm a `401 Unauthorized` response.
- Call **Auth / Login** with an invalid password to ensure the API returns the expected `401` error payload and does not overwrite the cached token.
- For idempotent operations (such as fee application), repeat the request with the same payload and verify the response indicates no duplicate fee records were created.
- Exercise **Reports / Minnesota summary (invalid format)** to validate the `422` response body and capture evidence that unsupported formats are rejected and audited.
- In the **Fees / Apply fees (invalid HMAC)** request, leave `hmac_secret` untouched so the pre-request script generates an intentionally corrupted signature and verify a `403` response with `detail.code = invalid_signature`.
- Exercise the dedicated negative requests — **Fees / Apply fees (stale timestamp)** and **Fees / Apply fees (replay)** — which auto-generate signatures using the exact request body to confirm `401`/`409` responses without manual overrides.
- After running **Fees / Rotate HMAC secret**, resend an apply request with the previously logged signature to confirm the API returns `detail.code = invalid_signature`.
- You can still force specific values via `hmac_timestamp_override` or `hmac_nonce_override` before calling **Fees / Apply fees (HMAC)** if you need custom test cases. Expect `detail.code = stale_timestamp` for an expired timestamp and `detail.code = replay_detected` when the same nonce is reused.
- Override `billing_plan_tier` to an unsupported value (e.g., `enterprise`) in the Billing folder to confirm `400 Bad Request`, and toggle Stripe variables off to document the `503 billing_unconfigured` skip path.

Document the responses in your test evidence to show both happy-path and guardrail coverage.

## Example Newman command

Run the full collection against a local backend using Newman:

```sh
newman run docs/postman/state-tax-wizard.postman_collection.json \
  --env-var base_url=http://localhost:8000 \
  --reporters cli,junit \
  --reporter-junit-export=reports/newman/state-tax-wizard.xml
```

This command overrides the `base_url`, writes CLI output, and exports a JUnit report that can be archived in CI.
