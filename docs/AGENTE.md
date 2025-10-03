# AGENTE – Validação M5 e Preparação M6

## Mapa do repositório
- `backend/app/routers/` – FastAPI routers para auth, fees, analytics, billing, etc. 【F:backend/app/routers/billing.py†L1-L220】【F:backend/app/routers/fees.py†L1-L220】
- `backend/app/services/` – Serviços de negócio (Stripe, entitlements, webhooks, fee engine, segurança). 【F:backend/app/services/stripe_service.py†L100-L151】【F:backend/app/services/entitlement_service.py†L1-L200】
- `backend/app/security/` – HMAC e rate limiting, com métricas de baixa cardinalidade. 【F:backend/app/security/hmac.py†L83-L179】
- `backend/app/models/models.py` – ORM + tipos utilitários (`GUID`) e relacionamentos. 【F:backend/app/models/models.py†L44-L154】
- `backend/app/observability.py` – Counters/histogramas Prometheus e loggers estruturados. 【F:backend/app/observability.py†L1-L104】
- `backend/alembic/versions/` – Migrações (Stripe/billing: `202510020001`, `202510020002`). 【F:backend/alembic/versions/202510020001_billing_stripe_integration.py†L1-L60】【F:backend/alembic/versions/202510020002_add_subscription_period_start.py†L1-L60】
- `backend/tests/` – Pytest (billing, entitlements, segurança, analytics). 【F:backend/tests/test_billing_api.py†L1-L200】【F:backend/tests/test_entitlements.py†L121-L154】
- `backend/smoke_test.py` – Harness com flags `--analytics-only`, `--reports-only`, `--security-only`, `--billing-only`. 【F:backend/smoke_test.py†L680-L736】
- `src/lib/api.ts` – Cliente REST tipado consumindo billing/fees/reports. 【F:src/lib/api.ts†L500-L612】
- `src/pages/Billing.tsx` – Tela de billing/trial/usage/upgrade. 【F:src/pages/Billing.tsx†L1-L420】
- `docs/backlog/` – Roadmap e notas por milestone (M5/M6). 【F:docs/backlog/15_milestone_05_billing.md†L1-L32】【F:docs/backlog/16_milestone_06_integrations.md†L1-L120】
- `docs/security/` – Guia HMAC, runbooks, observabilidade. 【F:docs/security/hmac.md†L1-L120】【F:docs/security/environment.md†L1-L160】
- `docs/postman/` – Coleção + README da collection. 【F:docs/postman/README.md†L1-L120】
- `docs/certification/EVIDENCE/` – Evidências limitadas (logs tail/head 200) produzidas a cada validação.
- `Makefile` – Alvos `migrate`, `seed`, `analytics-smoke`, `reports-smoke`, `security-smoke`, `billing-smoke`, `metrics`. 【F:Makefile†L1-L90】

## Fontes de verdade (ordem de autoridade)
1. Código de produção + testes automatizados.
2. `STATUS.md` (estado declarado + Recommended Next Step). 【F:STATUS.md†L1-L120】
3. `docs/backlog/00_release_plan.md` (roadmap consolidado). 【F:docs/backlog/00_release_plan.md†L1-L120】
4. Documentos de milestone em `docs/backlog/milestone_*` (Status Update / Remaining Enhancements). 【F:docs/backlog/15_milestone_05_billing.md†L1-L32】
5. `README.md` (onboarding, runbooks resumidos). 【F:README.md†L1-L180】

## Validação da Milestone 5 (Billing/Stripe)
1. **Setup**
   - Python 3.11 + `pip install -r backend/requirements.txt`.
   - Defina `APP_ENV=dev` e `DATABASE_URL` (PostgreSQL ou SQLite). O tipo `GUID()` garante compatibilidade multi-dialeto.

2. **Migrações**
   - `cd backend`
   - `DATABASE_URL=<conn>` `alembic upgrade head`
   - Colete saída (`tail -n 200`) em `docs/certification/EVIDENCE/migrate.txt`.

3. **Aplicação / Logs**
   - `APP_ENV=dev DATABASE_URL=<conn> uvicorn app.main:app --host 127.0.0.1 --port 8000`
   - Capture boot (`tail -n 200`) em `docs/certification/EVIDENCE/api_logs.txt`.

