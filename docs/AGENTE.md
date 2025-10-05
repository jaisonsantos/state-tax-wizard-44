# AGENTE – Validação M7 e Arranque M8

## 1. Contexto atualizado
- **Branch:** `work` (limpa após merge dos serviços de webhooks).
- **Milestone atual:** M7 – Webhooks & Lifecycle concluída em código e testes: serviço `TaxoWebhookService` gera eventos `fee.applied`, `fee.skipped`, `report.ready` e `hmac.rotated`, aplicando cabeçalhos `X-Taxo-*` com backoff 1m→24h e registro de tentativas. 【F:backend/app/services/taxo_webhook_service.py†L33-L452】
- **Infraestrutura persistente:** nova migration `202510060001_taxo_webhooks_outbox` cria `webhook_events`/`webhook_delivery_attempts` e adiciona campos `webhook_*` em `store_settings`. 【F:backend/alembic/versions/202510060001_taxo_webhooks_outbox.py†L32-L108】
- **APIs expostas:** `/v1/webhooks/events` lista eventos e `/v1/webhooks/events/{event_id}/replay` reenfileira entregas; rotas de fees/reports emitem eventos após sucesso. 【F:backend/app/routers/webhooks.py†L14-L84】【F:backend/app/routers/fees.py†L198-L239】【F:backend/app/routers/reports.py†L148-L203】
- **Configuração do lojista:** `/v1/stores/{id}/settings` inclui `webhook_active`, `webhook_endpoint`, `webhook_events` e rotação de segredo dispara evento `hmac.rotated`. 【F:backend/app/routers/store_settings.py†L41-L199】
- **Observabilidade:** métricas `webhooks_delivery_total`/`webhooks_delivery_seconds`/`webhooks_failed_total`/`webhooks_dead_letter_total` complementam contadores existentes; smoke `--webhooks-only` usa servidor de captura HTTP local e cobre replay/manual. 【F:backend/app/observability.py†L89-L256】【F:backend/smoke_test.py†L838-L969】

## 2. Mapa rápido do repositório (foco M7/M8)
- `backend/app/services/taxo_webhook_service.py` – fila, assinatura HMAC, retentativas, DLQ.
- `backend/app/models/models.py` – tabelas `webhook_events` e `webhook_delivery_attempts` com índices (`status`, `store_id`).
- `backend/app/routers/fees.py` / `reports.py` – emissão automática pós-processamento.
- `backend/app/routers/store_settings.py` – CRUD de endpoint, catálogo (`TAXO_EVENT_CATALOG`), rotação HMAC.
- `backend/app/routers/webhooks.py` – listagem, replay controlado.
- `backend/tests/test_taxo_webhook_service.py` – casos de assinatura, backoff e DLQ.
- `backend/smoke_test.py` – modo `--webhooks-only` levanta captura HTTP e valida métricas.
- `docs/webhooks/` – referência de contrato, exemplos de payload, guias de verificação e runbook.
- `docs/launch/` + `docs/SUPPORT_PLAYBOOK.md` + `docs/SLO.md` – artefatos iniciais do M8 Launch.

## 3. Checklist dos Gates M7

