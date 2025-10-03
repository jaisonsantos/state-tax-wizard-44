# AGENTE – Validação M5 e Preparação M6

## Snapshot Atual
- Commit atual: `82ee585`
- Branch: `main`
- `git status -s` (máx 20 linhas):

````
## main...origin/main
 M README.md
 M STATUS.md
 M backend/app/routers/billing.py
 M backend/app/schema/billing.py
 M backend/app/services/stripe_service.py
 M backend/tests/test_billing_api.py
 M backend/tests/test_stripe_service.py
 M docs/AGENTE.md
 M docs/api/billing.md
 M docs/backlog/15_milestone_05_billing.md
 M docs/billing/stripe.md
 M docs/certification/ACTION_PLAN.md
 M docs/certification/CHECKLIST.md
 M docs/certification/CONSISTENCY_PATCH.md
 M docs/certification/DECISION.md
 M docs/certification/DOCS_ORPHANS.md
 M docs/certification/EVIDENCE/api_logs.txt
 M docs/certification/EVIDENCE/billing_smoke.txt
 M docs/certification/EVIDENCE/metrics_dump.txt
 M docs/certification/EVIDENCE/migrate.txt
 M docs/certification/EVIDENCE/pytest.txt
````

## Mapa do repositório (foco em billing)
- `backend/app/routers/billing.py` – expõe entitlements, usage, checkout, portal e webhooks com degradação `billing_unconfigured`. 【F:backend/app/routers/billing.py†L1-L225】
- `backend/app/services/stripe_service.py` – integração Stripe (checkout, portal, sync, métricas). 【F:backend/app/services/stripe_service.py†L1-L260】
- `backend/app/services/entitlement_service.py` – limites de plano, uso e enforcement em `/v1/fees/apply`. 【F:backend/app/services/entitlement_service.py†L1-L210】
- `backend/app/observability.py` – métricas `billing_events_total`, `checkout_sessions_created_total`, `entitlement_denials_total`. 【F:backend/app/observability.py†L1-L140】
- `backend/tests/test_billing_api.py` e `backend/tests/test_entitlements.py` – cobertura para degradação, uso, limites, webhooks. 【F:backend/tests/test_billing_api.py†L1-L200】【F:backend/tests/test_entitlements.py†L1-L190】
- `backend/smoke_test.py` – modo `--billing-only` com skip automático quando Stripe não está configurado. 【F:backend/smoke_test.py†L305-L377】
- `src/lib/api.ts` e `src/pages/Billing.tsx` – cliente REST + UI (usage meter, upgrade, portal, tratamento `billing_unconfigured`). 【F:src/lib/api.ts†L520-L601】【F:src/pages/Billing.tsx†L1-L220】
- `docs/api/billing.md` & `docs/billing/stripe.md` – referência dos endpoints e runbook Stripe. 【F:docs/api/billing.md†L1-L160】【F:docs/billing/stripe.md†L1-L120】
- `docs/postman/state-tax-wizard.postman_collection.json` – pasta **Billing** cobre entitlements/usage/checkout/portal/webhook. 【F:docs/postman/state-tax-wizard.postman_collection.json†L893-L1200】
- `Makefile` – alvo `billing-smoke` (Stripe configurado = PASS; sem Stripe = mensagem SKIP). 【F:Makefile†L43-L88】

## Fontes de verdade (ordem)
1. Código e testes automatizados.
2. `STATUS.md` (estado + Recommended Next Step). 【F:STATUS.md†L1-L120】
3. `docs/backlog/00_release_plan.md`. 【F:docs/backlog/00_release_plan.md†L1-L190】
4. `docs/backlog/15_milestone_05_billing.md` / `docs/backlog/16_milestone_06_integrations.md`. 【F:docs/backlog/15_milestone_05_billing.md†L1-L32】【F:docs/backlog/16_milestone_06_integrations.md†L1-L90】
5. `README.md` (onboarding, validações). 【F:README.md†L80-L170】

