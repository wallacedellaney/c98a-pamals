"""Tela de detalhe — Reparáveis."""

import pandas as pd
import plotly.express as px
import streamlit as st

from shared import horario
from contrato005.components import data_global
from contrato005.components.paleta import AMBER, CATEGORICA, STATUS, layout_grafico
from contrato005.components.utils import ordenar_unicos

# "Onde se encontra" que significa que o item JÁ foi entregue pelo
# fornecedor (VEE ONE) pra unidade/base — só falta encerrar a burocracia da
# OS, não é mais um atraso de reparo de verdade. Pedido do Wallace em
# 2026-07-18: "quando tiver com os eles ou com terceirizados, quando tiver
# escrito: BABE, BAMN,BABV,BAPV,BABR,BANT,PAMALS,BACO,BASM,BACG EEAR
# SIGNIFICA QUE ELE ja entregou SO ATE ABERTO A BUROCRACIA". "PAMA-LS" é o
# nome real na fonte (o que o Wallace escreveu como "PAMALS"). **"V1
# PAMA-LS" NÃO entra aqui** — é um valor diferente (ainda com o
# fornecedor), confirmado pelo Wallace: "obs: v1 pamals esta com eles
# ainda" — por isso o match é por igualdade exata, não por "contém".
LOCAIS_ENTREGUES = {
    "BABE", "BAMN", "BABV", "BAPV", "BABR", "BANT", "PAMA-LS", "BACO", "BASM", "BACG", "EEAR",
}

# Prazo contratual de TAT (Turn Around Time) — confirmado pelo Wallace em 2026-07-18.
PRAZO_CONTRATUAL_TAT_DIAS = 110

# "Onde se encontra" vazio não é "sem dado" — pedido do Wallace em
# 2026-07-18: "quando tiver vazio, a empresa ainda nao passou, esta em
# processo interno da empresa ou nao foi informado por ela". Preenchido
# logo na entrada de render() (não só na exibição) pra entrar certo em
# TODO lugar que usa essa coluna — filtro, tabela e "Estatísticas de TAT"
# (sem isso, o `groupby` do gráfico "TAT médio por local" descartava essas
# linhas por padrão, já que pandas ignora grupos NaN).
LOCAL_NAO_INFORMADO = "Em processo interno / não informado pela empresa"


