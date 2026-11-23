#!/usr/bin/env bash
# Dá ao app (o service principal dele) acesso de leitura à silver e à gold.
#
# O app é um "usuário" do Unity Catalog e nasce sem acesso nenhum: sem estes
# grants o build do app falha no typegen com INSUFFICIENT_PERMISSIONS.
# Rode depois do primeiro `databricks bundle deploy` do app (é ele que cria o
# service principal) e antes do `databricks apps deploy`.
#
# Uso: bash scripts/conceder-acesso.sh [nome-do-app]   (padrão: minha-torre)
set -euo pipefail

APP="${1:-minha-torre}"
PROFILE="DEFAULT"
CATALOGO="farol_projeto"

# 1. O client id do service principal do app
SP=$(databricks apps get "$APP" --profile "$PROFILE" -o json \
  | grep -o '"service_principal_client_id": *"[^"]*"' \
  | sed 's/.*: *"\(.*\)"/\1/')

if [ -z "$SP" ]; then
  echo "Não achei o service_principal_client_id do app '$APP'. Ele já foi criado com 'databricks bundle deploy'?" >&2
  exit 1
fi
echo "App $APP · service principal $SP"

# 2. USE CATALOG no catálogo
databricks grants update catalog "$CATALOGO" --profile "$PROFILE" \
  --json "{\"changes\":[{\"principal\":\"$SP\",\"add\":[\"USE_CATALOG\"]}]}" > /dev/null
echo "  USE CATALOG em $CATALOGO"

# 3. USE SCHEMA + SELECT na gold e na silver (o SELECT no schema vale também
#    para tabelas criadas depois, como o gold.score_estouro_30d do modelo)
for SCHEMA in gold silver; do
  databricks grants update schema "$CATALOGO.$SCHEMA" --profile "$PROFILE" \
    --json "{\"changes\":[{\"principal\":\"$SP\",\"add\":[\"USE_SCHEMA\",\"SELECT\"]}]}" > /dev/null
  echo "  USE SCHEMA + SELECT em $CATALOGO.$SCHEMA"
done

echo "Pronto. Agora: cd $APP && databricks apps deploy --profile $PROFILE"
