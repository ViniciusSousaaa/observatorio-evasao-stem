"""Sistema visual minimalista e construtores de gráficos (Apache ECharts + HTML/CSS).

Princípio central: interface monocromática e silenciosa (#FFFFFF / #F7F8FA / #111827)
para que toda a cor visível na tela represente dados nos gráficos.
"""

from __future__ import annotations

import html
from typing import Any

import pandas as pd
import streamlit as st

try:
    from streamlit_echarts import st_echarts

    HAS_ECHARTS = True
except ImportError:
    HAS_ECHARTS = False

try:
    from streamlit_option_menu import option_menu

    HAS_OPTION_MENU = True
except ImportError:
    HAS_OPTION_MENU = False


# Neutros estruturais da interface (sem cor decorativa)
UI = {
    "bg": "#FFFFFF",
    "surface": "#F7F8FA",
    "border": "#E5E7EB",
    "ink": "#111827",
    "muted": "#6B7280",
    "subtle": "#9CA3AF",
}

# Paleta dedicada exclusivamente aos gráficos (poucas cores, alto contraste)
DATA = {
    "azul": "#2563EB",      # Referência, volume, masculino, branca
    "vermelho": "#DC2626",  # Evasão / desvinculados
    "verde": "#0D9488",     # Retenção / concluintes
    "violeta": "#7C3AED",   # ODS 5 — mulheres
    "ambar": "#D97706",     # ODS 18 — PPI / trancamento
    "neutro": "#94A3B8",    # Não declarada / transferidos
}

COR_POR_METRICA = {
    "taxa_evasao_matriculas_pct": DATA["vermelho"],
    "taxa_evasao_vinculos_pct": DATA["vermelho"],
    "taxa_retencao_pct": DATA["verde"],
    "taxa_trancamento_pct": DATA["ambar"],
    "taxa_transferencia_pct": DATA["azul"],
    "taxa_conclusao_pct": DATA["verde"],
    "razao_conclusao_ingresso_pct": DATA["azul"],
    "pct_mat_fem": DATA["violeta"],
    "pct_mat_ppi_declarado": DATA["ambar"],
    "taxa_subnotificacao_racial_pct": DATA["neutro"],
}


def render_html(markup: str) -> None:
    """Remove indentação e linhas em branco para evitar parsing de bloco de código."""
    limpo = "\n".join(linha.strip() for linha in markup.splitlines() if linha.strip())
    st.markdown(limpo, unsafe_allow_html=True)


