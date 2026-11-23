#!/usr/bin/env bash

set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"

if [[ ! -f "$RAIZ/.env" ]]; then
  echo "ERRO: Arquivo .env não encontrado. Utilize o .env.example como base." >&2
  exit 1
fi

set -a
source "$RAIZ/.env"
set +a
export PGCLIENTENCODING=UTF8

echo ">> 1/4 Criando tabelas e colunas (DDL)..."
psql -v ON_ERROR_STOP=1 -f "$RAIZ/sql/01_ddl_star_schema.sql"

echo ">> 2/4 Executando carga de dados..."
psql -v ON_ERROR_STOP=1 --single-transaction -f "$RAIZ/sql/02_carga_dados.sql"

echo ">> 3/4 Criando views de Regras de Negócio (ODS 5 e ODS 18)..."
psql -v ON_ERROR_STOP=1 -f "$RAIZ/sql/04_regras_negocio_views.sql"

echo ">> 4/4 Validando a carga e indicadores:"
psql -v ON_ERROR_STOP=1 -f "$RAIZ/sql/03_validacao.sql"
