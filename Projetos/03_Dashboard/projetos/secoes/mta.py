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

REORGANIZAÇÃO em 2026-09-03 (pedido do Wallace, checagem de recurso do
MTA) — a página passou a responder PRIMEIRO "quanto recurso ainda existe":
1. Cabeçalho / filtros (iguais)
2. Disponibilidade financeira (novo, primeira linha de cards)
3. Disponível por destinação (novo, quadro clicável)
4. Tabela operacional estilo Excel (subiu pra logo depois, agora com
   AG Grid — scroll, redimensionar/arrastar coluna, ordenar, filtrar por
   coluna, selecionar linhas, barra de resumo visível/selecionado)
5. Análise mensal / TGCO (novo, gráficos focados em decisão)
6. Gráficos secundários (os antigos "Situação"/"Análise financeira" —
   mesma lógica de sempre, só desceram de prioridade)
7. Análise do dinheiro em saldo (Contrato 005 / Hora de Voo) — INTOCADA,
   só mudou de posição (ver `_analise_saldo`, mesmos cálculos de sempre)
8. Histórico (evolução)

Os cálculos antigos (`situacao_consolidada`, `_categoria_destinacao`,
`_analise_saldo` inteira) continuam existindo e corretos — nada foi
reescrito, só reorganizado. As contas NOVAS (Aprovado/Utilizado/Disponível/
TGCO/Livre, Grupo estratégico) vêm de `projetos/regras/mta_regras.py`,
mesmo padrão de sempre (regra de negócio centralizada, não espalhada)."""

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from st_aggrid import AgGrid, ColumnsAutoSizeMode, DataReturnMode, GridOptionsBuilder, GridUpdateMode
from st_aggrid.shared import JsCode

from shared import horario
from projetos.components.atualizacao import botao_atualizar, status_atualizacao_html
from projetos.components.evolucao import secao_evolucao
from projetos.components.paleta import (
    CATEGORICA, COR_SITUACAO_MTA, INK, LINE, PANEL, SECONDARY, STATUS,
    PRIMARY as AMBER,
    cabecalho_pagina, cartao_indicador, grade_indicadores, layout_grafico, moeda_compacta, moeda_completa,
)
from projetos.regras.mta_regras import (
    CORES_STATUS_RECURSO, NAO_CLASSIFICADO, ORDEM_GRUPO_ESTRATEGICO,
    STATUS_ATENDIDO, STATUS_DISPONIVEL, STATUS_NAO_APROVADO,
    normalizar, prepare_mta_data, validar_fechamento,
)

MESES_ABREV = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

# Colunas visíveis por padrão na tabela operacional (pedido explícito do
# Wallace, 2026-09-03) — as demais continuam acessíveis pelo seletor
# "+ Mais colunas" acima da grade (ver `_tabela_operacional`).
COLUNAS_TABELA_PADRAO = [
    "linha", "STATUS_RECURSO", "situacao_consolidada", "aprovado", "tramite", "data_pedido",
    "preenchimento_tgco", "mes_previsto", "categoria", "subcategoria", "grupo_estrategico",
    "atividade", "tarefa", "valor", "executora", "nd", "pacote", "para_contrato", "para_motores",
]
COLUNAS_TABELA_EXTRA = [
    "digito", "rodada", "acao",
    "projeto_coordenador", "projeto_atividade", "observacao_coordenador", "impactos_nao_atendimento",
]
NOMES_COLUNAS = {
    "linha": "Linha", "situacao_consolidada": "Situação consolidada", "aprovado": "Aprovado",
    "tramite": "Trâmite", "data_pedido": "Data do pedido", "digito": "Dígito",
    "rodada": "Rodada de atendimento", "preenchimento_tgco": "Preenchimento da TGCO",
    "atividade": "Atividade", "tarefa": "Tarefa", "valor": "Valor", "executora": "Executora",
    "nd": "ND", "pacote": "Pacote", "para_contrato": "Para Contrato", "para_motores": "Para Motores",
    "mes_previsto": "Mês planejamento atual", "categoria": "Categoria", "subcategoria": "Subcategoria",
    "grupo_estrategico": "Grupo estratégico", "acao": "Ação", "STATUS_RECURSO": "Status do recurso",
    "projeto_coordenador": "Projeto (bloco coordenador)", "projeto_atividade": "Projeto (bloco atividade)",
    "observacao_coordenador": "Observação do coordenador", "impactos_nao_atendimento": "Impactos do não atendimento",
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
    """Categoria antiga (Hora de Voo/Motores/Sob Demanda/...) — usada só
    nos gráficos secundários (Situação/Análise financeira), que continuam
    com a mesma lógica de sempre. Ver `grupo_estrategico` em mta_regras.py
    pra dimensão estratégica nova, que é a usada nos cards principais."""
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


def _preparar(df):
    """Chama a preparação central (`mta_regras.prepare_mta_data`) e mantém
    apelidos em minúsculo das colunas derivadas — as seções antigas desta
    página (tabela, gráficos secundários, Contrato 005) já usam esses
    nomes, então nada precisou ser reescrito quando o eixo da página virou
    ATENDIDO x DISPONÍVEL (2026-09-03)."""
    trabalho = prepare_mta_data(df)
    trabalho["utilizado"] = trabalho["ATENDIDO_BOOL"]
    trabalho["disponivel"] = trabalho["DISPONIVEL_BOOL"]
    trabalho["com_tgco"] = trabalho["disponivel"] & trabalho["preenchimento_tgco"].apply(
        lambda v: normalizar(v) is not None
    )
    trabalho["livre"] = trabalho["disponivel"] & ~trabalho["com_tgco"]
    trabalho["grupo_estrategico"] = trabalho["GRUPO_ESTRATEGICO"]
    trabalho["categoria"] = trabalho["CATEGORIA"]
    trabalho["subcategoria"] = trabalho["SUBCATEGORIA"]
    return trabalho


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


def _disponibilidade_financeira(df):
    """Primeira área — ATENDIDO x DISPONÍVEL (eixo central da página,
    Wallace 2026-09-03). Aprovado operacional = Atendido + Disponível;
    cancelado/bloqueado/sem aprovado saem como EXCEÇÃO, nunca somem
    silenciosamente (item 7 do prompt)."""
    st.markdown('<div class="pj-titulo-secao">Disponibilidade financeira</div>', unsafe_allow_html=True)

    v = validar_fechamento(df)
    nao_aprovado = df[df["STATUS_RECURSO"] == STATUS_NAO_APROVADO]
    v_nao_aprovado = nao_aprovado["VALOR_NUMERICO"].sum(skipna=True)
    operacional = v["valor_aprovado_operacional"]
    pct_atendido = (100 * v["valor_atendido"] / operacional) if operacional else 0
    pct_disponivel = (100 * v["valor_disponivel"] / operacional) if operacional else 0

    cards = [
        cartao_indicador("Total aprovado", moeda_compacta(operacional),
                          f"{v['qtd_atendido'] + v['qtd_disponivel']} linha(s) · operacional (atendido + disponível)", "primary"),
        cartao_indicador("🟢 Atendido", moeda_compacta(v["valor_atendido"]),
                          f"{v['qtd_atendido']} linha(s) · {pct_atendido:.1f}% do aprovado", "good"),
        cartao_indicador("🔵 Disponível", moeda_compacta(v["valor_disponivel"]),
                          f"{v['qtd_disponivel']} linha(s) · {pct_disponivel:.1f}% do aprovado", "info"),
        cartao_indicador("% atendido", f"{pct_atendido:.1f}%", "Atendido ÷ aprovado operacional", "primary"),
        cartao_indicador("🔴 Não aprovado", moeda_compacta(v_nao_aprovado),
                          f"{len(nao_aprovado)} linha(s) · fora do recurso disponível", "critical"),
    ]
    if v["qtd_excecoes"]:
        cards.append(cartao_indicador(
            "🟠 Exceções", moeda_compacta(v["valor_excecoes"]),
            f"{v['qtd_excecoes']} linha(s) aprovadas mas canceladas/bloqueadas", "warning"))
    grade_indicadores(cards)

    st.caption(
        f"Aprovado bruto (tudo com Aprovado = SIM): {moeda_completa(v['valor_aprovado_bruto'])} · "
        f"{v['qtd_aprovado_bruto']} linha(s). A diferença pro operacional são as exceções "
        "(canceladas/bloqueadas), listadas abaixo."
    )
    if not v["fecha"]:
        st.error("⚠️ Atendido + Disponível + Exceções ≠ Aprovado bruto — avisa o Claude, a regra saiu do lugar.")
    if v["qtd_excecoes"]:
        with st.expander(f"🟠 Ver as {v['qtd_excecoes']} exceção(ões) (aprovado, mas cancelado/bloqueado)"):
            st.dataframe(
                v["excecoes"][["linha", "atividade", "tarefa", "tramite", "VALOR_NUMERICO"]].rename(
                    columns={"linha": "Linha", "atividade": "Atividade", "tarefa": "Tarefa",
                             "tramite": "Trâmite", "VALOR_NUMERICO": "Valor"}),
                hide_index=True, width="stretch",
            )


def _atendido_x_disponivel(df):
    """Visão geral + por categoria, lado a lado — 🟢 atendido x 🔵 disponível
    (gráfico que o Wallace pediu de volta: "aquele gráfico em colunas do que
    foi pago para coisa de contrato, coisa de motor")."""
    st.markdown('<div class="pj-titulo-secao">Atendido x Disponível</div>', unsafe_allow_html=True)

    base = df[df["STATUS_RECURSO"].isin([STATUS_ATENDIDO, STATUS_DISPONIVEL])].copy()
    if base.empty:
        st.info("Nada aprovado no filtro atual.")
        return

    cor_status = {STATUS_ATENDIDO: STATUS["good"], STATUS_DISPONIVEL: STATUS["info"]}

    col1, col2 = st.columns([1, 2])
    with col1:
        st.caption("Composição do aprovado operacional")
        comp = base.groupby("STATUS_RECURSO")["VALOR_NUMERICO"].sum(min_count=1).reset_index()
        fig = px.pie(comp, names="STATUS_RECURSO", values="VALOR_NUMERICO", hole=0.58,
                     color="STATUS_RECURSO", color_discrete_map=cor_status)
        fig.update_traces(textinfo="percent", textfont_size=14,
                           hovertemplate="%{label}: %{customdata[0]}<extra></extra>",
                           customdata=[[moeda_completa(x)] for x in comp["VALOR_NUMERICO"]])
        layout_grafico(fig, altura=330)
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.caption("Por categoria — quanto já foi atendido e quanto ainda está disponível")
        agrup = base.groupby(["CATEGORIA", "STATUS_RECURSO"])["VALOR_NUMERICO"].sum(min_count=1).reset_index()
        totais = agrup.groupby("CATEGORIA")["VALOR_NUMERICO"].sum().sort_values()
        agrup["rotulo"] = agrup["VALOR_NUMERICO"].apply(moeda_compacta)
        fig = px.bar(agrup, x="VALOR_NUMERICO", y="CATEGORIA", color="STATUS_RECURSO", orientation="h",
                     barmode="stack", text="rotulo", color_discrete_map=cor_status,
                     category_orders={"CATEGORIA": list(totais.index),
                                      "STATUS_RECURSO": [STATUS_ATENDIDO, STATUS_DISPONIVEL]})
        fig.update_traces(textposition="inside", insidetextanchor="middle")
        fig.update_layout(xaxis_title="", yaxis_title="", legend_title="")
        layout_grafico(fig, altura=max(330, 42 * len(totais)))
        st.plotly_chart(fig, width="stretch")

    tabela = base.pivot_table(index="CATEGORIA", columns="STATUS_RECURSO", values="VALOR_NUMERICO",
                               aggfunc="sum", fill_value=0).reset_index()
    for coluna in (STATUS_ATENDIDO, STATUS_DISPONIVEL):
        if coluna not in tabela.columns:
            tabela[coluna] = 0.0
    tabela["Total"] = tabela[STATUS_ATENDIDO] + tabela[STATUS_DISPONIVEL]
    tabela["% atendido"] = (100 * tabela[STATUS_ATENDIDO] / tabela["Total"]).round(0).fillna(0).astype(int).astype(str) + "%"
    tabela = tabela.sort_values("Total", ascending=False)
    exibir = tabela.copy()
    for coluna in (STATUS_ATENDIDO, STATUS_DISPONIVEL, "Total"):
        exibir[coluna] = exibir[coluna].apply(moeda_completa)
    st.dataframe(
        exibir.rename(columns={"CATEGORIA": "Categoria", STATUS_ATENDIDO: "Atendido",
                                STATUS_DISPONIVEL: "Disponível"}),
        hide_index=True, width="stretch",
    )
    st.caption(
        "Categoria e Grupo estratégico são visões DIFERENTES e se sobrepõem (uma Requisição de "
        "Serviço pode ser de Motores) — por isso nunca somar as duas juntas. O total geral sai "
        "sempre dos registros únicos da base."
    )


def _disponivel_por_destinacao(df):
    """Quadro gerencial — onde está o disponível, por grupo estratégico
    (não é o valor histórico total, é só a fatia ainda disponível). Clicar
    numa linha filtra a tabela operacional logo abaixo (via
    `st.session_state["mta_destinacao_selecionada"]`, lido em
    `_tabela_operacional`)."""
    st.markdown('<div class="pj-titulo-secao">Disponível por destinação</div>', unsafe_allow_html=True)
    st.caption(
        "Só a parte AINDA DISPONÍVEL (Aprovado, Trâmite vazio) de cada destinação — não é o valor "
        "histórico total contratado. Clique numa linha da tabela pra ver quais solicitações formam esse valor."
    )

    disponiveis = df[df["disponivel"]]
    if disponiveis.empty:
        st.info("Nada disponível no filtro atual.")
        return

    resumo = disponiveis.groupby("grupo_estrategico").apply(
        lambda g: pd.Series({
            "Disponível": g["valor"].sum(skipna=True),
            "Com TGCO": g.loc[g["com_tgco"], "valor"].sum(skipna=True),
            "Livre": g.loc[g["livre"], "valor"].sum(skipna=True),
            "Linhas": len(g),
        }),
        include_groups=False,
    ).reset_index().rename(columns={"grupo_estrategico": "Destinação"})
    ordem = {g: i for i, g in enumerate(ORDEM_GRUPO_ESTRATEGICO)}
    resumo["_ordem"] = resumo["Destinação"].map(ordem).fillna(999)
    resumo = resumo.sort_values("_ordem").drop(columns="_ordem")

    total_disp = resumo["Disponível"].sum()
    resumo["% do disponível"] = (100 * resumo["Disponível"] / total_disp).round(1) if total_disp else 0.0

    tabela_fmt = resumo.copy()
    for col in ("Disponível", "Com TGCO", "Livre"):
        tabela_fmt[col] = tabela_fmt[col].apply(moeda_completa)
    tabela_fmt["% do disponível"] = tabela_fmt["% do disponível"].apply(lambda v: f"{v:.1f}%")
    tabela_fmt["Linhas"] = tabela_fmt["Linhas"].astype(int)

    evento = st.dataframe(
        tabela_fmt, hide_index=True, width="stretch",
        on_select="rerun", selection_mode="single-row", key="mta_destinacao_tabela",
    )
    linhas_sel = evento.selection.get("rows", []) if evento else []
    if linhas_sel:
        destinacao_clicada = resumo.iloc[linhas_sel[0]]["Destinação"]
        st.session_state["mta_destinacao_selecionada"] = destinacao_clicada
        st.caption(f"👆 Filtrado abaixo pra **{destinacao_clicada}** — clique de novo na mesma linha, ou em \"Limpar seleção de destinação\", pra tirar o filtro.")
        if st.button("Limpar seleção de destinação", key="mta_destinacao_limpar"):
            st.session_state.pop("mta_destinacao_selecionada", None)
            st.rerun()

    with st.expander("ℹ️ Como \"Grupo estratégico\" é decidido (e por que não soma com \"Categoria\")"):
        st.markdown(
            "**Grupo estratégico** (Motores / Consumíveis / Contrato 005 / Modernização / Requisição CABW / "
            "Requisição de Serviço / Requisição FMS / Publicações / Outros contratos / Outros) é uma dimensão "
            "**independente** de **Categoria** (Hora de Voo / Sob Demanda / Parcela Fixa / Requisição, campo "
            "\"Para Contrato\" da planilha) — uma linha de Hora de Voo pode ser do Contrato 005, e uma "
            "requisição pode ser de Motores. **Nunca some as duas juntas** — dá dupla contagem.\n\n"
            "Regra: 1) \"Para Motores\" = Sim vira **Motores**, não importa a atividade (é o único campo "
            "explícito da planilha pra isso). 2) Tarefa contendo \"Consumíveis\" vira **Consumíveis** — existe "
            "tanto na Requisição CABW quanto na Requisição FMS (2 canais de compra diferentes pro mesmo tipo "
            "de item). 3) Daí em diante, pelo texto da Atividade (contrato nomeado, ou \"Outros "
            "contratos\"/\"Outros\" quando não bate com nenhum padrão conhecido). Conferido em 2026-09-03: "
            "cobre 100% do valor da planilha, sem sobra nem duplicata."
        )


def _tabela_operacional(df):
    """Tabela operacional — AG Grid (streamlit-aggrid), estilo planilha:
    scroll H/V, cabeçalho fixo, coluna redimensionável e arrastável,
    ordenação, filtro por coluna (texto/número, com opção "vazio"/"não
    vazio"), seleção múltipla com checkbox. Barra de resumo (visível +
    selecionado) logo abaixo, somando a coluna Valor NUMÉRICA (não o texto
    formatado) — pedido explícito do Wallace, 2026-09-03.

    Filtro do quadro "Disponível por destinação" (se houver) aplicado
    ANTES de entrar na grade — column filter do próprio AG Grid continua
    livre por cima disso."""
    st.markdown('<div class="pj-titulo-secao">Tabela operacional</div>', unsafe_allow_html=True)

    destinacao_sel = st.session_state.get("mta_destinacao_selecionada")
    base = df
    if destinacao_sel:
        base = df[df["grupo_estrategico"] == destinacao_sel]
        st.caption(f"Filtrado por destinação selecionada acima: **{destinacao_sel}** ({len(base)} linha(s)).")

    extras = st.multiselect(
        "+ Mais colunas", [c for c in COLUNAS_TABELA_EXTRA if c in base.columns],
        format_func=lambda c: NOMES_COLUNAS.get(c, c), key="mta_tabela_colunas_extra",
    )
    colunas = COLUNAS_TABELA_PADRAO + extras
    tabela = base[colunas].copy()
    tabela["mes_previsto"] = pd.to_datetime(tabela["mes_previsto"], errors="coerce")
    if "data_pedido" in tabela.columns:
        tabela["data_pedido"] = pd.to_datetime(tabela["data_pedido"], errors="coerce")
    tabela = tabela.rename(columns=NOMES_COLUNAS)

    formatador_moeda = JsCode(
        "function(params){ if (params.value == null) { return ''; } "
        "return 'R$ ' + params.value.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2}); }"
    )
    # NaT/None/"NaT" viram vazio, e data inválida devolve o texto original em
    # vez de "Invalid Date" (bug visto no teste de 2026-09-03: coluna "Data do
    # pedido" aparecia como "Invalid" nas linhas sem data).
    formatador_data = JsCode(
        "function(params){ var v = params.value; "
        "if (v === null || v === undefined || v === '' || v === 'NaT' || v === 'None') { return ''; } "
        "var d = new Date(v); "
        "if (isNaN(d.getTime())) { return String(v); } "
        "return d.toLocaleDateString('pt-BR', {day:'2-digit', month:'2-digit', year:'numeric'}); }"
    )
    filtro_texto_com_vazio = {
        "filter": "agTextColumnFilter",
        "filterParams": {"filterOptions": ["contains", "notContains", "equals", "blank", "notBlank"], "trimInput": True},
        "floatingFilter": True,
    }

    gb = GridOptionsBuilder.from_dataframe(tabela)
    # Larguras generosas de propósito — Wallace, 2026-09-03: "NÃO tentar
    # espremer todas as colunas na largura da tela, quero poder navegar
    # horizontalmente como Excel". Por isso `suppressSizeToFit` + nenhum
    # auto-size global: a grade fica mais larga que a tela e ganha scroll H.
    gb.configure_default_column(
        resizable=True, sortable=True, filter=True, floatingFilter=True, editable=False,
        width=180, minWidth=110, suppressSizeToFit=True, wrapHeaderText=True, autoHeaderHeight=True,
    )
    gb.configure_selection("multiple", use_checkbox=True, header_checkbox=True)
    gb.configure_pagination(enabled=False)
    gb.configure_grid_options(domLayout="normal", suppressColumnVirtualisation=True)

    for coluna in tabela.columns:
        if coluna == "Valor":
            gb.configure_column(coluna, type=["numericColumn"], filter="agNumberColumnFilter",
                                 valueFormatter=formatador_moeda, pinned="right", width=170)
        elif coluna in ("Mês planejamento atual", "Data do pedido"):
            gb.configure_column(coluna, valueFormatter=formatador_data, filter="agDateColumnFilter", width=170)
        elif coluna == "Linha":
            gb.configure_column(coluna, pinned="left", width=120, **filtro_texto_com_vazio)
        else:
            largura = 320 if coluna in ("Atividade", "Tarefa", "Situação consolidada") else 190
            gb.configure_column(coluna, **filtro_texto_com_vazio, width=largura)

    # Datas viram texto ISO (ou vazio) antes de entrar na grade — Timestamp/NaT
    # do pandas chega como objeto e o JS não consegue converter.
    for coluna in tabela.columns:
        if pd.api.types.is_datetime64_any_dtype(tabela[coluna]):
            tabela[coluna] = tabela[coluna].dt.strftime("%Y-%m-%d").where(tabela[coluna].notna(), "")

    grid_options = gb.build()

    grid_resposta = AgGrid(
        tabela,
        gridOptions=grid_options,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.MODEL_CHANGED | GridUpdateMode.SELECTION_CHANGED,
        allow_unsafe_jscode=True,
        columns_auto_size_mode=ColumnsAutoSizeMode.NO_AUTOSIZE,
        theme="alpine",
        height=460,
        key="mta_aggrid",
    )

    visivel = grid_resposta["data"]
    if not isinstance(visivel, pd.DataFrame):
        visivel = pd.DataFrame(visivel)
    selecionado = grid_resposta.get("selected_rows")
    if selecionado is None:
        selecionado = pd.DataFrame(columns=tabela.columns)
    elif not isinstance(selecionado, pd.DataFrame):
        selecionado = pd.DataFrame(selecionado)

    def _soma_valor(dframe):
        if dframe is None or dframe.empty or "Valor" not in dframe.columns:
            return 0.0
        return pd.to_numeric(dframe["Valor"], errors="coerce").sum(skipna=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f"""<div style="background:{PANEL};border:1px solid {LINE};border-radius:10px;padding:12px 16px;">
                <div style="font-size:12px;color:{SECONDARY};text-transform:uppercase;letter-spacing:0.04em;">Visível</div>
                <div style="font-size:20px;font-weight:700;color:{INK};">{len(visivel)} linha(s)</div>
                <div style="font-size:14px;color:{AMBER};font-weight:600;">{moeda_completa(_soma_valor(visivel))}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""<div style="background:{PANEL};border:1px solid {LINE};border-radius:10px;padding:12px 16px;">
                <div style="font-size:12px;color:{SECONDARY};text-transform:uppercase;letter-spacing:0.04em;">Selecionado</div>
                <div style="font-size:20px;font-weight:700;color:{INK};">{len(selecionado)} linha(s)</div>
                <div style="font-size:14px;color:{STATUS['good']};font-weight:600;">{moeda_completa(_soma_valor(selecionado))}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    st.caption(f"{len(base)} linha(s) na base (após filtros gerais da página) · {len(tabela.columns)} coluna(s) visíveis.")

    csv = tabela.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar (CSV)", csv, file_name="mta.csv", mime="text/csv", key="mta_export_csv")

    if not selecionado.empty and "Linha" in selecionado.columns:
        primeira = selecionado.iloc[0]
        registro = base[base["linha"] == primeira["Linha"]]
        if not registro.empty:
            _painel_detalhe(registro.iloc[0].to_dict())


def _analise_mensal_tgco(df):
    """Gráficos que respondem a decisão (pedido do Wallace, 2026-09-03:
    "diminuir prioridade dos gráficos... manter só o que responde a
    decisão"): composição do disponível (TGCO x livre), disponível por
    mês (quanto precisa ser usado quando) e disponível por destinação."""
    st.markdown('<div class="pj-titulo-secao">Análise mensal / TGCO</div>', unsafe_allow_html=True)

    disponiveis = df[df["disponivel"]]
    if disponiveis.empty:
        st.info("Nada disponível no filtro atual pra essa análise.")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.caption("Composição do disponível — com TGCO x livre")
        comp = pd.DataFrame([
            {"tipo": "Com providência TGCO", "valor": disponiveis.loc[disponiveis["com_tgco"], "valor"].sum(skipna=True)},
            {"tipo": "Livre", "valor": disponiveis.loc[disponiveis["livre"], "valor"].sum(skipna=True)},
        ])
        fig = px.pie(comp, names="tipo", values="valor", hole=0.55,
                     color="tipo", color_discrete_map={"Com providência TGCO": STATUS["warning"], "Livre": STATUS["neutro"]})
        fig.update_traces(textinfo="percent", hovertemplate="%{label}: %{customdata[0]}<extra></extra>",
                           customdata=[[moeda_completa(v)] for v in comp["valor"]], textfont_size=13)
        layout_grafico(fig, altura=320)
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.caption("Disponível por mês (Mês planejamento atual)")
        serie = disponiveis.dropna(subset=["mes_previsto"]).copy()
        if serie.empty:
            st.info("Nenhuma linha disponível tem mês previsto preenchido.")
        else:
            serie["mes"] = pd.to_datetime(serie["mes_previsto"]).dt.to_period("M").astype(str)
            agrupado = serie.groupby("mes")["valor"].sum(min_count=1).reset_index().sort_values("mes")
            agrupado["mes_label"] = agrupado["mes"].apply(_mes_ano)
            fig = px.bar(agrupado, x="mes_label", y="valor", color_discrete_sequence=[AMBER])
            _rotular_barras(fig, agrupado["valor"])
            fig.update_layout(xaxis_title="", yaxis_title="")
            layout_grafico(fig, altura=320)
            st.plotly_chart(fig, width="stretch")

    st.caption("Disponível por grande destinação")
    resumo = disponiveis.groupby("grupo_estrategico")["valor"].sum(min_count=1).reset_index()
    ordem = {g: i for i, g in enumerate(ORDEM_GRUPO_ESTRATEGICO)}
    resumo["_ordem"] = resumo["grupo_estrategico"].map(ordem).fillna(999)
    resumo = resumo.sort_values("_ordem")
    fig = px.bar(resumo, x="grupo_estrategico", y="valor", color_discrete_sequence=[CATEGORICA[1]])
    _rotular_barras(fig, resumo["valor"])
    fig.update_layout(xaxis_title="", yaxis_title="")
    layout_grafico(fig, altura=320)
    st.plotly_chart(fig, width="stretch")


def _disponivel_por_mes(df):
    """Item 26 — quanto do disponível está previsto pra cada mês (usa
    "Mês previsto", NUNCA a Data do pedido). Linha sem mês aparece como
    "Sem mês", não some da conta."""
    st.markdown('<div class="pj-titulo-secao">Disponível por mês</div>', unsafe_allow_html=True)

    disponiveis = df[df["DISPONIVEL_BOOL"]].copy()
    if disponiveis.empty:
        st.info("Nada disponível no filtro atual.")
        return

    disponiveis["_mes"] = disponiveis["MES_PLANEJAMENTO"].fillna("Sem mês")
    resumo = disponiveis.groupby("_mes").agg(
        valor=("VALOR_NUMERICO", "sum"), linhas=("linha", "count")
    ).reset_index()
    com_mes = resumo[resumo["_mes"] != "Sem mês"].sort_values("_mes")
    sem_mes = resumo[resumo["_mes"] == "Sem mês"]
    resumo = pd.concat([com_mes, sem_mes])
    resumo["rotulo_mes"] = resumo["_mes"].apply(lambda m: _mes_ano(m) if m != "Sem mês" else "Sem mês")

    col1, col2 = st.columns([2, 1])
    with col1:
        fig = px.bar(resumo, x="rotulo_mes", y="valor", color_discrete_sequence=[STATUS["info"]])
        _rotular_barras(fig, resumo["valor"])
        fig.update_layout(xaxis_title="", yaxis_title="")
        layout_grafico(fig, altura=330)
        st.plotly_chart(fig, width="stretch")
    with col2:
        exibir = resumo[["rotulo_mes", "valor", "linhas"]].copy()
        exibir["valor"] = exibir["valor"].apply(moeda_completa)
        st.dataframe(
            exibir.rename(columns={"rotulo_mes": "Mês previsto", "valor": "Disponível", "linhas": "Linhas"}),
            hide_index=True, width="stretch", height=330,
        )


def _nao_classificados(df):
    """Item 54 — nada de decisão silenciosa: toda linha que não casou com
    nenhuma regra de categoria aparece listada aqui, pra virar regra nova
    depois (REGRAS_CATEGORIA em projetos/regras/mta_regras.py)."""
    nc = df[df["CATEGORIA"] == NAO_CLASSIFICADO]
    if nc.empty:
        st.caption("✅ Todas as linhas casaram com alguma regra de categoria — nenhum \"Não classificado\".")
        return
    with st.expander(f"⚠️ {len(nc)} linha(s) sem regra de categoria — precisam de regra nova"):
        st.dataframe(
            nc[["linha", "atividade", "tarefa", "VALOR_NUMERICO"]].rename(columns={
                "linha": "Linha", "atividade": "Atividade", "tarefa": "Tarefa", "VALOR_NUMERICO": "Valor",
            }),
            hide_index=True, width="stretch",
        )


def _indicadores(df):
    total = len(df)
    aprovadas = int((df["aprovado"].apply(normalizar) == "SIM").sum())
    nao_aprovadas = int((df["aprovado"].apply(normalizar) == "NAO").sum())
    atendidas = int((df["situacao_consolidada"] == "Atendido").sum())
    em_tramite = int((df["situacao_consolidada"] == "Em trâmite").sum())
    valor_total = df["valor"].sum(skipna=True)
    valor_motores = df.loc[df["para_motores"].apply(normalizar) == "SIM", "valor"].sum(skipna=True)
    pct_atendidas = f"{100 * atendidas / total:.0f}% do total" if total else None

    st.markdown('<div class="pj-titulo-secao">Indicadores gerais (contagem)</div>', unsafe_allow_html=True)
    st.caption("Volume de solicitações — pra recurso financeiro disponível, ver \"Disponibilidade financeira\" no topo da página.")
    cards = [
        cartao_indicador("Total de solicitações", total, "Registros do C-98", "primary"),
        cartao_indicador("Atendidas", atendidas, pct_atendidas, "good"),
        cartao_indicador("Não aprovadas", nao_aprovadas, "Requerem análise" if nao_aprovadas else None, "critical"),
        cartao_indicador("Aprovadas", aprovadas, None, "info"),
    ]
    if em_tramite:
        cards.append(cartao_indicador("Em trâmite", em_tramite, None, "warning"))
    cards.append(cartao_indicador("Valor relacionado a motores", moeda_compacta(valor_motores), moeda_completa(valor_motores), "info"))
    grade_indicadores(cards)


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
    st.markdown('<div class="pj-titulo-secao">Análise financeira (histórico completo)</div>', unsafe_allow_html=True)

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
        st.caption("O que já chegou x o que ainda falta (por categoria operacional)")
        trabalho = df.copy()
        trabalho["categoria_antiga"] = trabalho.apply(_categoria_destinacao, axis=1)
        trabalho["situacao_chegada"] = trabalho["situacao_consolidada"].apply(
            lambda s: "Já atendido" if s == "Atendido" else "Ainda pendente"
        )
        agrupado = trabalho.groupby(["categoria_antiga", "situacao_chegada"])["valor"].sum(min_count=1).reset_index()
        if agrupado.empty:
            st.info("Sem dados suficientes pra essa quebra.")
        else:
            agrupado["rotulo"] = agrupado["valor"].apply(moeda_compacta)
            fig = px.bar(
                agrupado, x="categoria_antiga", y="valor", color="situacao_chegada", barmode="stack",
                text="rotulo",
                color_discrete_map={"Já atendido": STATUS["good"], "Ainda pendente": STATUS["warning"]},
                category_orders={"situacao_chegada": ["Já atendido", "Ainda pendente"]},
            )
            fig.update_traces(textposition="inside")
            fig.update_layout(xaxis_title="", yaxis_title="", legend_title="")
            layout_grafico(fig, altura=340)
            st.plotly_chart(fig, width="stretch")

    resumo = df.assign(categoria_antiga=df.apply(_categoria_destinacao, axis=1)).groupby("categoria_antiga").apply(
        lambda g: pd.Series({
            "Valor total": g["valor"].sum(skipna=True),
            "Já atendido": g.loc[g["situacao_consolidada"] == "Atendido", "valor"].sum(skipna=True),
            "Ainda pendente": g.loc[g["situacao_consolidada"] != "Atendido", "valor"].sum(skipna=True),
        }),
        include_groups=False,
    ).reset_index().rename(columns={"categoria_antiga": "Categoria"})
    resumo["% atendido"] = (100 * resumo["Já atendido"] / resumo["Valor total"]).round(0).astype("Int64").astype(str) + "%"
    for col in ("Valor total", "Já atendido", "Ainda pendente"):
        resumo[col] = resumo[col].apply(moeda_completa)
    st.dataframe(resumo, hide_index=True, width="stretch")

    with st.expander("ℹ️ O que entra em cada categoria (operacional, campo \"Para Contrato\")"):
        st.markdown(
            "- **Hora de Voo** — só o Contrato 005/CELOG-PAMALS (VEE ONE): as 10 parcelas anuais "
            "de horas de voo (\"Hora de Voo 01/10\" a \"10/10\"), ~1000 HV cada.\n"
            "- **Motores** — qualquer linha com \"Para Motores\" = Sim, **de vários contratos "
            "diferentes** (não só o 005): Revisão Geral (RG) e material de motor do CNT 006/2026, "
            "CNT 048/2022 e CNT 031/2022 (todos PW/PAMASP), câmbio de motor (CABW-PAMASP/2026) e "
            "requisições de serviço/publicação ligadas a motor.\n"
            "- **Requisição** — pedidos de material/serviço fora do escopo de Hora de Voo e Motores: "
            "Requisição CABW (ex.: consumíveis, GPS), Requisição FMS e pedidos pontuais por base "
            "(ex.: \"2025-BABR-24\").\n"
            "- **Sob Demanda** — só Contrato 005 (VEE ONE): \"Módulo Extra\", trabalho extra além das "
            "parcelas fixas de Hora de Voo (aquisição, publicações).\n"
            "- **Parcela Fixa** — projeto de Modernização do C-98 (contrato à parte, ainda sem número "
            "definido — \"CNT XXX/CELOG-PAMALS/2026\"), em 4 parcelas.\n\n"
            "Essa é a categoria **operacional** (campo bruto da planilha) — pra visão estratégica "
            "(Motores/Consumíveis/Contrato 005/...), ver \"Disponível por destinação\" no topo da página."
        )


def _projetar_saldo(saldo_inicial, media_mensal, fila_hv, horizonte_meses=15):
    """Projeção mês a mês do saldo real do Contrato 005: parte do saldo em
    aberto de hoje, soma cada parcela de Hora de Voo que ainda vai virar
    empenho ("Mês previsto" do MTA é o mês de USO — o empenho de fato
    acontece 1 mês depois, ex.: horas de junho são empenhadas em julho) e
    subtrai o gasto médio mensal (ver `_analise_saldo`). `fila_hv` NÃO deve
    incluir RAP — Wallace, 2026-07-30: "o valor de RAP da MTA já foi
    processo, virou dinheiro e já usei, o resultado dele são os empenhos
    que não são final 2026, então tira ele da linha cronológica de
    entrada" — o RAP já está refletido no `saldo_inicial` (via saldo dos
    empenhos pré-2026 do Contrato 005), contá-lo de novo aqui como entrada
    futura duplicaria esse dinheiro. Devolve (tabela mês a mês, primeiro
    mês em que o saldo fica negativo — ou None se não fica, dentro do
    horizonte, detalhe por mês de quais parcelas do MTA entram nesse mês —
    pra painel clicável)."""
    mes0 = pd.Timestamp(horario.hoje_br()).replace(day=1)

    entradas = {}
    detalhe_entradas = {}
    for _, row in fila_hv.iterrows():
        valor = row["valor"] or 0
        if pd.isna(valor) or pd.isna(row["mes_previsto"]):
            continue
        mes_uso = pd.Timestamp(row["mes_previsto"]).replace(day=1)
        mes_empenho = max(mes_uso + pd.DateOffset(months=1), mes0)
        entradas[mes_empenho] = entradas.get(mes_empenho, 0) + valor
        detalhe_entradas.setdefault(mes_empenho, []).append({"parcela": str(row["tarefa"]), "valor": valor})

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


def _empenhado_ate_calendario():
    """Até qual mês o empenho de Hora de Voo já está feito, e qual é o
    próximo — direto do calendário, sem depender do "Atendido" do MTA (que
    não bate 1:1 com a data real do empenho). Regra confirmada pelo
    Wallace em 2026-07-28: "horas de junho, empenhado em julho" — o
    empenho de um mês de uso acontece no mês seguinte, então o mês de uso
    corrente (hoje) só termina de ser empenhado no mês que vem; o mês de
    uso anterior já foi. Devolve (mes_uso_feito, mes_empenho_feito,
    mes_uso_proximo, mes_empenho_proximo)."""
    mes_atual = pd.Timestamp(horario.hoje_br()).replace(day=1)
    mes_uso_feito = mes_atual - pd.DateOffset(months=1)
    mes_empenho_feito = mes_atual
    mes_uso_proximo = mes_atual
    mes_empenho_proximo = mes_atual + pd.DateOffset(months=1)
    return mes_uso_feito, mes_empenho_feito, mes_uso_proximo, mes_empenho_proximo


def _analise_saldo(df, dados):
    """Análise do dinheiro em saldo (Hora de Voo) — Contrato 005. INTOCADA
    desde sempre (pedido explícito do Wallace, 2026-09-03: "não misturar a
    lógica do saldo real do Contrato 005 com o saldo de linhas MTA" / "não
    remover"). Só mudou de POSIÇÃO na página (agora depois da visão geral
    de recursos, não mais logo no início) — nenhum cálculo foi alterado."""
    st.markdown('<div class="pj-titulo-secao">Análise do dinheiro em saldo (Hora de Voo) — Contrato 005</div>', unsafe_allow_html=True)
    st.caption(
        "Cruza a fila de solicitações de Hora de Voo do MTA com o dinheiro real do "
        "Contrato 005 (VEE ONE) — a aba \"Empenhos\" não distingue categoria (o mesmo "
        "código ND cobre Hora de Voo, Parcela Fixa, Requisição e Sob Demanda), então o "
        "valor empenhado/saldo abaixo é do **contrato inteiro**, não só Hora de Voo. O "
        "\"Mês previsto\" do MTA é o **mês de uso** — o empenho de fato acontece 1 mês "
        "depois (ex.: horas de junho são empenhadas em julho; Wallace, 2026-07-28: "
        "\"horas de junho, empenhado em julho\"). RAP = saldo de empenho que não é "
        "diretamente de 2026 (ano anterior), ainda não usado — prioridade de uso."
    )

    empenhos_info = dados.get("empenhos_contrato005")
    if empenhos_info is not None:
        emp = empenhos_info["empenhos"].copy()
        emp["ano"] = emp["numero_empenho"].astype(str).str[:4]
        eh_rap_emp = emp["ano"] != "2026"

        saldo_total_real = emp["saldo"].sum(skipna=True)
        saldo_rap = emp.loc[eh_rap_emp, "saldo"].sum(skipna=True)
    else:
        emp = None
        eh_rap_emp = None
        saldo_total_real = saldo_rap = None

    hv = df[df["para_contrato"] == "HORA DE VOO"].copy()
    eh_rap_mta = hv["pacote"] == "RAP"
    atendido = hv[hv["situacao_consolidada"] == "Atendido"]
    fila_mta = hv[(hv["situacao_consolidada"] != "Atendido") & ~eh_rap_mta]
    rap_mta = hv[eh_rap_mta]
    # Projeção usa só a fila (sem RAP) — RAP já virou empenho de verdade e
    # já está refletido no saldo inicial (saldo dos empenhos pré-2026), contá-lo
    # de novo como entrada futura duplicaria o dinheiro.
    fila_projetavel = fila_mta

    # Dinheiro do ano da MTA (não é saldo do contrato) — Wallace,
    # 2026-07-28: "acho q se somar dinheiro so do contrato da na aba
    # atividade da planilha mta da aba solicitações" / "é dinheiro do ano
    # da mta e nao o saldo do contrato". Filtra TODO o MTA (não só Hora de
    # Voo) pela Atividade "CNT 005/CELOG-PAMALS/2025 - VEE ONE" — pega
    # também as poucas linhas de Sob Demanda que são desse mesmo contrato,
    # substitui o "Saldo do Contrato após 2° Reajuste" (R$76,9 mi, que é
    # só o teto de autorização plurianual, número grande demais e sem
    # relação direta com o ano corrente).
    cnt005_mta = df[df["atividade"] == "CNT 005/CELOG-PAMALS/2025 - VEE ONE"]
    dinheiro_ano_mta = cnt005_mta["valor"].sum(skipna=True)
    dinheiro_ano_mta_atendido = cnt005_mta.loc[cnt005_mta["situacao_consolidada"] == "Atendido", "valor"].sum(skipna=True)
    dinheiro_ano_mta_saldo = dinheiro_ano_mta - dinheiro_ano_mta_atendido

    mes_uso_feito, mes_emp_feito, mes_uso_prox, mes_emp_prox = _empenhado_ate_calendario()

    # Média de gasto mensal — Wallace, 2026-07-28: "media de gasto nao é do
    # cronograma é o real, quantas horas falta no ano? [...] divide por
    # quantos meses nao paguei e multiplica pela hora de voo (valor)".
    # "Meses não pagos" = meses de uso (a partir de hoje até dezembro)
    # cujo empenho ainda não aconteceu — o mês corrente conta (seu
    # empenho só sai no mês que vem). Horas restantes vêm da
    # Disponibilidade Diária (Coordenadoria) — "horas nao voadas e
    # extraida na disp diaria, tem a quantidade disponivel ai ainda":
    # esforço anual previsto − realizado, dado operacional real (cresce
    # dia a dia), mais confiável que somar "1000 HV" do texto das
    # parcelas do MTA (que é só o que foi parcelado/orçado). Cai pro texto
    # das parcelas só se a Disponibilidade Diária não estiver disponível.
    esforco_anual = dados.get("esforco_anual")
    if esforco_anual is not None:
        horas_restantes = esforco_anual["horas_nao_voadas"]
        fonte_horas = f"Disponibilidade Diária, {pd.Timestamp(esforco_anual['data_referencia']).strftime('%d/%m/%Y')} — {esforco_anual['horas_previstas']:.0f}h previstas − {esforco_anual['horas_realizadas']:.0f}h realizadas"
    else:
        pendente_hv = pd.concat([fila_mta, rap_mta])
        horas_restantes = pendente_hv["tarefa"].str.extract(r"(\d+)\s*HV")[0].astype(float).sum()
        fonte_horas = "Somado das parcelas MTA (fila + RAP) — Disponibilidade Diária não encontrada"
    valor_hora_voo = empenhos_info.get("valor_hora_voo") if empenhos_info is not None else None
    meses_nao_pagos = max(12 - mes_uso_prox.month + 1, 1)
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
        cartoes_empenho = [
            cartao_indicador("Dinheiro do ano (MTA, CNT 005/VEE ONE)", moeda_compacta(dinheiro_ano_mta),
                              "Toda solicitação do MTA dessa atividade (Hora de Voo + Sob Demanda)", "primary"),
            cartao_indicador("→ já atendido", moeda_compacta(dinheiro_ano_mta_atendido),
                              "Virou empenho", "good"),
            cartao_indicador("→ saldo (ainda não atendido)", moeda_compacta(dinheiro_ano_mta_saldo),
                              "Fila + RAP, ainda não virou empenho", "warning"),
        ]
        if empenhos_info is not None:
            cartoes_empenho += [
                cartao_indicador("Saldo dos empenhos (ainda não liquidado)", moeda_compacta(saldo_total_real),
                                  "Já é dinheiro formal, só falta gastar/liquidar", "warning"),
                cartao_indicador("→ dos quais RAP (pré-2026)", moeda_compacta(saldo_rap),
                                  "Prioridade: já deveria ter sido usado" if saldo_rap else "Sem RAP no momento",
                                  "critical" if saldo_rap else "neutro"),
            ]
        else:
            st.info("Dados de empenhos do Contrato 005 não encontrados em 02_Dados_Tratados/ — mostrando só o dinheiro do MTA.")
        grade_indicadores(cartoes_empenho)

        if media_mensal:
            st.divider()
            st.markdown("###### Consumo (Hora de Voo) — conta aberta")
            # "$" dispara modo matemático (LaTeX) no markdown do Streamlit —
            # escapa pra "R$" aparecer como texto, não sumir no meio da conta.
            conta = (
                f"Horas não voadas = **{horas_restantes:.0f} HV** ÷ "
                f"**{meses_nao_pagos} mês(es) não pago(s)** × **{moeda_completa(valor_hora_voo)}/HV** "
                f"= **{moeda_completa(media_mensal)}/mês**"
            ).replace("R$", "R\\$")
            st.markdown(conta)
            grade_indicadores([
                cartao_indicador("Horas não voadas", f"{horas_restantes:.0f} HV", fonte_horas, "warning"),
                cartao_indicador("÷ meses não pagos", str(meses_nao_pagos),
                                  f"Uso de {_mes_ano(mes_uso_prox.strftime('%Y-%m'))} até dez/{mes_uso_prox.year}", "neutro"),
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
            "hoje, soma cada parcela de Hora de Voo ainda na fila (sem RAP — RAP já virou empenho de "
            "verdade e já está no saldo inicial, contar de novo duplicaria) deslocada 1 mês pela "
            "defasagem empenho→uso, e subtrai o gasto médio mensal (ver conta em \"Consumo\", na aba "
            "Resumo — horas restantes ÷ meses não pagos × valor da hora de voo). Não considera novos "
            "ciclos de MTA além do que já está na fila — se a DIRMAB atrasar uma parcela, a data muda."
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

    filtrado = _filtros(_preparar(df))

    st.divider()
    _disponibilidade_financeira(filtrado)
    st.divider()
    _atendido_x_disponivel(filtrado)
    st.divider()
    _disponivel_por_destinacao(filtrado)
    st.divider()
    _tabela_operacional(filtrado)
    st.divider()
    _disponivel_por_mes(filtrado)
    st.divider()

    with st.expander("📊 Análises secundárias (TGCO, situação, executora, pacote)"):
        _analise_mensal_tgco(filtrado)
        st.divider()
        _indicadores(filtrado)
        st.divider()
        _situacao(filtrado)
        st.divider()
        _analise_financeira(filtrado)

    st.divider()
    _analise_saldo(filtrado, dados)

    st.divider()
    _nao_classificados(filtrado)

    st.divider()
    secao_evolucao(
        dados.get("mta_historico"), chave=["linha"], key_slider="mta_evolucao_slider",
        colunas_exibir=["linha", "situacao_consolidada", "aprovado", "tramite", "valor", "executora", "pacote"],
        nomes_colunas={
            "linha": "Linha", "situacao_consolidada": "Situação consolidada", "aprovado": "Aprovado",
            "tramite": "Trâmite", "valor": "Valor", "executora": "Executora", "pacote": "Pacote",
        },
    )
