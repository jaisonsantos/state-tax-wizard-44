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

When running in Postman, set `base_url` manually if your API is not on `localhost`. The login request will automatically populate `token` and `store_id` via the test script. For Newman, you can override defaults with an environment JSON file or `--env-var` flags.

## Execution order
1. **Auth / Login** — generates a JWT and seeds the collection variables.
2. **Monitoring** requests — confirm health checks and metrics respond without authentication.
3. **Protected endpoints** — run quote/apply/audit/report requests after the login step so the `Authorization` header is populated.
4. **Reports & billing** — use the previously captured `store_id` to scope report generation or billing previews. The MN JSON request now asserts that the API returns an attachment filename, ensuring browsers save the export predictably.
5. **Auth / Logout** — revoke the active session when you finish to validate the new `/api/auth/logout` endpoint and clear cached `token`/`store_id` variables for the next run.

Running requests in this sequence ensures dependent variables are always available for downstream calls. The **Reports** folder now includes CSV and JSON variants with test scripts that assert the `Content-Type` header matches the requested format and echo the evidence directory so Newman artifacts can be archived.

## Evidence logging & automation

When executing the collection in CI, set `--env-var evidence_dir=<path>` so the report scripts can log where CSV/JSON payloads are stored. Each report test writes a message such as `evidence_path=<dir>/mn-summary.json` to the Newman console for traceability. The logout script also removes `token` and `store_id`, which keeps chained Newman jobs from accidentally reusing stale credentials. The same variable can point to an artifact directory inside your CI workspace.

## Negative checks
To validate error handling, exercise at least the following scenarios after a successful login run:
- Re-run a protected request (e.g., **Fees / Quote**) with the `Authorization` header removed to confirm a `401 Unauthorized` response.
- Call **Auth / Login** with an invalid password to ensure the API returns the expected `401` error payload and does not overwrite the cached token.
- For idempotent operations (such as fee application), repeat the request with the same payload and verify the response indicates no duplicate fee records were created.
- Exercise **Reports / Minnesota summary (invalid format)** to validate the `422` response body and capture evidence that unsupported formats are rejected and audited.

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
