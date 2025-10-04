# GO-LIVE CHECKLIST – Milestone 8 (Launch)

> Status inicial pós-certificação M7. Atualize a coluna "Owner" com responsáveis reais e marque status conforme execução.

| Item | Owner | Status | Evidência/Notas |
| --- | --- | --- | --- |
| ✅ Webhook catálogo (`fee.applied`, `fee.skipped`, `report.ready`, `hmac.rotated`) funcionando em staging | Platform Eng | GREEN | `pytest -q`, smoke manual (`python backend/smoke_test.py --webhooks-only`) |
| ☐ Dashboards Grafana `Taxo – Webhooks` publicados (latência P95, taxa de sucesso, DLQ) | Observability | TODO | Queries prontas em `docs/observability.md` |
| ☐ Alertas Prometheus configurados (`webhooks_delivery_seconds_p95`, `webhooks_failed_total`, `webhooks_dead_letter_total`) | Observability | TODO | Ver `docs/webhooks/runbook.md` |
| ☐ Pipeline CI roda `pytest -q` + smoke webhooks + Newman folder "Webhooks" | DevEx | TODO | Adicionar job `webhooks-smoke` e `newman-webhooks` |
| ☐ Guia de suporte (FAQ, macros, escalonamento) publicado | Support Ops | IN PROGRESS | `docs/SUPPORT_PLAYBOOK.md` |
| ☐ Runbook de deploy/rollback validado (ensaio) | Platform Eng | TODO | `docs/launch/RUNBOOKS.md` |
| ☐ Comunicação externa (status page + release notes) preparada | Product Marketing | TODO | Templates em `docs/SUPPORT_PLAYBOOK.md` |
| ☐ Política de rotação HMAC comunicada aos clientes (cadência + canal) | Account Management | TODO | Reutilizar `docs/webhooks/runbook.md` |
| ☐ Backup/restore DB verificados pós-migration 202510060001 | SRE | TODO | `poetry run alembic upgrade head` + plano de rollback |
| ☐ Checklist anti-drift executado (`docs/certification/CHECKLIST.md`) | QA Lead | TODO | Atualizar marcações e anexar evidências |

## Ritos
- **Daily M8 Sync:** 15min, foco em itens vermelhos/laranjas.
- **Go/No-Go Review:** após conclusão de todos os itens "TODO".
- **Retro pós-launch:** 1 semana após go-live.

## Dependências externas
- Ambiente Prometheus/Grafana com acesso a `/metrics`.
- Canal de comunicação com lojistas (mailing ou status page).
- Equipe de suporte treinada para SLOs definidos em `docs/SLO.md`.
