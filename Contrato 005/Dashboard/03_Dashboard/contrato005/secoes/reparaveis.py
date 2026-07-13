"""Tela de detalhe — Reparáveis."""

import plotly.express as px
import streamlit as st

from contrato005.components import data_global
from contrato005.components.paleta import CATEGORICA, layout_grafico
from contrato005.components.utils import ordenar_unicos


def render(dados):
    if data_global.mostrar_snapshot_se_necessario(dados, "reparaveis"):
        return

    st.title("Reparáveis")

    df = dados["reparaveis"]

    col_f0, col_f1, col_f2, col_f3, col_f4 = st.columns(5)
    with col_f0:
        pns = st.multiselect("PN", ordenar_unicos(df["pn"]))
    with col_f1:
        situacoes = st.multiselect(
            "Situação (ST_OS)", ordenar_unicos(df["situacao"]),
            help="Por padrão mostra só as OS em aberto. Selecione 'OS concluída' aqui para vê-las também.",
        )
    with col_f2:
        condicoes = st.multiselect("Condição", ordenar_unicos(df["condicao"]))
    with col_f3:
        locais = st.multiselect("Onde se encontra", ordenar_unicos(df["onde_se_encontra"]))
    with col_f4:
        unidades = st.multiselect("Unidade solicitante", ordenar_unicos(df["unidade_solicitante"]))

    # Situação escolhida manualmente manda mais que o padrão "só em aberto" —
    # assim dá pra escolher "OS concluída" e ver as que já foram fechadas.
    filtrado = df.copy() if situacoes else df[df["em_aberto"]].copy()
    if pns:
        filtrado = filtrado[filtrado["pn"].isin(pns)]
    if situacoes:
        filtrado = filtrado[filtrado["situacao"].isin(situacoes)]
    if condicoes:
        filtrado = filtrado[filtrado["condicao"].isin(condicoes)]
    if locais:
        filtrado = filtrado[filtrado["onde_se_encontra"].isin(locais)]
    if unidades:
        filtrado = filtrado[filtrado["unidade_solicitante"].isin(unidades)]

    st.metric("OS (após filtro)", len(filtrado))

    tabela = filtrado[[
        "os", "pn", "cff", "nomenclatura", "sn", "unidade_solicitante", "situacao",
        "condicao", "onde_se_encontra", "data_inicio", "tat_siloms",
        "data_retorno_prevista", "sn_trocado_exchange", "termo_recebimento",
    ]].copy()
    # Colunas com tipos misturados (data/vazio, número/texto) viram string só
    # para exibição — evita erro de serialização da tabela, sem alterar o xlsx.
    for coluna in ("data_inicio", "data_retorno_prevista", "cff", "sn", "sn_trocado_exchange", "termo_recebimento"):
        tabela[coluna] = tabela[coluna].astype(str).replace({"None": "", "nan": "", "NaT": ""})

    st.dataframe(tabela, width="stretch", hide_index=True, height=420)

    with st.expander("Distribuição por condição"):
        contagem = filtrado["condicao"].value_counts().reset_index()
        contagem.columns = ["condicao", "quantidade"]
        fig = px.bar(contagem, x="quantidade", y="condicao", orientation="h",
                     color_discrete_sequence=[CATEGORICA[0]])
        fig.update_layout(yaxis_title="", xaxis_title="Quantidade", showlegend=False)
        layout_grafico(fig)
        st.plotly_chart(fig, width="stretch")
