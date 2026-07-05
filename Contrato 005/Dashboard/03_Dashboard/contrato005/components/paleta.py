"""
Paleta da direção "Torre de Controle" (ver 00_Instrucoes/00_BRAND/identidade_visual.md).

amber/cyan = cor de marca (nunca usar como status).
good/critical = cor de status (nunca usar como série qualquer).
"""

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
