# Stripe Billing Integration

This guide documents how the application integrates with Stripe for subscription lifecycle management, how to configure environments, and how to validate the flows in test mode.

## Products, prices & environment variables

1. Create three recurring products in the Stripe Dashboard: **Starter**, **Pro**, and **Plus**.
2. Create monthly prices for each product and capture their price IDs.
3. Populate the following environment variables (see `.env.example` for placeholders):

   ```bash
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   STRIPE_PRICE_ID_STARTER=price_...
   STRIPE_PRICE_ID_PRO=price_...
   STRIPE_PRICE_ID_PLUS=price_...
   ```

4. Restart the API container after updating the `.env` file so settings reload. Without these values the API returns `503 billing_unconfigured` and the billing smoke skips automatically.

## Test-mode workflow

1. Launch the stack: `make up migrate seed`.
2. Run `make billing-smoke`:
   - With Stripe configured it validates entitlements, usage, checkout session creation, and portal session creation.
   - Without Stripe variables it prints `⚠ SKIP: Stripe billing not configured`.
3. Use Stripe test cards (e.g., `4242 4242 4242 4242`, any future expiry/CVC) when completing Checkout Sessions.
4. The Customer Portal allows upgrades/downgrades and cancellation in test mode. Changes propagate immediately to `subscriptions` and surface via the `/v1/billing/entitlements` endpoint.
5. Replay webhooks with the Stripe CLI if required:

   ```bash
   stripe listen --forward-to localhost:8000/api/v1/billing/webhooks/stripe
   ```

   The application verifies signatures with `STRIPE_WEBHOOK_SECRET` and updates metrics/audit logs for every processed event.

## Observability

Billing activity emits metrics and logs alongside the existing fee/security signals:

- `billing_events_total{event}` tracks checkout sessions, portal sessions, webhook outcomes, and skips.
- `checkout_sessions_created_total{plan_tier}` increments on successful upgrade requests.
- `entitlement_denials_total{feature,plan}` captures plan gated features (advanced reports, unlimited transactions, etc.).
- Structured `billing` logs detail checkout sessions, portal hand-offs, webhook processing, and transaction limit violations.

All billing metrics appear in `/metrics` and are captured in `docs/certification/EVIDENCE/metrics_dump.txt`.

## Frontend & Postman

- The Billing page (`/billing`) consumes `/v1/billing/entitlements` and `/v1/billing/usage` to render the plan card, usage meter, trial banner, and CTA buttons. Errors from Stripe (including `billing_unconfigured` and `stripe_customer_missing`) are surfaced to the operator with actionable messaging.
- The Postman collection contains a **Billing** folder that exercises entitlements, usage, checkout, portal, and webhook sample requests. When Stripe is unconfigured the tests echo `BILLING_SKIPPED=true` so CI can treat the run as informational.

## Evidence & automation

- `make billing-smoke` stores console output in `docs/certification/EVIDENCE/billing_smoke.txt`.
- When the Newman billing folder is executed with local Stripe credentials, capture the CLI transcript manually (e.g., `newman_billing.txt`). The file is ignored by default via `.gitignore`, so attach it explicitly in certification packs when available.
- UI screenshots for billing and Settings/HMAC rotation are stored under `docs/certification/EVIDENCE/screens/`.

---

1. **Quickstart operacional** (passo-a-passo pra subir local e validar)
2. **Comandos de “vida real”** (make/CLI/queries)
3. **Portal do Stripe** (checklist em Test mode)
4. **Troubleshooting** (erros → causa → correção)
5. **Reconciliação** (como corrigir dados demo ↔ Stripe)

---

````md
## Quickstart (dev local)

1. **Subir stack**
   ```bash
   make up         # ou: make dev (foreground)
   make migrate && make seed
````

2. **Stripe em modo teste**

   * Crie produtos **Starter/Pro/Plus** e preços mensais.
   * Popule o `.env`:

     ```bash
     STRIPE_SECRET_KEY=sk_test_...
     STRIPE_WEBHOOK_SECRET=whsec_...
     STRIPE_PRICE_ID_STARTER=price_...
     STRIPE_PRICE_ID_PRO=price_...
     STRIPE_PRICE_ID_PLUS=price_...
     ```
   * (Opcional) Deixe o listener ligado:

     ```bash
     make stripe-listen
     ```
3. **Portal (Test mode)**

   * Settings → Billing → **Customer portal** → marque *Customers can switch plans*.
   * Adicione os produtos elegíveis (mesma moeda do preço do cliente).
   * **Redirect link**: `http://localhost:8080/billing`.
   * **Save changes** (cria a configuração default de teste).
4. **Validação rápida**

   ```bash
   make billing-smoke
   # Esperado: "Billing smoke completed successfully."
   ```

## Operação do dia a dia

### Make targets úteis

```bash
make up / down / dev / logs / logs-api
make migrate seed
make billing-smoke
make stripe-listen
```

### Stripe CLI “de bolso”

```bash
# Ver configs do portal (deve existir uma default: true)
stripe billing_portal configurations list --limit 3

# Listar a assinatura de um customer
stripe subscriptions list --customer cus_XXXX --status all --limit 1

# Testar criação direta de portal
stripe billing_portal sessions create \
  --customer cus_XXXX \
  --return_url http://localhost:8080/billing
```

