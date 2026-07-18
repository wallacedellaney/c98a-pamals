"""Tela de detalhe — Pagamentos."""

import pandas as pd
import plotly.express as px
import streamlit as st

from contrato005.components import data_global
from contrato005.components.paleta import CATEGORICA, layout_grafico
from contrato005.components.utils import formatar_moeda, ordenar_unicos

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
    if data_global.mostrar_snapshot_se_necessario(dados, "pagamentos"):
        return

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
    r1.metric(f"Valor das NFs — Módulo {st.session_state['modulo_resumo']}", formatar_moeda(modulo_atual['valor_nfs'].sum()))
    r2.metric("Faturado", formatar_moeda(modulo_atual['faturado'].sum()))
    r3.metric("Pendente", formatar_moeda(modulo_atual['pendente'].sum()))

    st.divider()

    # --- Filtros e visão geral do contrato ---
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        modulos = st.multiselect("Módulo", ordenar_unicos(df["modulo"].dropna().astype(int)))
    with col_f2:
        situacoes = st.multiselect("Situação", ordenar_unicos(df["situacao"]))
    with col_f3:
        referencias = st.multiselect("Referência", ordenar_unicos(df["referencia"]))
    with col_f4:
        notas = st.multiselect("Nº Nota Fiscal", ordenar_unicos(df["numero_nota_fiscal"]))

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
    col1.metric("Faturado (filtro)", formatar_moeda(filtrado['faturado'].sum()))
    col2.metric("Pendente (filtro)", formatar_moeda(filtrado['pendente'].sum()))
    col3.metric("Valor total do contrato", formatar_moeda(contrato['valor_total_contrato']))
    col4.metric("Saldo a faturar", formatar_moeda(contrato['saldo_a_faturar']))

    # Empenho é detalhe interno de execução orçamentária — escondido no
    # deploy externo "005CELOG2025" (pedido do Wallace: "tira empenho do
    # pagamento tb, ela nao precis saber").
    modo_externo = dados.get("modo_externo", False)
    colunas_tabela = [
        "modulo", "referencia", "numero_nota_fiscal", "data", "valor_nfs",
        "faturado", "pendente", "situacao",
    ]
    if not modo_externo:
        colunas_tabela.append("empenho_responsavel")

    st.dataframe(
        filtrado[colunas_tabela],
        width="stretch",
        hide_index=True,
        height=420,
    )

    if not modo_externo:
        with st.expander("Empenhos"):
            ef1, ef2 = st.columns(2)
            with ef1:
                nes = st.multiselect("Nº Empenho (NE)", ordenar_unicos(empenhos["numero_empenho"]))
            with ef2:
                responsaveis = st.multiselect("Responsável", ordenar_unicos(empenhos["responsavel"]))

            empenhos_filtrados = empenhos.copy()
            if nes:
                empenhos_filtrados = empenhos_filtrados[empenhos_filtrados["numero_empenho"].isin(nes)]
            if responsaveis:
                empenhos_filtrados = empenhos_filtrados[empenhos_filtrados["responsavel"].isin(responsaveis)]

            e1, e2 = st.columns(2)
            e1.metric("Valor empenhado (total)", formatar_moeda(empenhos_filtrados['valor_empenhado'].sum()))
            e2.metric("Saldo (total)", formatar_moeda(empenhos_filtrados['saldo'].sum()))
            st.dataframe(empenhos_filtrados, width="stretch", hide_index=True, height=360)

    with st.expander("Evolução mensal do faturamento", expanded=True):
        evolucao = filtrado[filtrado["tipo_registro"] == "mensal"][["referencia", "data", "valor_nfs"]].copy()
        evolucao["chave"] = evolucao.apply(_chave_cronologica, axis=1)
        evolucao = evolucao.sort_values("chave")

        fig = px.line(evolucao, x="referencia", y="valor_nfs", markers=True,
                      color_discrete_sequence=[CATEGORICA[0]],
                      category_orders={"referencia": evolucao["referencia"].tolist()})
        fig.update_traces(hovertemplate="%{x}<br>R$ %{y:,.2f}<extra></extra>")
        # separators=",." troca o padrão americano (1,234.56) pro brasileiro
        # (1.234,56) em todo o gráfico (eixo e hover) — achado pelo Wallace em
        # 2026-07-18: "40,817... parece que e 40 reais" (lido à brasileira, a
        # vírgula do formato americano parece separador decimal).
        fig.update_layout(xaxis_title="", yaxis_title="Valor faturado (R$)", separators=",.")
        fig.update_xaxes(tickangle=-45)
        fig.update_yaxes(tickprefix="R$ ", tickformat=",.0f")
        layout_grafico(fig, altura=300)
        st.plotly_chart(fig, width="stretch")
