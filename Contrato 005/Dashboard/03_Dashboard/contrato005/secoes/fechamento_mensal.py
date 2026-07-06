"""Página Fechamento Mensal — estrutura pronta (seletor de mês + as 2
subseções pedidas pelo Wallace), conteúdo ainda não definido.

Dividida em "Cômputo Mensal" e "Atrasos" — o Wallace vai dar instruções
específicas do que cada uma mostra. Não presumir métricas antes disso (ver
CLAUDE.md — não presumir escopo sem perguntar).
"""

import pandas as pd
import streamlit as st

MESES_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def _opcoes_mes(dados):
    """Todos os meses (ano-mês) presentes no histórico de emergências,
    começando por julho/2026 — se não houver dado ainda, usa só julho/2026."""
    df = dados.get("emergencias_totais")
    padrao = pd.Period("2026-07", freq="M")
    if df is None or df.empty or "data_abertura" not in df.columns:
        return [padrao]
    periodos = pd.to_datetime(df["data_abertura"].dropna()).dt.to_period("M").unique()
    meses = sorted(set(periodos) | {padrao})
    return meses


def _formatar_mes(periodo):
    return f"{MESES_PT[periodo.month - 1]}/{periodo.year}"


def render(dados):
    st.title("Fechamento Mensal")
    st.caption("Fechamento mensal do Contrato 005 — cômputo do mês e atrasos.")

    opcoes = _opcoes_mes(dados)
    padrao = pd.Period("2026-07", freq="M")
    indice_padrao = opcoes.index(padrao) if padrao in opcoes else len(opcoes) - 1

    mes_escolhido = st.selectbox(
        "Mês de referência",
        options=opcoes,
        index=indice_padrao,
        format_func=_formatar_mes,
        key="fecham_mes",
    )

    st.divider()
    aba_computo, aba_atrasos = st.tabs(["Cômputo Mensal", "Atrasos"])

    with aba_computo:
        st.subheader(f"Cômputo Mensal — {_formatar_mes(mes_escolhido)}")
        st.info("Ainda não construído — aguardando instruções do Wallace sobre o que exibir aqui.")

    with aba_atrasos:
        st.subheader(f"Atrasos — {_formatar_mes(mes_escolhido)}")
        st.info("Ainda não construído — aguardando instruções do Wallace sobre o que exibir aqui.")
