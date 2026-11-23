"""Converte a base tratada STEM (CSV) + metadados IBGE (JSON) em carga SQL.

Gera `sql/02_carga_dados.sql` em blocos de 1.000 linhas para o modelo Star Schema
(`dim_instituicao`, `dim_curso`, `dim_localidade`, `fato_metricas_evasao`).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

try:
    from enriquecer_ibge import carregar_mapa_ibge
except ImportError:
    from etl.python.enriquecer_ibge import carregar_mapa_ibge

TAMANHO_LOTE = 1000

PERFIS = ["fem", "masc", "branca", "preta", "parda", "amarela", "indigena", "cornd"]

COLUNAS_FATO = {
    "CO_IES": "id_ies",
    "CO_CURSO": "id_curso",
    "CO_MUNICIPIO": "id_municipio",
    "NU_ANO_CENSO": "ano_censo",
    "QT_ING": "qt_ingressantes",
    "QT_MAT": "qt_matriculados",
    "QT_CONC": "qt_concluintes",
    "QT_SIT_DESVINCULADO": "qt_desvinculados",
    "QT_SIT_TRANCADA": "qt_trancados",
    "QT_SIT_TRANSFERIDO": "qt_transferidos",
}
for etapa in ["ing", "mat", "conc"]:
    for perfil in PERFIS:
        COLUNAS_FATO[f"QT_{etapa.upper()}_{perfil.upper()}"] = f"qt_{etapa}_{perfil}"


def valor_sql(valor) -> str:
    if pd.isna(valor):
        return "NULL"
    if isinstance(valor, str):
        return "'" + valor.replace("'", "''") + "'"
    return str(int(valor))


def escrever_inserts(f, tabela: str, colunas_banco: list[str], linhas: list, conflito: str | None = None) -> None:
    sufixo = f" ON CONFLICT ({conflito}) DO NOTHING" if conflito else ""
    for inicio in range(0, len(linhas), TAMANHO_LOTE):
        lote = linhas[inicio : inicio + TAMANHO_LOTE]
        valores = ",\n".join(
            "(" + ", ".join(valor_sql(v) for v in linha) + ")" for linha in lote
        )
        f.write(
            f"INSERT INTO {tabela} ({', '.join(colunas_banco)}) VALUES\n{valores}{sufixo};\n\n"
        )


def csv_para_sql(
    csv_path: str | Path,
    sql_output_path: str | Path,
    ibge_json_path: str | Path = "data/processed/dim_municipios_ibge.json",
) -> None:
    print(f"Lendo o arquivo: {csv_path}...")

    df = pd.read_csv(csv_path, sep=";", dtype={"CO_MUNICIPIO": "Int64"})
    if "NU_ANO_CENSO" in df.columns:
        df = df.sort_values("NU_ANO_CENSO")

    dim_ies = df[["CO_IES", "TP_CATEGORIA_ADMINISTRATIVA", "TP_REDE"]].drop_duplicates(
        "CO_IES", keep="last"
    )
    dim_curso = df[
        ["CO_CURSO", "NO_CURSO", "NO_CINE_AREA_GERAL", "NO_CINE_AREA_ESPECIFICA", "TP_MODALIDADE_ENSINO"]
    ].drop_duplicates("CO_CURSO", keep="last")
    dim_loc = (
        df[["CO_MUNICIPIO", "SG_UF", "NO_REGIAO"]]
        .dropna(subset=["CO_MUNICIPIO"])
        .drop_duplicates("CO_MUNICIPIO", keep="last")
        .copy()
    )

    mapa_ibge = carregar_mapa_ibge(ibge_json_path)
    if mapa_ibge:
        print(f"Enriquecendo dim_localidade com {len(mapa_ibge)} municípios da API do IBGE...")
        dim_loc["nome_municipio"] = dim_loc["CO_MUNICIPIO"].map(
            lambda c: mapa_ibge.get(int(c), {}).get("nome_municipio")
        )
        dim_loc["mesorregiao"] = dim_loc["CO_MUNICIPIO"].map(
            lambda c: mapa_ibge.get(int(c), {}).get("mesorregiao")
        )
    else:
        print(
            "Aviso: arquivo IBGE não encontrado; campos nome_municipio e mesorregiao "
            "serão gravados como NULL. Execute etl/python/enriquecer_ibge.py para enriquecer."
        )
        dim_loc["nome_municipio"] = pd.NA
        dim_loc["mesorregiao"] = pd.NA

    fato = df[list(COLUNAS_FATO)]

    sql_path = Path(sql_output_path)
    sql_path.parent.mkdir(parents=True, exist_ok=True)

    with open(sql_path, "w", encoding="utf-8") as f:
        print("Gerando INSERTS para Dimensões e Fato...")

        f.write(
            "TRUNCATE fato_metricas_evasao, dim_instituicao, dim_curso, dim_localidade RESTART IDENTITY;\n\n"
        )

        escrever_inserts(
            f,
            "dim_instituicao",
            ["id_ies", "categoria_adm", "rede"],
            dim_ies.values.tolist(),
            "id_ies",
        )
        escrever_inserts(
            f,
            "dim_curso",
            ["id_curso", "nome_curso", "area_geral", "area_especifica", "modalidade"],
            dim_curso.values.tolist(),
            "id_curso",
        )
        escrever_inserts(
            f,
            "dim_localidade",
            ["id_municipio", "sigla_uf", "regiao", "nome_municipio", "mesorregiao"],
            dim_loc[["CO_MUNICIPIO", "SG_UF", "NO_REGIAO", "nome_municipio", "mesorregiao"]].values.tolist(),
            "id_municipio",
        )
        escrever_inserts(
            f,
            "fato_metricas_evasao",
            list(COLUNAS_FATO.values()),
            fato.values.tolist(),
        )

    print(f"\nSucesso! Script SQL gerado em: {sql_path}")
    print(f"  dim_instituicao:      {len(dim_ies):>7}")
    print(f"  dim_curso:            {len(dim_curso):>7}")
    print(f"  dim_localidade:       {len(dim_loc):>7}")
    print(f"  fato_metricas_evasao: {len(fato):>7}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera script SQL de carga para o Star Schema do Observatório STEM."
    )
    parser.add_argument(
        "--entrada",
        default="data/processed/base_tratada_stem.csv",
        help="CSV tratado gerado por tratar_base.py.",
    )
    parser.add_argument(
        "--saida",
        default="sql/02_carga_dados.sql",
        help="Caminho do script SQL de saída.",
    )
    parser.add_argument(
        "--ibge-json",
        default="data/processed/dim_municipios_ibge.json",
        help="JSON de municípios gerado por enriquecer_ibge.py.",
    )
    args = parser.parse_args()
    csv_para_sql(args.entrada, args.saida, args.ibge_json)


if __name__ == "__main__":
    main()
