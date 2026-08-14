"""Página Disponibilidade Diária — situação operacional da frota C-98, a partir
dos relatórios diários (ver 00_Instrucoes/disponibilidade_diaria.md).

Fase 1 (ver instruções para o que ainda falta): cabeçalho com seletor de
relatório, indicadores principais, distribuição por situação, previsões,
comparação com o relatório anterior, alertas classificados, painel por
unidade, busca e filtros.
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from shared import horario
from coordenadoria.components.paleta import (
    AMBER, CATEGORICA, CYAN, INK, LINE, PANEL, SECONDARY, STATUS, COR_SITUACAO, NOME_SITUACAO,
    ICONE_SITUACAO, COR_MD_SITUACAO, layout_grafico,
)
from coordenadoria.utils import atualizar_dados_disponibilidade, DISPONIBILIDADE_PASTA_URL

ORDEM_SITUACAO = ["DI", "DO", "II", "IN", "ITR", "IS", "IP"]
COLUNAS_SITUACAO_RESUMO = ["di", "do_", "ii", "in_", "itr", "is_", "ip"]

# Pasta do Cômputo Mensal (Contrato 005) — pedido do Wallace, 2026-08-14:
# jogar as linhas "contratual" e "real VEE ONE" (calculadas lá, ver
# calcular_computo_mensal.py) também no gráfico de evolução daqui. Lê só os
# CSVs prontos por caminho direto — nunca importa scripts do Contrato 005
# neste processo (cada área tem seu próprio common.py; colidem se os 2
# diretórios de scripts entrarem juntos no sys.path — bug real já visto e
# corrigido em 2026-08-14 numa atualização manual).
_RAIZ_PROJETO = Path(__file__).resolve().parents[4]
PASTA_COMPUTO_MENSAL = _RAIZ_PROJETO / "Contrato 005" / "Dashboard" / "02_Dados_Tratados" / "computo_mensal"
MESES_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

FILTRO_KEYS = ["disp_f_unidade", "disp_f_situacao", "disp_f_busca"]


def render(dados):
    if st.session_state.get("disp_aeronave_selecionada"):
        _detalhe_aeronave(dados, st.session_state["disp_aeronave_selecionada"])
        return

    relatorios = dados["disp_relatorios"]
    aeronaves = dados["disp_aeronaves"]

    st.title("Disponibilidade Diária")
    st.caption("Situação operacional da frota C-98 — disponibilidade, montagem e pendências do dia a dia.")

    if relatorios.empty:
        st.info(
            "Nenhum relatório carregado ainda. Peça ao Claude para buscar o relatório mais recente "
            "no Drive (pasta \"Atualização de Disponibilidade\")."
        )
        return

    _estilo()

    datas = sorted(relatorios["data_referencia"].dt.date.unique(), reverse=True)

    if "disp_idx" not in st.session_state:
        st.session_state["disp_idx"] = 0
    st.session_state["disp_idx"] = min(st.session_state["disp_idx"], len(datas) - 1)

    _cabecalho(dados, datas)

    aba_hoje, aba_evolucao = st.tabs(["Situação do dia", "Evolução e histórico"])

    with aba_hoje:
        data_atual = datas[st.session_state["disp_idx"]]
        rel_atual = relatorios[relatorios["data_referencia"].dt.date == data_atual].iloc[0]
        aer_atual = aeronaves[aeronaves["data_referencia"].dt.date == data_atual].copy()

        idx = st.session_state["disp_idx"]
        data_anterior = datas[idx + 1] if idx + 1 < len(datas) else None
        rel_anterior = relatorios[relatorios["data_referencia"].dt.date == data_anterior].iloc[0] if data_anterior is not None else None
        aer_anterior = aeronaves[aeronaves["data_referencia"].dt.date == data_anterior].copy() if data_anterior is not None else None

        _cards_indicadores(rel_atual)
        st.divider()
        col_dist, col_prev = st.columns([1.2, 1])
        with col_dist:
            _distribuicao_situacao(aer_atual)
        with col_prev:
            _previsoes(rel_atual)

        if rel_anterior is not None:
            st.divider()
            _comparacao(rel_atual, aer_atual, rel_anterior, aer_anterior, data_anterior)

        st.divider()
        aer_atual["_alerta"] = aer_atual.apply(classificar_alerta, axis=1)
        _alertas(aer_atual)

        st.divider()
        filtros = _busca_e_filtros(aer_atual)
        aer_f = _aplicar_filtros(aer_atual, filtros)
        _painel_por_unidade(aer_f)

    with aba_evolucao:
        _secao_evolucao(relatorios)


def _estilo():
    st.markdown(
        f"""<style>
