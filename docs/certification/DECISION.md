# Certification Decision – Milestone 5

- `LAST_COMPLETED_MILESTONE`: **M5 – Billing & Stripe Integration** 【F:docs/backlog/15_milestone_05_billing.md†L1-L32】
- `CURRENT_ACTIVE_MILESTONE`: **M6 – Platform Integrations Alpha** 【F:docs/backlog/16_milestone_06_integrations.md†L1-L160】

## Decision
- **M5: PASS**
  - `alembic upgrade head` executa integralmente em SQLite usando o novo tipo `GUID` portátil; mesma revisão continua válida para PostgreSQL. 【F:docs/certification/EVIDENCE/migrate.txt†L1-L10】【F:backend/alembic/versions/202501010000_initial_schema.py†L1-L120】
  - `StripeService` resolve `contact_email`, sincroniza metadados e cobre cenários sem usuários, com testes unitários dedicados. 【F:backend/app/services/stripe_service.py†L1-L220】【F:backend/tests/test_stripe_service.py†L1-L93】
  - `pytest -q` e smokes (analytics, reports, security) passaram; billing smoke reporta `billing_unconfigured` quando chaves Stripe não estão definidas, confirmando degradação graciosa. 【F:docs/certification/EVIDENCE/pytest.txt†L1-L50】【F:docs/certification/EVIDENCE/analytics_smoke.txt†L1-L3】【F:docs/certification/EVIDENCE/reports_smoke.txt†L1-L2】【F:docs/certification/EVIDENCE/security_smoke.txt†L1-L7】【F:docs/certification/EVIDENCE/billing_smoke.txt†L1-L1】
  - Métricas `billing_events_total`, `hmac_*`, `rate_limit_throttles_total` e `fees_*` seguem expostas no `/metrics`, alinhadas à observabilidade documentada. 【F:docs/certification/EVIDENCE/metrics_dump.txt†L1-L18】【F:backend/app/observability.py†L1-L96】

## NEXT_SLICE – Milestone 6 (Platform Integrations Alpha)
1. **WooCommerce Plugin** – Gerar client HMAC, hooks de fee/cart/order e painel administrativo com logs. Publicar pacote ZIP e documentação de instalação. 【F:docs/backlog/16_milestone_06_integrations.md†L12-L86】
2. **Shopify App POC** – Implementar app proxy + produto de fee oculto, sincronizando com `/v1/fees/quote/apply` via SDK Node. 【F:docs/backlog/16_milestone_06_integrations.md†L87-L160】
3. **Tooling & QA** – Adicionar scripts de build/teste (Makefile/CI) para plugins, cenários Postman/Newman cobrindo assinaturas Woo/Shopify, e atualizar docs com guias de onboarding e métricas específicas. 【F:docs/backlog/16_milestone_06_integrations.md†L12-L160】