## Diagnóstico atual (M5)
- ✅ Portal session corrigido – a API retorna `portal_session_id` e devolve `400 stripe_customer_missing` quando o store não possui metadados Stripe. Testes e TS types foram atualizados. 【F:backend/app/schema/billing.py†L45-L52】【F:backend/app/services/stripe_service.py†L200-L230】【F:backend/tests/test_billing_api.py†L129-L196】
- ✅ Evidências renovadas – `alembic upgrade head`, `pytest -q`, smokes (`analytics`, `reports`, `security`) e métricas foram executados com SQLite + seeds. Billing smoke permanece em modo SKIP sem chaves Stripe (comportamento esperado). 【F:docs/certification/EVIDENCE/migrate.txt†L1-L10】【F:docs/certification/EVIDENCE/pytest.txt†L1-L40】【F:docs/certification/EVIDENCE/security_smoke.txt†L1-L7】【F:docs/certification/EVIDENCE/billing_smoke.txt†L1-L1】
- ✅ Docs sincronizadas – README, STATUS, backlog M5, `docs/api/billing.md` e `docs/billing/stripe.md` refletem o novo contrato (`portal_session_id` + `stripe_customer_missing`).

## Como validar M5 (passo a passo)
1. **Setup**
   - `python3 -m venv .venv && source .venv/bin/activate`
   - `pip install -r backend/requirements.txt`
   - `npm install` (frontend, opcional para screenshots Playwright).
2. **Migrações**
   - `cd backend`
   - `DATABASE_URL=sqlite:///../docs/certification/tmp_dev.db alembic upgrade head | tail -n 200 > ../docs/certification/EVIDENCE/migrate.txt`
3. **Aplicação / Logs**
   - `APP_ENV=dev DATABASE_URL=sqlite:///../docs/certification/tmp_dev.db uvicorn app.main:app --host 127.0.0.1 --port 8000`
   - Capturar `tail -n 200` em `docs/certification/EVIDENCE/api_logs.txt` e encerrar o servidor.
4. **Testes automatizados**
   - `pytest -q > ../docs/certification/EVIDENCE/pytest.txt`
5. **Smokes** (API local em 127.0.0.1)
   - `SMOKE_API_BASE_URL=http://127.0.0.1:8010/api APP_ENV=dev DATABASE_URL=sqlite:///../docs/certification/tmp_dev.db ../.venv/bin/python smoke_test.py --analytics-only > ../docs/certification/EVIDENCE/analytics_smoke.txt`
   - Repetir para `--reports-only`, `--security-only`.
   - `--billing-only` produz SKIP se chaves Stripe não estiverem configuradas (registra evidência). Com credenciais reais o mesmo comando deve retornar PASS.
6. **Postman/Newman**
   - Atualizar `docs/postman/local.postman_environment.json` com Stripe keys.
   - `make newman-billing | tee docs/certification/EVIDENCE/newman_billing.txt` (espera PASS; sem env deve registrar SKIP).
7. **Métricas**
   - `curl -s http://127.0.0.1:8000/metrics | grep -E "(billing|rate_limit|hmac|fees|report|checkout|entitlement)" | head -n 80 > docs/certification/EVIDENCE/metrics_dump.txt`
8. **Limpeza**
   - Garantir que cada arquivo ≤512 KB e substituir em vez de concatenar.

> _Nota_: nesta rodada não rodamos testes porque as dependências não estão instaladas; a próxima execução deve seguir o roteiro acima para renovar as evidências.

## Limites de evidência
- Máx. 512 KB por arquivo em `docs/certification/EVIDENCE/`.
- Use `head -n 200` / `tail -n 200` para truncar logs.
- Arquivos gerados automaticamente (`*_scan*.txt`) devem ser resumidos e ignorados conforme necessário.

