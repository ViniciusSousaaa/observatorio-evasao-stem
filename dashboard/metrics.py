"""Regras de Negócio e cálculos de indicadores (Evasão, ODS 5 e ODS 18).

Mantém paridade exata com as views SQL definidas em `sql/04_regras_negocio_views.sql`
para garantir consistência (Veracidade) entre banco de dados e dashboard.
"""

from __future__ import annotations

import pandas as pd

MAPA_REDE = {
    1: "Pública",
    2: "Privada",
}

MAPA_MODALIDADE = {
    1: "Presencial",
    2: "EaD",
}

MAPA_CATEGORIA_ADM = {
    1: "Pública Federal",
    2: "Pública Estadual",
    3: "Pública Municipal",
    4: "Privada com fins lucrativos",
    5: "Privada sem fins lucrativos",
    6: "Privada - Particular em sentido estrito",
    7: "Especial",
    8: "Privada comunitária",
    9: "Privada confessional",
}

COLUNAS_SOMA = [
    "qt_ingressantes",
    "qt_matriculados",
    "qt_concluintes",
    "qt_desvinculados",
    "qt_trancados",
    "qt_transferidos",
    "qt_ing_fem",
    "qt_ing_masc",
    "qt_ing_branca",
    "qt_ing_preta",
    "qt_ing_parda",
    "qt_ing_amarela",
    "qt_ing_indigena",
    "qt_ing_cornd",
    "qt_mat_fem",
    "qt_mat_masc",
    "qt_mat_branca",
    "qt_mat_preta",
    "qt_mat_parda",
    "qt_mat_amarela",
    "qt_mat_indigena",
    "qt_mat_cornd",
    "qt_conc_fem",
    "qt_conc_masc",
    "qt_conc_branca",
    "qt_conc_preta",
    "qt_conc_parda",
    "qt_conc_amarela",
    "qt_conc_indigena",
    "qt_conc_cornd",
]

METRICAS_DINAMICAS = {
    "taxa_evasao_matriculas_pct": {
        "label": "Taxa de Evasão sobre Matrículas (%)",
        "codigo": "RN01",
        "formato": "{:.2f}%",
        "escala": "Reds",
        "descricao": "Desvinculados / Matriculados no ano.",
    },
    "taxa_evasao_vinculos_pct": {
        "label": "Taxa de Evasão sobre Vínculos Totais (%)",
        "codigo": "RN02",
        "formato": "{:.2f}%",
        "escala": "OrRd",
        "descricao": "Desvinculados / (Matriculados + Desvinculados + Concluintes).",
    },
    "taxa_retencao_pct": {
        "label": "Taxa de Retenção Estimada (%)",
        "codigo": "RN03",
        "formato": "{:.2f}%",
        "escala": "Teal",
        "descricao": "100% - Taxa de Evasão sobre Vínculos Totais.",
    },
    "taxa_trancamento_pct": {
        "label": "Taxa de Trancamento — Risco Futuro (%)",
        "codigo": "RN04",
        "formato": "{:.2f}%",
        "escala": "YlOrBr",
        "descricao": "Matrículas trancadas / Matriculados.",
    },
    "taxa_transferencia_pct": {
        "label": "Taxa de Transferência (%)",
        "codigo": "RN05",
        "formato": "{:.2f}%",
        "escala": "Blues",
        "descricao": "Transferidos / Matriculados.",
    },
    "taxa_conclusao_pct": {
        "label": "Taxa de Conclusão sobre Matrículas (%)",
        "codigo": "RN06",
        "formato": "{:.2f}%",
        "escala": "Greens",
        "descricao": "Concluintes / Matriculados.",
    },
    "razao_conclusao_ingresso_pct": {
        "label": "Razão Concluintes / Ingressantes (%)",
        "codigo": "RN07",
        "formato": "{:.2f}%",
        "escala": "BuGn",
        "descricao": "Proxy de eficiência do funil acadêmico (Concluintes / Ingressantes).",
    },
    "pct_mat_fem": {
        "label": "ODS 5 — Participação Feminina nas Matrículas (%)",
        "codigo": "RN09",
        "formato": "{:.2f}%",
        "escala": "Purples",
        "descricao": "Matrículas femininas / Total de matrículas com sexo informado.",
    },
    "pct_mat_ppi_declarado": {
        "label": "ODS 18 — Participação PPI nas Matrículas (%)",
        "codigo": "RN16",
        "formato": "{:.2f}%",
        "escala": "YlGnBu",
        "descricao": "Matrículas Pretas, Pardas e Indígenas / Total com raça declarada.",
    },
    "taxa_subnotificacao_racial_pct": {
        "label": "Veracidade — Cor/Raça Não Declarada (%)",
        "codigo": "RN20",
        "formato": "{:.2f}%",
        "escala": "Greys",
        "descricao": "Proporção de matrículas sem declaração de cor/raça (CORND).",
    },
}

