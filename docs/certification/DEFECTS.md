# Defects & Improvement Opportunities

## 1. Operations playbook for secret & Redis config (Severity: Low)

- **Description:** Infrastructure docs still need to explain how to provide `REDIS_URL` and rotated HMAC secrets in non-demo environments so operators can reproduce the smoke/CI setup.
- **Evidence:** README/Postman guides reference the secrets but do not prescribe vault/backfill steps. 【F:README.md†L80-L130】【F:docs/postman/README.md†L1-L140】
- **Recommendation:** Extend deployment docs with environment variable tables, credential storage guidance, and a reminder to rotate the secret after provisioning.

---

**Resolved**
- Distributed rate limiting now uses Redis with Prometheus counters and tests, closing the prior in-memory gap. 【F:backend/app/security/rate_limit.py†L1-L146】【F:backend/tests/test_rate_limiter.py†L1-L40】
- Timestamp handling across the fee service and tests is fully timezone-aware (`datetime.now(timezone.utc)`), eliminating the naive UTC defect noted previously. 【F:backend/app/services/fee_service.py†L1-L220】【F:backend/tests/test_time_awareness.py†L1-L30】
