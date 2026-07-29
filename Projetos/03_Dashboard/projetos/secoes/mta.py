"""Dashboard do projeto MTA — Acompanhamento e Solicitações, filtrado por
C-98. Ver 00_Instrucoes/mta.md.

Nota sobre a coluna "Para Contrato": na planilha real ela não tem Sim/Não
(só "Para Motores" tem) — guarda um texto de categoria (REQUISIÇÃO, SOB
DEMANDA, HORA DE VOO, PARCELA FIXA). Decisão do Wallace (2026-07-09): manter
o texto como está e mostrar a quebra por categoria, em vez de forçar um
indicador Sim/Não que a planilha não tem.

Redesenho visual completo em 2026-07-09 (tema centralizado em
projetos/components/paleta.py) — ordem da página: cabeçalho, filtros,
indicadores, situação das solicitações, análise financeira, tabela.
"""

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from shared import horario
from projetos.components.atualizacao import botao_atualizar, status_atualizacao_html
from projetos.components.evolucao import secao_evolucao
from projetos.components.filtros import filtro_colunas
from projetos.components.paleta import (
    CATEGORICA, COR_SITUACAO_MTA, INK, LINE, PANEL, SECONDARY, STATUS,
    PRIMARY as AMBER,
    cabecalho_pagina, cartao_indicador, grade_indicadores, layout_grafico, moeda_compacta, moeda_completa,
)
from projetos.regras.mta_regras import normalizar

MESES_ABREV = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

COLUNAS_TABELA = [
    "linha", "situacao_consolidada", "aprovado", "tramite", "data_pedido", "digito",
    "rodada", "preenchimento_tgco", "atividade", "tarefa", "valor", "executora",
    "pacote", "para_contrato", "para_motores", "mes_previsto",
]
NOMES_COLUNAS = {
    "linha": "Linha", "situacao_consolidada": "Situação consolidada", "aprovado": "Aprovado",
    "tramite": "Trâmite", "data_pedido": "Data do pedido", "digito": "Dígito",
    "rodada": "Rodada de atendimento", "preenchimento_tgco": "Preenchimento da TGCO",
    "atividade": "Atividade", "tarefa": "Tarefa", "valor": "Valor", "executora": "Executora",
    "pacote": "Pacote", "para_contrato": "Para Contrato", "para_motores": "Para Motores",
    "mes_previsto": "Mês previsto",
}
NOMES_CAMPOS_DETALHE = {
    "linha": "Linha", "projeto_coordenador": "Projeto (bloco coordenador)",
    "projeto_atividade": "Projeto (bloco atividade)", "situacao_consolidada": "Situação consolidada",
    "aprovado": "Aprovado", "acao": "Ação", "tramite": "Trâmite", "data_pedido": "Data do pedido",
    "digito": "Dígito", "rodada": "Rodada de atendimento", "preenchimento_tgco": "Preenchimento da TGCO",
    "observacao_coordenador": "Observação do coordenador", "impactos_nao_atendimento": "Impactos do não atendimento",
    "atividade": "Atividade", "tarefa": "Tarefa", "valor": "Valor", "executora": "Executora", "nd": "ND",
    "pacote": "Pacote", "para_contrato": "Para Contrato", "para_motores": "Para Motores",
    "mes_previsto": "Mês previsto",
}


def _mes_ano(periodo_str):
    ano, mes = periodo_str.split("-")
    return f"{MESES_ABREV[int(mes) - 1]}/{ano}"


def _categoria_destinacao(row):
    if normalizar(row["para_motores"]) == "SIM":
        return "Motores"
    if row["para_contrato"]:
        return row["para_contrato"].title()
    return "Sem categoria"


def _rotular_barras(fig, valores):
    fig.update_traces(text=[moeda_compacta(v) for v in valores], texttemplate="%{text}",
                       textposition="outside", cliponaxis=False)
    return fig


def _atualizar():
    from projetos.data.atualizar_drive import atualizar_fonte
    return atualizar_fonte("mta")


