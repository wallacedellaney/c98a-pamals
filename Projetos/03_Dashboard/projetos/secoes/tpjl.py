"""Dashboard do projeto TPJL — Controle CABW, filtrado por PJT = U8.
2025 e 2026 ficam em um único tópico de navegação com seleção de ano.

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

from html import escape

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
from projetos.data.tpjl_v2 import FONTES
from projetos.secoes import tpjl_v2

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


def _indicadores(df, sufixo):
    total = len(df)
    valor_total = df["valor_total"].sum(min_count=1)
    empenhados = int(df["status_atual"].apply(lambda s: _eh_status(s, "Empenhado")).sum())
    pendencias = int(df["status_atual"].apply(eh_pendencia).sum())

    grade_indicadores([
        cartao_indicador("Requisições U8", total, None, "primary"),
        cartao_indicador("Valor total", moeda_compacta(valor_total) if pd.notna(valor_total) else "—",
                        moeda_completa(valor_total) if pd.notna(valor_total) else None, "primary"),
        cartao_indicador("Empenhados", empenhados, f"{100 * empenhados / total:.0f}% do total" if total else None, "good"),
        cartao_indicador("Pendências", pendencias, None, "warning" if pendencias else "neutro"),
    ])


def _outros_indicadores(df):
    qtd_itens = df["qtd"].sum(skipna=True)
    em_andamento = int(df["status_atual"].apply(_em_andamento).sum())
    cancelados = int(df["status_atual"].apply(lambda s: _eh_status(s, "Cancelado")).sum())
    sem_previsao = int((df["situacao_previsao"] == "Sem data definida").sum())
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
            cartao_indicador("Itens (quantidade)", int(qtd_itens) if pd.notna(qtd_itens) else 0, None, "primary"),
            cartao_indicador("Em andamento", em_andamento, None, "info"),
            cartao_indicador("Cancelados", cancelados, None, "neutro"),
            cartao_indicador("Sem previsão definida", sem_previsao, None, "neutro"),
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
    titulo, controle = st.columns([2, 1], vertical_alignment="center")
    titulo.subheader("Situação das requisições", anchor=False)
    moeda = controle.toggle("Mostrar valores em R$", key=f"tpjl_moeda_{sufixo}")
    medida = "Valor total" if moeda else "Requisições"
    situacoes = df["status_atual"].astype("string").fillna("Sem informação")
    grupos = df.groupby(situacoes)["valor_total"]
    serie = grupos.size() if medida == "Requisições" else grupos.sum(min_count=1).dropna()
    if serie.empty:
        st.info("Nenhum valor informado para a seleção.")
        return
    serie = serie.sort_values(ascending=False, kind="stable")
    quadro = serie.rename_axis("Situação").reset_index(name="Medida")
    if len(quadro) > 8:
        restante = quadro.iloc[8:]["Medida"].sum()
        residuo = "Demais situações"
        while residuo in set(quadro.iloc[:8]["Situação"]):
            residuo += " (agrupadas)"
        quadro = pd.concat([quadro.iloc[:8], pd.DataFrame({"Situação": [residuo], "Medida": [restante]})],
                           ignore_index=True)
    quadro["Rótulo"] = quadro["Medida"].map(moeda_compacta if moeda else str)
    quadro["Detalhe"] = quadro["Medida"].map(moeda_completa if moeda else str)
    total = serie.sum()
    quadro["Participação"] = (quadro["Medida"] / total).map(lambda v: f"{v:.1%}".replace(".", ",")) if total else "—"
    fig = px.bar(quadro, x="Medida", y="Situação", orientation="h", text="Rótulo",
                 custom_data=["Detalhe", "Participação"], color_discrete_sequence=[CATEGORICA[0]])
    fig.update_traces(textposition="auto", hovertemplate="%{y}<br>" + medida
                      + ": %{customdata[0]}<br>Participação: %{customdata[1]}<extra></extra>")
    fig.update_yaxes(type="category", categoryorder="array", categoryarray=quadro["Situação"].tolist()[::-1])
    fig.update_layout(xaxis_title="Valor total (R$)" if moeda else "Requisições", yaxis_title="", showlegend=False)
    layout_grafico(fig, altura=max(245, 95 + 32 * len(quadro)))
    st.plotly_chart(fig, width="stretch", key=f"tpjl_situacao_{sufixo}")


def _distribuicao_etapa_processo(df, sufixo):
    st.markdown('<div class="pj-titulo-secao">Distribuição por etapa do processo</div>', unsafe_allow_html=True)
    st.caption("Cada requisição aparece na sua etapa identificada. A participação usa o total da seleção.")

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
    tabela["valor_exibido"] = tabela["valor"].map(moeda_completa)
    fig = px.bar(tabela, x="quantidade", y="etapa", orientation="h", text="quantidade",
                 custom_data=["pct", "valor_exibido"], color_discrete_sequence=[AMBER])
    fig.update_traces(
        textposition="auto",
        hovertemplate="%{y}<br>Requisições: %{x}<br>Participação: %{customdata[0]:.1f}%<br>Valor: %{customdata[1]}<extra></extra>",
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
        cores = {s: COR_SITUACAO_PREVISAO.get(s, STATUS["neutro"]) for s in contagem["situacao"]}
        fig = px.bar(contagem, x="quantidade", y="situacao", orientation="h", text="quantidade",
                     color="situacao", color_discrete_map=cores)
        fig.update_traces(textposition="auto", hovertemplate="%{y}<br>Requisições: %{x}<extra></extra>")
        fig.update_yaxes(categoryorder="array", categoryarray=contagem["situacao"].tolist()[::-1])
        fig.update_layout(xaxis_title="Requisições", yaxis_title="", showlegend=False)
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


def _limpar_filtros(sufixo):
    for campo in ("status_atual", "situacao", "mes", "busca"):
        st.session_state[f"tpjl_f_{campo}_{sufixo}"] = "" if campo == "busca" else []


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
        busca = st.text_input("Buscar requisição, PN ou descrição", key=f"tpjl_f_busca_{sufixo}")

    st.button("Limpar filtros", key=f"tpjl_f_limpar_{sufixo}", on_click=_limpar_filtros, args=(sufixo,))

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
            filtrado["numero_requisicao"].astype(str).str.lower().str.contains(b, na=False, regex=False)
            | filtrado["pn"].astype(str).str.lower().str.contains(b, na=False, regex=False)
            | filtrado["descricao"].astype(str).str.lower().str.contains(b, na=False, regex=False)
        ]
    return filtrado


def _painel_detalhe(registro, sufixo):
    linhas_html = []
    for campo, rotulo in NOMES_COLUNAS.items():
        valor = registro.get(campo)
        vazio = pd.isna(valor)
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
            f'<strong style="color:{INK};">{rotulo}:</strong> {escape(texto)}</div>'
        )
    metade = (len(linhas_html) + 1) // 2
    st.markdown(
        f"""<div style="background:{PANEL};border:1px solid {LINE};border-left:3px solid {AMBER};
        border-radius:10px;padding:16px 18px;margin-top:10px;">
            <div style="font-weight:700;color:{INK};margin-bottom:10px;font-size:15px;">
                Detalhe — Requisição {escape(str(registro.get('numero_requisicao', 'Não informado')))}
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 24px;">
                <div>{"".join(linhas_html[:metade])}</div>
                <div>{"".join(linhas_html[metade:])}</div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


