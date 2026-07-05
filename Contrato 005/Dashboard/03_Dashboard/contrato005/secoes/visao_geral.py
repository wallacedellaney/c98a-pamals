"""Tela de Visão Geral — resumo das 3 áreas, com atalho para cada uma."""

import pandas as pd
import plotly.express as px
import streamlit as st

from contrato005.components.paleta import CATEGORICA, STATUS, layout_grafico


def _ir_para(pagina):
    st.session_state["pagina"] = pagina
    st.rerun()


def render(dados):

    df_emerg = dados["emergencias"]
    df_rep = dados["reparaveis"]
    df_pag = dados["pagamentos"]
    contrato = dados["contrato"]

    emerg_abertas = df_emerg[df_emerg["em_aberto"]]
    emerg_atrasadas = emerg_abertas[emerg_abertas["dias_atraso"] > 0]
    rep_abertas = df_rep[df_rep["em_aberto"]]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Reparáveis")
        st.metric("OS em aberto", len(rep_abertas))
        st.metric("Condenados", int((rep_abertas["condicao"].str.upper() == "CONDENADO").sum()))
        if st.button("Ver Reparáveis →", width="stretch"):
            _ir_para("Reparáveis")

    with col2:
        st.subheader("Emergências Abertas")
        st.metric("Total em aberto", len(emerg_abertas))
        st.metric("Atrasadas", len(emerg_atrasadas))
        if st.button("Ver Emergências →", width="stretch"):
            _ir_para("Emergências Abertas")

    with col3:
        st.subheader("Pagamentos")
        st.metric("Total faturado", f"R$ {df_pag['faturado'].sum():,.2f}")
        st.metric("Pendente", f"R$ {df_pag['pendente'].sum():,.2f}")
        if st.button("Ver Pagamentos →", width="stretch"):
            _ir_para("Pagamentos")

    st.divider()

    g1, g2, g3 = st.columns(3)

    with g1:
        st.caption("Reparáveis por condição")
        contagem = rep_abertas["condicao"].value_counts().reset_index()
        contagem.columns = ["condicao", "quantidade"]
        fig = px.bar(contagem, x="quantidade", y="condicao", orientation="h",
                     color_discrete_sequence=[CATEGORICA[0]])
        fig.update_layout(yaxis_title="", xaxis_title="", showlegend=False)
        layout_grafico(fig)
        st.plotly_chart(fig, width="stretch")

    with g2:
        st.caption("Emergências: no prazo x atrasadas")
        resumo = pd.DataFrame({
            "status": ["No prazo", "Atrasada"],
            "quantidade": [len(emerg_abertas) - len(emerg_atrasadas), len(emerg_atrasadas)],
        })
        fig = px.bar(resumo, x="status", y="quantidade",
                     color="status",
                     color_discrete_map={"No prazo": STATUS["good"], "Atrasada": STATUS["critical"]})
        fig.update_layout(xaxis_title="", yaxis_title="", showlegend=False)
        layout_grafico(fig)
        st.plotly_chart(fig, width="stretch")

    with g3:
        st.caption("Valor faturado por módulo")
        por_modulo = df_pag.groupby("modulo")["valor_nfs"].sum().reset_index()
        por_modulo["modulo"] = "Módulo " + por_modulo["modulo"].astype(int).astype(str)
        fig = px.bar(por_modulo, x="modulo", y="valor_nfs", color_discrete_sequence=[CATEGORICA[0]])
        fig.update_layout(xaxis_title="", yaxis_title="", showlegend=False)
        layout_grafico(fig)
        st.plotly_chart(fig, width="stretch")

    st.caption(f"Saldo do contrato a faturar: R$ {contrato['saldo_a_faturar']:,.2f}")