.disp-indicador {{
    background: {PANEL};
    border: 1px solid {LINE};
    border-radius: 10px;
    padding: 0.9rem 1rem;
    box-shadow: 0 2px 6px rgba(0,0,0,0.25);
}}
.disp-indicador .valor {{ font-size: 2.2rem; font-weight: 800; }}
.disp-indicador .label {{ font-size: 1.05rem; color: {INK}; margin-top: 0.35rem; font-weight: 700; }}
.disp-indicador .sub {{ font-size: 0.92rem; color: {SECONDARY}; margin-top: 0.15rem; }}
.disp-barra {{ background: {LINE}; border-radius: 6px; height: 8px; margin-top: 0.5rem; overflow: hidden; }}
.disp-barra-fill {{ height: 100%; border-radius: 6px; }}
.disp-badge {{
    display: inline-block;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    color: {INK};
}}
.disp-unidade-resumo {{ font-size: 0.9rem; color: {SECONDARY}; }}
.disp-alerta-card {{
    background: {PANEL};
    border: 1px solid {LINE};
    border-radius: 10px;
    padding: 0.8rem 1rem;
}}
.st-key-disp_cards div.stButton > button {{
    text-align: left;
    white-space: pre-line;
    line-height: 1.6;
    border-radius: 10px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.2);
    height: auto;
    font-size: 1.0rem;
    padding: 0.7rem 0.9rem;
}}
.st-key-disp_cards div.stButton > button p {{
    font-size: 1.0rem;
}}
</style>""",
        unsafe_allow_html=True,
    )


def _cabecalho(dados, datas):
    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
    idx = st.session_state["disp_idx"]
    with col1:
        escolhida = st.selectbox(
            "Relatório de referência",
            options=datas,
            index=idx,
            format_func=lambda d: d.strftime("%d/%m/%Y"),
            key="disp_seletor_data",
        )
        if escolhida != datas[idx]:
            st.session_state["disp_idx"] = datas.index(escolhida)
            st.rerun()
    with col2:
        if st.button("← Anterior", key="disp_anterior", width="stretch", disabled=idx + 1 >= len(datas)):
            st.session_state["disp_idx"] = idx + 1
            st.rerun()
    with col3:
        if st.button("Próximo →", key="disp_proximo", width="stretch", disabled=idx == 0):
            st.session_state["disp_idx"] = idx - 1
            st.rerun()
    with col4:
        if st.button("🔄 Atualizar dados", key="disp_atualizar", width="stretch"):
            with st.spinner("Reprocessando relatórios locais..."):
                atualizar_dados_disponibilidade()
            st.rerun()
    with col5:
        st.link_button("🔗 Pasta no Drive", DISPONIBILIDADE_PASTA_URL, width="stretch")

    if dados["disp_atualizado_em"]:
        atualizado = horario.fromtimestamp_br(dados["disp_atualizado_em"]).strftime("%d/%m/%Y %H:%M")
        st.caption(f"Última atualização dos dados: **{atualizado}**")


def _card_indicador(col, valor, label, sub, cor, barra_pct=None, barra_cor=None):
    with col:
        barra_html = ""
        if barra_pct is not None:
            barra_html = (
                f'<div class="disp-barra"><div class="disp-barra-fill" '
                f'style="width:{min(barra_pct, 100)}%;background:{barra_cor};"></div></div>'
            )
        st.markdown(
            f'<div class="disp-indicador"><div class="valor" style="color:{cor};">{valor}</div>'
            f'<div class="label">{label}</div><div class="sub">{sub}</div>{barra_html}</div>',
            unsafe_allow_html=True,
        )


def _cards_indicadores(rel):
    disponiveis = int(rel["disponiveis_hoje"])
    montadas = int(rel["montadas_hoje"])
    pct_disp = round(100 * disponiveis / montadas) if montadas else 0
    pct_esforco = rel["esforco_percentual"]

    l1 = st.columns(4)
    _card_indicador(l1[0], disponiveis, "Disponíveis (D)", "DI + DO", STATUS["good"])
    _card_indicador(l1[1], montadas, "Montadas (M)", "sem AIFP/IPLR pendente", CYAN)
    _card_indicador(l1[2], f"{pct_disp}%", "% disponibilidade", f"{disponiveis} de {montadas} montadas",
                     AMBER, barra_pct=pct_disp, barra_cor=AMBER)
    _card_indicador(l1[3], int(rel["motores_disponiveis"]), "Motores disponíveis", "", SECONDARY)

    l2 = st.columns(4)
    _card_indicador(l2[0], f"{int(rel['previsao_fim_dia_disponiveis'])} D",
                     "Previsão fim do dia", f"{int(rel['previsao_fim_dia_montadas'])} M", STATUS["good"])
    _card_indicador(l2[1], f"{int(rel['previsao_semana_disponiveis_qtd'])} D",
                     "Previsão semanal", f"{int(rel['previsao_semana_montadas_qtd'])} M", CYAN)
    _card_indicador(l2[2], f"{pct_esforco:.2f}%".replace(".", ","), "Esforço aéreo realizado",
                     f"{rel['esforco_anual_realizado']} de {rel['esforco_anual_previsto']}",
                     AMBER, barra_pct=pct_esforco, barra_cor=AMBER)
    total_pendentes = int(rel["ii"]) + int(rel["in_"]) + int(rel["itr"]) + int(rel["is_"]) + int(rel["ip"])
    _card_indicador(l2[3], total_pendentes, "Aeronaves indisponíveis", "II + IN + ITR + IS + IP",
                     STATUS["critical"] if total_pendentes else STATUS["good"])


def _distribuicao_situacao(aer):
    st.markdown("##### Distribuição por situação")
    contagem = aer["situacao"].value_counts().reindex(ORDEM_SITUACAO).fillna(0).reset_index()
    contagem.columns = ["situacao", "quantidade"]
    contagem["nome"] = contagem["situacao"].map(NOME_SITUACAO)
    fig = px.bar(
        contagem, x="quantidade", y="situacao", orientation="h",
        color="situacao", color_discrete_map=COR_SITUACAO,
        hover_data={"nome": True, "situacao": False, "quantidade": True},
    )
    fig.update_layout(yaxis_title="", xaxis_title="", showlegend=False,
                       yaxis={"categoryorder": "array", "categoryarray": ORDEM_SITUACAO[::-1], "type": "category"})
    layout_grafico(fig, altura=260)
    st.plotly_chart(fig, width="stretch")
    st.caption(
        " · ".join(f"**{sigla}** {nome}" for sigla, nome in NOME_SITUACAO.items())
    )


def _previsoes(rel):
    st.markdown("##### Previsão semanal")
    disp_hoje = int(rel["disponiveis_hoje"])
    disp_semana = int(rel["previsao_semana_disponiveis_qtd"])
    mont_hoje = int(rel["montadas_hoje"])
    mont_semana = int(rel["previsao_semana_montadas_qtd"])

    st.markdown(
        f'<div class="disp-alerta-card">'
        f'<div style="font-size:1.1rem;"><strong>{disp_hoje} → {disp_semana}</strong> disponíveis '
        f'<span style="color:{SECONDARY};">({"+" if disp_semana >= disp_hoje else ""}{disp_semana - disp_hoje})</span></div>'
        f'<div style="color:{SECONDARY};font-size:0.85rem;margin-top:0.2rem;">Entram: {rel["previsao_semana_disponiveis_novas"] or "—"}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.write("")
    st.markdown(
        f'<div class="disp-alerta-card">'
        f'<div style="font-size:1.1rem;"><strong>{mont_hoje} → {mont_semana}</strong> montadas '
        f'<span style="color:{SECONDARY};">({"+" if mont_semana >= mont_hoje else ""}{mont_semana - mont_hoje})</span></div>'
        f'<div style="color:{SECONDARY};font-size:0.85rem;margin-top:0.2rem;">Entram: {rel["previsao_semana_montadas_novas"] or "—"}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def classificar_alerta(row):
    situacao = row["situacao"]
    if situacao in ("DI", "DO"):
        return None
    ocorrencia = str(row["ocorrencia"]).lower() if pd.notna(row["ocorrencia"]) else ""
    condicao = str(row["dpe_condicao"]).lower() if pd.notna(row["dpe_condicao"]) else ""
    dpe_data = row["dpe_data"]

    if situacao == "IP" or "acidentada" in ocorrencia or "sem motor" in ocorrencia:
        return "critico"
    if pd.notna(dpe_data):
        dias = (dpe_data.date() if hasattr(dpe_data, "date") else dpe_data) - horario.hoje_br()
        dias = dias.days
        if dias < 0:
            return "critico"
        if dias <= 7:
            return "atencao"
        return "programado"
    if condicao:
        if any(k in condicao for k in ["a ser definido", "a det", "sem previsão", "sem data"]):
            return "critico"
        return "atencao"
    return "critico"


def _alertas(aer):
    st.markdown("##### Requerem atenção")
    criticos = aer[aer["_alerta"] == "critico"]
    atencao = aer[aer["_alerta"] == "atencao"]
    programados = aer[aer["_alerta"] == "programado"]

    c1, c2, c3 = st.columns(3)
    _card_indicador(c1, len(criticos), "Críticos", "sem DPE, vencidas ou acidentadas", STATUS["critical"])
    _card_indicador(c2, len(atencao), "Em atenção", "DPE próxima ou condicionada", AMBER)
    _card_indicador(c3, len(programados), "Programados", "DPE definida, dentro do prazo", STATUS["good"])

    if len(criticos):
        with st.expander(f"⛔ Ver aeronaves críticas ({len(criticos)})", expanded=True):
            for _, row in criticos.iterrows():
                _linha_alerta(row, STATUS["critical"])


def _linha_alerta(row, cor):
    ocorrencia = row["ocorrencia"] if pd.notna(row["ocorrencia"]) else "—"
    dpe = row["dpe_texto_original"] if pd.notna(row["dpe_texto_original"]) else "sem DPE definido"
    st.markdown(
        f'<div class="disp-alerta-card" style="border-left:3px solid {cor};margin-bottom:0.5rem;">'
        f'<strong>FAB {row["matricula"]}</strong> <span style="color:{SECONDARY};">· {row["unidade"]} · {row["situacao"]}</span><br>'
        f'<span style="font-size:0.88rem;">{ocorrencia}</span><br>'
        f'<span style="font-size:0.82rem;color:{SECONDARY};">DPE: {dpe}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _comparacao(rel_atual, aer_atual, rel_anterior, aer_anterior, data_anterior):
    st.markdown(f"##### Mudanças desde {data_anterior.strftime('%d/%m/%Y')}")

    d_delta = int(rel_atual["disponiveis_hoje"]) - int(rel_anterior["disponiveis_hoje"])
    m_delta = int(rel_atual["montadas_hoje"]) - int(rel_anterior["montadas_hoje"])
    c1, c2 = st.columns(2)
    with c1:
        cor = STATUS["good"] if d_delta > 0 else (STATUS["critical"] if d_delta < 0 else SECONDARY)
        st.markdown(
            f'<div class="disp-alerta-card">Disponíveis: {int(rel_anterior["disponiveis_hoje"])} → '
            f'<strong style="color:{cor};">{int(rel_atual["disponiveis_hoje"])}</strong> '
            f'({"+" if d_delta >= 0 else ""}{d_delta})</div>',
            unsafe_allow_html=True,
        )
    with c2:
        cor = STATUS["good"] if m_delta > 0 else (STATUS["critical"] if m_delta < 0 else SECONDARY)
        st.markdown(
            f'<div class="disp-alerta-card">Montadas: {int(rel_anterior["montadas_hoje"])} → '
            f'<strong style="color:{cor};">{int(rel_atual["montadas_hoje"])}</strong> '
            f'({"+" if m_delta >= 0 else ""}{m_delta})</div>',
            unsafe_allow_html=True,
        )

    anterior_map = aer_anterior.set_index("matricula")["situacao"].to_dict()
    mudancas = []
    for _, row in aer_atual.iterrows():
        situ_ant = anterior_map.get(row["matricula"])
        if situ_ant is None:
            mudancas.append((row["matricula"], "novo no relatório", situ_ant, row["situacao"]))
        elif situ_ant != row["situacao"]:
            if situ_ant not in ("DI", "DO") and row["situacao"] in ("DI", "DO"):
                tag = "retornou à disponibilidade"
            elif situ_ant in ("DI", "DO") and row["situacao"] not in ("DI", "DO"):
                tag = "ficou indisponível"
            else:
                tag = "mudou de situação"
            mudancas.append((row["matricula"], tag, situ_ant, row["situacao"]))
    atuais = set(aer_atual["matricula"])
    for matricula, situ_ant in anterior_map.items():
        if matricula not in atuais:
            mudancas.append((matricula, "saiu do relatório", situ_ant, None))

    st.write("")
    if not mudancas:
        st.success("Nenhuma aeronave mudou de situação desde o relatório anterior.")
        return
    for matricula, tag, situ_ant, situ_atual in mudancas:
        transicao = f"{situ_ant or '—'} → {situ_atual or '—'}"
        st.markdown(f"- **FAB {matricula}** — {tag} ({transicao})")


def _busca_e_filtros(aer):
    st.markdown("##### Busca e filtros")
    c1, c2, c3 = st.columns(3)
    with c1:
        unidades = st.multiselect("Unidade", sorted(aer["unidade"].dropna().unique()), key="disp_f_unidade")
    with c2:
        situacoes = st.multiselect("Situação", ORDEM_SITUACAO, key="disp_f_situacao")
    with c3:
        busca = st.text_input("🔎 Busca (matrícula ou ocorrência)", key="disp_f_busca")

    if st.button("✕ Limpar filtros", key="disp_limpar_filtros"):
        for k in FILTRO_KEYS:
            st.session_state.pop(k, None)
        st.rerun()

    return dict(unidades=unidades, situacoes=situacoes, busca=busca)


def _aplicar_filtros(aer, f):
    df = aer.copy()
    if f["unidades"]:
        df = df[df["unidade"].isin(f["unidades"])]
    if f["situacoes"]:
        df = df[df["situacao"].isin(f["situacoes"])]
    if f["busca"]:
        termo = f["busca"].lower()
        df = df[
            df["matricula"].astype(str).str.lower().str.contains(termo)
            | df["ocorrencia"].fillna("").str.lower().str.contains(termo)
        ]
    return df


def _card_aeronave_disp(row):
    situacao = row["situacao"]
    icone = ICONE_SITUACAO.get(situacao, "•")
    cor_md = COR_MD_SITUACAO.get(situacao, "gray")
    ocorrencia = row["ocorrencia"] if pd.notna(row["ocorrencia"]) else None
    dpe = row["dpe_texto_original"] if pd.notna(row["dpe_texto_original"]) else None

    linhas = [
        f"**FAB {row['matricula']}**",
        f":{cor_md}[{icone} {situacao} — {NOME_SITUACAO.get(situacao, situacao)}]",
    ]
    if ocorrencia:
        linhas.append(ocorrencia)
    if dpe:
        linhas.append(f"DPE: {dpe}")

    if st.button("\n".join(linhas), key=f"disp_card_{row['matricula']}", width="stretch"):
        st.session_state["disp_aeronave_selecionada"] = row["matricula"]
        st.rerun()


def _painel_por_unidade(aer):
    st.markdown("##### Painel por unidade")
    if aer.empty:
        st.caption("Nenhuma aeronave no filtro atual.")
        return

    with st.container(key="disp_cards"):
        for unidade in aer["unidade"].drop_duplicates().tolist():
            grupo = aer[aer["unidade"] == unidade].sort_values("matricula")
            resumo_situacoes = grupo["situacao"].value_counts()
            resumo_txt = " · ".join(f"{qtd} {sit}" for sit, qtd in resumo_situacoes.items())
            with st.expander(f"{unidade} — {len(grupo)} aeronave(s) · {resumo_txt}"):
                cols = st.columns(3)
                for i, (_, row) in enumerate(grupo.iterrows()):
                    with cols[i % 3]:
                        _card_aeronave_disp(row)


def _semanas_disponiveis(datas):
    """Segundas-feiras de cada semana com pelo menos 1 relatório — "semana"
    é sempre segunda a sexta (mesmo critério já usado em Empréstimos,
    2026-07-23: "semana entenda de segunda a sexta")."""
    return sorted({d - pd.Timedelta(days=d.weekday()) for d in datas})


def _tabela_semana(relatorios, datas):
    st.markdown("##### Histórico da semana (segunda a sexta)")
    semanas = _semanas_disponiveis(datas)
    semana_escolhida = st.selectbox(
        "Semana", semanas, index=len(semanas) - 1,
        format_func=lambda seg: f"Semana de {seg.strftime('%d/%m/%Y')} a {(seg + pd.Timedelta(days=4)).strftime('%d/%m/%Y')}",
        key="disp_semana",
    )
    dias_uteis = [semana_escolhida + pd.Timedelta(days=i) for i in range(5)]
    nomes_dia = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]

    linhas = []
    for nome, dia in zip(nomes_dia, dias_uteis):
        if dia not in datas:
            linhas.append({"Dia": nome, "Data": dia.strftime("%d/%m"), "D": "—", "M": "—",
                            "% disponibilidade": "—", "Indisponíveis": "—"})
            continue
        rel = relatorios[relatorios["data_referencia"].dt.date == dia].iloc[0]
        d, m = int(rel["disponiveis_hoje"]), int(rel["montadas_hoje"])
        pct = round(100 * d / m) if m else 0
        indisponiveis = int(rel["ii"]) + int(rel["in_"]) + int(rel["itr"]) + int(rel["is_"]) + int(rel["ip"])
        linhas.append({"Dia": nome, "Data": dia.strftime("%d/%m"), "D": str(d), "M": str(m),
                        "% disponibilidade": f"{pct}%", "Indisponíveis": str(indisponiveis)})

    st.dataframe(pd.DataFrame(linhas), hide_index=True, width="stretch")
    st.caption("\"—\" = sem relatório salvo naquele dia (raro num dia útil).")


def _grafico_mensal(relatorios):
    st.markdown("##### Comparação mensal (média de D/M por mês)")
    rel = relatorios.copy()
    rel["mes"] = rel["data_referencia"].dt.to_period("M").astype(str)
    resumo = rel.groupby("mes").agg(
        media_disponiveis=("disponiveis_hoje", "mean"),
        media_montadas=("montadas_hoje", "mean"),
    ).reset_index().sort_values("mes")

    fig = px.line(resumo, x="mes", y=["media_disponiveis", "media_montadas"], markers=True,
                  color_discrete_sequence=[STATUS["good"], CYAN])
    fig.for_each_trace(lambda t: t.update(name={"media_disponiveis": "Disponíveis (D)", "media_montadas": "Montadas (M)"}[t.name]))
    fig.update_layout(xaxis_title="", yaxis_title="Média por dia", legend_title="")
    layout_grafico(fig, altura=260)
    st.plotly_chart(fig, width="stretch")
    st.caption("Média simples dos relatórios daquele mês (não pondera por dias úteis restantes).")


def _grafico_evolucao_mes(relatorios):
    """Evolução dia a dia dentro de um mês escolhido — mesmo padrão do
    gráfico "Evolução da % de aeronaves montadas no mês" do Cômputo Mensal
    (Contrato 005), mas aqui com a quantidade de aeronaves Disponíveis (D =
    DI+DO) e Montadas (M), não %. Pedido do Wallace, 2026-07-31: "coloca um
    grafico igual o da media mensal, que tem um grafico do mes inteiro
    [...] mostrando a evolucao no mes, coloca selecionavel o mes tb [...]
    importante o tanto de aeronave montada e o tanto de aeronave
    disponivel(di+do)" — diferente de `_grafico_mensal` (1 ponto = média do
    mês inteiro, comparando vários meses), este mostra 1 ponto por dia,
    dentro de um único mês por vez."""
    st.markdown("##### Evolução no mês — Disponíveis (D) x Montadas (M)")

    rel = relatorios.copy()
    rel["mes"] = rel["data_referencia"].dt.to_period("M")
    meses = sorted(rel["mes"].unique())
    mes_escolhido = st.selectbox(
        "Mês", meses, index=len(meses) - 1,
        format_func=lambda p: f"{MESES_PT[p.month - 1]}/{p.year}", key="disp_grafico_mes",
    )

    do_mes = rel[rel["mes"] == mes_escolhido].sort_values("data_referencia").copy()
    do_mes["dia"] = do_mes["data_referencia"].dt.day

    fig = px.line(
        do_mes, x="dia", y=["disponiveis_hoje", "montadas_hoje"], markers=True,
        color_discrete_sequence=[STATUS["good"], CYAN],
    )
    fig.for_each_trace(lambda t: t.update(name={"disponiveis_hoje": "Disponíveis (D)", "montadas_hoje": "Montadas (M)"}[t.name]))

    # Linha da média do mês — pedido do Wallace, 2026-07-31: "coloca a
    # linha da media no grafico". Uma linha pontilhada por métrica, na
    # mesma cor da série, com o valor médio no rótulo.
    media_d = do_mes["disponiveis_hoje"].mean()
    media_m = do_mes["montadas_hoje"].mean()
    fig.add_hline(
        y=media_d, line_dash="dash", line_color=STATUS["good"], opacity=0.6,
        annotation_text=f"Média D: {media_d:.1f}", annotation_position="bottom left",
        annotation_font_color=STATUS["good"],
    )
    fig.add_hline(
        y=media_m, line_dash="dash", line_color=CYAN, opacity=0.6,
        annotation_text=f"Média M: {media_m:.1f}", annotation_position="top left",
        annotation_font_color=CYAN,
    )

    ultimo_dia_mes = mes_escolhido.end_time.day
    fig.update_layout(
        xaxis_title="Dia do mês", yaxis_title="Quantidade de aeronaves", legend_title="",
        xaxis_range=[0.5, ultimo_dia_mes + 0.5],
    )
    layout_grafico(fig, altura=260)
    st.plotly_chart(fig, width="stretch")
    st.caption("Sem ponto nos dias sem relatório salvo (fim de semana, ou dia útil sem busca ainda).")

    _grafico_evolucao_percentual(do_mes, mes_escolhido)


def _carregar_percentuais_computo_mensal(ano, mes):
    """Lê os CSVs que o Cômputo Mensal (Contrato 005) já grava — sem
    importar nenhum script de lá (ver nota em `PASTA_COMPUTO_MENSAL`).
    Devolve (contratual_df, vee_one_df), cada um com colunas dia/montada
    (%) — ou None se o Cômputo Mensal desse mês ainda não foi calculado
    (precisa clicar "Recalcular" no Fechamento Mensal, Contrato 005,
    primeiro)."""
    mes_ref = f"{ano}-{mes:02d}"
    caminho_matriz = PASTA_COMPUTO_MENSAL / f"{mes_ref}_matriz.csv"
    caminho_vee_one = PASTA_COMPUTO_MENSAL / f"{mes_ref}_vee_one.csv"

    contratual = None
    if caminho_matriz.exists():
        matriz = pd.read_csv(caminho_matriz, dtype={"matricula": str})
        contratual = matriz.dropna(subset=["montada"]).groupby("dia")["montada"].mean().mul(100).reset_index()

    vee_one = pd.read_csv(caminho_vee_one) if caminho_vee_one.exists() else None
    return contratual, vee_one


def _grafico_evolucao_percentual(do_mes, mes_escolhido):
    """3 linhas de % montadas no mesmo mês do gráfico acima — pedido do
    Wallace, 2026-08-14: "a media de montada geral, conta itens fora do
    contrato, a media vee one real e a media contratual [...] no gráfico
    lá dentro da disp diária" (gráfico novo e separado, não misturado com a
    contagem de aeronaves do gráfico D x M acima — escalas diferentes).

    - **Geral** — direto do próprio relatório diário (Coordenadoria), soma
      dos 7 códigos de situação como total (a mesma regra de consistência
      já usada na extração) e `montadas_hoje` como numerador — cobre
      **todas** as aeronaves do relatório, dentro ou fora do contrato
      (confirmado pelo Wallace: "vai ser a que já puxa da todo dia, já
      puxa da mensagem da disp diária, ela já tá lá" — não é um cálculo
      novo, só uma % em cima do que a Disponibilidade Diária já extrai).
    - **Contratual** e **VEE ONE real** — vêm prontas do Cômputo Mensal
      (Contrato 005), só aeronaves "dentro do contrato" (ver
      `_carregar_percentuais_computo_mensal`)."""
    st.markdown("##### Evolução no mês — % de aeronaves montadas (geral x contratual x VEE ONE real)")

    do_mes = do_mes.copy()
    total_situacao = do_mes[COLUNAS_SITUACAO_RESUMO].sum(axis=1)
    do_mes["pct_geral"] = (100 * do_mes["montadas_hoje"] / total_situacao).where(total_situacao > 0)

    contratual, vee_one = _carregar_percentuais_computo_mensal(mes_escolhido.year, mes_escolhido.month)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=do_mes["dia"], y=do_mes["pct_geral"], mode="lines+markers",
        name="% montadas (geral — todas as aeronaves do relatório)",
        line=dict(color=CATEGORICA[2]),
    ))
    if contratual is not None:
        fig.add_trace(go.Scatter(
            x=contratual["dia"], y=contratual["montada"], mode="lines+markers",
            name="% montadas (contratual — Cômputo Mensal oficial)", line=dict(color=AMBER),
        ))
    if vee_one is not None:
        fig.add_trace(go.Scatter(
            x=vee_one["dia"], y=vee_one["montada"], mode="lines+markers",
            name="% montadas (real VEE ONE)", line=dict(color=CYAN, dash="dot"), marker=dict(size=5),
        ))

    ultimo_dia_mes = mes_escolhido.end_time.day
    fig.update_layout(
        xaxis_title="Dia do mês", yaxis_title="% montadas", yaxis_range=[0, 105], legend_title="",
        xaxis_range=[0.5, ultimo_dia_mes + 0.5],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    layout_grafico(fig, altura=260)
    st.plotly_chart(fig, width="stretch")

    if contratual is None or vee_one is None:
        st.info(
            "\"Contratual\" e/ou \"real VEE ONE\" não aparecem — o Cômputo Mensal desse mês ainda não foi "
            "calculado no Fechamento Mensal (Contrato 005). Abra lá e clique em \"🔄 Recalcular\" pra essas "
            "2 linhas aparecerem aqui também."
        )
    st.caption(
        "\"Geral\" conta todas as aeronaves do relatório diário (dentro ou fora do contrato). "
        "\"Contratual\" e \"real VEE ONE\" só contam aeronaves dentro do contrato — mesmas 2 linhas do "
        "gráfico \"Evolução da % de aeronaves montadas no mês\" no Cômputo Mensal (Contrato 005)."
    )


def _secao_evolucao(relatorios):
    """Evolução diária/semanal/mensal da frota inteira, tudo dentro da
    própria Disponibilidade Diária (2026-07-23, pedido do Wallace:
    "historico de disponibidade, vamos criar tb ... historicos semanais, e
    comparacoes diarias, mensais, tudo ali dentro da disponiblidade diaria
    mesmo"). A comparação diária (com o relatório imediatamente anterior)
    já existia na aba "Situação do dia" — aqui entram semana e mês, que
    faltavam."""
    if relatorios.empty or len(relatorios) < 2:
        st.info("Ainda não há histórico suficiente pra mostrar evolução.")
        return

    datas = sorted(relatorios["data_referencia"].dt.date.unique())

    _tabela_semana(relatorios, datas)
    st.divider()
    _grafico_evolucao_mes(relatorios)
    st.divider()
    _grafico_mensal(relatorios)


def _pendencias_rac_por_dia(dados, matricula):
    """Total de PNs distintos faltantes (RAC) por dia, pra cruzar com a
    situação operacional da mesma aeronave no histórico da Disponibilidade."""
    historico_rac = dados.get("rac_historico")
    if historico_rac is None or historico_rac.empty:
        return None
    hist_aeronave = historico_rac[historico_rac["matricula"] == str(matricula)]
    if hist_aeronave.empty:
        return None
    por_dia = hist_aeronave.groupby("data")["pn"].nunique().reset_index()
    por_dia.columns = ["data_referencia", "total_pendencias_rac"]
    return por_dia


def _detalhe_aeronave(dados, matricula):
    aeronaves = dados["disp_aeronaves"]

    if st.button("← Voltar à lista"):
        st.session_state["disp_aeronave_selecionada"] = None
        st.rerun()

    hist = aeronaves[aeronaves["matricula"] == matricula].sort_values("data_referencia")
    if hist.empty:
        st.warning("Aeronave não encontrada nos relatórios carregados.")
        return
    atual = hist.iloc[-1]

    st.title(f"FAB {matricula}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Situação atual", f"{atual['situacao']} — {NOME_SITUACAO.get(atual['situacao'], '')}")
    c2.metric("Unidade", atual["unidade"] or "—")
    c3.metric("Último relatório", atual["data_referencia"].strftime("%d/%m/%Y"))

    aba_atual, aba_historico = st.tabs(["Situação atual", "Histórico"])

    with aba_atual:
        ocorrencia = atual["ocorrencia"] if pd.notna(atual["ocorrencia"]) else "—"
        dpe = atual["dpe_texto_original"] if pd.notna(atual["dpe_texto_original"]) else "—"
        st.markdown(f"**Ocorrência:** {ocorrencia}")
        st.markdown(f"**DPE:** {dpe}")

    with aba_historico:
        if len(hist) < 2:
            st.info(
                "Só existe 1 relatório com esta aeronave até agora — o histórico vai crescendo "
                "conforme os relatórios diários forem chegando (seg-sex, via atualização automática)."
            )

        st.markdown("##### Linha do tempo — situação por relatório")
        fig = px.scatter(
            hist, x="data_referencia", y="situacao",
            color="situacao", color_discrete_map=COR_SITUACAO,
            category_orders={"situacao": ORDEM_SITUACAO},
        )
        fig.update_traces(marker=dict(size=12))
        fig.update_layout(yaxis_title="", xaxis_title="", showlegend=False)
        layout_grafico(fig, altura=220)
        st.plotly_chart(fig, width="stretch")

        tabela = hist[["data_referencia", "situacao", "ocorrencia", "dpe_texto_original"]].copy()

        pendencias_por_dia = _pendencias_rac_por_dia(dados, matricula)
        if pendencias_por_dia is not None:
            tabela = tabela.merge(pendencias_por_dia, on="data_referencia", how="left")
            tabela["total_pendencias_rac"] = tabela["total_pendencias_rac"].apply(
                lambda v: "—" if pd.isna(v) else f"{int(v)} PN(s)"
            )

        tabela["data_referencia"] = tabela["data_referencia"].dt.strftime("%d/%m/%Y")
        colunas = {
            "data_referencia": "Data", "situacao": "Situação",
            "ocorrencia": "Ocorrência", "dpe_texto_original": "DPE",
            "total_pendencias_rac": "Pendências RAC (mesmo dia)",
        }
        tabela = tabela.rename(columns=colunas).fillna("—").sort_values("Data", ascending=False)
        st.dataframe(tabela, hide_index=True, width="stretch")
        if pendencias_por_dia is not None:
            st.caption(
                "\"Pendências RAC (mesmo dia)\" só aparece nas datas em que o RAC também foi "
                "atualizado (a partir de 2026-07-06) — ver Coordenadoria/00_Instrucoes/rac.md."
            )

        csv = tabela.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Exportar histórico desta aeronave", csv,
                            file_name=f"historico_disponibilidade_{matricula}.csv", mime="text/csv")
