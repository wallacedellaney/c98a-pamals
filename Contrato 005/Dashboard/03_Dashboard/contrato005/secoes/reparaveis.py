"""Tela de detalhe — Reparáveis.

**Reorganizada em 2026-08-24** (pedido do Wallace: "vamos melhorar o
controle de reparaveis, as informacoes deles, o layort, as cores os
filtros"). Antes era uma coluna única gigante (cards + 3 gráficos +
filtros + tabela de ~400 linhas + mais 2 seções embaixo) — virou 3 abas
("📊 Visão Geral", "📋 Tabela / Consulta", "📅 Histórico"), pra quem só quer
consultar uma OS não precisar rolar por tudo. Mudanças principais:

- Cores condicionais (antes tudo era âmbar, até números ruins como "fora
  do prazo"): cards e barras do gráfico "TAT médio por local" agora usam
  STATUS["critical"]/STATUS["good"] conforme o prazo contratual.
- Gráfico "TAT médio por local" ficou clicável (pedido: "quero que tudo
  seja clicavel nessa parte") — clicar numa barra já filtra a aba
  "Tabela / Consulta" por aquele local (via `st.session_state`, ver
  `_secao_tabela`).
- Ranking das 10 OS mais atrasadas (não existia — só tinha a média por
  local, não um raio-x das piores individualmente).
- Coluna "Dias até vencer o prazo" na tabela (110 − TAT, só pra quem ainda
  tá com a empresa/terceirizados).
- Busca por texto livre (nomenclatura/PN/SN/OS) + atalho "só fora do
  prazo" — antes só dava pra filtrar por valor exato via multiselect.
- Botão de exportar (XLSX) a tabela já filtrada — não existia.
- Linha da tabela pintada quando fora do prazo/condenado.
- Corrigido bug mudo (mesmo already achado no Cômputo Mensal, 2026-08-20):
  célula vazia aparecia como o texto literal "None" em vez de branco.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from shared import horario
from contrato005.components import data_global
from contrato005.components.paleta import AMBER, STATUS, layout_grafico, metrica_html, titulo_bloco
from contrato005.components.utils import ordenar_unicos
from contrato005.components.exportar import gerar_xlsx_bytes

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

    # Laranja continua (identidade do sistema) — só um pouco mais de
    # respiro entre as barras/rótulos (pedido do Wallace no brief de
    # refinamento: "manter as barras laranjas... melhorar largura das
    # barras, espaçamento, rótulos, eixo X"). O mês de pico se destaca
    # sozinho por ser o maior valor, sem precisar mudar a cor dele.
    fig = px.bar(contagem, x="Mês", y="Aberturas", color_discrete_sequence=[AMBER])
    fig.update_traces(text=contagem["Aberturas"], textposition="outside", textfont_size=11)
    fig.update_layout(xaxis_title="", yaxis_title="Nº de aberturas", showlegend=False, bargap=0.3)
    layout_grafico(fig, altura=320)
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

    # Legenda visual (selos coloridos), não só texto — pedido do Wallace,
    # 2026-08-24: "queria que deixasse mais claro" (a distinção "com
    # empresa" x "entregue, falta burocracia" só em texto corrido não
    # ficava óbvia). As mesmas 2 cores aparecem nos cards de "Prazo" acima,
    # nos donuts e nas barras abaixo — esse selo é a "legenda mestra" delas.
    st.markdown(
        f'<span style="background:{AMBER}22;color:{AMBER};border:1px solid {AMBER}55;'
        f'border-radius:4px;padding:.15rem .5rem;font-size:.78rem;font-weight:600;">'
        f'🟠 Com a empresa e terceirizados — ainda não voltou</span>'
        f'&nbsp;&nbsp;'
        f'<span style="background:{STATUS["good"]}22;color:{STATUS["good"]};border:1px solid {STATUS["good"]}55;'
        f'border-radius:4px;padding:.15rem .5rem;font-size:.78rem;font-weight:600;">'
        f'🟢 Entregue — já voltou, falta só fechar a OS no SILOMS</span>',
        unsafe_allow_html=True,
    )
    with st.expander("ℹ️ Entenda os critérios dos indicadores"):
        st.markdown(
            "**Com a empresa e terceirizados x Entregue (falta burocracia)** — quando \"Onde se "
            "encontra\" é BABE/BAMN/BABV/BAPV/BABR/BANT/PAMA-LS/BACO/BASM/BACG/EEAR, o item já foi "
            "entregue pelo fornecedor — só falta encerrar a burocracia da OS no SILOMS, não é mais "
            "atraso de reparo de verdade. **\"V1 PAMA-LS\" não conta como entregue** (é outra etapa, "
            f"ainda com a empresa). Vazio = \"{LOCAL_NAO_INFORMADO}\".\n\n"
            f"**Prazo contratual** — {PRAZO_CONTRATUAL_TAT_DIAS} dias, só conta pra quem ainda está "
            "\"com a empresa e terceirizados\" (item já entregue não pesa mais contra o prazo, mesmo "
            "que o TAT dele já passe disso).\n\n"
            "**TAT real da empresa** — coluna reportada pela própria VEE ONE (só existe depois que o "
            "item já foi entregue); quando falta esse dado na planilha geral mas temos a data de "
            "devolução pela RMA em andamento, calculamos nós (devolução − início) — marcado como "
            "\"TAT calculado\" na coluna \"Fonte\" da tabela."
        )

    escopo_df["grupo"] = escopo_df["onde_se_encontra"].isin(LOCAIS_ENTREGUES).map(
        {True: "Entregue (falta burocracia)", False: "Com a empresa e terceirizados"}
    )
    empresa = escopo_df[escopo_df["grupo"] == "Com a empresa e terceirizados"]

    def _media_tat(sub):
        return f"{sub['tat_siloms'].mean():.0f} dias" if sub["tat_siloms"].notna().any() else "—"

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

    com_tat_empresa = escopo_df[escopo_df["tat_empresa"].notna()]
    calculados = int(com_tat_empresa["tat_calculado"].sum()) if not com_tat_empresa.empty else 0

    # 4 blocos visualmente agrupados (Volume/Prazo/TAT/Entregues) — pedido
    # do Wallace, 2026-08-24: "permitir que alguém olhe o dashboard por
    # poucos segundos e entenda: quantas OS existem, quantas com empresa,
    # quantas atrasadas, qual o TAT, quantas já entregues". Antes era uma
    # sequência solta de 8 cards do mesmo peso, um atrás do outro.
    titulo_bloco("Volume")
    c1, c2 = st.columns(2)
    metrica_html(c1, f"OS — {escopo}", len(escopo_df))
    metrica_html(c2, "Com a empresa e terceirizados", len(empresa))

    titulo_bloco("Prazo contratual")
    c3, c4 = st.columns(2)
    # Cores condicionais — pedido do Wallace: antes todo card era âmbar
    # (cor de marca), até números ruins como "fora do prazo". AMBER nunca
    # é usado como status (regra da paleta) — só good/critical.
    metrica_html(
        c3, f"Fora do prazo (> {PRAZO_CONTRATUAL_TAT_DIAS}d) — empresa/terceirizados",
        len(fora_prazo), cor=STATUS["critical"] if len(fora_prazo) else STATUS["good"],
    )
    metrica_html(
        c4, "Vencem o prazo este mês — empresa/terceirizados",
        len(vence_mes), cor=STATUS["critical"] if len(vence_mes) else STATUS["good"],
    )

    titulo_bloco("TAT (Turn Around Time)")
    c5, c6, c7 = st.columns(3)
    metrica_html(c5, "TAT médio geral", _media_tat(escopo_df), tamanho="1.6rem")
    metrica_html(c6, "TAT médio — empresa/terceirizados", _media_tat(empresa), tamanho="1.6rem")
    if not com_tat_empresa.empty:
        metrica_html(c7, "TAT real médio — empresa", f"{com_tat_empresa['tat_empresa'].mean():.0f} dias", tamanho="1.6rem")

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
    if not com_tat_empresa.empty:
        titulo_bloco("Entregues")
        c8, _ = st.columns(2)
        metrica_html(c8, "Itens com TAT real da empresa (já entregues)", len(com_tat_empresa))
        if calculados:
            st.caption(
                f"Dos {len(com_tat_empresa)} acima, {calculados} não vieram reportados pela empresa na "
                "planilha geral — foram calculados por nós (data de devolução da RMA − data início) por "
                "faltar o \"TAT\" na planilha geral pra esses. Ver coluna \"Fonte\" na tabela (\"— TAT "
                "calculado\")."
            )

    # Gráficos e detalhamento dentro de um expander — pedido do Wallace,
    # 2026-08-24: "queria que deixasse mais claro, parece que tem muita
    # informacao na tela principal tb ne". Os 4 blocos de números acima
    # (Volume/Prazo/TAT/Entregues) já respondem o essencial "em poucos
    # segundos" (pedido original do brief de refinamento); donuts, ranking
    # e o gráfico por local ficam aqui dentro, sob demanda.
    with st.expander("📊 Ver gráficos e detalhamento (situação física, ranking, TAT por local)"):
        titulo_bloco("Situação física x Prazo contratual")
        g1, g2 = st.columns(2)
        # Mesma dimensão/alinhamento pros 2 donuts (pedido do Wallace: "os dois
        # gráficos devem possuir mesma dimensão e alinhamento") + legenda
        # embaixo, centralizada e perto do gráfico (não afastada, à direita,
        # como o padrão do Plotly deixava antes).
        _ALTURA_DONUT = 260
        _LEGENDA_DONUT = dict(orientation="h", yanchor="top", y=-0.08, xanchor="center", x=0.5)
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
            fig_grupo.update_layout(legend=_LEGENDA_DONUT)
            layout_grafico(fig_grupo, altura=_ALTURA_DONUT)
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
            fig_prazo.update_layout(legend=_LEGENDA_DONUT)
            layout_grafico(fig_prazo, altura=_ALTURA_DONUT)
            st.plotly_chart(fig_prazo, width="stretch")

        # Ranking das piores OS — pedido do Wallace, 2026-08-24 ("pensa aí oq
        # podemos fazer"): a média por local (gráfico abaixo) não mostra um
        # raio-x das OS individuais mais atrasadas. Só sobre "com a
        # empresa/terceirizados" (mesmo grupo do prazo contratual). TAT (dias)
        # é o campo mais importante visualmente (pedido do Wallace no brief de
        # refinamento) — vem primeiro, Unidade por último (menor peso).
        titulo_bloco("Top 10 OS mais atrasadas")
        st.caption("Com a empresa/terceirizados, ordenado por dias em aberto (TAT SILOMS)")
        piores = (
            empresa.dropna(subset=["tat_siloms"])
            .sort_values("tat_siloms", ascending=False)
            .head(10)[["tat_siloms", "os", "pn", "nomenclatura", "onde_se_encontra", "unidade_solicitante"]]
            .rename(columns={
                "tat_siloms": "TAT (dias)", "os": "OS", "pn": "PN", "nomenclatura": "Nomenclatura",
                "onde_se_encontra": "Onde se encontra", "unidade_solicitante": "Unidade",
            })
        )
        if piores.empty:
            st.caption("Sem OS com TAT SILOMS preenchido nesse escopo.")
        else:
            piores["TAT (dias)"] = piores["TAT (dias)"].round(0).astype(int)
            # Cor com significado, não decoração (pedido do Wallace): número em
            # vermelho pra qualquer um fora do prazo (esperado, já que é a lista
            # das piores); fundo vermelho BEM suave só pro extremo (> 2x o
            # prazo contratual) — não pinta a linha inteira de vermelho forte
            # só porque está nessa tabela.
            limite_extremo = PRAZO_CONTRATUAL_TAT_DIAS * 2
            styler_piores = (
                piores.style
                .map(lambda v: f"color: {STATUS['critical']}; font-weight: 700;", subset=["TAT (dias)"])
                .apply(
                    lambda row: [f"background-color: {STATUS['critical']}14"] * len(row)
                    if row["TAT (dias)"] > limite_extremo else [""] * len(row),
                    axis=1,
                )
            )
            st.dataframe(styler_piores, hide_index=True, width="stretch")

        titulo_bloco("TAT médio por local")
        st.caption("'Onde se encontra' — clique numa barra pra filtrar a aba \"Tabela / Consulta\" por ela")
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
            # Cor condicional por barra — pedido do Wallace: "tem um negocio de
            # cor la de onde ta, ta um laranjao" (antes toda barra era âmbar
            # vívido, mesmo passando MUITO dos 110 dias — parecia que TODO
            # local estava crítico). Refinado no brief de design: só quem
            # passa do prazo fica vermelho (problema real); quem está dentro
            # fica num âmbar discreto/translúcido (identidade, não alarme).
            cores_barras = [
                STATUS["critical"] if v > PRAZO_CONTRATUAL_TAT_DIAS else f"{AMBER}66"
                for v in media_local["TAT médio (dias)"]
            ]
            fig_local = go.Figure(go.Bar(
                x=media_local["TAT médio (dias)"], y=media_local["Onde se encontra"],
                orientation="h", marker_color=cores_barras,
                customdata=media_local["Quantidade"],
                hovertemplate="%{y}<br>TAT médio: %{x} dias<br>Quantidade: %{customdata}<extra></extra>",
            ))
            # Linha do prazo contratual em laranja/âmbar (pedido do Wallace no
            # brief: "usar laranja/amarelo para essa referência") — antes
            # estava vermelha, o que confundia com "problema" (a linha em si
            # não é um problema, é só a referência de onde o prazo vence).
            fig_local.add_vline(x=PRAZO_CONTRATUAL_TAT_DIAS, line_dash="dash", line_color=AMBER,
                                 annotation_text=f"Prazo contratual — {PRAZO_CONTRATUAL_TAT_DIAS}d",
                                 annotation_font_color=AMBER)
            fig_local.update_layout(yaxis_title="", xaxis_title="TAT médio (dias)")
            layout_grafico(fig_local, altura=max(200, 28 * len(media_local)))
            evento_bar = st.plotly_chart(
                fig_local, width="stretch", on_select="rerun", selection_mode="points", key="rep_bar_local_clique",
            )
            pontos = evento_bar.selection.get("points", []) if evento_bar else []
            locais_clicados = sorted({p["y"] for p in pontos if "y" in p})
            if locais_clicados:
                st.session_state["rep_filtro_local_pendente"] = locais_clicados
                st.success(
                    f"🖱️ Clicado: **{', '.join(locais_clicados)}** — já filtrado na aba \"📋 Tabela / Consulta\"."
                )

            with st.expander("Ver tabela — TAT médio por local"):
                st.dataframe(media_local, hide_index=True, width="stretch")

    st.divider()


def _tabela_para_texto(tabela):
    """Converte TODAS as colunas pra string de exibição, com célula vazia
    virando "" — não só uma lista fixa de colunas como antes. Bug mudo
    achado em 2026-08-24 (mesmo já corrigido no Cômputo Mensal,
    2026-08-20): célula vazia (None/NaN/NaT) aparecia como o texto literal
    "None" na tabela em vez de branco — o Streamlit ignora o na_rep do
    pandas nessa versão quando a coluna ainda tem valor nulo de verdade."""
    tabela = tabela.copy()
    for coluna in tabela.columns:
        tabela[coluna] = tabela[coluna].astype(str).replace({"None": "", "nan": "", "NaT": "", "<NA>": ""})
    return tabela


def _secao_tabela(df):
    # Consome o clique feito no gráfico "TAT médio por local" (aba "Visão
    # Geral") — precisa ser ANTES do multiselect "Onde se encontra" ser
    # instanciado, pra virar o valor inicial dele nesse mesmo rerun.
    if "rep_filtro_local_pendente" in st.session_state:
        st.session_state["rep_filtro_locais"] = st.session_state.pop("rep_filtro_local_pendente")

    busca = st.text_input(
        "🔍 Buscar (nomenclatura, PN, SN ou OS)", key="rep_busca_texto",
        placeholder="Ex.: fuel control, C662041-0102, 3040265533...",
    )

    col_f0, col_f1, col_f2, col_f3, col_f4 = st.columns(5)
    with col_f0:
        pns = st.multiselect("PN", ordenar_unicos(df["pn"]), key="rep_filtro_pns")
    with col_f1:
        situacoes = st.multiselect(
            "Situação (ST_OS)", ordenar_unicos(df["situacao"]), key="rep_filtro_situacoes",
            help="Por padrão mostra só as OS em aberto. Selecione 'OS concluída' aqui para vê-las também.",
        )
    with col_f2:
        condicoes = st.multiselect("Condição", ordenar_unicos(df["condicao"]), key="rep_filtro_condicoes")
    with col_f3:
        locais = st.multiselect("Onde se encontra", ordenar_unicos(df["onde_se_encontra"]), key="rep_filtro_locais")
    with col_f4:
        unidades = st.multiselect("Unidade solicitante", ordenar_unicos(df["unidade_solicitante"]), key="rep_filtro_unidades")

    so_fora_prazo = st.checkbox(
        f"⚠️ Mostrar só \"fora do prazo contratual\" (> {PRAZO_CONTRATUAL_TAT_DIAS} dias, com a empresa/terceirizados)",
        key="rep_so_fora_prazo",
    )

    # Situação escolhida manualmente manda mais que o padrão "só em aberto" —
    # assim dá pra escolher "OS concluída" e ver as que já foram fechadas.
    filtrado = df.copy() if situacoes else df[df["em_aberto"]].copy()
    if busca:
        termo = busca.strip().lower()
        alvo = (
            filtrado["nomenclatura"].astype(str).str.lower()
            + " " + filtrado["pn"].astype(str).str.lower()
            + " " + filtrado["sn"].astype(str).str.lower()
            + " " + filtrado["os"].astype(str).str.lower()
        )
        filtrado = filtrado[alvo.str.contains(termo, na=False)]
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
    if so_fora_prazo:
        entregue = filtrado["onde_se_encontra"].isin(LOCAIS_ENTREGUES)
        filtrado = filtrado[(~entregue) & (filtrado["tat_siloms"] > PRAZO_CONTRATUAL_TAT_DIAS)]

    filtrado = filtrado.reset_index(drop=True)

    c_qtd, c_export = st.columns([3, 1])
    metrica_html(c_qtd, "OS (após filtro)", len(filtrado))
    with c_export:
        st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
        if not filtrado.empty:
            st.download_button(
                "⬇️ Exportar (XLSX)",
                gerar_xlsx_bytes(filtrado.drop(columns=["tat_calculado"], errors="ignore"), "Reparaveis"),
                file_name="reparaveis_filtrado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )

    # "Dias até vencer o prazo" — pedido do Wallace, 2026-08-24: coluna
    # nova, não existia (só tinha o TAT bruto). Só faz sentido pra quem
    # ainda está com a empresa/terceirizados (mesma regra do prazo
    # contratual); pra quem já foi entregue, fica em branco.
    entregue_mask = filtrado["onde_se_encontra"].isin(LOCAIS_ENTREGUES)
    filtrado["dias_ate_vencer"] = pd.NA
    elegivel = ~entregue_mask & filtrado["tat_siloms"].notna()
    filtrado.loc[elegivel, "dias_ate_vencer"] = PRAZO_CONTRATUAL_TAT_DIAS - filtrado.loc[elegivel, "tat_siloms"]

    tabela = filtrado[[
        "os", "pn", "cff", "nomenclatura", "sn", "unidade_solicitante", "situacao",
        "condicao", "onde_se_encontra", "data_inicio", "tat_siloms", "dias_ate_vencer", "tat_empresa",
        "data_entrega", "recibo", "sn_trocado_exchange", "termo_recebimento", "fonte",
    ]].copy()
    for coluna in ("data_inicio", "data_entrega"):
        tabela[coluna] = pd.to_datetime(tabela[coluna], errors="coerce").dt.strftime("%d/%m/%Y")

    # Guarda os valores numéricos ANTES de virar texto — usado só pra
    # decidir a cor da linha (`_cor_linha`), a mesma técnica do Cômputo
    # Mensal (2026-08-20): não dá pra colorir em cima da versão já em texto.
    tat_numerico = filtrado["tat_siloms"].reset_index(drop=True)
    condicao_numerica = filtrado["condicao"].reset_index(drop=True)

    tabela = tabela.rename(columns={
        "os": "OS", "pn": "PN", "cff": "CFF", "nomenclatura": "Nomenclatura", "sn": "SN",
        "unidade_solicitante": "Unidade solicitante", "situacao": "Situação", "condicao": "Condição",
        "onde_se_encontra": "Onde se encontra", "data_inicio": "Data início", "tat_siloms": "TAT SILOMS (dias)",
        "dias_ate_vencer": "Dias até vencer o prazo", "tat_empresa": "TAT empresa (dias)",
        "data_entrega": "Data de devolução empresa", "recibo": "Recibo",
        "sn_trocado_exchange": "SN trocado (exchange)", "termo_recebimento": "Termo de recebimento",
        "fonte": "Fonte (onde/devolução/recibo)",
    })
    tabela_texto = _tabela_para_texto(tabela)

    # Cor com significado, não decoração (pedido do Wallace no brief de
    # refinamento) — "fora do prazo" pinta a linha inteira num vermelho MUITO
    # suave (só sinaliza, não grita); "condenado" é um destaque DIFERENTE
    # (só a célula "Condição", texto vermelho forte) — antes os 2 casos
    # usavam o mesmo tom, misturando 2 significados diferentes numa cor só.
    idx_condicao = list(tabela_texto.columns).index("Condição")

    def _cor_linha(row):
        i = row.name
        tat = tat_numerico.iloc[i]
        condenado = isinstance(condicao_numerica.iloc[i], str) and "CONDENADO" in condicao_numerica.iloc[i].upper()
        estilos = [""] * len(row)
        if pd.notna(tat) and tat > PRAZO_CONTRATUAL_TAT_DIAS:
            estilos = [f"background-color: {STATUS['critical']}10"] * len(row)
        if condenado:
            estilos[idx_condicao] = f"color: {STATUS['critical']}; font-weight: 700;"
        return estilos

    styler = tabela_texto.style.apply(_cor_linha, axis=1)
    # OS/PN/Nomenclatura fixas na rolagem horizontal (pedido do Wallace:
    # "congelar, se possível: OS; PN; nomenclatura") — Streamlit 1.58
    # suporta `pinned` no column_config; seguro aqui porque `tabela_texto`
    # já não tem NaN nenhum sobrando (ver `_tabela_para_texto`) — declarar
    # column_config com NaN de verdade foi o que causou o bug do "None"
    # (ver Cômputo Mensal, 2026-08-20).
    colunas_fixas = {
        c: st.column_config.Column(pinned=True) for c in ("OS", "PN", "Nomenclatura") if c in tabela_texto.columns
    }
    st.dataframe(styler, width="stretch", hide_index=True, height=420, column_config=colunas_fixas)

    # Legenda condensada num expander (pedido do Wallace: "o texto atual
    # possui muitas informações importantes, porém ocupa bastante espaço...
    # transformar em 'ℹ️ Como interpretar esta tabela' dentro de um
    # expander, organizado em tópicos") — nada foi removido, só reorganizado.
    st.caption("🔴 Linha = fora do prazo contratual · Condição em vermelho = condenado")
    with st.expander("ℹ️ Como interpretar esta tabela"):
        st.markdown(
            "- **Linha com fundo vermelho suave** — TAT SILOMS > 110 dias (fora do prazo contratual), "
            "só pra quem ainda está com a empresa/terceirizados.\n"
            "- **\"Condição\" em vermelho** — a aba 1.9 da RMA marca esse item como condenado (o motivo "
            "vem junto no texto da célula).\n"
            "- **\"Onde se encontra\" / \"Data de devolução empresa\" / \"Recibo\"** — vêm da planilha "
            "geral (Controle de Reparáveis) por padrão.\n"
            "- **Coluna \"Fonte\"** — quando mostra \"RMA {Mês}/{Ano} (entregue no mês)\", a aba 1.8 da "
            "RMA confirma que a empresa devolveu esse item NESSE mês; \"RMA {Mês}/{Ano} (histórico)\" é "
            "uma OS mais antiga que a aba 1.10 (controle acumulado) já tinha o dado, mas não é do mês em "
            "referência.\n"
            "- **\"— TAT calculado\"** (no final da \"Fonte\") — o TAT real (aba \"Visão Geral\") não veio "
            "reportado pela empresa; calculamos nós (data de devolução da RMA − data início) porque "
            "faltava na planilha geral.\n\n"
            "Em todos os casos, situação/em aberto continuam vindo só da planilha geral (não mudam por "
            "isso) — só os campos citados acima são complementados pela RMA."
        )

    with st.expander("📊 Distribuição por condição"):
        contagem = filtrado["condicao"].value_counts().reset_index()
        contagem.columns = ["condicao", "quantidade"]
        contagem = contagem.sort_values("quantidade", ascending=True)
        fig = px.bar(contagem, x="quantidade", y="condicao", orientation="h",
                     color_discrete_sequence=[AMBER])
        fig.update_traces(text=contagem["quantidade"], textposition="outside")
        fig.update_layout(yaxis_title="", xaxis_title="Quantidade", showlegend=False)
        layout_grafico(fig, altura=max(200, 26 * len(contagem)))
        st.plotly_chart(fig, width="stretch")

    st.divider()
    _secao_complemento_rma()


def render(dados):
    if data_global.mostrar_snapshot_se_necessario(dados, "reparaveis"):
        return

    st.title("Reparáveis")

    df = _mesclar_complemento_rma(dados["reparaveis"], dados.get("reparaveis_complemento_rma"))
    df["onde_se_encontra"] = df["onde_se_encontra"].fillna(LOCAL_NAO_INFORMADO)

    aba_geral, aba_tabela, aba_historico = st.tabs(["📊 Visão Geral", "📋 Tabela / Consulta", "📅 Histórico"])

    with aba_geral:
        _secao_estatisticas_tat(df)

    with aba_tabela:
        _secao_tabela(df)

    with aba_historico:
        _secao_historico_mensal(df)
