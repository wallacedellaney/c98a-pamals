"""Dashboard geral — visão gerencial combinando RAC (configuração das
aeronaves) e Disponibilidade Diária (situação operacional do dia), pensada
pras informações que mais importam pra um gestor: quanto da frota está
pronta, o que está travando, e o que mudou.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from coordenadoria.components.paleta import (
    AMBER, CYAN, INK, LINE, PANEL, SECONDARY, STATUS, COR_SITUACAO, layout_grafico,
)
from coordenadoria.secoes.disponibilidade_diaria import ORDEM_SITUACAO, classificar_alerta


def render(dados):
    _estilo()
    st.title("Dashboard")
    st.caption(
        "Visão gerencial da frota C-98 — configuração (RAC), situação operacional do dia "
        "(Disponibilidade Diária), vencimentos e diagonal de manutenção num só lugar."
    )

    aeronaves = dados["rac_aeronaves"]
    pendencias = dados["rac_pendencias"]
    disp_relatorios = dados["disp_relatorios"]
    disp_aeronaves = dados["disp_aeronaves"]
    venc_tmot = dados.get("venc_tmot")
    venc_operadores = dados.get("venc_operadores")
    diagonal = dados.get("diagonal")

    rel_hoje = None
    aer_hoje = pd.DataFrame()
    if not disp_relatorios.empty:
        data_mais_recente = disp_relatorios["data_referencia"].max()
        rel_hoje = disp_relatorios[disp_relatorios["data_referencia"] == data_mais_recente].iloc[0]
        aer_hoje = disp_aeronaves[disp_aeronaves["data_referencia"] == data_mais_recente].copy()
        aer_hoje["_alerta"] = aer_hoje.apply(classificar_alerta, axis=1)

    _cards_indicadores(aeronaves, pendencias, rel_hoje, aer_hoje)

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        _config_frota(aeronaves)
        if st.button("🛩️ Ver RAC completo →", key="dash_ir_rac", width="stretch"):
            st.session_state["coord_pagina"] = "RAC"
            st.rerun()
    with col2:
        _situacao_hoje(aer_hoje, rel_hoje)
        if st.button("📋 Ver Disponibilidade Diária completa →", key="dash_ir_disp", width="stretch"):
            st.session_state["coord_pagina"] = "Disponibilidade Diária"
            st.rerun()

    st.divider()
    st.markdown("##### Vencimentos e Diagonal de Manutenção")
    col3, col4 = st.columns(2)
    with col3:
        _card_vencimentos(venc_tmot, venc_operadores)
        if st.button("📆 Ver Vencimentos →", key="dash_ir_venc", width="stretch"):
            st.session_state["coord_pagina"] = "Vencimentos"
            st.rerun()
    with col4:
        _card_diagonal(diagonal)
        if st.button("🗓️ Ver Diagonal de Manutenção →", key="dash_ir_diagonal", width="stretch"):
            st.session_state["coord_pagina"] = "Diagonal de Manutenção"
            st.rerun()

    st.divider()
    _pontos_atencao(aeronaves, pendencias, aer_hoje, rel_hoje, venc_tmot, venc_operadores, diagonal)


def _estilo():
    st.markdown(
        f"""<style>
