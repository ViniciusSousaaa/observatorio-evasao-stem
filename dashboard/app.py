"""Observatório de Evasão e Retenção em Cursos STEM — Dashboard Minimalista.

Interface neutra em branco e cinza para concentrar a atenção e a cor
exclusivamente nos gráficos (Apache ECharts e Plotly).
"""

from __future__ import annotations

import html

import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from db import carregar_dados
    from metrics import (
        DIMENSOES_AGRUPAMENTO,
        METRICAS_DINAMICAS,
        agregar_por_dimensao,
        calcular_kpis,
    )
    from ui_components import (
        COR_POR_METRICA,
        DATA,
        HAS_ECHARTS,
        UI,
        build_echarts_donut_raca,
        build_echarts_gauge_ipg,
        build_echarts_grouped_bar,
        build_echarts_horizontal_bar,
        build_echarts_line_temporal,
        build_echarts_sankey_fluxo,
        build_echarts_scatter_interseccional,
        injetar_css_minimalista,
        render_aviso_discreto,
        render_chart_header,
        render_echarts_safe,
        render_html,
        render_kpi_strip,
        render_nav_bar,
        render_page_header,
        render_section_header,
        render_stat_row,
    )
except ImportError:
    from dashboard.db import carregar_dados
    from dashboard.metrics import (
        DIMENSOES_AGRUPAMENTO,
        METRICAS_DINAMICAS,
        agregar_por_dimensao,
        calcular_kpis,
    )
    from dashboard.ui_components import (
        COR_POR_METRICA,
        DATA,
        HAS_ECHARTS,
        UI,
        build_echarts_donut_raca,
        build_echarts_gauge_ipg,
        build_echarts_grouped_bar,
        build_echarts_horizontal_bar,
        build_echarts_line_temporal,
        build_echarts_sankey_fluxo,
        build_echarts_scatter_interseccional,
        injetar_css_minimalista,
        render_aviso_discreto,
        render_chart_header,
        render_echarts_safe,
        render_html,
        render_kpi_strip,
        render_nav_bar,
        render_page_header,
        render_section_header,
        render_stat_row,
    )

st.set_page_config(
    page_title="Observatório de evasão em cursos STEM",
    layout="wide",
    initial_sidebar_state="expanded",
)

injetar_css_minimalista()


def _fmt_int(valor: int | float) -> str:
    return f"{int(round(valor)):,}".replace(",", ".")


def _estilizar_plotly(fig, height: int = 440):
    fig.update_layout(
        height=height,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family="IBM Plex Sans, sans-serif", color=UI["ink"], size=12),
        margin=dict(l=4, r=8, t=12, b=4),
        hoverlabel=dict(
            bgcolor="#111827",
            bordercolor="#1F2937",
            font=dict(color="#F9FAFB", family="IBM Plex Sans, sans-serif", size=12),
        ),
    )
    return fig


