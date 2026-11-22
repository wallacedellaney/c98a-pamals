"""Painéis SILOMS para consulta e triagem do projeto U8."""

import math

import pandas as pd
import plotly.express as px
import streamlit as st

from projetos.components.paleta import COR_TIPO_SALDO, PRIMARY, layout_grafico
from projetos.data.tpjl_v2 import FONTES, PASTA_LOCAL, ler_relatorio, sincronizar_fonte
from shared import drive_sync

TAMANHO_PAGINA = 100
CHAVE_PECA = ["PN", "CFF"]
CAMPOS_BUSCA = ("PN", "CFF", "Nomenclatura", "Requisição", "Pedido", "OS", "Plano")
FILTROS = {
    "consumo": ("Competência", "Unidade"),
    "estoque": ("Unidade", "Setor", "Tipo de saldo"),
    "requisicoes": ("Unidade de criação", "Unidade de destino", "Status da requisição", "Status do plano"),
    "pedidos": ("Tipo", "Status"),
    "os": ("Unidade executante", "Setor executante", "Tipo", "Prioridade", "Status"),
}
DATAS = {"requisicoes": "Emitida em", "pedidos": "Criado em", "os": "Criada em"}
PREVISOES = {"requisicoes": "Previsão de entrega", "os": "Fim previsto"}


@st.cache_data(show_spinner=False)
def _carregar(chave, caminho, atualizado_ns):
    return ler_relatorio(caminho.read_bytes(), chave)


def _fonte(chave, caminho=None):
    caminho = caminho or PASTA_LOCAL / f"{chave}.xlsx"
    try:
        return _carregar(chave, caminho, caminho.stat().st_mtime_ns)
    except (OSError, ValueError):
        return None


def _buscar(df, termo):
    colunas = [c for c in CAMPOS_BUSCA if c in df]
    mask = df[colunas].apply(lambda c: c.astype("string").str.contains(
        termo, case=False, regex=False, na=False,
    )).any(axis=1)
    return df.loc[mask]


def _triagem_consumo(consumo, estoque):
    pecas = consumo[CHAVE_PECA].drop_duplicates()
    saldo = estoque.loc[estoque["Tipo de saldo"].eq("Utilizável")]
    saldo = saldo.groupby(CHAVE_PECA)["Quantidade"].sum().rename("Saldo utilizável observado")
    presenca = estoque[CHAVE_PECA].drop_duplicates().assign(_consta=True)
    pecas = pecas.merge(presenca, how="left", on=CHAVE_PECA).join(saldo, on=CHAVE_PECA)
    sem_saldo = pecas.loc[~pecas["Saldo utilizável observado"].gt(0)].copy()
    sem_saldo["Situação no extrato"] = sem_saldo["_consta"].eq(True).map({
        True: "Consta sem saldo utilizável positivo",
        False: "Sem registro no extrato",
    })
    return sem_saldo.drop(columns="_consta")


def _barras(dados, grupo, valor, titulo, *, horizontal=False, selecionar=None):
    st.markdown(f"**{titulo}**")
    if dados.empty:
        st.caption("Sem registros para este gráfico.")
        return []
    args = {"x": valor, "y": grupo, "orientation": "h"} if horizontal else {"x": grupo, "y": valor}
    fig = px.bar(dados, **args, text=valor, color_discrete_sequence=[PRIMARY])
    eixo_grupo, eixo_valor = ("%{y}", "%{x}") if horizontal else ("%{x}", "%{y}")
    fig.update_traces(textposition="auto", hovertemplate=f"{eixo_grupo}<br>{valor}: {eixo_valor}<extra></extra>")
    if horizontal:
        fig.update_yaxes(type="category", categoryorder="array", categoryarray=dados[grupo].tolist()[::-1])
    else:
        # Mantém a competência original no evento de seleção mesmo quando parece uma data.
        fig.update_xaxes(type="category")
    altura = min(660, max(245, 90 + 32 * len(dados))) if horizontal else 285
    fig.update_layout(xaxis_title=valor if horizontal else "", yaxis_title="" if horizontal else valor)
    layout_grafico(fig, altura=altura)
    if selecionar:
        evento = st.plotly_chart(fig, width="stretch", key=selecionar,
                                 on_select="rerun", selection_mode="points")
        eixo = "y" if horizontal else "x"
        return [p[eixo] for p in evento.selection.points if eixo in p]
    st.plotly_chart(fig, width="stretch", key=f"v2_barras_{grupo}_{titulo}")
    return []


