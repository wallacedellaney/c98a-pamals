"""Tela de detalhe — Pagamentos."""

import re

import pandas as pd
import plotly.express as px
import streamlit as st

from contrato005.components import data_global
from contrato005.components.paleta import CATEGORICA, layout_grafico
from contrato005.components.utils import formatar_moeda, ordenar_unicos

MODULOS = [1, 2, 3]

MESES = {
    "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "MAIO": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12,
}


def _chave_cronologica(row):
    """'FEV/25' -> (2025, 2). Referências sem mês (ex.: REAJUSTE) usam a data da linha."""
    referencia = str(row["referencia"])
    if "/" in referencia:
        mes_str, ano_str = referencia.split("/")
        mes = MESES.get(mes_str.upper())
        if mes and ano_str.isdigit():
            return (2000 + int(ano_str), mes)
    if pd.notna(row["data"]):
        return (row["data"].year, row["data"].month)
    return (9999, 99)


SITUACOES_QUITADAS = {"Liquidado (NP)", "Pago (OB)", "Pago"}

FILTROS_SITUACAO = [
    ("Pago (SIAFI)", {"Pago (OB)", "Pago (SIAFI)"}),
    ("Liquidado (NP)", {"Liquidado (NP)"}),
    ("Faturado", {"Faturado, aguardando liquidação", "Faturado, aguardando pagamento"}),
    ("Pendente", {"Pendente de faturamento", "Pendente", "Sem lançamento"}),
]


def preparar_tabela_pagamentos(df, modo_externo):
    """Entrega a tabela na estrutura atual, inclusive para bases tratadas antigas.

    A extração passou a gravar OB e data de pagamento em 16/11/2026. Durante
    a transição, o arquivo XLSX publicado ainda pode não conter essas colunas;
    elas ficam vazias até a próxima atualização, sem interromper a página.
    """
    tabela = df.copy()
    for coluna in ("ordem_bancaria", "data_pagamento"):
        if coluna not in tabela.columns:
            tabela[coluna] = pd.NA

    colunas = [
        "modulo", "referencia", "numero_nota_fiscal", "data", "valor_nfs",
        "faturado", "pendente", "situacao", "ordem_pagamento", "observacao",
    ]
    if not modo_externo:
        colunas.extend(["empenho", "ordem_bancaria", "data_pagamento", "empenho_responsavel"])
    return tabela[colunas]


def _alerta_vencimentos(df):
    """NF faturada sem NP/OB com vencimento passado ou em até 7 dias (pedido de 16/11/2026)."""
    if "vencimento" not in df.columns:
        return
    hoje = pd.Timestamp.today().normalize()
    venc = pd.to_datetime(df["vencimento"], errors="coerce")
    abertas = df[~df["situacao"].isin(SITUACOES_QUITADAS) & venc.notna()].copy()
    abertas["vencimento"] = venc[abertas.index]
    abertas = abertas[abertas["vencimento"] <= hoje + pd.Timedelta(days=7)]
    if abertas.empty:
        return
    abertas["dias"] = (abertas["vencimento"] - hoje).dt.days
    linhas = []
    for _, r in abertas.sort_values("vencimento").iterrows():
        nf = "" if pd.isna(r["numero_nota_fiscal"]) else f"NF {int(r['numero_nota_fiscal'])} · "
        quando = f"venceu há {-r['dias']} dia(s)" if r["dias"] < 0 else (
            "vence hoje" if r["dias"] == 0 else f"vence em {r['dias']} dia(s)")
        linhas.append(f"- **{r['referencia']}** · {nf}{formatar_moeda(r['valor_nfs'])} · "
                      f"{r['vencimento']:%d/%m/%Y} ({quando}) · {r['situacao']}")
    st.error("**NF vencida ou vencendo em até 7 dias, sem NP/OB**\n\n" + "\n".join(linhas))


DATA_BASE_REAJUSTE = pd.Timestamp("2025-10-08")