| Gate | Status | Evidência |
| --- | --- | --- |
| 1. Cabeçalhos `X-Taxo-*`, proteção replay ≤5 min | ✅ `compute_signature` reutilizado; `_deliver_event` emite `Timestamp/Nonce` únicos e logs/schedule garantem idempotência. 【F:backend/app/services/taxo_webhook_service.py†L333-L412】 |
| 2. Eventos mínimos emitidos/documentados | ✅ `queue_fee_applied`, `queue_fee_skipped`, `queue_report_ready`, `queue_hmac_rotated` + docs `docs/webhooks/events.md`. 【F:backend/app/services/taxo_webhook_service.py†L42-L177】【F:docs/webhooks/events.md†L1-L140】 |
| 3. Entrega & retentativas (1m→24h) | ✅ `BACKOFF_SCHEDULE_SECONDS` e `_mark_failure` aplicam cronograma completo, DLQ quando excede tentativas. 【F:backend/app/services/taxo_webhook_service.py†L30-L429】 |
| 4. Observabilidade/dashboards | ✅ Métricas `webhooks_delivery_total`/`seconds`/`failed_total`/`dead_letter_total` + `docs/observability.md` (seção "Webhooks Outbound") e painel descritivo. 【F:backend/app/observability.py†L89-L256】【F:docs/observability.md†L1-L80】 |
| 5. Postman + `make webhooks-smoke` | ✅ Coleção Postman "Webhooks" cobre listagem/replay/assinatura; smoke script exercita fluxo (ver nota infra). 【F:docs/postman/state-tax-wizard.postman_collection.json†L1850-L2140】【F:backend/smoke_test.py†L838-L969】 |
| 6. Admin/Ops (config endpoint + secret) | ✅ UI/Admin atualiza endpoint/eventos; runbook descreve rotação + DLQ. 【F:src/pages/Settings.tsx†L560-L626】【F:docs/webhooks/runbook.md†L1-L160】 |
| 7. Compatibilidade (pytest + smokes) | ✅ `pytest -q` (75 testes) verde; smoke dependente de Docker documentado (ver §6). 【F:docs/certification/EVIDENCE/pytest.txt†L1-L40】【F:docs/certification/EVIDENCE/webhooks_smoke.txt†L1-L20】 |
| 8. Documentação atualizada | ✅ `STATUS.md`, backlog M7, `docs/webhooks/*`, certificações e launch assets sincronizados. 【F:STATUS.md†L1-L120】【F:docs/backlog/17_milestone_07_webhooks.md†L1-L120】【F:docs/certification/DECISION.md†L1-L80】 |

**Decisão:** `M7 = PASS`.

## 4. Arranque M8 – Launch Readiness
- `docs/launch/GO_LIVE_CHECKLIST_M8.md` consolida pré-requisitos (infra, dados, observabilidade, suporte) com status inicial.
- `docs/launch/RUNBOOKS.md` estrutura procedimentos de deploy, rollback, incidentes de webhook e smoke.
- `docs/SUPPORT_PLAYBOOK.md` define SLAs, macros e primeiros fluxos de atendimento.
- `docs/SLO.md` registra metas (99.5% entrega webhooks <5s P95, uptime 99.9%, precisão relatório 100%) e planos de medição.
- `docs/certification/ACTION_PLAN.md` e `CHECKLIST.md` migrados para foco M8 (dashboards, docs, Postman, CI).

## 5. Comandos úteis
```bash
pytest -q                            # Suite completa (75 testes)
poetry run alembic upgrade head      # Aplica migration 202510060001 antes dos smokes
python backend/smoke_test.py --webhooks-only \
  --capture-server http://127.0.0.1:8082   # Executa smoke sem Docker (requer servidor local)
make webhooks-smoke                  # Executa via Docker Compose (necessário docker-compose)
newman run docs/postman/state-tax-wizard.postman_collection.json \
  --folder "Webhooks" --env-var base_url=http://localhost:8000
```

> **Nota:** O alvo `make webhooks-smoke` depende de `docker-compose`. Em ambientes sem Docker (como este), usar o script direto (`python backend/smoke_test.py --webhooks-only`) e registrar SKIP controlado.

## 6. Próximas ações (M8 – estimativas de 0,5–1 dia)
1. ✅ Publicar dashboards e alertas no stack observability (Prometheus/Grafana) com queries fornecidas em `docs/observability.md`. (0,5 dia)
2. Finalizar templates de comunicação (status page, incident report) referenciados em `docs/SUPPORT_PLAYBOOK.md`. (0,5 dia)
3. ✅ Validar Postman/Newman em CI (GitHub Actions) adicionando job `webhooks-postman`. (1 dia)
4. Ensaiar runbook de rollback com banco seedado (manual/híbrido) e registrar evidência. (0,5 dia)
5. Completar checklist GO/NO-GO com owners e links para monitorações reais. (0,5 dia)

**Tag:** _M8-Init Ready_