def _por_mes(df, coluna, nome="Registros"):
    datas = pd.to_datetime(df[coluna], errors="coerce").dropna()
    return datas.dt.strftime("%Y-%m").value_counts().sort_index().rename_axis("Mês").reset_index(name=nome)


def _visuais(chave, df):
    if chave == "consumo":
        meses = df.groupby("Competência", as_index=False)["Consumo"].sum()
        selecionados = _barras(meses, "Competência", "Consumo", "Quantidade consumida por competência",
                                selecionar="v2_grafico_consumo")
        if selecionados:
            df = df.loc[df["Competência"].isin(selecionados)]
            st.caption("Competência selecionada no gráfico: " + ", ".join(map(str, selecionados)))
        criterio = st.radio("Ranking por", ("Competências com consumo", "Quantidade consumida"),
                            horizontal=True, key="v2_ranking_consumo")
        consumo = df.loc[df["Consumo"].gt(0)]
        ranking = consumo.groupby(CHAVE_PECA).agg(
            **{"Competências com consumo": ("Competência", "nunique"), "Quantidade consumida": ("Consumo", "sum")},
        ).reset_index().nlargest(10, criterio)
        ranking["Peça"] = ranking["PN"] + " · " + ranking["CFF"]
        _barras(ranking, "Peça", criterio, "Dez primeiras peças", horizontal=True)
    elif chave == "estoque":
        pecas = df.drop_duplicates([*CHAVE_PECA, "Unidade", "Tipo de saldo"])
        contagem = pecas.groupby(["Unidade", "Tipo de saldo"]).size().reset_index(name="Pares PN/CFF")
        st.markdown("**Peças distintas por unidade e tipo de saldo**")
        fig = px.bar(contagem, x="Unidade", y="Pares PN/CFF", color="Tipo de saldo", barmode="group",
                     text="Pares PN/CFF", color_discrete_map=COR_TIPO_SALDO)
        fig.update_layout(xaxis_title="", legend_title_text="")
        st.plotly_chart(layout_grafico(fig, altura=310), width="stretch")
    else:
        status = "Status da requisição" if chave == "requisicoes" else "Status"
        grupos = [status, "Status do plano"] if chave == "requisicoes" else [status, "Tipo"]
        colunas = st.columns(2)
        for grupo, coluna in zip(grupos, colunas):
            with coluna:
                frequencia = df[grupo].astype("string").fillna("Sem informação").value_counts()
                _barras(frequencia.rename_axis(grupo).reset_index(name="Registros"), grupo, "Registros",
                        f"Registros por {grupo.lower()}", horizontal=True)
        if chave == "os":
            oficinas = df["Setor executante"].value_counts().head(10).rename_axis("Oficina")
            _barras(oficinas.reset_index(name="OS"), "Oficina", "OS", "Dez oficinas com mais OS", horizontal=True)
        elif chave == "pedidos":
            criacao = pd.to_datetime(df["Criado em"], errors="coerce")
            conclusao = pd.to_datetime(df["Conclusão"], errors="coerce")
            duracao = (conclusao - criacao).dt.total_seconds().div(86400).dropna()
            duracao = duracao[duracao.ge(0)]
            if not duracao.empty:
                st.metric("Mediana entre criação e conclusão", f"{duracao.median():.1f} dias",
                          help="Calculada sobre os pedidos filtrados com as duas datas válidas.")
        _barras(_por_mes(df, DATAS[chave]), "Mês", "Registros", "Registros por mês")
    return df


