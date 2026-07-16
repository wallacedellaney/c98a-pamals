"""Tela "Reajuste" — valor do contrato, saldo por módulo e cronograma
físico financeiro, a partir da "Planilha Demonstrativa -2_Reajuste -
Contrato 005_CELOG-PAMALS_2025" do Wallace. Pedido do Wallace em
2026-07-16: "colcoa essa informcao no contrato pra saber o valor ... cria
uma aba chamada reajuste onde tem todas essas infomacoes ai dessa
planilha". Ver 00_Instrucoes/reajuste.md.
"""

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from contrato005.components.paleta import AMBER, CATEGORICA, CYAN, INK, LINE, PANEL, SECONDARY, STATUS, layout_grafico


def _fmt_moeda(valor):
    if valor is None or pd.isna(valor):
        return "—"
    return f"R$ {valor:,.2f}"


def _indicador(df, rotulo, ocorrencia=1):
    """Pega o valor da N-ésima ocorrência de um rótulo em "indicadores" (a
    planilha repete alguns rótulos em seções diferentes, ex. "Saldo do
    Módulo 1 até 08/10/25" e "... até 08/10/26" têm o MESMO texto base em
    momentos diferentes só quando o rótulo é idêntico — na prática cada
    rótulo real da planilha já é único por seção, mas isso protege contra
    qualquer repetição)."""
    achados = df[df["indicador"] == rotulo]
    if achados.empty or len(achados) < ocorrencia:
        return None
    return achados.iloc[ocorrencia - 1]["valor"]