def _numerico(serie):
    """Converte para número; texto como 'R$ 1.234,56' vira 1234.56 e lixo vira NaN.
    Evita o TypeError visto em 16/11/2026 (datas misturadas com valores na aba EMPENHOS)."""
    def conv(v):
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return v
        if isinstance(v, str):
            t = v.replace("R$", "").strip().replace(".", "").replace(",", ".")
            try:
                return float(t)
            except ValueError:
                return None
        return None
    return pd.to_numeric(serie.map(conv), errors="coerce")


def _saldo_inicial_modulo(dados, modulo):
    ind = dados.get("reajuste_indicadores")
    if ind is None or ind.empty:
        return None
    achados = ind[ind["indicador"] == f"Saldo do Módulo {modulo} após 1° Reajuste"]
    if achados.empty:
        return None
    return float(achados.iloc[0]["valor"])


def _saldo_por_modulo(df, dados):
    """Saldo de cada módulo = saldo após o 1º reajuste (08/10/2025, Planilha
    Demonstrativa) − NFs emitidas depois de 08/10/2025 (planilha 005 online)
    − orçamentos pedidos ainda sem NF (coluna Pendente = valor aprovado ou
    estimado). Pedido do Wallace em 16/11/2026."""
    st.markdown("##### Saldo por módulo")
    datas = pd.to_datetime(df["data"], errors="coerce")
    # NFs já abatidas no saldo-base: as da tabela "Antes do 1° Reajuste" da
    # Planilha Demonstrativa (ex.: SET/25, NF 704, emitida em 27/10/2025).
    # Sem essa lista, cai no corte por data de emissão.
    nf_antes = set()
    nfs_dem = dados.get("reajuste_notas_fiscais")
    if nfs_dem is not None and not nfs_dem.empty:
        antes = nfs_dem[nfs_dem["periodo"].astype(str).str.startswith("Antes")]
        nf_antes = set(pd.to_numeric(antes["nota_fiscal"], errors="coerce").dropna().astype(int))
    numero_nf = pd.to_numeric(df["numero_nota_fiscal"], errors="coerce")
    if nf_antes:
        depois_reajuste = numero_nf.notna() & ~numero_nf.isin(nf_antes)
    else:
        depois_reajuste = datas > DATA_BASE_REAJUSTE
    abertos = df[(df["tipo_registro"] == "orcamento") & df["numero_nota_fiscal"].isna()].copy()
    abertos["previsto"] = _numerico(abertos["pendente"])

    linhas, cols = [], st.columns(3)
    for col, m in zip(cols, MODULOS):
        inicial = _saldo_inicial_modulo(dados, m)
        if inicial is None:
            col.info(f"Módulo {m}: sem saldo-base (Planilha Demonstrativa).")
            continue
        faturado = df.loc[(df["modulo"] == m) & depois_reajuste, "valor_nfs"].sum()
        comprometido = abertos.loc[abertos["modulo"] == m, "previsto"].sum()
        atual = inicial - faturado
        livre = atual - comprometido
        col.metric(f"Módulo {m} · saldo hoje", formatar_moeda(atual))
        col.metric("Depois dos orçamentos pedidos", formatar_moeda(livre),
                   delta=f"-{formatar_moeda(comprometido)}" if comprometido else None,
                   delta_color="inverse")
        if livre < 0:
            col.error(f"Os orçamentos pedidos passam o saldo do Módulo {m} em {formatar_moeda(-livre)}.")
        linhas.append(m)
    st.caption(
        "Saldo hoje = saldo após o 1º reajuste (08/10/2025) − NFs que não estão na tabela "
        "\"Antes do 1° Reajuste\" da Planilha Demonstrativa. "
        "Orçamentos pedidos = coluna Pendente da planilha 005 online (valor aprovado ou estimativa)."
    )

    if not abertos.empty:
        tabela = abertos[["modulo", "referencia", "previsto", "observacao"]].copy()
        tabela["previsto"] = tabela["previsto"].apply(lambda v: formatar_moeda(v) if pd.notna(v) else "sem valor ainda")
        st.dataframe(
            tabela.rename(columns={"modulo": "Módulo", "referencia": "Orçamento pedido",
                                   "previsto": "Valor (aprovado/estimado)", "observacao": "Situação"}),
            hide_index=True, width="stretch",
        )
    st.divider()


