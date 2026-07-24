"""Tela de Visão Geral — resumo de todas as áreas do Contrato 005, com
atalho para cada uma. Reorganizada em 2026-07-09 em 2 grupos (Operacional
e Financeiro/Fechamento) em vez de espremer tudo numa linha só — Operacional
é o que muda dia a dia (Emergências, Reparáveis, Empréstimos); Financeiro é
mais periódico (Pagamentos, Fechamento Mensal).
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from shared import horario
from contrato005.components import data_global
from contrato005.components.paleta import CATEGORICA, STATUS, layout_grafico
from contrato005.components.utils import formatar_moeda
from contrato005.data.carregar_dados import carregar_computo_mensal


def _ir_para(pagina):
    st.session_state["pagina"] = pagina
    st.rerun()


def render(dados):
    data_global.mostrar_nota_historica_se_necessario(dados)

    df_emerg = dados["emergencias"]
    df_rep = dados["reparaveis"]
    df_pag = dados["pagamentos"]
    df_emp = dados.get("devolucoes")
    contrato = dados["contrato"]

    emerg_abertas = df_emerg[df_emerg["em_aberto"]]
    emerg_atrasadas = emerg_abertas[emerg_abertas["dias_atraso"] > 0]
    rep_abertas = df_rep[df_rep["em_aberto"]]

    hoje = horario.hoje_br()
    _, _, resumo_computo = carregar_computo_mensal(hoje.year, hoje.month)

    st.markdown("##### Operacional")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Emergências")
        st.metric("Em aberto", len(emerg_abertas))
        st.metric("Atrasadas", len(emerg_atrasadas))
        cb1, cb2 = st.columns(2)
        with cb1:
            if st.button("Abertas →", width="stretch", key="vg_ir_emerg_abertas"):
                _ir_para("Emergências Abertas")
        with cb2:
            if st.button("Totais →", width="stretch", key="vg_ir_emerg_totais"):
                _ir_para("Emergências Totais")

    with col2:
        st.subheader("Reparáveis")
        st.metric("OS em aberto", len(rep_abertas))
        st.metric("Condenados", int((rep_abertas["condicao"].str.upper() == "CONDENADO").sum()))
        if st.button("Ver Reparáveis →", width="stretch", key="vg_ir_reparaveis"):
            _ir_para("Reparáveis")

    with col3:
        st.subheader("Empréstimos")
        if df_emp is not None and not df_emp.empty:
            pendentes = int((df_emp["status"] == "Pendente").sum())
            total_qtd = df_emp["quantidade"].fillna(1).sum()
            st.metric("Pendentes", pendentes)
            st.metric("Total de itens (linhas)", len(df_emp))
            st.metric("Total de quantidade", f"{total_qtd:,.0f}".replace(",", "."))
        else:
            st.metric("Pendentes", "—")
            st.metric("Total de itens (linhas)", "—")
            st.metric("Total de quantidade", "—")
        if st.button("Ver Empréstimos →", width="stretch", key="vg_ir_emprestimos"):
            _ir_para("Empréstimos")

    g1, g2, g3 = st.columns(3)
    with g1:
        st.caption("Emergências: no prazo x atrasadas")
        resumo = pd.DataFrame({
            "status": ["No prazo", "Atrasada"],
            "quantidade": [len(emerg_abertas) - len(emerg_atrasadas), len(emerg_atrasadas)],
        })
        fig = px.bar(resumo, x="status", y="quantidade",
                     color="status",
                     color_discrete_map={"No prazo": STATUS["good"], "Atrasada": STATUS["critical"]})
        fig.update_layout(xaxis_title="", yaxis_title="", showlegend=False)
        layout_grafico(fig, altura=200)
        st.plotly_chart(fig, width="stretch")

    with g2:
        st.caption("Reparáveis por condição")
        contagem = rep_abertas["condicao"].value_counts().reset_index()
        contagem.columns = ["condicao", "quantidade"]
        fig = px.bar(contagem, x="quantidade", y="condicao", orientation="h",
                     color_discrete_sequence=[CATEGORICA[0]])
        fig.update_layout(yaxis_title="", xaxis_title="", showlegend=False)
        layout_grafico(fig, altura=200)
        st.plotly_chart(fig, width="stretch")

    with g3:
        st.caption("Empréstimos: status (por quantidade)")
        if df_emp is not None and not df_emp.empty:
            df_emp_qtd = df_emp.copy()
            df_emp_qtd["quantidade_efetiva"] = df_emp_qtd["quantidade"].fillna(1)
            contagem_emp = df_emp_qtd.groupby("status")["quantidade_efetiva"].sum().reset_index()
            contagem_emp.columns = ["status", "quantidade"]
            fig = px.pie(
                contagem_emp, names="status", values="quantidade", hole=0.55,
                color="status", color_discrete_map={"Pendente": STATUS["critical"], "OK": STATUS["good"]},
            )
            fig.update_traces(textinfo="value+percent", textfont_size=11)
            layout_grafico(fig, altura=200)
            st.plotly_chart(fig, width="stretch")
        else:
            st.caption("Sem dados ainda.")

    st.divider()
    st.markdown("##### Financeiro e Fechamento")
    col4, col5, col6 = st.columns(3)

    with col4:
        st.subheader("Pagamentos")
        pc1, pc2 = st.columns(2)
        with pc1:
            st.metric("Total faturado", formatar_moeda(df_pag['faturado'].sum()))
        with pc2:
            st.metric("Pendente", formatar_moeda(df_pag['pendente'].sum()))
        st.caption(f"Saldo do contrato a faturar: {formatar_moeda(contrato['saldo_a_faturar'])}")
        if st.button("Ver Pagamentos →", width="stretch", key="vg_ir_pagamentos"):
            _ir_para("Pagamentos")

        por_modulo = df_pag.groupby("modulo")["valor_nfs"].sum().reset_index()
        por_modulo["modulo"] = "Módulo " + por_modulo["modulo"].astype(int).astype(str)
        fig = px.bar(por_modulo, x="modulo", y="valor_nfs", color_discrete_sequence=[CATEGORICA[0]])
        fig.update_layout(xaxis_title="", yaxis_title="", showlegend=False)
        layout_grafico(fig, altura=200)
        st.plotly_chart(fig, width="stretch")

    with col5:
        st.subheader("Fechamento Mensal")
        if resumo_computo and resumo_computo.get("mmam_previa") is not None:
            fc1, fc2 = st.columns(2)
            with fc1:
                st.metric("MMAM prévia (mês atual)", f"{resumo_computo['mmam_previa']}%")
            with fc2:
                st.metric("Dias calculados", f"{resumo_computo['ultimo_dia_calculado']} de {resumo_computo['ultimo_dia_mes']}")
        else:
            st.metric("MMAM prévia (mês atual)", "—")
        st.caption("Cômputo Mensal — prévia automática da matriz de aeronaves montadas (Pré-RMA).")
        if st.button("Ver Fechamento →", width="stretch", key="vg_ir_fechamento"):
            _ir_para("Fechamento Mensal")

    with col6:
        st.subheader("Reajuste")
        ind_reajuste = dados.get("reajuste_indicadores")
        if ind_reajuste is not None and not ind_reajuste.empty:
            v_1 = ind_reajuste.loc[ind_reajuste["indicador"] == "Valor do Contrato após 1° Reajuste", "valor"]
            v_2 = ind_reajuste.loc[ind_reajuste["indicador"] == "Valor do Contrato após 2° Reajuste", "valor"]
            st.metric("Valor do contrato (após 1° Reajuste)", formatar_moeda(v_1.iloc[0]) if len(v_1) else "—")
            st.caption(f"Após 2° Reajuste (projeção): {formatar_moeda(v_2.iloc[0])}" if len(v_2) else "—")
        else:
            st.metric("Valor do contrato (após reajuste)", "—")
        if st.button("Ver Reajuste →", width="stretch", key="vg_ir_reajuste"):
            _ir_para("Reajuste")