def _registros(filtrado, sufixo):
    tabela = filtrado[COLUNAS_TABELA].rename(columns=NOMES_COLUNAS)
    evento = st.dataframe(
        tabela, hide_index=True, width="stretch", height=420,
        on_select="rerun", selection_mode="single-row", key=f"tpjl_tabela_{sufixo}",
    )
    linhas_selecionadas = evento.selection.get("rows", []) if evento else []
    if linhas_selecionadas and 0 <= linhas_selecionadas[0] < len(filtrado):
        registro = filtrado.iloc[linhas_selecionadas[0]].to_dict()
        _painel_detalhe(registro, sufixo)

    csv = tabela.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar (CSV)", csv, file_name=f"tpjl_{sufixo}.csv", mime="text/csv", key=f"tpjl_csv_{sufixo}")



def _pagina(df, sufixo, historico=None):
    if df is None or df.empty:
        st.info("Sem requisições U8 neste ano.")
        return
    with st.expander("Filtros da consulta"):
        filtrado = _filtros(df, sufixo)
    st.caption(f"{sufixo} · {len(filtrado)} de {len(df)} requisições")
    if not filtrado.empty:
        _indicadores(filtrado, sufixo)
    vista = st.segmented_control("Visualização CABW", ("Situação", "Etapas", "Previsões", "Registros", "Histórico do ano"),
                                default="Situação", required=True, label_visibility="collapsed", key=f"tpjl_vista_{sufixo}")
    if vista != "Histórico do ano":
        if filtrado.empty:
            st.info("Nenhuma requisição corresponde aos filtros selecionados.")
        else:
            renderizar = {"Situação": _situacao_do_processo, "Etapas": _distribuicao_etapa_processo,
                          "Previsões": _analise_previsoes, "Registros": _registros}
            renderizar[vista](filtrado, sufixo)
            _outros_indicadores(filtrado)
        return
    st.caption(f"Comparação das extrações de {sufixo} para o conjunto completo do ano.")
    secao_evolucao(
        historico, chave=["ano", "numero_requisicao", "pn"], key_slider=f"tpjl_evolucao_slider_{sufixo}",
        colunas_exibir=["ano", "numero_requisicao", "pn", "status_atual", "valor_total", "situacao_previsao"],
        nomes_colunas={
            "ano": "Ano", "numero_requisicao": "Nº Requisição", "pn": "PN",
            "status_atual": "Status atual", "valor_total": "Valor total", "situacao_previsao": "Situação da previsão",
        },
    )


def render(dados):
    estado_atual = dados.get("tpjl_estado", {})

    st.title("TPJL", anchor=False)
    cabw = "Controle CABW · 2025 e 2026"
    fontes = {fonte[0]: chave for chave, fonte in FONTES.items()}
    indice, periodo = st.columns([3, 1])
    topico = indice.selectbox("Consulta TPJL", ("Prioridades U8", cabw, *fontes), key="tpjl_indice")
    if topico == "Prioridades U8":
        tpjl_v2.render_prioridades()
        return
    if topico in fontes:
        tpjl_v2.render(fontes[topico])
        return

    dados_por_ano = dados.get("tpjl") or {}
    ano = periodo.radio("Ano do Controle CABW", (2025, 2026), index=1, horizontal=True, key="tpjl_ano")
    historico = dados.get("tpjl_historico")
    if historico is not None and not historico.empty:
        historico = historico.loc[historico["ano"].astype(str).eq(str(ano))]
    _pagina(dados_por_ano.get(ano), str(ano), historico=historico)
    with st.expander("Fonte e atualização do Controle CABW"):
        cabecalho_pagina("Controle CABW", "TPOB 2025 e 2026 · aba COORDENADORES", "Projeto U8",
                         status_atualizacao_html(estado_atual))
        botao_atualizar("TPJL", _atualizar, key="tpjl_atualizar")
