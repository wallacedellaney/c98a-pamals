"""Tela "Emergências Totais" — todo o histórico de emergências (abertas e
concluídas) do provedor VEE ONE, sem o filtro de "em aberto" da tela
"Emergências Abertas". Ver 00_Instrucoes/emergencias.md."""

import pandas as pd
import plotly.express as px
import streamlit as st

from contrato005.components.paleta import CATEGORICA, layout_grafico
from contrato005.components.utils import ordenar_unicos

COLUNAS_TABELA = [
    "om_emg", "om", "numero_emergencia", "pn", "nomenclatura", "categoria",
    "matricula_aeronave", "situacao", "tpemg", "data_abertura", "data_info",
    "quantidade", "unidade_medida", "prazo_entrega", "dpe", "atendido_cancelado",
    "dias_atraso", "dias_corridos", "estoque", "retirado_empresa_recibo_obrigatorio",
    "obs_coordenadoria_fiscal", "obs_vee_one", "provedor", "awb", "prev_entrega",
    "mensagem_operador",
]
NOMES_COLUNAS = {
    "om_emg": "OM_EMG", "om": "OM", "numero_emergencia": "EMERGÊNCIA", "pn": "PN",
    "nomenclatura": "NOMENCLATURA", "categoria": "CAT", "matricula_aeronave": "MATR",
    "situacao": "ST_EMG", "tpemg": "TPEMG", "data_abertura": "DT_EMG", "data_info": "INFO EMG",
    "quantidade": "QT_EMG", "unidade_medida": "UE", "prazo_entrega": "PRAZO DE ENTREGA",
    "dpe": "DPE", "atendido_cancelado": "Atd/cancelada", "dias_atraso": "DIAS ATRASO",
    "dias_corridos": "DIAS CORRIDOS", "estoque": "Estoque",
    "retirado_empresa_recibo_obrigatorio": "Retirado pela empresa?/Obrigatório recibo",
    "obs_coordenadoria_fiscal": "OBSERVAÇÃO COORDENADORIA/FISCAL",
    "obs_vee_one": "OBSERVAÇÃO VEE ONE", "provedor": "Provedor", "awb": "AWB",
    "prev_entrega": "Prev Entrega", "mensagem_operador": "Mensagem para operador",
}

FILTRO_KEYS = [
    "et_f_pns", "et_f_aeronaves", "et_f_oms", "et_f_categorias", "et_f_situacoes",
    "et_f_tpemgs", "et_f_status", "et_f_data_de", "et_f_data_ate", "et_f_atrasadas",
]


