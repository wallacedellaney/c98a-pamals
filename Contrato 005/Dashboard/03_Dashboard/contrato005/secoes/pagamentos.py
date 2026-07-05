"""Tela de detalhe — Pagamentos."""

import pandas as pd
import plotly.express as px
import streamlit as st

from contrato005.components.paleta import CATEGORICA, layout_grafico

MODULOS = [1, 2, 3]

MESES = {
    "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "MAIO": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12,
}


def _chave_cronologica(row):
    """'FEV/25' -> (2025, 2). Referências sem mês (ex.: REAJUSTE) usam a data da linha."""
    referencia = str(row["referencia"])
    if "/" in referencia:
        mes_str, ano_str = referencia.split("/")
        mes = MESES.get(mes_str.upper())
        if mes and ano_str.isdigit():
            return (2000 + int(ano_str), mes)
    if pd.notna(row["data"]):
        return (row["data"].year, row["data"].month)
    return (9999, 99)


def render(dados):
    st.title("Pagamentos")

    df = dados["pagamentos"]
    contrato = dados["contrato"]
    empenhos = dados["empenhos"]

    # --- Resumo rápido por módulo (clicável) ---
    if "modulo_resumo" not in st.session_state:
        st.session_state["modulo_resumo"] = 1

    st.caption("Resumo rápido por módulo")
    mcols = st.columns(3)
    for col, m in zip(mcols, MODULOS):
        with col:
            ativo = st.session_state["modulo_resumo"] == m
            if st.button(f"Módulo {m}", key=f"modulo_{m}", width="stretch",
                         type="primary" if ativo else "secondary"):
                st.session_state["modulo_resumo"] = m
                st.rerun()

    modulo_atual = df[df["modulo"] == st.session_state["modulo_resumo"]]
    r1, r2, r3 = st.columns(3)
    r1.metric(f"Valor das NFs — Módulo {st.session_state['modulo_resumo']}", f"R$ {modulo_atual['valor_nfs'].sum():,.2f}")
    r2.metric("Faturado", f"R$ {modulo_atual['faturado'].sum():,.2f}")
    r3.metric("Pendente", f"R$ {modulo_atual['pendente'].sum():,.2f}")

    st.divider()

    # --- Filtros e visão geral do contrato ---
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        modulos = st.multiselect("Módulo", sorted(df["modulo"].dropna().unique().astype(int)))
    with col_f2:
        situacoes = st.multiselect("Situação", sorted(df["situacao"].dropna().unique()))
    with col_f3:
        referencias = st.multiselect("Referência", sorted(df["referencia"].dropna().unique()))
    with col_f4:
        notas = st.multiselect("Nº Nota Fiscal", sorted(df["numero_nota_fiscal"].dropna().unique()))

    filtrado = df.copy()
    if modulos:
        filtrado = filtrado[filtrado["modulo"].isin(modulos)]
    if situacoes:
        filtrado = filtrado[filtrado["situacao"].isin(situacoes)]
    if referencias:
        filtrado = filtrado[filtrado["referencia"].isin(referencias)]
    if notas:
        filtrado = filtrado[filtrado["numero_nota_fiscal"].isin(notas)]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Faturado (filtro)", f"R$ {filtrado['faturado'].sum():,.2f}")
    col2.metric("Pendente (filtro)", f"R$ {filtrado['pendente'].sum():,.2f}")
    col3.metric("Valor total do contrato", f"R$ {contrato['valor_total_contrato']:,.2f}")
    col4.metric("Saldo a faturar", f"R$ {contrato['saldo_a_faturar']:,.2f}")

    st.dataframe(
        filtrado[[
            "modulo", "referencia", "numero_nota_fiscal", "data", "valor_nfs",
            "faturado", "pendente", "situacao", "empenho_responsavel",
        ]],
        width="stretch",
        hide_index=True,
        height=420,
    )

    with st.expander("Empenhos"):
        ef1, ef2 = st.columns(2)
        with ef1:
            nes = st.multiselect("Nº Empenho (NE)", sorted(empenhos["numero_empenho"].dropna().unique()))
        with ef2:
            responsaveis = st.multiselect("Responsável", sorted(empenhos["responsavel"].dropna().unique()))

        empenhos_filtrados = empenhos.copy()
        if nes:
            empenhos_filtrados = empenhos_filtrados[empenhos_filtrados["numero_empenho"].isin(nes)]
        if responsaveis:
            empenhos_filtrados = empenhos_filtrados[empenhos_filtrados["responsavel"].isin(responsaveis)]

        e1, e2 = st.columns(2)
        e1.metric("Valor empenhado (total)", f"R$ {empenhos_filtrados['valor_empenhado'].sum():,.2f}")
        e2.metric("Saldo (total)", f"R$ {empenhos_filtrados['saldo'].sum():,.2f}")
        st.dataframe(empenhos_filtrados, width="stretch", hide_index=True, height=360)

    with st.expander("Evolução mensal do faturamento", expanded=True):
        evolucao = filtrado[filtrado["tipo_registro"] == "mensal"][["referencia", "data", "valor_nfs"]].copy()
        evolucao["chave"] = evolucao.apply(_chave_cronologica, axis=1)
        evolucao = evolucao.sort_values("chave")

        fig = px.line(evolucao, x="referencia", y="valor_nfs", markers=True,
                      color_discrete_sequence=[CATEGORICA[0]],
                      category_orders={"referencia": evolucao["referencia"].tolist()})
        fig.update_traces(hovertemplate="%{x}<br>R$ %{y:,.2f}<extra></extra>")
        fig.update_layout(xaxis_title="", yaxis_title="Valor faturado (R$)")
        fig.update_xaxes(tickangle=-45)
        fig.update_yaxes(tickprefix="R$ ", tickformat=",.0f")
        layout_grafico(fig, altura=300)
        st.plotly_chart(fig, width="stretch")