def _filtros(chave, df, obtido_em):
    if chave in DATAS:
        coluna = DATAS[chave]
        datas = pd.to_datetime(df[coluna], errors="coerce").dt.date
        if datas.notna().any():
            validas = datas.dropna()
            limites = (validas.min(), validas.max())
            periodo = st.date_input(coluna, limites, min_value=limites[0], max_value=limites[1],
                                    format="DD/MM/YYYY", key=f"v2_periodo_{chave}")
            if len(periodo) == 2 and periodo != limites:
                df = df.loc[datas.between(*periodo)]
    opcoes_filtro = {c: sorted(df[c].dropna().astype(str).unique()) for c in FILTROS[chave]}
    for i in range(0, len(opcoes_filtro), 3):
        campos = list(opcoes_filtro)[i:i + 3]
        for nome, col in zip(campos, st.columns(len(campos))):
            selecionados = col.multiselect(nome, opcoes_filtro[nome], key=f"v2_{chave}_{nome}")
            if selecionados:
                df = df.loc[df[nome].astype(str).isin(selecionados)]
    if chave in PREVISOES:
        previsao = pd.to_datetime(df[PREVISOES[chave]], errors="coerce").dt.normalize()
        referencia = pd.to_datetime(obtido_em, dayfirst=True, errors="coerce")
        if pd.notna(referencia):
            referencia = referencia.normalize()
            limite = referencia + pd.DateOffset(years=1)
            tipos = {
                "Sem previsão": previsao.isna(),
                "Data anterior à extração": previsao.lt(referencia),
                "Até 30 dias após a extração": previsao.between(referencia, referencia + pd.Timedelta(days=30)),
                "Mais de um ano após a extração": previsao.gt(limite),
            }
            opcao = st.selectbox("Faixa da data prevista", ("Todas", *tipos), key=f"v2_previsao_{chave}")
            if opcao in tipos:
                df = df.loc[tipos[opcao]]
    if chave == "pedidos":
        saldo = df["Qtd. pedida"] - df["Qtd. atendida"]
        restante = st.radio("Quantidade atendida", ("Todos", "Parcial", "Diferença positiva"),
                            horizontal=True, key="v2_saldo_pedidos")
        if restante == "Parcial":
            df = df.loc[saldo.gt(0) & df["Qtd. atendida"].gt(0)]
        elif restante == "Diferença positiva":
            df = df.loc[saldo.gt(0)]
        referencia = pd.to_datetime(obtido_em, dayfirst=True, errors="coerce")
        if pd.notna(referencia):
            idade = (referencia.normalize() - pd.to_datetime(df["Criado em"]).dt.normalize()).dt.days
            faixa = st.selectbox("Idade desde a criação na extração", ("Todas", "Até 30 dias", "31 a 90 dias", "Mais de 90 dias"),
                                 key="v2_idade_pedidos")
            limites = {"Até 30 dias": (0, 30), "31 a 90 dias": (31, 90), "Mais de 90 dias": (91, math.inf)}
            if faixa in limites:
                df = df.loc[idade.between(*limites[faixa])]
    return df


def _tabela(df, chave):
    if df.empty:
        st.info("Nenhum registro para os filtros selecionados.")
        return
    paginas = math.ceil(len(df) / TAMANHO_PAGINA)
    pagina = st.number_input("Página", 1, paginas, 1, key=f"v2_pg_{chave}_{paginas}") if paginas > 1 else 1
    inicio = (pagina - 1) * TAMANHO_PAGINA
    lote = df.iloc[inicio:inicio + TAMANHO_PAGINA]
    fim = inicio + len(lote)
    st.caption(f"Registros {inicio + 1:,} a {fim:,} de {len(df):,}".replace(",", "."))
    evento = st.dataframe(lote, hide_index=True, width="stretch", on_select="rerun",
                          selection_mode="single-row", key=f"v2_tabela_{chave}_{pagina}")
    if evento.selection.rows and evento.selection.rows[0] < len(lote):
        registro = lote.iloc[evento.selection.rows[0]]
        st.subheader("Detalhe do registro")
        detalhe = registro.astype("string").fillna("—").rename("Valor").rename_axis("Campo").reset_index()
        st.dataframe(detalhe, hide_index=True, width="stretch")
    st.download_button("Baixar resultado em CSV", df.to_csv(index=False, sep=";").encode("utf-8-sig"),
                       file_name=f"tpjl-{chave}-u8.csv", mime="text/csv", key=f"v2_csv_{chave}")