def _secao_estatisticas_tat(df):
    abertos = df[df["em_aberto"]].copy()
    if abertos.empty:
        return

    st.markdown("##### Estatísticas de TAT")
    st.caption(
        "\"Com a empresa e terceirizados\" = ainda não entregue pelo fornecedor. Quando \"Onde se "
        "encontra\" é BABE/BAMN/BABV/BAPV/BABR/BANT/PAMA-LS/BACO/BASM/BACG/EEAR, já foi entregue — "
        "só falta encerrar a burocracia da OS (\"V1 PAMA-LS\" não conta como entregue, é outra "
        f"etapa, ainda com a empresa). Vazio = \"{LOCAL_NAO_INFORMADO}\"."
    )

    abertos = abertos.copy()
    abertos["grupo"] = abertos["onde_se_encontra"].isin(LOCAIS_ENTREGUES).map(
        {True: "Entregue (falta burocracia)", False: "Com a empresa e terceirizados"}
    )
    empresa = abertos[abertos["grupo"] == "Com a empresa e terceirizados"]

    def _media_tat(sub):
        return f"{sub['tat_siloms'].mean():.0f} dias" if sub["tat_siloms"].notna().any() else "—"

    c1, c2 = st.columns(2)
    c1.metric("Abertos (geral)", len(abertos))
    c2.metric("Média de TAT geral (mesmo faltando a burocracia)", _media_tat(abertos))

    c3, c4 = st.columns(2)
    c3.metric("Com a empresa e terceirizados", len(empresa))
    c4.metric("Média de TAT — empresa e terceirizados", _media_tat(empresa))

    # Prazo contratual (dentro/fora, vence este mês) só faz sentido pra quem
    # ainda está com a empresa/terceirizados — item já entregue (só falta
    # burocracia) não conta mais contra o prazo. Pedido do Wallace em
    # 2026-07-18: "o prazo dentro e fora do prazo so os que estao com a
    # empresa".
    hoje = pd.Timestamp(horario.hoje_br())
    fora_prazo = empresa[empresa["tat_siloms"] > PRAZO_CONTRATUAL_TAT_DIAS]
    dentro_prazo = empresa[empresa["tat_siloms"] <= PRAZO_CONTRATUAL_TAT_DIAS]

    com_data = empresa.dropna(subset=["data_inicio"]).copy()
    com_data["data_limite"] = pd.to_datetime(com_data["data_inicio"]) + pd.Timedelta(days=PRAZO_CONTRATUAL_TAT_DIAS)
    vence_mes = com_data[
        (com_data["data_limite"].dt.year == hoje.year)
        & (com_data["data_limite"].dt.month == hoje.month)
        & (com_data["tat_siloms"] <= PRAZO_CONTRATUAL_TAT_DIAS)
    ]

    c5, c6 = st.columns(2)
    c5.metric(f"Fora do prazo contratual (> {PRAZO_CONTRATUAL_TAT_DIAS} dias) — empresa/terceirizados", len(fora_prazo), delta_color="inverse")
    c6.metric("Vencem o prazo contratual este mês — empresa/terceirizados", len(vence_mes), delta_color="inverse")

    g1, g2 = st.columns(2)
    with g1:
        st.caption("Com a empresa e terceirizados x Entregue (falta burocracia)")
        contagem_grupo = abertos["grupo"].value_counts().reset_index()
        contagem_grupo.columns = ["grupo", "quantidade"]
        fig_grupo = px.pie(
            contagem_grupo, names="grupo", values="quantidade", hole=0.55,
            color="grupo",
            color_discrete_map={"Com a empresa e terceirizados": AMBER, "Entregue (falta burocracia)": STATUS["good"]},
        )
        fig_grupo.update_traces(textinfo="value+percent", textfont_size=12)
        layout_grafico(fig_grupo, altura=230)
        st.plotly_chart(fig_grupo, width="stretch")

    with g2:
        st.caption(f"Dentro x fora do prazo contratual ({PRAZO_CONTRATUAL_TAT_DIAS} dias) — só empresa/terceirizados")
        contagem_prazo = pd.DataFrame({
            "situacao": ["Dentro do prazo", "Fora do prazo"],
            "quantidade": [len(dentro_prazo), len(fora_prazo)],
        })
        fig_prazo = px.pie(
            contagem_prazo, names="situacao", values="quantidade", hole=0.55,
            color="situacao",
            color_discrete_map={"Dentro do prazo": STATUS["good"], "Fora do prazo": STATUS["critical"]},
        )
        fig_prazo.update_traces(textinfo="value+percent", textfont_size=12)
        layout_grafico(fig_prazo, altura=230)
        st.plotly_chart(fig_prazo, width="stretch")

    st.caption("TAT médio por local ('Onde se encontra')")
    media_local = (
        abertos.dropna(subset=["tat_siloms"])
        .groupby("onde_se_encontra")["tat_siloms"]
        .agg(["mean", "count"])
        .reset_index()
        .rename(columns={"onde_se_encontra": "Onde se encontra", "mean": "TAT médio (dias)", "count": "Quantidade"})
        .sort_values("TAT médio (dias)", ascending=False)
    )
    media_local["TAT médio (dias)"] = media_local["TAT médio (dias)"].round(0).astype(int)
    fig_local = px.bar(
        media_local, x="TAT médio (dias)", y="Onde se encontra", orientation="h",
        color_discrete_sequence=[AMBER],
    )
    fig_local.add_vline(x=PRAZO_CONTRATUAL_TAT_DIAS, line_dash="dash", line_color=STATUS["critical"],
                         annotation_text=f"{PRAZO_CONTRATUAL_TAT_DIAS}d contratual")
    fig_local.update_layout(yaxis_title="", xaxis_title="TAT médio (dias)")
    layout_grafico(fig_local, altura=max(200, 28 * len(media_local)))
    st.plotly_chart(fig_local, width="stretch")

    with st.expander("Ver tabela — TAT médio por local"):
        st.dataframe(media_local, hide_index=True, width="stretch")

    st.divider()


def render(dados):
    if data_global.mostrar_snapshot_se_necessario(dados, "reparaveis"):
        return

    st.title("Reparáveis")

    df = dados["reparaveis"].copy()
    df["onde_se_encontra"] = df["onde_se_encontra"].fillna(LOCAL_NAO_INFORMADO)

    _secao_estatisticas_tat(df)

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