def _aplicar_filtros_sidebar(df: pd.DataFrame) -> tuple[pd.DataFrame, str, str, str]:
    with st.sidebar:
        render_html('<div class="sidebar-heading">Filtrar dados</div>')

        anos_disp = sorted(df["ano_censo"].dropna().unique().tolist())
        anos_sel = st.multiselect("Ano do Censo", options=anos_disp, default=anos_disp)
        df_f = df[df["ano_censo"].isin(anos_sel)] if anos_sel else df.iloc[0:0]

        regioes_disp = sorted(df_f["regiao"].dropna().unique().tolist())
        regioes_sel = st.multiselect("Região", options=regioes_disp, default=regioes_disp)
        df_f = df_f[df_f["regiao"].isin(regioes_sel)] if regioes_sel else df_f.iloc[0:0]

        ufs_disp = sorted(df_f["sigla_uf"].dropna().unique().tolist())
        ufs_sel = st.multiselect(
            "Estado (UF)",
            options=ufs_disp,
            default=[],
            placeholder="Todos os estados",
        )
        if ufs_sel:
            df_f = df_f[df_f["sigla_uf"].isin(ufs_sel)]

        areas_disp = sorted(df_f["area_geral"].dropna().unique().tolist())
        areas_sel = st.multiselect("Área STEM", options=areas_disp, default=areas_disp)
        df_f = df_f[df_f["area_geral"].isin(areas_sel)] if areas_sel else df_f.iloc[0:0]

        espec_disp = sorted(df_f["area_especifica"].dropna().unique().tolist())
        espec_sel = st.multiselect(
            "Área específica",
            options=espec_disp,
            default=[],
            placeholder="Todas as áreas específicas",
        )
        if espec_sel:
            df_f = df_f[df_f["area_especifica"].isin(espec_sel)]

        redes_disp = sorted(df_f["rede_desc"].dropna().unique().tolist())
        redes_sel = st.multiselect("Rede de ensino", options=redes_disp, default=redes_disp)
        df_f = df_f[df_f["rede_desc"].isin(redes_sel)] if redes_sel else df_f.iloc[0:0]

        mods_disp = sorted(df_f["modalidade_desc"].dropna().unique().tolist())
        mods_sel = st.multiselect("Modalidade", options=mods_disp, default=mods_disp)
        df_f = df_f[df_f["modalidade_desc"].isin(mods_sel)] if mods_sel else df_f.iloc[0:0]

        cats_disp = sorted(df_f["categoria_adm_desc"].dropna().unique().tolist())
        cats_sel = st.multiselect(
            "Categoria administrativa",
            options=cats_disp,
            default=[],
            placeholder="Todas as categorias",
        )
        if cats_sel:
            df_f = df_f[df_f["categoria_adm_desc"].isin(cats_sel)]

        st.divider()
        render_html('<div class="sidebar-subhead">Recorte demográfico</div>')
        foco_genero = st.radio(
            "Gênero (ODS 5)",
            options=["Comparativo", "Feminino", "Masculino"],
            index=0,
            horizontal=True,
        )
        foco_raca = st.selectbox(
            "Raça ou cor (ODS 18)",
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

        st.divider()
        st.caption(
            "Dados públicos agregados (INEP e IBGE), sem identificação individual de estudantes (LGPD)."
        )

    if anos_sel:
        anos_txt = f"{min(anos_sel)} a {max(anos_sel)}" if len(anos_sel) > 1 else str(anos_sel[0])
    else:
        anos_txt = "período não selecionado"
    resumo = f"{anos_txt} ({df_f['sigla_uf'].nunique()} UFs e {df_f['nome_curso'].nunique()} cursos)"
    return df_f, foco_genero, foco_raca, resumo


def _render_kpis(kpis: dict) -> None:
    render_kpi_strip(
        [
            {
                "label": "Matrículas STEM",
                "value": _fmt_int(kpis["total_matriculados"]),
                "meta": f"{_fmt_int(kpis['total_ingressantes'])} ingressantes",
                "dot": DATA["azul"],
            },
            {
                "label": "Taxa de evasão",
                "value": f"{kpis['taxa_evasao_matriculas_pct']:.2f}%",
                "meta": f"{kpis['taxa_evasao_vinculos_pct']:.2f}% sobre vínculos",
                "dot": DATA["vermelho"],
            },
            {
                "label": "Retenção estimada",
                "value": f"{kpis['taxa_retencao_pct']:.2f}%",
                "meta": f"{kpis['taxa_trancamento_pct']:.2f}% trancadas",
                "dot": DATA["verde"],
            },
            {
                "label": "Mulheres (ODS 5)",
                "value": f"{kpis['pct_mat_fem']:.2f}%",
                "meta": f"Funil {kpis['delta_funil_fem_pp']:+.2f} pp",
                "dot": DATA["violeta"],
            },
            {
                "label": "PPI decl. (ODS 18)",
                "value": f"{kpis['pct_mat_ppi_declarado']:.2f}%",
                "meta": f"Funil {kpis['delta_funil_ppi_pp']:+.2f} pp",
                "dot": DATA["ambar"],
            },
            {
                "label": "Concl. / ingresso",
                "value": f"{kpis['razao_conclusao_ingresso_pct']:.2f}%",
                "meta": f"{kpis['taxa_subnotificacao_racial_pct']:.1f}% cor não decl.",
                "dot": DATA["neutro"],
            },
        ]
    )


def _secao_panorama(df: pd.DataFrame, kpis: dict) -> None:
    render_section_header(
        "Indicadores dinâmicos",
        "Escolha a métrica, o agrupamento e o tipo de gráfico para comparar segmentos.",
    )

    col_m, col_d, col_t = st.columns([2.2, 1.8, 1.3])
    with col_m:
        metrica_key = st.selectbox(
            "Métrica",
            options=list(METRICAS_DINAMICAS.keys()),
            format_func=lambda k: METRICAS_DINAMICAS[k]["label"],
        )
    with col_d:
        dim_key = st.selectbox(
            "Agrupar por",
            options=list(DIMENSOES_AGRUPAMENTO.keys()),
            format_func=lambda k: DIMENSOES_AGRUPAMENTO[k],
        )
    with col_t:
        tipo_viz = st.selectbox(
            "Formato",
            options=["Barras horizontais", "Série histórica", "Treemap"],
        )

    meta = METRICAS_DINAMICAS[metrica_key]
    cor = COR_POR_METRICA.get(metrica_key, DATA["azul"])
    st.caption(f"Fórmula ({meta['codigo']}): {meta['descricao']}")

    agg = agregar_por_dimensao(df, dim_key).sort_values(metrica_key, ascending=False)
    if len(agg) > 20 and dim_key == "area_especifica":
        agg = agg.head(20)

    if tipo_viz == "Barras horizontais":
        agg_plot = agg.sort_values(metrica_key, ascending=True)
        cats = [str(x) for x in agg_plot[dim_key].tolist()]
        vals = [round(float(v), 2) for v in agg_plot[metrica_key].tolist()]
        tooltips = [
            (
                f"<strong>{html.escape(str(r[dim_key]))}</strong><br/>"
                f"{html.escape(meta['label'])}: <b>{float(r[metrica_key]):.2f}%</b><br/>"
                f"Matrículas: <b>{_fmt_int(r['qt_matriculados'])}</b><br/>"
                f"Desvinculados: <b>{_fmt_int(r['qt_desvinculados'])}</b><br/>"
                f"Mulheres: <b>{float(r['pct_mat_fem']):.1f}%</b> | PPI: <b>{float(r['pct_mat_ppi_declarado']):.1f}%</b>"
            )
            for _, r in agg_plot.iterrows()
        ]
        altura = max(300, min(560, 42 * len(cats) + 56))
        opts = build_echarts_horizontal_bar(cats, vals, cor, "%", tooltips=tooltips)
        if not render_echarts_safe(opts, height=f"{altura}px", key=f"rank_{metrica_key}_{dim_key}"):
            fig = px.bar(agg_plot, x=metrica_key, y=dim_key, orientation="h", text=metrica_key, color_discrete_sequence=[cor])
            fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
            st.plotly_chart(_estilizar_plotly(fig, altura), use_container_width=True)

    elif tipo_viz == "Série histórica":
        if df["ano_censo"].nunique() == 1:
            st.caption(
                "Apenas um ano está carregado. Para curvas multi-ano, execute tratar_base.py com múltiplos anos."
            )
        agg_tempo = agregar_por_dimensao(df, ["ano_censo", "area_geral"]).sort_values("ano_censo")
        opts = build_echarts_line_temporal(agg_tempo, metrica_key)
        if not render_echarts_safe(opts, height="400px", key=f"line_{metrica_key}"):
            fig = px.line(agg_tempo, x="ano_censo", y=metrica_key, color="area_geral", markers=True)
            st.plotly_chart(_estilizar_plotly(fig, 400), use_container_width=True)

    else:
        agg_tree = agg[agg["qt_matriculados"] > 0]
        if not agg_tree.empty:
            fig = px.treemap(
                agg_tree,
                path=[dim_key],
                values="qt_matriculados",
                color=metrica_key,
                color_continuous_scale=[DATA["verde"], DATA["ambar"], DATA["vermelho"]],
                hover_data=["qt_desvinculados", "pct_mat_fem", "pct_mat_ppi_declarado"],
            )
            st.plotly_chart(_estilizar_plotly(fig, 430), use_container_width=True)

    st.divider()
    col_esq, col_dir = st.columns([1.25, 1.0], gap="large")

    with col_esq:
        render_chart_header(
            "Fluxo estudantil em STEM",
            "Distribuição de vínculos entre entrada, permanência ativa, conclusão e evasão.",
        )
        opts_sk = build_echarts_sankey_fluxo(kpis)
        if not render_echarts_safe(opts_sk, height="360px", key="sankey_fluxo"):
            fluxo_df = pd.DataFrame(
                {
                    "Situação": ["Matriculados", "Ingressantes", "Desvinculados", "Concluintes", "Trancados", "Transferidos"],
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
            fig_f = px.bar(fluxo_df, x="Situação", y="Estudantes", color_discrete_sequence=[DATA["azul"]])
            st.plotly_chart(_estilizar_plotly(fig_f, 350), use_container_width=True)

    with col_dir:
        render_chart_header(
            "Rede de ensino por modalidade",
            f"Comparativo de {meta['label'].lower()} entre oferta presencial e a distância.",
        )
        agg_rm = agregar_por_dimensao(df, ["rede_desc", "modalidade_desc"])
        redes = sorted(agg_rm["rede_desc"].unique().tolist())
        mods = sorted(agg_rm["modalidade_desc"].unique().tolist())
        series_rm: dict[str, list[float]] = {}
        for mod in mods:
            sub = agg_rm[agg_rm["modalidade_desc"] == mod].set_index("rede_desc")
            series_rm[mod] = [
                round(float(sub.loc[r, metrica_key]), 2) if r in sub.index else 0.0
                for r in redes
            ]
        opts_rm = build_echarts_grouped_bar(
            redes,
            series_rm,
            cores=[DATA["azul"], DATA["vermelho"], DATA["verde"]],
        )
        if not render_echarts_safe(opts_rm, height="360px", key=f"rm_{metrica_key}"):
            fig_rm = px.bar(agg_rm, x="rede_desc", y=metrica_key, color="modalidade_desc", barmode="group")
            st.plotly_chart(_estilizar_plotly(fig_rm, 350), use_container_width=True)


def _secao_ods5(df: pd.DataFrame, kpis: dict, foco_genero: str) -> None:
    render_section_header(
        "Igualdade de gênero em STEM (ODS 5)",
        "Acompanhamento da paridade entre mulheres e homens do ingresso até a conclusão.",
    )

    col_g, col_s = st.columns([1.0, 2.2], gap="large")
    with col_g:
        render_chart_header(
            "Índice de paridade de gênero",
            "Razão matrículas femininas sobre masculinas (RN11).",
        )
        opts_ipg = build_echarts_gauge_ipg(kpis["ipg_matriculas"])
        if not render_echarts_safe(opts_ipg, height="240px", key="gauge_ipg"):
            st.metric("IPG", f"{kpis['ipg_matriculas']:.3f}")

    with col_s:
        render_stat_row(
            [
                {
                    "label": "Distância da paridade",
                    "value": f"{kpis['gap_paridade_fem_pp']:+.2f} pp",
                    "note": "Diferença em relação a 50%",
                },
                {
                    "label": "Variação no funil feminino",
                    "value": f"{kpis['delta_funil_fem_pp']:+.2f} pp",
                    "note": "Conclusão menos ingresso",
                },
                {
                    "label": "Concl. / ingresso feminino",
                    "value": f"{kpis['razao_conc_ing_fem_pct']:.2f}%",
                    "note": "Eficiência do funil (RN14)",
                },
                {
                    "label": "Concl. / ingresso masculino",
                    "value": f"{kpis['razao_conc_ing_masc_pct']:.2f}%",
                    "note": "Eficiência do funil (RN14)",
                },
            ]
        )

    col1, col2 = st.columns(2, gap="large")
    with col1:
        render_chart_header(
            "Participação por etapa do curso",
            f"Exibição selecionada: {foco_genero.lower()}. Linha tracejada marca 50%.",
        )
        etapas = ["Ingresso", "Matrícula", "Conclusão"]
        fem_vals = [kpis["pct_ing_fem"], kpis["pct_mat_fem"], kpis["pct_conc_fem"]]
        masc_vals = [round(100.0 - v, 2) if v > 0 else 0.0 for v in fem_vals]
        if foco_genero == "Feminino":
            series_g = {"Feminino": fem_vals}
            cores_g = [DATA["violeta"]]
        elif foco_genero == "Masculino":
            series_g = {"Masculino": masc_vals}
            cores_g = [DATA["azul"]]
        else:
            series_g = {"Feminino": fem_vals, "Masculino": masc_vals}
            cores_g = [DATA["violeta"], DATA["azul"]]

        opts_fg = build_echarts_grouped_bar(etapas, series_g, cores_g, linha_referencia=50.0, y_max=100)
        if not render_echarts_safe(opts_fg, height="350px", key=f"ods5_funil_{foco_genero}"):
            st.bar_chart(pd.DataFrame(series_g, index=etapas))

    with col2:
        render_chart_header(
            "Mulheres nas matrículas por área e rede",
            "Comparação entre instituições públicas e privadas nas três áreas STEM.",
        )
        agg_g = agregar_por_dimensao(df, ["area_geral", "rede_desc"])
        areas = sorted(agg_g["area_geral"].unique().tolist())
        redes = sorted(agg_g["rede_desc"].unique().tolist())
        series_ar = {}
        for r in redes:
            sub = agg_g[agg_g["rede_desc"] == r].set_index("area_geral")
            series_ar[r] = [round(float(sub.loc[a, "pct_mat_fem"]), 2) if a in sub.index else 0.0 for a in areas]
        opts_ar = build_echarts_grouped_bar(
            areas,
            series_ar,
            cores=[DATA["violeta"], "#C4B5FD"],
            linha_referencia=50.0,
            y_max=100,
        )
        if not render_echarts_safe(opts_ar, height="350px", key="ods5_area_rede"):
            fig_ag = px.bar(agg_g, x="area_geral", y="pct_mat_fem", color="rede_desc", barmode="group")
            st.plotly_chart(_estilizar_plotly(fig_ag, 350), use_container_width=True)

    st.divider()
    render_chart_header(
        "Cursos com menor e maior participação feminina",
        "Ordenação entre cursos com ao menos 500 matrículas no recorte filtrado.",
    )
    agg_curso = agregar_por_dimensao(df, ["nome_curso", "area_geral"])
    agg_relev = agg_curso[agg_curso["qt_matriculados"] >= 500]
    if agg_relev.empty:
        agg_relev = agg_curso

    col_cfg = {
        "nome_curso": st.column_config.TextColumn("Curso", width="medium"),
        "area_geral": st.column_config.TextColumn("Área STEM"),
        "qt_matriculados": st.column_config.NumberColumn("Matrículas", format="%d"),
        "pct_mat_fem": st.column_config.ProgressColumn("Mulheres", min_value=0, max_value=100, format="%.1f%%"),
        "delta_funil_fem_pp": st.column_config.NumberColumn("Delta funil", format="%+.2f pp"),
    }
    cols_tab = ["nome_curso", "area_geral", "qt_matriculados", "pct_mat_fem", "delta_funil_fem_pp"]

    c_low, c_high = st.columns(2, gap="large")
    with c_low:
        st.caption("Menor participação feminina")
        st.dataframe(
            agg_relev.sort_values("pct_mat_fem", ascending=True).head(10)[cols_tab],
            column_config=col_cfg,
            use_container_width=True,
            hide_index=True,
        )
    with c_high:
        st.caption("Maior participação feminina")
        st.dataframe(
            agg_relev.sort_values("pct_mat_fem", ascending=False).head(10)[cols_tab],
            column_config=col_cfg,
            use_container_width=True,
            hide_index=True,
        )


def _secao_ods18(df: pd.DataFrame, kpis: dict, foco_raca: str) -> None:
    render_section_header(
        "Igualdade étnico-racial em STEM (ODS 18)",
        "Participação de pessoas pretas, pardas e indígenas (PPI) e taxa de subnotificação racial.",
    )

    render_stat_row(
        [
            {
                "label": "PPI nas matrículas declaradas",
                "value": f"{kpis['pct_mat_ppi_declarado']:.2f}%",
                "note": "Exclui cor não declarada (RN16)",
            },
            {
                "label": "Concl. / ingresso PPI",
                "value": f"{kpis['razao_conc_ing_ppi_pct']:.2f}%",
                "note": "Eficiência do funil PPI",
            },
            {
                "label": "Concl. / ingresso branca",
                "value": f"{kpis['razao_conc_ing_branca_pct']:.2f}%",
                "note": "Referência comparativa",
            },
            {
                "label": "Gap de conclusão racial",
                "value": f"{kpis['gap_conclusao_racial_pp']:+.2f} pp",
                "note": "Branca menos PPI (RN19)",
            },
        ]
    )

    col1, col2 = st.columns(2, gap="large")
    with col1:
        render_chart_header(
            "Composição racial das matrículas",
            "Distribuição absoluta segundo autodeclaração no Censo INEP.",
        )
        dados_rosca = [
            {"name": "Branca", "value": int(df["qt_mat_branca"].sum()), "itemStyle": {"color": DATA["azul"]}},
            {"name": "Parda", "value": int(df["qt_mat_parda"].sum()), "itemStyle": {"color": DATA["ambar"]}},
            {"name": "Preta", "value": int(df["qt_mat_preta"].sum()), "itemStyle": {"color": "#92400E"}},
            {"name": "Amarela", "value": int(df["qt_mat_amarela"].sum()), "itemStyle": {"color": "#EAB308"}},
            {"name": "Indígena", "value": int(df["qt_mat_indigena"].sum()), "itemStyle": {"color": DATA["verde"]}},
            {"name": "Não declarada", "value": int(df["qt_mat_cornd"].sum()), "itemStyle": {"color": "#CBD5E1"}},
        ]
        opts_donut = build_echarts_donut_raca(dados_rosca)
        if not render_echarts_safe(opts_donut, height="340px", key="ods18_donut"):
            fig_c = px.pie(pd.DataFrame(dados_rosca), names="name", values="value", hole=0.5)
            st.plotly_chart(_estilizar_plotly(fig_c, 340), use_container_width=True)

    with col2:
        render_chart_header(
            f"Trajetória no funil: {foco_raca}",
            "Participação percentual no ingresso, na matrícula ativa e na conclusão.",
        )
        mapa_raca_cols = {
            "PPI (Preta, Parda e Indígena)": ("qt_ing_ppi", "qt_mat_ppi", "qt_conc_ppi", DATA["ambar"]),
            "Branca": ("qt_ing_branca", "qt_mat_branca", "qt_conc_branca", DATA["azul"]),
            "Preta": ("qt_ing_preta", "qt_mat_preta", "qt_conc_preta", "#92400E"),
            "Parda": ("qt_ing_parda", "qt_mat_parda", "qt_conc_parda", DATA["ambar"]),
            "Indígena": ("qt_ing_indigena", "qt_mat_indigena", "qt_conc_indigena", DATA["verde"]),
            "Amarela": ("qt_ing_amarela", "qt_mat_amarela", "qt_conc_amarela", "#EAB308"),
            "Não Declarada (Veracidade)": ("qt_ing_cornd", "qt_mat_cornd", "qt_conc_cornd", DATA["neutro"]),
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
        series_fr = {
            foco_raca: [_pct_etapa(c_ing, "ing"), _pct_etapa(c_mat, "mat"), _pct_etapa(c_conc, "conc")]
        }
        cores_fr = [cor_dest]
        if foco_raca not in {"Branca", "Não Declarada (Veracidade)"}:
            series_fr["Branca (declarados)"] = [
                _pct_etapa("qt_ing_branca", "ing"),
                _pct_etapa("qt_mat_branca", "mat"),
                _pct_etapa("qt_conc_branca", "conc"),
            ]
            cores_fr.append(DATA["azul"])

        opts_fr = build_echarts_grouped_bar(
            ["Ingresso", "Matrícula", "Conclusão"],
            series_fr,
            cores=cores_fr,
            y_max=100,
        )
        if not render_echarts_safe(opts_fr, height="340px", key=f"ods18_funil_{foco_raca}"):
            st.bar_chart(pd.DataFrame(series_fr, index=["Ingresso", "Matrícula", "Conclusão"]))

    st.divider()
    render_chart_header(
        "Participação PPI e subnotificação racial por região",
        "Contraste entre representatividade declarada e percentual de matrículas sem cor informada (RN20).",
    )
    agg_reg = agregar_por_dimensao(df, "regiao").sort_values("pct_mat_ppi_declarado", ascending=False)
    opts_reg = build_echarts_grouped_bar(
        agg_reg["regiao"].astype(str).tolist(),
        {
            "PPI nas matrículas declaradas": [round(float(v), 2) for v in agg_reg["pct_mat_ppi_declarado"]],
            "Cor não declarada (veracidade)": [round(float(v), 2) for v in agg_reg["taxa_subnotificacao_racial_pct"]],
        },
        cores=[DATA["ambar"], "#CBD5E1"],
        y_max=100,
    )
    if not render_echarts_safe(opts_reg, height="340px", key="ods18_regiao"):
        st.bar_chart(agg_reg.set_index("regiao")[["pct_mat_ppi_declarado", "taxa_subnotificacao_racial_pct"]])


def _secao_cruzamento(df: pd.DataFrame) -> None:
    render_section_header(
        "Cruzamento de gênero, raça e evasão",
        "Cada círculo representa um estado, área específica ou curso, dimensionado pelo volume de matrículas e colorido pela taxa de evasão.",
    )

    render_html(
        """
        <div class="note-inline">
            Nos microdados agregados de cursos do INEP, sexo e cor/raça aparecem em colunas separadas para ingressantes,
            matriculados e concluintes, sem desagregação para desvinculados nem cruzamento individual. O gráfico abaixo
            apresenta a relação ecológica entre participação feminina, participação PPI e evasão em cada segmento.
        </div>
        """
    )

    granularidade = st.radio(
        "Nível de agregação",
        options=["sigla_uf", "area_especifica", "nome_curso"],
        format_func=lambda k: {
            "sigla_uf": "Estados (UF)",
            "area_especifica": "Áreas específicas",
            "nome_curso": "Cursos (40 maiores)",
        }[k],
        horizontal=True,
    )

    grupos = ["sigla_uf", "regiao"] if granularidade == "sigla_uf" else [granularidade, "area_geral"]
    agg = agregar_por_dimensao(df, grupos)
    if granularidade == "nome_curso":
        agg = agg.sort_values("qt_matriculados", ascending=False).head(40)

    agg_plot = agg[agg["qt_matriculados"] > 0]
    if agg_plot.empty:
        st.warning("Não há registros com matrículas positivas para exibir neste recorte.")
        return

    opts_sc = build_echarts_scatter_interseccional(agg_plot, granularidade)
    if not render_echarts_safe(opts_sc, height="490px", key=f"scatter_{granularidade}"):
        fig_sc = px.scatter(
            agg_plot,
            x="pct_mat_fem",
            y="pct_mat_ppi_declarado",
            size="qt_matriculados",
            color="taxa_evasao_matriculas_pct",
            color_continuous_scale=[DATA["verde"], DATA["ambar"], DATA["vermelho"]],
            hover_name=granularidade,
        )
        st.plotly_chart(_estilizar_plotly(fig_sc, 470), use_container_width=True)


def _secao_exploracao(df: pd.DataFrame) -> None:
    render_section_header(
        "Exploração territorial e por curso",
        "Aprofunde a análise por hierarquia geográfica (IBGE) ou acadêmica e exporte os dados filtrados.",
    )

    modo = st.radio(
        "Hierarquia",
        options=["Região, estado e município", "Área STEM, área específica e curso"],
        horizontal=True,
    )

    if modo.startswith("Região"):
        c1, c2 = st.columns(2)
        with c1:
            reg_sel = st.selectbox("Região", ["Todas"] + sorted(df["regiao"].unique().tolist()))
        df_sub = df if reg_sel == "Todas" else df[df["regiao"] == reg_sel]
        with c2:
            uf_sel = st.selectbox("Estado (UF)", ["Todos"] + sorted(df_sub["sigla_uf"].unique().tolist()))
        df_sub = df_sub if uf_sel == "Todos" else df_sub[df_sub["sigla_uf"] == uf_sel]
        hierarquia = ["regiao", "sigla_uf", "nome_municipio"]
    else:
        c1, c2 = st.columns(2)
        with c1:
            area_sel = st.selectbox("Área STEM", ["Todas"] + sorted(df["area_geral"].unique().tolist()))
        df_sub = df if area_sel == "Todas" else df[df["area_geral"] == area_sel]
        with c2:
            esp_sel = st.selectbox(
                "Área específica",
                ["Todas"] + sorted(df_sub["area_especifica"].unique().tolist()),
            )
        df_sub = df_sub if esp_sel == "Todas" else df_sub[df_sub["area_especifica"] == esp_sel]
        hierarquia = ["area_geral", "area_especifica", "nome_curso"]

    agg_dd = agregar_por_dimensao(df_sub, hierarquia).sort_values("qt_matriculados", ascending=False)
    top_sun = agg_dd[agg_dd["qt_matriculados"] > 0].head(80)

    if not top_sun.empty:
        fig_sun = px.sunburst(
            top_sun,
            path=hierarquia,
            values="qt_matriculados",
            color="taxa_evasao_matriculas_pct",
            color_continuous_scale=[DATA["verde"], DATA["ambar"], DATA["vermelho"]],
            hover_data=["pct_mat_fem", "pct_mat_ppi_declarado"],
        )
        fig_sun.update_coloraxes(colorbar_title="Evasão (%)")
        st.plotly_chart(_estilizar_plotly(fig_sun, 450), use_container_width=True)

    col_busca, col_dl = st.columns([3.2, 1.0], vertical_alignment="bottom")
    with col_busca:
        busca = st.text_input("Buscar na tabela", placeholder="Digite curso, estado ou município")
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
    with col_dl:
        csv_bytes = tabela[cols_exibir].to_csv(index=False, sep=";").encode("utf-8-sig")
        st.download_button(
            label="Exportar recorte em CSV",
            data=csv_bytes,
            file_name="observatorio_stem_recorte.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.dataframe(
        tabela[cols_exibir].head(200),
        column_config={
            "regiao": st.column_config.TextColumn("Região"),
            "sigla_uf": st.column_config.TextColumn("UF", width="small"),
            "nome_municipio": st.column_config.TextColumn("Município"),
            "area_geral": st.column_config.TextColumn("Área STEM"),
            "area_especifica": st.column_config.TextColumn("Área específica"),
            "nome_curso": st.column_config.TextColumn("Curso"),
            "qt_ingressantes": st.column_config.NumberColumn("Ingressantes", format="%d"),
            "qt_matriculados": st.column_config.NumberColumn("Matrículas", format="%d"),
            "qt_concluintes": st.column_config.NumberColumn("Concluintes", format="%d"),
            "qt_desvinculados": st.column_config.NumberColumn("Desvinculados", format="%d"),
            "taxa_evasao_matriculas_pct": st.column_config.ProgressColumn(
                "Evasão", min_value=0, max_value=100, format="%.2f%%"
            ),
            "taxa_retencao_pct": st.column_config.ProgressColumn(
                "Retenção", min_value=0, max_value=100, format="%.2f%%"
            ),
            "pct_mat_fem": st.column_config.ProgressColumn(
                "Mulheres", min_value=0, max_value=100, format="%.1f%%"
            ),
            "pct_mat_ppi_declarado": st.column_config.ProgressColumn(
                "PPI decl.", min_value=0, max_value=100, format="%.1f%%"
            ),
        },
        use_container_width=True,
        hide_index=True,
    )


def main() -> None:
    df, _origem, _aviso = carregar_dados()
    df_filtrado, foco_genero, foco_raca, resumo_filtro = _aplicar_filtros_sidebar(df)

    render_page_header(resumo_filtro)

    if not HAS_ECHARTS:
        render_aviso_discreto(
            "Instale streamlit-echarts (pip install -r dashboard/requirements.txt) para ativar os gráficos interativos."
        )

    if df_filtrado.empty:
        st.error("Nenhum registro corresponde aos filtros atuais. Ajuste os critérios na barra lateral.")
        return

    secao = render_nav_bar()

    kpis = calcular_kpis(df_filtrado)
    _render_kpis(kpis)

    if secao == "Panorama":
        _secao_panorama(df_filtrado, kpis)
    elif secao == "Gênero (ODS 5)":
        _secao_ods5(df_filtrado, kpis, foco_genero)
    elif secao == "Raça e cor (ODS 18)":
        _secao_ods18(df_filtrado, kpis, foco_raca)
    elif secao == "Cruzamento":
        _secao_cruzamento(df_filtrado)
    else:
        _secao_exploracao(df_filtrado)


if __name__ == "__main__":
    main()
