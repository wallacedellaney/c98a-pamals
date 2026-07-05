"""Diagonal de Manutenção — linha do tempo (Gantt) de indisponibilidade por
aeronave. Combina duas fontes, lado a lado na mesma linha por aeronave:
* "Real (hoje)" — situação de verdade, tirada do relatório mais recente da
  Disponibilidade Diária (situação != DI/DO), até a data prevista (DPE) ou
  +14 dias se não houver previsão.
* "Programado" — projeção futura de inspeções, tirada da Diagonal de
  Manutenção de cada operador.
Ver 00_Instrucoes/diagonal_manutencao.md.
"""

from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from coordenadoria.components.filtros import filtro_colunas
from coordenadoria.components.paleta import CATEGORICA, INK, LINE, PANEL, SECONDARY, layout_grafico
from coordenadoria.utils import atualizar_dados_diagonal_manutencao

FONTE_REAL = "Real (hoje)"
FONTE_PROGRAMADO = "Programado"
PATTERN_FONTE = {FONTE_REAL: "", FONTE_PROGRAMADO: "/"}


def _eventos_reais(disp_aeronaves):
    """Constrói os eventos "de verdade" a partir do relatório mais recente da
    Disponibilidade Diária — aeronaves com situação != DI/DO (ver
    00_Instrucoes/disponibilidade_diaria.md pro significado de cada código)."""
    if disp_aeronaves is None or disp_aeronaves.empty:
        return pd.DataFrame(columns=["operador", "aeronave", "periodo_inicio", "periodo_fim", "motivo", "confianca", "fonte"])

    ultima_data = disp_aeronaves["data_referencia"].max()
    hoje_snapshot = disp_aeronaves[disp_aeronaves["data_referencia"] == ultima_data]
    indisponiveis = hoje_snapshot[~hoje_snapshot["situacao"].isin(["DI", "DO"])].copy()
    if indisponiveis.empty:
        return pd.DataFrame(columns=["operador", "aeronave", "periodo_inicio", "periodo_fim", "motivo", "confianca", "fonte"])

    def _fim(row):
        if pd.notna(row["dpe_data"]):
            return row["dpe_data"]
        return row["data_referencia"] + timedelta(days=14)

    def _motivo(row):
        base = row["situacao"]
        if pd.notna(row["ocorrencia"]) and str(row["ocorrencia"]).strip():
            base = f"{row['situacao']}: {row['ocorrencia']}"
        if pd.isna(row["dpe_data"]):
            base += " (sem previsão de retorno — +14d de referência)"
        return base

    indisponiveis["periodo_inicio"] = indisponiveis["data_referencia"]
    indisponiveis["periodo_fim"] = indisponiveis.apply(_fim, axis=1)
    indisponiveis["motivo"] = indisponiveis.apply(_motivo, axis=1)
    indisponiveis["operador"] = indisponiveis["unidade"]
    indisponiveis["confianca"] = "Real"
    indisponiveis["fonte"] = FONTE_REAL
    return indisponiveis.rename(columns={"matricula": "aeronave"})[
        ["operador", "aeronave", "periodo_inicio", "periodo_fim", "motivo", "confianca", "fonte"]
    ]


