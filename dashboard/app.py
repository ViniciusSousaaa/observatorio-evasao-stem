"""Observatório de Evasão e Retenção em Cursos STEM — Dashboard Dinâmico.

Conecta-se ao Data Warehouse PostgreSQL (Google Cloud SQL) e permite análise
interativa de evasão, retenção e equidade de gênero (ODS 5) e raça/cor (ODS 18).
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:
    from db import carregar_dados
    from metrics import (
        DIMENSOES_AGRUPAMENTO,
        METRICAS_DINAMICAS,
        agregar_por_dimensao,
        calcular_kpis,
    )
except ImportError:
    from dashboard.db import carregar_dados
    from dashboard.metrics import (
        DIMENSOES_AGRUPAMENTO,
        METRICAS_DINAMICAS,
        agregar_por_dimensao,
        calcular_kpis,
    )

st.set_page_config(
    page_title="Observatório de Evasão STEM | ODS 5 & ODS 18",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.4rem; padding-bottom: 2rem; }
    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 14px 16px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .badge-fonte {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
        background: #CCFBF1;
        color: #115E59;
        margin-bottom: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _fmt_int(valor: int | float) -> str:
    return f"{int(round(valor)):,}".replace(",", ".")


def _aplicar_filtros_sidebar(df: pd.DataFrame) -> tuple[pd.DataFrame, str, str]:
    st.sidebar.header("🎛️ Filtros Dinâmicos Cruzados")

    anos_disp = sorted(df["ano_censo"].dropna().unique().tolist())
    anos_sel = st.sidebar.multiselect(
        "Ano do Censo",
        options=anos_disp,
        default=anos_disp,
    )
    df_f = df[df["ano_censo"].isin(anos_sel)] if anos_sel else df.iloc[0:0]

    regioes_disp = sorted(df_f["regiao"].dropna().unique().tolist())
    regioes_sel = st.sidebar.multiselect(
        "Região",
        options=regioes_disp,
        default=regioes_disp,
    )
    df_f = df_f[df_f["regiao"].isin(regioes_sel)] if regioes_sel else df_f.iloc[0:0]

    ufs_disp = sorted(df_f["sigla_uf"].dropna().unique().tolist())
    ufs_sel = st.sidebar.multiselect(
        "Estado (UF)",
        options=ufs_disp,
        default=[],
        placeholder="Todos os estados filtrados",
    )
    if ufs_sel:
        df_f = df_f[df_f["sigla_uf"].isin(ufs_sel)]

    areas_disp = sorted(df_f["area_geral"].dropna().unique().tolist())
    areas_sel = st.sidebar.multiselect(
        "Área STEM (CINE Geral)",
        options=areas_disp,
        default=areas_disp,
    )
    df_f = df_f[df_f["area_geral"].isin(areas_sel)] if areas_sel else df_f.iloc[0:0]

    espec_disp = sorted(df_f["area_especifica"].dropna().unique().tolist())
    espec_sel = st.sidebar.multiselect(
        "Área Específica (opcional)",
        options=espec_disp,
        default=[],
        placeholder="Todas as áreas específicas",
    )
    if espec_sel:
        df_f = df_f[df_f["area_especifica"].isin(espec_sel)]

    redes_disp = sorted(df_f["rede_desc"].dropna().unique().tolist())
    redes_sel = st.sidebar.multiselect(
        "Rede de Ensino",
        options=redes_disp,
        default=redes_disp,
    )
    df_f = df_f[df_f["rede_desc"].isin(redes_sel)] if redes_sel else df_f.iloc[0:0]

    mods_disp = sorted(df_f["modalidade_desc"].dropna().unique().tolist())
    mods_sel = st.sidebar.multiselect(
        "Modalidade",
        options=mods_disp,
        default=mods_disp,
    )
    df_f = df_f[df_f["modalidade_desc"].isin(mods_sel)] if mods_sel else df_f.iloc[0:0]

    cats_disp = sorted(df_f["categoria_adm_desc"].dropna().unique().tolist())
    cats_sel = st.sidebar.multiselect(
        "Categoria Administrativa (opcional)",
        options=cats_disp,
        default=[],
        placeholder="Todas as categorias",
    )
    if cats_sel:
        df_f = df_f[df_f["categoria_adm_desc"].isin(cats_sel)]

    st.sidebar.divider()
    st.sidebar.subheader("🎯 Recorte ODS 5 & ODS 18")
    foco_genero = st.sidebar.radio(
        "Destaque de Gênero (ODS 5)",
        options=["Feminino", "Masculino", "Comparativo"],
        index=2,
        horizontal=True,
    )
    foco_raca = st.sidebar.selectbox(
        "Destaque Étnico-Racial (ODS 18)",
        options=[
            "PPI (Preta, Parda e Indígena)",
            "Branca",
            "Preta",
            "Parda",
            "Indígena",
            "Amarela",
            "Não Declarada (Veracidade)",
        ],
        index=0,
    )

    st.sidebar.caption(
        "Fonte: Microdados do Censo da Educação Superior (INEP) enriquecidos com "
        "API de Localidades do IBGE. Dados agregados em conformidade com a LGPD."
    )
    return df_f, foco_genero, foco_raca


def _render_kpis(kpis: dict) -> None:
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric(
        "Matrículas STEM",
        _fmt_int(kpis["total_matriculados"]),
        delta=f"Ing: {_fmt_int(kpis['total_ingressantes'])}",
        delta_color="off",
    )
    c2.metric(
        "Taxa de Evasão (RN01)",
        f"{kpis['taxa_evasao_matriculas_pct']:.2f}%",
        delta=f"Vínculos: {kpis['taxa_evasao_vinculos_pct']:.2f}%",
        delta_color="inverse",
    )
    c3.metric(
        "Retenção Estimada (RN03)",
        f"{kpis['taxa_retencao_pct']:.2f}%",
        delta=f"Tranc.: {kpis['taxa_trancamento_pct']:.2f}%",
        delta_color="off",
    )
    c4.metric(
        "ODS 5 — Mulheres (RN09)",
        f"{kpis['pct_mat_fem']:.2f}%",
        delta=f"Funil: {kpis['delta_funil_fem_pp']:+.2f} pp",
    )
    c5.metric(
        "ODS 18 — PPI Decl. (RN16)",
        f"{kpis['pct_mat_ppi_declarado']:.2f}%",
        delta=f"Funil: {kpis['delta_funil_ppi_pp']:+.2f} pp",
    )
    c6.metric(
        "Concl. / Ingresso (RN07)",
        f"{kpis['razao_conclusao_ingresso_pct']:.2f}%",
        delta=f"Cor ND: {kpis['taxa_subnotificacao_racial_pct']:.1f}%",
        delta_color="off",
    )


def _aba_visao_geral(df: pd.DataFrame, kpis: dict) -> None:
    st.subheader("Alteração Dinâmica de Métrica e Eixo em Tempo Real")
    col_m, col_d, col_t = st.columns([2, 2, 1.3])
    with col_m:
        metrica_key = st.selectbox(
            "Selecione a métrica analisada",
            options=list(METRICAS_DINAMICAS.keys()),
            format_func=lambda k: f"[{METRICAS_DINAMICAS[k]['codigo']}] {METRICAS_DINAMICAS[k]['label']}",
        )
    with col_d:
        dim_key = st.selectbox(
            "Selecione o eixo / agrupamento",
            options=list(DIMENSOES_AGRUPAMENTO.keys()),
            format_func=lambda k: DIMENSOES_AGRUPAMENTO[k],
        )
    with col_t:
        tipo_grafico = st.selectbox(
            "Tipo de visualização",
            options=["Barras Horizontais", "Barras Verticais", "Treemap", "Linha Temporal"],
        )

    meta = METRICAS_DINAMICAS[metrica_key]
    st.caption(f"**Regra de Negócio ({meta['codigo']}):** {meta['descricao']}")

    agg = agregar_por_dimensao(df, dim_key).sort_values(metrica_key, ascending=False)
    if len(agg) > 27 and dim_key in {"area_especifica"}:
        agg = agg.head(20)

    if tipo_grafico == "Barras Horizontais":
        fig = px.bar(
            agg.sort_values(metrica_key, ascending=True),
            x=metrica_key,
            y=dim_key,
            orientation="h",
            color=metrica_key,
            color_continuous_scale=meta["escala"],
            text=metrica_key,
            hover_data=["qt_matriculados", "qt_desvinculados", "pct_mat_fem", "pct_mat_ppi_declarado"],
            labels={metrica_key: meta["label"], dim_key: DIMENSOES_AGRUPAMENTO[dim_key]},
        )
        fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
    elif tipo_grafico == "Barras Verticais":
        fig = px.bar(
            agg,
            x=dim_key,
            y=metrica_key,
            color=metrica_key,
            color_continuous_scale=meta["escala"],
            text=metrica_key,
            hover_data=["qt_matriculados", "qt_desvinculados"],
            labels={metrica_key: meta["label"], dim_key: DIMENSOES_AGRUPAMENTO[dim_key]},
        )
        fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
    elif tipo_grafico == "Treemap":
        fig = px.treemap(
            agg[agg["qt_matriculados"] > 0],
            path=[dim_key],
            values="qt_matriculados",
            color=metrica_key,
            color_continuous_scale=meta["escala"],
            hover_data=["qt_desvinculados", metrica_key],
        )
    else:
        if df["ano_censo"].nunique() == 1:
            st.info(
                "Apenas 1 ano está carregado no recorte atual. Para visualizar curvas históricas, "
                "execute `python etl/python/tratar_base.py --baixar --anos 2022 2023 2024`."
            )
        agg_tempo = agregar_por_dimensao(df, ["ano_censo", "area_geral"]).sort_values("ano_censo")
        fig = px.line(
            agg_tempo,
            x="ano_censo",
            y=metrica_key,
            color="area_geral",
            markers=True,
            labels={"ano_censo": "Ano", metrica_key: meta["label"], "area_geral": "Área STEM"},
        )
        fig.update_xaxes(dtick=1)

    fig.update_layout(height=440, margin=dict(l=10, r=20, t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)

    col_esq, col_dir = st.columns(2)
    with col_esq:
        st.markdown("#### Matriz Rede × Modalidade")
        agg_rm = agregar_por_dimensao(df, ["rede_desc", "modalidade_desc"])
        fig_rm = px.bar(
            agg_rm,
            x="rede_desc",
            y=metrica_key,
            color="modalidade_desc",
            barmode="group",
            text=metrica_key,
            color_discrete_sequence=["#0F766E", "#F59E0B"],
            labels={
                "rede_desc": "Rede de Ensino",
                metrica_key: meta["label"],
                "modalidade_desc": "Modalidade",
            },
        )
        fig_rm.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
        fig_rm.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig_rm, use_container_width=True)

    with col_dir:
        st.markdown("#### Composição do Fluxo Estudantil")
        fluxo_df = pd.DataFrame(
            {
                "Situação": [
                    "Matriculados",
                    "Ingressantes",
                    "Desvinculados (Evasão)",
                    "Concluintes",
                    "Trancados",
                    "Transferidos",
                ],
                "Estudantes": [
                    kpis["total_matriculados"],
                    kpis["total_ingressantes"],
                    kpis["total_desvinculados"],
                    kpis["total_concluintes"],
                    kpis["total_trancados"],
                    kpis["total_transferidos"],
                ],
            }
        )
        fig_fl = px.bar(
            fluxo_df,
            x="Situação",
            y="Estudantes",
            color="Situação",
            text="Estudantes",
            color_discrete_sequence=["#1D4ED8", "#0EA5E9", "#DC2626", "#16A34A", "#D97706", "#64748B"],
        )
        fig_fl.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig_fl.update_layout(height=360, showlegend=False, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig_fl, use_container_width=True)


def _aba_ods5(df: pd.DataFrame, kpis: dict, foco_genero: str) -> None:
    st.subheader("ODS 5 — Igualdade de Gênero em Cursos STEM")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Índice de Paridade (IPG — RN11)", f"{kpis['ipg_matriculas']:.3f}", help="1,000 = paridade exata (Fem/Masc)")
    m2.metric("Gap vs. Paridade 50% (RN12)", f"{kpis['gap_paridade_fem_pp']:+.2f} pp")
    m3.metric("Concl./Ingresso Feminina (RN14)", f"{kpis['razao_conc_ing_fem_pct']:.2f}%")
    m4.metric("Concl./Ingresso Masculina (RN14)", f"{kpis['razao_conc_ing_masc_pct']:.2f}%")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Funil de Representatividade por Gênero (%)")
        funil_g = pd.DataFrame(
            {
                "Etapa": ["Ingresso", "Matrícula", "Conclusão"],
                "Feminino (%)": [kpis["pct_ing_fem"], kpis["pct_mat_fem"], kpis["pct_conc_fem"]],
                "Masculino (%)": [
                    round(100.0 - kpis["pct_ing_fem"], 2) if kpis["pct_ing_fem"] else 0.0,
                    round(100.0 - kpis["pct_mat_fem"], 2) if kpis["pct_mat_fem"] else 0.0,
                    round(100.0 - kpis["pct_conc_fem"], 2) if kpis["pct_conc_fem"] else 0.0,
                ],
            }
        )
        colunas_plot = (
            ["Feminino (%)"]
            if foco_genero == "Feminino"
            else ["Masculino (%)"]
            if foco_genero == "Masculino"
            else ["Feminino (%)", "Masculino (%)"]
        )
        fig_fg = px.bar(
            funil_g.melt(id_vars="Etapa", value_vars=colunas_plot, var_name="Gênero", value_name="Participação (%)"),
            x="Etapa",
            y="Participação (%)",
            color="Gênero",
            barmode="group",
            text="Participação (%)",
            color_discrete_map={"Feminino (%)": "#7C3AED", "Masculino (%)": "#0284C7"},
        )
        fig_fg.add_hline(y=50, line_dash="dash", line_color="#64748B", annotation_text="Paridade 50%")
        fig_fg.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
        fig_fg.update_layout(height=370, yaxis_range=[0, 105])
        st.plotly_chart(fig_fg, use_container_width=True)

    with col2:
        st.markdown("#### Participação Feminina por Área STEM e Rede")
        agg_g = agregar_por_dimensao(df, ["area_geral", "rede_desc"])
        fig_ag = px.bar(
            agg_g,
            x="area_geral",
            y="pct_mat_fem",
            color="rede_desc",
            barmode="group",
            text="pct_mat_fem",
            color_discrete_sequence=["#6D28D9", "#A78BFA"],
            labels={"area_geral": "Área STEM", "pct_mat_fem": "% Mulheres nas Matrículas", "rede_desc": "Rede"},
        )
        fig_ag.add_hline(y=50, line_dash="dash", line_color="#64748B")
        fig_ag.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_ag.update_layout(height=370, yaxis_range=[0, 100])
        st.plotly_chart(fig_ag, use_container_width=True)

    st.markdown("#### Cursos STEM: Menor e Maior Participação Feminina (mín. 500 matrículas)")
    agg_curso = agregar_por_dimensao(df, ["nome_curso", "area_geral"])
    agg_curso_relev = agg_curso[agg_curso["qt_matriculados"] >= 500]
    if agg_curso_relev.empty:
        agg_curso_relev = agg_curso

    c_low, c_high = st.columns(2)
    with c_low:
        st.caption("Top 10 cursos com MENOR representatividade feminina")
        st.dataframe(
            agg_curso_relev.sort_values("pct_mat_fem", ascending=True)
            .head(10)[["nome_curso", "area_geral", "qt_matriculados", "pct_mat_fem", "delta_funil_fem_pp"]]
            .rename(
                columns={
                    "nome_curso": "Curso",
                    "area_geral": "Área STEM",
                    "qt_matriculados": "Matrículas",
                    "pct_mat_fem": "% Mulheres",
                    "delta_funil_fem_pp": "Delta Funil (pp)",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
    with c_high:
        st.caption("Top 10 cursos com MAIOR representatividade feminina")
        st.dataframe(
            agg_curso_relev.sort_values("pct_mat_fem", ascending=False)
            .head(10)[["nome_curso", "area_geral", "qt_matriculados", "pct_mat_fem", "delta_funil_fem_pp"]]
            .rename(
                columns={
                    "nome_curso": "Curso",
                    "area_geral": "Área STEM",
                    "qt_matriculados": "Matrículas",
                    "pct_mat_fem": "% Mulheres",
                    "delta_funil_fem_pp": "Delta Funil (pp)",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )


def _aba_ods18(df: pd.DataFrame, kpis: dict, foco_raca: str) -> None:
    st.subheader("ODS 18 — Igualdade Étnico-Racial em Cursos STEM")

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("PPI nas Matrículas Decl. (RN16)", f"{kpis['pct_mat_ppi_declarado']:.2f}%")
    r2.metric("Concl./Ingresso PPI (RN19)", f"{kpis['razao_conc_ing_ppi_pct']:.2f}%")
    r3.metric("Concl./Ingresso Branca (RN19)", f"{kpis['razao_conc_ing_branca_pct']:.2f}%")
    r4.metric(
        "Gap de Conclusão Racial (RN19)",
        f"{kpis['gap_conclusao_racial_pp']:+.2f} pp",
        help="Diferença (Branca − PPI) na razão Concluintes/Ingressantes.",
        delta_color="inverse",
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Composição Étnico-Racial das Matrículas STEM")
        comp = pd.DataFrame(
            {
                "Cor/Raça": ["Branca", "Parda", "Preta", "Amarela", "Indígena", "Não Declarada"],
                "Matrículas": [
                    int(df["qt_mat_branca"].sum()),
                    int(df["qt_mat_parda"].sum()),
                    int(df["qt_mat_preta"].sum()),
                    int(df["qt_mat_amarela"].sum()),
                    int(df["qt_mat_indigena"].sum()),
                    int(df["qt_mat_cornd"].sum()),
                ],
            }
        )
        fig_comp = px.pie(
            comp,
            names="Cor/Raça",
            values="Matrículas",
            hole=0.45,
            color="Cor/Raça",
            color_discrete_map={
                "Branca": "#60A5FA",
                "Parda": "#D97706",
                "Preta": "#92400E",
                "Amarela": "#FACC15",
                "Indígena": "#15803D",
                "Não Declarada": "#94A3B8",
            },
        )
        fig_comp.update_layout(height=370)
        st.plotly_chart(fig_comp, use_container_width=True)

    with col2:
        st.markdown(f"#### Funil Acadêmico — Composição Étnico-Racial (Destaque: {foco_raca})")
        mapa_raca_cols = {
            "PPI (Preta, Parda e Indígena)": ("qt_ing_ppi", "qt_mat_ppi", "qt_conc_ppi", "#B45309"),
            "Branca": ("qt_ing_branca", "qt_mat_branca", "qt_conc_branca", "#2563EB"),
            "Preta": ("qt_ing_preta", "qt_mat_preta", "qt_conc_preta", "#92400E"),
            "Parda": ("qt_ing_parda", "qt_mat_parda", "qt_conc_parda", "#D97706"),
            "Indígena": ("qt_ing_indigena", "qt_mat_indigena", "qt_conc_indigena", "#15803D"),
            "Amarela": ("qt_ing_amarela", "qt_mat_amarela", "qt_conc_amarela", "#CA8A04"),
            "Não Declarada (Veracidade)": ("qt_ing_cornd", "qt_mat_cornd", "qt_conc_cornd", "#64748B"),
        }

        totais_etapa = {
            "ing": "qt_ingressantes",
            "mat": "qt_matriculados",
            "conc": "qt_concluintes",
        }

        def _pct_etapa(col_etapa: str, etapa: str) -> float:
            num = float(df[col_etapa].sum())
            if foco_raca == "Não Declarada (Veracidade)":
                den = float(df[totais_etapa[etapa]].sum())
            else:
                den = float(
                    df[f"qt_{etapa}_branca"].sum()
                    + df[f"qt_{etapa}_ppi"].sum()
                    + df[f"qt_{etapa}_amarela"].sum()
                )
            return round((num / den) * 100.0, 2) if den else 0.0

        c_ing, c_mat, c_conc, cor_dest = mapa_raca_cols[foco_raca]
        branca_ing = _pct_etapa("qt_ing_branca", "ing")
        branca_mat = _pct_etapa("qt_mat_branca", "mat")
        branca_conc = _pct_etapa("qt_conc_branca", "conc")

        dados_funil_r = {
            "Etapa": ["Ingresso", "Matrícula", "Conclusão"],
            foco_raca: [
                _pct_etapa(c_ing, "ing"),
                _pct_etapa(c_mat, "mat"),
                _pct_etapa(c_conc, "conc"),
            ],
        }
        cores_funil_r = {foco_raca: cor_dest}
        if foco_raca != "Branca" and foco_raca != "Não Declarada (Veracidade)":
            dados_funil_r["Branca (% declarados)"] = [branca_ing, branca_mat, branca_conc]
            cores_funil_r["Branca (% declarados)"] = "#2563EB"

        funil_r = pd.DataFrame(dados_funil_r)
        fig_fr = px.bar(
            funil_r.melt(id_vars="Etapa", var_name="Grupo", value_name="Participação (%)"),
            x="Etapa",
            y="Participação (%)",
            color="Grupo",
            barmode="group",
            text="Participação (%)",
            color_discrete_map=cores_funil_r,
        )
        fig_fr.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
        fig_fr.update_layout(height=370, yaxis_range=[0, 105])
        st.plotly_chart(fig_fr, use_container_width=True)

    st.markdown("#### Diagnóstico de Veracidade (RN20) e Gap Racial por Região")
    agg_reg = agregar_por_dimensao(df, "regiao").sort_values("pct_mat_ppi_declarado", ascending=False)
    fig_reg = go.Figure()
    fig_reg.add_trace(
        go.Bar(
            name="% PPI nas Matrículas",
            x=agg_reg["regiao"],
            y=agg_reg["pct_mat_ppi_declarado"],
            marker_color="#B45309",
            text=agg_reg["pct_mat_ppi_declarado"].map(lambda v: f"{v:.1f}%"),
            textposition="outside",
        )
    )
    fig_reg.add_trace(
        go.Bar(
            name="% Cor Não Declarada (Subnotificação)",
            x=agg_reg["regiao"],
            y=agg_reg["taxa_subnotificacao_racial_pct"],
            marker_color="#94A3B8",
            text=agg_reg["taxa_subnotificacao_racial_pct"].map(lambda v: f"{v:.1f}%"),
            textposition="outside",
        )
    )
    fig_reg.update_layout(barmode="group", height=360, yaxis_title="Percentual (%)")
    st.plotly_chart(fig_reg, use_container_width=True)


def _aba_interseccional(df: pd.DataFrame) -> None:
    st.subheader("Cruzamento ODS 5 (Gênero) × ODS 18 (Raça/Cor) × Evasão")
    st.info(
        "**Nota Metodológica (Transparência & Veracidade):** Nos microdados agregados de cursos do "
        "Censo da Educação Superior (INEP), o sexo e a cor/raça são divulgados em colunas separadas "
        "para ingressantes, matriculados e concluintes, mas não existem desagregados para "
        "`QT_SIT_DESVINCULADO` nem em tabela cruzada individual (Mulher × Raça). Por isso, este painel "
        "realiza a **análise interseccional ecológica por UF, Área Específica e Curso**, cruzando "
        "participação feminina, participação PPI e taxa de evasão."
    )

    granularidade = st.radio(
        "Nível de agregação da dispersão",
        options=["sigla_uf", "area_especifica", "nome_curso"],
        format_func=lambda k: {
            "sigla_uf": "Por Estado (UF)",
            "area_especifica": "Por Área Específica STEM",
            "nome_curso": "Por Curso (Top 40 por matrículas)",
        }[k],
        horizontal=True,
    )

    agg = agregar_por_dimensao(df, [granularidade, "area_geral"] if granularidade != "sigla_uf" else ["sigla_uf", "regiao"])
    if granularidade == "nome_curso":
        agg = agg.sort_values("qt_matriculados", ascending=False).head(40)

    agg_plot = agg[agg["qt_matriculados"] > 0]
    if agg_plot.empty:
        st.warning("Não há registros com matrículas positivas para o gráfico de dispersão.")
        return

    fig_sc = px.scatter(
        agg_plot,
        x="pct_mat_fem",
        y="pct_mat_ppi_declarado",
        size="qt_matriculados",
        color="taxa_evasao_matriculas_pct",
        color_continuous_scale="RdYlGn_r",
        hover_name=granularidade,
        hover_data={
            "qt_matriculados": ":,.0f",
            "taxa_evasao_matriculas_pct": ":.2f",
            "delta_funil_fem_pp": ":+.2f",
            "delta_funil_ppi_pp": ":+.2f",
        },
        labels={
            "pct_mat_fem": "ODS 5 — Participação Feminina nas Matrículas (%)",
            "pct_mat_ppi_declarado": "ODS 18 — Participação PPI nas Matrículas Decl. (%)",
            "taxa_evasao_matriculas_pct": "Evasão (%)",
            "qt_matriculados": "Matrículas",
        },
        size_max=48,
    )
    fig_sc.add_vline(x=50, line_dash="dot", line_color="#64748B", annotation_text="50% Mulheres")
    fig_sc.add_hline(y=50, line_dash="dot", line_color="#64748B", annotation_text="50% PPI")
    fig_sc.update_layout(height=480)
    st.plotly_chart(fig_sc, use_container_width=True)


def _aba_drilldown(df: pd.DataFrame) -> None:
    st.subheader("Drill-Down Hierárquico e Detalhamento por Segmento")

    modo = st.radio(
        "Caminho de Drill-Down",
        options=["Territorial (Região → UF → Município)", "Acadêmico (Área Geral → Área Específica → Curso)"],
        horizontal=True,
    )

    if modo.startswith("Territorial"):
        col_r, col_u = st.columns(2)
        with col_r:
            reg_sel = st.selectbox("1. Região", ["Todas"] + sorted(df["regiao"].unique().tolist()))
        df_sub = df if reg_sel == "Todas" else df[df["regiao"] == reg_sel]
        with col_u:
            uf_sel = st.selectbox("2. Estado (UF)", ["Todos"] + sorted(df_sub["sigla_uf"].unique().tolist()))
        df_sub = df_sub if uf_sel == "Todos" else df_sub[df_sub["sigla_uf"] == uf_sel]

        hierarquia = ["regiao", "sigla_uf", "nome_municipio"]
        agg_dd = agregar_por_dimensao(df_sub, hierarquia).sort_values("qt_matriculados", ascending=False)
        top_sun = agg_dd.head(80)
    else:
        col_a, col_e = st.columns(2)
        with col_a:
            area_sel = st.selectbox("1. Área STEM", ["Todas"] + sorted(df["area_geral"].unique().tolist()))
        df_sub = df if area_sel == "Todas" else df[df["area_geral"] == area_sel]
        with col_e:
            esp_sel = st.selectbox(
                "2. Área Específica",
                ["Todas"] + sorted(df_sub["area_especifica"].unique().tolist()),
            )
        df_sub = df_sub if esp_sel == "Todas" else df_sub[df_sub["area_especifica"] == esp_sel]

        hierarquia = ["area_geral", "area_especifica", "nome_curso"]
        agg_dd = agregar_por_dimensao(df_sub, hierarquia).sort_values("qt_matriculados", ascending=False)
        top_sun = agg_dd.head(80)

    if not top_sun.empty:
        fig_sun = px.sunburst(
            top_sun[top_sun["qt_matriculados"] > 0],
            path=hierarquia,
            values="qt_matriculados",
            color="taxa_evasao_matriculas_pct",
            color_continuous_scale="RdYlGn_r",
            hover_data=["pct_mat_fem", "pct_mat_ppi_declarado"],
        )
        fig_sun.update_layout(height=440, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig_sun, use_container_width=True)

    busca = st.text_input("🔎 Pesquisar segmento na tabela detalhada", placeholder="Digite curso, UF ou município...")
    tabela = agg_dd.copy()
    if busca:
        mask = tabela[hierarquia].astype(str).apply(lambda s: s.str.contains(busca, case=False, na=False)).any(axis=1)
        tabela = tabela[mask]

    cols_exibir = hierarquia + [
        "qt_ingressantes",
        "qt_matriculados",
        "qt_concluintes",
        "qt_desvinculados",
        "taxa_evasao_matriculas_pct",
        "taxa_retencao_pct",
        "pct_mat_fem",
        "pct_mat_ppi_declarado",
    ]
    st.dataframe(tabela[cols_exibir].head(200), use_container_width=True, hide_index=True)

    csv_bytes = tabela[cols_exibir].to_csv(index=False, sep=";").encode("utf-8-sig")
    st.download_button(
        label="⬇️ Exportar recorte filtrado (CSV)",
        data=csv_bytes,
        file_name="observatorio_stem_recorte.csv",
        mime="text/csv",
    )


def main() -> None:
    df, origem, aviso = carregar_dados()

    st.markdown(f"<span class='badge-fonte'>Fonte ativa: {origem}</span>", unsafe_allow_html=True)
    st.title("🎓 Observatório de Evasão e Retenção em Cursos STEM")
    st.markdown(
        "Painel interativo de Big Data & Analytics alinhado à **ODS 5 (Igualdade de Gênero)** "
        "e à **ODS 18 (Igualdade Étnico-Racial)** — Censo da Educação Superior (INEP) + API IBGE."
    )

    if aviso:
        st.warning(aviso)

    df_filtrado, foco_genero, foco_raca = _aplicar_filtros_sidebar(df)

    if df_filtrado.empty:
        st.error("Nenhum registro encontrado para a combinação atual de filtros. Ajuste os filtros na barra lateral.")
        return

    kpis = calcular_kpis(df_filtrado)
    _render_kpis(kpis)

    st.divider()
    aba1, aba2, aba3, aba4, aba5 = st.tabs(
        [
            "📊 Visão Geral & Fluxo Dinâmico",
            "♀️ ODS 5 — Gênero",
            "✊🏾 ODS 18 — Raça/Cor",
            "🔀 Interseccionalidade",
            "🔎 Drill-Down & Dados",
        ]
    )

    with aba1:
        _aba_visao_geral(df_filtrado, kpis)
    with aba2:
        _aba_ods5(df_filtrado, kpis, foco_genero)
    with aba3:
        _aba_ods18(df_filtrado, kpis, foco_raca)
    with aba4:
        _aba_interseccional(df_filtrado)
    with aba5:
        _aba_drilldown(df_filtrado)


if __name__ == "__main__":
    main()