DIMENSOES_AGRUPAMENTO = {
    "area_geral": "Área STEM (CINE Geral)",
    "area_especifica": "Área Específica (CINE)",
    "regiao": "Região Geográfica",
    "sigla_uf": "Estado (UF)",
    "rede_desc": "Rede de Ensino (Pública vs. Privada)",
    "modalidade_desc": "Modalidade (Presencial vs. EaD)",
    "categoria_adm_desc": "Categoria Administrativa",
    "ano_censo": "Ano do Censo",
}


def _div_pct(numerador: float, denominador: float) -> float:
    if not denominador:
        return 0.0
    return round((float(numerador) / float(denominador)) * 100.0, 2)


def _div_ratio(numerador: float, denominador: float, casas: int = 3) -> float:
    if not denominador:
        return 0.0
    return round(float(numerador) / float(denominador), casas)


def normalizar_colunas_analiticas(df: pd.DataFrame) -> pd.DataFrame:
    """Garante colunas descritivas padronizadas (aceita CSV bruto tratado ou view SQL)."""
    out = df.copy()

    renomear = {
        "NU_ANO_CENSO": "ano_censo",
        "CO_IES": "id_ies",
        "TP_CATEGORIA_ADMINISTRATIVA": "categoria_adm",
        "TP_REDE": "rede",
        "SG_UF": "sigla_uf",
        "CO_MUNICIPIO": "id_municipio",
        "NO_REGIAO": "regiao",
        "CO_CURSO": "id_curso",
        "NO_CURSO": "nome_curso",
        "NO_CINE_AREA_GERAL": "area_geral",
        "NO_CINE_AREA_ESPECIFICA": "area_especifica",
        "TP_MODALIDADE_ENSINO": "modalidade",
        "QT_ING": "qt_ingressantes",
        "QT_MAT": "qt_matriculados",
        "QT_CONC": "qt_concluintes",
        "QT_SIT_DESVINCULADO": "qt_desvinculados",
        "QT_SIT_TRANCADA": "qt_trancados",
        "QT_SIT_TRANSFERIDO": "qt_transferidos",
    }
    for etapa in ["ing", "mat", "conc"]:
        for perfil in ["fem", "masc", "branca", "preta", "parda", "amarela", "indigena", "cornd"]:
            renomear[f"QT_{etapa.upper()}_{perfil.upper()}"] = f"qt_{etapa}_{perfil}"

    out = out.rename(columns={k: v for k, v in renomear.items() if k in out.columns})

    if "rede_desc" not in out.columns and "rede" in out.columns:
        out["rede_desc"] = out["rede"].map(MAPA_REDE).fillna("Não informado")
    if "modalidade_desc" not in out.columns and "modalidade" in out.columns:
        out["modalidade_desc"] = out["modalidade"].map(MAPA_MODALIDADE).fillna("Não informado")
    if "categoria_adm_desc" not in out.columns and "categoria_adm" in out.columns:
        out["categoria_adm_desc"] = (
            out["categoria_adm"].map(MAPA_CATEGORIA_ADM).fillna("Não informado")
        )

    if "nome_municipio" not in out.columns:
        out["nome_municipio"] = "EaD sem polo / Não informado"
    else:
        out["nome_municipio"] = out["nome_municipio"].fillna("EaD sem polo / Não informado")

    if "mesorregiao" not in out.columns:
        out["mesorregiao"] = "Não informado"
    else:
        out["mesorregiao"] = out["mesorregiao"].fillna("Não informado")

    out["sigla_uf"] = out["sigla_uf"].fillna("ND")
    out["regiao"] = out["regiao"].fillna("Sem UF / EaD")

    for col in COLUNAS_SOMA:
        if col not in out.columns:
            out[col] = 0
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0).astype(int)

    out["qt_ing_ppi"] = out["qt_ing_preta"] + out["qt_ing_parda"] + out["qt_ing_indigena"]
    out["qt_mat_ppi"] = out["qt_mat_preta"] + out["qt_mat_parda"] + out["qt_mat_indigena"]
    out["qt_conc_ppi"] = out["qt_conc_preta"] + out["qt_conc_parda"] + out["qt_conc_indigena"]
    return out


