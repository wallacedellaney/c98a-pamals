"""Página Fechamento Mensal — seletor de mês + 2 subseções: "Cômputo
Mensal" (feito, ver 00_Instrucoes/computo_mensal.md) e "Atrasos" (ainda não
definido — não presumir métricas sem perguntar ao Wallace, ver CLAUDE.md).
"""

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from contrato005.components.paleta import AMBER, LINE, STATUS, layout_grafico

ABREV_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

SCRIPTS_PYTHON = Path(__file__).resolve().parents[3] / "05_Scripts" / "python"
if str(SCRIPTS_PYTHON) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PYTHON))

from contrato005.data.carregar_dados import carregar_computo_mensal

MESES_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def _opcoes_mes(dados):
    """Todos os meses (ano-mês) presentes no histórico de emergências,
    começando por julho/2026 — se não houver dado ainda, usa só julho/2026."""
    df = dados.get("emergencias_totais")
    padrao = pd.Period("2026-07", freq="M")
    if df is None or df.empty or "data_abertura" not in df.columns:
        return [padrao]
    periodos = pd.to_datetime(df["data_abertura"].dropna()).dt.to_period("M").unique()
    meses = sorted(set(periodos) | {padrao})
    return meses


def _formatar_mes(periodo):
    return f"{MESES_PT[periodo.month - 1]}/{periodo.year}"


def render(dados):
    st.title("Fechamento Mensal")
    st.caption("Fechamento mensal do Contrato 005 — cômputo do mês e atrasos.")

    opcoes = _opcoes_mes(dados)
    padrao = pd.Period("2026-07", freq="M")
    indice_padrao = opcoes.index(padrao) if padrao in opcoes else len(opcoes) - 1

    mes_escolhido = st.selectbox(
        "Mês de referência",
        options=opcoes,
        index=indice_padrao,
        format_func=_formatar_mes,
        key="fecham_mes",
    )

    st.divider()
    aba_computo, aba_atrasos = st.tabs(["Cômputo Mensal", "Atrasos"])

    with aba_computo:
        _computo_mensal(mes_escolhido)

    with aba_atrasos:
        st.subheader(f"Atrasos — {_formatar_mes(mes_escolhido)}")
        st.info("Ainda não construído — aguardando instruções do Wallace sobre o que exibir aqui.")


def _computo_mensal(mes_escolhido):
    st.subheader(f"Cômputo Mensal — {_formatar_mes(mes_escolhido)}")
    st.caption(
        "Prévia calculada automaticamente a partir dos registros de emergências AIFP/IPLR sem estoque "
        "(ver 00_Instrucoes/computo_mensal.md) — não substitui a Pré-RNA oficial, é uma conferência."
    )

    col_calc, _ = st.columns([1, 3])
    with col_calc:
        if st.button("🔄 Recalcular", key="computo_recalcular", width="stretch"):
            with st.spinner("Recalculando a partir das emergências..."):
                import calcular_computo_mensal
                calcular_computo_mensal.calcular_mes(mes_escolhido.year, mes_escolhido.month)
            st.rerun()

    df_matriz, df_motivos, resumo = carregar_computo_mensal(mes_escolhido.year, mes_escolhido.month)
    if df_matriz is None:
        st.info("Ainda não foi calculado pra este mês — clique em \"Recalcular\".")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("MMAM prévia", f"{resumo['mmam_previa']}%" if resumo["mmam_previa"] is not None else "—")
    c2.metric("Aeronaves pontuadas", len(resumo["aeronaves_pontuadas"]))
    c3.metric("Dias já decorridos", f"{resumo['ultimo_dia_calculado']} de {resumo.get('ultimo_dia_mes', resumo['ultimo_dia_calculado'])}")

    if resumo["inconsistencias"]:
        with st.expander(f"⚠️ {len(resumo['inconsistencias'])} inconsistência(s) — revisar manualmente", expanded=True):
            for i in resumo["inconsistencias"]:
                st.markdown(f"- {i}")

    st.markdown("##### Evolução da % de aeronaves montadas no mês")
    media_diaria = df_matriz.dropna(subset=["montada"]).groupby("dia")["montada"].mean().mul(100).reset_index()
    fig = px.line(media_diaria, x="dia", y="montada", markers=True, color_discrete_sequence=[AMBER])
    fig.update_layout(
        yaxis_title="% montadas", xaxis_title="Dia do mês", yaxis_range=[0, 105],
        xaxis_range=[0.5, resumo.get("ultimo_dia_mes", media_diaria["dia"].max()) + 0.5],
    )
    layout_grafico(fig, altura=220)
    st.plotly_chart(fig, width="stretch")

    st.markdown("##### Matriz aeronave x dia (1 = montada, 0 = desmontada) — mês inteiro, sáb/dom marcados em cinza")
    pivot = df_matriz.pivot(index="matricula", columns="dia", values="montada")

    mapa_rotulo = {}
    fins_de_semana = set()
    for dia in pivot.columns:
        wd = date(mes_escolhido.year, mes_escolhido.month, int(dia)).weekday()
        rotulo = f"{dia} {ABREV_SEMANA[wd]}"
        mapa_rotulo[dia] = rotulo
        if wd >= 5:
            fins_de_semana.add(rotulo)
    pivot = pivot.rename(columns=mapa_rotulo)

    def _cor_fabrica(coluna):
        def _colorir(v):
            if pd.isna(v):
                return f"background-color: {LINE}" if coluna in fins_de_semana else ""
            cor = STATUS["good"] if v == 1 else STATUS["critical"]
            return f"background-color: {cor}55"
        return _colorir

    styler = pivot.style
    for coluna in pivot.columns:
        styler = styler.map(_cor_fabrica(coluna), subset=[coluna])

    st.dataframe(styler, width="stretch", height=460)

    if resumo["aeronaves_fora_listadas"]:
        st.caption(
            "Fora do contrato (listadas, sem pontuação): "
            + ", ".join(f"FAB {m}" for m in resumo["aeronaves_fora_listadas"])
        )

    st.markdown("##### Justificativa das negativações")
    if df_motivos.empty:
        st.success("Nenhuma negativação no período — todas as aeronaves pontuadas ficaram montadas.")
    else:
        tabela = df_motivos.rename(columns={
            "matricula": "Matrícula", "numero_emergencia": "Emergência", "tipo": "Tipo",
            "data_abertura": "Data abertura", "data_info": "Data informação", "estoque": "Estoque",
            "inicio_negativacao": "Início negativação", "data_cancelamento": "Cancelamento/conclusão",
            "periodo_no_mes_inicio": "Negativado de", "periodo_no_mes_fim": "Negativado até",
        }).fillna("ainda aberto")
        st.dataframe(tabela, hide_index=True, width="stretch")

    csv = df_matriz.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar matriz (CSV)", csv,
                        file_name=f"computo_mensal_{mes_escolhido}.csv", mime="text/csv")
