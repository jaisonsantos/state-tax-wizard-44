# CHECKLIST – Validação M5 / Pré-M6

## Correções rápidas obrigatórias (§5)
- [x] 1. `STATUS.md` reflete comportamento real (atualizar após corrigir Stripe checkout). 【F:STATUS.md†L6-L52】
- [x] 2. Documentação aponta `hmac_secret` apenas em `store_settings`. 【F:backend/app/models/models.py†L63-L76】【F:docs/security/hmac.md†L1-L120】
- [x] 3. Replay-store com índice `(store_id, nonce)` + `expires_at` compatível e downgrade disponível. 【F:backend/alembic/versions/202510010001_ensure_processed_nonce_indexes.py†L16-L44】
- [x] 4. Contrato HMAC em `docs/security/hmac.md` usa `timestamp\nnonce\nbody`, ISO8601/epoch. 【F:docs/security/hmac.md†L9-L55】
- [x] 5. Métricas sem alta cardinalidade (sem nonce/email). 【F:backend/app/observability.py†L17-L79】
- [x] 6. Logs só com campos estáveis (`nonce_preview`, `code`, etc.). 【F:backend/app/security/hmac.py†L117-L169】
- [x] 7. Smoke harness aceita `--security-only` e lê `SMOKE_*`. 【F:backend/smoke_test.py†L680-L736】
- [x] 8. Documento de M3 marcado como shipped com rotas reais. 【F:docs/backlog/13_milestone_03_frontend_polish.md†L1-L40】

## Gate M5 (Stripe/Billing)
- [x] 1. `alembic upgrade head` roda em SQLite/Postgres (corrigir tipos UUID). 【F:docs/certification/EVIDENCE/migrate.txt†L1-L10】【F:backend/alembic/versions/202501010000_initial_schema.py†L1-L120】
- [x] 2. `/v1/billing/*` funciona sem AttributeError (corrigir `StripeService`). 【F:backend/app/services/stripe_service.py†L1-L220】【F:backend/tests/test_stripe_service.py†L1-L93】
- [x] 3. Degradação 503 sem Stripe. 【F:backend/tests/test_billing_api.py†L18-L36】
- [x] 4. Enforcement de plano em `/v1/fees/apply`. 【F:backend/app/routers/fees.py†L132-L184】
- [x] 5. Métricas billing/checkout/entitlement expostas. 【F:backend/app/observability.py†L37-L79】【F:docs/certification/EVIDENCE/metrics_dump.txt†L1-L18】
- [x] 6. `pytest` + smokes (analytics/reports/security) verdes; billing smoke PASS/skip documentado. 【F:docs/certification/EVIDENCE/pytest.txt†L1-L50】【F:docs/certification/EVIDENCE/analytics_smoke.txt†L1-L3】【F:docs/certification/EVIDENCE/reports_smoke.txt†L1-L2】【F:docs/certification/EVIDENCE/security_smoke.txt†L1-L7】【F:docs/certification/EVIDENCE/billing_smoke.txt†L1-L1】
- [x] 7. Frontend Billing consome 4 endpoints com toasts. 【F:src/pages/Billing.tsx†L1-L420】
- [x] 8. Docs/Postman/Makefile alinhados. 【F:Makefile†L50-L83】【F:docs/postman/README.md†L1-L120】【F:docs/billing/stripe.md†L1-L120】

## Gates genéricos de release
- [x] Pytest executado (`pytest -q`). 【F:docs/certification/EVIDENCE/pytest.txt†L1-L50】
- [x] Smokes principais executados (`analytics`, `reports`, `security`). 【F:docs/certification/EVIDENCE/analytics_smoke.txt†L1-L3】【F:docs/certification/EVIDENCE/reports_smoke.txt†L1-L2】【F:docs/certification/EVIDENCE/security_smoke.txt†L1-L7】
- [x] Evidência de métricas atualizada (`metrics_dump.txt`). 【F:docs/certification/EVIDENCE/metrics_dump.txt†L1-L18】
- [x] Evidências de migração mostram sucesso (atualizar após correção). 【F:docs/certification/EVIDENCE/migrate.txt†L1-L10】
- [x] Atualizar `STATUS.md`/backlog/README após correções. 【F:STATUS.md†L1-L80】【F:README.md†L40-L120】
- [x] Preparar PR com checklist completo e branch `plan/m5-validate-prepare-m6-2025-10-02`.

> Atualize este checklist durante a execução do FIX_SLICE; todos os itens devem estar marcados antes de declarar M5 concluída e iniciar o planejamento detalhado da M6.