def render(dados):
    st.title("Diagonal de Manutenção")
    st.caption(
        "Linha do tempo por aeronave: sólido = situação real hoje (Disponibilidade "
        "Diária), listrado = projeção futura de inspeção programada (Diagonal de "
        "Manutenção)."
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔄 Atualizar dados", key="diagonal_atualizar"):
            with st.spinner("Reprocessando dados locais..."):
                atualizar_dados_diagonal_manutencao()
            st.rerun()

    df_programado = dados["diagonal"].copy()
    if not df_programado.empty:
        df_programado["fonte"] = FONTE_PROGRAMADO
    df_real = _eventos_reais(dados.get("disp_aeronaves"))
    df = pd.concat([df_real, df_programado], ignore_index=True)

    if df.empty:
        st.info("Nenhum dado carregado ainda. Peça ao Claude para buscar a Diagonal de Manutenção de cada operador.")
        return

    if dados["diagonal_atualizado_em"]:
        atualizado = datetime.fromtimestamp(dados["diagonal_atualizado_em"]).strftime("%d/%m/%Y %H:%M")
        st.caption(f"Última atualização dos dados (Diagonal): **{atualizado}**")
    if not df_real.empty:
        st.caption(f"Situação real de hoje: **{df_real['periodo_inicio'].max().strftime('%d/%m/%Y')}** ({len(df_real)} aeronave(s) indisponível(is) no último relatório de Disponibilidade Diária)")

    hoje = pd.Timestamp.now().normalize()

    c1, c2 = st.columns([1, 3])
    with c1:
        operadores = st.multiselect("Operador", sorted(df["operador"].unique()), key="diagonal_filtro_operador")
    with c2:
        meses_a_frente = st.slider("Meses à frente", min_value=1, max_value=18, value=6, key="diagonal_meses")

    limite = hoje + pd.DateOffset(months=meses_a_frente)
    filtrado = df[(df["periodo_fim"] >= hoje) & (df["periodo_inicio"] <= limite)].copy()
    if operadores:
        filtrado = filtrado[filtrado["operador"].isin(operadores)]

    if filtrado.empty:
        st.caption("Nenhum evento de indisponibilidade no período/filtro selecionado.")
        return

    # Uma linha por aeronave (não por operador+aeronave): as duas fontes às
    # vezes nomeiam o operador diferente pra mesma aeronave (ex.: Diagonal diz
    # "BABR", Disponibilidade Diária diz "6º ETA") — a matrícula é o dado que
    # não muda entre fontes, então é ela que decide a linha no gráfico.
    filtrado["aeronave_label"] = "FAB " + filtrado["aeronave"].astype(str)

    st.divider()
    st.caption(f"{filtrado['aeronave'].nunique()} aeronave(s) com indisponibilidade (real ou projetada) · {len(filtrado)} evento(s) na janela selecionada")

    ordem_y = sorted(filtrado["aeronave_label"].unique(), reverse=True)
    fig = px.timeline(
        filtrado, x_start="periodo_inicio", x_end="periodo_fim", y="aeronave_label",
        color="operador", color_discrete_sequence=CATEGORICA,
        pattern_shape="fonte", pattern_shape_map=PATTERN_FONTE,
        hover_data={"motivo": True, "confianca": True, "fonte": True, "operador": True, "aeronave_label": False},
        category_orders={"aeronave_label": ordem_y},
    )
    fig.add_vline(x=hoje, line_dash="dash", line_color=SECONDARY, annotation_text="hoje", annotation_position="top")
    fig.update_layout(xaxis_title="", yaxis_title="", legend_title="Operador")
    layout_grafico(fig, altura=max(280, 28 * filtrado["aeronave_label"].nunique()))
    st.plotly_chart(fig, width="stretch")
    st.caption("Listrado (╱) = projeção futura (Programado) · sólido = situação real de hoje.")

    st.divider()
    st.caption("Aeronaves indisponíveis por mês (soma de eventos na janela selecionada)")
    resumo = (
        filtrado.assign(mes=filtrado["periodo_inicio"].dt.to_period("M").dt.to_timestamp())
        .groupby("mes")["aeronave"].nunique().reset_index(name="qtd_aeronaves")
    )
    fig2 = px.bar(resumo, x="mes", y="qtd_aeronaves", color_discrete_sequence=[CATEGORICA[0]])
    fig2.update_layout(xaxis_title="", yaxis_title="Aeronaves")
    layout_grafico(fig2, altura=180)
    st.plotly_chart(fig2, width="stretch")

    st.divider()
    tabela = filtrado[["fonte", "operador", "aeronave", "periodo_inicio", "periodo_fim", "motivo", "confianca"]].rename(columns={
        "fonte": "Fonte", "operador": "Operador", "aeronave": "Aeronave", "periodo_inicio": "Início",
        "periodo_fim": "Fim", "motivo": "Motivo", "confianca": "Confiança",
    }).sort_values("Início")
    tabela = filtro_colunas(tabela, key_prefix="diagonal")
    st.caption(f"{len(tabela)} item(ns) após os filtros por coluna.")
    st.dataframe(tabela, hide_index=True, width="stretch")
