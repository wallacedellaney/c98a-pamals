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
from coordenadoria.components.paleta import AMBER, CATEGORICA, CYAN, INK, LINE, PANEL, SECONDARY, layout_grafico
from coordenadoria.utils import atualizar_dados_diagonal_manutencao

FONTE_REAL = "Real (hoje)"
FONTE_PROGRAMADO = "Programado"
FONTE_AJUSTADO = "Programado (ajustado)"
FONTE_MOTOR = "Motor (planilha)"
PATTERN_FONTE = {FONTE_REAL: "", FONTE_PROGRAMADO: "/", FONTE_AJUSTADO: "x"}
COR_OPERADOR_MOTOR = {"TBO": AMBER, "HSI": CYAN, "Simulação": CATEGORICA[2]}

# Frota "dentro do contrato" — pré-selecionada por padrão no filtro de
# Aeronave (pedido do Wallace em 2026-07-14), pra não precisar marcar toda
# vez; continua editável (dá pra tirar/incluir depois, é só o valor
# inicial). Ver 00_Instrucoes/computo_mensal.md pra aeronaves fora do
# contrato (2726, 2730, 2732, 2734) e sem condições (2701, 2706, 2724),
# que ficam de fora dessa lista de propósito.
AERONAVES_PADRAO = {
    "2702", "2703", "2704", "2708", "2709", "2720", "2719", "2721", "2722", "2723",
    "2727", "2728", "2729", "2731", "2733", "2736", "2737", "2738", "2739", "2740",
    "2741", "2742", "2743",
}


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


EVENTOS_TBO_HSI_MOTOR = {"TBO", "TBO*", "HSI"}


def _eventos_motor(motores_diagonal):
    """Eventos de TBO/HSI vindos da planilha de Motores (Diagonal Nova) —
    aparecem direto na Diagonal de Manutenção das aeronaves, sempre a
    partir da fonte fixa (não a simulação). Pedido do Wallace em
    2026-07-15: "essas informacoes sao sempre vinculada com a planilha de
    motores" + "colocar um quadradinho escrito dentro hsi ou tbo pra
    visualização" — por isso o texto "TBO"/"HSI" vai escrito dentro da
    própria barra (`texto_evento`), e a cor segue o tipo de evento (âmbar/
    ciano), não o operador. Ver 00_Instrucoes/motores.md."""
    colunas = ["operador", "aeronave", "periodo_inicio", "periodo_fim", "motivo", "confianca", "fonte", "texto_evento"]
    if motores_diagonal is None or motores_diagonal.empty:
        return pd.DataFrame(columns=colunas)

    eventos = motores_diagonal[motores_diagonal["evento"].isin(EVENTOS_TBO_HSI_MOTOR)].copy()
    # ANV vazio na fonte (célula `False`) sobrevive ao ida-e-volta pelo
    # Excel como 0 — nenhuma aeronave da frota tem matrícula 0, então é
    # seguro tratar como "sem aeronave vinculada" e descartar.
    eventos = eventos[eventos["anv"].apply(lambda v: pd.notna(v) and v is not False and v != 0)]
    if eventos.empty:
        return pd.DataFrame(columns=colunas)

    eventos["periodo_inicio"] = pd.to_datetime(dict(year=eventos["ano"], month=eventos["mes"], day=1))
    eventos["periodo_fim"] = eventos["periodo_inicio"] + pd.DateOffset(months=1) - pd.Timedelta(days=1)
    eventos["aeronave"] = eventos["anv"].astype(int).astype(str)
    eventos["texto_evento"] = eventos["evento"].str.rstrip("*")
    eventos["operador"] = eventos["texto_evento"]
    eventos["motivo"] = eventos.apply(
        lambda r: f"Motor SN {r['serial']} — {r['evento']}" + (f": {r['comentario']}" if pd.notna(r["comentario"]) else ""),
        axis=1,
    )
    eventos["confianca"] = "Motores (planilha)"
    eventos["fonte"] = FONTE_MOTOR
    return eventos[colunas]


