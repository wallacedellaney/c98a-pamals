"""
Página RAC — situação das aeronaves e materiais faltantes (dashboard
institucional, não uma cópia da planilha).

Regras (ver 00_Instrucoes/rac.md):
* Aeronaves DENTRO do contrato mostram a lista detalhada de pendências;
  aeronaves FORA do contrato mostram só o quantitativo total.
* Aeronaves "Sem condições" nunca entram no grupo "sem pendências"/regulares,
  mesmo com total_pendencias = 0 — ficam sempre na área de prioridade.
* Sem "% de completude" — usamos faixas/contagens (sem base de cálculo confiável).
"""

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from coordenadoria.components.paleta import STATUS, AMBER, CYAN, SECONDARY, PANEL, LINE, INK, layout_grafico
from coordenadoria.utils import atualizar_dados_rac, RAC_PLANILHA_URL

ICONE_DISPONIBILIDADE = {"Montada": "✅", "Desmontada": "🛠️", "Sem condições": "⛔"}
COR_MD_DISPONIBILIDADE = {"Montada": "green", "Desmontada": "orange", "Sem condições": "red"}

FILTRO_KEYS = [
    "rac_f_matriculas", "rac_f_unidades", "rac_f_situacao", "rac_f_busca",
    "rac_f_pns", "rac_f_nomenclaturas", "rac_f_contrato", "rac_f_pendencia",
]


def render(dados):
    if st.session_state.get("rac_aeronave_selecionada"):
        _detalhe_aeronave(dados, st.session_state["rac_aeronave_selecionada"])
        return

    _estilo_rac()

    aeronaves = dados["rac_aeronaves"]
    pendencias = dados["rac_pendencias"]

    _cabecalho(dados)
    _cards_indicadores(aeronaves, pendencias)
    _graficos_analiticos(aeronaves, pendencias)
    _pontos_atencao(aeronaves, pendencias)

    st.divider()
    filtros = _busca_e_filtros(aeronaves, pendencias)
    aeronaves_f, pendencias_f = _aplicar_filtros(aeronaves, pendencias, filtros)

    aba_aeronaves, aba_materiais, aba_matriz = st.tabs(["Aeronaves", "Materiais críticos", "Matriz RAC"])
    with aba_aeronaves:
        _aba_aeronaves(aeronaves_f, pendencias_f)
    with aba_materiais:
        _materiais_criticos(pendencias_f)
    with aba_matriz:
        _matriz(aeronaves_f, pendencias_f)


