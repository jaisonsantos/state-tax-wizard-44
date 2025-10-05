# Project Status Report

> Consulte o [backlog consolidado](docs/backlog/README.md) para dependências detalhadas e milestones futuros.

## Backend
- **Outgoing webhooks (M7):** Serviço `TaxoWebhookService` gera eventos `fee.applied`, `fee.skipped`, `report.ready`, `hmac.rotated`, assina com `X-Taxo-*`, aplica backoff 1m→24h, grava tentativas (`webhook_delivery_attempts`) e fornece replay (`/v1/webhooks/events/{id}/replay`). 【F:backend/app/services/taxo_webhook_service.py†L33-L452】【F:backend/app/routers/webhooks.py†L14-L84】
- **Store settings:** `/v1/stores/{id}/settings` expõe `webhook_active`, `webhook_endpoint`, `webhook_events`, e rotação de segredo publica evento `hmac.rotated`. 【F:backend/app/routers/store_settings.py†L41-L199】
- **Fees & Reports:** Endpoints aplicam taxas/relatórios e enfileiram eventos automaticamente; `queue_fee_applied` usa IDs estáveis e `queue_report_ready` gera `download_path` assinado. 【F:backend/app/routers/fees.py†L198-L239】【F:backend/app/routers/reports.py†L148-L203】
- **Migrations:** `202510060001_taxo_webhooks_outbox` adiciona tabelas `webhook_events`/`webhook_delivery_attempts` e campos `webhook_*` em `store_settings`. Executar `poetry run alembic upgrade head` antes de subir ambiente. 【F:backend/alembic/versions/202510060001_taxo_webhooks_outbox.py†L32-L108】
- **Observabilidade:** Prometheus registra `webhooks_delivery_total`, `webhooks_delivery_seconds`, `webhooks_failed_total`, `webhooks_dead_letter_total`; logs via `log_webhook_delivery` mantêm PII fora. 【F:backend/app/observability.py†L89-L256】
- **Testes:** `backend/tests/test_taxo_webhook_service.py` cobre assinatura, backoff, falhas e DLQ; `pytest -q` (75 testes) verde. 【F:backend/tests/test_taxo_webhook_service.py†L1-L290】【F:docs/certification/EVIDENCE/pytest.txt†L1-L40】
- **Billing & entitlements:** novos tiers Free/Starter/Pro/Plus/Enterprise (commit 10k/25k/50k), `warn_threshold_pct=80`, métricas `entitlement_warnings_total`/`enterprise_overage_total`, degradação `503 billing_unconfigured` quando price IDs ausentes. 【F:backend/app/services/entitlement_service.py†L16-L285】【F:backend/app/observability.py†L49-L111】

## Frontend
- **Settings – Webhooks:** Tela exibe toggle `Enable webhooks`, campo de endpoint, seleção de eventos e botão de rotação de segredo, consumindo novos campos da API. 【F:src/pages/Settings.tsx†L560-L626】
- **API Client:** `src/lib/api.ts` inclui tipos para eventos de webhook e chamadas `getWebhookEvents`, `replayWebhookEvent`, `updateStoreSettings` com novos campos. 【F:src/lib/api.ts†L62-L105】【F:src/lib/api.ts†L471-L509】
- **Status geral:** Dashboard, relatórios e integrações permanecem estáveis (sem regressões detectadas).
- **Billing UI:** grade atualizada com Free→Plus + Enterprise (commit/overage), callouts quando `warnings[]` retornam ≥80%, modal "Fale com vendas" quando price IDs enterprise não configurados, e modal global para `transaction_limit_exceeded`. 【F:src/pages/Billing.tsx†L1-L424】【F:src/components/BillingLimitModal.tsx†L1-L65】

## Documentation & Tooling
- `docs/webhooks/*` cobre contrato, eventos, verificação, configuração e runbook operacional.
- `docs/launch/GO_LIVE_CHECKLIST_M8.md`, `docs/launch/RUNBOOKS.md`, `docs/SUPPORT_PLAYBOOK.md`, `docs/SLO.md` preparam launch M8 (dashboards, alertas, suporte, SLOs).
- Postman coleção inclui pasta "Webhooks" com scripts de assinatura `X-Taxo-*`; README atualizado com instruções de captura.
- `docs/AGENTE.md`, `docs/certification/*` marcam M7=PASS e planejam execução de M8 Init.
- Pricing model/versioning versionados em `docs/market/PRICING_MODEL.md` + `PRICING_GRID.csv`; API docs refletem campos `warn_threshold_pct`, `stripe_prices_configured` e `enterprise_overage`. 【F:docs/market/PRICING_MODEL.md†L1-L48】【F:docs/api/billing.md†L12-L129】

## Observability
- Painel Grafana versionado em `docs/observability/webhooks_dashboard.json` cobre sucesso, latência p95, falhas, DLQ, tentativas e correlação com fees/reports.
- Alertas Prometheus consolidados em `docs/observability/prometheus_alerts_webhooks.yaml` (latência, falhas, DLQ) com rótulo `service=taxo-api`.
- Captura de métricas (`metrics_dump.txt`) automatizada via job `Backend CI / smoke-newman`, publicando artefato `metrics-webhooks.txt`.
- Métricas novas: `entitlement_warnings_total{plan}`, `enterprise_overage_total{plan}` e `billing_events_total{event}` filtráveis via `make metrics`. Observabilidade doc atualizada com exemplos. 【F:docs/observability.md†L1-L120】

## QA & Automation
- `pytest -q` executado localmente (75 passed).
- Job `Backend CI / smoke-newman` adiciona `python backend/smoke_test.py --webhooks-only` + `newman run ... --folder Webhooks` com environment gerado dinamicamente, garantindo evento disponível antes do replay.
- Artefatos de evidência (`webhooks_smoke.txt`, `newman_webhooks.md`, `metrics-webhooks.txt`) são anexados automaticamente nas execuções da branch principal.

## Recommended Next Step (Milestone Alignment)
- **NEXT_SLICE: M8 Launch Readiness – Ensaio operacional** – executar dry-run de deploy/rollback com checklist assinado, validar playbook de suporte e confirmar owners dos alertas antes do go/no-go. 【F:docs/certification/ACTION_PLAN.md†L1-L140】
