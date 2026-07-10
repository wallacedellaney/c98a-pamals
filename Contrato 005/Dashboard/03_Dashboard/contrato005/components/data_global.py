"""Controle de data global — pedido do Wallace em 2026-07-10: arrastar um
slider pra qualquer dia sincroniza Reparáveis, Pagamentos, Empréstimos e
Emergências Abertas pro estado daquele dia. Reaproveita os históricos
diários já existentes de cada fonte (nenhuma base nova) — ver
00_Instrucoes/analise_periodo.md.

Cada fonte só tem histórico a partir de um dia diferente (Emergências desde
2026-07-06; Reparáveis/Pagamentos/Empréstimos desde 2026-07-10, dia em que
essa gravação começou pra elas) — nada retroativo. Quando a data escolhida
não tem snapshot de uma fonte específica, essa página mostra o estado
ATUAL (mais recente) normalmente, sem quebrar nem inventar dado.

Design deliberado (pedido do Wallace: "não reescrever o projeto inteiro,
implementar em módulos, preservando a lógica existente"): cada página
continua exatamente como estava pra "hoje" (o caso mais comum) — só quando
uma data PASSADA é escolhida é que a página troca, no topo do próprio
render(), pra uma visão histórica reduzida (só os campos que o snapshot
daquele dia guardou). Zero mudança na lógica normal de cada página.
"""

import pandas as pd
import streamlit as st

FONTES = {
    "reparaveis": {
        "chave_historico": "historico_reparaveis",
        "colunas": ["os", "pn", "nomenclatura", "unidade_solicitante", "situacao", "condicao", "onde_se_encontra", "tat_siloms"],
        "nomes": {
            "os": "OS", "pn": "PN", "nomenclatura": "Nomenclatura", "unidade_solicitante": "Unidade",
            "situacao": "Situação", "condicao": "Condição", "onde_se_encontra": "Onde se encontra",
            "tat_siloms": "TAT SILOMS",
        },
        "titulo": "Reparáveis",
    },
    "pagamentos": {
        "chave_historico": "historico_pagamentos",
        "colunas": ["tipo_registro", "modulo", "referencia", "numero_recibo", "numero_nota_fiscal", "valor_nfs", "faturado", "pendente", "situacao"],
        "nomes": {
            "tipo_registro": "Tipo", "modulo": "Módulo", "referencia": "Referência", "numero_recibo": "Recibo",
            "numero_nota_fiscal": "NF", "valor_nfs": "Valor NF", "faturado": "Faturado", "pendente": "Pendente",
            "situacao": "Situação",
        },
        "titulo": "Pagamentos",
    },
    "devolucoes": {
        "chave_historico": "historico_devolucoes",
        "colunas": ["numero_ordem", "part_number", "categoria", "destino", "anv", "status"],
        "nomes": {
            "numero_ordem": "Nº Ordem", "part_number": "Part Number", "categoria": "Categoria",
            "destino": "Destino", "anv": "Aeronave", "status": "Status",
        },
        "titulo": "Empréstimos",
    },
    "emergencias": {
        "chave_historico": "historico_emergencias",
        "colunas": ["numero_emergencia", "om", "matricula_aeronave", "pn", "situacao", "tpemg", "prazo_entrega", "dias_atraso", "estoque"],
        "nomes": {
            "numero_emergencia": "Emergência", "om": "Unidade", "matricula_aeronave": "Aeronave", "pn": "PN",
            "situacao": "Status", "tpemg": "Tipo", "prazo_entrega": "Prazo", "dias_atraso": "Dias de atraso",
            "estoque": "Estoque",
        },
        "titulo": "Emergências Abertas",
    },
}


def _todas_as_datas(dados):
    """União de todas as datas com snapshot em qualquer fonte — define as
    opções do slider (o mais amplo possível, cada fonte filtra o que não tem)."""
    datas = set()
    for config in FONTES.values():
        historico = dados.get(config["chave_historico"])
        if historico is not None and not historico.empty:
            datas |= set(pd.to_datetime(historico["data_snapshot"]).dt.date.unique())
    return sorted(datas)


