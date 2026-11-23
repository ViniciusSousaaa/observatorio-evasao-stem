"""Pipeline ETL para os microdados do Censo da Educação Superior (INEP).

Suporta processamento multi-ano em chunks, filtragem das áreas STEM (CINE),
padronização de tipos, tratamento de nulos, remoção de duplicatas, download
opcional direto do portal do INEP e geração de relatório JSON de qualidade
(Veracidade).
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

INEP_URL_TEMPLATE = (
    "https://download.inep.gov.br/microdados/"
    "microdados_censo_da_educacao_superior_{ano}.zip"
)

AREAS_STEM = [
    "Computação e Tecnologias da Informação e Comunicação (TIC)",
    "Engenharia, produção e construção",
    "Ciências naturais, matemática e estatística",
]

COLUNAS_DESCRITIVAS = [
    "NU_ANO_CENSO",
    "CO_IES",
    "TP_CATEGORIA_ADMINISTRATIVA",
    "TP_REDE",
    "SG_UF",
    "CO_MUNICIPIO",
    "NO_REGIAO",
    "CO_CURSO",
    "NO_CURSO",
    "NO_CINE_AREA_GERAL",
    "NO_CINE_AREA_ESPECIFICA",
    "TP_MODALIDADE_ENSINO",
]

METRICAS_FLUXO = [
    "QT_ING",
    "QT_MAT",
    "QT_CONC",
    "QT_SIT_DESVINCULADO",
    "QT_SIT_TRANCADA",
    "QT_SIT_TRANSFERIDO",
]

PERFIS = ["FEM", "MASC", "BRANCA", "PRETA", "PARDA", "AMARELA", "INDIGENA", "CORND"]
METRICAS_PERFIL = [
    f"{etapa}_{perfil}"
    for etapa in ["QT_ING", "QT_MAT", "QT_CONC"]
    for perfil in PERFIS
]

METRICAS = METRICAS_FLUXO + METRICAS_PERFIL
TODAS_COLUNAS = COLUNAS_DESCRITIVAS + METRICAS


def baixar_microdados_inep(ano: int, raw_dir: Path) -> Path:
    """Baixa o pacote ZIP oficial do Censo da Educação Superior para o ano."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    destino = raw_dir / f"microdados_censo_da_educacao_superior_{ano}.zip"
    if destino.exists():
        print(f"Arquivo já existe localmente: {destino}")
        return destino

    url = INEP_URL_TEMPLATE.format(ano=ano)
    print(f"Baixando microdados do INEP ({ano}): {url}")
    urllib.request.urlretrieve(url, destino)
    print(f"Download concluído: {destino} ({destino.stat().st_size / (1024 * 1024):.1f} MB)")
    return destino


def localizar_csv_cursos(zip_path: Path) -> str:
    """Localiza o arquivo MICRODADOS_CADASTRO_CURSOS_*.CSV dentro do ZIP."""
    padrao = re.compile(r"MICRODADOS_CADASTRO_CURSOS_\d{4}\.CSV$", re.IGNORECASE)
    with zipfile.ZipFile(zip_path) as z:
        for nome in z.namelist():
            if padrao.search(nome):
                return nome
    raise FileNotFoundError(
        f"Nenhum arquivo MICRODADOS_CADASTRO_CURSOS_AAAA.CSV encontrado em {zip_path}"
    )


def descobrir_arquivos_zip(raw_dir: Path, anos: list[int] | None, baixar: bool) -> list[Path]:
    """Descobre ou baixa os arquivos ZIP a processar."""
    if anos:
        arquivos: list[Path] = []
        for ano in sorted(set(anos)):
            caminho = raw_dir / f"microdados_censo_da_educacao_superior_{ano}.zip"
            if not caminho.exists() and baixar:
                caminho = baixar_microdados_inep(ano, raw_dir)
            if not caminho.exists():
                raise FileNotFoundError(
                    f"Arquivo não encontrado: {caminho}. "
                    f"Baixe manualmente ou execute com --baixar."
                )
            arquivos.append(caminho)
        return arquivos

    encontrados = sorted(raw_dir.glob("microdados_censo_da_educacao_superior_*.zip"))
    if encontrados:
        return encontrados

    if baixar:
        return [baixar_microdados_inep(2024, raw_dir)]

    raise FileNotFoundError(
        f"Nenhum microdado encontrado em {raw_dir}. "
        "Coloque o .zip do INEP em data/raw/ ou execute com --baixar --anos 2024."
    )