def _ficha(fontes):
    termo = st.text_input("Buscar peça por PN, CFF, nomenclatura ou número de registro", key="v2_ficha_busca").strip()
    if not termo:
        return
    encontrados = [_buscar(rel[0], termo) for rel in fontes.values()]
    pecas = pd.concat(encontrados, ignore_index=True)[CHAVE_PECA + ["Nomenclatura"]]
    pecas = pecas.dropna(subset=CHAVE_PECA).drop_duplicates(CHAVE_PECA)
    if pecas.empty:
        st.info("Nenhuma peça encontrada.")
        return
    exato = pecas["PN"].str.upper().eq(termo.upper())
    pecas = pecas.assign(_exato=exato).sort_values(["_exato", "PN", "CFF"], ascending=[False, True, True])
    rotulos = {(pn, cff): f"{pn} · {cff} · {nome}" for pn, cff, nome, _ in pecas.itertuples(index=False, name=None)}
    pn, cff = st.selectbox("Peça", list(rotulos), format_func=rotulos.__getitem__, key="v2_ficha_peca")
    st.caption("Registros relacionados pelo PN e pelo CFF.")
    secoes = st.tabs([FONTES[k][0] for k in fontes])
    for (k, (df, _, data)), secao in zip(fontes.items(), secoes):
        with secao:
            item = df.loc[df["PN"].eq(pn) & df["CFF"].eq(cff)]
            st.caption(f"Extração de {data}")
            if k == "consumo" and not item.empty:
                serie = item.groupby("Competência", as_index=False)["Consumo"].sum()
                _barras(serie, "Competência", "Consumo", "Consumo da peça")
            if k == "estoque" and not item.empty:
                totais = item.groupby("Tipo de saldo")["Quantidade"].sum()
                for col, tipo in zip(st.columns(2), ("Utilizável", "Reparável")):
                    col.metric(tipo, f"{totais.get(tipo, 0):g}")
            _tabela(item, f"ficha_{k}")

    _historico_peca(pn, cff)


def _historico_peca(pn, cff):
    with st.expander("Posições mensais da peça"):
        historico = []
        for chave in ("estoque", "requisicoes", "pedidos", "os"):
            arquivos = sorted((PASTA_LOCAL / "historico" / chave).glob("*.xlsx"))
            if not arquivos:
                continue
            for arquivo in arquivos:
                fonte = _fonte(chave, arquivo)
                if fonte is None:
                    continue
                df, _, data = fonte
                item = df.loc[df["PN"].eq(pn) & df["CFF"].eq(cff)]
                mes = arquivo.stem
                if chave == "estoque":
                    saldo = item.groupby("Tipo de saldo")["Quantidade"].sum()
                    for tipo in ("Utilizável", "Reparável"):
                        historico.append((mes, data, FONTES[chave][0], tipo, saldo.get(tipo), "Quantidade"))
                else:
                    coluna = "Status da requisição" if chave == "requisicoes" else "Status"
                    contagem = item[coluna].astype("string").fillna("Sem informação").value_counts()
                    for status, n in contagem.items():
                        historico.append((mes, data, FONTES[chave][0], status, n, "Registros"))
        if not historico:
            st.info("As posições mensais aparecerão após atualizar os relatórios.")
            return
        tabela = pd.DataFrame(historico, columns=["Mês", "Extração", "Fonte", "Saldo ou status", "Valor", "Medida"])
        estoque = tabela[(tabela["Medida"] == "Quantidade") & tabela["Valor"].notna()]
        if estoque["Mês"].nunique() > 1:
            fig = px.line(estoque, x="Mês", y="Valor", color="Saldo ou status", markers=True,
                          title="Posições de estoque registradas", color_discrete_map=COR_TIPO_SALDO)
            st.plotly_chart(layout_grafico(fig, altura=310), width="stretch")
        st.dataframe(tabela, hide_index=True, width="stretch")