### Health checks no banco

```bash
# Stores com IDs do Stripe
docker-compose exec -T db psql -U user -d rdf -c "\x on" \
  -c "SELECT id, name, stripe_customer_id, stripe_subscription_id, created_at FROM stores ORDER BY created_at DESC;"

# Subscriptions mais recentes
docker-compose exec -T db psql -U user -d rdf \
  -c "SELECT id, store_id, provider, plan, status, stripe_subscription_id, current_period_start, current_period_end, updated_at FROM subscriptions ORDER BY updated_at DESC LIMIT 10;"

# Join store ↔ subscription
docker-compose exec -T db psql -U user -d rdf -c "
SELECT s.name, s.id AS store_id, s.stripe_customer_id,
       sub.stripe_subscription_id, sub.status, sub.plan,
       sub.current_period_start, sub.current_period_end
FROM stores s
LEFT JOIN subscriptions sub ON sub.store_id = s.id
ORDER BY s.created_at DESC;"
```

### Reconciliação (quando a seed deixou `sub_demo_*`)

```bash
# 1) Descobrir a assinatura real do customer
docker-compose exec -T api python - <<'PY'
import os, stripe
stripe.api_key=os.environ["STRIPE_SECRET_KEY"]
subs = stripe.Subscription.list(customer="cus_XXXX", status="all", limit=1)
print(subs.data[0].id, subs.data[0].status)
PY

# 2) Atualizar banco (trocar 'sub_REAL' e store_id)
docker-compose exec -T db psql -U user -d rdf -c "
UPDATE stores SET stripe_subscription_id='sub_REAL' WHERE id='STORE_UUID';
UPDATE subscriptions SET stripe_subscription_id='sub_REAL' WHERE store_id='STORE_UUID';"
```

## Troubleshooting (erros comuns)

| Sintoma (log/HTTP)                                                    | Causa provável                                   | Como corrigir                                                                                                           |
| --------------------------------------------------------------------- | ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| `503 billing_unconfigured` nos endpoints de billing                   | Vars do Stripe faltando                          | Preencher `.env` (`STRIPE_*`) e reiniciar o `api` se necessário.                                                        |
| `create-portal-session → 500` e mensagem “No configuration provided…” | Portal de teste **não salvo**                    | Em *Customer portal* (Test mode), configure e **Save changes**; opcional: usar `STRIPE_PORTAL_CONFIGURATION_ID=pc_...`. |
| Checkout `500`                                                        | Price id incorreto ou moeda diferente            | Checar `STRIPE_PRICE_ID_*` e a moeda do produto.                                                                        |
| Webhook `KeyError: current_period_start`                              | Mudança na payload do Stripe                     | (Já tratado) Handler faz `retrieve()` e usa `billing_cycle_anchor` como fallback.                                       |
| Portal abre mas não mostra “Plus”                                     | Só há **EUR** para Plus; cliente está em **USD** | Crie **price USD** para Plus e adicione o produto nos *Subscription products*.                                          |
| Toast frontend “body stream already read”                             | Resposta lida 2x                                 | No fetch, parseie **uma** vez (`await res.json()` **ou** `await res.text()`).                                           |

## Observabilidade & evidências

* Métricas expostas em `/metrics`: `billing_events_total{event}`, `checkout_sessions_created_total{plan_tier}`, `entitlement_denials_total{feature,plan}` .
* Evidência:

  ```bash
  make billing-smoke | tee docs/certification/EVIDENCE/billing_smoke.txt
  ```

---

## 2) Acrescentar em `docs/api/billing.md` (logo após a lista de endpoints)

```md
## cURL de exemplo

### Entitlements
```bash
curl -s "http://localhost:8000/api/v1/billing/entitlements?store_id=<STORE_UUID>" \
 -H "Authorization: Bearer <token>"
````

### Usage

```bash
curl -s "http://localhost:8000/api/v1/billing/usage?store_id=<STORE_UUID>" \
 -H "Authorization: Bearer <token>"
```

### Checkout (Pro)

```bash
curl -s -X POST "http://localhost:8000/api/v1/billing/create-checkout-session?store_id=<STORE_UUID>" \
 -H "Authorization: Bearer <token>" \
 -H "Content-Type: application/json" \
 -d '{"plan_tier":"pro","success_url":"http://localhost:8080/billing?success=true","cancel_url":"http://localhost:8080/billing"}'
```

### Portal

```bash
curl -s -X POST "http://localhost:8000/api/v1/billing/create-portal-session?store_id=<STORE_UUID>&return_url=http://localhost:8080/billing" \
 -H "Authorization: Bearer <token>"
```

## Códigos de erro padronizados

* `503` → `{ "detail": { "code": "billing_unconfigured", ... } }` quando Stripe não está configurado .
* `400` → `{ "detail": { "code": "stripe_customer_missing" } }` ao abrir portal sem `customer`.
* (Opcional) `400` → `{ "detail": { "code": "portal_not_configured" } }` se a API propagar o erro do portal sem default config.

---

### With these steps Milestone 5 (Billing/Stripe) is fully operational in test mode and ready for sandboxes or pilot stores.
