# CHECKLIST – M7 Concluída / M8 Init

## Correções Rápidas (Anti-Drift)
- [x] `STATUS.md` reflete webhooks outbound, catálogo e próximo passo (M8 Launch). 【F:STATUS.md†L1-L200】
- [x] `hmac_secret` isolado em `store_settings` com rotação auditável + evento `hmac.rotated`. 【F:backend/app/models/models.py†L60-L120】【F:backend/app/routers/store_settings.py†L90-L162】
- [x] Replay-store (`processed_nonces`) mantém índice `(store_id, nonce)` com TTL e downgrade. 【F:backend/app/models/models.py†L188-L214】
- [x] Contrato HMAC (`timestamp\nnonce\nbody`) documentado e aplicado nos webhooks Taxo. 【F:docs/security/hmac.md†L1-L120】【F:backend/app/services/taxo_webhook_service.py†L333-L373】
- [x] Métricas com baixa cardinalidade para webhooks (`webhooks_delivery_total`, `webhooks_delivery_seconds`, `webhooks_failed_total`, `webhooks_dead_letter_total`). 【F:backend/app/observability.py†L89-L256】
- [x] Logs omitindo payload sensível e exibindo apenas `nonce` truncado. 【F:backend/app/observability.py†L118-L135】
- [x] Smokes aceitam `--webhooks-only`/`--security-only` e respeitam `SMOKE_*`. 【F:backend/smoke_test.py†L810-L1040】
- [x] Docs M5/M6 atualizadas com referências corretas e estado pós-M7. 【F:docs/backlog/15_milestone_05_billing.md†L1-L80】【F:docs/backlog/16_milestone_06_integrations.md†L1-L120】

## Gates M7 – Webhooks & Lifecycle
- [x] Cabeçalhos `X-Taxo-*` e proteção replay ≤5 min implementados e documentados. 【F:backend/app/services/taxo_webhook_service.py†L333-L412】【F:docs/webhooks/verification.md†L40-L140】
- [x] Eventos `fee.applied`, `fee.skipped`, `report.ready`, `hmac.rotated` com IDs estáveis. 【F:backend/app/services/taxo_webhook_service.py†L42-L177】【F:docs/webhooks/events.md†L1-L140】
- [x] Backoff 1m→24h e DLQ documentados (runbook + serviço). 【F:backend/app/services/taxo_webhook_service.py†L30-L429】【F:docs/webhooks/runbook.md†L1-L160】
- [x] `webhook_events`/`webhook_delivery_attempts` persistem status/attempts e suportam replay. 【F:backend/app/models/models.py†L228-L310】
- [x] Observabilidade/dashboards atualizados com métricas de entrega. 【F:docs/observability.md†L1-L80】
- [x] Postman + Makefile + smoke cobrem assinatura própria, inválidos, replay. 【F:docs/postman/state-tax-wizard.postman_collection.json†L1850-L2140】【F:backend/smoke_test.py†L838-L969】【F:Makefile†L60-L90】
- [x] Admin/Ops – UI configura endpoint/eventos; runbook descreve incidentes e rotação. 【F:src/pages/Settings.tsx†L560-L626】【F:docs/webhooks/runbook.md†L1-L160】
- [x] QA regressivo executado (`pytest -q`) e smoke documentado (SKIP controlado sem Docker). 【F:docs/certification/EVIDENCE/pytest.txt†L1-L10】【F:docs/certification/EVIDENCE/webhooks_smoke.txt†L1-L20】
- [x] Documentação dedicada (`docs/webhooks/*`, STATUS/backlog) concluída. 【F:docs/webhooks/README.md†L1-L80】【F:docs/backlog/17_milestone_07_webhooks.md†L1-L160】

## Pré-Gates M8 – Launch (Planejamento)
- [x] `docs/launch/GO_LIVE_CHECKLIST_M8.md` criado/atualizado com owners, status e evidências pendentes. 【F:docs/launch/GO_LIVE_CHECKLIST_M8.md†L1-L200】
- [x] `docs/launch/RUNBOOKS.md` cobre deploy, rollback, incidentes, smoke e métricas. 【F:docs/launch/RUNBOOKS.md†L1-L200】
- [x] `docs/SUPPORT_PLAYBOOK.md` define SLAs, macros de comunicação e matriz de severidade. 【F:docs/SUPPORT_PLAYBOOK.md†L1-L180】
- [x] `docs/SLO.md` registra objetivos (latência, uptime, precisão) e métodos de medição. 【F:docs/SLO.md†L1-L160】
