"""Camada de acesso a dados do Dashboard (PostgreSQL Cloud SQL + fallbacks seguros).

Prioridade de conexão:
1. PostgreSQL via `st.secrets["postgres"]`, `st.secrets["DATABASE_URL"]` ou variáveis de ambiente (.env).
2. Base tratada local (`data/processed/base_tratada_stem.csv`) para desenvolvimento offline.
3. Conjunto demonstrativo calibrado nos totais oficiais do Censo STEM 2024 (apenas preview sem banco).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

try:
    from metrics import normalizar_colunas_analiticas
except ImportError:
    from dashboard.metrics import normalizar_colunas_analiticas

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ_PROJETO / ".env")

QUERY_VIEW_ANALITICA = """
SELECT
    ano_censo,
    id_ies,
    categoria_adm,
    categoria_adm_desc,
    rede,
    rede_desc,
    id_curso,
    nome_curso,
    area_geral,
    area_especifica,
    modalidade,
    modalidade_desc,
    id_municipio,
    nome_municipio,
    mesorregiao,
    sigla_uf,
    regiao,
    qt_ingressantes,
    qt_matriculados,
    qt_concluintes,
    qt_desvinculados,
    qt_trancados,
    qt_transferidos,
    qt_ing_fem,
    qt_ing_masc,
    qt_ing_branca,
    qt_ing_preta,
    qt_ing_parda,
    qt_ing_amarela,
    qt_ing_indigena,
    qt_ing_cornd,
    qt_mat_fem,
    qt_mat_masc,
    qt_mat_branca,
    qt_mat_preta,
    qt_mat_parda,
    qt_mat_amarela,
    qt_mat_indigena,
    qt_mat_cornd,
    qt_conc_fem,
    qt_conc_masc,
    qt_conc_branca,
    qt_conc_preta,
    qt_conc_parda,
    qt_conc_amarela,
    qt_conc_indigena,
    qt_conc_cornd
FROM vw_base_analitica_stem
"""

QUERY_STAR_SCHEMA_DIRETO = """
SELECT
    f.ano_censo,
    f.id_ies,
    i.categoria_adm,
    i.rede,
    f.id_curso,
    c.nome_curso,
    c.area_geral,
    c.area_especifica,
    c.modalidade,
    f.id_municipio,
    l.sigla_uf,
    l.regiao,
    f.qt_ingressantes,
    f.qt_matriculados,
    f.qt_concluintes,
    f.qt_desvinculados,
    f.qt_trancados,
    f.qt_transferidos,
    f.qt_ing_fem,
    f.qt_ing_masc,
    f.qt_ing_branca,
    f.qt_ing_preta,
    f.qt_ing_parda,
    f.qt_ing_amarela,
    f.qt_ing_indigena,
    f.qt_ing_cornd,
    f.qt_mat_fem,
    f.qt_mat_masc,
    f.qt_mat_branca,
    f.qt_mat_preta,
    f.qt_mat_parda,
    f.qt_mat_amarela,
    f.qt_mat_indigena,
    f.qt_mat_cornd,
    f.qt_conc_fem,
    f.qt_conc_masc,
    f.qt_conc_branca,
    f.qt_conc_preta,
    f.qt_conc_parda,
    f.qt_conc_amarela,
    f.qt_conc_indigena,
    f.qt_conc_cornd
