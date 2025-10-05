# Newman – Webhooks folder (CI automation)
# Registrado automaticamente pelo job `Backend CI / smoke-newman` após o smoke CLI gerar eventos reais.
# O arquivo é sobrescrito na pipeline com o resumo do comando abaixo:
#   newman run docs/postman/state-tax-wizard.postman_collection.json \
#     --folder Webhooks --environment ci.newman_environment.json --reporters cli
#
# Para execução manual fora da pipeline:
#   1. Inicie o backend (`uvicorn app.main:app --host 0.0.0.0 --port 8000`).
#   2. Copie `.env.example` para `.env` (mesmo nos ambientes locais) para reproduzir o setup da pipeline.
#   3. Rode `python backend/smoke_test.py --webhooks-only` para gerar ao menos um evento `fee.applied`.
#   4. Gere um environment JSON com token/store_id (ver `.github/workflows/backend.yml`, passo "Generate Newman environment").
#   5. Execute o comando Newman acima e capture a saída neste arquivo.
#
# A primeira execução na pipeline atualiza este documento automaticamente com o log real (≤512 KB).
