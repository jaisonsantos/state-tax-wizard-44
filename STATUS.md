# Project Status Report

> Consulte o [backlog consolidado](docs/backlog/README.md) para dependências detalhadas e milestones futuros.

## Backend
- **Outgoing webhooks (M7):** Serviço `TaxoWebhookService` gera eventos `fee.applied`, `fee.skipped`, `report.ready`, `hmac.rotated`, assina com `X-Taxo-*`, aplica backoff 1m→24h, grava tentativas (`webhook_delivery_attempts`) e fornece replay (`/v1/webhooks/events/{id}/replay`). 【F:backend/app/services/taxo_webhook_service.py†L33-L452】【F:backend/app/routers/webhooks.py†L14-L84】
- **Store settings:** `/v1/stores/{id}/settings` expõe `webhook_active`, `webhook_endpoint`, `webhook_events`, e rotação de segredo publica evento `hmac.rotated`. 【F:backend/app/routers/store_settings.py†L41-L199】
- **Fees & Reports:** Endpoints aplicam taxas/relatórios e enfileiram eventos automaticamente; `queue_fee_applied` usa IDs estáveis e `queue_report_ready` gera `download_path` assinado. 【F:backend/app/routers/fees.py†L198-L239】【F:backend/app/routers/reports.py†L148-L203】
- **Migrations:** `202510060001_taxo_webhooks_outbox` adiciona tabelas `webhook_events`/`webhook_delivery_attempts` e campos `webhook_*` em `store_settings`. Executar `poetry run alembic upgrade head` antes de subir ambiente. 【F:backend/alembic/versions/202510060001_taxo_webhooks_outbox.py†L32-L108】
- **Observabilidade:** Prometheus registra `webhooks_delivery_total`, `webhooks_delivery_seconds`, `webhooks_failed_total`, `webhooks_dead_letter_total`; logs via `log_webhook_delivery` mantêm PII fora. 【F:backend/app/observability.py†L89-L256】
- **Testes:** `backend/tests/test_taxo_webhook_service.py` cobre assinatura, backoff, falhas e DLQ; `pytest -q` (73 testes) verde. 【F:backend/tests/test_taxo_webhook_service.py†L1-L290】【F:docs/certification/EVIDENCE/pytest.txt†L1-L10】

## Frontend
- **Settings – Webhooks:** Tela exibe toggle `Enable webhooks`, campo de endpoint, seleção de eventos e botão de rotação de segredo, consumindo novos campos da API. 【F:src/pages/Settings.tsx†L560-L626】
- **API Client:** `src/lib/api.ts` inclui tipos para eventos de webhook e chamadas `getWebhookEvents`, `replayWebhookEvent`, `updateStoreSettings` com novos campos. 【F:src/lib/api.ts†L62-L105】【F:src/lib/api.ts†L471-L509】
- **Status geral:** Dashboard, relatórios e integrações permanecem estáveis (sem regressões detectadas).

## Documentation & Tooling
- `docs/webhooks/*` cobre contrato, eventos, verificação, configuração e runbook operacional.
- `docs/launch/GO_LIVE_CHECKLIST_M8.md`, `docs/launch/RUNBOOKS.md`, `docs/SUPPORT_PLAYBOOK.md`, `docs/SLO.md` preparam launch M8 (dashboards, alertas, suporte, SLOs).
- Postman coleção inclui pasta "Webhooks" com scripts de assinatura `X-Taxo-*`; README atualizado com instruções de captura.
- `docs/AGENTE.md`, `docs/certification/*` marcam M7=PASS e planejam execução de M8 Init.

## Observability
- Painel recomendado: sucesso de entrega, latência p95, falhas por motivo, DLQ, timeline de tentativas e correlação com métricas de fees/reports.
- Alertas sugeridos: latência >5s (warning), `webhooks_failed_total` >0 (critical), `webhooks_dead_letter_total` >0 (critical).
- Evidências atuais: `metrics_dump.txt` aguarda captura real (stack Prometheus ausente nesta sandbox); instruções documentadas.

## QA & Automation
- `pytest -q` executado localmente (73 passed).
- `make webhooks-smoke` depende de `docker-compose`; tentativa registrada (erro 127). Alternativa manual documentada em `docs/AGENTE.md`.
- Próxima etapa: automatizar smoke + Newman em CI (M8).

## Recommended Next Step (Milestone Alignment)
- **NEXT_SLICE: M8 Launch Readiness** – publicar dashboards/alertas, automatizar smokes/Newman, validar runbooks e suporte antes do go-live. 【F:docs/certification/ACTION_PLAN.md†L1-L140】
