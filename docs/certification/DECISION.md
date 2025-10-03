# Certification Decision – Milestone 5

- `LAST_COMPLETED_MILESTONE`: **M5 – Billing & Stripe Integration** 【F:docs/backlog/15_milestone_05_billing.md†L1-L32】
- `CURRENT_ACTIVE_MILESTONE`: **M6 – Platform Integrations Alpha** 【F:docs/backlog/16_milestone_06_integrations.md†L1-L160】

## Decision
- **M5: PASS**
  - Portal API retorna `portal_session_id` e responde `400 stripe_customer_missing` quando a loja não possui metadados Stripe; testes de unidade cobrem o caminho feliz e o erro. 【F:backend/app/schema/billing.py†L45-L52】【F:backend/app/routers/billing.py†L150-L177】【F:backend/tests/test_billing_api.py†L130-L196】
  - `pytest -q` (61 testes) e smokes (`analytics`, `reports`, `security`) executados em Python 3.12 com evidências arquivadas; billing smoke registra SKIP controlado sem chaves Stripe. 【F:docs/certification/EVIDENCE/pytest.txt†L1-L40】【F:docs/certification/EVIDENCE/security_smoke.txt†L1-L7】【F:docs/certification/EVIDENCE/billing_smoke.txt†L1-L1】
  - Migração SQLite (`migrate.txt`), logs de boot (`api_logs.txt`) e métricas (`metrics_dump.txt`) foram atualizados após o seed determinístico. 【F:docs/certification/EVIDENCE/migrate.txt†L1-L10】【F:docs/certification/EVIDENCE/api_logs.txt†L1-L8】【F:docs/certification/EVIDENCE/metrics_dump.txt†L1-L30】

## NEXT_SLICE – Milestone 6 (Platform Integrations Alpha)
1. **WooCommerce Plugin** – entregar plugin PHP com assinatura HMAC compartilhando helpers do SDK e registrar logs/metadados no Woo admin. 【F:docs/backlog/16_milestone_06_integrations.md†L12-L86】
2. **Shopify App POC** – implementar app proxy/Functions para injetar o fee product, persistir ordens via `/v1/fees/*` e medir falhas. 【F:docs/backlog/16_milestone_06_integrations.md†L87-L160】
3. **Tooling & QA** – novos smokes `integrations`, coleção Postman "Integrations", métricas `integrations_*`, documentação e ajustes de CI/Makefile. 【F:docs/backlog/16_milestone_06_integrations.md†L12-L160】
