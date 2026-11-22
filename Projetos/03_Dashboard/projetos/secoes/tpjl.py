"""Dashboard do projeto TPJL — Controle CABW, filtrado por PJT = U8.
2025 e 2026 ficam separados (decisão do Wallace em 2026-07-09 — não fundir
os anos), com uma 4ª aba "Visão consolidada" combinando os dois. Ver
00_Instrucoes/tpjl.md.

Redesenho visual completo em 2026-07-09:
- "Registros vencidos por situação" tinha um bug de rótulo: mostrava TODAS
  as 5 situações de previsão (inclusive "Sem data definida"/"Cancelado")
  como se fossem "vencidas". Corrigido: o gráfico agora se chama
  "Distribuição por situação da previsão" (as 5 categorias, corretamente
  nomeadas) e existe um indicador separado "Previsões vencidas" + estado
  vazio profissional quando não há nenhuma.
- O funil (plotly Funnel, que parecia barras soltas sem relação real de
  conversão) foi substituído por "Distribuição por etapa do processo":
  etapas na ordem real do processo, cada uma com quantidade, % do total e
  valor — sem simular uma conversão que a planilha não permite calcular.
- "Em cotação" também agrupa "Selecionada para Cotação" (grafia real da
  planilha) — mesma etapa do processo, nomes diferentes.
"""

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from projetos.components.atualizacao import botao_atualizar, status_atualizacao_html
from projetos.components.evolucao import secao_evolucao
from projetos.components.paleta import (
    CATEGORICA, COR_SITUACAO_PREVISAO, INK, LINE, PANEL, SECONDARY, STATUS,
    PRIMARY as AMBER,
    cabecalho_pagina, cartao_indicador, grade_indicadores, layout_grafico, moeda_compacta, moeda_completa,
)
from projetos.regras.tpjl_regras import eh_pendencia, normalizar
from projetos.secoes import tpjl_extras

COLUNAS_TABELA = [
    "numero_requisicao", "pn", "descricao", "qtd", "valor_unit", "valor_total",
    "status_comprar", "status_11g", "status", "status_atual",
    "previsao_empenho", "situacao_previsao", "dias_atraso", "dpe", "observacao_coordenadores",
]
NOMES_COLUNAS = {
    "numero_requisicao": "Nº Requisição", "pn": "PN", "descricao": "Descrição", "qtd": "Quantidade",
    "valor_unit": "Valor unitário", "valor_total": "Valor total", "status_comprar": "Status Comprar",
    "status_11g": "Status 11G", "status": "Status", "status_atual": "Status atual",
    "previsao_empenho": "Previsão para empenho", "situacao_previsao": "Situação da previsão",
    "dias_atraso": "Dias de atraso", "dpe": "DPE", "observacao_coordenadores": "Observação dos coordenadores",
}
ETAPAS_PROCESSO = [
    ("Solicitação", ("Análise do Pedido",)),
    ("Cotação", ("Em Cotação", "Selecionada para Cotação", "Recebida na Comissão", "Recebida no Solicitante")),
    ("Validação", ("Validada", "Aguardando Validação")),
    ("Mapa", ("Mapa Gerado", "Mapa Aprovado")),
    ("Empenho solicitado", ("Empenho Solicitado",)),
    ("Empenho aprovado", ("Empenho Aprovado",)),
    ("Empenhado", ("Empenhado",)),
]
STATUS_INICIAIS_OU_FINAIS = {"SEM INFORMACAO", "EMPENHADO", "CANCELADO", "ITEM DESERTO", "ITEM FRACASSADO"}


def _rotular_barras(fig, valores):
    fig.update_traces(text=[moeda_compacta(v) for v in valores], texttemplate="%{text}",
                       textposition="outside", cliponaxis=False)
    return fig


def _eh_status(valor, *nomes):
    alvo = {normalizar(n) for n in nomes}
    return normalizar(valor) in alvo


def _em_andamento(status_atual_valor):
    """Ativamente em processamento — pendente (ver eh_pendencia) e com
    status já identificado (não "Sem informação")."""
    return eh_pendencia(status_atual_valor) and normalizar(status_atual_valor) != "SEM INFORMACAO"


def _atualizar():
    from projetos.data.atualizar_drive import atualizar_fonte
    return atualizar_fonte("tpjl")