def render_prioridades():
    st.subheader("Prioridades U8")
    fontes = {k: rel for k in FONTES if (rel := _fonte(k)) is not None}
    if not fontes:
        st.info("Carregue os relatórios pelo botão de atualização em cada tópico.")
        return
    _ficha(fontes)

    with st.expander("Datas das fontes"):
        for k, (_, periodo, data) in fontes.items():
            st.caption(f"{FONTES[k][0]} · {data} · {periodo}")

    listas = {}
    if {"consumo", "estoque"} <= fontes.keys():
        listas["Peças consumidas sem saldo utilizável positivo"] = _triagem_consumo(
            fontes["consumo"][0], fontes["estoque"][0],
        )
    if "requisicoes" in fontes:
        df = fontes["requisicoes"][0]
        listas["Requisições sem data prevista"] = df.loc[df["Previsão de entrega"].isna()]
    if "pedidos" in fontes:
        df = fontes["pedidos"][0]
        listas["Pedidos EME com diferença de quantidade"] = df.loc[
            df["Tipo"].eq("EME") & df["Qtd. pedida"].gt(df["Qtd. atendida"])
        ]
    if "os" in fontes:
        df = fontes["os"][0]
        listas["OS com prioridade E"] = df.loc[df["Prioridade"].eq("E")]
    if listas:
        st.subheader("Listas de triagem")
        st.caption("Os registros incluem os códigos de status de origem. Compare-os antes de usar a lista para cobrança.")
        if st.session_state.get("v2_prioridades_lista") not in listas:
            st.session_state["v2_prioridades_lista"] = next(iter(listas))
        escolha = st.radio("Lista", list(listas), key="v2_prioridades_lista", label_visibility="collapsed",
                          format_func=lambda nome: f"{nome} ({len(listas[nome]):,})".replace(",", "."))
        lista = listas[escolha]
        if "Situação no extrato" in lista:
            situacao = st.radio("Situação no extrato", ("Todas", *sorted(lista["Situação no extrato"].unique())),
                                horizontal=True, key="v2_triagem_estoque")
            if situacao != "Todas":
                lista = lista.loc[lista["Situação no extrato"].eq(situacao)]
        _tabela(lista, "prioridades")


def render(chave):
    titulo, pasta, _, _ = FONTES[chave]
    st.subheader(titulo)
    fonte = _fonte(chave)
    with st.expander("Fonte SILOMS e atualização", expanded=fonte is None):
        st.markdown(f"[Pasta da fonte no Drive](https://drive.google.com/drive/folders/{pasta})")
        if st.button(f"Atualizar {titulo} pelo Drive", key=f"v2_sync_{chave}"):
            try:
                with st.spinner("Buscando e conferindo a exportação SILOMS…"):
                    drive_sync.garantir_credencial_arquivo()
                    sincronizar_fonte(chave)
                st.success("Relatório atualizado.")
            except (ValueError, OSError, drive_sync.DriveSyncError):
                st.error("Falha na atualização. Verifique o acesso da conta de serviço e a exportação XLSX no Drive.")
    if fonte is None:
        st.info("Carregue um relatório válido pelo botão de atualização.")
        return
    df, filtros, obtido_em = fonte
    st.caption(f"Extraído em {obtido_em} · {filtros}")
    if chave == "consumo":
        extraido = pd.to_datetime(obtido_em, dayfirst=True, errors="coerce")
        if pd.notna(extraido) and not extraido.is_month_end and df["Competência"].eq(extraido.strftime("%Y-%m")).any():
            st.caption(f"Competência {extraido:%m/%Y} parcial até a extração.")

    busca = st.text_input("Buscar por PN, CFF, nomenclatura ou número", key=f"v2_busca_{chave}").strip()
    if busca:
        df = _buscar(df, busca)
    with st.expander("Filtros do relatório"):
        if chave == "consumo" and not df.empty:
            if st.checkbox("Peças com consumo em pelo menos duas competências", key="v2_consumo_recorrente"):
                frequencia = df.loc[df["Consumo"].gt(0)].groupby(CHAVE_PECA)["Competência"].nunique()
                recorrentes = frequencia[frequencia.ge(2)].reset_index()[CHAVE_PECA]
                df = df.merge(recorrentes, on=CHAVE_PECA)
        if not df.empty:
            df = _filtros(chave, df, obtido_em)
        if chave == "estoque":
            consumo = _fonte("consumo")
            if consumo is not None and st.checkbox("Com consumo na base disponível", key="v2_estoque_consumo"):
                df = df.merge(consumo[0][CHAVE_PECA].drop_duplicates(), on=CHAVE_PECA)
    if df.empty:
        st.info("Nenhum registro corresponde à busca e aos filtros.")
        return
    graficos, registros = st.tabs(["Gráficos", "Registros"])
    with graficos:
        df = _visuais(chave, df)
    with registros:
        _tabela(df, chave)