def render(dados):
    st.title("Reajuste")
    st.caption(
        "Valor do Contrato 005/CELOG-PAMALS/2025, saldo por módulo e cronograma físico financeiro — "
        "fonte: Planilha Demonstrativa -2_Reajuste- (Drive, pessoal do Wallace)."
    )

    ind = dados.get("reajuste_indicadores")
    if ind is None or ind.empty:
        st.info(
            "Nenhum dado de Reajuste carregado ainda. Peça ao Claude para buscar a "
            "\"Planilha Demonstrativa -2_Reajuste-\" no Drive."
        )
        return

    if dados.get("reajuste_atualizado_em"):
        atualizado = datetime.fromtimestamp(dados["reajuste_atualizado_em"]).strftime("%d/%m/%Y %H:%M")
        st.caption(f"Última atualização dos dados: **{atualizado}**")

    # --- Valor do contrato: assinatura -> 1° Reajuste -> 2° Reajuste (atual) ---
    st.markdown("##### Valor do Contrato")
    v_assinatura = _indicador(ind, "Assinatura do Contrato( Valor total)")
    v_1_reajuste = _indicador(ind, "Valor do Contrato após 1° Reajuste")
    v_2_reajuste = _indicador(ind, "Valor do Contrato após 2° Reajuste")

    c1, c2, c3 = st.columns(3)
    c1.metric("Assinatura do contrato", _fmt_moeda(v_assinatura))
    c2.metric("Após 1° Reajuste", _fmt_moeda(v_1_reajuste),
              delta=_fmt_moeda(v_1_reajuste - v_assinatura) if v_1_reajuste and v_assinatura else None)
    c3.metric("Após 2° Reajuste (projeção)", _fmt_moeda(v_2_reajuste))
    st.caption(
        "⚠️ O 2° Reajuste só acontece de fato em outubro (aniversário anual do contrato, "
        "confirmado pelo Wallace) — até lá, o índice fica em 0% e os valores acima são só a "
        "execução rolada pra frente com o mesmo saldo do 1° Reajuste, não um valor final novo."
    )

    st.divider()

    # --- Saldo por módulo, nas 3 fases ---
    st.markdown("##### Saldo por módulo")
    fases = [
        ("Assinatura", ["Módulo 1", "Módulo 2", "Módulo 3"], 1),
        ("Saldo até 08/10/25 (antes do 1° Reajuste)",
         ["Saldo do Módulo 1 até 08/10/25", "Saldo do Módulo 2 até 08/10/25", "Saldo do Módulo 3 até 08/10/25"], 1),
        ("Saldo após 1° Reajuste",
         ["Saldo do Módulo 1 após 1° Reajuste", "Saldo do Módulo 2 após 1° Reajuste", "Saldo do Módulo 3 após 1° Reajuste"], 1),
        ("Saldo até 08/10/26 (antes do 2° Reajuste)",
         ["Saldo do Módulo 1 até 08/10/26", "Saldo do Módulo 2 até 08/10/26", "Saldo do Módulo 3 até 08/10/26"], 1),
        ("Saldo após 2° Reajuste (projeção)",
         ["Saldo do Módulo 1 após 2° Reajuste", "Saldo do Módulo 2 após 2° Reajuste", "Saldo do Módulo 3 após 2° Reajuste"], 1),
    ]
    linhas_saldo = []
    for nome_fase, rotulos, ocorrencia in fases:
        linha = {"Fase": nome_fase}
        for i, rotulo in enumerate(rotulos, start=1):
            linha[f"Módulo {i}"] = _indicador(ind, rotulo, ocorrencia)
        linhas_saldo.append(linha)
    tabela_saldo = pd.DataFrame(linhas_saldo)
    for col in ["Módulo 1", "Módulo 2", "Módulo 3"]:
        tabela_saldo[col] = tabela_saldo[col].apply(_fmt_moeda)
    st.dataframe(tabela_saldo, hide_index=True, width="stretch")

    st.divider()

    # --- Detalhamento de cada reajuste ---
    aba1, aba2 = st.tabs(["1° Reajuste (aplicado)", "2° Reajuste (projeção)"])
    with aba1:
        _detalhe_reajuste(ind, ocorrencia=1)
    with aba2:
        _detalhe_reajuste(ind, ocorrencia=2)

    st.divider()

    # --- Notas fiscais ---
    st.markdown("##### Notas fiscais consideradas")
    nf = dados.get("reajuste_notas_fiscais")
    if nf is None or nf.empty:
        st.caption("Sem notas fiscais carregadas.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            periodo_f = st.multiselect("Período", sorted(nf["periodo"].unique()), key="reajuste_f_periodo")
        with c2:
            modulo_f = st.multiselect("Módulo", sorted(nf["modulo"].dropna().unique()), key="reajuste_f_modulo")
        filtrado = nf.copy()
        if periodo_f:
            filtrado = filtrado[filtrado["periodo"].isin(periodo_f)]
        if modulo_f:
            filtrado = filtrado[filtrado["modulo"].isin(modulo_f)]

        tabela_nf = filtrado[[
            "periodo", "nota_fiscal", "valor_total_nf", "descricao_nf", "modulo",
            "orcamento", "autorizacao", "aprovacao", "emissao_nf", "vencimento_nf",
        ]].rename(columns={
            "periodo": "Período", "nota_fiscal": "Nota Fiscal", "valor_total_nf": "Valor Total",
            "descricao_nf": "Descrição", "modulo": "Módulo", "orcamento": "Orçamento",
            "autorizacao": "Autorização", "aprovacao": "Aprovação/Reunião mensal",
            "emissao_nf": "Emissão NF", "vencimento_nf": "Vencimento NF",
        })
        st.caption(f"{len(tabela_nf)} nota(s) fiscal(is) — total {_fmt_moeda(filtrado['valor_total_nf'].sum())}")
        st.dataframe(tabela_nf, hide_index=True, width="stretch")

    st.divider()

    # --- Cronograma físico financeiro ---
    st.markdown("##### Cronograma físico financeiro")
    cron = dados.get("reajuste_cronograma_mensal")
    if cron is None or cron.empty:
        st.caption("Sem cronograma carregado.")
    else:
        cron = cron.copy()
        cron["mes"] = pd.to_datetime(cron["mes"])
        longo = cron.melt(
            id_vars=["mes", "apos_1_reajuste"], value_vars=["modulo_1", "modulo_2", "modulo_3"],
            var_name="modulo", value_name="valor",
        )
        longo["modulo"] = longo["modulo"].replace({
            "modulo_1": "Módulo 1", "modulo_2": "Módulo 2", "modulo_3": "Módulo 3",
        })
        fig = px.bar(
            longo, x="mes", y="valor", color="modulo", color_discrete_sequence=CATEGORICA,
            labels={"modulo": "Módulo", "valor": "Valor (R$)", "mes": ""},
        )
        fig.add_vline(
            x=pd.Timestamp(2025, 10, 1), line_dash="dash", line_color=SECONDARY,
            annotation_text="1° Reajuste", annotation_position="top",
        )
        fig.update_layout(barmode="stack")
        layout_grafico(fig, altura=280)
        st.plotly_chart(fig, width="stretch")
        st.caption(
            "Cronograma projetado até 2029 pela própria planilha (mantém os valores mensais atuais "
            "de cada módulo constantes pra frente) — não é um novo reajuste previsto, só a projeção "
            "financeira linear que a planilha do Wallace já traz."
        )

        with st.expander("Ver tabela mensal completa"):
            tabela_cron = longo.pivot_table(index="mes", columns="modulo", values="valor").reset_index()
            tabela_cron["mes"] = tabela_cron["mes"].dt.strftime("%m/%Y")
            for col in ["Módulo 1", "Módulo 2", "Módulo 3"]:
                if col in tabela_cron.columns:
                    tabela_cron[col] = tabela_cron[col].apply(_fmt_moeda)
            st.dataframe(tabela_cron.rename(columns={"mes": "Mês"}), hide_index=True, width="stretch")

    resumo = dados.get("reajuste_cronograma_resumo")
    if resumo is not None and not resumo.empty:
        with st.expander("Resumo — Proposta Comercial x Executado x Reajustado"):
            tabela_resumo = resumo.copy()
            # As 2 últimas linhas da fonte trazem o TOTAL (não Módulo 3) na
            # coluna "modulo_3" — erro de posição na planilha original (o
            # Wallace colocou o valor 1 coluna à direita nessas 2 linhas
            # específicas); mostrado como "Total" pra não confundir com
            # Módulo 3 de verdade.
            totais = tabela_resumo["descricao"].str.startswith("Valor total")
            tabela_resumo.loc[totais, "modulo_1"] = None
            tabela_resumo.loc[totais, "modulo_2"] = None
            tabela_resumo = tabela_resumo.rename(columns={
                "descricao": "Descrição", "modulo_1": "Módulo 1", "modulo_2": "Módulo 2", "modulo_3": "Módulo 3/Total",
            })
            for col in ["Módulo 1", "Módulo 2", "Módulo 3/Total"]:
                tabela_resumo[col] = tabela_resumo[col].apply(_fmt_moeda)
            st.dataframe(tabela_resumo, hide_index=True, width="stretch")


def _detalhe_reajuste(ind, ocorrencia):
    ordinal = "1°" if ocorrencia == 1 else "2°"
    ipca_anterior = _indicador(ind, "Índice IPCA em Out/2024", ocorrencia)
    ipca_atual = _indicador(ind, "Índice IPCA em Out/2025", ocorrencia)
    indice = _indicador(ind, "Índice do 1° Reajuste Subprocesso 43898", ocorrencia)
    sup1 = _indicador(ind, "Suplemento Contratual Módulo 1", ocorrencia)
    sup2 = _indicador(ind, "Suplemento Contratual Módulo 2", ocorrencia)
    sup3 = _indicador(ind, "Suplemento Contratual Módulo 3", ocorrencia)
    sup_total = _indicador(ind, "Suplemento Contratual total", ocorrencia)
    valor_hv = _indicador(ind, "Valor da hora de voo", ocorrencia)
    sup_hv = _indicador(ind, "Suplemento hora de voo", ocorrencia)
    # Este rótulo já traz o número do reajuste no próprio texto ("após 1°"/
    # "após 2°"), então só existe 1 ocorrência de cada — sempre buscar a 1ª.
    valor_hv_pos = _indicador(ind, f"Valor da hora de voo após {ordinal} Reajuste", 1)

    c1, c2, c3 = st.columns(3)
    c1.metric("Índice IPCA (ano anterior)", f"{ipca_anterior:,.2f}" if ipca_anterior else "—")
    c2.metric("Índice IPCA (ano atual)", f"{ipca_atual:,.2f}" if ipca_atual else "—")
    c3.metric(f"Índice do {ordinal} Reajuste", f"{indice * 100:.2f}%" if indice is not None else "—")

    c4, c5, c6, c7 = st.columns(4)
    c4.metric("Suplemento Módulo 1", _fmt_moeda(sup1))
    c5.metric("Suplemento Módulo 2", _fmt_moeda(sup2))
    c6.metric("Suplemento Módulo 3", _fmt_moeda(sup3))
    c7.metric("Suplemento total", _fmt_moeda(sup_total))

    c8, c9, c10 = st.columns(3)
    c8.metric("Valor da hora de voo (antes)", _fmt_moeda(valor_hv))
    c9.metric("Suplemento hora de voo", _fmt_moeda(sup_hv))
    c10.metric(f"Valor da hora de voo após {ordinal} Reajuste", _fmt_moeda(valor_hv_pos))