def _estilo_rac():
    st.markdown(
        f"""
        <style>
        .indicador-card {{
            background: {PANEL};
            border: 1px solid {LINE};
            border-radius: 10px;
            padding: 0.9rem 1rem;
            box-shadow: 0 2px 6px rgba(0,0,0,0.25);
        }}
        .indicador-topo {{ display: flex; align-items: center; justify-content: space-between; }}
        .indicador-icone {{ font-size: 1.5rem; opacity: 0.85; }}
        .indicador-valor {{ font-size: 2.4rem; font-weight: 800; }}
        .indicador-label {{ font-size: 1.15rem; color: {INK}; margin-top: 0.4rem; font-weight: 700; }}
        .indicador-sub {{ font-size: 1rem; color: {SECONDARY}; margin-top: 0.15rem; }}

        .painel-atencao {{
            background: {PANEL};
            border: 1px solid {LINE};
            border-left: 3px solid {AMBER};
            border-radius: 10px;
            padding: 0.7rem 1.1rem;
        }}
        .item-atencao {{
            padding: 0.55rem 0;
            border-bottom: 1px solid {LINE};
            font-size: 1rem;
        }}
        .item-atencao:last-child {{ border-bottom: none; }}

        .st-key-rac_cards div.stButton > button {{
            text-align: left;
            white-space: pre-line;
            line-height: 1.6;
            border-radius: 10px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
            height: auto;
            font-size: 1.05rem;
            padding: 0.9rem 1.1rem;
        }}
        .st-key-rac_cards div.stButton > button p {{
            font-size: 1.05rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _cabecalho(dados):
    st.title("RAC — Análise Crítica de Emergências C-98")
    st.caption("Acompanhamento da situação das aeronaves e dos itens faltantes para composição da configuração prevista.")

    atualizado = datetime.fromtimestamp(dados["atualizado_em"]).strftime("%d/%m/%Y %H:%M")
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    with col1:
        st.caption(f"Última atualização: **{atualizado}** · Arquivo: `base_rac_tratada.xlsx`")
    with col2:
        if st.button("🔄 Atualizar dados", key="rac_atualizar", width="stretch"):
            with st.spinner("Atualizando..."):
                atualizar_dados_rac()
            st.rerun()
    with col3:
        csv = dados["rac_pendencias"].to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Exportar relatório", csv, file_name="rac_pendencias.csv",
                            mime="text/csv", width="stretch")
    with col4:
        st.link_button("🔗 Planilha original", RAC_PLANILHA_URL, width="stretch")


def _card_indicador(col, icone, valor, label, sub, cor):
    with col:
        st.markdown(
            f'<div class="indicador-card">'
            f'<div class="indicador-topo">'
            f'<span class="indicador-icone">{icone}</span>'
            f'<span class="indicador-valor" style="color:{cor};">{valor}</span>'
            f"</div>"
            f'<div class="indicador-label">{label}</div>'
            f'<div class="indicador-sub">{sub}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )


def _cards_indicadores(aeronaves, pendencias):
    total = len(aeronaves)
    montadas = int((aeronaves["disponibilidade"] == "Montada").sum())
    desmontadas = int((aeronaves["disponibilidade"] == "Desmontada").sum())
    sem_condicoes = int((aeronaves["disponibilidade"] == "Sem condições").sum())
    dentro = int((aeronaves["contrato"] == "Dentro do contrato").sum())
    fora = int((aeronaves["contrato"] == "Fora do contrato").sum())
    pns_distintos = int(pendencias["pn"].nunique())
    total_unidades = int(aeronaves["soma_unidades_faltantes"].sum())

    pct = lambda n: round(100 * n / total) if total else 0

    l1 = st.columns(4)
    _card_indicador(l1[0], "🛩️", total, "Total de aeronaves", "frota completa", INK)
    _card_indicador(l1[1], "✅", montadas, "Montadas", f"{pct(montadas)}% da frota", STATUS["good"])
    _card_indicador(l1[2], "🛠️", desmontadas, "Desmontadas", "com pendência de material", AMBER)
    _card_indicador(l1[3], "⛔", sem_condicoes, "Sem condições", "fora de operação", STATUS["critical"])

    l2 = st.columns(4)
    _card_indicador(l2[0], "📄", dentro, "Dentro do contrato", f"{pct(dentro)}% da frota", CYAN)
    _card_indicador(l2[1], "🚫", fora, "Fora do contrato", f"{pct(fora)}% da frota",
                     STATUS["critical"] if fora else SECONDARY)
    _card_indicador(l2[2], "🔩", pns_distintos, "PNs distintos faltantes", "itens diferentes", SECONDARY)
    _card_indicador(l2[3], "📦", total_unidades, "Unidades faltantes", "no total",
                     AMBER if total_unidades else STATUS["good"])


def _graficos_analiticos(aeronaves, pendencias):
    st.write("")
    st.markdown("##### Visão analítica")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.caption("Situação da frota")
        contagem = (
            aeronaves["disponibilidade"].value_counts()
            .reindex(["Montada", "Desmontada", "Sem condições"]).fillna(0).reset_index()
        )
        contagem.columns = ["situacao", "quantidade"]
        fig = px.pie(
            contagem, names="situacao", values="quantidade", hole=0.55,
            color="situacao",
            color_discrete_map={"Montada": STATUS["good"], "Desmontada": AMBER, "Sem condições": STATUS["critical"]},
        )
        fig.update_traces(textinfo="value+percent", textfont_size=11)
        layout_grafico(fig, altura=230)
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.caption("Aeronaves com mais pendências")
        metrica = st.radio("Métrica", ["PNs distintos", "Unidades faltantes"], horizontal=True,
                            key="rac_metrica_top_aeronaves", label_visibility="collapsed")
        campo = "total_pendencias" if metrica == "PNs distintos" else "soma_unidades_faltantes"
        top = aeronaves[aeronaves[campo] > 0].sort_values(campo, ascending=False).head(8)
        if top.empty:
            st.caption("Nenhuma pendência no momento.")
        else:
            fig = px.bar(top, x=campo, y="matricula", orientation="h", color_discrete_sequence=[AMBER])
            fig.update_layout(yaxis_title="", xaxis_title="", yaxis={"categoryorder": "total ascending", "type": "category"})
            layout_grafico(fig, altura=230)
            st.plotly_chart(fig, width="stretch")

    with col3:
        st.caption("PNs mais críticos")
        if pendencias.empty:
            st.caption("Sem pendências no momento.")
        else:
            top_pn = (
                pendencias.groupby(["pn", "nomenclatura"])["matricula"].nunique()
                .sort_values(ascending=False).head(8).reset_index()
            )
            top_pn.columns = ["pn", "nomenclatura", "aeronaves_afetadas"]
            fig = px.bar(top_pn, x="aeronaves_afetadas", y="pn", orientation="h",
                         color_discrete_sequence=[CYAN])
            fig.update_layout(yaxis_title="", xaxis_title="", yaxis={"categoryorder": "total ascending", "type": "category"})
            layout_grafico(fig, altura=230)
            st.plotly_chart(fig, width="stretch")


def _pontos_atencao(aeronaves, pendencias):
    st.write("")
    st.markdown("##### Pontos de atenção")
    itens = []

    sem_condicoes = aeronaves[aeronaves["disponibilidade"] == "Sem condições"]
    if len(sem_condicoes):
        matriculas = ", ".join(f"FAB {m}" for m in sem_condicoes["matricula"])
        itens.append(f"⛔ {len(sem_condicoes)} aeronave(s) sem condições: {matriculas}.")

    top_aer = aeronaves.sort_values("soma_unidades_faltantes", ascending=False).head(3)
    for _, row in top_aer.iterrows():
        if row["soma_unidades_faltantes"] > 0:
            itens.append(
                f"🛠️ FAB {row['matricula']} possui {int(row['soma_unidades_faltantes'])} unidades "
                f"faltantes ({int(row['total_pendencias'])} PNs)."
            )

    if not pendencias.empty:
        top_pn = pendencias.groupby(["pn", "nomenclatura"])["matricula"].nunique().sort_values(ascending=False)
        if len(top_pn) and top_pn.iloc[0] > 1:
            pn, nome = top_pn.index[0]
            itens.append(f"🔩 PN {pn} ({nome}) afeta {top_pn.iloc[0]} aeronaves.")

    fora_operacionais = aeronaves[
        (aeronaves["contrato"] == "Fora do contrato") & (aeronaves["disponibilidade"] != "Sem condições")
    ]
    if len(fora_operacionais):
        itens.append(f"🚫 {len(fora_operacionais)} aeronave(s) montadas/desmontadas estão fora do contrato.")

    if not itens:
        st.markdown(
            '<div class="painel-atencao"><div class="item-atencao">✅ Nenhum ponto de atenção — frota regular.</div></div>',
            unsafe_allow_html=True,
        )
        return

    html = "".join(f'<div class="item-atencao">{item}</div>' for item in itens)
    st.markdown(f'<div class="painel-atencao">{html}</div>', unsafe_allow_html=True)


def _busca_e_filtros(aeronaves, pendencias):
    st.write("")
    st.markdown("##### Busca e filtros")
    c1, c2, c3, c4 = st.columns([1, 1, 1, 1.4])
    with c1:
        matriculas = st.multiselect("Matrícula", sorted(aeronaves["matricula"].unique()), key="rac_f_matriculas")
    with c2:
        unidades = st.multiselect("Unidade", sorted(aeronaves["unidade"].dropna().unique()), key="rac_f_unidades")
    with c3:
        situacao = st.multiselect("Situação", sorted(aeronaves["disponibilidade"].unique()), key="rac_f_situacao")
    with c4:
        busca = st.text_input("🔎 Busca geral (matrícula, PN ou nomenclatura)", key="rac_f_busca")

    with st.expander("Filtros avançados"):
        c5, c6, c7, c8 = st.columns(4)
        with c5:
            pns = st.multiselect("PN", sorted(pendencias["pn"].unique()), key="rac_f_pns")
        with c6:
            nomenclaturas = st.multiselect("Nomenclatura", sorted(pendencias["nomenclatura"].dropna().unique()),
                                            key="rac_f_nomenclaturas")
        with c7:
            contrato = st.multiselect("Vínculo contratual", sorted(aeronaves["contrato"].unique()),
                                       key="rac_f_contrato")
        with c8:
            pendencia_sn = st.selectbox("Pendência", ["Todas", "Com pendência", "Sem pendência"],
                                         key="rac_f_pendencia")

    st.write("")
    if st.button("✕ Limpar filtros", key="rac_limpar_filtros"):
        for k in FILTRO_KEYS:
            st.session_state.pop(k, None)
        st.rerun()

    return dict(matriculas=matriculas, unidades=unidades, situacao=situacao, busca=busca,
                pns=pns, nomenclaturas=nomenclaturas, contrato=contrato, pendencia=pendencia_sn)


def _aplicar_filtros(aeronaves, pendencias, f):
    aer = aeronaves.copy()
    if f["matriculas"]:
        aer = aer[aer["matricula"].isin(f["matriculas"])]
    if f["unidades"]:
        aer = aer[aer["unidade"].isin(f["unidades"])]
    if f["situacao"]:
        aer = aer[aer["disponibilidade"].isin(f["situacao"])]
    if f["contrato"]:
        aer = aer[aer["contrato"].isin(f["contrato"])]
    if f["pendencia"] == "Com pendência":
        aer = aer[aer["total_pendencias"] > 0]
    elif f["pendencia"] == "Sem pendência":
        aer = aer[aer["total_pendencias"] == 0]

    pend = pendencias[pendencias["matricula"].isin(aer["matricula"])].copy()

    if f["pns"]:
        pend = pend[pend["pn"].isin(f["pns"])]
        aer = aer[aer["matricula"].isin(pend["matricula"])]
    if f["nomenclaturas"]:
        pend = pend[pend["nomenclatura"].isin(f["nomenclaturas"])]
        aer = aer[aer["matricula"].isin(pend["matricula"])]
    if f["busca"]:
        b = f["busca"].strip().lower()
        pend_match = pend[
            pend["pn"].astype(str).str.lower().str.contains(b)
            | pend["nomenclatura"].astype(str).str.lower().str.contains(b, na=False)
        ]
        aer_match_direto = aer["matricula"].astype(str).str.lower().str.contains(b)
        aer = aer[aer_match_direto | aer["matricula"].isin(pend_match["matricula"])]
        pend = pend[pend["matricula"].isin(aer["matricula"])]

    return aer, pend


def _card_aeronave(row, pendencias):
    disponibilidade = row["disponibilidade"]
    fora = row["contrato"] == "Fora do contrato"
    icone = ICONE_DISPONIBILIDADE.get(disponibilidade, "•")
    cor_md = COR_MD_DISPONIBILIDADE.get(disponibilidade, "gray")
    contrato_txt = "Fora do contrato" if fora else "Dentro do contrato"

    principal = ""
    if row["total_pendencias"] > 0 and not fora:
        pend_aer = pendencias[pendencias["matricula"] == row["matricula"]]
        if not pend_aer.empty:
            principal_row = pend_aer.sort_values("quantidade_faltante", ascending=False).iloc[0]
            principal = f"Principal: {principal_row['nomenclatura']}"

    linhas = [
        f"**FAB {row['matricula']}**",
        f"{row['unidade'] or '—'}",
        f":{cor_md}[{icone} {disponibilidade}] · {contrato_txt}",
        f"{int(row['total_pendencias'])} PNs · {int(row['soma_unidades_faltantes'])} un. faltantes",
    ]
    if principal:
        linhas.append(principal)

    if st.button("\n".join(linhas), key=f"card_{row['matricula']}", width="stretch"):
        st.session_state["rac_aeronave_selecionada"] = row["matricula"]
        st.rerun()


def _aba_aeronaves(aeronaves, pendencias):
    prioritarias = aeronaves[aeronaves["disponibilidade"] != "Montada"].copy()
    regulares = aeronaves[aeronaves["disponibilidade"] == "Montada"]

    ordem = {"Sem condições": 0, "Desmontada": 1}
    if not prioritarias.empty:
        prioritarias["_ordem"] = prioritarias["disponibilidade"].map(ordem).fillna(2)
        prioritarias = prioritarias.sort_values(["_ordem", "soma_unidades_faltantes"], ascending=[True, False])

    with st.container(key="rac_cards"):
        st.markdown(f"###### Aeronaves prioritárias ({len(prioritarias)})")
        if prioritarias.empty:
            st.success("Nenhuma aeronave com pendência ou fora de condição no momento — frota regular.")
        else:
            cols = st.columns(3)
            for i, (_, row) in enumerate(prioritarias.iterrows()):
                with cols[i % 3]:
                    _card_aeronave(row, pendencias)

        with st.expander(f"✅ Aeronaves regulares — sem pendências ({len(regulares)})"):
            if regulares.empty:
                st.caption("Nenhuma aeronave regular no filtro atual.")
            else:
                cols = st.columns(3)
                for i, (_, row) in enumerate(regulares.iterrows()):
                    with cols[i % 3]:
                        _card_aeronave(row, pendencias)


def _materiais_criticos(pendencias):
    st.markdown("###### Materiais críticos (afetam mais aeronaves)")
    if pendencias.empty:
        st.caption("Nenhuma pendência no filtro atual.")
        return
    resumo = (
        pendencias.groupby(["pn", "nomenclatura"])
        .agg(aeronaves_afetadas=("matricula", "nunique"), quantidade_total_faltante=("quantidade_faltante", "sum"))
        .reset_index()
        .sort_values("aeronaves_afetadas", ascending=False)
    )
    st.dataframe(resumo, hide_index=True, width="stretch", height=440)


def _matriz(aeronaves, pendencias):
    st.markdown("###### Matriz de pendências")
    col1, col2 = st.columns(2)
    with col1:
        ocultar_sem_pendencia = st.checkbox("Ocultar aeronaves sem pendência", value=True, key="rac_matriz_ocultar")
    with col2:
        somente_contrato = st.checkbox("Mostrar somente aeronaves do contrato", key="rac_matriz_contrato")

    aer = aeronaves.copy()
    if ocultar_sem_pendencia:
        aer = aer[aer["total_pendencias"] > 0]
    if somente_contrato:
        aer = aer[aer["contrato"] == "Dentro do contrato"]

    pend = pendencias[pendencias["matricula"].isin(aer["matricula"])]
    if pend.empty:
        st.caption("Nenhum dado para exibir com os filtros atuais.")
        return

    pivot = pend.pivot_table(index=["pn", "nomenclatura"], columns="matricula",
                              values="quantidade_faltante", fill_value=0)
    ordem_colunas = [c for c in aer["matricula"] if c in pivot.columns]
    pivot = pivot[ordem_colunas]
    st.caption("Cabeçalho fica visível ao rolar (padrão do componente de tabela).")
    st.dataframe(pivot, width="stretch", height=520)


def _detalhe_aeronave(dados, matricula):
    aeronaves = dados["rac_aeronaves"]
    pendencias = dados["rac_pendencias"]

    if st.button("← Voltar à lista"):
        st.session_state["rac_aeronave_selecionada"] = None
        st.rerun()

    linha = aeronaves[aeronaves["matricula"] == matricula]
    if linha.empty:
        st.warning("Aeronave não encontrada nos dados atuais.")
        return
    row = linha.iloc[0]

    st.title(f"FAB {matricula}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Unidade", row["unidade"] or "—")
    c2.metric("Situação", row["disponibilidade"])
    c3.metric("Contrato", row["contrato"])
    c4.metric("PNs distintos faltantes", int(row["total_pendencias"]))
    st.metric("Quantidade total faltante", f"{int(row['soma_unidades_faltantes'])} unidades")

    if row["contrato"] == "Fora do contrato":
        st.info(
            "Aeronave fora do contrato — exibindo apenas o quantitativo total, "
            "sem detalhamento dos itens (ver regra em rac.md)."
        )
        return

    pend_aeronave = pendencias[pendencias["matricula"] == matricula].sort_values(
        "quantidade_faltante", ascending=False
    )

    busca = st.text_input("Buscar nas pendências (PN ou nomenclatura)", key="busca_detalhe")
    if busca:
        b = busca.strip().lower()
        pend_aeronave = pend_aeronave[
            pend_aeronave["pn"].astype(str).str.lower().str.contains(b)
            | pend_aeronave["nomenclatura"].astype(str).str.lower().str.contains(b, na=False)
        ]

    st.markdown("##### Materiais faltantes")
    st.dataframe(pend_aeronave[["pn", "nomenclatura", "quantidade_faltante"]],
                 hide_index=True, width="stretch")

    csv = pend_aeronave.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar esta aeronave", csv, file_name=f"pendencias_{matricula}.csv", mime="text/csv")
