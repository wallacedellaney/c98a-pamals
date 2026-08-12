"""Tela de detalhe — Reparáveis."""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from shared import horario
from contrato005.components import data_global
from contrato005.components.paleta import AMBER, CATEGORICA, STATUS, layout_grafico
from contrato005.components.utils import ordenar_unicos

SCRIPTS_PYTHON = Path(__file__).resolve().parents[3] / "05_Scripts" / "python"
if str(SCRIPTS_PYTHON) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PYTHON))

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

MESES_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def _mesclar_complemento_rma(df, complemento):
    """Mescla "Data de devolução empresa"/"Onde se encontra"/"Recibo" vindos
    da RMA em andamento do mês por cima da planilha geral, só pras OS que a
    RMA já confirma como devolvidas — pedido do Wallace, 2026-08-12: a
    burocracia da OS pode continuar aberta na planilha geral por um tempo
    mesmo depois da empresa já ter devolvido de verdade (ver RMA, aba 1.8 +
    1.10). Nunca inventa: só sobrescreve os 3 campos quando a RMA de fato
    trouxe um valor pra aquela OS; `situacao`/`em_aberto` continuam vindo só
    da planilha geral (não foi pedido mexer nisso). Cria a coluna `fonte`
    (ex.: "RMA Julho/2026") — vazia pra OS sem complemento, indicando que a
    informação é só da planilha geral mesmo.

    **TAT real calculado (2026-08-12)** — Wallace: "a empresa tem mais OS
    né, acho que ela computou desde o início [...] vamos pegar o que tá com
    OS concluída na nossa planilha e buscar os dados de entrega na deles,
    para irmos criando o TAT real se tiver data de entrega [...] ou
    completar com o que tiver". A 1.10 da RMA cobre bem mais OS do que a
    planilha geral já tem `tat_empresa` preenchido (o "TAT" que a própria
    empresa relata lá) — quando falta `tat_empresa` mas a gente tem
    `data_inicio` (planilha geral) e a data de devolução (RMA), calcula
    `tat_empresa = (data_devolução − data_início).dias` — não é inventar
    dado, é derivar de 2 datas reais. `tat_calculado=True` marca as linhas
    onde isso aconteceu (a "Fonte" ganha o sufixo "— TAT calculado")."""
    df = df.copy()
    df["fonte"] = ""
    df["tat_calculado"] = False
    if complemento is None or complemento.empty:
        return df

    # `data_entrega` é datetime64 na base tratada — pode receber tanto uma
    # data real (data_devolucao_empresa) quanto texto ambíguo não-parseável
    # (data_devolucao_empresa_texto, ex.: "14/5/2025 E 25/07/2025"), então
    # precisa virar coluna de objeto antes de misturar os dois tipos.
    df["data_entrega"] = df["data_entrega"].astype(object)

    mais_recente = (
        complemento.sort_values(["ano_referencia", "mes_referencia"])
        .drop_duplicates("os", keep="last")
        .set_index("os")
    )
    df["os"] = df["os"].astype(str)
    for numero_os, linha in mais_recente.iterrows():
        idx = df.index[df["os"] == numero_os]
        if idx.empty:
            continue
        if linha["onde_se_encontra"]:
            df.loc[idx, "onde_se_encontra"] = linha["onde_se_encontra"]
        if linha["recibo"]:
            df.loc[idx, "recibo"] = linha["recibo"]
        if pd.notna(linha["data_devolucao_empresa"]):
            df.loc[idx, "data_entrega"] = linha["data_devolucao_empresa"]
        elif linha["data_devolucao_empresa_texto"]:
            df.loc[idx, "data_entrega"] = linha["data_devolucao_empresa_texto"]
        # Condenado (aba 1.9 da RMA) — sobrescreve "Condição" mesmo que a
        # planilha geral ainda mostre "EM REPARO" (burocracia em aberto),
        # com o motivo de condenação junto.
        if bool(linha.get("condenado", False)):
            motivo = linha.get("motivo_condenacao")
            df.loc[idx, "condicao"] = f"CONDENADO — {motivo}" if motivo else "CONDENADO"

        fonte = linha["fonte"]
        # TAT real calculado — só quando falta tat_empresa E temos as 2
        # datas reais (data_inicio da planilha geral + devolução da RMA).
        tat_atual = df.loc[idx, "tat_empresa"]
        data_inicio = df.loc[idx, "data_inicio"]
        if tat_atual.isna().all() and pd.notna(linha["data_devolucao_empresa"]) and data_inicio.notna().all():
            dias = (pd.Timestamp(linha["data_devolucao_empresa"]) - data_inicio).dt.days
            df.loc[idx, "tat_empresa"] = dias
            df.loc[idx, "tat_calculado"] = True
            fonte = f"{fonte} — TAT calculado" if fonte else "TAT calculado (RMA)"
        df.loc[idx, "fonte"] = fonte
    return df