def injetar_css_minimalista() -> None:
    """Injeta tipografia IBM Plex Sans e estilos neutros minimalistas."""
    render_html(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            color: #111827;
            -webkit-font-smoothing: antialiased;
        }

        .stApp {
            background-color: #FFFFFF;
        }

        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 3rem;
            max-width: 1320px;
        }

        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        header[data-testid="stHeader"] {
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(6px);
        }

        /* Sidebar clara, discreta e monocromática */
        section[data-testid="stSidebar"] {
            background-color: #F7F8FA;
            border-right: 1px solid #E5E7EB;
        }
        section[data-testid="stSidebar"] label {
            color: #374151 !important;
            font-size: 0.8rem !important;
            font-weight: 500 !important;
        }
        section[data-testid="stSidebar"] [data-baseweb="select"] > div {
            background-color: #FFFFFF !important;
            border: 1px solid #D1D5DB !important;
            border-radius: 3px !important;
        }
        section[data-testid="stSidebar"] [data-baseweb="tag"] {
            background-color: #E5E7EB !important;
            color: #111827 !important;
            border-radius: 3px !important;
        }
        section[data-testid="stSidebar"] [data-baseweb="tag"] > span {
            border-radius: 3px !important;
        }
        section[data-testid="stSidebar"] [data-baseweb="tag"] svg {
            fill: #4B5563 !important;
        }
        section[data-testid="stSidebar"] input {
            border-radius: 3px !important;
        }
        section[data-testid="stSidebar"] hr {
            border-color: #E5E7EB;
        }

        /* Cabeçalho limpo sem decoração excessiva */
        .page-header {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: flex-end;
            gap: 1rem;
            padding-bottom: 1.15rem;
            border-bottom: 1px solid #E5E7EB;
            margin-bottom: 0.75rem;
        }
        .page-title {
            font-size: 1.75rem;
            font-weight: 600;
            letter-spacing: -0.025em;
            line-height: 1.2;
            color: #111827;
            margin: 0 0 0.3rem 0;
        }
        .page-desc {
            font-size: 0.9rem;
            color: #6B7280;
            line-height: 1.45;
            max-width: 68ch;
            margin: 0;
        }
        .source-badge {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            font-size: 0.78rem;
            font-weight: 500;
            color: #374151;
            background: #F7F8FA;
            border: 1px solid #E5E7EB;
            border-radius: 999px;
            padding: 5px 12px;
            white-space: nowrap;
        }
        .source-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            display: inline-block;
        }

        /* Aviso enxuto de ambiente */
        .quiet-banner {
            background: #F7F8FA;
            border-left: 2px solid #9CA3AF;
            padding: 0.65rem 0.95rem;
            margin: 0.5rem 0 1rem 0;
            font-size: 0.83rem;
            color: #4B5563;
            line-height: 1.45;
        }

        /* Faixa única de KPIs (sem 6 cards separados) */
        .kpi-strip {
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            border-top: 1px solid #E5E7EB;
            border-bottom: 1px solid #E5E7EB;
            margin: 0.75rem 0 1.65rem 0;
            background: #FFFFFF;
        }
        @media (max-width: 1120px) {
            .kpi-strip { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        }
        @media (max-width: 640px) {
            .kpi-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        .kpi-cell {
            padding: 1rem 1.1rem;
            border-right: 1px solid #E5E7EB;
        }
        .kpi-cell:last-child {
            border-right: none;
        }
        .kpi-head {
            display: flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 0.35rem;
        }
        .kpi-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            flex-shrink: 0;
        }
        .kpi-label {
            font-size: 0.78rem;
            font-weight: 500;
            color: #6B7280;
        }
        .kpi-value {
            font-size: 1.6rem;
            font-weight: 600;
            letter-spacing: -0.02em;
            line-height: 1.15;
            color: #111827;
            font-variant-numeric: tabular-nums;
            margin-bottom: 0.25rem;
        }
        .kpi-meta {
            font-size: 0.75rem;
            color: #6B7280;
            font-variant-numeric: tabular-nums;
        }

        /* Faixa secundária de 4 métricas (ODS 5 / ODS 18) */
        .stat-row {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            border-top: 1px solid #E5E7EB;
            border-bottom: 1px solid #E5E7EB;
            margin: 0.5rem 0 1.5rem 0;
        }
        @media (max-width: 900px) {
            .stat-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        .stat-cell {
            padding: 0.85rem 1rem;
            border-right: 1px solid #E5E7EB;
        }
        .stat-cell:last-child {
            border-right: none;
        }
        .stat-label {
            font-size: 0.77rem;
            color: #6B7280;
            margin-bottom: 0.25rem;
        }
        .stat-val {
            font-size: 1.35rem;
            font-weight: 600;
            color: #111827;
            font-variant-numeric: tabular-nums;
        }
        .stat-note {
            font-size: 0.74rem;
            color: #9CA3AF;
            margin-top: 2px;
        }

        /* Títulos de seção e gráfico (sentence case, sem ornamento) */
        .section-title {
            font-size: 1.18rem;
            font-weight: 600;
            letter-spacing: -0.015em;
            color: #111827;
            margin: 0 0 0.2rem 0;
        }
        .section-lead {
            font-size: 0.86rem;
            color: #6B7280;
            max-width: 72ch;
            margin: 0 0 1.1rem 0;
        }
        .chart-title {
            font-size: 0.94rem;
            font-weight: 600;
            color: #111827;
            margin: 0 0 0.15rem 0;
        }
        .chart-caption {
            font-size: 0.78rem;
            color: #6B7280;
            margin: 0 0 0.5rem 0;
        }

        .sidebar-heading {
            font-size: 0.92rem;
            font-weight: 600;
            color: #111827;
            margin: 0 0 0.75rem 0;
            padding-bottom: 0.55rem;
            border-bottom: 1px solid #E5E7EB;
        }
        .sidebar-subhead {
            font-size: 0.82rem;
            font-weight: 600;
            color: #374151;
            margin: 0.25rem 0 0.5rem 0;
        }

        .note-inline {
            font-size: 0.83rem;
            color: #4B5563;
            line-height: 1.5;
            max-width: 78ch;
            padding-left: 0.85rem;
            border-left: 2px solid #D1D5DB;
            margin: 0.25rem 0 1.1rem 0;
        }

        /* Botão de exportação sóbrio */
        .stDownloadButton > button {
            background-color: #111827 !important;
            color: #FFFFFF !important;
            border: 1px solid #111827 !important;
            border-radius: 6px !important;
            font-weight: 500 !important;
            font-size: 0.82rem !important;
        }
        .stDownloadButton > button:hover {
            background-color: #374151 !important;
            border-color: #374151 !important;
        }
        </style>
        """
    )


def render_page_header(resumo_filtro: str) -> None:
    render_html(
        f"""
        <div class="page-header">
            <div>
                <h1 class="page-title">Observatório de evasão em cursos STEM</h1>
                <p class="page-desc">
                    Análise dos microdados do Censo da Educação Superior (INEP) e IBGE para {html.escape(resumo_filtro)}.
                </p>
            </div>
        </div>
        """
    )


def render_aviso_discreto(texto: str) -> None:
    render_html(f'<div class="quiet-banner">{html.escape(texto)}</div>')


def render_nav_bar() -> str:
    """Navegação horizontal minimalista com sublinhado na aba ativa."""
    opcoes = [
        "Panorama",
        "Gênero (ODS 5)",
        "Raça e cor (ODS 18)",
        "Cruzamento",
        "Território e cursos",
    ]
    if HAS_OPTION_MENU:
        return option_menu(
            menu_title=None,
            options=opcoes,
            icons=[""] * len(opcoes),
            orientation="horizontal",
            styles={
                "container": {
                    "padding": "0",
                    "background-color": "#FFFFFF",
                    "border-bottom": "1px solid #E5E7EB",
                    "border-radius": "0px",
                    "margin-bottom": "0.5rem",
                },
                "icon": {"display": "none"},
                "nav-link": {
                    "font-family": "'IBM Plex Sans', sans-serif",
                    "font-size": "0.86rem",
                    "font-weight": "500",
                    "color": "#6B7280",
                    "text-align": "center",
                    "margin": "0 6px 0 0",
                    "padding": "0.6rem 0.9rem",
                    "border-radius": "0px",
                    "border-bottom": "2px solid transparent",
                    "--hover-color": "#F7F8FA",
                },
                "nav-link-selected": {
                    "background-color": "transparent",
                    "color": "#111827",
                    "font-weight": "600",
                    "border-bottom": "2px solid #111827",
                },
            },
        )
    return st.radio("Navegação", options=opcoes, horizontal=True, label_visibility="collapsed")


def render_kpi_strip(items: list[dict[str, str]]) -> None:
    """Faixa única de indicadores com divisórias finas sem ícones decorativos."""
    celulas = []
    for item in items:
        celulas.append(
            f'<div class="kpi-cell">'
            f'<div class="kpi-head">'
            f'<span class="kpi-label">{html.escape(item["label"])}</span>'
            f"</div>"
            f'<div class="kpi-value">{html.escape(item["value"])}</div>'
            f'<div class="kpi-meta">{html.escape(item["meta"])}</div>'
            f"</div>"
        )
    render_html(f'<div class="kpi-strip">{"".join(celulas)}</div>')


def render_stat_row(items: list[dict[str, str]]) -> None:
    celulas = []
    for item in items:
        celulas.append(
            f'<div class="stat-cell">'
            f'<div class="stat-label">{html.escape(item["label"])}</div>'
            f'<div class="stat-val">{html.escape(item["value"])}</div>'
            f'<div class="stat-note">{html.escape(item.get("note", ""))}</div>'
            f"</div>"
        )
    render_html(f'<div class="stat-row">{"".join(celulas)}</div>')


def render_section_header(title: str, lead: str = "") -> None:
    lead_html = f'<p class="section-lead">{html.escape(lead)}</p>' if lead else ""
    render_html(f'<h2 class="section-title">{html.escape(title)}</h2>{lead_html}')


def render_chart_header(title: str, caption: str = "") -> None:
    cap_html = f'<p class="chart-caption">{html.escape(caption)}</p>' if caption else ""
    render_html(f'<div class="chart-title">{html.escape(title)}</div>{cap_html}')


def render_echarts_safe(options: dict[str, Any], height: str = "400px", key: str | None = None) -> bool:
    if not HAS_ECHARTS:
        return False
    st_echarts(options=options, height=height, key=key)
    return True


def _tooltip(trigger: str = "axis") -> dict[str, Any]:
    return {
        "trigger": trigger,
        "backgroundColor": "#111827",
        "borderColor": "#1F2937",
        "borderWidth": 1,
        "padding": [9, 13],
        "textStyle": {
            "color": "#F9FAFB",
            "fontFamily": "IBM Plex Sans, sans-serif",
            "fontSize": 12,
        },
    }


def build_echarts_horizontal_bar(
    categorias: list[str],
    valores: list[float],
    cor: str,
    sufixo: str = "%",
    tooltips: list[str] | None = None,
) -> dict[str, Any]:
    max_val = max(valores) if valores else 100.0
    if tooltips:
        dados_serie: list[Any] = [
            {"value": v, "tooltip": {"formatter": tt}}
            for v, tt in zip(valores, tooltips)
        ]
        tt_cfg = _tooltip("item")
    else:
        dados_serie = valores
        tt_cfg = {**_tooltip("axis"), "axisPointer": {"type": "shadow"}}

    return {
        "backgroundColor": "transparent",
        "animationDuration": 450,
        "grid": {"left": "1%", "right": "10%", "top": "4%", "bottom": "4%", "containLabel": True},
        "tooltip": tt_cfg,
        "xAxis": {
            "type": "value",
            "max": round(max_val * 1.16, 1) if max_val > 0 else 100,
            "axisLabel": {
                "formatter": f"{{value}}{sufixo}",
                "color": UI["muted"],
                "fontFamily": "IBM Plex Sans, sans-serif",
                "fontSize": 11,
            },
            "splitLine": {"lineStyle": {"color": "#F1F3F5"}},
        },
        "yAxis": {
            "type": "category",
            "data": categorias,
            "axisLine": {"lineStyle": {"color": UI["border"]}},
            "axisTick": {"show": False},
            "axisLabel": {
                "color": UI["ink"],
                "fontFamily": "IBM Plex Sans, sans-serif",
                "fontSize": 12,
                "width": 230,
                "overflow": "truncate",
            },
        },
        "series": [
            {
                "type": "bar",
                "data": dados_serie,
                "barMaxWidth": 22,
                "showBackground": True,
                "backgroundStyle": {"color": "#F3F4F6", "borderRadius": [0, 4, 4, 0]},
                "itemStyle": {"color": cor, "borderRadius": [0, 4, 4, 0]},
                "label": {
                    "show": True,
                    "position": "right",
                    "formatter": f"{{c}}{sufixo}",
                    "color": UI["ink"],
                    "fontFamily": "IBM Plex Sans, sans-serif",
                    "fontSize": 11,
                    "fontWeight": 600,
                },
            }
        ],
    }


def build_echarts_line_temporal(df_tempo: pd.DataFrame, metrica_key: str) -> dict[str, Any]:
    anos = [str(a) for a in sorted(df_tempo["ano_censo"].unique().tolist())]
    areas = sorted(df_tempo["area_geral"].unique().tolist())
    cores = [DATA["azul"], DATA["vermelho"], DATA["verde"], DATA["ambar"]]

    series = []
    for idx, area in enumerate(areas):
        sub = df_tempo[df_tempo["area_geral"] == area].set_index("ano_censo")
        vals = [
            round(float(sub.loc[int(a), metrica_key]), 2) if int(a) in sub.index else None
            for a in anos
        ]
        cor = cores[idx % len(cores)]
        series.append(
            {
                "name": area,
                "type": "line",
                "smooth": 0.2,
                "symbol": "circle",
                "symbolSize": 8,
                "lineStyle": {"width": 2.5, "color": cor},
                "itemStyle": {"color": cor, "borderColor": "#FFFFFF", "borderWidth": 2},
                "data": vals,
            }
        )

    return {
        "backgroundColor": "transparent",
        "animationDuration": 500,
        "tooltip": _tooltip("axis"),
        "legend": {
            "bottom": 0,
            "icon": "circle",
            "itemWidth": 9,
            "itemHeight": 9,
            "textStyle": {"color": UI["ink"], "fontFamily": "IBM Plex Sans, sans-serif", "fontSize": 12},
        },
        "grid": {"left": "2%", "right": "4%", "top": "8%", "bottom": "18%", "containLabel": True},
        "xAxis": {
            "type": "category",
            "data": anos,
            "axisLine": {"lineStyle": {"color": UI["border"]}},
            "axisLabel": {"color": UI["ink"], "fontFamily": "IBM Plex Sans, sans-serif", "fontSize": 12},
        },
        "yAxis": {
            "type": "value",
            "axisLabel": {
                "formatter": "{value}%",
                "color": UI["muted"],
                "fontFamily": "IBM Plex Sans, sans-serif",
                "fontSize": 11,
            },
            "splitLine": {"lineStyle": {"color": "#F1F3F5"}},
        },
        "series": series,
    }


def build_echarts_sankey_fluxo(kpis: dict[str, Any]) -> dict[str, Any]:
    ing = int(kpis["total_ingressantes"])
    mat = int(kpis["total_matriculados"])
    conc = int(kpis["total_concluintes"])
    desv = int(kpis["total_desvinculados"])
    tranc = int(kpis["total_trancados"])
    transf = int(kpis["total_transferidos"])

    ativos_remanescentes = max(1, mat - tranc - transf)
    base_continuantes = max(1, (mat + desv + conc) - ing)

    nodes = [
        {"name": "Ingressantes", "itemStyle": {"color": DATA["azul"]}},
        {"name": "Coortes anteriores", "itemStyle": {"color": "#60A5FA"}},
        {"name": "Vínculos em STEM", "itemStyle": {"color": "#334155"}},
        {"name": "Permanência ativa", "itemStyle": {"color": DATA["verde"]}},
        {"name": "Concluintes", "itemStyle": {"color": "#10B981"}},
        {"name": "Desvinculados", "itemStyle": {"color": DATA["vermelho"]}},
        {"name": "Trancados", "itemStyle": {"color": DATA["ambar"]}},
        {"name": "Transferidos", "itemStyle": {"color": DATA["neutro"]}},
    ]
    links = [
        {"source": "Ingressantes", "target": "Vínculos em STEM", "value": max(1, ing)},
        {"source": "Coortes anteriores", "target": "Vínculos em STEM", "value": base_continuantes},
        {"source": "Vínculos em STEM", "target": "Permanência ativa", "value": ativos_remanescentes},
        {"source": "Vínculos em STEM", "target": "Concluintes", "value": max(1, conc)},
        {"source": "Vínculos em STEM", "target": "Desvinculados", "value": max(1, desv)},
        {"source": "Vínculos em STEM", "target": "Trancados", "value": max(1, tranc)},
        {"source": "Vínculos em STEM", "target": "Transferidos", "value": max(1, transf)},
    ]

    return {
        "backgroundColor": "transparent",
        "tooltip": {**_tooltip("item"), "formatter": "{b}: {c} estudantes"},
        "series": [
            {
                "type": "sankey",
                "left": "1%",
                "right": "20%",
                "top": "6%",
                "bottom": "6%",
                "nodeWidth": 14,
                "nodeGap": 14,
                "draggable": False,
                "emphasis": {"focus": "adjacency"},
                "lineStyle": {"color": "gradient", "curveness": 0.45, "opacity": 0.4},
                "label": {
                    "color": UI["ink"],
                    "fontFamily": "IBM Plex Sans, sans-serif",
                    "fontSize": 12,
                    "fontWeight": 500,
                },
                "data": nodes,
                "links": links,
            }
        ],
    }


def build_echarts_grouped_bar(
    categorias: list[str],
    series_dict: dict[str, list[float]],
    cores: list[str],
    linha_referencia: float | None = None,
    sufixo: str = "%",
    y_max: float | None = None,
) -> dict[str, Any]:
    series = []
    for idx, (nome, valores) in enumerate(series_dict.items()):
        cfg: dict[str, Any] = {
            "name": nome,
            "type": "bar",
            "data": valores,
            "barMaxWidth": 32,
            "itemStyle": {"color": cores[idx % len(cores)], "borderRadius": [4, 4, 0, 0]},
            "label": {
                "show": True,
                "position": "top",
                "formatter": f"{{c}}{sufixo}",
                "color": UI["ink"],
                "fontFamily": "IBM Plex Sans, sans-serif",
                "fontSize": 11,
                "fontWeight": 600,
            },
        }
        if idx == 0 and linha_referencia is not None:
            cfg["markLine"] = {
                "symbol": "none",
                "silent": True,
                "lineStyle": {"type": "dashed", "color": UI["subtle"], "width": 1.2},
                "label": {
                    "formatter": f"Paridade {linha_referencia:.0f}%",
                    "color": UI["muted"],
                    "fontFamily": "IBM Plex Sans, sans-serif",
                    "fontSize": 11,
                },
                "data": [{"yAxis": linha_referencia}],
            }
        series.append(cfg)

    y_axis: dict[str, Any] = {
        "type": "value",
        "axisLabel": {
            "formatter": f"{{value}}{sufixo}",
            "color": UI["muted"],
            "fontFamily": "IBM Plex Sans, sans-serif",
            "fontSize": 11,
        },
        "splitLine": {"lineStyle": {"color": "#F1F3F5"}},
    }
    if y_max is not None:
        y_axis["max"] = y_max

    return {
        "backgroundColor": "transparent",
        "animationDuration": 450,
        "tooltip": {**_tooltip("axis"), "axisPointer": {"type": "shadow"}},
        "legend": {
            "bottom": 0,
            "icon": "circle",
            "itemWidth": 9,
            "itemHeight": 9,
            "textStyle": {"color": UI["ink"], "fontFamily": "IBM Plex Sans, sans-serif", "fontSize": 12},
        },
        "grid": {"left": "2%", "right": "3%", "top": "10%", "bottom": "16%", "containLabel": True},
        "xAxis": {
            "type": "category",
            "data": categorias,
            "axisLine": {"lineStyle": {"color": UI["border"]}},
            "axisTick": {"show": False},
            "axisLabel": {
                "color": UI["ink"],
                "fontFamily": "IBM Plex Sans, sans-serif",
                "fontSize": 12,
                "interval": 0,
                "width": 135,
                "overflow": "break",
            },
        },
        "yAxis": y_axis,
        "series": series,
    }


def build_echarts_gauge_ipg(ipg: float) -> dict[str, Any]:
    val = max(0.0, min(1.2, round(float(ipg), 3)))
    return {
        "backgroundColor": "transparent",
        "series": [
            {
                "type": "gauge",
                "startAngle": 180,
                "endAngle": 0,
                "center": ["50%", "74%"],
                "radius": "106%",
                "min": 0,
                "max": 1.2,
                "splitNumber": 6,
                "axisLine": {
                    "lineStyle": {
                        "width": 14,
                        "color": [
                            [0.42, DATA["vermelho"]],
                            [0.75, DATA["ambar"]],
                            [1.0, DATA["verde"]],
                        ],
                    }
                },
                "pointer": {
                    "length": "52%",
                    "width": 5,
                    "offsetCenter": [0, "-16%"],
                    "itemStyle": {"color": UI["ink"]},
                },
                "axisTick": {"length": 5, "lineStyle": {"color": "auto", "width": 1}},
                "splitLine": {"length": 10, "lineStyle": {"color": "auto", "width": 1.5}},
                "axisLabel": {
                    "color": UI["muted"],
                    "fontSize": 10,
                    "fontFamily": "IBM Plex Sans, sans-serif",
                    "distance": -32,
                },
                "title": {
                    "offsetCenter": [0, "18%"],
                    "fontSize": 12,
                    "fontFamily": "IBM Plex Sans, sans-serif",
                    "color": UI["muted"],
                },
                "detail": {
                    "fontSize": 26,
                    "fontFamily": "IBM Plex Sans, sans-serif",
                    "fontWeight": 600,
                    "offsetCenter": [0, "-4%"],
                    "valueAnimation": True,
                    "color": UI["ink"],
                },
                "data": [{"value": val, "name": "Paridade ideal = 1,000"}],
            }
        ],
    }


def build_echarts_donut_raca(dados: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "backgroundColor": "transparent",
        "tooltip": {**_tooltip("item"), "formatter": "{b}<br/>{c} matrículas ({d}%)"},
        "legend": {
            "orient": "vertical",
            "right": "4%",
            "top": "middle",
            "icon": "circle",
            "itemWidth": 9,
            "itemHeight": 9,
            "textStyle": {
                "color": UI["ink"],
                "fontFamily": "IBM Plex Sans, sans-serif",
                "fontSize": 12,
            },
        },
        "series": [
            {
                "name": "Cor ou raça",
                "type": "pie",
                "radius": ["52%", "78%"],
                "center": ["36%", "50%"],
                "avoidLabelOverlap": True,
                "itemStyle": {"borderRadius": 4, "borderColor": "#FFFFFF", "borderWidth": 2},
                "label": {"show": False},
                "emphasis": {
                    "label": {
                        "show": True,
                        "fontSize": 13,
                        "fontWeight": 600,
                        "fontFamily": "IBM Plex Sans, sans-serif",
                        "color": UI["ink"],
                        "formatter": "{b}\n{d}%",
                    }
                },
                "data": dados,
            }
        ],
    }


def build_echarts_scatter_interseccional(df_agg: pd.DataFrame, col_nome: str) -> dict[str, Any]:
    max_mat = float(df_agg["qt_matriculados"].max()) if not df_agg.empty else 1.0
    max_ev = float(df_agg["taxa_evasao_matriculas_pct"].max()) if not df_agg.empty else 60.0
    min_ev = float(df_agg["taxa_evasao_matriculas_pct"].min()) if not df_agg.empty else 0.0

    pontos = []
    for _, row in df_agg.iterrows():
        nome = str(row[col_nome])
        x = round(float(row["pct_mat_fem"]), 2)
        y = round(float(row["pct_mat_ppi_declarado"]), 2)
        ev = round(float(row["taxa_evasao_matriculas_pct"]), 2)
        mat = float(row["qt_matriculados"])
        mat_fmt = f"{int(mat):,}".replace(",", ".")
        raio = 11.0 + 32.0 * ((mat / max_mat) ** 0.5) if max_mat > 0 else 13.0
        pontos.append(
            {
                "name": nome,
                "value": [x, y, ev, int(mat)],
                "symbolSize": round(raio, 1),
                "tooltip": {
                    "formatter": (
                        f"<strong>{html.escape(nome)}</strong><br/>"
                        f"Mulheres (ODS 5): <b>{x:.2f}%</b><br/>"
                        f"PPI declarados (ODS 18): <b>{y:.2f}%</b><br/>"
                        f"Taxa de evasão: <b>{ev:.2f}%</b><br/>"
                        f"Matrículas: <b>{mat_fmt}</b>"
                    )
                },
            }
        )

    return {
        "backgroundColor": "transparent",
        "animationDuration": 500,
        "grid": {"left": "7%", "right": "14%", "top": "10%", "bottom": "13%"},
        "tooltip": _tooltip("item"),
        "xAxis": {
            "type": "value",
            "name": "Participação feminina nas matrículas (%)",
            "nameLocation": "middle",
            "nameGap": 30,
            "min": 0,
            "max": 100,
            "nameTextStyle": {"color": UI["ink"], "fontWeight": 500, "fontFamily": "IBM Plex Sans"},
            "axisLabel": {"formatter": "{value}%", "color": UI["muted"], "fontFamily": "IBM Plex Sans"},
            "splitLine": {"lineStyle": {"color": "#F1F3F5"}},
        },
        "yAxis": {
            "type": "value",
            "name": "Participação PPI declarada (%)",
            "nameLocation": "middle",
            "nameGap": 44,
            "min": 0,
            "max": 100,
            "nameTextStyle": {"color": UI["ink"], "fontWeight": 500, "fontFamily": "IBM Plex Sans"},
            "axisLabel": {"formatter": "{value}%", "color": UI["muted"], "fontFamily": "IBM Plex Sans"},
            "splitLine": {"lineStyle": {"color": "#F1F3F5"}},
        },
        "visualMap": {
            "type": "continuous",
            "dimension": 2,
            "min": round(min_ev, 1),
            "max": max(round(max_ev, 1), round(min_ev, 1) + 1.0),
            "calculable": True,
            "orient": "vertical",
            "right": 4,
            "top": "center",
            "text": ["Maior evasão", "Menor evasão"],
            "textStyle": {"color": UI["muted"], "fontSize": 11, "fontFamily": "IBM Plex Sans"},
            "inRange": {"color": [DATA["verde"], DATA["ambar"], DATA["vermelho"]]},
        },
        "series": [
            {
                "type": "scatter",
                "data": pontos,
                "itemStyle": {"opacity": 0.88, "borderColor": "#FFFFFF", "borderWidth": 1.5},
                "label": {
                    "show": len(pontos) <= 28,
                    "formatter": "{b}",
                    "position": "top",
                    "color": UI["ink"],
                    "fontSize": 10,
                    "fontFamily": "IBM Plex Sans, sans-serif",
                },
                "markLine": {
                    "silent": True,
                    "symbol": "none",
                    "lineStyle": {"type": "dashed", "color": "#D1D5DB", "width": 1.2},
                    "data": [{"xAxis": 50}, {"yAxis": 50}],
                },
            }
        ],
    }
