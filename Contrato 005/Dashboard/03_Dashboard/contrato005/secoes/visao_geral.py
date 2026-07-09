"""Tela de Visão Geral — resumo de todas as áreas do Contrato 005, com
atalho para cada uma. Atualizada em 2026-07-09 pra cobrir Empréstimos e
Fechamento Mensal, que não existiam quando essa tela foi criada.
"""

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from contrato005.components.paleta import AMBER, CATEGORICA, STATUS, layout_grafico
from contrato005.data.carregar_dados import carregar_computo_mensal


def _ir_para(pagina):
    st.session_state["pagina"] = pagina
    st.rerun()


def render(dados):

    df_emerg = dados["emergencias"]
    df_rep = dados["reparaveis"]
    df_pag = dados["pagamentos"]
    df_emp = dados.get("devolucoes")
    contrato = dados["contrato"]

    emerg_abertas = df_emerg[df_emerg["em_aberto"]]
    emerg_atrasadas = emerg_abertas[emerg_abertas["dias_atraso"] > 0]
    rep_abertas = df_rep[df_rep["em_aberto"]]

    hoje = date.today()
    _, _, resumo_computo = carregar_computo_mensal(hoje.year, hoje.month)

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.subheader("Reparáveis")
        st.metric("OS em aberto", len(rep_abertas))
        st.metric("Condenados", int((rep_abertas["condicao"].str.upper() == "CONDENADO").sum()))
        if st.button("Ver Reparáveis →", width="stretch", key="vg_ir_reparaveis"):
            _ir_para("Reparáveis")

    with col2:
        st.subheader("Emergências")
        st.metric("Em aberto", len(emerg_abertas))
        st.metric("Atrasadas", len(emerg_atrasadas))
        if st.button("Ver Abertas →", width="stretch", key="vg_ir_emerg_abertas"):
            _ir_para("Emergências Abertas")
        if st.button("Ver Totais →", width="stretch", key="vg_ir_emerg_totais"):
            _ir_para("Emergências Totais")

    with col3:
        st.subheader("Empréstimos")
        if df_emp is not None and not df_emp.empty:
            pendentes = int((df_emp["status"] == "Pendente").sum())
            st.metric("Pendentes", pendentes)
            st.metric("Total de itens", len(df_emp))
        else:
            st.metric("Pendentes", "—")
            st.metric("Total de itens", "—")
        if st.button("Ver Empréstimos →", width="stretch", key="vg_ir_emprestimos"):
            _ir_para("Empréstimos")

    with col4:
        st.subheader("Fechamento Mensal")
        if resumo_computo and resumo_computo.get("mmam_previa") is not None:
            st.metric("MMAM prévia (mês atual)", f"{resumo_computo['mmam_previa']}%")
            st.metric("Dias calculados", f"{resumo_computo['ultimo_dia_calculado']} de {resumo_computo['ultimo_dia_mes']}")
        else:
            st.metric("MMAM prévia (mês atual)", "—")
            st.metric("Dias calculados", "—")
        if st.button("Ver Fechamento →", width="stretch", key="vg_ir_fechamento"):
            _ir_para("Fechamento Mensal")

    with col5:
        st.subheader("Pagamentos")
        st.metric("Total faturado", f"R$ {df_pag['faturado'].sum():,.2f}")
        st.metric("Pendente", f"R$ {df_pag['pendente'].sum():,.2f}")
        if st.button("Ver Pagamentos →", width="stretch", key="vg_ir_pagamentos"):
            _ir_para("Pagamentos")

    st.divider()

    g1, g2, g3, g4 = st.columns(4)

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
        st.caption("Empréstimos: status")
        if df_emp is not None and not df_emp.empty:
            contagem_emp = df_emp["status"].value_counts().reset_index()
            contagem_emp.columns = ["status", "quantidade"]
            fig = px.pie(
                contagem_emp, names="status", values="quantidade", hole=0.55,
                color="status", color_discrete_map={"Pendente": STATUS["critical"], "OK": STATUS["good"]},
            )
            fig.update_traces(textinfo="value+percent", textfont_size=11)
            layout_grafico(fig)
            st.plotly_chart(fig, width="stretch")
        else:
            st.caption("Sem dados ainda.")

    with g4:
        st.caption("Valor faturado por módulo")
        por_modulo = df_pag.groupby("modulo")["valor_nfs"].sum().reset_index()
        por_modulo["modulo"] = "Módulo " + por_modulo["modulo"].astype(int).astype(str)
        fig = px.bar(por_modulo, x="modulo", y="valor_nfs", color_discrete_sequence=[CATEGORICA[0]])
        fig.update_layout(xaxis_title="", yaxis_title="", showlegend=False)
        layout_grafico(fig)
        st.plotly_chart(fig, width="stretch")

    st.caption(f"Saldo do contrato a faturar: R$ {contrato['saldo_a_faturar']:,.2f}")
