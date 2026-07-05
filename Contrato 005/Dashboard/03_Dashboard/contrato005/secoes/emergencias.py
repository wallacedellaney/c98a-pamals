"""Tela de detalhe — Emergências Abertas."""

import pandas as pd
import plotly.express as px
import streamlit as st

from contrato005.components.paleta import AMBER, CATEGORICA, layout_grafico

TPEMG_PRIORIDADE = ("AIFP", "IPLR")  # prazo de 6 e 10 dias corridos (ver emergencias.md) — ANCE tem 30


def _destacar_prioridade(row):
    if row["tpemg"] in TPEMG_PRIORIDADE:
        return [f"background-color: {AMBER}22"] * len(row)
    return [""] * len(row)


def render(dados):
    st.title("Emergências Abertas")

    df = dados["emergencias"]
    df = df[df["em_aberto"]]

    col_f0, col_f1, col_f2, col_f3, col_f4 = st.columns(5)
    with col_f0:
        pns = st.multiselect("PN", sorted(df["pn"].dropna().unique()))
    with col_f1:
        aeronaves = st.multiselect("Aeronave (MATR)", sorted(df["matricula_aeronave"].dropna().unique()))
    with col_f2:
        situacoes = st.multiselect("Situação (ST_EMG)", sorted(df["situacao"].dropna().unique()))
    with col_f3:
        tpemgs = st.multiselect("TPEMG", sorted(df["tpemg"].dropna().unique()))
    with col_f4:
        so_atrasadas = st.checkbox("Mostrar só atrasadas")

    filtrado = df.copy()
    if pns:
        filtrado = filtrado[filtrado["pn"].isin(pns)]
    if aeronaves:
        filtrado = filtrado[filtrado["matricula_aeronave"].isin(aeronaves)]
    if situacoes:
        filtrado = filtrado[filtrado["situacao"].isin(situacoes)]
    if tpemgs:
        filtrado = filtrado[filtrado["tpemg"].isin(tpemgs)]
    if so_atrasadas:
        filtrado = filtrado[filtrado["dias_atraso"] > 0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Em aberto (após filtro)", len(filtrado))
    col2.metric("Atrasadas", int((filtrado["dias_atraso"] > 0).sum()))
    media_atraso = filtrado.loc[filtrado["dias_atraso"] > 0, "dias_atraso"].mean()
    col3.metric("Atraso médio (dias)", f"{media_atraso:.1f}" if pd.notna(media_atraso) else "—")
    col4.metric("Prioridade alta (AIFP/IPLR)", int(filtrado["tpemg"].isin(TPEMG_PRIORIDADE).sum()))

    st.caption("Linhas destacadas em âmbar: TPEMG = AIFP (prazo 6 dias) ou IPLR (prazo 10 dias) — prazo bem mais curto que ANCE (30 dias).")

    tabela = filtrado[[
        "numero_emergencia", "om", "matricula_aeronave", "pn", "nomenclatura",
        "situacao", "tpemg", "prazo_entrega", "dias_atraso", "dias_corridos",
    ]]
    st.dataframe(
        tabela.style.apply(_destacar_prioridade, axis=1),
        width="stretch",
        hide_index=True,
        height=420,
    )

    with st.expander("Distribuição por situação"):
        por_situacao = filtrado["situacao"].value_counts().reset_index()
        por_situacao.columns = ["situacao", "quantidade"]
        fig = px.bar(por_situacao, x="situacao", y="quantidade", color_discrete_sequence=[CATEGORICA[0]])
        fig.update_layout(xaxis_title="", yaxis_title="Quantidade", showlegend=False)
        layout_grafico(fig)
        st.plotly_chart(fig, width="stretch")