def _secao_complemento_rma():
    """Botão pra repetir, em qualquer mês futuro, o cruzamento que o Wallace
    pediu manualmente em 2026-08-12 pra julho — sem precisar pedir de novo
    na conversa. Ver `extrair_reparaveis_rma.py`."""
    with st.expander("🔄 Complementar com a RMA em andamento do mês"):
        st.caption(
            "Busca no Drive a \"RMA em andamento\" (ou \"Pré RMA\") do mês escolhido e complementa \"ONDE SE "
            "ENCONTRA\"/\"Data de devolução empresa\"/\"RECIBO CASO TENHA\"/\"Condição\" na tabela acima, "
            "pras OS que a burocracia da planilha geral ainda não fechou — cruzando a aba 1.10 (todo o "
            "controle de OS, marcando quais a 1.8 confirma como entregues NESTE mês) e a 1.9 (condenados)."
        )
        hoje = horario.hoje_br()
        col_ano, col_mes, col_botao = st.columns([1, 2, 2])
        with col_ano:
            ano = st.number_input("Ano", min_value=2025, max_value=2035, value=hoje.year, step=1, key="rep_rma_ano")
        with col_mes:
            mes = st.selectbox(
                "Mês", options=list(range(1, 13)), index=hoje.month - 1,
                format_func=lambda m: MESES_PT[m - 1], key="rep_rma_mes",
            )
        with col_botao:
            st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
            if st.button("Buscar e complementar", key="rep_rma_buscar", width="stretch"):
                with st.spinner("Buscando a RMA do mês no Drive..."):
                    try:
                        from shared import drive_sync
                        drive_sync.garantir_credencial_arquivo()
                        import extrair_reparaveis_rma
                        resultado = extrair_reparaveis_rma.atualizar_do_mes(int(ano), int(mes))
                        st.success(
                            f"Complementado a partir de \"{resultado['arquivo']}\": "
                            f"{resultado['os_complementadas_no_mes']} OS com dado (1.10 + 1.9) "
                            f"({resultado['os_entregues_no_mes']} entregues neste mês [aba 1.8] + "
                            f"{resultado['os_historico']} histórico de meses anteriores, "
                            f"{resultado['os_condenadas']} condenadas [aba 1.9]; "
                            f"{resultado['total_acumulado']} acumuladas no total, "
                            f"{resultado['inconsistencias']} inconsistência(s) — ver log em 06_Logs/)."
                        )
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Falha ao buscar/complementar: {e}")


def _secao_historico_mensal(df):
    """Número de OS abertas (campo Data Início) por mês — pedido do
    Wallace, 2026-08-03: "coloca uma coluna tb do historico por mes de
    numero de aberturas". Usa TODAS as OS (abertas e concluídas, não só as
    em aberto hoje) — "abertura" é sobre quando a OS entrou, não sobre a
    situação atual dela."""
    st.markdown("##### Histórico mensal — número de aberturas")
    st.caption("Quantidade de OS abertas (Data Início) por mês, independente da situação atual (em aberto ou já concluída).")

    hist = df.copy()
    hist["mes"] = hist["data_inicio"].dt.to_period("M")
    contagem = hist.groupby("mes").size().reset_index(name="Aberturas").sort_values("mes")
    contagem["Mês"] = contagem["mes"].apply(lambda p: f"{MESES_PT[p.month - 1]}/{p.year}")

    fig = px.bar(contagem, x="Mês", y="Aberturas", color_discrete_sequence=[CATEGORICA[0]])
    fig.update_traces(text=contagem["Aberturas"], textposition="outside")
    fig.update_layout(xaxis_title="", yaxis_title="Nº de aberturas", showlegend=False)
    layout_grafico(fig)
    st.plotly_chart(fig, width="stretch")

    st.dataframe(contagem[["Mês", "Aberturas"]], hide_index=True, width="stretch")