def _concatenar(dados_por_ano):
    partes = []
    for ano, df in dados_por_ano.items():
        parte = df.copy()
        parte["ano"] = ano
        partes.append(parte)
    return pd.concat(partes, ignore_index=True)


def _indicadores(df, sufixo):
    total = len(df)
    qtd_itens = df["qtd"].sum(skipna=True)
    valor_total = df["valor_total"].sum(skipna=True)
    empenhados = int(df["status_atual"].apply(lambda s: _eh_status(s, "Empenhado")).sum())
    em_andamento = int(df["status_atual"].apply(_em_andamento).sum())
    pendencias = int(df["status_atual"].apply(eh_pendencia).sum())
    cancelados = int(df["status_atual"].apply(lambda s: _eh_status(s, "Cancelado")).sum())
    sem_previsao = int((df["situacao_previsao"] == "Sem data definida").sum())

    st.markdown('<div class="pj-titulo-secao">Indicadores principais</div>', unsafe_allow_html=True)
    grade_indicadores([
        cartao_indicador("Requisições U8", total, None, "primary"),
        cartao_indicador("Itens (quantidade)", int(qtd_itens) if pd.notna(qtd_itens) else 0, None, "primary"),
        cartao_indicador("Valor total", moeda_compacta(valor_total), moeda_completa(valor_total), "primary"),
        cartao_indicador("Empenhados", empenhados, f"{100 * empenhados / total:.0f}% do total" if total else None, "good"),
        cartao_indicador("Em andamento", em_andamento, None, "info"),
        cartao_indicador("Pendências", pendencias, "Ainda não concluídas" if pendencias else None, "warning"),
        cartao_indicador("Cancelados", cancelados, None, "neutro"),
        cartao_indicador("Sem previsão definida", sem_previsao, None, "neutro"),
    ])

    with st.expander("Outros indicadores"):
        empenho_solicitado = int(df["status_atual"].apply(lambda s: _eh_status(s, "Empenho Solicitado")).sum())
        empenho_aprovado = int(df["status_atual"].apply(lambda s: _eh_status(s, "Empenho Aprovado")).sum())
        em_cotacao = int(df["status_atual"].apply(lambda s: _eh_status(s, "Em Cotação", "Selecionada para Cotação")).sum())
        mapas_gerados = int(df["status_atual"].apply(lambda s: _eh_status(s, "Mapa Gerado")).sum())
        mapas_aprovados = int(df["status_atual"].apply(lambda s: _eh_status(s, "Mapa Aprovado")).sum())
        fracassados_desertos = int(df["status_atual"].apply(lambda s: _eh_status(s, "Item Fracassado", "Item Deserto")).sum())
        previsoes_vencidas = int((df["situacao_previsao"] == "Vencido").sum())
        sem_observacao = int(df["observacao_coordenadores"].isna().sum())

        grade_indicadores([
            cartao_indicador("Empenho solicitado", empenho_solicitado, None, "info"),
            cartao_indicador("Empenho aprovado", empenho_aprovado, None, "info"),
            cartao_indicador("Em cotação", em_cotacao, None, "info"),
            cartao_indicador("Mapas gerados", mapas_gerados, None, "neutro"),
            cartao_indicador("Mapas aprovados", mapas_aprovados, None, "neutro"),
            cartao_indicador("Fracassados/desertos", fracassados_desertos, None, "critical"),
            cartao_indicador("Previsões vencidas", previsoes_vencidas, None, "critical" if previsoes_vencidas else "good"),
            cartao_indicador("Sem observação dos coordenadores", sem_observacao, None, "neutro"),
        ])