def processar_zip(zip_path: Path, tamanho_lote: int = 50000) -> tuple[pd.DataFrame, dict]:
    """Lê e filtra um arquivo ZIP do INEP em lotes, retornando DataFrame e métricas."""
    nome_csv = localizar_csv_cursos(zip_path)
    print(f"Lendo {zip_path.name} -> {nome_csv} em lotes de {tamanho_lote} linhas...")

    lotes: list[pd.DataFrame] = []
    total_lido = 0

    with zipfile.ZipFile(zip_path) as z, z.open(nome_csv) as arquivo:
        leitor = pd.read_csv(
            arquivo,
            sep=";",
            encoding="latin-1",
            usecols=lambda c: c in TODAS_COLUNAS,
            chunksize=tamanho_lote,
            dtype={
                "SG_UF": str,
                "NO_REGIAO": str,
                "NO_CURSO": str,
                "NO_CINE_AREA_GERAL": str,
                "NO_CINE_AREA_ESPECIFICA": str,
            },
        )
        for lote in leitor:
            total_lido += len(lote)
            filtrado = lote[lote["NO_CINE_AREA_GERAL"].isin(AREAS_STEM)]
            if not filtrado.empty:
                lotes.append(filtrado)

    if not lotes:
        df_ano = pd.DataFrame(columns=TODAS_COLUNAS)
    else:
        df_ano = pd.concat(lotes, ignore_index=True)

    # Garante presença de todas as colunas esperadas mesmo se alguma variar entre edições
    for col in TODAS_COLUNAS:
        if col not in df_ano.columns:
            df_ano[col] = 0 if col in METRICAS else pd.NA

    nulos_metricas = int(df_ano[METRICAS].isna().sum().sum())
    df_ano[METRICAS] = df_ano[METRICAS].fillna(0).clip(lower=0).astype(int)
    df_ano["CO_MUNICIPIO"] = pd.to_numeric(df_ano["CO_MUNICIPIO"], errors="coerce").astype("Int64")

    antes_dedup = len(df_ano)
    df_ano = df_ano.drop_duplicates()
    duplicatas_removidas = antes_dedup - len(df_ano)

    df_ano = df_ano[TODAS_COLUNAS]

    resumo_ano = {
        "arquivo": zip_path.name,
        "csv_interno": nome_csv,
        "linhas_lidas_brutas": total_lido,
        "linhas_stem_validas": len(df_ano),
        "reducao_volume_pct": round((1 - len(df_ano) / total_lido) * 100, 2) if total_lido else 0.0,
        "nulos_imputados_zero": nulos_metricas,
        "duplicatas_removidas": duplicatas_removidas,
        "linhas_sem_municipio_ead": int(df_ano["CO_MUNICIPIO"].isna().sum()),
    }
    return df_ano, resumo_ano