def render_seletor_global(dados):
    """Slider de data global — chamar 1x em contrato_app.py, antes de
    despachar pra página ativa. Grava em st.session_state["data_global"] e
    devolve a data escolhida (ou None se nenhuma fonte tiver histórico)."""
    datas = _todas_as_datas(dados)
    if not datas:
        st.session_state["data_global"] = None
        return None

    if st.session_state.get("data_global") not in datas:
        st.session_state["data_global"] = datas[-1]

    col_slider, col_info = st.columns([3, 1])
    with col_slider:
        escolhida = st.select_slider(
            "📅 Controle de data global — arraste pra ver o sistema em qualquer dia",
            options=datas, value=st.session_state["data_global"],
            format_func=lambda d: d.strftime("%d/%m/%Y"), key="data_global_slider",
        )
    st.session_state["data_global"] = escolhida
    with col_info:
        st.write("")
        if escolhida == datas[-1]:
            st.caption("Mostrando dados **atuais** (mais recentes).")
        else:
            st.caption(f"Visão histórica de **{escolhida.strftime('%d/%m/%Y')}**.")
    return escolhida


def mostrar_nota_historica_se_necessario(dados):
    """Versão "leve" do guard — não substitui a página (Visão Geral mistura
    várias fontes, não dá pra reconstruir ela inteira a partir dos
    snapshots individuais sem duplicar toda a lógica de cada card), só
    avisa que os números abaixo são de HOJE, mesmo se uma data passada
    estiver selecionada no controle global."""
    data_global = st.session_state.get("data_global")
    if data_global is None:
        return
    datas = _todas_as_datas(dados)
    if not datas or data_global == datas[-1]:
        return
    st.info(
        f"📅 O controle de data global está em **{data_global.strftime('%d/%m/%Y')}**, mas a Visão Geral "
        "sempre mostra os números atuais (ela mistura várias fontes, não tem uma versão histórica própria "
        "ainda). Pra ver o retrato daquele dia, veja Reparáveis, Emergências Abertas, Pagamentos ou "
        "Empréstimos individualmente."
    )


def mostrar_snapshot_se_necessario(dados, chave_fonte):
    """Se a data global NÃO for a mais recente E existir snapshot daquele
    dia pra essa fonte específica, renderiza a visão histórica reduzida e
    devolve True (quem chamou deve `return` nesse caso). Senão devolve
    False e a página renderiza exatamente como sempre renderizou."""
    data_global = st.session_state.get("data_global")
    config = FONTES.get(chave_fonte)
    if data_global is None or config is None:
        return False

    historico = dados.get(config["chave_historico"])
    if historico is None or historico.empty:
        return False

    datas_da_fonte = sorted(pd.to_datetime(historico["data_snapshot"]).dt.date.unique())
    if not datas_da_fonte or data_global == datas_da_fonte[-1]:
        return False

    if data_global not in datas_da_fonte:
        st.info(
            f"Essa fonte ainda não tinha histórico gravado em {data_global.strftime('%d/%m/%Y')} "
            f"(começou em {datas_da_fonte[0].strftime('%d/%m/%Y')}) — mostrando os dados atuais abaixo."
        )
        return False

    snapshot = historico[pd.to_datetime(historico["data_snapshot"]).dt.date == data_global]
    st.title(config["titulo"])
    st.info(
        f"📅 Visão histórica de **{data_global.strftime('%d/%m/%Y')}** (controle de data global) — "
        "mostra só os campos gravados no snapshot daquele dia. Pra ver todos os detalhes de hoje, "
        "arraste o slider lá em cima pro dia mais recente."
    )
    tabela = snapshot[config["colunas"]].rename(columns=config["nomes"])
    st.dataframe(tabela, hide_index=True, width="stretch", height=min(35 * (len(tabela) + 1) + 3, 480))
    st.caption(f"{len(tabela)} registro(s) nesse snapshot.")
    csv = tabela.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Exportar (CSV)", csv, file_name=f"{chave_fonte}_{data_global}.csv", mime="text/csv",
        key=f"data_global_csv_{chave_fonte}",
    )
    return True
