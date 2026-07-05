"""Página Previsão Mensal — ainda não construída.

Menu e identidade visual já preparados; falta definir a fonte de dados junto
com o Wallace antes de implementar (ver CLAUDE.md — não presumir escopo).
"""

import streamlit as st


def render(dados):
    st.title("Previsão Mensal")
    st.caption(
        "Indicadores no topo, filtros por mês/aeronave/unidade, calendário ou linha "
        "do tempo, tabela de previsões, alertas de vencimento e eventos para os "
        "próximos 30/60/90 dias."
    )
    st.info("Ainda não construída — vamos definir a fonte de dados juntos quando chegar a vez.")
