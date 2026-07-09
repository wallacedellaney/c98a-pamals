"""
Dashboard interativo do Contrato 005 — 4 partes navegáveis por botões na parte
de baixo da tela: Visão Geral, Reparáveis, Emergências Abertas, Pagamentos.

Lê somente arquivos de 02_Dados_Tratados/ (ver 00_Instrucoes/dashboard.md).
Identidade visual "Torre de Controle" — ver 00_Instrucoes/00_BRAND/identidade_visual.md.

Exposto como função `render()` para poder ser embutido dentro da página principal
"C-98A PAMALS" (ver ../../../app.py), com um botão de voltar para o menu.
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

from contrato005.components.paleta import AMBER, SECONDARY, LINE
from contrato005.data.carregar_dados import carregar_tudo
from contrato005.secoes import (
    visao_geral, reparaveis, emergencias, emergencias_totais,
    fechamento_mensal, emprestimos, pagamentos,
)

PAGINAS = {
    "Visão Geral": visao_geral,
    "Reparáveis": reparaveis,
    "Emergências Abertas": emergencias,
    "Emergências Totais": emergencias_totais,
    "Fechamento Mensal": fechamento_mensal,
    "Empréstimos": emprestimos,
    "Pagamentos": pagamentos,
}

DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_GERAR_DADOS = DASHBOARD_ROOT / "05_Scripts" / "python" / "gerar_dados_tratados.py"


def _atualizar_dados():
    """Roda de novo a extração a partir do que já está em 01_Bases_Originais/
    (não busca nada novo do Google Drive — isso é feito pelo Claude, sob
    pedido ou por agenda — ver CLAUDE.md)."""
    resultado = subprocess.run(
        [sys.executable, str(SCRIPT_GERAR_DADOS)],
        cwd=str(SCRIPT_GERAR_DADOS.parent),
        capture_output=True,
        text=True,
    )
    st.cache_data.clear()
    if resultado.returncode == 0:
        st.toast("Dados atualizados a partir de 01_Bases_Originais/.", icon="✅")
    else:
        st.error(f"Erro ao atualizar dados:\n\n{resultado.stderr or resultado.stdout}")


def render(ao_voltar=None):
    if "pagina" not in st.session_state:
        st.session_state["pagina"] = "Visão Geral"

    dados = carregar_tudo()

    st.markdown(
        f"""
        <style>
        .c98-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 0.9rem;
            margin-bottom: 1.3rem;
            border-bottom: 1px solid {LINE};
        }}
        .c98-header .brand {{ display: flex; align-items: center; gap: 0.7rem; }}
        .c98-header .mark {{
            width: 2rem; height: 2rem;
            border: 1.5px solid {AMBER};
            border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-size: 0.72rem; font-weight: 700; color: {AMBER};
        }}
        .c98-header .name {{ font-size: 0.95rem; font-weight: 600; letter-spacing: 0.03em; }}
        .c98-header .name small {{
            display: block; font-size: 0.68rem; color: {SECONDARY};
            letter-spacing: 0.08em; font-weight: 400; margin-top: 0.15rem;
        }}
        .c98-header .clock {{ font-size: 0.78rem; color: {SECONDARY}; letter-spacing: 0.03em; }}

        h1 {{
            font-size: 1rem !important;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            font-weight: 600 !important;
            color: {SECONDARY} !important;
        }}

        /* Os dados (números/tabelas) são o protagonista — os gráficos só apoiam. */
        [data-testid="stMetricValue"] {{
            font-size: 2rem !important;
            font-weight: 700 !important;
            color: {AMBER} !important;
        }}
        [data-testid="stMetricLabel"] {{
            font-size: 0.72rem !important;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: {SECONDARY} !important;
        }}

        .c98-nav {{
            margin-top: 2rem;
            padding-top: 0.8rem;
            border-top: 1px solid {LINE};
        }}
        </style>

        <div class="c98-header">
            <div class="brand">
                <div class="mark">98</div>
                <div class="name">C-98 / OPS<small>CONTRATO 005 · CELOG-PAMALS · VEE ONE</small></div>
            </div>
            <div class="clock">HOJE {datetime.now().strftime('%d/%m/%Y')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_voltar, col_atualizar = st.columns([4, 1])
    with col_voltar:
        if ao_voltar is not None:
            if st.button("← Voltar ao menu"):
                ao_voltar()
                st.rerun()
    with col_atualizar:
        if st.button("🔄 Atualizar dados", width="stretch"):
            with st.spinner("Atualizando..."):
                _atualizar_dados()
            st.rerun()

    PAGINAS[st.session_state["pagina"]].render(dados)

    st.markdown('<div class="c98-nav"></div>', unsafe_allow_html=True)
    nav_cols = st.columns(len(PAGINAS))
    for col, nome in zip(nav_cols, PAGINAS):
        with col:
            ativo = nome == st.session_state["pagina"]
            if st.button(nome, key=f"nav_{nome}", width="stretch",
                         type="primary" if ativo else "secondary"):
                st.session_state["pagina"] = nome
                st.rerun()

    st.caption(f"Dados atualizados em {datetime.fromtimestamp(dados['atualizado_em']).strftime('%d/%m/%Y %H:%M')}")