def _vinculos_por_empenho(df):
    """Monta o detalhe por NE sem somar o saldo de uma mesma NE mais de uma vez."""
    vinculos = {}
    for _, linha in df.iterrows():
        if pd.isna(linha.get("empenho")):
            continue
        for ne in re.split(r"[,\n]", str(linha["empenho"])):
            ne = ne.strip()
            if not re.fullmatch(r"\d{4}NE\d+", ne):
                continue
            nf = linha.get("numero_nota_fiscal")
            nf_texto = f"NF {int(nf)}" if pd.notna(nf) else "sem NF"
            vinculos.setdefault(ne, []).append(
                f"{linha['referencia']} · {nf_texto} · {linha['situacao']}"
            )
    return {ne: " | ".join(itens) for ne, itens in vinculos.items()}


def _controle_por_situacao(df):
    """Mostra valores clicáveis; a escolha filtra a tabela detalhada abaixo."""
    if "pagamentos_filtro_situacao" not in st.session_state:
        st.session_state["pagamentos_filtro_situacao"] = None

    st.markdown("##### Situação financeira")
    st.caption("Clique em uma situação para ver somente os lançamentos correspondentes.")
    colunas = st.columns(len(FILTROS_SITUACAO))
    for coluna, (rotulo, situacoes) in zip(colunas, FILTROS_SITUACAO):
        parte = df[df["situacao"].isin(situacoes)]
        ativo = st.session_state["pagamentos_filtro_situacao"] == rotulo
        with coluna:
            st.metric(rotulo, formatar_moeda(parte["valor_nfs"].sum()), f"{len(parte)} lançamento(s)")
            if st.button(
                "Ocultar detalhe" if ativo else "Ver detalhes",
                key=f"pagamentos_situacao_{rotulo}",
                type="primary" if ativo else "secondary",
                width="stretch",
            ):
                st.session_state["pagamentos_filtro_situacao"] = None if ativo else rotulo
                st.rerun()

    ativo = st.session_state["pagamentos_filtro_situacao"]
    if not ativo:
        return df, None
    situacoes = dict(FILTROS_SITUACAO)[ativo]
    return df[df["situacao"].isin(situacoes)].copy(), ativo


def _mostrar_empenhos(empenhos, df, saldo_informado):
    """Visão interna das NEs: total, usado, saldo e notas vinculadas."""
    with st.expander("Empenhos, saldos e cobertura das NFs", expanded=True):
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("Valor empenhado", formatar_moeda(empenhos["valor_empenhado"].sum()))
        e2.metric("Já liquidado", formatar_moeda(empenhos["valor_utilizado"].sum()))
        saldo_calculado = empenhos["saldo"].sum()
        e3.metric("Saldo calculado pelas NEs", formatar_moeda(saldo_calculado))
        e4.metric("Saldo informado no controle", formatar_moeda(saldo_informado))
        diferenca = saldo_calculado - saldo_informado
        if abs(diferenca) > 0.01:
            st.warning(
                "Divergência entre a soma das NEs e o resumo do Controle de Pagamentos: "
                f"{formatar_moeda(diferenca)}. Conferir a atualização do cabeçalho da planilha."
            )
        st.caption("Cada NE entra uma única vez neste total. O saldo não é repetido por NF vinculada.")

        vinculos = _vinculos_por_empenho(df)
        tabela = empenhos.copy()
        tabela["notas_vinculadas"] = tabela["numero_empenho"].map(vinculos).fillna("Sem lançamento na aba Controle")
        tabela = tabela.sort_values(["saldo", "numero_empenho"], ascending=[False, True])
        st.dataframe(
            tabela.rename(columns={
                "numero_empenho": "NE", "valor_empenhado": "Empenhado",
                "valor_utilizado": "Liquidado", "saldo": "Saldo",
                "responsavel": "Responsável", "justificativa": "Justificativa",
                "notas_vinculadas": "NFs / situação vinculadas",
            }),
            hide_index=True, width="stretch", height=360,
        )

        ne = st.selectbox(
            "Consultar uma NE e as respectivas NFs",
            ["Todas"] + tabela["numero_empenho"].tolist(),
            key="pagamentos_ne_consulta",
        )
        if ne != "Todas":
            linhas = df[df["empenho"].fillna("").map(
                lambda valor: ne in [p.strip() for p in re.split(r"[,\n]", str(valor))]
            )]
            linhas = preparar_tabela_pagamentos(linhas, modo_externo=False)
            st.dataframe(
                linhas[[
                    "referencia", "numero_nota_fiscal", "valor_nfs", "situacao",
                    "ordem_pagamento", "ordem_bancaria", "data_pagamento", "observacao",
                ]].rename(columns={
                    "referencia": "Referência", "numero_nota_fiscal": "NF",
                    "valor_nfs": "Valor", "situacao": "Situação", "ordem_pagamento": "NP",
                    "ordem_bancaria": "OB", "data_pagamento": "Data do pagamento",
                    "observacao": "Observação",
                }),
                hide_index=True, width="stretch",
            )


