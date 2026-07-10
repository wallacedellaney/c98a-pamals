"""
Tema visual centralizado da área Projetos (MTA/TPJL) — cores, tipografia,
grid responsivo e componentes HTML reutilizáveis (card de indicador, selo de
status, cabeçalho de página, card de projeto na home). Revisão completa
pedida pelo Wallace em 2026-07-09: "design profissional, responsivo, sem
precisar de zoom, paleta consistente com significado fixo por cor".

Único módulo de tema da área — qualquer cor/espaçamento/componente visual
novo entra aqui, não espalhado pelos arquivos de secoes/.

Regra de cor (pedida explicitamente, não inventar variação):
- Laranja (PRIMARY) é a cor de marca/destaque — botões, aba ativa, seleção,
  série principal dos gráficos. NUNCA em todo texto/número comum.
- Números comuns usam branco (INK).
- Verde (STATUS["good"]) só pra concluído/positivo.
- Azul (STATUS["info"]) só pra andamento/informativo.
- Amarelo (STATUS["warning"]) só pra atenção.
- Vermelho (STATUS["critical"]) só pra atraso/erro/cancelamento/problema.
- Cinza (STATUS["neutro"]) pra neutro/vazio/encerrado.
- Sem roxo, sem ciano solto — a ordem categórica fixa dos gráficos é
  laranja/azul/verde/amarelo/vermelho (CATEGORICA), nunca cor aleatória por
  gráfico.
"""

import math

import streamlit as st

BG = "#0B1118"
PANEL = "#121A24"
PANEL_2 = "#182230"
PANEL_HOVER = "#1D2938"
LINE = "#293747"

INK = "#F3F6F9"
SECONDARY = "#A6B2C1"
MUTED = "#718096"

PRIMARY = "#F4A62A"
PRIMARY_HOVER = "#FFB84A"
PRIMARY_SOFT = "rgba(244, 166, 42, 0.12)"

STATUS = {
    "info": "#4D9DE0",
    "good": "#3DBB83",
    "warning": "#F2C14E",
    "critical": "#E06470",
    "neutro": MUTED,
}

# Ordem categórica fixa pros gráficos (nunca ciclar cor aleatória por série).
CATEGORICA = [PRIMARY, STATUS["info"], STATUS["good"], STATUS["warning"], STATUS["critical"]]

# Cores fixas de "Situação consolidada" (MTA) — usar em TODOS os gráficos que
# mostrarem essa dimensão, nunca uma paleta diferente por gráfico.
COR_SITUACAO_MTA = {
    "Atendido": STATUS["good"],
    "Aprovado, aguardando atendimento": STATUS["info"],
    "Em trâmite": STATUS["warning"],
    "Não aprovado": STATUS["critical"],
    "Sem informação": STATUS["neutro"],
}

# Cores fixas de "Situação da previsão" (TPJL).
COR_SITUACAO_PREVISAO = {
    "No prazo": STATUS["info"],
    "Concluído": STATUS["good"],
    "Vencido": STATUS["critical"],
    "Cancelado": STATUS["neutro"],
    "Sem data definida": STATUS["neutro"],
}

FONTE_BASE = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Roboto, sans-serif"
FONTE_MONO = "SF Mono, Roboto Mono, ui-monospace, Menlo, monospace"

MAX_WIDTH = "1560px"


def moeda_completa(valor):
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "R$ 0,00"
    return "R$ " + f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def moeda_compacta(valor):
    """Formato compacto pra caber em card/rótulo de barra (ex.: "R$ 88,2
    mi") — o valor completo continua disponível no hover/detalhe."""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "R$ 0"
    sinal = "-" if valor < 0 else ""
    absv = abs(valor)
    if absv >= 1_000_000:
        texto = f"{absv / 1_000_000:.1f}".replace(".", ",") + " mi"
    elif absv >= 1_000:
        texto = f"{absv / 1_000:.0f} mil"
    else:
        texto = f"{absv:.0f}"
    return f"{sinal}R$ {texto}"