FROM fato_metricas_evasao f
INNER JOIN dim_instituicao i ON i.id_ies = f.id_ies
INNER JOIN dim_curso       c ON c.id_curso = f.id_curso
LEFT  JOIN dim_localidade  l ON l.id_municipio = f.id_municipio
"""


def _obter_config_postgres() -> dict[str, Any] | None:
    """Lê credenciais PostgreSQL de st.secrets ou variáveis de ambiente."""
    try:
        if "DATABASE_URL" in st.secrets:
            return {"dsn": st.secrets["DATABASE_URL"]}
        if "postgres" in st.secrets:
            sec = st.secrets["postgres"]
            if sec.get("host") and sec.get("password"):
                return {
                    "host": sec["host"],
                    "port": int(sec.get("port", 5432)),
                    "dbname": sec.get("database", "observatorio_stem"),
                    "user": sec.get("user", "etl_user"),
                    "password": sec["password"],
                    "sslmode": sec.get("sslmode", "require"),
                }
    except Exception:
        pass

    if os.getenv("DATABASE_URL"):
        return {"dsn": os.environ["DATABASE_URL"]}

    if os.getenv("PGHOST") and os.getenv("PGPASSWORD"):
        return {
            "host": os.environ["PGHOST"],
            "port": int(os.getenv("PGPORT", "5432")),
            "dbname": os.getenv("PGDATABASE", "observatorio_stem"),
            "user": os.getenv("PGUSER", "etl_user"),
            "password": os.environ["PGPASSWORD"],
            "sslmode": os.getenv("PGSSLMODE", "prefer"),
        }

    return None


def _carregar_postgres(cfg: dict[str, Any]) -> pd.DataFrame:
    import psycopg2

    conn = psycopg2.connect(**cfg, connect_timeout=10)
    try:
        try:
            df = pd.read_sql_query(QUERY_VIEW_ANALITICA, conn)
        except Exception:
            conn.rollback()
            df = pd.read_sql_query(QUERY_STAR_SCHEMA_DIRETO, conn)
    finally:
        conn.close()

    return normalizar_colunas_analiticas(df)


def _gerar_dataset_demonstracao() -> pd.DataFrame:
    """Dataset demonstrativo calibrado nos indicadores reais do Censo STEM 2024."""
    registros = []
    ufs = [
        ("Nordeste", "BA", "Salvador", "Metropolitana de Salvador", 2927408, 1.00, 0.72),
        ("Nordeste", "PE", "Recife", "Metropolitana de Recife", 2611606, 0.96, 0.61),
        ("Nordeste", "PB", "João Pessoa", "Mata Paraibana", 2507507, 0.80, 0.63),
        ("Nordeste", "RN", "Natal", "Leste Potiguar", 2408102, 0.80, 0.60),
        ("Sudeste", "SP", "São Paulo", "Metropolitana de São Paulo", 3550308, 0.97, 0.36),
        ("Sudeste", "RJ", "Rio de Janeiro", "Metropolitana do Rio de Janeiro", 3304557, 1.02, 0.49),
        ("Sudeste", "MG", "Belo Horizonte", "Metropolitana de Belo Horizonte", 3106200, 0.94, 0.54),
        ("Sul", "PR", "Curitiba", "Metropolitana de Curitiba", 4106902, 0.93, 0.28),
        ("Sul", "RS", "Porto Alegre", "Metropolitana de Porto Alegre", 4314902, 0.91, 0.21),
        ("Centro-Oeste", "DF", "Brasília", "Distrito Federal", 5300108, 0.95, 0.52),
        ("Norte", "AM", "Manaus", "Centro Amazonense", 1302603, 1.24, 0.76),
        ("Norte", "RO", "Porto Velho", "Madeira-Guaporé", 1100205, 1.27, 0.68),
    ]
    cursos = [
        (
            101,
            "Análise e Desenvolvimento de Sistemas",
            "Computação e Tecnologias da Informação e Comunicação (TIC)",
            "Desenvolvimento de software e aplicativos",
            0.378,
            0.21,
        ),
        (
            102,
            "Ciência da Computação",
            "Computação e Tecnologias da Informação e Comunicação (TIC)",
            "Computação e tecnologias da informação",
            0.340,
            0.19,
        ),
        (
            201,
            "Engenharia Civil",
            "Engenharia, produção e construção",
            "Engenharia e profissões correlatas",
            0.289,
            0.32,
        ),
        (
            202,
            "Engenharia de Produção",
            "Engenharia, produção e construção",
            "Manufatura e processamento",
            0.275,
            0.36,
        ),
        (
            301,
            "Matemática",
            "Ciências naturais, matemática e estatística",
            "Matemática e estatística",
            0.255,
            0.44,
        ),
        (
            302,
            "Ciências Biológicas",
            "Ciências naturais, matemática e estatística",
            "Ciências biológicas e correlatas",
            0.232,
            0.56,
        ),
    ]
    perfis_oferta = [
        (1, 1, 1, 0.54, 1.15),  # Pública Federal Presencial (~16.8% evasão)
        (2, 1, 2, 0.85, 0.92),  # Pública Estadual EaD
        (4, 2, 1, 0.95, 1.00),  # Privada c/ fins lucrativos Presencial
        (4, 2, 2, 1.44, 0.86),  # Privada c/ fins lucrativos EaD (~47.1% evasão)
        (5, 2, 1, 0.88, 1.05),  # Privada s/ fins lucrativos Presencial
    ]

    id_ies_seq = 1000
    for ano, fator_ano in [(2022, 0.91), (2023, 0.96), (2024, 1.00)]:
        for regiao, uf, mun, meso, cod_mun, fator_ev_uf, share_ppi_uf in ufs:
            for id_c, nome_c, area_g, area_e, ev_base, share_fem_base in cursos:
                for cat_adm, rede, mod, fator_ev_mod, fator_conc in perfis_oferta:
                    id_ies_seq += 1
                    mat = int(round(1250 * fator_ano * (1.35 if mod == 2 and rede == 2 else 0.72)))
                    ing = int(round(mat * (0.55 if mod == 2 else 0.41)))
                    ev_rate = min(0.68, ev_base * fator_ev_uf * fator_ev_mod)
                    desv = int(round(mat * ev_rate))
                    tranc = int(round(mat * (0.14 if mod == 2 else 0.08)))
                    transf = int(round(mat * 0.045))
                    conc = int(round(mat * 0.125 * fator_conc))

                    # Gênero (ODS 5): ligeira variação entre ingresso e conclusão
                    fem_ing_p = max(0.10, min(0.65, share_fem_base))
                    fem_mat_p = max(0.10, min(0.65, share_fem_base - 0.01))
                    fem_conc_p = max(0.10, min(0.68, share_fem_base + 0.015))

                    # Raça/Cor (ODS 18): inclui cornd (~18% de subnotificação na privada EaD, menor na pública)
                    cornd_p = 0.24 if (rede == 2 and mod == 2) else 0.11
                    ppi_ing_p = share_ppi_uf * (1.0 - cornd_p)
                    ppi_mat_p = (share_ppi_uf - 0.015) * (1.0 - cornd_p)
                    ppi_conc_p = max(0.08, (share_ppi_uf - 0.05) * (1.0 - cornd_p))

                    def split_raca(total: int, ppi_p: float) -> tuple[int, int, int, int, int, int]:
                        cornd = int(round(total * cornd_p))
                        amarela = int(round(total * 0.018))
                        ppi = int(round(total * ppi_p))
                        preta = int(round(ppi * 0.22))
                        indigena = max(1, int(round(ppi * 0.025)))
                        parda = max(0, ppi - preta - indigena)
                        branca = max(0, total - cornd - amarela - preta - parda - indigena)
                        return branca, preta, parda, amarela, indigena, cornd

                    ing_b, ing_pr, ing_pa, ing_am, ing_in, ing_nd = split_raca(ing, ppi_ing_p)
                    mat_b, mat_pr, mat_pa, mat_am, mat_in, mat_nd = split_raca(mat, ppi_mat_p)
                    con_b, con_pr, con_pa, con_am, con_in, con_nd = split_raca(conc, ppi_conc_p)

                    registros.append(
                        {
                            "ano_censo": ano,
                            "id_ies": id_ies_seq,
                            "categoria_adm": cat_adm,
                            "rede": rede,
                            "id_curso": id_c * 10 + mod,
                            "nome_curso": nome_c,
                            "area_geral": area_g,
                            "area_especifica": area_e,
                            "modalidade": mod,
                            "id_municipio": cod_mun,
                            "nome_municipio": mun,
                            "mesorregiao": meso,
                            "sigla_uf": uf,
                            "regiao": regiao,
                            "qt_ingressantes": ing,
                            "qt_matriculados": mat,
                            "qt_concluintes": conc,
                            "qt_desvinculados": desv,
                            "qt_trancados": tranc,
                            "qt_transferidos": transf,
                            "qt_ing_fem": int(round(ing * fem_ing_p)),
                            "qt_ing_masc": ing - int(round(ing * fem_ing_p)),
                            "qt_ing_branca": ing_b,
                            "qt_ing_preta": ing_pr,
                            "qt_ing_parda": ing_pa,
                            "qt_ing_amarela": ing_am,
                            "qt_ing_indigena": ing_in,
                            "qt_ing_cornd": ing_nd,
                            "qt_mat_fem": int(round(mat * fem_mat_p)),
                            "qt_mat_masc": mat - int(round(mat * fem_mat_p)),
                            "qt_mat_branca": mat_b,
                            "qt_mat_preta": mat_pr,
                            "qt_mat_parda": mat_pa,
                            "qt_mat_amarela": mat_am,
                            "qt_mat_indigena": mat_in,
                            "qt_mat_cornd": mat_nd,
                            "qt_conc_fem": int(round(conc * fem_conc_p)),
                            "qt_conc_masc": conc - int(round(conc * fem_conc_p)),
                            "qt_conc_branca": con_b,
                            "qt_conc_preta": con_pr,
                            "qt_conc_parda": con_pa,
                            "qt_conc_amarela": con_am,
                            "qt_conc_indigena": con_in,
                            "qt_conc_cornd": con_nd,
                        }
                    )

    return normalizar_colunas_analiticas(pd.DataFrame(registros))


@st.cache_data(ttl=600, show_spinner="Carregando dados do Observatório STEM...")
def carregar_dados() -> tuple[pd.DataFrame, str, str | None]:
    """Retorna (DataFrame analítico, origem_label, aviso_opcional)."""
    cfg = _obter_config_postgres()
    if cfg:
        try:
            df = _carregar_postgres(cfg)
            return df, "PostgreSQL (Google Cloud SQL)", None
        except Exception as exc:
            aviso_db = f"Não foi possível conectar ao PostgreSQL ({exc}). Usando fallback."
    else:
        aviso_db = None

    csv_local = RAIZ_PROJETO / "data" / "processed" / "base_tratada_stem.csv"
    if csv_local.exists():
        df_csv = pd.read_csv(csv_local, sep=";", dtype={"CO_MUNICIPIO": "Int64"})
        return normalizar_colunas_analiticas(df_csv), "CSV Tratado Local", aviso_db

    df_demo = _gerar_dataset_demonstracao()
    aviso = (
        aviso_db
        or "Credenciais PostgreSQL não configuradas em `.env` ou Streamlit Secrets. "
        "Exibindo conjunto demonstrativo calibrado (2022–2024) para navegação."
    )
    return df_demo, "Modo Demonstração (Calibrado)", aviso
