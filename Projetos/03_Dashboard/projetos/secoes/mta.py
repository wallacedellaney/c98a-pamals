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


def _analise_saldo(df, dados):
    st.markdown('<div class="pj-titulo-secao">Análise do dinheiro em saldo (Hora de Voo)</div>', unsafe_allow_html=True)
    st.caption(
        "Cruza a fila de solicitações de Hora de Voo do MTA com o saldo real dos "
        "empenhos do Contrato 005 (aba \"Empenhos\", CELOG-PAMALS). O empenho previsto "
        "pra um mês só é de fato utilizado no mês seguinte (ex.: Hora de Voo prevista "
        "pra junho é usada em julho). RAP = saldo de empenho que não é diretamente de "
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
        saldo_ano_corrente = emp.loc[~eh_rap_emp, "saldo"].sum(skipna=True)

        cronograma = empenhos_info["cronograma_mensal"]
        vigente = cronograma[cronograma["apos_1_reajuste"]]
        media_mensal = (
            (vigente["modulo_1"] + vigente["modulo_2"] + vigente["modulo_3"]).mean()
            if not vigente.empty else None
        )

        cartoes_empenho = [
            cartao_indicador("Empenhado (real, Contrato 005)", moeda_compacta(valor_empenhado_real),
                              moeda_completa(valor_empenhado_real), "primary"),
            cartao_indicador("Saldo em aberto (real, ainda não gasto)", moeda_compacta(saldo_total_real),
                              moeda_completa(saldo_total_real), "warning"),
            cartao_indicador("RAP — resto a pagar (empenho pré-2026)", moeda_compacta(saldo_rap),
                              "Prioridade: já deveria ter sido usado" if saldo_rap else "Sem RAP no momento",
                              "critical" if saldo_rap else "neutro"),
            cartao_indicador("Saldo do ano corrente (2026)", moeda_compacta(saldo_ano_corrente),
                              "Dentro do prazo normal de uso", "info"),
        ]
        if media_mensal:
            cartoes_empenho.append(
                cartao_indicador("Média de gasto mensal (cronograma)", moeda_compacta(media_mensal),
                                  moeda_completa(media_mensal) + "/mês, pós 1° Reajuste", "info")
            )
    else:
        cartoes_empenho = []
        st.info("Dados de empenhos do Contrato 005 não encontrados em 02_Dados_Tratados/ — mostrando só a fila do MTA.")

    hv = df[df["para_contrato"] == "HORA DE VOO"].copy()
    eh_rap_mta = hv["pacote"] == "RAP"
    atendido = hv[hv["situacao_consolidada"] == "Atendido"]
    fila_mta = hv[(hv["situacao_consolidada"] != "Atendido") & ~eh_rap_mta]
    rap_mta = hv[eh_rap_mta]

    cartoes_mta = [
        cartao_indicador("MTA — Hora de Voo já atendida", moeda_compacta(atendido["valor"].sum(skipna=True)),
                          f"{len(atendido)} parcela(s) — pode virar empenho", "good"),
        cartao_indicador("MTA — ainda na fila (aprovado/em trâmite)", moeda_compacta(fila_mta["valor"].sum(skipna=True)),
                          f"{len(fila_mta)} parcela(s) pendente(s)", "warning"),
    ]
    if not rap_mta.empty:
        cartoes_mta.append(
            cartao_indicador("MTA — RAP (Hora de Voo)", moeda_compacta(rap_mta["valor"].sum(skipna=True)),
                              f"{len(rap_mta)} parcela(s) — prioridade", "critical")
        )

    grade_indicadores(cartoes_empenho + cartoes_mta)

    if empenhos_info is not None:
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

    if hv.empty:
        st.info("Sem solicitações de Hora de Voo no filtro atual do MTA.")
        return

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
        st.caption("Mês do empenho x mês de uso real (defasagem de 1 mês)")
        detalhe = []
        for _, row in ordenado.iterrows():
            if row["pacote"] == "RAP":
                mes_emp, mes_uso = "RAP (ciclo anterior)", "Usar já — prioridade"
            elif pd.notna(row["mes_previsto"]):
                ts = pd.Timestamp(row["mes_previsto"])
                mes_emp = _mes_ano(ts.strftime("%Y-%m"))
                mes_uso = _mes_ano((ts + pd.DateOffset(months=1)).strftime("%Y-%m"))
            else:
                mes_emp, mes_uso = "—", "—"
            detalhe.append({
                "Parcela": row["parcela"], "Valor": moeda_completa(row["valor"]),
                "Mês do empenho": mes_emp, "Mês de uso estimado": mes_uso,
                "Situação": row["situacao_consolidada"],
            })
        st.dataframe(pd.DataFrame(detalhe), hide_index=True, width="stretch", height=340)


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
