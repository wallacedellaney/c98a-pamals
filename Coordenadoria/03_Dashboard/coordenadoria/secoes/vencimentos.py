"""Página Vencimentos — mini-dashboard interno dividido em duas partes
clicáveis: Operadores (fonte ainda não definida — placeholder) e TMOT
(controle de vencimento de itens por hora/pouso/calendário, ver
00_Instrucoes/vencimentos.md).
"""

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from coordenadoria.components.filtros import filtro_colunas
from coordenadoria.components.paleta import AMBER, CYAN, INK, LINE, PANEL, SECONDARY, STATUS, layout_grafico
from coordenadoria.utils import atualizar_dados_vencimentos, atualizar_dados_vencimentos_operadores, VENCIMENTOS_PLANILHA_URL

OPERADORES_ESPERADOS = ["BAMN", "BABE", "CLA", "BANT", "BABR", "PAMA-LS", "DACTA II", "BACO", "BACG"]

TIPOS = ["Hora", "Pouso", "Calendário"]
COR_TIPO = {"Hora": STATUS["good"], "Pouso": CYAN, "Calendário": AMBER}
UNIDADE_TIPO = {"Hora": "horas", "Pouso": "pousos", "Calendário": "dias"}

# Limite de antecedência pro alerta de "próximo do vencimento" (item ainda não
# vencido, mas dentro dessa margem) — definido pelo Wallace: 100h, 50 pousos,
# 3 meses (3*30 = 90 dias, já que Calendário é armazenado em dias).
LIMITE_ALERTA = {"Hora": 100, "Pouso": 50, "Calendário": 90}

# Termos que escondem o item por padrão no filtro inicial de Nomenclatura da
# aba Operadores (pedido do Wallace em 2026-07-16: são peças de motor/hélice,
# já cobertas pela página "Motores") — "contém" em qualquer posição do texto
# (não só no início), confirmado com o Wallace, por isso "BERÇO DO MOTOR"
# também entra (contém "MOTOR") mesmo não começando com o termo. "ENGI" (não
# "ENGINE") de propósito, pra pegar também "RING AY-ENGI" (nomenclatura vem
# truncada na fonte, sem o "NE" final) — mas "RING SNAP – ANEL FRENO" (peça
# de freio) fica de fora, já que não contém nenhum desses termos. Segue
# sempre editável no filtro — é só o valor inicial.
TERMOS_MOTOR_HELICE_OCULTOS = [
    "DISK", "ANEL DO", "ENGI", "MOTOR", "HUB", "IMPELLER", "HÉLICE", "KIT HSI",
]

# Situação pré-selecionada por padrão no filtro inicial da aba Operadores
# (pedido do Wallace em 2026-07-16) — "Ok"/"Condição"/"Não instalado"/"Não
# aplicável" ficam de fora do padrão, mas continuam selecionáveis.
SITUACAO_PADRAO_OPERADORES = ["Vencido", "Próximo"]


def _nomenclatura_motor_helice(nomenclatura):
    texto = str(nomenclatura or "").upper()
    return any(termo in texto for termo in TERMOS_MOTOR_HELICE_OCULTOS)


def _status_vencimento(row):
    # Célula vazia no Excel volta como NaN; bool(NaN) é True em Python e
    # marcava incorretamente "Condição"/"Não instalado" como vencido.
    if pd.notna(row["vencido"]) and bool(row["vencido"]):
        return "Vencido"
    if row["tipo_vencimento"] not in LIMITE_ALERTA:
        # Tipos sem vencimento programado por hora/pouso/calendário (ex.:
        # "Condição" — BACG "O/C", "Não instalado" — BANT) usam o próprio
        # nome do tipo como situação, em vez de forçar "Vencido"/"Próximo"/
        # "Ok" — evita hardcode de uma string por tipo novo que aparecer.
        return row["tipo_vencimento"]
    if row["disponibilidade_valor"] <= LIMITE_ALERTA[row["tipo_vencimento"]]:
        return "Próximo"
    return "Ok"


def render(dados):
    area = st.session_state.get("venc_area")
    if area == "TMOT":
        _tmot(dados)
        return
    if area == "Operadores":
        _operadores(dados)
        return
    _menu(dados)


def _estilo():
    st.markdown(
        f"""<style>
.venc-card {{
    background: {PANEL};
    border: 1px solid {LINE};
    border-radius: 10px;
    padding: 0.9rem 1rem;
    box-shadow: 0 2px 6px rgba(0,0,0,0.25);
}}
.venc-card .valor {{ font-size: 2.1rem; font-weight: 800; }}
.venc-card .label {{ font-size: 1rem; color: {INK}; margin-top: 0.35rem; font-weight: 700; }}
.venc-card .sub {{ font-size: 0.85rem; color: {SECONDARY}; margin-top: 0.15rem; }}
.venc-menu-card button {{
    height: 9rem !important;
    text-align: center !important;
    font-size: 1.15rem !important;
    white-space: pre-line !important;
}}
</style>""",
        unsafe_allow_html=True,
    )