def layout_grafico(fig, altura=340):
    """Fundo transparente, grade discreta, legenda com contraste — altura
    entre 300-380px por padrão (pedido explícito, nunca gráficos gigantes ou
    esmagados)."""
    fig.update_layout(
        height=altura,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONTE_BASE, color=SECONDARY, size=13),
        margin=dict(l=8, r=8, t=32, b=8),
        legend=dict(font=dict(color=INK, size=12), bgcolor="rgba(0,0,0,0)", orientation="h", y=1.12),
    )
    fig.update_xaxes(gridcolor=LINE, zerolinecolor=LINE, color=SECONDARY, showgrid=True, gridwidth=1)
    fig.update_yaxes(gridcolor=LINE, zerolinecolor=LINE, color=SECONDARY, showgrid=True, gridwidth=1)
    return fig


def injetar_tema():
    """CSS global do tema — chamar UMA VEZ no topo do render() de cada
    página (projetos_app.py já chama; secoes/ não precisam chamar de novo)."""
    st.markdown(
        f"""
        <style>
        .stApp {{ background: {BG}; }}
        .block-container {{
            max-width: {MAX_WIDTH};
            padding-top: 1.4rem;
            padding-bottom: 2.5rem;
        }}

        h1, h2, h3, h4, h5 {{ color: {INK} !important; letter-spacing: 0 !important; }}
        p, span, label, div {{ letter-spacing: 0; }}

        .pj-titulo-pagina {{
            font-size: 28px; font-weight: 800; color: {INK}; margin: 0 0 2px 0;
        }}
        .pj-subtitulo-pagina {{ font-size: 14px; color: {SECONDARY}; margin: 0; }}
        .pj-titulo-secao {{
            font-size: 19px; font-weight: 700; color: {INK};
            margin: 28px 0 12px 0; padding-top: 4px;
        }}

        /* Cabeçalho compacto de página (MTA/TPJL) */
        .pj-cabecalho {{
            display: flex; justify-content: space-between; align-items: flex-start;
            gap: 16px; flex-wrap: wrap;
            padding: 14px 18px; margin-bottom: 18px;
            background: {PANEL}; border: 1px solid {LINE}; border-radius: 12px;
        }}
        .pj-cabecalho .pj-meta {{ font-size: 13px; color: {SECONDARY}; margin-top: 4px; }}
        .pj-cabecalho .pj-meta strong {{ color: {INK}; font-weight: 600; }}
        .pj-selo-filtro {{
            display: inline-block; padding: 3px 10px; border-radius: 999px;
            background: {PRIMARY_SOFT}; border: 1px solid rgba(244,166,42,0.35);
            color: {PRIMARY}; font-size: 12px; font-weight: 700; margin-top: 6px;
        }}
        .pj-cabecalho-status {{ text-align: right; font-size: 13px; color: {SECONDARY}; }}

        /* Selo de status genérico */
        .pj-selo {{
            display: inline-flex; align-items: center; gap: 5px;
            padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 700;
        }}

        /* Grade de indicadores — 4/2/1 colunas conforme a largura da tela */
        .grade-indicadores {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
            gap: 12px;
            margin-bottom: 6px;
        }}
        .cartao-indicador {{
            background: {PANEL}; border: 1px solid {LINE}; border-left: 3px solid var(--cor-indicador, {PRIMARY});
            border-radius: 10px; padding: 14px 16px;
        }}
        .cartao-indicador .ci-titulo {{
            font-size: 13px; color: {SECONDARY}; font-weight: 600; margin-bottom: 6px;
        }}
        .cartao-indicador .ci-valor {{
            font-size: 28px; font-weight: 800; color: {INK}; line-height: 1.15;
        }}
        .cartao-indicador .ci-auxiliar {{ font-size: 12.5px; color: {MUTED}; margin-top: 4px; }}

        /* Card de projeto (home) */
        .pj-card-projeto {{
            background: {PANEL}; border: 1px solid {LINE}; border-radius: 14px;
            padding: 20px 22px; height: 100%; display: flex; flex-direction: column;
            transition: border-color 0.15s ease, background 0.15s ease;
        }}
        .pj-card-projeto:hover {{ border-color: {PRIMARY}; background: {PANEL_HOVER}; }}
        .pj-card-projeto .pcp-nome {{ font-size: 20px; font-weight: 800; color: {INK}; }}
        .pj-card-projeto .pcp-desc {{ font-size: 13.5px; color: {SECONDARY}; margin: 2px 0 10px 0; }}

        /* Tabs — aba ativa com fundo laranja suave (pedido explícito) */
        button[data-baseweb="tab"] {{
            font-size: 14.5px !important; font-weight: 600 !important; color: {SECONDARY} !important;
            padding: 8px 16px !important; border-radius: 8px 8px 0 0 !important;
        }}
        button[data-baseweb="tab"][aria-selected="true"] {{
            background: {PRIMARY_SOFT} !important; color: {PRIMARY} !important;
            border-bottom: 2.5px solid {PRIMARY} !important;
        }}
        [data-baseweb="tab-highlight"] {{ background-color: {PRIMARY} !important; }}

        /* Métricas nativas do Streamlit — usadas só em contextos pontuais */
        [data-testid="stMetricValue"] {{ font-size: 26px !important; font-weight: 800 !important; color: {INK} !important; white-space: normal !important; overflow: visible !important; text-overflow: unset !important; }}
        [data-testid="stMetricLabel"] {{ font-size: 13px !important; color: {SECONDARY} !important; white-space: normal !important; overflow: visible !important; text-overflow: unset !important; }}
        [data-testid="stMetricDelta"] {{ font-size: 12.5px !important; }}

        div.stButton > button {{
            border-radius: 9px !important; font-weight: 700 !important;
            border: 1px solid rgba(244,166,42,0.55) !important;
            background: {PRIMARY_SOFT} !important; color: {PRIMARY} !important;
        }}
        div.stButton > button:hover {{
            background: {PRIMARY} !important; color: #0B1118 !important;
            border-color: {PRIMARY} !important;
            box-shadow: 0 0 22px rgba(244,166,42,0.30);
        }}

        [data-testid="stDataFrame"] {{ border: 1px solid {LINE}; border-radius: 10px; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def selo(texto, cor="neutro"):
    """HTML (string) de um selo colorido — sempre embutir dentro de outro
    st.markdown/f-string, nunca chamar st.markdown sozinho com isso (pra não
    fragmentar a div em várias chamadas, mesmo erro do </div> na tela)."""
    hexcor = STATUS.get(cor, MUTED) if cor not in ("primary",) else PRIMARY
    return (f'<span class="pj-selo" style="background:{hexcor}22;color:{hexcor};">'
            f'{texto}</span>')


def cartao_indicador(titulo, valor, auxiliar=None, cor="primary"):
    """Devolve o HTML de UM card — usar com grade_indicadores(), nunca
    sozinho (a grade toda vira uma única chamada st.markdown)."""
    hexcor = PRIMARY if cor == "primary" else STATUS.get(cor, PRIMARY)
    aux_html = f'<div class="ci-auxiliar">{auxiliar}</div>' if auxiliar else ""
    return (
        f'<div class="cartao-indicador" style="--cor-indicador:{hexcor};">'
        f'<div class="ci-titulo">{titulo}</div>'
        f'<div class="ci-valor">{valor}</div>'
        f'{aux_html}'
        f'</div>'
    )


def grade_indicadores(cards_html):
    st.markdown(f'<div class="grade-indicadores">{"".join(cards_html)}</div>', unsafe_allow_html=True)


def cabecalho_pagina(titulo, meta_esquerda, selo_filtro, status_html):
    """Cabeçalho compacto — título + fonte à esquerda, selo do filtro fixo,
    status de atualização à direita. Tudo numa única chamada st.markdown."""
    st.markdown(
        f"""<div class="pj-cabecalho">
            <div>
                <div class="pj-titulo-pagina" style="font-size:22px;">{titulo}</div>
                <div class="pj-meta">{meta_esquerda}</div>
                <div class="pj-selo-filtro">{selo_filtro}</div>
            </div>
            <div class="pj-cabecalho-status">{status_html}</div>
        </div>""",
        unsafe_allow_html=True,
    )