def calcular_kpis(df: pd.DataFrame) -> dict[str, float | int]:
    """Calcula todos os KPIs consolidados (RN01 a RN20) para o recorte filtrado."""
    if df.empty:
        return {
            "total_ingressantes": 0,
            "total_matriculados": 0,
            "total_concluintes": 0,
            "total_desvinculados": 0,
            "total_trancados": 0,
            "total_transferidos": 0,
            "taxa_evasao_matriculas_pct": 0.0,
            "taxa_evasao_vinculos_pct": 0.0,
            "taxa_retencao_pct": 0.0,
            "taxa_trancamento_pct": 0.0,
            "taxa_transferencia_pct": 0.0,
            "taxa_conclusao_pct": 0.0,
            "razao_conclusao_ingresso_pct": 0.0,
            "pct_ing_fem": 0.0,
            "pct_mat_fem": 0.0,
            "pct_conc_fem": 0.0,
            "ipg_matriculas": 0.0,
            "gap_paridade_fem_pp": 0.0,
            "delta_funil_fem_pp": 0.0,
            "razao_conc_ing_fem_pct": 0.0,
            "razao_conc_ing_masc_pct": 0.0,
            "pct_ing_ppi_declarado": 0.0,
            "pct_mat_ppi_declarado": 0.0,
            "pct_conc_ppi_declarado": 0.0,
            "delta_funil_ppi_pp": 0.0,
            "razao_conc_ing_ppi_pct": 0.0,
            "razao_conc_ing_branca_pct": 0.0,
            "gap_conclusao_racial_pp": 0.0,
            "taxa_subnotificacao_racial_pct": 0.0,
        }

    s = df[COLUNAS_SOMA].sum()
    ing = int(s["qt_ingressantes"])
    mat = int(s["qt_matriculados"])
    conc = int(s["qt_concluintes"])
    desv = int(s["qt_desvinculados"])
    tranc = int(s["qt_trancados"])
    transf = int(s["qt_transferidos"])

    vinculos = mat + desv + conc
    taxa_evasao_vinc = _div_pct(desv, vinculos)

    # ODS 5 — Gênero
    ing_fem, ing_masc = int(s["qt_ing_fem"]), int(s["qt_ing_masc"])
    mat_fem, mat_masc = int(s["qt_mat_fem"]), int(s["qt_mat_masc"])
    conc_fem, conc_masc = int(s["qt_conc_fem"]), int(s["qt_conc_masc"])

    pct_ing_fem = _div_pct(ing_fem, ing_fem + ing_masc)
    pct_mat_fem = _div_pct(mat_fem, mat_fem + mat_masc)
    pct_conc_fem = _div_pct(conc_fem, conc_fem + conc_masc)

    # ODS 18 — Raça/Cor (PPI = Preta + Parda + Indígena)
    ing_ppi = int(s["qt_ing_preta"] + s["qt_ing_parda"] + s["qt_ing_indigena"])
    mat_ppi = int(s["qt_mat_preta"] + s["qt_mat_parda"] + s["qt_mat_indigena"])
    conc_ppi = int(s["qt_conc_preta"] + s["qt_conc_parda"] + s["qt_conc_indigena"])

    ing_decl = int(s["qt_ing_branca"]) + ing_ppi + int(s["qt_ing_amarela"])
    mat_decl = int(s["qt_mat_branca"]) + mat_ppi + int(s["qt_mat_amarela"])
    conc_decl = int(s["qt_conc_branca"]) + conc_ppi + int(s["qt_conc_amarela"])

    pct_ing_ppi = _div_pct(ing_ppi, ing_decl)
    pct_mat_ppi = _div_pct(mat_ppi, mat_decl)
    pct_conc_ppi = _div_pct(conc_ppi, conc_decl)

    razao_ppi = _div_pct(conc_ppi, ing_ppi)
    razao_branca = _div_pct(int(s["qt_conc_branca"]), int(s["qt_ing_branca"]))

    return {
        "total_ingressantes": ing,
        "total_matriculados": mat,
        "total_concluintes": conc,
        "total_desvinculados": desv,
        "total_trancados": tranc,
        "total_transferidos": transf,
        "taxa_evasao_matriculas_pct": _div_pct(desv, mat),
        "taxa_evasao_vinculos_pct": taxa_evasao_vinc,
        "taxa_retencao_pct": round(100.0 - taxa_evasao_vinc, 2) if vinculos else 0.0,
        "taxa_trancamento_pct": _div_pct(tranc, mat),
        "taxa_transferencia_pct": _div_pct(transf, mat),
        "taxa_conclusao_pct": _div_pct(conc, mat),
        "razao_conclusao_ingresso_pct": _div_pct(conc, ing),
        "pct_ing_fem": pct_ing_fem,
        "pct_mat_fem": pct_mat_fem,
        "pct_conc_fem": pct_conc_fem,
        "ipg_matriculas": _div_ratio(mat_fem, mat_masc, 3),
        "gap_paridade_fem_pp": round(pct_mat_fem - 50.0, 2) if (mat_fem + mat_masc) else 0.0,
        "delta_funil_fem_pp": round(pct_conc_fem - pct_ing_fem, 2),
        "razao_conc_ing_fem_pct": _div_pct(conc_fem, ing_fem),
        "razao_conc_ing_masc_pct": _div_pct(conc_masc, ing_masc),
        "pct_ing_ppi_declarado": pct_ing_ppi,
        "pct_mat_ppi_declarado": pct_mat_ppi,
        "pct_conc_ppi_declarado": pct_conc_ppi,
        "delta_funil_ppi_pp": round(pct_conc_ppi - pct_ing_ppi, 2),
        "razao_conc_ing_ppi_pct": razao_ppi,
        "razao_conc_ing_branca_pct": razao_branca,
        "gap_conclusao_racial_pp": round(razao_branca - razao_ppi, 2),
        "taxa_subnotificacao_racial_pct": _div_pct(int(s["qt_mat_cornd"]), mat),
    }