4. **Evidências de métricas**
   - `curl -s http://127.0.0.1:8000/metrics | grep -E "(rate_limit|hmac|billing|fees|report)" | head -n 50 > docs/certification/EVIDENCE/metrics_dump.txt`

5. **Testes automatizados**
   - `pytest -q` (root em `backend/`). 【F:docs/certification/EVIDENCE/pytest.txt†L1-L50】
   - `python smoke_test.py --analytics-only` / `--reports-only` / `--billing-only` / padrão (gera `analytics_smoke.txt`, etc.). 【F:docs/certification/EVIDENCE/analytics_smoke.txt†L1-L3】【F:docs/certification/EVIDENCE/reports_smoke.txt†L1-L2】【F:docs/certification/EVIDENCE/security_smoke.txt†L1-L7】【F:docs/certification/EVIDENCE/billing_smoke.txt†L1-L1】

6. **Limites de evidência**
   - Sempre sobrescreva arquivos em `docs/certification/EVIDENCE/` com `head -n 200` ou `tail -n 200`.
   - Não exceder 512 KB. Se algum arquivo crescer, resuma e ajuste `.gitignore` (`docs/certification/EVIDENCE/*_scan*.txt`).

## Gate M5 – Checklist
- [x] **1. Migrações Stripe prontas / `alembic upgrade head` limpa** – `GUID()` portátil cobre SQLite e PostgreSQL; evidência registrada no último upgrade. 【F:backend/alembic/versions/202501010000_initial_schema.py†L1-L120】【F:docs/certification/EVIDENCE/migrate.txt†L1-L10】
- [x] **2. `/v1/billing/*` íntegros** – `StripeService` resolve `contact_email`, sincroniza `Store`/`Subscription` e tem cobertura dedicada. 【F:backend/app/services/stripe_service.py†L1-L220】【F:backend/tests/test_stripe_service.py†L1-L93】
- [x] **3. Degradação sem Stripe (503 `billing_unconfigured`)** – Teste cobre entitlements `503`. 【F:backend/tests/test_billing_api.py†L18-L36】
- [x] **4. Enforcement de plano em `/v1/fees/apply`** – Chamada `EntitlementService.enforce_transaction_limit` condicionada a Stripe configurado. 【F:backend/app/routers/fees.py†L132-L184】
- [x] **5. Observabilidade billing/checkout/entitlements** – Counters `billing_events_total`, `checkout_sessions_created_total`, `entitlement_denials_total`. 【F:backend/app/observability.py†L37-L79】【F:docs/certification/EVIDENCE/metrics_dump.txt†L1-L18】
- [x] **6. Testes & smokes** – `pytest -q` verde, smokes analytics/reports/security verdes, billing smoke em modo skip com mensagem clara. 【F:docs/certification/EVIDENCE/analytics_smoke.txt†L1-L3】【F:docs/certification/EVIDENCE/reports_smoke.txt†L1-L2】【F:docs/certification/EVIDENCE/security_smoke.txt†L1-L7】【F:docs/certification/EVIDENCE/billing_smoke.txt†L1-L1】
- [x] **7. Frontend Billing.tsx** – Consome entitlements/usage/checkout/portal com toasts e trial UI. 【F:src/pages/Billing.tsx†L1-L420】
- [x] **8. Docs/Postman/Makefile alinhados** – Makefile expõe alvos, README/Postman documentam skip, guia Stripe atualizado. 【F:Makefile†L50-L83】【F:docs/postman/README.md†L1-L120】【F:docs/postman/state-tax-wizard.postman_collection.json†L940-L1259】【F:docs/billing/stripe.md†L1-L120】

> **Resultado:** M5 **concluída** – todos os gates executados com sucesso e evidências atualizadas.

