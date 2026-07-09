"""Tela "Empréstimos" — material emprestado/retirado de estoque e o que
falta devolver, a partir da planilha "Devoluções". Ver
00_Instrucoes/emprestimos.md.
"""

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from contrato005.components.paleta import AMBER, CATEGORICA, STATUS, layout_grafico


def _linha_mensal(df, coluna_data, cor):
    serie = df.dropna(subset=[coluna_data]).copy()
    if serie.empty:
        st.info("Sem datas registradas ainda.")
        return
    serie["mes"] = pd.to_datetime(serie[coluna_data]).dt.to_period("M").astype(str)
    contagem = serie.groupby("mes").size().reset_index(name="quantidade").sort_values("mes")
    fig = px.line(contagem, x="mes", y="quantidade", markers=True, color_discrete_sequence=[cor])
    fig.update_layout(xaxis_title="", yaxis_title="Itens")
    layout_grafico(fig, altura=230)
    st.plotly_chart(fig, width="stretch")


def render(dados):
    st.title("Empréstimos")
    st.caption(
        "Material retirado do estoque/emprestado e pendente de devolução — fonte: planilha \"Devoluções\". "
        "Ver 00_Instrucoes/emprestimos.md."
    )

    df = dados.get("devolucoes")
    if df is None or df.empty:
        st.info("Ainda não foi carregado — ver 00_Instrucoes/emprestimos.md pra buscar do Drive.")
        return

    atualizado_em = dados.get("devolucoes_atualizado_em")
    if atualizado_em:
        st.caption(f"Última atualização: **{datetime.fromtimestamp(atualizado_em).strftime('%d/%m/%Y %H:%M')}**")

    total = len(df)
    pendentes = int((df["status"] == "Pendente").sum())
    ok = int((df["status"] == "OK").sum())
    pct_ok = round(100 * ok / total) if total else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total de itens", total)
    c2.metric("Pendentes", pendentes, delta_color="inverse")
    c3.metric("OK (devolvidos)", ok)
    c4.metric("% concluído", f"{pct_ok}%")

    st.write("")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption("Status")
        contagem = df["status"].value_counts().reset_index()
        contagem.columns = ["status", "quantidade"]
        fig = px.pie(
            contagem, names="status", values="quantidade", hole=0.55,
            color="status", color_discrete_map={"Pendente": STATUS["critical"], "OK": STATUS["good"]},
        )
        fig.update_traces(textinfo="value+percent", textfont_size=11)
        layout_grafico(fig, altura=230)
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.caption("Por categoria (C/T/R)")
        cat = df["categoria"].value_counts().reset_index()
        cat.columns = ["categoria", "quantidade"]
        fig = px.bar(cat, x="categoria", y="quantidade", color_discrete_sequence=[CATEGORICA[0]])
        fig.update_layout(xaxis_title="", yaxis_title="")
        layout_grafico(fig, altura=230)
        st.plotly_chart(fig, width="stretch")

    with col3:
        st.caption("Top unidades (destino)")
        destino = df["destino"].value_counts().head(8).reset_index()
        destino.columns = ["destino", "quantidade"]
        fig = px.bar(destino, x="quantidade", y="destino", orientation="h", color_discrete_sequence=[CATEGORICA[1]])
        fig.update_layout(
            xaxis_title="", yaxis_title="",
            yaxis={"categoryorder": "total ascending", "type": "category"},
        )
        layout_grafico(fig, altura=230)
        st.plotly_chart(fig, width="stretch")

    st.divider()
    st.markdown("##### Evolução mensal")
    col_emp, col_dev = st.columns(2)
    with col_emp:
        st.caption("Empréstimos por mês (data do pedido de envio)")
        _linha_mensal(df, "pedido_envio", AMBER)
    with col_dev:
        st.caption("Devoluções por mês (data de devolução)")
        _linha_mensal(df, "data_devolucao", STATUS["good"])

    st.divider()
    st.markdown("##### Todos os itens")

    c1, c2, c3, c4 = st.columns([1, 1, 1, 1.4])
    with c1:
        status_f = st.selectbox("Status", ["Todos", "Pendente", "OK"], key="emp_f_status")
    with c2:
        categorias_f = st.multiselect("Categoria", sorted(df["categoria"].dropna().unique()), key="emp_f_categoria")
    with c3:
        destinos_f = st.multiselect("Destino", sorted(df["destino"].dropna().unique()), key="emp_f_destino")
    with c4:
        busca = st.text_input("🔎 Busca (PN, descrição, aeronave)", key="emp_f_busca")

    filtrado = df.copy()
    if status_f != "Todos":
        filtrado = filtrado[filtrado["status"] == status_f]
    if categorias_f:
        filtrado = filtrado[filtrado["categoria"].isin(categorias_f)]
    if destinos_f:
        filtrado = filtrado[filtrado["destino"].isin(destinos_f)]
    if busca:
        b = busca.strip().lower()
        filtrado = filtrado[
            filtrado["part_number"].astype(str).str.lower().str.contains(b, na=False)
            | filtrado["descricao"].astype(str).str.lower().str.contains(b, na=False)
            | filtrado["anv"].astype(str).str.lower().str.contains(b, na=False)
        ]

    colunas_tabela = [
        "numero_ordem", "part_number", "descricao", "categoria", "quantidade_texto",
        "pedido_emg", "motivo", "pedido_envio", "anv", "destino", "numero_rc",
        "nf_devolucao_vee_one", "data_devolucao", "observacao_fiscal", "observacao_empresa", "status",
    ]
    nomes_colunas = {
        "numero_ordem": "Nº Ordem", "part_number": "Part Number", "descricao": "Descrição",
        "categoria": "CAT", "quantidade_texto": "QTD", "pedido_emg": "Pedido/EMG",
        "motivo": "Motivo", "pedido_envio": "Pedido de envio", "anv": "ANV", "destino": "Destino",
        "numero_rc": "Nº RC", "nf_devolucao_vee_one": "NF devolução VEE ONE",
        "data_devolucao": "Data devolução", "observacao_fiscal": "Observação Fiscal",
        "observacao_empresa": "Observação Empresa", "status": "Status",
    }
    tabela = filtrado[colunas_tabela].rename(columns=nomes_colunas)
    st.caption(f"{len(tabela)} de {total} itens")
    st.dataframe(tabela, hide_index=True, width="stretch", height=460)

    csv = tabela.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar (CSV)", csv, file_name="emprestimos.csv", mime="text/csv")