def _menu(dados):
    st.title("Vencimentos")
    st.caption("Controle de vencimentos da frota C-98 — operadores e TMOT (itens por hora, pouso e calendário).")
    _estilo()

    tmot = dados["venc_tmot"]
    operadores_df = dados["venc_operadores"]
    c1, c2 = st.columns(2)
    with c1:
        if operadores_df.empty:
            sub_op = "Em construção"
        else:
            n_ops = operadores_df["operador"].nunique()
            sub_op = f"{len(operadores_df)} itens · {n_ops} de {len(OPERADORES_ESPERADOS)} operadores"
        st.markdown('<div class="venc-menu-card">', unsafe_allow_html=True)
        if st.button(f"👥\n\n**Operadores**\n\n{sub_op}", key="venc_ir_operadores", width="stretch"):
            st.session_state["venc_area"] = "Operadores"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        sub = f"{len(tmot)} itens cadastrados" if not tmot.empty else "sem dados ainda"
        st.markdown('<div class="venc-menu-card">', unsafe_allow_html=True)
        if st.button(f"🔧\n\n**TMOT**\n\n{sub}", key="venc_ir_tmot", width="stretch"):
            st.session_state["venc_area"] = "TMOT"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


def _operadores(dados):
    st.title("Vencimentos — Operadores")
    st.caption("Controle de Vencimentos enviado por cada operador/base — cada um no seu próprio formato.")
    _estilo()

    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        if st.button("← Voltar", key="venc_op_voltar"):
            st.session_state["venc_area"] = None
            st.rerun()
    with col2:
        if st.button("🔄 Atualizar dados", key="venc_op_atualizar"):
            with st.spinner("Reprocessando dados locais..."):
                atualizar_dados_vencimentos_operadores()
            st.rerun()

    df = dados["venc_operadores"]
    if df.empty:
        st.info(
            "Nenhum dado carregado ainda. Peça ao Claude para buscar o Controle de Vencimentos "
            "mais recente de cada operador (pasta \"MAPEM / DIAGONAL / VENCIMENTOS\")."
        )
        return

    if dados["venc_operadores_atualizado_em"]:
        atualizado = datetime.fromtimestamp(dados["venc_operadores_atualizado_em"]).strftime("%d/%m/%Y %H:%M")
        st.caption(f"Última atualização dos dados: **{atualizado}**")

    presentes = sorted(df["operador"].unique())
    faltando = [op for op in OPERADORES_ESPERADOS if op not in presentes]
    st.caption(
        f"Operadores incorporados: **{', '.join(presentes)}**"
        + (f" · faltam: {', '.join(faltando)} (ver 00_Instrucoes/vencimentos.md)" if faltando else "")
    )

    df = df.copy()
    df["_status"] = df.apply(_status_vencimento, axis=1)

    aeronaves_rac = dados.get("rac_aeronaves")
    if aeronaves_rac is not None and not aeronaves_rac.empty:
        matriculas_contrato = set(
            aeronaves_rac.loc[aeronaves_rac["contrato"] == "Dentro do contrato", "matricula"].astype(str)
        )
    else:
        matriculas_contrato = set()

    st.divider()
    total = len(df)
    vencidos = int((df["_status"] == "Vencido").sum())
    proximos = int((df["_status"] == "Próximo").sum())
    c1, c2, c3, c4 = st.columns(4)
    _card(c1, total, "Total de itens", f"{len(presentes)} de {len(OPERADORES_ESPERADOS)} operadores", INK)
    _card(c2, vencidos, "Vencidos", "já passaram do limite", STATUS["critical"] if vencidos else STATUS["good"])
    _card(c3, proximos, "Próximos do vencimento", "≤100h / ≤50 pousos / ≤3 meses", AMBER if proximos else STATUS["good"])
    _card(c4, len(presentes), "Operadores nesta base", ", ".join(presentes), CYAN)

    st.divider()
    abas = st.tabs([f"Por {t.lower()}" for t in TIPOS])
    for aba, tipo in zip(abas, TIPOS):
        with aba:
            _secao_tipo_operadores(df, tipo, matriculas_contrato)


