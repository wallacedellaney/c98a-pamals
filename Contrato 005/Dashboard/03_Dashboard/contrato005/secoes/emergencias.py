"""Tela de detalhe — Emergências Abertas."""

import pandas as pd
import plotly.express as px
import streamlit as st

from contrato005.components import data_global
from contrato005.components.paleta import AMBER, CATEGORICA, layout_grafico
from contrato005.components.utils import ordenar_unicos

TPEMG_PRIORIDADE = ("AIFP", "IPLR")  # prazo de 6 e 10 dias corridos (ver emergencias.md) — ANCE tem 30

COLUNAS_TABELA = [
    "om", "numero_emergencia", "pn", "nomenclatura", "matricula_aeronave",
    "situacao", "tpemg", "data_abertura", "data_info", "quantidade",
    "prazo_entrega", "dpe", "atendido_cancelado", "dias_atraso", "dias_corridos",
    "estoque", "obs_coordenadoria_fiscal", "obs_vee_one",
]
NOMES_COLUNAS = {
    "om": "OM", "numero_emergencia": "EMERGÊNCIA", "pn": "PN", "nomenclatura": "NOMENCLATURA",
    "matricula_aeronave": "MATR", "situacao": "ST_EMG", "tpemg": "TPEMG",
    "data_abertura": "DT_EMG", "data_info": "INFO EMG", "quantidade": "QT_EMG",
    "prazo_entrega": "PRAZO DE ENTREGA", "dpe": "DPE", "atendido_cancelado": "Atd/cancelada",
    "dias_atraso": "DIAS ATRASO", "dias_corridos": "DIAS CORRIDOS", "estoque": "Estoque",
    "obs_coordenadoria_fiscal": "OBSERVAÇÃO COORDENADORIA/FISCAL", "obs_vee_one": "OBSERVAÇÃO VEE ONE",
}


def _destacar_prioridade(row):
    if row["TPEMG"] in TPEMG_PRIORIDADE:
        return [f"background-color: {AMBER}22"] * len(row)
    return [""] * len(row)


def render(dados):
    if data_global.mostrar_snapshot_se_necessario(dados, "emergencias"):
        return

    st.title("Emergências Abertas")

    df = dados["emergencias"]
    df = df[df["em_aberto"]]

    col_f0, col_f1, col_f2, col_f3, col_f4 = st.columns(5)
    with col_f0:
        pns = st.multiselect("PN", ordenar_unicos(df["pn"]))
    with col_f1:
        aeronaves = st.multiselect("Aeronave (MATR)", ordenar_unicos(df["matricula_aeronave"]))
    with col_f2:
        situacoes = st.multiselect("Situação (ST_EMG)", ordenar_unicos(df["situacao"]))
    with col_f3:
        tpemgs = st.multiselect("TPEMG", ordenar_unicos(df["tpemg"]))
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

    tabela = filtrado[COLUNAS_TABELA].rename(columns=NOMES_COLUNAS)
    st.dataframe(
        tabela.style.apply(_destacar_prioridade, axis=1),
        width="stretch",
        hide_index=True,
        height=420,
    )

    st.divider()
    _novidades(dados)

    with st.expander("Distribuição por situação"):
        por_situacao = filtrado["situacao"].value_counts().reset_index()
        por_situacao.columns = ["situacao", "quantidade"]
        fig = px.bar(por_situacao, x="situacao", y="quantidade", color_discrete_sequence=[CATEGORICA[0]])
        fig.update_layout(xaxis_title="", yaxis_title="Quantidade", showlegend=False)
        layout_grafico(fig)
        st.plotly_chart(fig, width="stretch")


def _novidades(dados):
    st.markdown("##### Novidades desde a última atualização")
    historico = dados.get("historico_emergencias")
    if historico is None or historico.empty:
        st.info(
            "Ainda não há histórico registrado — o registro começou em 2026-07-06 e "
            "acumula um snapshot por dia útil, junto da atualização automática (seg-sex 12h)."
        )
        return

    datas = sorted(historico["data_snapshot"].unique())
    if len(datas) < 2:
        st.info(
            f"Só existe 1 snapshot até agora ({pd.Timestamp(datas[-1]).strftime('%d/%m/%Y')}) — "
            "a comparação aparece a partir do 2º dia útil registrado."
        )
        return

    data_atual, data_anterior = datas[-1], datas[-2]
    atual = historico[historico["data_snapshot"] == data_atual]
    anterior = historico[historico["data_snapshot"] == data_anterior]

    novas = atual[~atual["numero_emergencia"].isin(anterior["numero_emergencia"])]
    saidas = anterior[~anterior["numero_emergencia"].isin(atual["numero_emergencia"])]

    st.caption(
        f"Comparando {pd.Timestamp(data_anterior).strftime('%d/%m/%Y')} → "
        f"{pd.Timestamp(data_atual).strftime('%d/%m/%Y')}"
    )
    c1, c2 = st.columns(2)
    c1.metric("Novas emergências", len(novas))
    c2.metric("Saíram da lista (atendidas/canceladas)", len(saidas))

    if len(novas):
        with st.expander(f"🆕 Ver as {len(novas)} nova(s)", expanded=True):
            st.dataframe(
                novas[["numero_emergencia", "om", "matricula_aeronave", "pn", "nomenclatura",
                       "situacao", "tpemg", "data_abertura"]].rename(columns=NOMES_COLUNAS),
                hide_index=True, width="stretch",
            )
    if len(saidas):
        with st.expander(f"✅ Ver as {len(saidas)} que saíram"):
            st.dataframe(
                saidas[["numero_emergencia", "om", "matricula_aeronave", "pn", "nomenclatura",
                        "situacao", "tpemg", "data_abertura"]].rename(columns=NOMES_COLUNAS),
                hide_index=True, width="stretch",
            )
    if not len(novas) and not len(saidas):
        st.success("Nenhuma mudança na lista de emergências em aberto desde o último snapshot.")
