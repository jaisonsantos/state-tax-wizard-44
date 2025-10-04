# Decision Log — Milestone Alignment (M7 → M8)

## Milestone status
- **LAST_COMPLETED_MILESTONE:** M7 — Webhooks & Lifecycle. Eventos outbound `fee.applied`, `fee.skipped`, `report.ready`, `hmac.rotated` entregues com HMAC `X-Taxo-*`, DLQ/replay, UI/Admin, Postman e documentação completos. 【F:backend/app/services/taxo_webhook_service.py†L24-L305】【F:docs/webhooks/README.md†L1-L80】【F:docs/certification/DECISION.md†L1-L60】
- **CURRENT_ACTIVE_MILESTONE:** M8 — Launch Readiness. Foco em dashboards/alertas, automação de smokes/Newman, runbooks e suporte. 【F:docs/certification/ACTION_PLAN.md†L1-L140】【F:docs/launch/GO_LIVE_CHECKLIST_M8.md†L1-L200】
- **NEXT_SLICE (1–2 semanas):** Executar plano M8 Init: provisionar observabilidade, rodar smokes/Postman em CI, validar runbooks, capturar métricas reais e fechar checklist. 【F:docs/AGENTE.md†L80-L140】【F:docs/certification/CHECKLIST.md†L1-L80】

## Key findings
- **Serviço de webhooks consolidado:** Migration `202510060001` cria outbox, serviço assina e registra tentativas, UI expõe controles. Replays disponíveis via API e smoke CLI documentada. 【F:backend/alembic/versions/202510060001_taxo_webhooks_outbox.py†L32-L108】【F:backend/app/routers/webhooks.py†L14-L84】【F:backend/smoke_test.py†L838-L969】
- **Tooling/documentação alinhados:** `docs/webhooks/*`, Postman (pasta "Webhooks"), README, STATUS e backlog atualizados para refletir novo contrato `X-Taxo-*`. 【F:docs/postman/state-tax-wizard.postman_collection.json†L1820-L2140】【F:README.md†L8-L60】【F:docs/backlog/17_milestone_07_webhooks.md†L1-L120】
- **Certificação e governança prontas:** `docs/AGENTE.md`, `docs/certification/*`, `docs/launch/*`, `docs/SLO.md` orientam a execução do M8 com próximos passos claros e artefatos ≤512 KB. 【F:docs/AGENTE.md†L1-L160】【F:docs/launch/RUNBOOKS.md†L1-L180】【F:docs/SLO.md†L1-L120】

## Risks & dependencies
- **Stack Prometheus/Grafana indisponível nesta sandbox:** métricas reais ainda não coletadas (`metrics_dump.txt` contém instruções). Provisionamento necessário antes do go-live. 【F:docs/certification/EVIDENCE/metrics_dump.txt†L1-L7】
- **Dependência de Docker para `make webhooks-smoke`:** alvo falha sem `docker-compose`; alternativa manual documentada mas precisa de automação em CI. 【F:docs/certification/EVIDENCE/webhooks_smoke.txt†L1-L10】
- **Coordenação cross-team:** Suporte/Marketing/EngOps precisam alinhar comunicação (status page, incident templates) – ver itens pendentes no GO-LIVE checklist. 【F:docs/launch/GO_LIVE_CHECKLIST_M8.md†L1-L200】

## API / documentação follow-ups
1. Capturar evidência real de métricas `webhooks_delivery_*` e anexar ao `metrics_dump.txt` após provisionamento Prometheus.
2. Adicionar screenshots/UI ao guia `docs/webhooks/configuration.md` quando front-end puder ser executado no ambiente de certificação.
3. Automatizar Newman (pasta "Webhooks") e smoke CLI em pipeline GitHub Actions; atualizar documentação com links para relatórios.

## Impact
- Equipe pode iniciar execução de M8 com plano claro e artefatos de launch prontos.
- Operações possuem runbooks/suporte padronizados e SLO definidos para o novo serviço de webhooks.
- Próxima rodada deve priorizar observabilidade real, automação de testes e ensaio de rollback antes do go-live.
