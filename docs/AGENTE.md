# AGENTE – M7 Webhooks ✅ / Preparação M8

## Snapshot Atual
- Commit: `3c6c149bb9a6712ab772549836c99491c623a16f`
- Branch: `main`
- `git status -s`: clean

## Mapa do Repositório
- `backend/app/models/models.py` – inclui a tabela `processed_webhooks` com status, tentativas, DLQ e timestamps. 【F:backend/app/models/models.py†L220-L260】
- `backend/app/routers/billing.py` – webhook Stripe com verificação de assinatura e endpoint de replay autenticado. 【F:backend/app/routers/billing.py†L200-L270】
- `backend/app/services/webhook_service.py` – idempotência, retry/backoff, métricas e roteamento de eventos Stripe. 【F:backend/app/services/webhook_service.py†L40-L260】
- `backend/app/observability.py` – novos contadores/histograma `webhooks_received_total`, `webhooks_processed_total`, `webhook_processing_latency_ms`. 【F:backend/app/observability.py†L77-L150】
- `backend/tests/test_billing_webhook_endpoint.py` – cobre sucesso, duplicados, assinaturas inválidas e replay DLQ. 【F:backend/tests/test_billing_webhook_endpoint.py†L1-L140】
- `backend/smoke_test.py` – modo `--webhooks-only` assina payload, executa replay e valida métricas. 【F:backend/smoke_test.py†L800-L960】
- `docs/postman/state-tax-wizard.postman_collection.json` – pasta **Webhooks** com requests positivo/negativo e pré-script de assinatura. 【F:docs/postman/state-tax-wizard.postman_collection.json†L1700-L1900】
- `docs/api/billing.md`, `docs/billing/stripe.md`, `docs/security/observability.md`, `STATUS.md` – documentação atualizada com fluxo, métricas e procedimentos. 【F:docs/api/billing.md†L1-L220】【F:docs/billing/stripe.md†L1-L200】【F:docs/security/observability.md†L1-L80】【F:STATUS.md†L6-L70】
- `Makefile` – novos alvos `webhooks-smoke` e `m7-validation`. 【F:Makefile†L1-L150】

## Validação M7
- **Gates executados:**
  1. `processed_webhooks` + migration (`upgrade`/`downgrade`). 【F:backend/alembic/versions/202510050001_add_processed_webhooks_table.py†L1-L90】
  2. `/v1/billing/webhooks/stripe` com assinatura, idempotência e DLQ → ✅
  3. `POST /v1/billing/webhooks/stripe/replay/{event_id}` autenticado → ✅
  4. Métricas `webhooks_received_total`, `webhooks_processed_total`, `webhook_processing_latency_ms` em `/metrics` + docs → ✅
  5. Smoke `make webhooks-smoke` com payload assinado e replay → ✅
  6. Postman **Webhooks** (processado + assinatura inválida) → ✅
  7. STATUS/README/backlog atualizados para M7; `docs/certification/*` reflete decisão → ✅
  8. Compat M2–M6 preservada (`pytest`, smokes existentes) → ✅

- **Comandos úteis**
  ```bash
  # Backend / dados
  docker-compose exec api python -m alembic upgrade head | tail -n 200 > docs/certification/EVIDENCE/migrate.txt
  docker-compose exec api pytest -q | tee docs/certification/EVIDENCE/pytest.txt
  make analytics-smoke reports-smoke security-smoke billing-smoke integrations-smoke webhooks-smoke

  # Webhooks específicos
  make webhooks-smoke
  curl -X POST "$API/api/v1/billing/webhooks/stripe/replay/$EVENT" -H "Authorization: Bearer $TOKEN"
  ```

- **Evidências esperadas** (≤512 KB): `pytest.txt`, `analytics_smoke.txt`, `reports_smoke.txt`, `security_smoke.txt`, `billing_smoke.txt`, `integrations_smoke.txt`, `webhooks_smoke.txt`, `metrics_dump.txt` (com linhas `integration_*` e `webhooks_*`), `newman_integrations.txt`, `newman_webhooks.txt`, `api_logs.txt`.

## Próximo Passo — M8 Launch Readiness
- Dashboards/alertas: aplicar blueprint em `docs/observability.md` (painéis + regras Prometheus) e versionar JSON no repo de infra.
- Automatizar limpeza de `processed_webhooks` (job semanal) e monitorar counters pós-limpeza.
- Revisar parity de reversals/reporting para Shopify/Woo e anexar evidências (`make full-validation`, Postman completo).
- Consolidar runbooks (incident response atualizado, replay CLI) e preparar pacote de go-live/rollback.

## Riscos / Observações
- Garantir `STRIPE_WEBHOOK_SECRET` configurado em todos os ambientes (smokes/Postman falham sem ele).
- Respeitar limite de 512 KB em evidências e mascarar segredos (`nonce_preview`, sem payload completo).
- Monitore o crescimento de `processed_webhooks` (planejar limpeza futura ou TTL).
- Shopify/WooCommerce order webhooks & reversals continuam pendentes para M8 — alinhar escopo e métricas adicionais.