.dash-card {{
    background: {PANEL};
    border: 1px solid {LINE};
    border-radius: 10px;
    padding: 0.9rem 1rem;
    box-shadow: 0 2px 6px rgba(0,0,0,0.25);
}}
.dash-card .valor {{ font-size: 2.1rem; font-weight: 800; }}
.dash-card .label {{ font-size: 1rem; color: {INK}; margin-top: 0.35rem; font-weight: 700; }}
.dash-card .sub {{ font-size: 0.85rem; color: {SECONDARY}; margin-top: 0.15rem; }}
.dash-painel {{
    background: {PANEL};
    border: 1px solid {LINE};
    border-left: 3px solid {AMBER};
    border-radius: 10px;
    padding: 0.7rem 1.1rem;
}}
.dash-item {{
    padding: 0.5rem 0;
    border-bottom: 1px solid {LINE};
    font-size: 0.92rem;
}}
.dash-item:last-child {{ border-bottom: none; }}
</style>""",
        unsafe_allow_html=True,
    )


def _card(col, valor, label, sub, cor):
    with col:
        st.markdown(
            f'<div class="dash-card"><div class="valor" style="color:{cor};">{valor}</div>'
            f'<div class="label">{label}</div><div class="sub">{sub}</div></div>',
            unsafe_allow_html=True,
        )


def _cards_indicadores(aeronaves, pendencias, rel_hoje, aer_hoje):
    total = len(aeronaves)
    fora_contrato = int((aeronaves["contrato"] == "Fora do contrato").sum())
    sem_condicoes = int((aeronaves["disponibilidade"] == "Sem condições").sum())
    unidades_faltantes = int(aeronaves["soma_unidades_faltantes"].sum())

    l1 = st.columns(4)
    _card(l1[0], total, "Frota total", "cadastradas no RAC", INK)
    if rel_hoje is not None:
        disponiveis = int(rel_hoje["disponiveis_hoje"])
        montadas = int(rel_hoje["montadas_hoje"])
        pct_disp = round(100 * disponiveis / montadas) if montadas else 0
        _card(l1[1], disponiveis, "Disponíveis hoje", "DI + DO (Disp. Diária)", STATUS["good"])
        _card(l1[2], montadas, "Montadas hoje", "sem AIFP/IPLR (Disp. Diária)", CYAN)
        _card(l1[3], f"{pct_disp}%", "% disponibilidade", f"{disponiveis} de {montadas} montadas", AMBER)
    else:
        _card(l1[1], "—", "Disponíveis hoje", "sem dados de Disponibilidade Diária", SECONDARY)
        _card(l1[2], "—", "Montadas hoje", "sem dados de Disponibilidade Diária", SECONDARY)
        _card(l1[3], "—", "% disponibilidade", "", SECONDARY)

    l2 = st.columns(4)
    _card(l2[0], fora_contrato, "Fora do contrato", "RAC", STATUS["critical"] if fora_contrato else STATUS["good"])
    _card(l2[1], sem_condicoes, "Sem condições", "RAC — acidentadas/estocadas", STATUS["critical"] if sem_condicoes else STATUS["good"])
    _card(l2[2], unidades_faltantes, "Unidades faltantes", "RAC — total de peças em falta", AMBER if unidades_faltantes else STATUS["good"])
    if aer_hoje is not None and not aer_hoje.empty:
        criticos = int((aer_hoje["_alerta"] == "critico").sum())
        _card(l2[3], criticos, "Alertas críticos hoje", "Disponibilidade Diária", STATUS["critical"] if criticos else STATUS["good"])
    else:
        _card(l2[3], "—", "Alertas críticos hoje", "sem dados de Disponibilidade Diária", SECONDARY)


def _card_vencimentos(venc_tmot, venc_operadores):
    vencidos_tmot = int(venc_tmot["vencido"].sum()) if venc_tmot is not None and not venc_tmot.empty else 0
    vencidos_operadores = (
        int(venc_operadores["vencido"].sum()) if venc_operadores is not None and not venc_operadores.empty else 0
    )
    total_vencidos = vencidos_tmot + vencidos_operadores

    st.markdown("###### Vencimentos")
    c1, c2, c3 = st.columns(3)
    _card(c1, total_vencidos, "Total vencido", "TMOT + Operadores", STATUS["critical"] if total_vencidos else STATUS["good"])
    _card(c2, vencidos_tmot, "TMOT", "", STATUS["critical"] if vencidos_tmot else STATUS["good"])
    _card(c3, vencidos_operadores, "Operadores", "", STATUS["critical"] if vencidos_operadores else STATUS["good"])


def _card_diagonal(diagonal):
    st.markdown("###### Diagonal de Manutenção")
    if diagonal is not None and not diagonal.empty:
        hoje = pd.Timestamp.now().normalize()
        indisponiveis_agora = diagonal[(diagonal["periodo_inicio"] <= hoje) & (diagonal["periodo_fim"] >= hoje)]
        aeronaves_diagonal = indisponiveis_agora["aeronave"].nunique()
        c1, c2 = st.columns(2)
        _card(c1, aeronaves_diagonal, "Indisponíveis hoje", "projeção", STATUS["critical"] if aeronaves_diagonal else STATUS["good"])
        _card(c2, diagonal["aeronave"].nunique(), "Aeronaves na diagonal", "total com período projetado", INK)
    else:
        st.caption("Sem dados de Diagonal de Manutenção ainda.")


def _config_frota(aeronaves):
    st.markdown("##### Configuração da frota (RAC)")
    contagem = (
        aeronaves["disponibilidade"].value_counts()
        .reindex(["Montada", "Desmontada", "Sem condições"]).fillna(0).reset_index()
    )
    contagem.columns = ["situacao", "quantidade"]
    fig = px.pie(
        contagem, names="situacao", values="quantidade", hole=0.55,
        color="situacao",
        color_discrete_map={"Montada": STATUS["good"], "Desmontada": AMBER, "Sem condições": STATUS["critical"]},
    )
    fig.update_traces(textinfo="value+percent", textfont_size=11)
    layout_grafico(fig, altura=240)
    st.plotly_chart(fig, width="stretch")
    st.caption("Baseado em pendências de material cadastradas no RAC — não muda dia a dia.")


def _situacao_hoje(aer_hoje, rel_hoje):
    st.markdown("##### Situação operacional hoje (Disponibilidade Diária)")
    if aer_hoje is None or aer_hoje.empty:
        st.caption("Nenhum relatório de Disponibilidade Diária carregado ainda.")
        return
    contagem = aer_hoje["situacao"].value_counts().reindex(ORDEM_SITUACAO).fillna(0).reset_index()
    contagem.columns = ["situacao", "quantidade"]
    fig = px.bar(
        contagem, x="quantidade", y="situacao", orientation="h",
        color="situacao", color_discrete_map=COR_SITUACAO,
    )
    fig.update_layout(yaxis_title="", xaxis_title="", showlegend=False,
                       yaxis={"categoryorder": "array", "categoryarray": ORDEM_SITUACAO[::-1], "type": "category"})
    layout_grafico(fig, altura=240)
    st.plotly_chart(fig, width="stretch")
    data_txt = rel_hoje["data_referencia"].strftime("%d/%m/%Y")
    st.caption(f"Relatório de {data_txt} — DI/DO disponível, demais códigos indisponível por algum motivo.")


def _pontos_atencao(aeronaves, pendencias, aer_hoje, rel_hoje, venc_tmot=None, venc_operadores=None, diagonal=None):
    st.markdown("##### Pontos de atenção")
    itens = []

    sem_condicoes = aeronaves[aeronaves["disponibilidade"] == "Sem condições"]
    if len(sem_condicoes):
        matriculas = ", ".join(f"FAB {m}" for m in sem_condicoes["matricula"])
        itens.append(f"⛔ RAC: {len(sem_condicoes)} aeronave(s) sem condições: {matriculas}.")

    top_aer = aeronaves.sort_values("soma_unidades_faltantes", ascending=False).head(3)
    for _, row in top_aer.iterrows():
        if row["soma_unidades_faltantes"] > 0:
            itens.append(
                f"🛠️ RAC: FAB {row['matricula']} possui {int(row['soma_unidades_faltantes'])} unidades "
                f"faltantes ({int(row['total_pendencias'])} PNs)."
            )

    if not pendencias.empty:
        top_pn = pendencias.groupby(["pn", "nomenclatura"])["matricula"].nunique().sort_values(ascending=False)
        if len(top_pn) and top_pn.iloc[0] > 1:
            pn, nome = top_pn.index[0]
            itens.append(f"🔩 RAC: PN {pn} ({nome}) afeta {top_pn.iloc[0]} aeronaves.")

    if aer_hoje is not None and not aer_hoje.empty:
        criticos = aer_hoje[aer_hoje["_alerta"] == "critico"]
        if len(criticos):
            matriculas = ", ".join(f"FAB {m}" for m in criticos["matricula"])
            itens.append(f"🚨 Disp. Diária: {len(criticos)} aeronave(s) em alerta crítico hoje: {matriculas}.")
        if rel_hoje is not None and rel_hoje["previsao_semana_disponiveis_qtd"] > rel_hoje["disponiveis_hoje"]:
            delta = int(rel_hoje["previsao_semana_disponiveis_qtd"] - rel_hoje["disponiveis_hoje"])
            itens.append(f"📈 Disp. Diária: previsão de +{delta} disponíveis até o fim da semana.")

    if venc_tmot is not None and not venc_tmot.empty:
        vencidos_tmot = int(venc_tmot["vencido"].sum())
        if vencidos_tmot:
            itens.append(f"📆 Vencimentos (TMOT): {vencidos_tmot} item(ns) já vencido(s).")
    if venc_operadores is not None and not venc_operadores.empty:
        vencidos_op = int(venc_operadores["vencido"].sum())
        if vencidos_op:
            itens.append(f"📆 Vencimentos (Operadores): {vencidos_op} item(ns) já vencido(s).")

    if diagonal is not None and not diagonal.empty:
        hoje_ts = pd.Timestamp.now().normalize()
        indisponiveis_agora = diagonal[(diagonal["periodo_inicio"] <= hoje_ts) & (diagonal["periodo_fim"] >= hoje_ts)]
        n_diagonal = indisponiveis_agora["aeronave"].nunique()
        if n_diagonal:
            aeronaves_diag = ", ".join(f"FAB {a}" for a in sorted(indisponiveis_agora["aeronave"].unique()))
            itens.append(f"🗓️ Diagonal de Manutenção: {n_diagonal} aeronave(s) indisponível(is) hoje: {aeronaves_diag}.")

    if not itens:
        st.markdown(
            '<div class="dash-painel"><div class="dash-item">✅ Nenhum ponto de atenção — frota regular.</div></div>',
            unsafe_allow_html=True,
        )
        return

    html = "".join(f'<div class="dash-item">{item}</div>' for item in itens)
    st.markdown(f'<div class="dash-painel">{html}</div>', unsafe_allow_html=True)