def _card(col, valor, label, sub, cor):
    with col:
        st.markdown(
            f'<div class="venc-card"><div class="valor" style="color:{cor};">{valor}</div>'
            f'<div class="label">{label}</div><div class="sub">{sub}</div></div>',
            unsafe_allow_html=True,
        )


def _tmot(dados):
    st.title("Vencimentos — TMOT")
    st.caption("Itens de manutenção com vencimento por hora, pouso ou calendário.")
    _estilo()

    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        if st.button("← Voltar", key="venc_tmot_voltar"):
            st.session_state["venc_area"] = None
            st.rerun()
    with col2:
        if st.button("🔄 Atualizar dados", key="venc_tmot_atualizar"):
            with st.spinner("Reprocessando dados locais..."):
                atualizar_dados_vencimentos()
            st.rerun()
    with col3:
        st.link_button("🔗 Planilha original", VENCIMENTOS_PLANILHA_URL)

    df = dados["venc_tmot"]
    if df.empty:
        st.info("Nenhum dado de vencimento carregado ainda.")
        return

    if dados["venc_atualizado_em"]:
        atualizado = datetime.fromtimestamp(dados["venc_atualizado_em"]).strftime("%d/%m/%Y %H:%M")
        st.caption(f"Última atualização dos dados: **{atualizado}**")

    df = df.copy()
    df["_status"] = df.apply(_status_vencimento, axis=1)

    st.divider()
    total = len(df)
    vencidos = int((df["_status"] == "Vencido").sum())
    proximos = int((df["_status"] == "Próximo").sum())
    c1, c2, c3 = st.columns(3)
    _card(c1, total, "Total de itens", "cadastrados no TMOT", INK)
    _card(c2, vencidos, "Vencidos", "já passaram do limite", STATUS["critical"] if vencidos else STATUS["good"])
    _card(c3, proximos, "Próximos do vencimento",
          "≤100h / ≤50 pousos / ≤3 meses", AMBER if proximos else STATUS["good"])

    st.divider()
    abas = st.tabs([f"Por {t.lower()}" for t in TIPOS])
    for aba, tipo in zip(abas, TIPOS):
        with aba:
            _secao_tipo(df, tipo)


def _secao_tipo(df, tipo):
    sub = df[df["tipo_vencimento"] == tipo].copy()
    if sub.empty:
        st.caption("Nenhum item nessa categoria.")
        return

    unidade = UNIDADE_TIPO[tipo]
    minimo = int(sub["disponibilidade_valor"].min())
    maximo = int(sub["disponibilidade_valor"].max())

    faixa = st.slider(
        f"Faixa de disponibilidade ({unidade}) — negativo é vencido",
        min_value=minimo, max_value=maximo, value=(minimo, maximo),
        key=f"venc_slider_{tipo}",
    )
    filtrado = sub[sub["disponibilidade_valor"].between(faixa[0], faixa[1])]

    vencidos = int((filtrado["_status"] == "Vencido").sum())
    proximos = int((filtrado["_status"] == "Próximo").sum())
    st.caption(f"{len(filtrado)} item(ns) na faixa selecionada · {vencidos} vencido(s) · {proximos} próximo(s) do vencimento")

    if not filtrado.empty:
        fig = px.histogram(filtrado, x="disponibilidade_valor", nbins=30, color_discrete_sequence=[COR_TIPO[tipo]])
        fig.update_layout(xaxis_title=f"Disponibilidade ({unidade})", yaxis_title="Itens")
        fig.add_vline(x=0, line_dash="dash", line_color=SECONDARY)
        layout_grafico(fig, altura=200)
        st.plotly_chart(fig, width="stretch")

    if tipo == "Calendário":
        # Calendário: o dado que importa pro usuário é a data mesmo, não os
        # dias derivados (usados só internamente pro slider acima).
        colunas = ["matricula", "operador", "pn", "nomenclatura", "inspecao", "data_vencimento", "_status"]
    else:
        # Hora/Pouso: mostrar as duas informações juntas — quanto falta E a
        # data prevista de vencimento.
        colunas = ["matricula", "operador", "pn", "nomenclatura", "inspecao",
                   "disponibilidade_valor", "data_vencimento", "_status"]

    tabela = filtrado[colunas].rename(columns={
        "matricula": "Matrícula", "operador": "Operador", "pn": "PN", "nomenclatura": "Nomenclatura",
        "inspecao": "Inspeção", "disponibilidade_valor": f"Disponibilidade ({unidade})",
        "data_vencimento": "Data prevista", "_status": "Situação",
    }).sort_values("Data prevista")

    tabela = filtro_colunas(tabela, key_prefix=f"venc_{tipo}")
    st.caption(f"{len(tabela)} item(ns) após os filtros por coluna.")
    st.dataframe(tabela, hide_index=True, width="stretch")