def render(dados):
    st.title("Emergências Totais")
    st.caption(
        "Todo o histórico de emergências do provedor VEE ONE — abertas e concluídas, "
        "desde que o provedor passou a aparecer na planilha. Ver 00_Instrucoes/emergencias.md."
    )

    df = dados.get("emergencias_totais")
    if df is None or df.empty:
        st.info(
            "Ainda não foi gerado o histórico completo — rodar "
            "`extrair_historico_completo()` em `05_Scripts/python/extrair_emergencias.py`."
        )
        return

    atualizado_em = dados.get("emergencias_totais_atualizado_em")
    if atualizado_em:
        from shared import horario
        st.caption(f"Última extração: **{horario.fromtimestamp_br(atualizado_em).strftime('%d/%m/%Y %H:%M')}**")

    st.markdown("##### Busca e filtros")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        pns = st.multiselect("PN", ordenar_unicos(df["pn"]), key="et_f_pns")
    with c2:
        aeronaves = st.multiselect("Aeronave (MATR)", ordenar_unicos(df["matricula_aeronave"]), key="et_f_aeronaves")
    with c3:
        oms = st.multiselect("OM", ordenar_unicos(df["om"]), key="et_f_oms")
    with c4:
        status = st.selectbox("Situação geral", ["Todas", "Em aberto", "Concluídas"], key="et_f_status")

    with st.expander("Filtros avançados"):
        c5, c6, c7 = st.columns(3)
        with c5:
            categorias = st.multiselect("Categoria (CAT)", ordenar_unicos(df["categoria"]), key="et_f_categorias")
        with c6:
            situacoes = st.multiselect("Situação (ST_EMG)", ordenar_unicos(df["situacao"]), key="et_f_situacoes")
        with c7:
            tpemgs = st.multiselect("TPEMG", ordenar_unicos(df["tpemg"]), key="et_f_tpemgs")

        c8, c9, c10 = st.columns(3)
        with c8:
            data_de = st.date_input("Aberta a partir de", value=None, key="et_f_data_de")
        with c9:
            data_ate = st.date_input("Aberta até", value=None, key="et_f_data_ate")
        with c10:
            so_atrasadas = st.checkbox("Mostrar só atrasadas", key="et_f_atrasadas")

    if st.button("✕ Limpar filtros", key="et_limpar_filtros"):
        for k in FILTRO_KEYS:
            st.session_state.pop(k, None)
        st.rerun()

    filtrado = df.copy()
    if pns:
        filtrado = filtrado[filtrado["pn"].isin(pns)]
    if aeronaves:
        filtrado = filtrado[filtrado["matricula_aeronave"].isin(aeronaves)]
    if oms:
        filtrado = filtrado[filtrado["om"].isin(oms)]
    if status == "Em aberto":
        filtrado = filtrado[filtrado["em_aberto"]]
    elif status == "Concluídas":
        filtrado = filtrado[~filtrado["em_aberto"]]
    if categorias:
        filtrado = filtrado[filtrado["categoria"].isin(categorias)]
    if situacoes:
        filtrado = filtrado[filtrado["situacao"].isin(situacoes)]
    if tpemgs:
        filtrado = filtrado[filtrado["tpemg"].isin(tpemgs)]
    if data_de:
        filtrado = filtrado[filtrado["data_abertura"] >= pd.Timestamp(data_de)]
    if data_ate:
        filtrado = filtrado[filtrado["data_abertura"] <= pd.Timestamp(data_ate)]
    if so_atrasadas:
        filtrado = filtrado[filtrado["dias_atraso"] > 0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total (após filtro)", len(filtrado))
    c2.metric("Em aberto", int(filtrado["em_aberto"].sum()))
    c3.metric("Concluídas", int((~filtrado["em_aberto"]).sum()))
    media_atraso = filtrado.loc[filtrado["dias_atraso"] > 0, "dias_atraso"].mean()
    c4.metric("Atraso médio p/ atrasadas (dias)", f"{media_atraso:.1f}" if pd.notna(media_atraso) else "—")

    # No site da empresa (005CELOG2025), fica só estatística (cards +
    # gráficos abaixo) — sem acesso à planilha geral (linha a linha) nem
    # exportação. Pedido do Wallace em 2026-07-18: "emergencias totais
    # vamos deixar so estatistica no site da emprsea, sem acesso a
    # planilha geral, nem exportar". No site principal continua tudo.
    if not dados.get("modo_externo"):
        tabela = filtrado[COLUNAS_TABELA + ["em_aberto"]].copy()
        tabela["awb"] = tabela["awb"].apply(lambda v: str(v) if pd.notna(v) else v)
        tabela["em_aberto"] = tabela["em_aberto"].map({True: "Em aberto", False: "Concluída"})
        tabela = tabela.rename(columns={**NOMES_COLUNAS, "em_aberto": "Status"})
        st.dataframe(tabela, hide_index=True, width="stretch", height=460)

        csv = tabela.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Exportar (CSV)", csv, file_name="emergencias_totais.csv", mime="text/csv")

    with st.expander("Distribuição por situação"):
        por_situacao = filtrado["situacao"].value_counts().reset_index()
        por_situacao.columns = ["situacao", "quantidade"]
        fig = px.bar(por_situacao, x="situacao", y="quantidade", color_discrete_sequence=[CATEGORICA[0]])
        fig.update_layout(xaxis_title="", yaxis_title="Quantidade", showlegend=False)
        layout_grafico(fig)
        st.plotly_chart(fig, width="stretch")

    with st.expander("Emergências por mês (data de abertura)"):
        por_mes = filtrado.dropna(subset=["data_abertura"]).copy()
        por_mes["mes"] = pd.to_datetime(por_mes["data_abertura"]).dt.to_period("M").astype(str)
        contagem = por_mes.groupby("mes").size().reset_index(name="quantidade").sort_values("mes")
        fig = px.bar(contagem, x="mes", y="quantidade", color_discrete_sequence=[CATEGORICA[1]])
        fig.update_layout(xaxis_title="", yaxis_title="Quantidade", showlegend=False)
        layout_grafico(fig)
        st.plotly_chart(fig, width="stretch")