def _dados_motor_aeronave(aeronave, diagonal_meta, situacao):
    """Motor(es) vinculado(s) a uma aeronave — cruza pelo ANV da Diagonal
    Nova (metadados de planejamento: Hr disponível, Voo mensal, Mês
    disponível), com condição/%TBO voada vindo da Situação (SILOMS) via SN.
    Ver 00_Instrucoes/motores.md."""
    if diagonal_meta is None or diagonal_meta.empty:
        return []
    try:
        anv_num = float(aeronave)
    except (TypeError, ValueError):
        return []
    linhas = diagonal_meta[diagonal_meta["anv"] == anv_num]
    resultado = []
    for _, meta in linhas.iterrows():
        sit = situacao[situacao["sn"] == meta["serial"]] if situacao is not None and not situacao.empty else pd.DataFrame()
        resultado.append({
            "serial": meta["serial"],
            "hr_disp": meta["hr_disp"],
            "voo_mensal": meta["voo_mensal"],
            "mes_disp": meta["mes_disp"],
            "condicao": sit.iloc[0]["condicao"] if not sit.empty else None,
            "pct_tbo_voada": sit.iloc[0]["pct_tbo_voada"] if not sit.empty else None,
        })
    return resultado


def _rotulo_motor(aeronave, diagonal_meta, situacao):
    """Resumo curto do motor pra escrever direto no rótulo da aeronave no
    Gantt (pedido do Wallace em 2026-07-15: "ta dificil de ver a
    informacao do motor na diagonal geral, deixa de forma mais visivel,
    escreve la") — sem precisar abrir o expander pra ver o básico (SN e
    %TBO); o expander continua só pra simular horas de voo."""
    motores_aer = _dados_motor_aeronave(aeronave, diagonal_meta, situacao)
    if not motores_aer:
        return "sem motor vinculado"
    partes = []
    for m in motores_aer:
        if pd.notna(m["pct_tbo_voada"]):
            partes.append(f"SN {m['serial']} ({m['pct_tbo_voada']:.0f}% TBO)")
        else:
            partes.append(f"SN {m['serial']}")
    return " · ".join(partes)


