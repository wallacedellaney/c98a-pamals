"""Página "Análise de Período" — central dinâmica de análise sobre o
histórico diário de emergências (novas, concluídas, entraram/saíram de
atraso, mudança de estoque disponível). Pedido do Wallace em 2026-07-10.
Ver 00_Instrucoes/analise_periodo.md.

Reaproveita o histórico diário já existente (historico_emergencias.csv,
gravado desde 2026-07-06 dentro de extrair_emergencias.py) — nada de base
nova. Lógica de comparação em components/comparacao_periodo.py (sem
Streamlit, testável sozinha); esta página só monta a interface.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from contrato005.components.comparacao_periodo import (
    datas_disponiveis, diff_periodo, linha_do_tempo, periodo_anterior_equivalente,
)
from contrato005.components.paleta import AMBER, CATEGORICA, CYAN, LINE, PANEL, SECONDARY, STATUS, layout_grafico
from contrato005.components.utils import AVISO_MMAM_PREVIA, ordenar_unicos

NOMES_COLUNAS = {
    "numero_emergencia": "Emergência", "om": "Unidade", "matricula_aeronave": "Aeronave",
    "pn": "PN", "nomenclatura": "Nomenclatura", "situacao": "Status", "tpemg": "Tipo",
    "data_abertura": "Abertura", "prazo_entrega": "Prazo", "dpe": "DPE",
    "dias_atraso": "Dias de atraso", "estoque": "Estoque",
}
COLUNAS_TABELA = [
    "numero_emergencia", "tpemg", "matricula_aeronave", "pn", "situacao",
    "om", "prazo_entrega", "dias_atraso", "estoque",
]


def _fmt(d):
    return d.strftime("%d/%m")


def _card(col, titulo, atual, anterior, cor_quando_sobe):
    delta = (atual - anterior) if anterior is not None else None
    col.metric(
        titulo, atual,
        delta=delta if delta not in (None, 0) else (None if delta is None else "0"),
        delta_color=cor_quando_sobe,
    )


def _resumo_texto(resultado, data_inicio, data_fim):
    return (
        f"Resumo do período {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}:\n"
        f"- {len(resultado['novas'])} nova(s) emergência(s) aberta(s)\n"
        f"- {len(resultado['concluidas'])} emergência(s) concluída(s)/cancelada(s)\n"
        f"- {len(resultado['entraram_atraso'])} item(ns) entraram em atraso\n"
        f"- {len(resultado['sairam_atraso'])} item(ns) saíram do atraso\n"
        f"- {len(resultado['estoque_ficou_sem'])} item(ns) ficaram sem estoque disponível\n"
        f"- {len(resultado['estoque_passou_ter'])} item(ns) passaram a ter estoque disponível"
    )


def _narrativa_executiva(resultado, data_inicio, data_fim):
    n = {chave: len(df) for chave, df in resultado.items()}
    if not any(n.values()):
        return f"Nenhuma mudança relevante entre {_fmt(data_inicio)} e {_fmt(data_fim)}."

    frases = []
    if n["novas"] or n["concluidas"]:
        frases.append(
            f"foram abertas {n['novas']} emergência(s) nova(s) e concluídas/canceladas {n['concluidas']}"
        )
    if n["entraram_atraso"] or n["sairam_atraso"]:
        frases.append(
            f"{n['entraram_atraso']} item(ns) passaram a estar atrasado(s) e {n['sairam_atraso']} saíram do atraso"
        )
    if n["estoque_ficou_sem"] or n["estoque_passou_ter"]:
        frases.append(
            f"{n['estoque_ficou_sem']} item(ns) ficaram sem estoque disponível e {n['estoque_passou_ter']} passaram a ter"
        )
    corpo = "; ".join(frases)
    return f"Entre {_fmt(data_inicio)} e {_fmt(data_fim)}, {corpo}."


def _tabela_com_filtro(df, chave_prefixo, titulo, cor_borda):
    st.markdown(
        f'<div style="border-left:3px solid {cor_borda};padding-left:0.6rem;font-weight:700;">{titulo} ({len(df)})</div>',
        unsafe_allow_html=True,
    )
    if df.empty:
        st.caption("Nenhum item.")
        return
    tabela = df[[c for c in COLUNAS_TABELA if c in df.columns]].rename(columns=NOMES_COLUNAS)
    st.dataframe(tabela, hide_index=True, width="stretch", height=min(35 * (len(tabela) + 1) + 3, 260))


MESES_ABREV = ["", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def _grafico_linha_mensal(df, coluna_y, titulo_y, cor, sufixo="%", altura=220, faixa_y=None):
    fig = px.line(df, x="mes_label", y=coluna_y, markers=True, color_discrete_sequence=[cor])
    fig.update_traces(
        text=df[coluna_y].map(lambda v: f"{v:.1f}{sufixo}"), textposition="top center", mode="lines+markers+text",
    )
    media = df[coluna_y].mean()
    fig.add_hline(y=media, line_dash="dash", line_color=SECONDARY, annotation_text="média do ano")
    fig.update_layout(xaxis_title="", yaxis_title=titulo_y, yaxis_range=faixa_y)
    layout_grafico(fig, altura=altura)
    st.plotly_chart(fig, width="stretch")


def _secao_desempenho(dados):
    """Indicadores de desempenho da empresa ao longo do ano — pedido do
    Wallace em 2026-07-18: "coloca tb um historico da MMAM do ano de 2026
    e graficos de desempenho da empresa", depois "ficou ruim, deixa uma
    linha que vai mudando, melhore essa analise da empresa, coloca mais
    grafico" (trocado de barra pra linha, e adicionados 2 gráficos novos).
    3 indicadores, todos por mês de 2026:
    1. MMAM — lido do Cômputo Mensal já calculado (não recalcula nada).
    2. % de entregas no prazo — recalculado ao vivo a partir de
       emergencias_totais (mesma regra da aba Atrasos: dias_atraso <= 0 =
       no prazo), agrupado pelo mês de conclusão/cancelamento
       (`atendido_cancelado`) — dá pra fazer pra qualquer mês passado
       porque emergencias_totais já tem a data de cada emergência,
       diferente do MMAM que depende de um cálculo salvo por mês.
    3. Novas emergências abertas — contagem por mês de `data_abertura`,
       mesma fonte."""
    hist_mmam = dados.get("historico_mmam")
    df_totais = dados.get("emergencias_totais")
    if (hist_mmam is None or hist_mmam.empty) and (df_totais is None or df_totais.empty):
        return

    st.markdown("##### Desempenho da empresa — 2026")

    tem_algum_dado = False

    # 1) MMAM ------------------------------------------------------------
    if hist_mmam is not None and not hist_mmam.empty:
        hist_ano = hist_mmam[(hist_mmam["ano"] == 2026) & hist_mmam["mmam_previa"].notna()].copy()
        if not hist_ano.empty:
            tem_algum_dado = True
            hist_ano["mes_label"] = hist_ano["mes"].apply(lambda m: MESES_ABREV[m])
            st.caption(
                "**MMAM (Média Mensal de Aeronaves Montadas)** — prévia automática calculada pelo "
                "Cômputo Mensal (aba Fechamento Mensal, ver 00_Instrucoes/computo_mensal.md)."
            )
            c1, c2 = st.columns(2)
            c1.metric("MMAM médio no ano", f"{hist_ano['mmam_previa'].mean():.2f}%")
            c2.metric("Meses calculados", len(hist_ano))
            _grafico_linha_mensal(hist_ano, "mmam_previa", "MMAM (%)", AMBER, faixa_y=[0, 108])
            st.info(AVISO_MMAM_PREVIA)

    # 2) % de entregas no prazo e 3) novas emergências --------------------
    if df_totais is not None and not df_totais.empty:
        trabalho = df_totais.copy()
        trabalho["atendido_dt"] = pd.to_datetime(trabalho["atendido_cancelado"], errors="coerce")
        trabalho["abertura_dt"] = pd.to_datetime(trabalho["data_abertura"], errors="coerce")

        concluidas = trabalho[trabalho["atendido_dt"].notna() & (trabalho["atendido_dt"].dt.year == 2026)].copy()
        if not concluidas.empty:
            tem_algum_dado = True
            concluidas["mes"] = concluidas["atendido_dt"].dt.month
            resumo_prazo = concluidas.groupby("mes").apply(
                lambda g: pd.Series({
                    "total": len(g), "no_prazo": int((g["dias_atraso"] <= 0).sum()),
                }),
                include_groups=False,
            ).reset_index()
            resumo_prazo["pct_no_prazo"] = resumo_prazo["no_prazo"] / resumo_prazo["total"] * 100
            resumo_prazo["mes_label"] = resumo_prazo["mes"].apply(lambda m: MESES_ABREV[m])

            st.caption(
                "**% de entregas no prazo** — emergências concluídas/canceladas em cada mês com "
                "dias_atraso ≤ 0 no momento do atendimento (mesma regra da aba Atrasos)."
            )
            c1, c2 = st.columns(2)
            c1.metric("% no prazo médio no ano", f"{resumo_prazo['pct_no_prazo'].mean():.1f}%")
            c2.metric("Total de entregas no ano", int(resumo_prazo["total"].sum()))
            _grafico_linha_mensal(resumo_prazo, "pct_no_prazo", "% no prazo", STATUS["good"], faixa_y=[0, 108])

        abertas_2026 = trabalho[trabalho["abertura_dt"].notna() & (trabalho["abertura_dt"].dt.year == 2026)].copy()
        if not abertas_2026.empty:
            tem_algum_dado = True
            abertas_2026["mes"] = abertas_2026["abertura_dt"].dt.month
            resumo_novas = abertas_2026.groupby("mes").size().reset_index(name="qtd")
            resumo_novas["mes_label"] = resumo_novas["mes"].apply(lambda m: MESES_ABREV[m])

            st.caption("**Novas emergências abertas por mês** — todas as emergências VEE ONE, por data de abertura.")
            c1, c2 = st.columns(2)
            c1.metric("Média de novas por mês", f"{resumo_novas['qtd'].mean():.1f}")
            c2.metric("Total no ano", int(resumo_novas["qtd"].sum()))
            _grafico_linha_mensal(resumo_novas, "qtd", "Novas emergências", CYAN, sufixo="", faixa_y=None)

    if not tem_algum_dado:
        st.caption("Ainda sem dado de 2026 suficiente pra montar os gráficos de desempenho.")
    st.divider()


def render(dados):
    st.title("Análise de Período")
    st.caption(
        "Central de análise sobre o histórico diário de emergências (VEE ONE) — "
        "escolha o intervalo e veja o que mudou, comparado com o período equivalente anterior."
    )

    _secao_desempenho(dados)

    historico = dados.get("historico_emergencias")
    datas = datas_disponiveis(historico)
    if len(datas) < 2:
        st.info(
            "Ainda não há histórico suficiente pra comparar períodos — o histórico começou em "
            f"{datas[0].strftime('%d/%m/%Y') if datas else '—'} e cresce um dia por vez. Volte amanhã."
        )
        return

    # 1) Slider de período ---------------------------------------------------
    data_inicio, data_fim = st.select_slider(
        "Intervalo de análise",
        options=datas,
        value=(datas[0], datas[-1]),
        format_func=_fmt,
        key="analise_periodo_slider",
    )
    if data_inicio > data_fim:
        data_inicio, data_fim = data_fim, data_inicio
    st.caption(f"Período selecionado: **{_fmt(data_inicio)} a {_fmt(data_fim)}** ({len(datas)} dia(s) de histórico disponíveis no total)")

    resultado = diff_periodo(historico, data_inicio, data_fim)

    # 2) Comparação automática com o período anterior equivalente ------------
    inicio_ant, fim_ant = periodo_anterior_equivalente(datas, data_inicio, data_fim)
    resultado_anterior = diff_periodo(historico, inicio_ant, fim_ant) if inicio_ant else None
    if resultado_anterior:
        st.caption(f"Comparando com o período anterior equivalente: {_fmt(inicio_ant)} a {_fmt(fim_ant)}")
    else:
        st.caption("Período anterior equivalente ainda não tem histórico suficiente — mostrando só o período atual.")

    def _n(res, chave):
        return len(res[chave]) if res else None

    # 3) Cards -----------------------------------------------------------
    st.markdown("##### O que mudou")
    c1, c2, c3, c4, c5 = st.columns(5)
    _card(c1, "Novas emergências", len(resultado["novas"]), _n(resultado_anterior, "novas"), "off")
    _card(c2, "Concluídas", len(resultado["concluidas"]), _n(resultado_anterior, "concluidas"), "off")
    _card(c3, "Entraram em atraso", len(resultado["entraram_atraso"]), _n(resultado_anterior, "entraram_atraso"), "inverse")
    _card(c4, "Saíram do atraso", len(resultado["sairam_atraso"]), _n(resultado_anterior, "sairam_atraso"), "normal")
    with c5:
        st.metric(
            "Mudança de estoque",
            len(resultado["estoque_ficou_sem"]) + len(resultado["estoque_passou_ter"]),
        )
        st.caption(f"{len(resultado['estoque_ficou_sem'])} ficaram sem · {len(resultado['estoque_passou_ter'])} passaram a ter")

    st.divider()

    # 4) Gráfico de linha temporal ----------------------------------------
    st.markdown("##### Evolução diária no período")
    tl = linha_do_tempo(historico, data_inicio, data_fim)
    if tl.empty:
        st.info("Sem dados suficientes nesse intervalo.")
    else:
        fig = px.line(
            tl, x="data", y=["total_aberto", "total_atrasado"], markers=True,
            color_discrete_sequence=[AMBER, STATUS["critical"]],
        )
        fig.update_layout(
            yaxis_title="Quantidade", xaxis_title="", legend_title="",
        )
        fig.for_each_trace(lambda t: t.update(name={"total_aberto": "Em aberto", "total_atrasado": "Atrasadas"}.get(t.name, t.name)))
        layout_grafico(fig, altura=240)
        st.plotly_chart(fig, width="stretch")

    st.divider()

    # 5) "O que mudou?" — linguagem executiva -------------------------------
    st.markdown("##### O que mudou?")
    st.markdown(
        f'<div style="background:{PANEL};border:1px solid {LINE};border-left:3px solid {AMBER};'
        f'border-radius:8px;padding:0.9rem 1.1rem;font-size:0.95rem;">{_narrativa_executiva(resultado, data_inicio, data_fim)}</div>',
        unsafe_allow_html=True,
    )

    st.write("")
    if st.button("📋 Gerar resumo do período", key="analise_periodo_resumo"):
        st.code(_resumo_texto(resultado, data_inicio, data_fim), language=None)
        st.download_button(
            "⬇️ Baixar resumo (.txt)",
            _resumo_texto(resultado, data_inicio, data_fim).encode("utf-8"),
            file_name=f"resumo_{data_inicio}_{data_fim}.txt", mime="text/plain",
            key="analise_periodo_resumo_download",
        )

    st.divider()

    # 6) Detalhe por categoria ------------------------------------------
    st.markdown("##### Detalhe por categoria")
    aba_novas, aba_concluidas, aba_atraso_entrou, aba_atraso_saiu, aba_estoque = st.tabs([
        f"Novas ({len(resultado['novas'])})",
        f"Concluídas ({len(resultado['concluidas'])})",
        f"Entraram em atraso ({len(resultado['entraram_atraso'])})",
        f"Saíram do atraso ({len(resultado['sairam_atraso'])})",
        "Estoque",
    ])
    with aba_novas:
        _tabela_com_filtro(resultado["novas"], "novas", "Novas emergências", CYAN)
    with aba_concluidas:
        _tabela_com_filtro(resultado["concluidas"], "concluidas", "Concluídas/canceladas", STATUS["good"])
    with aba_atraso_entrou:
        _tabela_com_filtro(resultado["entraram_atraso"], "entrou", "Entraram em atraso", STATUS["critical"])
    with aba_atraso_saiu:
        _tabela_com_filtro(resultado["sairam_atraso"], "saiu", "Saíram do atraso", STATUS["good"])
    with aba_estoque:
        col_a, col_b = st.columns(2)
        with col_a:
            _tabela_com_filtro(resultado["estoque_ficou_sem"], "sem_estoque", "Ficaram sem estoque", STATUS["critical"])
        with col_b:
            _tabela_com_filtro(resultado["estoque_passou_ter"], "com_estoque", "Passaram a ter estoque", STATUS["good"])

    st.divider()

    # 7) Tabela dinâmica filtrável (situação no fim do período) ------------
    st.markdown(f"##### Tabela operacional — situação em {_fmt(data_fim)}")
    hist = historico.copy()
    hist["data_snapshot"] = pd.to_datetime(hist["data_snapshot"]).dt.date
    snapshot_fim = hist[hist["data_snapshot"] == data_fim]

    if snapshot_fim.empty:
        st.info("Sem dados nesse dia.")
        return

    c1, c2, c3, c4, c5 = st.columns(5)
    tipo_f = c1.multiselect("Tipo", ordenar_unicos(snapshot_fim["tpemg"]), key="analise_f_tipo")
    aeronave_f = c2.multiselect("Aeronave", ordenar_unicos(snapshot_fim["matricula_aeronave"]), key="analise_f_aeronave")
    pn_f = c3.multiselect("PN", ordenar_unicos(snapshot_fim["pn"]), key="analise_f_pn")
    status_f = c4.multiselect("Status", ordenar_unicos(snapshot_fim["situacao"]), key="analise_f_status")
    unidade_f = c5.multiselect("Unidade", ordenar_unicos(snapshot_fim["om"]), key="analise_f_unidade")

    if st.button("✕ Limpar filtros", key="analise_periodo_limpar"):
        for chave in ("analise_f_tipo", "analise_f_aeronave", "analise_f_pn", "analise_f_status", "analise_f_unidade"):
            st.session_state.pop(chave, None)
        st.rerun()

    filtrado = snapshot_fim.copy()
    if tipo_f:
        filtrado = filtrado[filtrado["tpemg"].isin(tipo_f)]
    if aeronave_f:
        filtrado = filtrado[filtrado["matricula_aeronave"].isin(aeronave_f)]
    if pn_f:
        filtrado = filtrado[filtrado["pn"].isin(pn_f)]
    if status_f:
        filtrado = filtrado[filtrado["situacao"].isin(status_f)]
    if unidade_f:
        filtrado = filtrado[filtrado["om"].isin(unidade_f)]

    st.caption(f"Exibindo {len(filtrado)} de {len(snapshot_fim)} emergências em aberto em {_fmt(data_fim)}")
    tabela = filtrado[[c for c in COLUNAS_TABELA if c in filtrado.columns]].rename(columns=NOMES_COLUNAS)
    st.dataframe(tabela, hide_index=True, width="stretch", height=min(35 * (len(tabela) + 1) + 3, 420))

    csv = tabela.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar (CSV)", csv, file_name=f"analise_periodo_{data_fim}.csv", mime="text/csv")
