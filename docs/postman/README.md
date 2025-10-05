# Postman & Newman Collection Guide

Esta coleção cobre os fluxos do State Tax Wizard. Use-a para validar APIs, webhooks outbound e rotinas operacionais.

## Pré-requisitos
- Backend em execução (`make dev` ou `uvicorn backend.app.main:app --reload`).
- Postman Desktop/CLI **ou** Node.js 18+ com [`newman`](https://www.npmjs.com/package/newman) instalado globalmente:
  ```sh
  npm install --global newman
  ```
- Acesso de rede ao host definido em `{{base_url}}`.
- Opcional: servidor HTTP de captura (ex.: `python -m http.server 8082`) para receber webhooks reais durante os smokes.

## Variáveis da coleção

| Variável | Propósito | Default |
| --- | --- | --- |
| `base_url` | URL raiz do backend | `http://localhost:8000` |
| `token` | JWT após login | _preenchido pelo login_ |
| `store_id` | Loja ativa | _preenchido pelo login_ |
| `evidence_dir` | Diretório para artefatos (quando usado em CI) | _opcional_ |
| `hmac_secret` | Segredo usado para `/v1/fees/apply`; atualizado pela rotação | `demo-hmac-secret` |
| `taxo_webhook_secret` | Segredo atual do webhook outbound (capturado em `Rotate HMAC`) | _(vazio)_ |
| `webhook_endpoint` | Endpoint alvo para entregas (usado na atualização de settings) | `http://127.0.0.1:8082/capture` |
| `hmac_timestamp_override` / `hmac_nonce_override` | Forces para cenários negativos | _opcional_ |
| `billing_plan_tier` | Plano usado nos testes de billing | `pro` |

> Exemplo de ambiente em `docs/postman/local.postman_environment.json`. Duplique-o, atualize credenciais e aponte via `--environment` no Newman.
> Para validar Enterprise via Checkout configure também `STRIPE_PRICE_ID_E10K`, `STRIPE_PRICE_ID_E25K`, `STRIPE_PRICE_ID_E50K` no backend; quando ausentes os testes confirmam o fallback "Fale com vendas".

## Ordem sugerida
1. **Auth / Login** – gera `token`/`store_id`.
2. **Monitoring** – valida `/healthz` e `/metrics`.
3. **Fees / Apply** – exercita assinatura HMAC (`X-Taxo-*`) com geração automática de timestamp/nonce pela pre-request script.
4. **Fees / Rotate HMAC secret** – captura novo segredo (atualiza `hmac_secret` + `taxo_webhook_secret`).
5. **Reports / Analytics / Billing / Integrations** – como antes (a pasta Billing agora valida `warn_threshold_pct`, `warnings[]`, `stripe_prices_configured` e `billing_unconfigured`).
6. **Webhooks**:
   - `Webhooks / Update settings (enable)` – configura endpoint e eventos.
   - `Webhooks / Rotate HMAC secret` – gera segredo dedicado e atualiza variáveis.
   - Execute smoke (`python backend/smoke_test.py --webhooks-only`) ou acione fluxos na API para gerar eventos reais.
   - `Webhooks / List events` – confirma armazenamento e captura `event_id`.
   - `Webhooks / Replay last event` – executa replay manual e valida status.
7. **Auth / Logout** – encerra a sessão.

## Scripts automáticos
- O script `prerequest` adiciona `Authorization: Bearer <token>` automaticamente.
- Para `fees/apply`, o script gera corpo canonicalizado, `X-Taxo-Timestamp`, `X-Taxo-Nonce` e `X-Taxo-Signature` conforme contrato (`timestamp\nnonce\nbody`).
- Requisições que dependem de `taxo_webhook_secret` o capturam via `Webhooks / Rotate HMAC secret`.

## Evidências e automação
- Use `--env-var evidence_dir=<dir>` no Newman para registrar caminhos de artefatos (logs, CSV, JSON).
- Scripts das pastas de Analytics, Reports e Webhooks podem escrever `evidence_path=<dir>/...` no console para arquivamento.
- O workflow `Backend CI / smoke-newman` (ver `.github/workflows/backend.yml`) executa `python backend/smoke_test.py --webhooks-only` e, em seguida, `newman run ... --folder Webhooks` com um ambiente gerado dinamicamente. O relatório CLI consolidado é salvo em `docs/certification/EVIDENCE/newman_webhooks.md`.
- O teste "Webhooks / List events" agora falha caso nenhum evento esteja disponível, garantindo que o smoke CLI continue gerando `fee.applied` antes da validação.

## Cenários negativos recomendados
- **HMAC inválido**: utilize a requisição "Fees / Apply fees (invalid HMAC)" para verificar `403 invalid_signature`.
- **Timestamp vencido / nonce reutilizado**: use as requisições dedicadas após definir `hmac_timestamp_override`/`hmac_nonce_override`.
- **Webhooks**: após configurar endpoint inválido, rode `Webhooks / List events` para confirmar status `failed` com `last_error`. Repare em `docs/webhooks/runbook.md` para procedimentos de replay.
- **Replay manual**: execute `Webhooks / Replay last event` com `last_taxo_event_id` inexistente para validar `404` (edite a URL manualmente para testes negativos).
- **Checkout sem price ID**: altere `billing_plan_tier` para `enterprise_e10k` sem configurar `STRIPE_PRICE_ID_E10K`; espere `503 billing_unconfigured`.

## Exemplo Newman
```sh
newman run docs/postman/state-tax-wizard.postman_collection.json \
  --env-var base_url=http://localhost:8000 \
  --env-var webhook_endpoint=http://127.0.0.1:8082/capture \
  --reporters cli,junit \
  --reporter-junit-export=reports/newman/state-tax-wizard.xml
```

Execute com o servidor alvo e um endpoint de captura acessível para observar eventos gerados (fee/report/hmac). Documente evidências ≤512 KB.