def _filtros(df):
    st.markdown('<div class="pj-titulo-secao">Filtros</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        situacao_f = st.multiselect("Situação consolidada", sorted(df["situacao_consolidada"].dropna().unique()), key="mta_f_situacao")
    with c2:
        executora_f = st.multiselect("Executora", sorted(df["executora"].dropna().unique()), key="mta_f_executora")
    with c3:
        pacote_f = st.multiselect("Pacote", sorted(df["pacote"].dropna().unique()), key="mta_f_pacote")
    with c4:
        busca = st.text_input("🔎 Busca (Linha, Dígito, Atividade, Tarefa)", key="mta_f_busca")

    c5, c6 = st.columns([3, 1])
    with c5:
        meses = sorted(pd.to_datetime(df["mes_previsto"].dropna()).dt.to_period("M").astype(str).unique())
        mes_f = st.multiselect("Mês previsto", meses, format_func=_mes_ano, key="mta_f_mes")
    with c6:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        limpar = st.button("Limpar filtros", key="mta_f_limpar", width="stretch")

    if limpar:
        for chave in ("mta_f_situacao", "mta_f_executora", "mta_f_pacote", "mta_f_busca", "mta_f_mes"):
            st.session_state.pop(chave, None)
        st.rerun()

    filtrado = df.copy()
    if situacao_f:
        filtrado = filtrado[filtrado["situacao_consolidada"].isin(situacao_f)]
    if executora_f:
        filtrado = filtrado[filtrado["executora"].isin(executora_f)]
    if pacote_f:
        filtrado = filtrado[filtrado["pacote"].isin(pacote_f)]
    if mes_f:
        filtrado = filtrado[pd.to_datetime(filtrado["mes_previsto"]).dt.to_period("M").astype(str).isin(mes_f)]
    if busca:
        b = busca.strip().lower()
        filtrado = filtrado[
            filtrado["linha"].astype(str).str.lower().str.contains(b, na=False)
            | filtrado["digito"].astype(str).str.lower().str.contains(b, na=False)
            | filtrado["atividade"].astype(str).str.lower().str.contains(b, na=False)
            | filtrado["tarefa"].astype(str).str.lower().str.contains(b, na=False)
        ]

    st.caption(f"Exibindo {len(filtrado)} de {len(df)} solicitações")
    return filtrado


def _indicadores(df):
    total = len(df)
    aprovadas = int((df["aprovado"].apply(normalizar) == "SIM").sum())
    nao_aprovadas = int((df["aprovado"].apply(normalizar) == "NAO").sum())
    atendidas = int((df["situacao_consolidada"] == "Atendido").sum())
    em_tramite = int((df["situacao_consolidada"] == "Em trâmite").sum())
    sem_andamento = int(df["tramite"].isna().sum())
    valor_total = df["valor"].sum(skipna=True)
    valor_motores = df.loc[df["para_motores"].apply(normalizar) == "SIM", "valor"].sum(skipna=True)
    pct_atendidas = f"{100 * atendidas / total:.0f}% do total" if total else None

    st.markdown('<div class="pj-titulo-secao">Indicadores principais</div>', unsafe_allow_html=True)
    grade_indicadores([
        cartao_indicador("Total de solicitações", total, "Registros do C-98", "primary"),
        cartao_indicador("Atendidas", atendidas, pct_atendidas, "good"),
        cartao_indicador("Não aprovadas", nao_aprovadas, "Requerem análise" if nao_aprovadas else None, "critical"),
        cartao_indicador("Valor total", moeda_compacta(valor_total), moeda_completa(valor_total), "primary"),
        cartao_indicador("Aprovadas", aprovadas, None, "info"),
        cartao_indicador("Em trâmite", em_tramite, None, "warning"),
        cartao_indicador("Sem andamento informado", sem_andamento, None, "neutro"),
        cartao_indicador("Valor relacionado a motores", moeda_compacta(valor_motores), moeda_completa(valor_motores), "info"),
    ])


def _situacao(df):
    st.markdown('<div class="pj-titulo-secao">Situação das solicitações</div>', unsafe_allow_html=True)
    valor_total = df["valor"].sum(skipna=True)

    col1, col2 = st.columns(2)
    with col1:
        st.caption(f"Valor por situação consolidada · total {moeda_completa(valor_total)}")
        agrupado = df.groupby("situacao_consolidada", dropna=True)["valor"].sum(min_count=1).reset_index()
        cores = {s: COR_SITUACAO_MTA.get(s, STATUS["neutro"]) for s in agrupado["situacao_consolidada"]}
        fig = px.pie(agrupado, names="situacao_consolidada", values="valor", hole=0.55,
                     color="situacao_consolidada", color_discrete_map=cores)
        fig.update_traces(
            textinfo="percent",
            hovertemplate="%{label}: %{customdata[0]}<extra></extra>",
            customdata=[[moeda_completa(v)] for v in agrupado["valor"]],
            textfont_size=13,
        )
        layout_grafico(fig, altura=340)
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.caption("Quantidade por situação consolidada")
        contagem = df["situacao_consolidada"].value_counts().reset_index()
        contagem.columns = ["situacao", "quantidade"]
        cores = {s: COR_SITUACAO_MTA.get(s, STATUS["neutro"]) for s in contagem["situacao"]}
        fig = px.bar(contagem.sort_values("quantidade"), x="quantidade", y="situacao", orientation="h",
                     color="situacao", color_discrete_map=cores)
        fig.update_traces(text=contagem.sort_values("quantidade")["quantidade"], textposition="outside", cliponaxis=False)
        fig.update_layout(xaxis_title="", yaxis_title="", showlegend=False, yaxis={"type": "category"})
        layout_grafico(fig, altura=340)
        st.plotly_chart(fig, width="stretch")


def _analise_financeira(df):
    st.markdown('<div class="pj-titulo-secao">Análise financeira</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.caption("Valor por mês previsto")
        serie = df.dropna(subset=["mes_previsto"]).copy()
        if serie.empty:
            st.info("Sem datas de previsão registradas.")
        else:
            serie["mes"] = pd.to_datetime(serie["mes_previsto"]).dt.to_period("M").astype(str)
            agrupado = serie.groupby("mes")["valor"].sum(min_count=1).reset_index().sort_values("mes")
            agrupado["mes_label"] = agrupado["mes"].apply(_mes_ano)
            fig = px.bar(agrupado, x="mes_label", y="valor", color_discrete_sequence=[AMBER])
            _rotular_barras(fig, agrupado["valor"])
            fig.update_layout(xaxis_title="", yaxis_title="")
            layout_grafico(fig, altura=340)
            st.plotly_chart(fig, width="stretch")

    with col2:
        st.caption("Valor por executora")
        agrupado = df.groupby("executora", dropna=True)["valor"].sum(min_count=1).reset_index().sort_values("valor", ascending=True)
        fig = px.bar(agrupado, x="valor", y="executora", orientation="h", color_discrete_sequence=[CATEGORICA[1]])
        _rotular_barras(fig, agrupado["valor"])
        fig.update_layout(xaxis_title="", yaxis_title="", yaxis={"type": "category"})
        layout_grafico(fig, altura=340)
        st.plotly_chart(fig, width="stretch")

    col3, col4 = st.columns(2)
    with col3:
        st.caption("Valor por pacote")
        agrupado = df.groupby("pacote", dropna=True)["valor"].sum(min_count=1).reset_index().sort_values("valor", ascending=True)
        fig = px.bar(agrupado, x="valor", y="pacote", orientation="h", color_discrete_sequence=[CATEGORICA[2]])
        _rotular_barras(fig, agrupado["valor"])
        fig.update_layout(xaxis_title="", yaxis_title="", yaxis={"type": "category"})
        layout_grafico(fig, altura=340)
        st.plotly_chart(fig, width="stretch")

    with col4:
        st.caption("O que já chegou x o que ainda falta (por categoria)")
        trabalho = df.copy()
        trabalho["categoria"] = trabalho.apply(_categoria_destinacao, axis=1)
        trabalho["situacao_chegada"] = trabalho["situacao_consolidada"].apply(
            lambda s: "Já atendido" if s == "Atendido" else "Ainda pendente"
        )
        agrupado = trabalho.groupby(["categoria", "situacao_chegada"])["valor"].sum(min_count=1).reset_index()
        if agrupado.empty:
            st.info("Sem dados suficientes pra essa quebra.")
        else:
            # Rótulo como COLUNA do próprio dataframe (não uma lista solta
            # passada via update_traces) — com 2 séries (cores), uma lista
            # única aplicada por update_traces repete/desalinha entre as 2
            # séries. Como coluna, o Plotly separa certo por série.
            agrupado["rotulo"] = agrupado["valor"].apply(moeda_compacta)
            fig = px.bar(
                agrupado, x="categoria", y="valor", color="situacao_chegada", barmode="stack",
                text="rotulo",
                color_discrete_map={"Já atendido": STATUS["good"], "Ainda pendente": STATUS["warning"]},
                category_orders={"situacao_chegada": ["Já atendido", "Ainda pendente"]},
            )
            fig.update_traces(textposition="inside")
            fig.update_layout(xaxis_title="", yaxis_title="", legend_title="")
            layout_grafico(fig, altura=340)
            st.plotly_chart(fig, width="stretch")

    resumo = df.assign(categoria=df.apply(_categoria_destinacao, axis=1)).groupby("categoria").apply(
        lambda g: pd.Series({
            "Valor total": g["valor"].sum(skipna=True),
            "Já atendido": g.loc[g["situacao_consolidada"] == "Atendido", "valor"].sum(skipna=True),
            "Ainda pendente": g.loc[g["situacao_consolidada"] != "Atendido", "valor"].sum(skipna=True),
        }),
        include_groups=False,
    ).reset_index()
    resumo["% atendido"] = (100 * resumo["Já atendido"] / resumo["Valor total"]).round(0).astype("Int64").astype(str) + "%"
    for col in ("Valor total", "Já atendido", "Ainda pendente"):
        resumo[col] = resumo[col].apply(moeda_completa)
    st.dataframe(resumo, hide_index=True, width="stretch")


def _projetar_saldo(saldo_inicial, media_mensal, fila_hv, horizonte_meses=15):
    """Projeção mês a mês do saldo real do Contrato 005: parte do saldo em
    aberto de hoje, soma cada parcela de Hora de Voo que ainda vai virar
    empenho ("Mês previsto" do MTA é o mês de USO — o empenho de fato
    acontece 1 mês antes; RAP tratado como prioridade e somado já no
    próximo mês) e subtrai o gasto médio mensal (ver `_analise_saldo`).
    Devolve (tabela mês a mês, primeiro mês em que o saldo fica negativo —
    ou None se não fica, dentro do horizonte, detalhe por mês de quais
    parcelas do MTA entram nesse mês — pra painel clicável)."""
    mes0 = pd.Timestamp(horario.hoje_br()).replace(day=1)

    entradas = {}
    detalhe_entradas = {}
    for _, row in fila_hv.iterrows():
        valor = row["valor"] or 0
        if pd.isna(valor):
            continue
        if row["pacote"] == "RAP":
            mes_empenho = mes0 + pd.DateOffset(months=1)
        elif pd.notna(row["mes_previsto"]):
            mes_uso = pd.Timestamp(row["mes_previsto"]).replace(day=1)
            mes_empenho = max(mes_uso - pd.DateOffset(months=1), mes0)
        else:
            continue
        entradas[mes_empenho] = entradas.get(mes_empenho, 0) + valor
        rotulo = str(row["tarefa"]) + (" — RAP, prioridade" if row["pacote"] == "RAP" else "")
        detalhe_entradas.setdefault(mes_empenho, []).append({"parcela": rotulo, "valor": valor})

    linhas = []
    saldo = saldo_inicial
    mes = mes0
    mes_critico = None
    for _ in range(horizonte_meses):
        entrada = entradas.get(mes, 0.0)
        saida = media_mensal or 0.0
        saldo_final = saldo + entrada - saida
        linhas.append({
            "mes": mes, "saldo_inicial": saldo, "entrada": entrada, "saida": saida, "saldo_final": saldo_final,
            "entradas_detalhe": detalhe_entradas.get(mes, []),
        })
        if saldo_final < 0 and mes_critico is None:
            mes_critico = mes
        saldo = saldo_final
        mes = mes + pd.DateOffset(months=1)
    return pd.DataFrame(linhas), mes_critico


def _painel_detalhe_mes(linha):
    entradas = linha["entradas_detalhe"]
    if entradas:
        linhas_entrada = "".join(
            f'<div style="font-size:13.5px;color:{SECONDARY};margin-bottom:4px;">'
            f'• {e["parcela"]} — <strong style="color:{INK};">{moeda_completa(e["valor"])}</strong></div>'
            for e in entradas
        )
    else:
        linhas_entrada = f'<div style="font-size:13.5px;color:{SECONDARY};">Nenhuma parcela prevista pra entrar nesse mês.</div>'

    st.markdown(
        f"""<div style="background:{PANEL};border:1px solid {LINE};border-left:3px solid {AMBER};
        border-radius:10px;padding:16px 18px;margin-top:10px;">
            <div style="font-weight:700;color:{INK};margin-bottom:10px;font-size:15px;">
                Detalhe — {linha['mes_label']}
            </div>
            <div style="font-size:13.5px;color:{SECONDARY};margin-bottom:6px;">
                <strong style="color:{INK};">Saldo inicial:</strong> {moeda_completa(linha['saldo_inicial'])}</div>
            <div style="font-size:13.5px;color:{SECONDARY};margin-bottom:6px;">
                <strong style="color:{INK};">Saída (gasto médio, horas restantes ÷ meses × valor da hora):</strong> {moeda_completa(linha['saida'])}</div>
            <div style="font-size:13.5px;color:{SECONDARY};margin:10px 0 4px;">
                <strong style="color:{INK};">Entrada — {moeda_completa(linha['entrada'])} no total:</strong></div>
            {linhas_entrada}
            <div style="font-size:13.5px;color:{SECONDARY};margin-top:10px;">
                <strong style="color:{INK};">Saldo final do mês:</strong> {moeda_completa(linha['saldo_final'])}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def _empenhado_ate_mta(hv):
    """Até qual mês o empenho real de Hora de Voo já está feito, e qual é o
    próximo — Wallace, 2026-07-28: "deixa claro ate qual mes que ta pago,
    por exemplo eu empenhei um valor ja referente a junho, julho nem
    emepnhei ainda". Uma parcela só conta como "empenhada" se TODAS as
    linhas dela (às vezes uma parcela vem dividida em 2, ex. 2048 + outro
    código) estiverem "Atendido". "Mês previsto" é o mês de uso — o
    empenho real é 1 mês antes. Devolve (mes_empenho_feito, mes_uso_feito,
    mes_empenho_proximo, mes_uso_proximo) — qualquer um pode vir None se
    não houver parcela nessa condição."""
    trabalho = hv[hv["pacote"] != "RAP"].copy()
    trabalho["parcela_num"] = trabalho["tarefa"].str.extract(r"(\d+)/\d+").astype(float)
    por_parcela = trabalho.groupby("parcela_num").agg(
        completa=("situacao_consolidada", lambda s: (s == "Atendido").all()),
        mes_previsto=("mes_previsto", "first"),
    ).reset_index().sort_values("parcela_num")

    feitas = por_parcela[por_parcela["completa"] & por_parcela["mes_previsto"].notna()]
    pendentes = por_parcela[~por_parcela["completa"] & por_parcela["mes_previsto"].notna()]

    mes_uso_feito = mes_empenho_feito = mes_uso_proximo = mes_empenho_proximo = None
    if not feitas.empty:
        mes_uso_feito = pd.Timestamp(feitas.iloc[-1]["mes_previsto"]).replace(day=1)
        mes_empenho_feito = mes_uso_feito - pd.DateOffset(months=1)
    if not pendentes.empty:
        mes_uso_proximo = pd.Timestamp(pendentes.iloc[0]["mes_previsto"]).replace(day=1)
        mes_empenho_proximo = mes_uso_proximo - pd.DateOffset(months=1)
    return mes_empenho_feito, mes_uso_feito, mes_empenho_proximo, mes_uso_proximo


def _analise_saldo(df, dados):
    st.markdown('<div class="pj-titulo-secao">Análise do dinheiro em saldo (Hora de Voo)</div>', unsafe_allow_html=True)
    st.caption(
        "Cruza a fila de solicitações de Hora de Voo do MTA com o dinheiro real do "
        "Contrato 005 (VEE ONE) — a aba \"Empenhos\" não distingue categoria (o mesmo "
        "código ND cobre Hora de Voo, Parcela Fixa, Requisição e Sob Demanda), então o "
        "valor empenhado/saldo abaixo é do **contrato inteiro**, não só Hora de Voo. O "
        "\"Mês previsto\" do MTA é o **mês de uso** — o empenho de fato acontece 1 mês "
        "antes (ex.: Hora de Voo com uso previsto em julho tem o empenho feito em "
        "junho; Wallace, 2026-07-28: \"eu empenhei um valor já referente a junho, "
        "julho nem empenhei ainda\"). RAP = saldo de empenho que não é diretamente de "
        "2026 (ano anterior), ainda não usado — prioridade de uso."
    )

    empenhos_info = dados.get("empenhos_contrato005")
    if empenhos_info is not None:
        emp = empenhos_info["empenhos"].copy()
        emp["ano"] = emp["numero_empenho"].astype(str).str[:4]
        eh_rap_emp = emp["ano"] != "2026"

        valor_empenhado_real = emp["valor_empenhado"].sum(skipna=True)
        saldo_total_real = emp["saldo"].sum(skipna=True)
        saldo_rap = emp.loc[eh_rap_emp, "saldo"].sum(skipna=True)
        saldo_geral_contrato = empenhos_info.get("saldo_geral_contrato")

    else:
        emp = None
        eh_rap_emp = None
        valor_empenhado_real = saldo_total_real = saldo_rap = saldo_geral_contrato = None

    hv = df[df["para_contrato"] == "HORA DE VOO"].copy()
    eh_rap_mta = hv["pacote"] == "RAP"
    atendido = hv[hv["situacao_consolidada"] == "Atendido"]
    fila_mta = hv[(hv["situacao_consolidada"] != "Atendido") & ~eh_rap_mta]
    rap_mta = hv[eh_rap_mta]
    fila_projetavel = hv[hv["situacao_consolidada"] != "Atendido"]  # fila + RAP, o que ainda pode virar empenho

    mes_emp_feito, mes_uso_feito, mes_emp_prox, mes_uso_prox = _empenhado_ate_mta(hv)

    # Média de gasto mensal — Wallace, 2026-07-28: "media de gasto nao é do
    # cronograma é o real, quantas horas falta no ano? [...] divide por
    # quantos meses nao paguei e multiplica pela hora de voo (valor)"; e
    # "desses valores ai so nao paguei ainda julho ne, junho ja empenhei"
    # — "meses não pagos" conta a partir do mês seguinte ao último
    # empenhado de verdade (não do mês corrente do calendário).
    pendente_hv = pd.concat([fila_mta, rap_mta])
    horas_restantes = pendente_hv["tarefa"].str.extract(r"(\d+)\s*HV")[0].astype(float).sum()
    valor_hora_voo = empenhos_info.get("valor_hora_voo") if empenhos_info is not None else None
    meses_nao_pagos = (
        max(12 - mes_emp_feito.month, 1) if mes_emp_feito is not None
        else max(12 - horario.hoje_br().month, 1)
    )
    media_mensal = (
        (horas_restantes / meses_nao_pagos) * valor_hora_voo
        if horas_restantes and valor_hora_voo else None
    )

    aba_resumo, aba_projecao, aba_parcelas, aba_empenhos = st.tabs(
        ["📊 Resumo", "📈 Até quando dá a grana", "📅 Parcelas do MTA", "📄 Empenhos (Contrato 005)"]
    )

    with aba_resumo:
        if mes_emp_feito is not None:
            st.markdown("###### Até qual mês o empenho de Hora de Voo já está feito")
            cartoes_ate_quando = [
                cartao_indicador("✅ Empenhado até", _mes_ano(mes_emp_feito.strftime("%Y-%m")),
                                  f"Cobre o uso de {_mes_ano(mes_uso_feito.strftime('%Y-%m'))}", "good"),
            ]
            if mes_emp_prox is not None:
                cartoes_ate_quando.append(
                    cartao_indicador("⏳ Próximo a empenhar", _mes_ano(mes_emp_prox.strftime("%Y-%m")),
                                      f"Referente ao uso de {_mes_ano(mes_uso_prox.strftime('%Y-%m'))}", "warning")
                )
            grade_indicadores(cartoes_ate_quando)
            st.divider()

        st.markdown("###### Dinheiro do contrato")
        cartoes_empenho = []
        if empenhos_info is not None:
            if saldo_geral_contrato is not None:
                cartoes_empenho.append(
                    cartao_indicador("Saldo geral do contrato (Módulo 1+2+3)", moeda_compacta(saldo_geral_contrato),
                                      "Quanto ainda pode ser empenhado dentro da autorização (Reajuste)", "primary")
                )
            cartoes_empenho += [
                cartao_indicador("Já empenhado (NE emitidas)", moeda_compacta(valor_empenhado_real),
                                  "Formalizado em nota de empenho — " + moeda_completa(valor_empenhado_real), "info"),
                cartao_indicador("→ saldo desses empenhos (ainda não liquidado)", moeda_compacta(saldo_total_real),
                                  "Já é dinheiro formal, só falta gastar/liquidar", "warning"),
                cartao_indicador("→ dos quais RAP (pré-2026)", moeda_compacta(saldo_rap),
                                  "Prioridade: já deveria ter sido usado" if saldo_rap else "Sem RAP no momento",
                                  "critical" if saldo_rap else "neutro"),
            ]
            grade_indicadores(cartoes_empenho)
        else:
            st.info("Dados de empenhos do Contrato 005 não encontrados em 02_Dados_Tratados/ — mostrando só a fila do MTA.")

        if media_mensal:
            st.divider()
            st.markdown("###### Consumo (Hora de Voo) — conta aberta")
            # "$" dispara modo matemático (LaTeX) no markdown do Streamlit —
            # escapa pra "R$" aparecer como texto, não sumir no meio da conta.
            conta = (
                f"Horas de Hora de Voo ainda não atendidas = **{horas_restantes:.0f} HV** ÷ "
                f"**{meses_nao_pagos} mês(es) não pago(s)** × **{moeda_completa(valor_hora_voo)}/HV** "
                f"= **{moeda_completa(media_mensal)}/mês**"
            ).replace("R$", "R\\$")
            st.markdown(conta)
            grade_indicadores([
                cartao_indicador("Horas ainda não atendidas", f"{horas_restantes:.0f} HV",
                                  "Somado das parcelas fila + RAP", "warning"),
                cartao_indicador("÷ meses não pagos", str(meses_nao_pagos),
                                  f"A partir de {_mes_ano((mes_emp_feito + pd.DateOffset(months=1)).strftime('%Y-%m'))}"
                                  if mes_emp_feito is not None else "Meses restantes do ano", "neutro"),
                cartao_indicador("× valor da hora de voo", moeda_completa(valor_hora_voo),
                                  "Real, pós 2° Reajuste (Contrato 005)", "info"),
                cartao_indicador("= Média de gasto mensal", moeda_compacta(media_mensal),
                                  "Usada na projeção — inclusive pra 2027", "primary"),
            ])

        st.divider()
        st.markdown("###### Fila do MTA (Hora de Voo)")
        cartoes_mta = [
            cartao_indicador("Já atendida", moeda_compacta(atendido["valor"].sum(skipna=True)),
                              f"{len(atendido)} parcela(s) — pode virar empenho", "good"),
            cartao_indicador("Ainda na fila (aprovado/em trâmite)", moeda_compacta(fila_mta["valor"].sum(skipna=True)),
                              f"{len(fila_mta)} parcela(s) pendente(s)", "warning"),
        ]
        if not rap_mta.empty:
            cartoes_mta.append(
                cartao_indicador("RAP (Hora de Voo)", moeda_compacta(rap_mta["valor"].sum(skipna=True)),
                                  f"{len(rap_mta)} parcela(s) — prioridade", "critical")
            )
        grade_indicadores(cartoes_mta)

    with aba_projecao:
        st.caption(
            "Projeção mês a mês do **saldo dos empenhos já emitidos** (não do saldo geral do contrato, "
            "que é só o limite de autorização — isso aqui é dinheiro já formalizado): parte do saldo de "
            "hoje, soma cada parcela de Hora de Voo que ainda vai virar empenho (deslocada 1 mês pela "
            "defasagem empenho→uso; RAP entra já no próximo mês, por prioridade) e subtrai o gasto médio "
            "mensal (ver conta em \"Consumo\", na aba Resumo — horas restantes ÷ meses não pagos × valor "
            "da hora de voo). Não considera novos ciclos de MTA além do que já está na fila — se a "
            "DIRMAB atrasar uma parcela, a data muda."
        )
        if empenhos_info is None or not media_mensal:
            st.info("Sem dados de empenhos/hora de voo do Contrato 005 — não dá pra projetar.")
        else:
            projecao, mes_critico = _projetar_saldo(saldo_total_real, media_mensal, fila_projetavel)

            if mes_critico is not None:
                st.markdown(
                    f"🔴 **No ritmo atual, o saldo fica negativo a partir de {_mes_ano(mes_critico.strftime('%Y-%m'))}** "
                    "— a fila de parcelas do MTA que ainda vai virar empenho não é suficiente pra acompanhar o "
                    "gasto médio a partir daí, a não ser que uma nova rodada do MTA reforce antes disso."
                )
            else:
                st.markdown(
                    f"🟢 **O saldo se mantém positivo nos próximos {len(projecao)} meses** — as parcelas do MTA "
                    "que ainda vão virar empenho parecem suficientes pra acompanhar o ritmo de gasto, sem faltar dinheiro."
                )

            projecao["situacao_saldo"] = (projecao["saldo_final"] < 0).map({True: "Negativo", False: "Positivo"})
            projecao["mes_label"] = projecao["mes"].dt.strftime("%Y-%m").apply(_mes_ano)
            fig = px.bar(
                projecao, x="mes_label", y="saldo_final", color="situacao_saldo",
                color_discrete_map={"Positivo": STATUS["good"], "Negativo": STATUS["critical"]},
            )
            fig.add_hline(y=0, line_dash="dash", line_color=SECONDARY)
            fig.update_traces(text=[moeda_compacta(v) for v in projecao["saldo_final"]], textposition="outside", cliponaxis=False)
            fig.update_layout(xaxis_title="", yaxis_title="Saldo projetado", legend_title="", showlegend=False)
            layout_grafico(fig, altura=340)
            evento_proj = st.plotly_chart(
                fig, width="stretch", key="mta_projecao_chart", on_select="rerun", selection_mode="points"
            )
            st.caption("👆 Clique num mês na barra pra ver o detalhe: saldo inicial, o que entra (qual parcela) e o que sai.")

            pontos = evento_proj.selection.get("points", []) if evento_proj else []
            if pontos:
                mes_clicado = pontos[0].get("x")
                linha_clicada = projecao[projecao["mes_label"] == mes_clicado]
                if not linha_clicada.empty:
                    _painel_detalhe_mes(linha_clicada.iloc[0])

            tabela_proj = projecao[["mes_label", "saldo_inicial", "entrada", "saida", "saldo_final"]].copy()
            for coluna in ("saldo_inicial", "entrada", "saida", "saldo_final"):
                tabela_proj[coluna] = tabela_proj[coluna].apply(moeda_completa)
            st.dataframe(
                tabela_proj.rename(columns={
                    "mes_label": "Mês", "saldo_inicial": "Saldo inicial", "entrada": "Entrada (nova empenho)",
                    "saida": "Saída (gasto médio)", "saldo_final": "Saldo final",
                }),
                hide_index=True, width="stretch", height=380,
            )

    with aba_parcelas:
        if hv.empty:
            st.info("Sem solicitações de Hora de Voo no filtro atual do MTA.")
        else:
            hv["parcela"] = hv["tarefa"].str.extract(r"(\d+/\d+)")
            hv["parcela_num"] = hv["tarefa"].str.extract(r"(\d+)/\d+").astype(float)
            ordenado = hv.sort_values("parcela_num")

            col1, col2 = st.columns([3, 2])
            with col1:
                st.caption("Valor por parcela, colorido por situação")
                cores = {s: COR_SITUACAO_MTA.get(s, STATUS["neutro"]) for s in ordenado["situacao_consolidada"].unique()}
                fig = px.bar(ordenado, x="parcela", y="valor", color="situacao_consolidada", color_discrete_map=cores)
                _rotular_barras(fig, ordenado["valor"])
                fig.update_layout(xaxis_title="Parcela", yaxis_title="", legend_title="")
                layout_grafico(fig, altura=340)
                st.plotly_chart(fig, width="stretch")

            with col2:
                st.caption("Mês de uso (\"Mês previsto\" do MTA) x mês do empenho real (1 mês antes)")
                detalhe = []
                for _, row in ordenado.iterrows():
                    if row["pacote"] == "RAP":
                        mes_emp, mes_uso = "Já processado — RAP", "Ciclo anterior"
                    elif pd.notna(row["mes_previsto"]):
                        ts = pd.Timestamp(row["mes_previsto"])
                        mes_uso = _mes_ano(ts.strftime("%Y-%m"))
                        mes_emp = _mes_ano((ts - pd.DateOffset(months=1)).strftime("%Y-%m"))
                    else:
                        mes_emp, mes_uso = "—", "—"
                    detalhe.append({
                        "Parcela": row["parcela"], "Valor": moeda_completa(row["valor"]),
                        "Mês do empenho": mes_emp, "Mês de uso estimado": mes_uso,
                        "Situação": row["situacao_consolidada"],
                    })
                st.dataframe(pd.DataFrame(detalhe), hide_index=True, width="stretch", height=340)

    with aba_empenhos:
        if empenhos_info is None:
            st.info("Dados de empenhos do Contrato 005 não encontrados em 02_Dados_Tratados/.")
        else:
            st.caption("Empenhos do Contrato 005 — valor e saldo reais, por número de NE")
            tabela_emp = emp.copy()
            tabela_emp["RAP"] = eh_rap_emp.map({True: "Sim — prioridade", False: "Não"})
            tabela_emp = tabela_emp[["numero_empenho", "ano", "valor_empenhado", "saldo", "RAP"]].sort_values(
                "saldo", ascending=False
            )
            tabela_emp["valor_empenhado"] = tabela_emp["valor_empenhado"].apply(moeda_completa)
            tabela_emp["saldo"] = tabela_emp["saldo"].apply(moeda_completa)
            st.dataframe(
                tabela_emp.rename(columns={
                    "numero_empenho": "Nº Empenho", "ano": "Ano",
                    "valor_empenhado": "Valor empenhado", "saldo": "Saldo",
                }),
                hide_index=True, width="stretch", height=280,
            )

            st.caption(
                "Pode ter atraso entre o MTA marcar uma parcela \"Atendido\" e o empenho real aparecer "
                "aqui — o histórico diário abaixo garante que dá pra sempre achar quando um NE "
                "apareceu ou mudou de saldo, o dinheiro nunca \"some\" nesse meio-tempo."
            )
            secao_evolucao(
                empenhos_info.get("historico_empenhos"), chave=["numero_empenho"],
                key_slider="mta_empenhos_evolucao_slider",
                colunas_exibir=["numero_empenho", "valor_empenhado", "saldo"],
                nomes_colunas={"numero_empenho": "Nº Empenho", "valor_empenhado": "Valor empenhado", "saldo": "Saldo"},
            )


def _painel_detalhe(registro):
    linhas_html = []
    for campo, rotulo in NOMES_CAMPOS_DETALHE.items():
        valor = registro.get(campo)
        if valor is None or (isinstance(valor, float) and pd.isna(valor)):
            texto = "Não informado"
        elif campo == "valor":
            texto = moeda_completa(valor)
        elif campo in ("data_pedido", "mes_previsto") and pd.notna(valor):
            texto = pd.Timestamp(valor).strftime("%d/%m/%Y")
        else:
            texto = str(valor)
        linhas_html.append(
            f'<div style="font-size:13.5px;color:{SECONDARY};margin-bottom:6px;">'
            f'<strong style="color:{INK};">{rotulo}:</strong> {texto}</div>'
        )
    metade = (len(linhas_html) + 1) // 2
    st.markdown(
        f"""<div style="background:{PANEL};border:1px solid {LINE};border-left:3px solid {AMBER};
        border-radius:10px;padding:16px 18px;margin-top:10px;">
            <div style="font-weight:700;color:{INK};margin-bottom:10px;font-size:15px;">
                Detalhe — Linha {registro.get('linha', 'Não informado')}
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 24px;">
                <div>{"".join(linhas_html[:metade])}</div>
                <div>{"".join(linhas_html[metade:])}</div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


def render(dados):
    estado_atual = dados.get("mta_estado", {})

    col_titulo, col_botao = st.columns([4, 1])
    with col_titulo:
        cabecalho_pagina(
            "MTA — Acompanhamento e Solicitações",
            "Fonte: planilha \"MTA - Acompanhamento e Solicitações\", aba \"Solicitações\"",
            "Projeto: C-98",
            status_atualizacao_html(estado_atual),
        )
    with col_botao:
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        botao_atualizar("MTA", _atualizar, key="mta_atualizar")

    df = dados.get("mta")
    if df is None or df.empty:
        st.info("Ainda não foi carregado — clique em \"Atualizar MTA\" acima.")
        return

    filtrado = _filtros(df)
    _indicadores(filtrado)
    st.divider()
    _situacao(filtrado)
    st.divider()
    _analise_financeira(filtrado)
    st.divider()
    _analise_saldo(filtrado, dados)
    st.divider()

    st.markdown('<div class="pj-titulo-secao">Tabela operacional</div>', unsafe_allow_html=True)
    tabela = filtrado[COLUNAS_TABELA].rename(columns=NOMES_COLUNAS)
    tabela = filtro_colunas(tabela, key_prefix="mta")
    st.caption(f"{len(tabela)} linha(s) após os filtros por coluna.")
    evento = st.dataframe(
        tabela, hide_index=True, width="stretch", height=420,
        on_select="rerun", selection_mode="single-row", key="mta_tabela",
    )
    linhas_selecionadas = evento.selection.get("rows", []) if evento else []
    if linhas_selecionadas:
        registro = tabela.iloc[linhas_selecionadas[0]]
        registro = filtrado[filtrado["linha"] == registro["Linha"]].iloc[0].to_dict()
        _painel_detalhe(registro)

    csv = tabela.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar (CSV)", csv, file_name="mta.csv", mime="text/csv")

    st.divider()
    secao_evolucao(
        dados.get("mta_historico"), chave=["linha"], key_slider="mta_evolucao_slider",
        colunas_exibir=["linha", "situacao_consolidada", "aprovado", "tramite", "valor", "executora", "pacote"],
        nomes_colunas={
            "linha": "Linha", "situacao_consolidada": "Situação consolidada", "aprovado": "Aprovado",
            "tramite": "Trâmite", "valor": "Valor", "executora": "Executora", "pacote": "Pacote",
        },
    )
