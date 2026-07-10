"""Página inicial da área "Projetos" — seleção entre MTA e TPJL. Cada card
mostra tudo (nome, descrição, filtro, indicadores e última atualização)
dentro do próprio card, sem indicadores soltos abaixo — redesenho pedido
pelo Wallace em 2026-07-09.
"""

from datetime import datetime

import streamlit as st

from projetos.components.paleta import STATUS, moeda_compacta, selo
from projetos.regras.tpjl_regras import eh_pendencia

MOEDA_SIMULADA_MTA = 1_284_930.55
MOEDA_SIMULADA_TPJL = 842_110.20


def _indicadores_mta(df):
    if df is None or df.empty:
        return {
            "total": 47, "pendencias": 12, "valor_total": MOEDA_SIMULADA_MTA,
            "simulado": True,
        }
    pendencias = int((df["situacao_consolidada"] != "Atendido").sum())
    return {
        "total": len(df), "pendencias": pendencias,
        "valor_total": df["valor"].sum(skipna=True), "simulado": False,
    }


def _indicadores_tpjl(dados_por_ano):
    if not dados_por_ano:
        return {
            "total": 163, "pendencias": 28, "valor_total": MOEDA_SIMULADA_TPJL,
            "simulado": True,
        }
    total = sum(len(df) for df in dados_por_ano.values())
    pendencias = sum(int(df["status_atual"].apply(eh_pendencia).sum()) for df in dados_por_ano.values())
    valor_total = sum(df["valor_total"].sum(skipna=True) for df in dados_por_ano.values())
    return {"total": total, "pendencias": pendencias, "valor_total": valor_total, "simulado": False}


def _card(titulo, subtitulo, filtro, indicadores, atualizado_em, key):
    simulado = indicadores.get("simulado")
    atualizado_texto = (
        f"Atualizado em {datetime.fromtimestamp(atualizado_em).strftime('%d/%m/%Y às %H:%M')}"
        if atualizado_em else "Ainda não atualizado"
    )
    selo_html = selo("Dados simulados", "warning") if simulado else selo("Dados reais", "good")

    st.markdown(
        f"""<div class="pj-card-projeto">
            <div class="pcp-nome">{titulo}</div>
            <div class="pcp-desc">{subtitulo}</div>
            <div style="margin-bottom:12px;">
                <span class="pj-selo-filtro">{filtro}</span> {selo_html}
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px;">
                <div>
                    <div style="font-size:22px;font-weight:800;color:#F3F6F9;">{indicadores['total']}</div>
                    <div style="font-size:12.5px;color:#A6B2C1;">registros</div>
                </div>
                <div>
                    <div style="font-size:22px;font-weight:800;color:{STATUS['critical'] if indicadores['pendencias'] else '#F3F6F9'};">{indicadores['pendencias']}</div>
                    <div style="font-size:12.5px;color:#A6B2C1;">pendências</div>
                </div>
                <div style="grid-column:span 2;">
                    <div style="font-size:22px;font-weight:800;color:#F4A62A;">{moeda_compacta(indicadores['valor_total'])}</div>
                    <div style="font-size:12.5px;color:#A6B2C1;">valor total</div>
                </div>
            </div>
            <div style="font-size:12.5px;color:#718096;margin-bottom:2px;">{atualizado_texto}</div>
        </div>""",
        unsafe_allow_html=True,
    )
    return st.button(f"Abrir dashboard — {titulo}  →", key=key, width="stretch")


def render(dados):
    ultima = max([t for t in (dados.get("mta_atualizado_em"), dados.get("tpjl_atualizado_em")) if t], default=None)
    ultima_texto = datetime.fromtimestamp(ultima).strftime("%d/%m/%Y às %H:%M") if ultima else "ainda não atualizado"

    st.markdown(
        f"""<div style="margin-bottom:20px;">
            <div class="pj-titulo-pagina">Acompanhamento de Projetos</div>
            <div class="pj-subtitulo-pagina">Solicitações do MTA (DIRMAB) e requisições do TPJL (CABW/EUA), filtradas pro C-98.
            Última atualização geral: {ultima_texto}.</div>
        </div>""",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2, gap="medium")

    with col1:
        clicou = _card(
            "MTA", "Acompanhamento e Solicitações", "Projeto: C-98",
            _indicadores_mta(dados.get("mta")), dados.get("mta_atualizado_em"),
            key="proj_card_mta",
        )
        if clicou:
            st.session_state["projetos_pagina"] = "MTA"
            st.rerun()

    with col2:
        clicou = _card(
            "TPJL", "Controle CABW", "Projeto: U8",
            _indicadores_tpjl(dados.get("tpjl")), dados.get("tpjl_atualizado_em"),
            key="proj_card_tpjl",
        )
        if clicou:
            st.session_state["projetos_pagina"] = "TPJL"
            st.rerun()
