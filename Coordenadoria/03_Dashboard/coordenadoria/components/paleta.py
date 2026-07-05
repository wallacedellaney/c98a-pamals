"""
Paleta "Torre de Controle" — igual à usada no Contrato 005 (ver
Contrato 005/Dashboard/00_Instrucoes/00_BRAND/identidade_visual.md), pra manter
a mesma identidade visual entre as duas áreas do C-98A PAMALS.

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

# Ordem categórica fixa para gráficos com mais de uma série de identidade.
CATEGORICA = [AMBER, CYAN, "#8a7fd6", SECONDARY, "#d98a4f"]

FONTE_MONO = "SF Mono, Roboto Mono, ui-monospace, Menlo, monospace"


def layout_grafico(fig, altura=260):
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


def faixa_pendencia(soma_unidades_faltantes):
    """Classificação por faixa (não por %, ver rac.md — sem base confiável pra completude)."""
    if soma_unidades_faltantes == 0:
        return "Sem pendências"
    if soma_unidades_faltantes <= 5:
        return "1 a 5 unidades faltantes"
    if soma_unidades_faltantes <= 15:
        return "6 a 15 unidades faltantes"
    return "Mais de 15 unidades faltantes"


ORDEM_FAIXAS = [
    "Sem pendências",
    "1 a 5 unidades faltantes",
    "6 a 15 unidades faltantes",
    "Mais de 15 unidades faltantes",
]

# Cores por código de situação operacional diária (ver
# 00_Instrucoes/disponibilidade_diaria.md). Reaproveita a paleta da marca —
# nada de cor nova fora da identidade "Torre de Controle".
COR_SITUACAO = {
    "DI": STATUS["good"],
    "DO": CYAN,
    "II": AMBER,
    "IN": STATUS["critical"],
    "ITR": SECONDARY,
    "IS": CATEGORICA[2],  # roxo
    "IP": "#5a4632",
}

NOME_SITUACAO = {
    "DI": "Disponível",
    "DO": "Disponível c/ restrição",
    "II": "Manutenção programada",
    "IN": "Manutenção não programada",
    "ITR": "Aguardando transporte",
    "IS": "Aguardando suprimento",
    "IP": "Indisponibilidade prolongada",
}