def _situacao_do_processo(df, sufixo):
    st.markdown('<div class="pj-titulo-secao">Situação do processo</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.caption("Distribuição por Status atual (quantidade)")
        contagem = df["status_atual"].value_counts().reset_index()
        contagem.columns = ["status_atual", "quantidade"]
        contagem = contagem.sort_values("quantidade", ascending=False)
        if len(contagem) > 8:
            principais = contagem.iloc[:8]
            outros = pd.DataFrame([{"status_atual": "Outros", "quantidade": contagem.iloc[8:]["quantidade"].sum()}])
            contagem = pd.concat([principais, outros], ignore_index=True)
        contagem = contagem.sort_values("quantidade")
        fig = px.bar(contagem, x="quantidade", y="status_atual", orientation="h",
                     color_discrete_sequence=[CATEGORICA[0]])
        fig.update_traces(text=contagem["quantidade"], textposition="outside", cliponaxis=False)
        fig.update_layout(xaxis_title="", yaxis_title="", yaxis={"type": "category"})
        layout_grafico(fig, altura=360)
        st.plotly_chart(fig, width="stretch", key=f"tpjl_situacao_qtd_{sufixo}")

    with col2:
        st.caption("Valores por situação (participação no total)")
        agrupado = df.groupby("status_atual")["valor_total"].sum(min_count=1).reset_index()
        agrupado = agrupado.sort_values("valor_total", ascending=False)
        if len(agrupado) > 8:
            principais = agrupado.iloc[:8]
            outros = pd.DataFrame([{"status_atual": "Outros", "valor_total": agrupado.iloc[8:]["valor_total"].sum()}])
            agrupado = pd.concat([principais, outros], ignore_index=True)
        fig = px.treemap(agrupado, path=["status_atual"], values="valor_total",
                          color_discrete_sequence=CATEGORICA)
        fig.update_traces(
            texttemplate="%{label}<br>%{customdata[0]}",
            customdata=[[moeda_compacta(v)] for v in agrupado["valor_total"]],
        )
        layout_grafico(fig, altura=360)
        st.plotly_chart(fig, width="stretch", key=f"tpjl_situacao_valor_{sufixo}")


def _distribuicao_etapa_processo(df, sufixo):
    st.markdown('<div class="pj-titulo-secao">Distribuição por etapa do processo</div>', unsafe_allow_html=True)
    st.caption("Quantidade, participação e valor por etapa — não representa uma conversão sequencial garantida, "
               "já que nem todo status da planilha permite identificar a etapa anterior.")

    total = len(df)
    linhas = []
    for nome, sinonimos in ETAPAS_PROCESSO:
        mascara = df["status_atual"].apply(lambda s: _eh_status(s, *sinonimos))
        qtd = int(mascara.sum())
        valor = df.loc[mascara, "valor_total"].sum(skipna=True)
        if qtd > 0:
            linhas.append({"etapa": nome, "quantidade": qtd, "valor": valor, "pct": 100 * qtd / total if total else 0})

    if not linhas:
        st.info("Sem etapas identificáveis no processo pra esse conjunto de dados.")
        return

    tabela = pd.DataFrame(linhas)
    fig = px.bar(tabela, x="quantidade", y="etapa", orientation="h", color_discrete_sequence=[AMBER])
    fig.update_traces(
        text=[f"{q} ({p:.0f}%) · {moeda_compacta(v)}" for q, p, v in zip(tabela["quantidade"], tabela["pct"], tabela["valor"])],
        textposition="outside", cliponaxis=False,
    )
    fig.update_layout(
        xaxis_title="", yaxis_title="",
        yaxis={"categoryorder": "array", "categoryarray": [e for e, _ in ETAPAS_PROCESSO][::-1]},
    )
    layout_grafico(fig, altura=360)
    st.plotly_chart(fig, width="stretch", key=f"tpjl_etapas_{sufixo}")


def _analise_previsoes(df, sufixo):
    st.markdown('<div class="pj-titulo-secao">Análise de previsões</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.caption("Distribuição por situação da previsão")
        contagem = df["situacao_previsao"].value_counts().reset_index()
        contagem.columns = ["situacao", "quantidade"]
        cores = {s: STATUS.get(COR_SITUACAO_PREVISAO.get(s, "neutro"), SECONDARY) for s in contagem["situacao"]}
        fig = px.bar(contagem, x="situacao", y="quantidade", color="situacao", color_discrete_map=cores)
        fig.update_traces(text=contagem["quantidade"], textposition="outside", cliponaxis=False)
        fig.update_layout(xaxis_title="", yaxis_title="", showlegend=False)
        layout_grafico(fig, altura=340)
        st.plotly_chart(fig, width="stretch", key=f"tpjl_previsao_{sufixo}")

    with col2:
        st.caption("Vencidos")
        vencidos = df[df["situacao_previsao"] == "Vencido"]
        if vencidos.empty:
            st.success("Nenhuma previsão vencida encontrada.")
        else:
            st.metric("Requisições vencidas", len(vencidos))
            resumo = vencidos[["numero_requisicao", "descricao", "dias_atraso"]].sort_values("dias_atraso", ascending=False)
            resumo.columns = ["Nº Requisição", "Descrição", "Dias de atraso"]
            st.dataframe(resumo, hide_index=True, width="stretch", height=220)


def _filtros(df, sufixo):
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        status_atual_f = st.multiselect("Status atual", sorted(df["status_atual"].dropna().unique()), key=f"tpjl_f_status_atual_{sufixo}")
    with c2:
        situacao_f = st.multiselect("Situação da previsão", sorted(df["situacao_previsao"].dropna().unique()), key=f"tpjl_f_situacao_{sufixo}")
    with c3:
        meses = sorted(df["previsao_empenho"].dropna().dt.to_period("M").astype(str).unique())
        mes_f = st.multiselect("Previsão por mês", meses, key=f"tpjl_f_mes_{sufixo}")
    with c4:
        busca = st.text_input("🔎 Busca (Nº requisição, PN, Descrição)", key=f"tpjl_f_busca_{sufixo}")

    limpar = st.button("Limpar filtros", key=f"tpjl_f_limpar_{sufixo}")
    if limpar:
        for chave in (f"tpjl_f_status_atual_{sufixo}", f"tpjl_f_situacao_{sufixo}", f"tpjl_f_mes_{sufixo}", f"tpjl_f_busca_{sufixo}"):
            st.session_state.pop(chave, None)
        st.rerun()

    filtrado = df.copy()
    if status_atual_f:
        filtrado = filtrado[filtrado["status_atual"].isin(status_atual_f)]
    if situacao_f:
        filtrado = filtrado[filtrado["situacao_previsao"].isin(situacao_f)]
    if mes_f:
        filtrado = filtrado[filtrado["previsao_empenho"].dt.to_period("M").astype(str).isin(mes_f)]
    if busca:
        b = busca.strip().lower()
        filtrado = filtrado[
            filtrado["numero_requisicao"].astype(str).str.lower().str.contains(b, na=False)
            | filtrado["pn"].astype(str).str.lower().str.contains(b, na=False)
            | filtrado["descricao"].astype(str).str.lower().str.contains(b, na=False)
        ]
    st.caption(f"Exibindo {len(filtrado)} de {len(df)} requisições")
    return filtrado


def _painel_detalhe(registro, sufixo):
    linhas_html = []
    for campo, rotulo in NOMES_COLUNAS.items():
        valor = registro.get(campo)
        vazio = valor is None or (isinstance(valor, (float, pd.Timestamp)) and pd.isna(valor))
        if vazio:
            texto = "Não informado"
        elif campo in ("valor_unit", "valor_total"):
            texto = moeda_completa(valor)
        elif campo in ("previsao_empenho", "dpe") and pd.notna(valor):
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
                Detalhe — Requisição {registro.get('numero_requisicao', 'Não informado')}
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 24px;">
                <div>{"".join(linhas_html[:metade])}</div>
                <div>{"".join(linhas_html[metade:])}</div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


def _pagina(df, sufixo, historico=None):
    if df is None or df.empty:
        st.info(f"Sem requisições U8 encontradas.")
        return

    _indicadores(df, sufixo)
    st.divider()
    _situacao_do_processo(df, sufixo)
    st.divider()
    _distribuicao_etapa_processo(df, sufixo)
    st.divider()
    _analise_previsoes(df, sufixo)
    st.divider()

    st.markdown('<div class="pj-titulo-secao">Filtros</div>', unsafe_allow_html=True)
    filtrado = _filtros(df, sufixo)

    st.markdown('<div class="pj-titulo-secao">Tabela operacional</div>', unsafe_allow_html=True)
    tabela = filtrado[COLUNAS_TABELA].rename(columns=NOMES_COLUNAS)
    evento = st.dataframe(
        tabela, hide_index=True, width="stretch", height=420,
        on_select="rerun", selection_mode="single-row", key=f"tpjl_tabela_{sufixo}",
    )
    linhas_selecionadas = evento.selection.get("rows", []) if evento else []
    if linhas_selecionadas:
        registro = filtrado.iloc[linhas_selecionadas[0]].to_dict()
        _painel_detalhe(registro, sufixo)

    csv = tabela.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar (CSV)", csv, file_name=f"tpjl_{sufixo}.csv", mime="text/csv", key=f"tpjl_csv_{sufixo}")

    st.divider()
    secao_evolucao(
        historico, chave=["ano", "numero_requisicao", "pn"], key_slider=f"tpjl_evolucao_slider_{sufixo}",
        colunas_exibir=["ano", "numero_requisicao", "pn", "status_atual", "valor_total", "situacao_previsao"],
        nomes_colunas={
            "ano": "Ano", "numero_requisicao": "Nº Requisição", "pn": "PN",
            "status_atual": "Status atual", "valor_total": "Valor total", "situacao_previsao": "Situação da previsão",
        },
    )


def _comparativo(dados_por_ano):
    resumo = {}
    for ano, df in dados_por_ano.items():
        resumo[ano] = {
            "total": len(df),
            "valor_total": df["valor_total"].sum(skipna=True),
            "qtd_itens": df["qtd"].sum(skipna=True),
        }

    st.markdown('<div class="pj-titulo-secao">Indicadores por ano</div>', unsafe_allow_html=True)
    cards = []
    for ano, r in resumo.items():
        cards.append(cartao_indicador(f"Requisições U8 — {ano}", r["total"], None, "primary"))
        cards.append(cartao_indicador(f"Valor total — {ano}", moeda_compacta(r["valor_total"]), moeda_completa(r["valor_total"]), "info"))
    grade_indicadores(cards)

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.caption("Valor total por ano")
        tabela = pd.DataFrame({"ano": [str(a) for a in resumo.keys()], "valor_total": [r["valor_total"] for r in resumo.values()]})
        fig = px.bar(tabela, x="ano", y="valor_total", color_discrete_sequence=[AMBER])
        _rotular_barras(fig, tabela["valor_total"])
        fig.update_layout(xaxis_title="", yaxis_title="", xaxis={"type": "category"})
        layout_grafico(fig, altura=340)
        st.plotly_chart(fig, width="stretch", key="tpjl_comp_valor_ano")

    with col2:
        st.caption("Comparação 2025 x 2026 — valor por Status atual")
        partes = []
        for ano, df in dados_por_ano.items():
            agrupado = df.groupby("status_atual")["valor_total"].sum(min_count=1).reset_index()
            agrupado["ano"] = str(ano)
            partes.append(agrupado)
        junto = pd.concat(partes, ignore_index=True)
        fig = px.bar(junto, x="status_atual", y="valor_total", color="ano", barmode="group",
                     color_discrete_sequence=[AMBER, STATUS["info"]])
        fig.update_layout(xaxis_title="", yaxis_title="", legend_title="")
        layout_grafico(fig, altura=340)
        st.plotly_chart(fig, width="stretch", key="tpjl_comp_status")


def render(dados):
    estado_atual = dados.get("tpjl_estado", {})

    col_titulo, col_botao = st.columns([4, 1])
    with col_titulo:
        cabecalho_pagina(
            "TPJL — Controle CABW",
            "Fontes: \"TPOB - Controle CABW 2025\" e \"TPOB - Controle CABW 2026\", aba \"COORDENADORES\"",
            "Projeto: U8",
            status_atualizacao_html(estado_atual),
        )
    with col_botao:
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        botao_atualizar("TPJL", _atualizar, key="tpjl_atualizar")

    dados_por_ano = dados.get("tpjl")
    if not dados_por_ano:
        st.info("Ainda não foi carregado — clique em \"Atualizar TPJL\" acima.")
        return

    historico = dados.get("tpjl_historico")

    (aba_consolidada, aba_2025, aba_2026, aba_comparativo,
     aba_consumo, aba_estoque, aba_solicitacoes) = st.tabs([
        "Visão consolidada", "2025", "2026", "Comparativo",
        "Consumo", "Estoque", "Solicitações",
    ])
    with aba_consolidada:
        _pagina(_concatenar(dados_por_ano), "consolidado", historico=historico)
    with aba_2025:
        hist_2025 = historico[historico["ano"] == "2025"] if historico is not None and not historico.empty else historico
        _pagina(dados_por_ano.get(2025), "2025", historico=hist_2025)
    with aba_2026:
        hist_2026 = historico[historico["ano"] == "2026"] if historico is not None and not historico.empty else historico
        _pagina(dados_por_ano.get(2026), "2026", historico=hist_2026)
    with aba_comparativo:
        _comparativo(dados_por_ano)
    with aba_consumo:
        tpjl_extras.render_consumo(dados)
    with aba_estoque:
        tpjl_extras.render_estoque(dados)
    with aba_solicitacoes:
        tpjl_extras.render_solicitacoes(dados)