def _secao_motores_por_aeronave(aeronaves, diagonal_meta, situacao, hoje):
    """Painel discreto — 1 expander por aeronave (colapsado por padrão),
    mostrando o motor vinculado + um campo editável de "Voo mensal" pra
    simular "e se eu voar mais/menos por mês". Pedido do Wallace em
    2026-07-15: "inserir de forma inteligente essas informacoes de motor
    la na diagonal das aeronaves, de forma discreta ... insere tb uma
    forma ... da media mensal de horas de voo por aeronave, no qual eu
    consiga clicar e se eu alterar ali, ajeita a possicao ... na diagonal
    geral" — a planilha de Motores (Diagonal Nova) continua sempre fixa,
    só essa simulação aqui é editável (não grava em nenhum arquivo).

    2026-07-15: o painel inteiro virou um único expander fechado por
    padrão (pedido do Wallace: "deixa ele minimizado, ai quando clicar que
    aparece as aeronaves para simular") — antes cada aeronave já aparecia
    aberta na tela; agora só a lista de aeronaves aparece depois de abrir
    o expander de fora."""
    with st.expander("🔧 Simulador de horas de voo por aeronave"):
        if diagonal_meta is None or diagonal_meta.empty:
            st.caption('Sem dados de motor carregados — ver página "Motores".')
            return []

        eventos_ajustados = []
        cols = st.columns(3)
        for i, aeronave in enumerate(aeronaves):
            motores_aer = _dados_motor_aeronave(aeronave, diagonal_meta, situacao)
            with cols[i % 3]:
                with st.expander(f"🔧 FAB {aeronave}"):
                    if not motores_aer:
                        st.caption("Sem motor vinculado nos dados de planejamento (Diagonal Nova).")
                        continue
                    for m in motores_aer:
                        pct_txt = f" · {m['pct_tbo_voada']:.0f}% TBO voada" if pd.notna(m["pct_tbo_voada"]) else ""
                        st.caption(f"SN {m['serial']} — {m['condicao'] or '—'}{pct_txt}")
                        if pd.isna(m["voo_mensal"]) or pd.isna(m["hr_disp"]):
                            st.caption("Sem dado de planejamento (Voo mensal/Hr disponível) pra esse motor.")
                            continue
                        st.caption(
                            f"Voo mensal atual: {m['voo_mensal']:.1f} h/mês · Hr disponível: {m['hr_disp']:.0f} h · "
                            f"Previsão original: {m['mes_disp']:.1f} mês(es)"
                        )
                        novo_voo = st.number_input(
                            "Simular horas de voo por mês", min_value=1.0, value=float(m["voo_mensal"]), step=1.0,
                            key=f"diagonal_voo_mensal_{aeronave}_{m['serial']}",
                        )
                        if abs(novo_voo - m["voo_mensal"]) > 0.01:
                            novos_meses = m["hr_disp"] / novo_voo
                            nova_data = hoje + pd.DateOffset(days=round(novos_meses * 30.44))
                            st.info(
                                f"Nova previsão: **{novos_meses:.1f} mês(es)** → ~{nova_data.strftime('%d/%m/%Y')} "
                                f"(original: {m['mes_disp']:.1f} mês(es))"
                            )
                            eventos_ajustados.append({
                                "operador": "Simulação", "aeronave": aeronave,
                                "periodo_inicio": hoje, "periodo_fim": nova_data,
                                "motivo": f"TBO/HSI ajustado (SN {m['serial']}): {novo_voo:.0f}h/mês simulado (original {m['voo_mensal']:.0f}h/mês)",
                                "confianca": "Simulado", "fonte": FONTE_AJUSTADO,
                            })
        return eventos_ajustados


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
    df_motor = _eventos_motor(dados.get("motores_diagonal"))
    df = pd.concat([df_real, df_programado, df_motor], ignore_index=True)
    df["texto_evento"] = df["texto_evento"].fillna("") if "texto_evento" in df.columns else ""
    # aeronave precisa ser sempre string — as 3 fontes guardam tipos
    # diferentes (int/float/str), e misturado isso faz o .unique() tratar
    # 2722 (int) e "2722" (str) como valores diferentes, duplicando a
    # aeronave nos filtros/expanders mais adiante.
    def _aeronave_str(v):
        if pd.isna(v):
            return None
        return str(int(v)) if isinstance(v, float) and float(v).is_integer() else str(v)
    df["aeronave"] = df["aeronave"].apply(_aeronave_str)

    if df.empty:
        st.info("Nenhum dado carregado ainda. Peça ao Claude para buscar a Diagonal de Manutenção de cada operador.")
        return

    if dados["diagonal_atualizado_em"]:
        atualizado = datetime.fromtimestamp(dados["diagonal_atualizado_em"]).strftime("%d/%m/%Y %H:%M")
        st.caption(f"Última atualização dos dados (Diagonal): **{atualizado}**")
    if not df_real.empty:
        st.caption(f"Situação real de hoje: **{df_real['periodo_inicio'].max().strftime('%d/%m/%Y')}** ({len(df_real)} aeronave(s) indisponível(is) no último relatório de Disponibilidade Diária)")

    hoje = pd.Timestamp.now().normalize()

    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        operadores = st.multiselect("Operador", sorted(df["operador"].unique()), key="diagonal_filtro_operador")
    with c2:
        opcoes_aeronave = sorted(df["aeronave"].dropna().unique(), key=str)
        padrao_aeronave = [a for a in opcoes_aeronave if str(a) in AERONAVES_PADRAO]
        aeronaves_f = st.multiselect(
            "Aeronave", opcoes_aeronave, default=padrao_aeronave, key="diagonal_filtro_aeronave"
        )
    with c3:
        meses_a_frente = st.slider("Meses à frente", min_value=1, max_value=18, value=6, key="diagonal_meses")

    limite = hoje + pd.DateOffset(months=meses_a_frente)
    filtrado = df[(df["periodo_fim"] >= hoje) & (df["periodo_inicio"] <= limite)].copy()
    if operadores:
        filtrado = filtrado[filtrado["operador"].isin(operadores)]
    if aeronaves_f:
        filtrado = filtrado[filtrado["aeronave"].isin(aeronaves_f)]

    if filtrado.empty:
        st.caption("Nenhum evento de indisponibilidade no período/filtro selecionado.")
        return

    diagonal_meta = dados.get("motores_diagonal_meta")
    situacao_motores = dados.get("motores_situacao")

    st.divider()
    aeronaves_no_filtro = sorted(filtrado["aeronave"].dropna().unique(), key=str)
    eventos_ajustados = _secao_motores_por_aeronave(aeronaves_no_filtro, diagonal_meta, situacao_motores, hoje)
    if eventos_ajustados:
        filtrado = pd.concat([filtrado, pd.DataFrame(eventos_ajustados)], ignore_index=True)

    # Uma linha por aeronave (não por operador+aeronave): as duas fontes às
    # vezes nomeiam o operador diferente pra mesma aeronave (ex.: Diagonal diz
    # "BABR", Disponibilidade Diária diz "6º ETA") — a matrícula é o dado que
    # não muda entre fontes, então é ela que decide a linha no gráfico.
    # O rótulo já traz o motor (SN + %TBO) escrito direto — pedido do
    # Wallace em 2026-07-15, "escreve la" — sem precisar clicar em nada.
    mapa_rotulo_motor = {
        a: _rotulo_motor(a, diagonal_meta, situacao_motores) for a in filtrado["aeronave"].dropna().unique()
    }
    filtrado["aeronave_label"] = (
        "FAB " + filtrado["aeronave"].astype(str) + " — " + filtrado["aeronave"].map(mapa_rotulo_motor)
    )

    st.divider()
    st.caption(f"{filtrado['aeronave'].nunique()} aeronave(s) com indisponibilidade (real ou projetada) · {len(filtrado)} evento(s) na janela selecionada")

    # Eventos de motor (TBO/HSI) não viram barra de mês inteiro — geralmente
    # tem troca de motor no meio do período, então a barra mentiria sobre a
    # duração. Pedido do Wallace em 2026-07-15: "coloca so o ponto de
    # inicio, nao coloca o mes inteiro ... e so para estar escrito tbo ou
    # hsi msm, sem linha pontinha ou bolinha" — só o texto "TBO"/"HSI"
    # marcado no ponto de início, sem barra/marcador de forma nenhuma.
    barras = filtrado[filtrado["fonte"] != FONTE_MOTOR].copy()
    pontos_motor = filtrado[filtrado["fonte"] == FONTE_MOTOR].copy()

    ordem_y = sorted(filtrado["aeronave_label"].unique(), reverse=True)
    fig = px.timeline(
        barras, x_start="periodo_inicio", x_end="periodo_fim", y="aeronave_label",
        color="operador", color_discrete_map=COR_OPERADOR_MOTOR, color_discrete_sequence=CATEGORICA,
        pattern_shape="fonte", pattern_shape_map=PATTERN_FONTE,
        hover_data={"motivo": True, "confianca": True, "fonte": True, "operador": True, "aeronave_label": False},
        category_orders={"aeronave_label": ordem_y},
    )
    for evento_tipo, cor in (("TBO", AMBER), ("HSI", CYAN)):
        pontos = pontos_motor[pontos_motor["texto_evento"] == evento_tipo]
        if pontos.empty:
            continue
        fig.add_scatter(
            x=pontos["periodo_inicio"], y=pontos["aeronave_label"], mode="text",
            text=pontos["texto_evento"], textposition="middle right",
            textfont=dict(color=cor, size=11, family="Arial Black"),
            hovertext=pontos["motivo"], hoverinfo="text", showlegend=False, name=evento_tipo,
        )
    fig.add_vline(x=hoje, line_dash="dash", line_color=SECONDARY, annotation_text="hoje", annotation_position="top")
    fig.update_layout(xaxis_title="", yaxis_title="", legend_title="Operador")
    layout_grafico(fig, altura=max(280, 28 * filtrado["aeronave_label"].nunique()))
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Listrado (╱) = projeção futura (Programado) · sólido = situação real de hoje · "
        "\"TBO\"/\"HSI\" escrito (âmbar/ciano), sem barra, marca só o início do mês previsto "
        "pela planilha de Motores (a barra inteira enganaria, geralmente troca de motor no meio) · "
        "xadrez (╳), operador \"Simulação\" = previsão recalculada com as horas de voo ajustadas "
        "no painel \"🔧 Simulador\" acima."
    )

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
