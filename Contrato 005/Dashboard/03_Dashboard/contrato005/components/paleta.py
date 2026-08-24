"""
Paleta da direção "Torre de Controle" (ver 00_Instrucoes/00_BRAND/identidade_visual.md).

amber/cyan = cor de marca (nunca usar como status).
good/critical = cor de status (nunca usar como série qualquer).

**Refinamento visual sitewide (2026-08-24)** — pedido do Wallace ("brief"
completo de 20 itens: manter a identidade atual — dark mode, laranja,
fonte, abas, dados — só melhorar hierarquia/organização/cores
semânticas). Regra confirmada no brief: laranja = identidade/seleção,
nunca "decoração" de problema; vermelho só pra problema real (fora do
prazo/vencido); verde só pra positivo (dentro do prazo/entregue); cinza
pra neutro. `metrica_html()`/`titulo_bloco()` abaixo são os componentes
novos, pensados pra reaproveitar em qualquer seção que precise de cards
de métrica com cor semântica (não só Reparáveis) — `[data-testid=
"stMetricValue"]` no CSS global de `contrato_app.py` força a cor AMBER
com `!important` em todo `st.metric()` da área (bom pra métrica neutra,
mas não dá pra colorir de vermelho/verde por cima) — por isso um card
que precisa de cor semântica usa HTML puro, não `st.metric()`.
"""

import streamlit as st

BG = "#10151b"
PANEL = "#161d24"
INK = "#eef2f4"
SECONDARY = "#7e93a1"
LINE = "#2a343d"

AMBER = "#f2a93b"
CYAN = "#5fd0d9"

STATUS = {
    "good": "#4fb477",
    "critical": "#e2564f",
}

# Espaçamento vertical consistente — pedido do Wallace: "criar uma
# variável de espaçamento consistente no CSS" (distância uniforme entre
# cabeçalho/controles/indicadores/gráficos/tabelas/notas, sem elementos
# colados nem vãos grandes). Usado em `margin`/`padding` de blocos HTML
# customizados (`st.markdown` com `unsafe_allow_html`) — `st.columns`/
# `st.divider()` nativos do Streamlit já têm seu próprio espaçamento fixo,
# não dá pra sobrescrever token por token neles.
ESPACO = {"xs": "0.35rem", "sm": "0.7rem", "md": "1.1rem", "lg": "1.8rem", "xl": "2.6rem"}

# Ordem categórica fixa para gráficos com mais de uma série de identidade
# (nunca ciclar, nunca reordenar por rank/filtro).
CATEGORICA = [AMBER, CYAN, "#8a7fd6", SECONDARY, "#d98a4f"]

FONTE_MONO = "SF Mono, Roboto Mono, ui-monospace, Menlo, monospace"


def layout_grafico(fig, altura=200):
    """Aplica o fundo/grade/tipografia padrão da Torre de Controle a uma figura Plotly."""
    fig.update_layout(
        height=altura,
        plot_bgcolor=PANEL,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONTE_MONO, color=SECONDARY, size=12),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    fig.update_xaxes(gridcolor=LINE, zerolinecolor=LINE, color=SECONDARY)
    fig.update_yaxes(gridcolor=LINE, zerolinecolor=LINE, color=SECONDARY)
    return fig


def metrica_html(col, label, valor, cor=None, tamanho="2rem"):
    """Card de métrica em HTML puro (label pequeno/cinza/maiúsculo em cima,
    valor grande/forte embaixo) — mesma hierarquia visual do `st.metric()`
    nativo (ver CSS global em `contrato_app.py`), mas com `cor` livre pra
    poder ser semântica (STATUS["critical"]/STATUS["good"]), o que
    `st.metric()` não permite por causa do `!important` no CSS global.
    `cor=None` usa a cor padrão do tema (texto claro, mesmo efeito visual
    de um `st.metric()` neutro sem forçar AMBER)."""
    cor = cor or INK
    col.markdown(
        f'<div style="font-size:.72rem;color:{SECONDARY};text-transform:uppercase;'
        f'letter-spacing:.06em;margin-bottom:.15rem;">{label}</div>'
        f'<div style="font-size:{tamanho};font-weight:700;color:{cor};line-height:1.25;">{valor}</div>',
        unsafe_allow_html=True,
    )


def titulo_bloco(texto):
    """Cabeçalho pequeno de um "bloco" de métricas relacionadas (ex.: "OS —
    VOLUME", "PRAZO CONTRATUAL") — pedido do Wallace: agrupar métricas
    "visualmente relacionadas" em vez de uma sequência solta do mesmo
    peso. Só texto pequeno/maiúsculo/laranja discreto, não compete com o
    título da seção (`##### Nome da seção`, nível 2 da hierarquia)."""
    st.markdown(
        f'<div style="font-size:.68rem;color:{AMBER};text-transform:uppercase;'
        f'letter-spacing:.08em;font-weight:600;margin:{ESPACO["sm"]} 0 {ESPACO["xs"]} 0;">{texto}</div>',
        unsafe_allow_html=True,
    )