## Correções rápidas obrigatórias (§5) – Status
- [x] 1. `STATUS.md` verídico – Documento alinhado com novo `contact_email` e migrações portáveis. 【F:STATUS.md†L6-L52】
- [x] 2. Segredo HMAC reside em `store_settings` (docs ok). 【F:backend/app/models/models.py†L63-L76】【F:docs/security/hmac.md†L1-L120】
- [x] 3. Replay-store com índice `(store_id, nonce)` + `expires_at` e TTL oportunista, compatível Postgres/SQLite, downgrade presente. 【F:backend/alembic/versions/202510010001_ensure_processed_nonce_indexes.py†L16-L44】【F:backend/app/security/hmac.py†L83-L179】
- [x] 4. Contrato HMAC documentado (`timestamp\nnonce\nbody`, ISO 8601/epoch). 【F:docs/security/hmac.md†L9-L55】
- [x] 5. Métricas de baixa cardinalidade (sem nonce/email) – Counters usam `store_id`, `event`, `plan`, sem dados sensíveis. 【F:backend/app/observability.py†L17-L79】
- [x] 6. Logs seguros (usam `nonce_preview`, códigos estáveis). 【F:backend/app/security/hmac.py†L117-L169】
- [x] 7. Smoke flags presentes (`--security-only`, leitura de env `SMOKE_*`). 【F:backend/smoke_test.py†L680-L736】
- [x] 8. M3 doc marca “shipped” com rotas reais. 【F:docs/backlog/13_milestone_03_frontend_polish.md†L1-L40】

## Plano resumido para M6 (Integrations Alpha)
1. **WooCommerce Plugin** (1.5–2 dias)
   - Implementar plugin PHP com hooks de fee/order, client HMAC e painel de settings/logs. 【F:docs/backlog/16_milestone_06_integrations.md†L12-L86】
   - Criar testes PHPUnit + `package.sh` para gerar ZIP distribuível.
   - Riscos: compatibilidade WooCommerce; mitigar com matriz de versões documentada.

2. **Shopify App Proxy + Fee Product** (2 dias)
   - Construir app Remix (ou Express) com proxy `/apps/tax-wizard/quote`, criação de produto oculto e webhooks de ordem. 【F:docs/backlog/16_milestone_06_integrations.md†L87-L160】
   - Adicionar endpoints auxiliares no backend (`/v1/integrations/shopify/*`) e métricas `integration_requests_total`.
   - Riscos: limites Shopify → retries/exponential backoff.

3. **Tooling & Docs** (1 dia)
   - Atualizar Settings UI com seção "Integrations", Postman/Newman, README/runbooks e Makefile/CI (`woocommerce-build`, `shopify-build`). 【F:docs/certification/ACTION_PLAN.md†L1-L73】
   - Entregar guias passo-a-passo e evidências ≤512 KB.

## Branch & PR sugeridos (próxima passada)
- **Branch**: `feature/m6-integrations-alpha-2025-10-02`
- **PR Title**: `Milestone 6 – Platform Integrations Alpha`
- **PR Body (rascunho)**:
  ```markdown
  ## Summary
  - Deliver WooCommerce plugin + Shopify app proxy leveraging `/v1/fees/*` with HMAC.
  - Add backend helpers/métricas de integrações e seção "Integrations" na UI/admin.
  - Atualizar documentação, Postman e CI/Makefile com fluxo de build/teste dos conectores.

  ## Testing
  - `pytest -q`
  - `python smoke_test.py --security-only`
  - `composer test` (WooCommerce)
  - `npm run test` (Shopify app)
  - `npm run build`
  - `curl -s $SMOKE_METRICS_URL | grep integration_`

  ## Evidence
  - `docs/certification/EVIDENCE/*.txt`
  - Plugin build artefacts (`integrations/woocommerce/dist/*.zip`)
  - Shopify app test logs (`integrations/shopify/.logs/*.txt`)

  ## Risks & Rollback
  - Plugins opcionais: rollback removendo ZIPs/publicação e desativando feature flags.
  - Endpoints novos protegidos por flags (`INTEGRATIONS_*`); rollback = desabilitar flag e reimplantar imagem anterior.

  ## Checklist
  - [ ] Plugins Woo/Shopify compilam e testam
  - [ ] Métricas `integration_*` expostas e documentadas
  - [ ] Docs/Postman/UI atualizados
  ```

## Sumário executivo
- **M5 = PASS** (gates concluídos, evidências regeneradas, documentação alinhada).
- **Próximas ações**:
  1. Entregar plugin WooCommerce com HMAC + logs (`1.5–2 dias`, risco médio – compatibilidade WP/WC).
  2. Construir app Shopify + endpoints auxiliares (`2 dias`, risco médio – limites Shopify).
  3. Atualizar UI/tooling/docs/CI para integrações (`1 dia`, risco baixo – depende de 1–2).