def agregar_por_dimensao(df: pd.DataFrame, colunas_grupo: str | list[str]) -> pd.DataFrame:
    """Agrupa o DataFrame pelas dimensões escolhidas e calcula todas as RN01-RN20."""
    grupos = [colunas_grupo] if isinstance(colunas_grupo, str) else list(colunas_grupo)
    if df.empty:
        return pd.DataFrame(columns=grupos + list(METRICAS_DINAMICAS))

    agg = df.groupby(grupos, dropna=False, as_index=False)[COLUNAS_SOMA].sum()

    agg["qt_ing_ppi"] = agg["qt_ing_preta"] + agg["qt_ing_parda"] + agg["qt_ing_indigena"]
    agg["qt_mat_ppi"] = agg["qt_mat_preta"] + agg["qt_mat_parda"] + agg["qt_mat_indigena"]
    agg["qt_conc_ppi"] = agg["qt_conc_preta"] + agg["qt_conc_parda"] + agg["qt_conc_indigena"]

    vinculos = agg["qt_matriculados"] + agg["qt_desvinculados"] + agg["qt_concluintes"]
    nan = float("nan")
    agg["taxa_evasao_matriculas_pct"] = (
        100.0 * agg["qt_desvinculados"] / agg["qt_matriculados"].replace(0, nan)
    ).fillna(0.0).round(2)
    agg["taxa_evasao_vinculos_pct"] = (
        100.0 * agg["qt_desvinculados"] / vinculos.replace(0, nan)
    ).fillna(0.0).round(2)
    agg["taxa_retencao_pct"] = (100.0 - agg["taxa_evasao_vinculos_pct"]).where(vinculos > 0, 0.0).round(2)
    agg["taxa_trancamento_pct"] = (
        100.0 * agg["qt_trancados"] / agg["qt_matriculados"].replace(0, nan)
    ).fillna(0.0).round(2)
    agg["taxa_transferencia_pct"] = (
        100.0 * agg["qt_transferidos"] / agg["qt_matriculados"].replace(0, nan)
    ).fillna(0.0).round(2)
    agg["taxa_conclusao_pct"] = (
        100.0 * agg["qt_concluintes"] / agg["qt_matriculados"].replace(0, nan)
    ).fillna(0.0).round(2)
    agg["razao_conclusao_ingresso_pct"] = (
        100.0 * agg["qt_concluintes"] / agg["qt_ingressantes"].replace(0, nan)
    ).fillna(0.0).round(2)

    # ODS 5
    ing_sexo = agg["qt_ing_fem"] + agg["qt_ing_masc"]
    mat_sexo = agg["qt_mat_fem"] + agg["qt_mat_masc"]
    conc_sexo = agg["qt_conc_fem"] + agg["qt_conc_masc"]

    agg["pct_ing_fem"] = (100.0 * agg["qt_ing_fem"] / ing_sexo.replace(0, nan)).fillna(0.0).round(2)
    agg["pct_mat_fem"] = (100.0 * agg["qt_mat_fem"] / mat_sexo.replace(0, nan)).fillna(0.0).round(2)
    agg["pct_conc_fem"] = (100.0 * agg["qt_conc_fem"] / conc_sexo.replace(0, nan)).fillna(0.0).round(2)
    agg["ipg_matriculas"] = (agg["qt_mat_fem"] / agg["qt_mat_masc"].replace(0, nan)).fillna(0.0).round(3)
    agg["delta_funil_fem_pp"] = (agg["pct_conc_fem"] - agg["pct_ing_fem"]).round(2)
    agg["razao_conc_ing_fem_pct"] = (
        100.0 * agg["qt_conc_fem"] / agg["qt_ing_fem"].replace(0, nan)
    ).fillna(0.0).round(2)
    agg["razao_conc_ing_masc_pct"] = (
        100.0 * agg["qt_conc_masc"] / agg["qt_ing_masc"].replace(0, nan)
    ).fillna(0.0).round(2)

    # ODS 18
    ing_decl = agg["qt_ing_branca"] + agg["qt_ing_ppi"] + agg["qt_ing_amarela"]
    mat_decl = agg["qt_mat_branca"] + agg["qt_mat_ppi"] + agg["qt_mat_amarela"]
    conc_decl = agg["qt_conc_branca"] + agg["qt_conc_ppi"] + agg["qt_conc_amarela"]

    agg["pct_ing_ppi_declarado"] = (
        100.0 * agg["qt_ing_ppi"] / ing_decl.replace(0, nan)
    ).fillna(0.0).round(2)
    agg["pct_mat_ppi_declarado"] = (
        100.0 * agg["qt_mat_ppi"] / mat_decl.replace(0, nan)
    ).fillna(0.0).round(2)
    agg["pct_conc_ppi_declarado"] = (
        100.0 * agg["qt_conc_ppi"] / conc_decl.replace(0, nan)
    ).fillna(0.0).round(2)
    agg["delta_funil_ppi_pp"] = (agg["pct_conc_ppi_declarado"] - agg["pct_ing_ppi_declarado"]).round(2)
    agg["razao_conc_ing_ppi_pct"] = (
        100.0 * agg["qt_conc_ppi"] / agg["qt_ing_ppi"].replace(0, nan)
    ).fillna(0.0).round(2)
    agg["razao_conc_ing_branca_pct"] = (
        100.0 * agg["qt_conc_branca"] / agg["qt_ing_branca"].replace(0, nan)
    ).fillna(0.0).round(2)
    agg["gap_conclusao_racial_pp"] = (
        agg["razao_conc_ing_branca_pct"] - agg["razao_conc_ing_ppi_pct"]
    ).round(2)
    agg["taxa_subnotificacao_racial_pct"] = (
        100.0 * agg["qt_mat_cornd"] / agg["qt_matriculados"].replace(0, nan)
    ).fillna(0.0).round(2)

    return agg
