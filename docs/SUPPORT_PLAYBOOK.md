# Support Playbook – Webhook Launch (M8)

## Objetivos
- Prover atendimento nível 1 e 2 para incidentes de webhooks.
- Garantir comunicação clara com lojistas durante o launch.

## SLAs / SLIs
- **Tempo de primeira resposta:** ≤ 30 min (horário comercial) / ≤ 1h (fora do horário) via Zendesk.
- **Tempo para mitigação:** ≤ 2h para falhas críticas (DLQ>0, falha generalizada).
- **Atualização de status:** a cada 30 min enquanto incidente ativo.

## Canais
- **Ticket (Zendesk):** formulário "Webhook Issue" (inclui campos endpoint, store_id, timestamps).
- **Chat (Slack Connect):** canal `#webhooks-support`.
- **Status Page:** template "Webhook Delivery Degradation" (ver abaixo).

## Templates
### Resposta inicial (ticket)
```
Olá {{contact_name}},

Recebemos seu reporte sobre webhooks Taxo. Estamos analisando o comportamento descrito.
Referência: store {{store_id}}, endpoint {{endpoint}}.

Próximos passos:
1. Validaremos logs e tentativas recentes.
2. Caso necessário, acionaremos você para confirmar configurações do endpoint.

Manteremos atualizações a cada 30 minutos.
Obrigado,
Equipe State Tax Wizard
```

### Status page
```
Incident: Webhook Delivery Latency
Impacto: atrasos na entrega de eventos fee.applied/report.ready para subset de lojas.
Ação imediata: revisando fila de DLQ e reprocessando eventos afetados.
Atualização em: 30 minutos.
```

## Troubleshooting rápido
1. Confirmar store_id e endpoint via `/v1/stores/{id}/settings`.
2. Checar status via `/v1/webhooks/events?store_id=...`.
3. Se `last_error=missing_hmac_secret`, orientar rotação imediata.
4. Executar replay: `/v1/webhooks/events/{event_id}/replay` (informar operador do cliente).
5. Registrar todas as ações no ticket.

## Escalonamento
- **Severidade 1 (falha geral):** acionar EngOps via PagerDuty.
- **Severidade 2 (loja crítica):** EngOps em até 30 min.
- **Severidade 3 (baixa prioridade):** acompanhar via ticket, atualizar diariamente.

## Pós-incidente
- Atualizar `docs/launch/GO_LIVE_CHECKLIST_M8.md` item "Suporte".
- Compartilhar resumo semanal com Product e EngOps.
- Registrar melhorias no backlog (`docs/backlog/18_milestone_08_launch.md`).

## FAQ rápida
- **Como obter segredo atual?** Somente via rotação (`POST /v1/stores/{id}/hmac/rotate`). O valor é exibido uma única vez.
- **Posso desativar webhooks temporariamente?** Sim, defina `webhook_active=false`; eventos permanecerão `pending` até reativação.
- **Como validar assinatura?** Seguir [`docs/webhooks/verification.md`](docs/webhooks/verification.md).