def render(dados):
    if data_global.mostrar_snapshot_se_necessario(dados, "pagamentos"):
        return

    st.title("Pagamentos")

    df = dados["pagamentos"].copy()
    contrato = dados["contrato"]
    empenhos = dados["empenhos"].copy()
    for c in ("valor_nfs", "faturado", "pendente"):
        df[c] = _numerico(df[c])
    for c in ("valor_empenhado", "saldo"):
        empenhos[c] = _numerico(empenhos[c])
    if "valor_utilizado" in empenhos:
        empenhos["valor_utilizado"] = _numerico(empenhos["valor_utilizado"])
    else:
        empenhos["valor_utilizado"] = empenhos["valor_empenhado"] - empenhos["saldo"]
    empenhos = empenhos[empenhos["numero_empenho"].astype(str).str.match(r"^\d{4}NE\d+$")]

    _alerta_vencimentos(df)
    _saldo_por_modulo(df, dados)

    # --- Resumo rápido por módulo (clicável) ---
    if "modulo_resumo" not in st.session_state:
        st.session_state["modulo_resumo"] = 1

    st.caption("Resumo rápido por módulo")
    mcols = st.columns(3)
    for col, m in zip(mcols, MODULOS):
        with col:
            ativo = st.session_state["modulo_resumo"] == m
            if st.button(f"Módulo {m}", key=f"modulo_{m}", width="stretch",
                         type="primary" if ativo else "secondary"):
                st.session_state["modulo_resumo"] = m
                st.rerun()

    modulo_atual = df[df["modulo"] == st.session_state["modulo_resumo"]]
    r1, r2, r3 = st.columns(3)
    r1.metric(f"Valor das NFs — Módulo {st.session_state['modulo_resumo']}", formatar_moeda(modulo_atual['valor_nfs'].sum()))
    r2.metric("Faturado", formatar_moeda(modulo_atual['faturado'].sum()))
    r3.metric("Pendente", formatar_moeda(modulo_atual['pendente'].sum()))

    st.divider()

    # --- Filtros e visão geral do contrato ---
    filtrado_por_status, status_ativo = _controle_por_situacao(df)
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        modulos = st.multiselect("Módulo", ordenar_unicos(df["modulo"].dropna().astype(int)))
    with col_f2:
        situacoes = st.multiselect("Situação", ordenar_unicos(df["situacao"]))
    with col_f3:
        referencias = st.multiselect("Referência", ordenar_unicos(df["referencia"]))
    with col_f4:
        notas = st.multiselect("Nº Nota Fiscal", ordenar_unicos(df["numero_nota_fiscal"]))

    filtrado = filtrado_por_status.copy()
    if modulos:
        filtrado = filtrado[filtrado["modulo"].isin(modulos)]
    if situacoes:
        filtrado = filtrado[filtrado["situacao"].isin(situacoes)]
    if referencias:
        filtrado = filtrado[filtrado["referencia"].isin(referencias)]
    if notas:
        filtrado = filtrado[filtrado["numero_nota_fiscal"].isin(notas)]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Faturado (filtro)", formatar_moeda(filtrado['faturado'].sum()))
    col2.metric("Pendente (filtro)", formatar_moeda(filtrado['pendente'].sum()))
    col3.metric("Valor total do contrato", formatar_moeda(contrato['valor_total_contrato']))
    col4.metric("Saldo informado no controle", formatar_moeda(contrato['saldo_a_faturar']))
    if status_ativo:
        st.caption(f"Detalhe filtrado: **{status_ativo}**. Use o mesmo botão para voltar a todos os lançamentos.")

    st.divider()

    # --- Situação dos pagamentos (Pago / Faturado, aguardando pagamento /
    # Pendente / Sem lançamento — regra em extrair_pagamentos.situacao_pagamento,
    # ver 00_Instrucoes/pagamentos.md) — pedido do Wallace em 2026-07-18:
    # "tem coisa que so ta faturado, tem coisa que foi pago, tem a ordem de
    # pagamento e observacoes la, vamos apresentar".
    st.markdown("##### Situação dos pagamentos")
    st.caption("Liquidado (NP) = NP emitida, liquidação feita; o dinheiro sai na OB. "
               "Pago (OB) = pagamento confirmado no SIAFI.")
    resumo_situacao = (
        filtrado.groupby("situacao")
        .agg(quantidade=("situacao", "size"), valor=("valor_nfs", "sum"))
        .reset_index()
        .sort_values("valor", ascending=False)
    )
    sc1, sc2 = st.columns([1, 2])
    with sc1:
        tabela_situacao = resumo_situacao.copy()
        tabela_situacao["valor"] = tabela_situacao["valor"].apply(formatar_moeda)
        st.dataframe(
            tabela_situacao.rename(columns={"situacao": "Situação", "quantidade": "Qtd.", "valor": "Valor"}),
            hide_index=True, width="stretch",
        )
    with sc2:
        fig_situacao = px.bar(
            resumo_situacao, x="valor", y="situacao", orientation="h",
            color_discrete_sequence=[CATEGORICA[0]], text="quantidade",
        )
        fig_situacao.update_traces(texttemplate="%{text} lançamento(s)", textposition="outside")
        fig_situacao.update_layout(xaxis_title="Valor (R$)", yaxis_title="", separators=",.")
        layout_grafico(fig_situacao, altura=200)
        st.plotly_chart(fig_situacao, width="stretch")

    # Empenho é detalhe interno de execução orçamentária — escondido no
    # deploy externo "005CELOG2025" (pedido do Wallace: "tira empenho do
    # pagamento tb, ela nao precis saber").
    modo_externo = dados.get("modo_externo", False)
    st.dataframe(
        preparar_tabela_pagamentos(filtrado, modo_externo).rename(columns={
            "ordem_pagamento": "NP", "ordem_bancaria": "OB",
            "data_pagamento": "Data do pagamento", "empenho": "NE(s)",
            "observacao": "Observação",
        }),
        width="stretch",
        hide_index=True,
        height=420,
    )

    if not modo_externo:
        _mostrar_empenhos(empenhos, df, contrato['saldo_a_faturar'])

    with st.expander("Evolução mensal do faturamento", expanded=True):
        evolucao = filtrado[filtrado["tipo_registro"] == "mensal"][["referencia", "data", "valor_nfs"]].copy()
        evolucao["chave"] = evolucao.apply(_chave_cronologica, axis=1)
        evolucao = evolucao.sort_values("chave")

        fig = px.line(evolucao, x="referencia", y="valor_nfs", markers=True,
                      color_discrete_sequence=[CATEGORICA[0]],
                      category_orders={"referencia": evolucao["referencia"].tolist()})
        fig.update_traces(hovertemplate="%{x}<br>R$ %{y:,.2f}<extra></extra>")
        # separators=",." troca o padrão americano (1,234.56) pro brasileiro
        # (1.234,56) em todo o gráfico (eixo e hover) — achado pelo Wallace em
        # 2026-07-18: "40,817... parece que e 40 reais" (lido à brasileira, a
        # vírgula do formato americano parece separador decimal).
        fig.update_layout(xaxis_title="", yaxis_title="Valor faturado (R$)", separators=",.")
        fig.update_xaxes(tickangle=-45)
        fig.update_yaxes(tickprefix="R$ ", tickformat=",.0f")
        layout_grafico(fig, altura=300)
        st.plotly_chart(fig, width="stretch")
