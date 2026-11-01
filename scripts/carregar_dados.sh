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

echo ">> Criando tabelas (DDL)..."
psql -v ON_ERROR_STOP=1 -f "$RAIZ/sql/01_ddl_star_schema.sql"

echo ">> Executando carga de dados..."
psql -v ON_ERROR_STOP=1 --single-transaction -f "$RAIZ/sql/02_carga_dados.sql"

echo ">> Validando a carga:"
psql -v ON_ERROR_STOP=1 -f "$RAIZ/sql/03_validacao.sql"