def _secao_estatisticas_tat(df):
    st.markdown("##### Estatísticas de TAT")

    # Filtro de escopo (pedido do Wallace, 2026-08-12: "coloca as OS
    # fechadas lá tb e todas, dar por filtrar OS aberta no SILOMS e OS já
    # fechada e todas, aí as estatística giram em todos de conforme eu
    # selecionar e geral") — antes essa seção só olhava OS em aberto; agora
    # todas as contas abaixo recalculam de acordo com a escolha.
    escopo = st.radio(
        "OS consideradas nas estatísticas abaixo",
        ["Abertas no SILOMS", "Fechadas", "Todas"],
        horizontal=True, key="rep_tat_escopo",
    )
    if escopo == "Abertas no SILOMS":
        escopo_df = df[df["em_aberto"]].copy()
    elif escopo == "Fechadas":
        escopo_df = df[~df["em_aberto"]].copy()
    else:
        escopo_df = df.copy()

    if escopo_df.empty:
        st.info(f"Nenhuma OS em \"{escopo}\".")
        return

    st.caption(
        "\"Com a empresa e terceirizados\" = ainda não entregue pelo fornecedor. Quando \"Onde se "
        "encontra\" é BABE/BAMN/BABV/BAPV/BABR/BANT/PAMA-LS/BACO/BASM/BACG/EEAR, já foi entregue — "
        "só falta encerrar a burocracia da OS (\"V1 PAMA-LS\" não conta como entregue, é outra "
        f"etapa, ainda com a empresa). Vazio = \"{LOCAL_NAO_INFORMADO}\"."
    )

    escopo_df["grupo"] = escopo_df["onde_se_encontra"].isin(LOCAIS_ENTREGUES).map(
        {True: "Entregue (falta burocracia)", False: "Com a empresa e terceirizados"}
    )
    empresa = escopo_df[escopo_df["grupo"] == "Com a empresa e terceirizados"]

    def _media_tat(sub):
        return f"{sub['tat_siloms'].mean():.0f} dias" if sub["tat_siloms"].notna().any() else "—"

    c1, c2 = st.columns(2)
    c1.metric(f"OS — {escopo}", len(escopo_df))
    c2.metric("Média de TAT geral (mesmo faltando a burocracia)", _media_tat(escopo_df))

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

    # TAT real reportado pela própria empresa (coluna "TAT " da fonte, sob
    # "INFORMAÇÕES DA EMPRESA") — disponível a partir de 2026-07-27 (Wallace:
    # "tem o TAT DA EMPRESA AGORA"). Só existe depois que o item já foi
    # entregue (vem "NÃO APLICÁVEL" enquanto em reparo, já tratado como None
    # na extração) — é uma medida retrospectiva (itens já concluídos ou já
    # entregues mesmo sem burocracia fechada), respeita o escopo escolhido
    # acima como todo o resto da seção.
    #
    # Desde 2026-08-12, parte desse número é **calculado por nós** (não
    # reportado pela empresa) — quando falta `tat_empresa` na planilha
    # geral mas a RMA (que cobre mais OS, "desde o início") tem a data de
    # devolução, `_mesclar_complemento_rma` já calculou
    # `data_devolução − data_início` e marcou `tat_calculado=True`.
    com_tat_empresa = escopo_df[escopo_df["tat_empresa"].notna()]
    if not com_tat_empresa.empty:
        calculados = int(com_tat_empresa["tat_calculado"].sum())
        c7, c8 = st.columns(2)
        c7.metric("Itens com TAT real da empresa (já entregues)", len(com_tat_empresa))
        c8.metric("Média de TAT real — empresa", f"{com_tat_empresa['tat_empresa'].mean():.0f} dias")
        if calculados:
            st.caption(
                f"Dos {len(com_tat_empresa)} acima, {calculados} não vieram reportados pela empresa na "
                "planilha geral — foram calculados por nós (data de devolução da RMA − data início) por "
                "faltar o \"TAT\" na planilha geral pra esses. Ver coluna \"Fonte\" na tabela (\"— TAT "
                "calculado\")."
            )

    g1, g2 = st.columns(2)
    with g1:
        st.caption("Com a empresa e terceirizados x Entregue (falta burocracia)")
        contagem_grupo = escopo_df["grupo"].value_counts().reset_index()
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
        escopo_df.dropna(subset=["tat_siloms"])
        .groupby("onde_se_encontra")["tat_siloms"]
        .agg(["mean", "count"])
        .reset_index()
        .rename(columns={"onde_se_encontra": "Onde se encontra", "mean": "TAT médio (dias)", "count": "Quantidade"})
        .sort_values("TAT médio (dias)", ascending=False)
    )
    if media_local.empty:
        # "tat_siloms" (TAT corrente do SILOMS) normalmente só existe pra OS
        # ainda em aberto — em "Fechadas" costuma vir tudo vazio, não é bug.
        st.caption("Sem \"TAT SILOMS\" preenchido nas OS desse escopo — normal em \"Fechadas\".")
    else:
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

    df = _mesclar_complemento_rma(dados["reparaveis"], dados.get("reparaveis_complemento_rma"))
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
        "condicao", "onde_se_encontra", "data_inicio", "tat_siloms", "tat_empresa",
        "data_entrega", "recibo", "sn_trocado_exchange", "termo_recebimento", "fonte",
    ]].copy()
    # Colunas com tipos misturados (data/vazio, número/texto) viram string só
    # para exibição — evita erro de serialização da tabela, sem alterar o xlsx.
    for coluna in ("data_inicio", "data_entrega", "cff", "sn", "sn_trocado_exchange", "termo_recebimento", "recibo"):
        tabela[coluna] = tabela[coluna].astype(str).replace({"None": "", "nan": "", "NaT": ""})
    tabela = tabela.rename(columns={
        "onde_se_encontra": "ONDE SE ENCONTRA", "data_entrega": "Data de devolução empresa",
        "recibo": "RECIBO CASO TENHA",
        "fonte": "Fonte (onde/devolução/recibo)",
    })

    st.dataframe(tabela, width="stretch", hide_index=True, height=420)
    st.caption(
        "\"ONDE SE ENCONTRA\", \"Data de devolução empresa\" e \"RECIBO CASO TENHA\" vêm da planilha geral "
        "(Controle de Reparáveis) por padrão. Quando a coluna \"Fonte\" mostra \"RMA {Mês}/{Ano} (entregue no "
        "mês)\", a aba 1.8 da RMA confirma que a empresa devolveu esse item NESSE mês; \"RMA {Mês}/{Ano} "
        "(histórico)\" é uma OS mais antiga que a aba 1.10 (controle acumulado) já tinha o dado, mas não é do "
        "mês em referência; \"— condenado\" no final indica que a aba 1.9 da RMA marca esse item como "
        "condenado (aí a \"Condição\" também é sobrescrita com o motivo); \"— TAT calculado\" indica que o "
        "\"TAT\" real (na seção \"Estatísticas de TAT\" acima) não veio reportado pela empresa — calculamos "
        "nós (data de devolução da RMA − data início) porque faltava na planilha geral. Em todos os casos, "
        "situação/em aberto continuam vindo só da planilha geral (não mudam por isso) — só os campos citados "
        "são complementados."
    )

    with st.expander("Distribuição por condição"):
        contagem = filtrado["condicao"].value_counts().reset_index()
        contagem.columns = ["condicao", "quantidade"]
        fig = px.bar(contagem, x="quantidade", y="condicao", orientation="h",
                     color_discrete_sequence=[CATEGORICA[0]])
        fig.update_layout(yaxis_title="", xaxis_title="Quantidade", showlegend=False)
        layout_grafico(fig)
        st.plotly_chart(fig, width="stretch")

    st.divider()
    _secao_complemento_rma()

    st.divider()
    _secao_historico_mensal(df)