def _secao_tipo_operadores(df, tipo, matriculas_contrato):
    sub = df[df["tipo_vencimento"] == tipo].copy()
    if sub.empty:
        st.caption("Nenhum item nessa categoria.")
        return

    unidade = UNIDADE_TIPO[tipo]
    minimo = int(sub["disponibilidade_valor"].min())
    maximo = int(sub["disponibilidade_valor"].max())

    c1, c2 = st.columns([2, 1])
    with c1:
        faixa = st.slider(
            f"Faixa de disponibilidade ({unidade}) — negativo é vencido",
            min_value=minimo, max_value=maximo, value=(minimo, maximo),
            key=f"venc_op_slider_{tipo}",
        )
    with c2:
        operadores = st.multiselect("Operador", sorted(sub["operador"].unique()), key=f"venc_op_filtro_{tipo}")

    aeronaves_disponiveis = sorted(sub["matricula"].astype(str).unique())
    padrao_aeronaves = [a for a in aeronaves_disponiveis if a in matriculas_contrato] or aeronaves_disponiveis
    situacoes_disponiveis = sorted(sub["_status"].unique())
    padrao_situacoes = [s for s in SITUACAO_PADRAO_OPERADORES if s in situacoes_disponiveis] or situacoes_disponiveis

    c3, c4, c5 = st.columns([1.4, 1.4, 1])
    with c3:
        aeronaves_f = st.multiselect(
            "Aeronave", aeronaves_disponiveis, default=padrao_aeronaves, key=f"venc_op_aeronave_{tipo}",
        )
    with c4:
        situacoes_f = st.multiselect(
            "Situação", situacoes_disponiveis, default=padrao_situacoes, key=f"venc_op_situacao_{tipo}",
        )
    with c5:
        ocultar_motor_helice = st.checkbox(
            "Ocultar motor/hélice", value=True, key=f"venc_op_ocultar_motor_{tipo}",
            help="Esconde por padrão itens de motor/hélice (Disk, Engine, Motor, Hub Compressor, "
                 "Impeller, Hélice, Kit HSI) — já cobertos pela página Motores. Desmarque pra ver todos.",
        )

    filtrado = sub[sub["disponibilidade_valor"].between(faixa[0], faixa[1])]
    if operadores:
        filtrado = filtrado[filtrado["operador"].isin(operadores)]
    if aeronaves_f:
        filtrado = filtrado[filtrado["matricula"].astype(str).isin(aeronaves_f)]
    if situacoes_f:
        filtrado = filtrado[filtrado["_status"].isin(situacoes_f)]
    if ocultar_motor_helice:
        filtrado = filtrado[~filtrado["nomenclatura"].apply(_nomenclatura_motor_helice)]

    vencidos = int((filtrado["_status"] == "Vencido").sum())
    proximos = int((filtrado["_status"] == "Próximo").sum())
    st.caption(f"{len(filtrado)} item(ns) na faixa selecionada · {vencidos} vencido(s) · {proximos} próximo(s) do vencimento")

    if not filtrado.empty:
        fig = px.histogram(filtrado, x="disponibilidade_valor", color="operador", nbins=30)
        fig.update_layout(xaxis_title=f"Disponibilidade ({unidade})", yaxis_title="Itens")
        fig.add_vline(x=0, line_dash="dash", line_color=SECONDARY)
        layout_grafico(fig, altura=220)
        st.plotly_chart(fig, width="stretch")

    if tipo == "Calendário":
        colunas = ["matricula", "operador", "especialidade", "nomenclatura", "pn",
                   "data_vencimento", "_status", "mes_fonte", "arquivo_fonte"]
    else:
        colunas = ["matricula", "operador", "especialidade", "nomenclatura", "pn",
                   "disponibilidade_valor", "data_vencimento", "_status", "mes_fonte", "arquivo_fonte"]

    tabela = filtrado[colunas].rename(columns={
        "matricula": "Matrícula", "operador": "Operador", "especialidade": "Especialidade",
        "nomenclatura": "Nomenclatura", "pn": "PN", "disponibilidade_valor": f"Disponibilidade ({unidade})",
        "data_vencimento": "Data prevista", "_status": "Situação",
        "mes_fonte": "Mês fonte", "arquivo_fonte": "Arquivo fonte",
    }).sort_values("Data prevista")

    tabela = filtro_colunas(tabela, key_prefix=f"venc_op_{tipo}")
    st.caption(f"{len(tabela)} item(ns) após os filtros por coluna.")
    st.dataframe(tabela, hide_index=True, width="stretch")