## Gate M5 – Checklist
- [x] **1. Endpoints documentados/alinhados** – Portal retorna `portal_session_id` e documenta `stripe_customer_missing`. 【F:backend/app/schema/billing.py†L45-L52】【F:docs/api/billing.md†L113-L140】
- [x] **2. Degradação `billing_unconfigured`** – `_ensure_billing_configured()` cobre entitlements/usage/checkout/portal; webhook checa `stripe_webhook_secret`. 【F:backend/app/routers/billing.py†L21-L186】【F:backend/tests/test_billing_api.py†L18-L110】
- [x] **3. Enforcement em `/v1/fees/apply`** – limite mensal aplicado somente quando Stripe ativo. 【F:backend/app/routers/fees.py†L132-L185】【F:backend/app/services/entitlement_service.py†L124-L185】
- [x] **4. Métricas billing** – counters definidos e usados (`billing_events_total`, `checkout_sessions_created_total`, `entitlement_denials_total`). 【F:backend/app/observability.py†L37-L88】【F:docs/certification/EVIDENCE/metrics_dump.txt†L1-L40】
- [x] **5. Migrações com upgrade/downgrade + cadeia única** – revisões `20251002000(1, 2, 3)` encadeadas e reversíveis. 【F:backend/alembic/versions/202510020001_billing_stripe_integration.py†L1-L92】
- [x] **6. Seeds determinísticos** – `seed_data.py` cria stores com Stripe IDs/planos para uso/entitlements. 【F:backend/seed_data.py†L1-L170】
- [x] **7. Testes automatizados** – cobertura para degradação, uso, limites, webhooks e `StripeService`. 【F:backend/tests/test_billing_api.py†L1-L200】【F:backend/tests/test_stripe_service.py†L1-L136】
- [x] **8. Smokes (`analytics`, `reports`, `security`)** – executados com evidência atualizada; billing smoke documenta SKIP sem Stripe test keys. 【F:docs/certification/EVIDENCE/security_smoke.txt†L1-L7】【F:docs/certification/EVIDENCE/billing_smoke.txt†L1-L1】
- [x] **9. Postman Billing folder** – continua alinhado (`portal_session_id` + código de erro) e documentado no README. 【F:docs/postman/state-tax-wizard.postman_collection.json†L1134-L1186】【F:docs/postman/README.md†L59-L110】
- [x] **10. Frontend Billing** – tela trata `billing_unconfigured`, upgrade e portal, com toasts. 【F:src/pages/Billing.tsx†L1-L220】
- [x] **11. Docs sincronizadas** – README, STATUS, backlog M5 e guia Stripe atualizados pós-fix. 【F:README.md†L80-L150】【F:STATUS.md†L6-L66】【F:docs/backlog/15_milestone_05_billing.md†L1-L28】【F:docs/billing/stripe.md†L1-L110】

## Resultado M5
- ✅ `pytest -q` (61 testes) em Python 3.12 com warnings conhecidos.
- ✅ Smokes `analytics`, `reports`, `security` PASS; `billing-only` documenta SKIP quando Stripe está desativado.
- ✅ Evidências atualizadas (`api_logs.txt`, `migrate.txt`, `metrics_dump.txt`, `md_index.txt`).
- 🔜 Para ambientes com Stripe test mode basta exportar `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID_*` antes de rodar `billing-smoke` e Newman para observar o caminho feliz.

## Plano preliminar M6 (somente após M5 ✅)
- Revalidar backlog `docs/backlog/16_milestone_06_integrations.md` e priorizar WooCommerce plugin (SDK JS/PHP) e Shopify proxy/SDK.
- Preparar feature flags (`INTEGRATIONS_WOO_ENABLED`, `INTEGRATIONS_SHOPIFY_ENABLED`) e métricas `integrations_*` descritas no backlog.
- Expandir QA (Postman folder “Integrations”, smoke `integrations-smoke`) após concluir o fix slice.

## Anti-drift
- `rg "X-(RDF-)?(Signature|Timestamp|Nonce)" -n docs src backend | head`
- `rg "hmac_secret.*store" -n docs backend | head`
- `curl -s $API/metrics | grep -E "(billing|checkout|entitlement)" | head`

## Branch & PR
- **Branch sugerida**: `feature/m6-integrations-alpha-2025-10-04`
- **PR title**: `Integrations Alpha – WooCommerce & Shopify connectors`
- **Checklist do PR**:
  1. Referenciar esta rodada de validação e anexar as evidências (`docs/certification/EVIDENCE/`).
  2. Descrever a estratégia de rollout/rollback para WooCommerce e Shopify.
  3. Incluir plano de QA (pytest, novos smokes, Newman Integrations).
