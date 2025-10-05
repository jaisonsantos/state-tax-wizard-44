# Launch Runbooks – M8 Init

## Deploy (Blue/Green)
1. Confirmar `pytest -q` verde e migrations aplicadas em staging (`poetry run alembic upgrade head`).
2. Construir imagens (`docker compose build api worker`).
3. Aplicar infraestrutura (Terraform/Helm) apontando para imagem nova.
4. Executar `python backend/smoke_test.py --webhooks-only --capture-server <url>` em staging.
5. Executar `newman run docs/postman/state-tax-wizard.postman_collection.json --folder Webhooks`.
6. Aprovar mudança na change management e promover para produção.

## Rollback
- **Soft rollback:** desativar webhooks (`webhook_active=false`) para lojas impactadas enquanto investiga.
- **Full rollback:**
  1. Reverter deploy (image tag anterior).
  2. Rodar `alembic downgrade 202510060001` somente se necessário e sem eventos novos (coordenação com DBAs).
  3. Executar script para reprocessar eventos DLQ pós-rollback (`/v1/webhooks/events/{id}/replay`).

## Pós-deploy
- Monitorar dashboards (`webhooks_delivery_total`, `webhooks_delivery_seconds`, `webhooks_failed_total`, `webhooks_dead_letter_total`).
- Validar logs sem erros `missing_endpoint`/`missing_hmac_secret` inesperados.
- Atualizar `docs/launch/GO_LIVE_CHECKLIST_M8.md` com status "GREEN".
- Comunicar suporte sobre estado da entrega.

## Incident Response
1. **Detecção** – alerta de latência >5s ou DLQ>0.
2. **Avaliação** – verificar `/v1/webhooks/events` e logs (`log_webhook_delivery`).
3. **Mitigação** – aplicar procedimentos do [runbook de webhooks](../webhooks/runbook.md).
4. **Comunicação** – abrir incidente no template do suporte (ver `docs/SUPPORT_PLAYBOOK.md`).
5. **Resolução** – confirmar `status=delivered` e fechar alerta.
6. **Postmortem** – documentar causa raiz, impacto, ações preventivas.

## Checklist Pré-Go-Live
- [x] `pytest -q`
- [x] `python backend/smoke_test.py --webhooks-only`
- [x] `newman run ... --folder Webhooks`
- [ ] Dashboards/alertas revisados
- [ ] Suporte briefed (SLA, macros)
- [ ] Owners confirmados (runbooks, SLO)

## Artefatos relacionados
- `docs/SLO.md`
- `docs/SUPPORT_PLAYBOOK.md`
- `docs/webhooks/runbook.md`