def tratar_base(
    zip_paths: list[Path],
    saida_path: Path,
    relatorio_path: Path | None = None,
    tamanho_lote: int = 50000,
) -> pd.DataFrame:
    """Executa o tratamento completo para um ou mais arquivos anuais do INEP."""
    frames: list[pd.DataFrame] = []
    resumos_arquivos: list[dict] = []

    for zp in zip_paths:
        df_ano, resumo = processar_zip(zp, tamanho_lote=tamanho_lote)
        frames.append(df_ano)
        resumos_arquivos.append(resumo)

    df = pd.concat(frames, ignore_index=True).drop_duplicates()
    df = df[TODAS_COLUNAS]

    saida_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(saida_path, sep=";", index=False, encoding="utf-8")

    total_mat = int(df["QT_MAT"].sum())
    total_cornd = int(df["QT_MAT_CORND"].sum())
    pct_cornd = round((total_cornd / total_mat) * 100, 2) if total_mat else 0.0

    relatorio = {
        "executado_em_utc": datetime.now(timezone.utc).isoformat(),
        "anos_processados": sorted(int(a) for a in df["NU_ANO_CENSO"].dropna().unique()),
        "total_linhas_brutas": sum(r["linhas_lidas_brutas"] for r in resumos_arquivos),
        "total_linhas_stem_finais": len(df),
        "total_instituicoes": int(df["CO_IES"].nunique()),
        "total_cursos": int(df["CO_CURSO"].nunique()),
        "total_municipios": int(df["CO_MUNICIPIO"].dropna().nunique()),
        "veracidade": {
            "total_nulos_metricas_imputados_zero": sum(r["nulos_imputados_zero"] for r in resumos_arquivos),
            "total_duplicatas_removidas": sum(r["duplicatas_removidas"] for r in resumos_arquivos),
            "linhas_ead_sem_municipio_preservadas": int(df["CO_MUNICIPIO"].isna().sum()),
            "taxa_cor_nao_declarada_matriculas_pct": pct_cornd,
            "lgpd_sem_dados_pessoais_identificaveis": True,
        },
        "totais_consolidados": {
            "ingressantes": int(df["QT_ING"].sum()),
            "matriculados": total_mat,
            "concluintes": int(df["QT_CONC"].sum()),
            "desvinculados": int(df["QT_SIT_DESVINCULADO"].sum()),
            "trancados": int(df["QT_SIT_TRANCADA"].sum()),
            "transferidos": int(df["QT_SIT_TRANSFERIDO"].sum()),
            "matriculas_femininas": int(df["QT_MAT_FEM"].sum()),
            "matriculas_ppi": int(
                df["QT_MAT_PRETA"].sum() + df["QT_MAT_PARDA"].sum() + df["QT_MAT_INDIGENA"].sum()
            ),
        },
        "detalhes_por_arquivo": resumos_arquivos,
    }

    if relatorio_path:
        relatorio_path.parent.mkdir(parents=True, exist_ok=True)
        relatorio_path.write_text(
            json.dumps(relatorio, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Relatório de qualidade (JSON) salvo em: {relatorio_path}")

    print(f"Linhas brutas lidas: {relatorio['total_linhas_brutas']}")
    print(f"Linhas STEM finais:  {relatorio['total_linhas_stem_finais']}")
    print(f"Anos processados:    {relatorio['anos_processados']}")
    print(f"Base tratada salva em: {saida_path}")
    return df


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ETL dos microdados do Censo da Educação Superior (INEP) para cursos STEM."
    )
    parser.add_argument(
        "--anos",
        type=int,
        nargs="+",
        default=None,
        help="Lista de anos para processar (ex: --anos 2022 2023 2024). Se omitido, processa todos os .zip em data/raw/.",
    )
    parser.add_argument(
        "--baixar",
        action="store_true",
        help="Baixa automaticamente os arquivos .zip faltantes direto do portal oficial do INEP.",
    )
    parser.add_argument(
        "--raw-dir",
        default="data/raw",
        help="Diretório de entrada dos arquivos .zip do INEP.",
    )
    parser.add_argument(
        "--saida",
        default="data/processed/base_tratada_stem.csv",
        help="Caminho de saída da base tratada consolidada em UTF-8.",
    )
    parser.add_argument(
        "--relatorio",
        default="data/processed/relatorio_qualidade_etl.json",
        help="Caminho do relatório semi-estruturado (JSON) de qualidade/veracidade.",
    )
    parser.add_argument(
        "--tamanho-lote",
        type=int,
        default=50000,
        help="Quantidade de linhas por chunk de leitura.",
    )
    args = parser.parse_args()

    zips = descobrir_arquivos_zip(Path(args.raw_dir), args.anos, args.baixar)
    tratar_base(
        zip_paths=zips,
        saida_path=Path(args.saida),
        relatorio_path=Path(args.relatorio),
        tamanho_lote=args.tamanho_lote,
    )


if __name__ == "__main__":
    main()
