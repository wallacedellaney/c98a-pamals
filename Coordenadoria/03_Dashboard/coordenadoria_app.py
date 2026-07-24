"""
Entrada da área Coordenadoria — 3 partes navegáveis por botões na parte de
baixo da tela: Dashboard, RAC, Previsão Mensal.

Identidade visual "Torre de Controle" — igual ao Contrato 005, ver
Contrato 005/Dashboard/00_Instrucoes/00_BRAND/identidade_visual.md.

Exposto como função `render()` para poder ser embutido dentro da página
principal "C-98A PAMALS" (ver ../../app.py), com um botão de voltar.
"""

from datetime import datetime

import streamlit as st

from coordenadoria.components.fontes_dados import secao_fontes_dados
from coordenadoria.components.paleta import AMBER, SECONDARY, LINE, PANEL, STATUS, INK
from coordenadoria.data.carregar_dados import carregar_tudo
from coordenadoria.secoes import dashboard_geral, rac, disponibilidade_diaria, diagonal_manutencao, vencimentos, motores, previsao_mensal
from coordenadoria.utils import atualizar_dados_rac, garantir_disponibilidade_atualizada

PAGINAS = {
    "Dashboard": dashboard_geral,
    "RAC": rac,
    "Disponibilidade Diária": disponibilidade_diaria,
    "Diagonal de Manutenção": diagonal_manutencao,
    "Vencimentos": vencimentos,
    "Motores": motores,
    "Previsão Mensal": previsao_mensal,
}


def render(ao_voltar=None):
    if "coord_pagina" not in st.session_state:
        st.session_state["coord_pagina"] = "Dashboard"

    # Antes de carregar qualquer dado — garante que a Disponibilidade Diária
    # está em dia (busca no Drive na hora se hoje ainda não tiver relatório
    # salvo), pra QUALQUER página da Coordenadoria já usar dado fresco (não
    # só a própria tela de Disponibilidade Diária). Ver docstring da função.
    status_disponibilidade = garantir_disponibilidade_atualizada()
    dados = carregar_tudo()
    dados["disp_status_atualizacao"] = status_disponibilidade

    st.markdown(
        f"""<style>
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
    font-size: 0.62rem; font-weight: 700; color: {AMBER};
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
[data-testid="stMetricValue"] {{
    font-size: 2rem !important;
    font-weight: 700 !important;
    color: {INK} !important;
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
.coord-card {{
    background: {PANEL};
    border: 1px solid {LINE};
    border-radius: 6px;
    padding: 0.9rem 1rem;
    margin-bottom: 0.8rem;
}}
.coord-card.borda-critica {{ border-left: 3px solid {STATUS['critical']}; }}
.coord-card.borda-atencao {{ border-left: 3px solid {AMBER}; }}
.coord-card.borda-ok {{ border-left: 3px solid {STATUS['good']}; }}
.coord-selo {{
    display: inline-block;
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    padding: 0.12rem 0.45rem;
    border-radius: 3px;
    text-transform: uppercase;
}}
.coord-selo.fora-contrato {{ background: {STATUS['critical']}22; color: {STATUS['critical']}; }}
</style>
<div class="c98-header"><div class="brand"><div class="mark">CO</div><div class="name">COORDENADORIA<small>C-98A PAMALS</small></div></div><div class="clock">HOJE {datetime.now().strftime('%d/%m/%Y')}</div></div>""",
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
                atualizar_dados_rac()
            st.rerun()

    PAGINAS[st.session_state["coord_pagina"]].render(dados)

    st.markdown('<div class="c98-nav"></div>', unsafe_allow_html=True)
    nav_cols = st.columns(len(PAGINAS))
    for col, nome in zip(nav_cols, PAGINAS):
        with col:
            ativo = nome == st.session_state["coord_pagina"]
            if st.button(nome, key=f"coord_nav_{nome}", width="stretch",
                         type="primary" if ativo else "secondary"):
                st.session_state["coord_pagina"] = nome
                st.session_state["rac_aeronave_selecionada"] = None
                st.session_state["venc_area"] = None
                st.rerun()

    st.caption(f"Dados atualizados em {datetime.fromtimestamp(dados['atualizado_em']).strftime('%d/%m/%Y %H:%M')}")

    secao_fontes_dados(dados)
