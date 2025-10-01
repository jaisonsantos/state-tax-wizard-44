# Consistency Patch Log

## Applied updates
- Documented the new Redis-backed rate limiter and HMAC rotation workflow in `docs/security/hmac.md`, including retry semantics and audit expectations. 【F:docs/security/hmac.md†L1-L120】
- Added `rate_limit_throttles_total` to the observability catalog so dashboards and alerts cover throttling events. 【F:docs/security/observability.md†L1-L160】
- Extended the Postman collection with a **Rotate HMAC secret** request that captures the one-time secret response and resets signing variables. 【F:docs/postman/state-tax-wizard.postman_collection.json†L470-L540】
- Introduced `anti-drift`/`ci-anti-drift` Makefile targets to keep header/secret scans and the security smoke job wired into CI. 【F:Makefile†L1-L110】
- Consolidated documentation into `docs/` by relocating certification artifacts to `docs/certification/`, moving evidence under `docs/certification/EVIDENCE/`, and gathering security guides under `docs/security/`. 【F:docs/certification/CERTIFICATION.md†L1-L80】【F:docs/security/ui-guide.md†L1-L80】
- Renamed backlog milestones/releases to `00_*`/`1X_*` format and added cross-links so navigation stays coherent after the restructure. 【F:docs/backlog/README.md†L9-L32】【F:docs/backlog/14_milestone_04_security.md†L1-L12】

No additional drift detected between code, docs, and tooling after these updates.
