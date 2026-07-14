"""Consumo / Estoque / Solicitações — 3 fontes extras do TPJL, da pasta Drive
"Planilhas TPLJ", integradas DENTRO da mesma página "TPJL — Controle CABW"
(pedido do Wallace em 2026-07-14: "no mesmo layout das coisas que estao ai,
inclusive dentro ... gosto de filtros e estatisticas"). 3 abas novas
("Consumo", "Estoque", "Solicitações"), chamadas a partir de
secoes/tpjl.py::render(). Ver 00_Instrucoes/tpjl.md.

Cada fonte já vem 100% filtrada em Projeto = "U8" (confirmado na extração,
ver extrair_tpjl_extras.py) — não há filtro de projeto aqui, só os filtros
próprios de cada tabela (ano/mês/categoria/unidade/status/etc.).

"Categoria" (C/R/T/P) e "Setor"/"Unidade" vêm exatamente como a planilha
escreve — não convertidos pra um nome mais "amigável" porque o significado
exato de cada sigla não foi confirmado com o Wallace.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from projetos.components.atualizacao import botao_atualizar, status_atualizacao_html
from projetos.components.paleta import (
    COR_STATUS_SOLICITACAO, STATUS,
    PRIMARY as AMBER,
    cabecalho_pagina, cartao_indicador, grade_indicadores, layout_grafico,
)


def _atualizar():
    from projetos.data.atualizar_drive import atualizar_fonte
    return atualizar_fonte("tpjl_extras")


def _num(v):
    if v is None or pd.isna(v):
        return "0"
    return f"{v:,.0f}".replace(",", ".")


def _rotular(fig, valores):
    fig.update_traces(text=[_num(v) for v in valores], textposition="outside", cliponaxis=False)
    return fig


def _agrupado_top_n(df, coluna_grupo, coluna_valor, n=10, agregacao="sum"):
    """Agrupa e ordena por valor, ficando só com os top N + 'Outros'."""
    if agregacao == "sum":
        agrupado = df.groupby(coluna_grupo)[coluna_valor].sum()
    else:
        agrupado = df.groupby(coluna_grupo)[coluna_valor].count()
    agrupado = agrupado.sort_values(ascending=False)
    if len(agrupado) > n:
        principais = agrupado.iloc[:n]
        outros = pd.Series({"Outros": agrupado.iloc[n:].sum()}, name=agrupado.name)
        outros.index.name = agrupado.index.name
        agrupado = pd.concat([principais, outros])
    return agrupado.reset_index(name=coluna_valor)


def _cabecalho_fonte(titulo, estado_atual, key_sufixo):
    col_titulo, col_botao = st.columns([4, 1])
    with col_titulo:
        st.markdown(f'<div class="pj-titulo-secao">{titulo}</div>', unsafe_allow_html=True)
        st.markdown(status_atualizacao_html(estado_atual), unsafe_allow_html=True)
    with col_botao:
        st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
        botao_atualizar("Consumo/Estoque/Solicitações", _atualizar, key=f"tpjl_extras_atualizar_{key_sufixo}")


def _secao_consumo(df, estado_atual):
    _cabecalho_fonte("Consumo — histórico mensal (Projeto U8)", estado_atual, "consumo")
    st.caption('Fonte: relatório "Consumo" da pasta Drive "Planilhas TPLJ".')

    if df is None or df.empty:
        st.info('Ainda não foi carregado — clique em "Atualizar" acima.')
        return

    total_linhas = len(df)
    qtd_total = df["qtd_consumo"].sum(skipna=True)
    pns_distintos = df["pn"].nunique()
    periodo = df.assign(_p=df["ano"] * 100 + df["mes"])
    ini, fim = periodo.loc[periodo["_p"].idxmin()], periodo.loc[periodo["_p"].idxmax()]
    texto_periodo = f"{ini['mes']:02.0f}/{ini['ano']:.0f} a {fim['mes']:02.0f}/{fim['ano']:.0f}"

    grade_indicadores([
        cartao_indicador("Linhas de consumo", _num(total_linhas), None, "primary"),
        cartao_indicador("Quantidade total consumida", _num(qtd_total), None, "primary"),
        cartao_indicador("Part Numbers distintos", _num(pns_distintos), None, "info"),
        cartao_indicador("Período coberto", texto_periodo, None, "neutro"),
    ])

    st.markdown('<div class="pj-titulo-secao">Filtros</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        anos_f = st.multiselect("Ano", sorted(df["ano"].dropna().unique(), reverse=True), key="tpjl_consumo_f_ano")
    with c2:
        meses_f = st.multiselect("Mês", sorted(df["mes"].dropna().unique()), key="tpjl_consumo_f_mes")
    with c3:
        categorias_f = st.multiselect("Categoria", sorted(df["categoria"].dropna().unique()), key="tpjl_consumo_f_categoria")
    with c4:
        busca = st.text_input("🔎 Busca (PN, Descrição)", key="tpjl_consumo_f_busca")

    filtrado = df.copy()
    if anos_f:
        filtrado = filtrado[filtrado["ano"].isin(anos_f)]
    if meses_f:
        filtrado = filtrado[filtrado["mes"].isin(meses_f)]
    if categorias_f:
        filtrado = filtrado[filtrado["categoria"].isin(categorias_f)]
    if busca:
        b = busca.strip().lower()
        filtrado = filtrado[
            filtrado["pn"].astype(str).str.lower().str.contains(b, na=False)
            | filtrado["descricao"].astype(str).str.lower().str.contains(b, na=False)
        ]
    st.caption(f"Exibindo {len(filtrado)} de {len(df)} linhas")

    if filtrado.empty:
        st.caption("Nenhuma linha após os filtros.")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.caption("Quantidade consumida por ano")
        por_ano = filtrado.groupby("ano")["qtd_consumo"].sum().reset_index()
        fig = px.bar(por_ano, x="ano", y="qtd_consumo", color_discrete_sequence=[AMBER])
        _rotular(fig, por_ano["qtd_consumo"])
        fig.update_layout(xaxis_title="", yaxis_title="", xaxis={"type": "category"})
        layout_grafico(fig, altura=340)
        st.plotly_chart(fig, width="stretch", key="tpjl_consumo_por_ano")

    with col2:
        st.caption("Quantidade consumida por categoria")
        por_cat = filtrado.groupby("categoria")["qtd_consumo"].sum().sort_values(ascending=False).reset_index()
        fig = px.bar(por_cat.sort_values("qtd_consumo"), x="qtd_consumo", y="categoria", orientation="h",
                     color_discrete_sequence=[STATUS["info"]])
        _rotular(fig, por_cat.sort_values("qtd_consumo")["qtd_consumo"])
        fig.update_layout(xaxis_title="", yaxis_title="")
        layout_grafico(fig, altura=340)
        st.plotly_chart(fig, width="stretch", key="tpjl_consumo_por_categoria")

    st.caption("Top 10 Part Numbers mais consumidos (quantidade)")
    top_pn = filtrado.groupby(["pn", "descricao"])["qtd_consumo"].sum().reset_index()
    top_pn = top_pn.sort_values("qtd_consumo", ascending=False).head(10)
    top_pn["rotulo"] = top_pn["pn"].astype(str) + " — " + top_pn["descricao"].astype(str).str.slice(0, 40)
    top_pn = top_pn.sort_values("qtd_consumo")
    fig = px.bar(top_pn, x="qtd_consumo", y="rotulo", orientation="h", color_discrete_sequence=[STATUS["good"]])
    _rotular(fig, top_pn["qtd_consumo"])
    fig.update_layout(xaxis_title="", yaxis_title="")
    layout_grafico(fig, altura=380)
    st.plotly_chart(fig, width="stretch", key="tpjl_consumo_top_pn")

    st.markdown('<div class="pj-titulo-secao">Tabela — Consumo</div>', unsafe_allow_html=True)
    nomes = {
        "pn": "PN", "cff": "CFF", "descricao": "Descrição", "categoria": "Categoria",
        "mes": "Mês", "ano": "Ano", "qtd_consumo": "Qtd Consumo",
    }
    tabela = filtrado[list(nomes.keys())].rename(columns=nomes).sort_values(["Ano", "Mês"], ascending=False)
    st.dataframe(tabela, hide_index=True, width="stretch", height=420)
    csv = tabela.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar (CSV)", csv, file_name="tpjl_consumo.csv", mime="text/csv", key="tpjl_consumo_csv")


def _secao_estoque(df, estado_atual):
    _cabecalho_fonte("Estoque — situação atual (Projeto U8)", estado_atual, "estoque")
    st.caption('Fonte: relatório "Estoque" da pasta Drive "Planilhas TPLJ".')

    if df is None or df.empty:
        st.info('Ainda não foi carregado — clique em "Atualizar" acima.')
        return

    total_linhas = len(df)
    qtd_total = df["qtd_estoque"].sum(skipna=True)
    pns_distintos = df["pn"].nunique()
    unidades_distintas = df["unidade"].nunique()

    grade_indicadores([
        cartao_indicador("Itens em estoque (linhas)", _num(total_linhas), None, "primary"),
        cartao_indicador("Quantidade total em estoque", _num(qtd_total), None, "primary"),
        cartao_indicador("Part Numbers distintos", _num(pns_distintos), None, "info"),
        cartao_indicador("Unidades/bases distintas", _num(unidades_distintas), None, "neutro"),
    ])

    st.markdown('<div class="pj-titulo-secao">Filtros</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        unidades_f = st.multiselect("Unidade", sorted(df["unidade"].dropna().unique(), key=str), key="tpjl_estoque_f_unidade")
    with c2:
        setores_f = st.multiselect("Setor", sorted(df["setor"].dropna().unique(), key=str), key="tpjl_estoque_f_setor")
    with c3:
        categorias_f = st.multiselect("Categoria", sorted(df["categoria"].dropna().unique()), key="tpjl_estoque_f_categoria")
    with c4:
        busca = st.text_input("🔎 Busca (PN, Descrição)", key="tpjl_estoque_f_busca")

    filtrado = df.copy()
    if unidades_f:
        filtrado = filtrado[filtrado["unidade"].isin(unidades_f)]
    if setores_f:
        filtrado = filtrado[filtrado["setor"].isin(setores_f)]
    if categorias_f:
        filtrado = filtrado[filtrado["categoria"].isin(categorias_f)]
    if busca:
        b = busca.strip().lower()
        filtrado = filtrado[
            filtrado["pn"].astype(str).str.lower().str.contains(b, na=False)
            | filtrado["descricao"].astype(str).str.lower().str.contains(b, na=False)
        ]
    st.caption(f"Exibindo {len(filtrado)} de {len(df)} linhas")

    if filtrado.empty:
        st.caption("Nenhuma linha após os filtros.")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.caption("Quantidade em estoque por unidade (top 10)")
        por_unidade = _agrupado_top_n(filtrado, "unidade", "qtd_estoque", n=10)
        fig = px.bar(por_unidade.sort_values("qtd_estoque"), x="qtd_estoque", y="unidade", orientation="h",
                     color_discrete_sequence=[AMBER])
        _rotular(fig, por_unidade.sort_values("qtd_estoque")["qtd_estoque"])
        fig.update_layout(xaxis_title="", yaxis_title="")
        layout_grafico(fig, altura=340)
        st.plotly_chart(fig, width="stretch", key="tpjl_estoque_por_unidade")

    with col2:
        st.caption("Quantidade em estoque por setor")
        por_setor = filtrado.groupby("setor")["qtd_estoque"].sum().sort_values(ascending=False).reset_index()
        fig = px.bar(por_setor.sort_values("qtd_estoque"), x="qtd_estoque", y="setor", orientation="h",
                     color_discrete_sequence=[STATUS["info"]])
        _rotular(fig, por_setor.sort_values("qtd_estoque")["qtd_estoque"])
        fig.update_layout(xaxis_title="", yaxis_title="")
        layout_grafico(fig, altura=340)
        st.plotly_chart(fig, width="stretch", key="tpjl_estoque_por_setor")

    st.caption("Top 10 Part Numbers com mais quantidade em estoque")
    top_pn = filtrado.groupby(["pn", "descricao"])["qtd_estoque"].sum().reset_index()
    top_pn = top_pn.sort_values("qtd_estoque", ascending=False).head(10)
    top_pn["rotulo"] = top_pn["pn"].astype(str) + " — " + top_pn["descricao"].astype(str).str.slice(0, 40)
    top_pn = top_pn.sort_values("qtd_estoque")
    fig = px.bar(top_pn, x="qtd_estoque", y="rotulo", orientation="h", color_discrete_sequence=[STATUS["good"]])
    _rotular(fig, top_pn["qtd_estoque"])
    fig.update_layout(xaxis_title="", yaxis_title="")
    layout_grafico(fig, altura=380)
    st.plotly_chart(fig, width="stretch", key="tpjl_estoque_top_pn")

    st.markdown('<div class="pj-titulo-secao">Tabela — Estoque</div>', unsafe_allow_html=True)
    nomes = {
        "pn": "PN", "cff": "CFF", "descricao": "Descrição", "categoria": "Categoria",
        "setor": "Setor", "unidade": "Unidade", "qtd_estoque": "Qtd em Estoque",
    }
    tabela = filtrado[list(nomes.keys())].rename(columns=nomes).sort_values("Qtd em Estoque", ascending=False)
    st.dataframe(tabela, hide_index=True, width="stretch", height=420)
    csv = tabela.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar (CSV)", csv, file_name="tpjl_estoque.csv", mime="text/csv", key="tpjl_estoque_csv")


def _secao_solicitacoes(df, estado_atual):
    _cabecalho_fonte("Solicitações — log de pedidos (Projeto U8)", estado_atual, "solicitacoes")
    st.caption('Fonte: relatório "Solicitações" da pasta Drive "Planilhas TPLJ".')

    if df is None or df.empty:
        st.info('Ainda não foi carregado — clique em "Atualizar" acima.')
        return

    total = len(df)
    pendentes = int((df["status"] == "Pendente").sum())
    aprovadas = int((df["status"] == "Aprovada").sum())
    finalizadas = int((df["status"] == "Finalizada").sum())
    negadas = int((df["status"] == "Negada").sum())

    grade_indicadores([
        cartao_indicador("Total de solicitações", _num(total), None, "primary"),
        cartao_indicador("Pendentes", _num(pendentes), None, "warning"),
        cartao_indicador("Aprovadas", _num(aprovadas), None, "info"),
        cartao_indicador("Finalizadas", _num(finalizadas), f"{100 * finalizadas / total:.0f}% do total" if total else None, "good"),
        cartao_indicador("Negadas", _num(negadas), None, "critical"),
    ])

    st.markdown('<div class="pj-titulo-secao">Filtros</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        tipos_f = st.multiselect("Tipo", sorted(df["tipo"].dropna().unique()), key="tpjl_sol_f_tipo")
    with c2:
        status_f = st.multiselect("Status", sorted(df["status"].dropna().unique()), key="tpjl_sol_f_status")
    with c3:
        solicitantes_f = st.multiselect("Solicitante", sorted(df["solicitante"].dropna().unique(), key=str), key="tpjl_sol_f_solicitante")
    with c4:
        busca = st.text_input("🔎 Busca (Nº, PN, Nomenclatura)", key="tpjl_sol_f_busca")

    filtrado = df.copy()
    if tipos_f:
        filtrado = filtrado[filtrado["tipo"].isin(tipos_f)]
    if status_f:
        filtrado = filtrado[filtrado["status"].isin(status_f)]
    if solicitantes_f:
        filtrado = filtrado[filtrado["solicitante"].isin(solicitantes_f)]
    if busca:
        b = busca.strip().lower()
        filtrado = filtrado[
            filtrado["numero_solicitacao"].astype(str).str.lower().str.contains(b, na=False)
            | filtrado["pn"].astype(str).str.lower().str.contains(b, na=False)
            | filtrado["nomenclatura"].astype(str).str.lower().str.contains(b, na=False)
        ]
    st.caption(f"Exibindo {len(filtrado)} de {len(df)} solicitações")

    if filtrado.empty:
        st.caption("Nenhuma solicitação após os filtros.")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.caption("Distribuição por Status")
        contagem = filtrado["status"].value_counts().reset_index()
        contagem.columns = ["status", "quantidade"]
        cores = {s: COR_STATUS_SOLICITACAO.get(s, STATUS["neutro"]) for s in contagem["status"]}
        fig = px.bar(contagem, x="status", y="quantidade", color="status", color_discrete_map=cores)
        _rotular(fig, contagem["quantidade"])
        fig.update_layout(xaxis_title="", yaxis_title="", showlegend=False)
        layout_grafico(fig, altura=340)
        st.plotly_chart(fig, width="stretch", key="tpjl_sol_por_status")

    with col2:
        st.caption("Distribuição por Tipo")
        contagem_tipo = filtrado["tipo"].value_counts().sort_values().reset_index()
        contagem_tipo.columns = ["tipo", "quantidade"]
        fig = px.bar(contagem_tipo, x="quantidade", y="tipo", orientation="h", color_discrete_sequence=[AMBER])
        _rotular(fig, contagem_tipo["quantidade"])
        fig.update_layout(xaxis_title="", yaxis_title="")
        layout_grafico(fig, altura=340)
        st.plotly_chart(fig, width="stretch", key="tpjl_sol_por_tipo")

    col3, col4 = st.columns(2)
    with col3:
        st.caption("Top 10 solicitantes (quantidade de pedidos)")
        top_solic = _agrupado_top_n(filtrado, "solicitante", "numero_solicitacao", n=10, agregacao="count")
        top_solic = top_solic.rename(columns={"numero_solicitacao": "quantidade"})
        fig = px.bar(top_solic.sort_values("quantidade"), x="quantidade", y="solicitante", orientation="h",
                     color_discrete_sequence=[STATUS["info"]])
        _rotular(fig, top_solic.sort_values("quantidade")["quantidade"])
        fig.update_layout(xaxis_title="", yaxis_title="")
        layout_grafico(fig, altura=340)
        st.plotly_chart(fig, width="stretch", key="tpjl_sol_top_solicitantes")

    with col4:
        st.caption("Solicitações por mês de criação")
        com_data = filtrado.dropna(subset=["data_criacao"]).copy()
        if com_data.empty:
            st.caption("Sem datas de criação válidas nesse conjunto de dados.")
        else:
            com_data["mes_criacao"] = com_data["data_criacao"].dt.to_period("M").dt.to_timestamp()
            por_mes = com_data.groupby("mes_criacao").size().reset_index(name="quantidade")
            fig = px.bar(por_mes, x="mes_criacao", y="quantidade", color_discrete_sequence=[STATUS["good"]])
            fig.update_layout(xaxis_title="", yaxis_title="")
            layout_grafico(fig, altura=340)
            st.plotly_chart(fig, width="stretch", key="tpjl_sol_por_mes")

    st.markdown('<div class="pj-titulo-secao">Tabela — Solicitações</div>', unsafe_allow_html=True)
    nomes = {
        "numero_solicitacao": "Nº Solicitação", "pn": "PN", "nomenclatura": "Nomenclatura",
        "categoria": "Categoria", "quantidade": "Quantidade", "tipo": "Tipo", "status": "Status",
        "unidade_estocagem": "Unid. Estocagem", "solicitante": "Solicitante",
        "data_criacao": "Data de Criação", "ultima_atualizacao": "Última Atualização",
    }
    tabela = filtrado[list(nomes.keys())].rename(columns=nomes).sort_values("Data de Criação", ascending=False)
    st.dataframe(tabela, hide_index=True, width="stretch", height=420)
    csv = tabela.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar (CSV)", csv, file_name="tpjl_solicitacoes.csv", mime="text/csv", key="tpjl_sol_csv")


def render_consumo(dados):
    extras = dados.get("tpjl_extras") or {}
    _secao_consumo(extras.get("consumo"), dados.get("tpjl_extras_estado", {}))


def render_estoque(dados):
    extras = dados.get("tpjl_extras") or {}
    _secao_estoque(extras.get("estoque"), dados.get("tpjl_extras_estado", {}))


def render_solicitacoes(dados):
    extras = dados.get("tpjl_extras") or {}
    _secao_solicitacoes(extras.get("solicitacoes"), dados.get("tpjl_extras_estado", {}))
