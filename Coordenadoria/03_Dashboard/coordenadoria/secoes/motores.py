"""Página Motores — visão executiva de motores (SILOMS) e hélices, projeção
de vencimento de TBO/HSI (Diagonal Nova, com os comentários das células) e
ordens de serviço em andamento (OS). Fonte: planilha pessoal do Wallace
"MOTORES C-98" (Google Drive) — ver 00_Instrucoes/motores.md.

Redesenho executivo em 2026-07-14 (pedido do Wallace, spec detalhada):
4 subabas (Visão Geral / Diagonal TBO/HSI / Ordens de Serviço / Hélices),
cabeçalho enxuto, faixas de risco por cor (Vencido/Atenção/Normal a partir
de % TBO voada), tabelas completas em expansível, filtros numa linha só.
"Previsão" (perdas TBO/HSI/PNP, produção) ficou de fora por pedido do
Wallace — precisa de outras abas da planilha (cenário/produção) ainda não
extraídas.
"""

import re
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from coordenadoria.components.evolucao import secao_evolucao
from coordenadoria.components.filtros import filtro_colunas
from coordenadoria.components.paleta import AMBER, CYAN, INK, LINE, PANEL, SECONDARY, STATUS, layout_grafico
from coordenadoria.utils import atualizar_dados_motores

EVENTOS_TBO_HSI = {"TBO", "TBO*", "HSI"}
MESES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

COR_CONDICAO = {
    "APL": STATUS["good"], "OS": STATUS["critical"], "REPARA": AMBER,
    "RECOLH": CYAN, "REMOV": SECONDARY,
}

# INT/REC/SOL — tradução do código de status da OS (melhor interpretação a
# partir do vocabulário SILOMS; não confirmado literalmente com o Wallace,
# ver 00_Instrucoes/motores.md).
NOMES_STATUS_OS = {"INT": "Internado (em conserto)", "REC": "Recebida", "SOL": "Solicitada"}

NOMES_SITUACAO = {
    "om": "OM", "pn": "PN", "sn": "SN", "fabricante": "Fabricante",
    "parcial_tso": "TSO", "totais_tsn": "TSN",
    "pct_tbo_voada": "% TBO voada", "matricula": "Matrícula", "tbo": "TBO",
    "condicao": "Condição", "faixa_risco": "Situação", "numero_doc": "Nº Doc",
    "data_doc": "Data Doc", "motivo": "Motivo", "tipo": "Tipo", "projeto": "Projeto",
    "controle": "Controle", "data_1": "Data 1", "data_2": "Data 2", "recolhimento": "Recolhimento",
}
COLUNAS_SITUACAO_PRINCIPAIS = ["sn", "matricula", "om", "faixa_risco", "pct_tbo_voada", "condicao", "tbo", "motivo"]
COLUNAS_SITUACAO_DETALHE = ["pn", "fabricante", "tipo", "controle", "parcial_tso", "totais_tsn", "numero_doc", "data_doc"]

NOMES_OS = {
    "os": "OS", "status_legivel": "Status", "tipo": "Tipo", "sn": "SN", "matricula": "Matrícula",
    "nomenclatura": "Nomenclatura", "data_status": "Data Status", "data_inicio_real": "Início Real",
    "data_fim_prev": "Fim Previsto", "prioridade": "Prioridade", "unidade_exec": "Unidade Exec.",
    "solicitante": "Solicitante", "atrasada": "Atrasada?",
    "os_origem": "OS Origem", "cff": "CFF", "data_recebimento": "Recebimento",
    "data_inicio_prev": "Início Previsto", "data_fim_real": "Fim Real", "setor_exec": "Setor Exec.",
    "unidade_solic": "Unidade Solic.", "setor_solic": "Setor Solic.",
    "pessoa_solicitante": "Pessoa Solicitante", "comentarios": "Comentários",
}
COLUNAS_OS_PRINCIPAIS = ["os", "status_legivel", "sn", "matricula", "nomenclatura", "data_status", "data_fim_prev", "atrasada", "unidade_exec"]
COLUNAS_OS_DETALHE = ["tipo", "os_origem", "cff", "prioridade", "data_recebimento", "data_inicio_prev",
                       "data_inicio_real", "data_fim_real", "setor_exec", "solicitante", "unidade_solic",
                       "setor_solic", "pessoa_solicitante", "comentarios"]


def _faixa_risco(pct):
    """Vencido (vermelho) >= 100% · Atenção (amarelo) 80-99% · Normal (verde) < 80%."""
    if pd.isna(pct):
        return "Sem dado"
    if pct >= 100:
        return "Vencido"
    if pct >= 80:
        return "Atenção"
    return "Normal"


COR_FAIXA = {"Vencido": STATUS["critical"], "Atenção": AMBER, "Normal": STATUS["good"], "Sem dado": SECONDARY}


def _fmt_data(valor):
    return valor.strftime("%d/%m/%Y") if pd.notna(valor) else "—"


def _fmt_horas(valor):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "—"
    return f"{valor:,.0f} h".replace(",", ".")


def _encurtar_fabricante(valor):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "—"
    texto = re.sub(r"^\d{4,6}-", "", str(valor))
    return texto[:26].rstrip() + "…" if len(texto) > 28 else texto


def _fmt_pct(valor):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "—"
    return f"{valor:.0f}%"


def _preparar_tabela(df, colunas_data=(), colunas_hora=(), colunas_fabricante=(), colunas_pct=()):
    """Padronização geral: datas dd/mm/aaaa, horas com "h", % formatado,
    fabricante encurtado, "None"/NaN vira "—" em tudo. Colunas numéricas
    precisam ser formatadas ANTES do fillna("—") — senão a coluna fica com
    tipo misto (número + texto) e quebra a serialização Arrow do
    st.dataframe."""
    df = df.copy()
    for c in colunas_data:
        if c in df.columns:
            df[c] = df[c].apply(_fmt_data)
    for c in colunas_hora:
        if c in df.columns:
            df[c] = df[c].apply(_fmt_horas)
    for c in colunas_pct:
        if c in df.columns:
            df[c] = df[c].apply(_fmt_pct)
    for c in colunas_fabricante:
        if c in df.columns:
            df[c] = df[c].apply(_encurtar_fabricante)

    # Colunas de texto "livre" às vezes têm um valor numérico solto (ex.:
    # "motivo" com 315.0 ou 315 em vez de texto) — sem normalizar, a coluna
    # fica com tipo misto (número + "—") depois do fillna e quebra o Arrow.
    # Bug real visto em 2026-07-23: o `isinstance(v, float)` original não
    # pegava valor já como `int` puro (não só float), então "Motivo" ainda
    # quebrava (`ArrowTypeError: Expected bytes, got a 'int' object`) —
    # agora cobre os dois tipos.
    ja_tratadas = set(colunas_data) | set(colunas_hora) | set(colunas_pct) | set(colunas_fabricante)
    for c in df.columns:
        if c in ja_tratadas:
            continue
        if df[c].dtype == object or pd.api.types.is_float_dtype(df[c]) or pd.api.types.is_integer_dtype(df[c]):
            df[c] = df[c].apply(
                lambda v: str(int(v)) if isinstance(v, (int, float)) and not isinstance(v, bool) and pd.notna(v)
                and float(v).is_integer() else v
            )

    return df.fillna("—")


def _card_indicador(col, icone, valor, label, sub, cor):
    with col:
        st.markdown(
            f'<div style="background:{PANEL};border:1px solid {LINE};border-radius:10px;'
            f'padding:0.9rem 1rem;min-height:112px;box-shadow:0 2px 6px rgba(0,0,0,0.25);">'
            f'<div style="display:flex;align-items:center;justify-content:space-between;">'
            f'<span style="font-size:1.4rem;opacity:0.85;">{icone}</span>'
            f'<span style="font-size:1.9rem;font-weight:800;color:{cor};">{valor}</span>'
            f"</div>"
            f'<div style="font-size:0.98rem;color:{INK};margin-top:0.4rem;font-weight:700;">{label}</div>'
            f'<div style="font-size:0.85rem;color:{SECONDARY};margin-top:0.15rem;">{sub}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )


def render(dados):
    st.title("Motores")
    st.caption('Fonte: planilha pessoal "MOTORES C-98" (Drive do Wallace) — SILOMS, Diagonal Nova, OS, Hélice.')

    col1, col2 = st.columns([4, 1])
    with col1:
        atualizado = dados.get("motores_atualizado_em")
        if atualizado:
            st.caption(f"Última atualização: **{datetime.fromtimestamp(atualizado).strftime('%d/%m/%Y %H:%M')}**")
    with col2:
        if st.button("🔄 Atualizar dados", key="motores_atualizar", width="stretch"):
            with st.spinner("Atualizando..."):
                atualizar_dados_motores()
            st.rerun()

    situacao = dados.get("motores_situacao")
    if situacao is None or situacao.empty:
        st.info('Ainda não foi carregado — clique em "Atualizar dados" acima.')
        return
    situacao = situacao.assign(faixa_risco=situacao["pct_tbo_voada"].apply(_faixa_risco))

    aba_geral, aba_diagonal, aba_os, aba_helice = st.tabs(
        ["Visão Geral", "Diagonal TBO/HSI", "Ordens de Serviço", "Hélices"]
    )
    with aba_geral:
        _aba_visao_geral(situacao, "motor", "motores_sit", historico=dados.get("motores_historico_situacao"))
    with aba_diagonal:
        _aba_diagonal(dados.get("motores_diagonal"), situacao, historico=dados.get("motores_historico_diagonal"))
    with aba_os:
        _aba_os(dados.get("motores_os"))
    with aba_helice:
        helice = dados.get("motores_helice")
        if helice is None or helice.empty:
            st.info("Sem dados de hélice carregados.")
        else:
            helice = helice.assign(faixa_risco=helice["pct_tbo_voada"].apply(_faixa_risco))
            _aba_visao_geral(helice, "hélice", "motores_hel")


def _aba_visao_geral(df, rotulo, key_sufixo, historico=None):
    total = len(df)
    por_condicao = df["condicao"].value_counts()
    aplicados = int(por_condicao.get("APL", 0))
    outra_condicao = total - aplicados
    vencidos = int((df["faixa_risco"] == "Vencido").sum())
    atencao = int((df["faixa_risco"] == "Atenção").sum())

    l1 = st.columns(5)
    _card_indicador(l1[0], "🔧", total, f"Total de {rotulo}s", "registros na planilha", INK)
    _card_indicador(l1[1], "✅", aplicados, "Aplicados", "instalados e aptos", STATUS["good"])
    _card_indicador(l1[2], "🛠️", outra_condicao, "Em manutenção/outra condição", "OS · REPARA · RECOLH · outros",
                     STATUS["critical"] if outra_condicao else STATUS["good"])
    _card_indicador(l1[3], "🟡", atencao, "Próximos do TBO/HSI", "80% a 99% de TBO voada", AMBER)
    _card_indicador(l1[4], "🔴", vencidos, "Vencidos", "100% ou mais de TBO voada",
                     STATUS["critical"] if vencidos else STATUS["good"])

    col1, col2 = st.columns([1, 1])
    with col1:
        st.caption("Distribuição por condição")
        contagem = df["condicao"].fillna("Não informado").value_counts().reset_index()
        contagem.columns = ["condicao", "quantidade"]
        cores = [COR_CONDICAO.get(c, SECONDARY) for c in contagem["condicao"]]
        fig = px.bar(contagem.sort_values("quantidade"), x="quantidade", y="condicao", orientation="h",
                     color="condicao", color_discrete_map=COR_CONDICAO)
        fig.update_traces(text=contagem.sort_values("quantidade")["quantidade"], textposition="outside", cliponaxis=False)
        fig.update_layout(xaxis_title="", yaxis_title="", showlegend=False)
        layout_grafico(fig, altura=230)
        st.plotly_chart(fig, width="stretch", key=f"{key_sufixo}_barras_condicao")

    with col2:
        st.caption("⚠️ Atenção imediata — mais críticos")
        criticos = df[df["faixa_risco"].isin(["Vencido", "Atenção"])].sort_values("pct_tbo_voada", ascending=False).head(8)
        if criticos.empty:
            st.success(f"Nenhum {rotulo} em atenção/vencido no momento.")
        else:
            linhas_html = ""
            for _, row in criticos.iterrows():
                cor = COR_FAIXA[row["faixa_risco"]]
                pct_txt = f"{row['pct_tbo_voada']:.0f}%" if pd.notna(row["pct_tbo_voada"]) else "—"
                linhas_html += (
                    f'<div style="padding:0.4rem 0;border-bottom:1px solid {LINE};font-size:0.92rem;">'
                    f'<strong>SN {row["sn"]}</strong> — FAB {row["matricula"] if pd.notna(row["matricula"]) else "—"} · '
                    f'<span style="color:{cor};font-weight:700;">{row["faixa_risco"]} ({pct_txt})</span>'
                    f"</div>"
                )
            st.markdown(
                f'<div style="background:{PANEL};border:1px solid {LINE};border-left:3px solid {AMBER};'
                f'border-radius:10px;padding:0.6rem 1rem;">{linhas_html}</div>',
                unsafe_allow_html=True,
            )

    st.markdown("##### Filtros")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        oms_f = st.multiselect("OM", sorted(df["om"].dropna().unique(), key=str), key=f"{key_sufixo}_f_om")
    with c2:
        condicoes_f = st.multiselect("Condição", sorted(df["condicao"].dropna().unique()), key=f"{key_sufixo}_f_condicao")
    with c3:
        faixa_f = st.multiselect("Situação", ["Vencido", "Atenção", "Normal", "Sem dado"], key=f"{key_sufixo}_f_faixa")
    with c4:
        busca = st.text_input("🔎 Busca (SN, PN, Matrícula)", key=f"{key_sufixo}_f_busca")

    filtrado = df.copy()
    if oms_f:
        filtrado = filtrado[filtrado["om"].isin(oms_f)]
    if condicoes_f:
        filtrado = filtrado[filtrado["condicao"].isin(condicoes_f)]
    if faixa_f:
        filtrado = filtrado[filtrado["faixa_risco"].isin(faixa_f)]
    if busca:
        b = busca.strip().lower()
        filtrado = filtrado[
            filtrado["sn"].astype(str).str.lower().str.contains(b, na=False)
            | filtrado["pn"].astype(str).str.lower().str.contains(b, na=False)
            | filtrado["matricula"].astype(str).str.lower().str.contains(b, na=False)
        ]
    st.caption(f"Exibindo {len(filtrado)} de {len(df)} registros")

    with st.expander("📋 Tabela completa"):
        tabela = _preparar_tabela(
            filtrado, colunas_data=["data_doc"], colunas_hora=["parcial_tso", "totais_tsn", "tbo"],
            colunas_fabricante=["fabricante"], colunas_pct=["pct_tbo_voada"],
        )
        colunas_ordem = [c for c in COLUNAS_SITUACAO_PRINCIPAIS + COLUNAS_SITUACAO_DETALHE if c in tabela.columns]
        tabela = tabela[colunas_ordem].rename(columns=NOMES_SITUACAO)
        tabela = filtro_colunas(tabela, key_prefix=key_sufixo)
        st.caption(f"{len(tabela)} linha(s) após os filtros por coluna.")
        st.dataframe(tabela, hide_index=True, width="stretch", height=420)
        csv = tabela.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Exportar (CSV)", csv, file_name=f"motores_{key_sufixo}.csv", mime="text/csv", key=f"{key_sufixo}_csv")

    if historico is not None:
        with st.expander("🕐 Evolução (histórico diário)"):
            secao_evolucao(
                historico, chave=["sn"], key_slider=f"{key_sufixo}_evolucao_slider",
                colunas_exibir=["sn", "matricula", "condicao", "pct_tbo_voada", "motivo"],
                nomes_colunas={
                    "sn": "SN", "matricula": "Matrícula", "condicao": "Condição",
                    "pct_tbo_voada": "% TBO voada", "motivo": "Motivo",
                },
                titulo="",
            )


def _aba_diagonal(df, situacao, historico=None):
    if df is None or df.empty:
        st.info("Sem dados de Diagonal carregados.")
        return

    eventos = df[df["evento"].isin(EVENTOS_TBO_HSI)].copy()
    # Unidade (OM) vem da Situação, cruzando pelo serial/SN — a Diagonal Nova
    # não tem essa coluna própria.
    mapa_unidade = situacao.drop_duplicates("sn").set_index("sn")["om"]
    eventos["unidade"] = eventos["serial"].map(mapa_unidade)

    hoje = pd.Timestamp.now().normalize()
    eventos["periodo"] = pd.to_datetime(dict(year=eventos["ano"], month=eventos["mes"], day=1))
    eventos["dias_ate"] = (eventos["periodo"] - hoje).dt.days

    vencidos = eventos[eventos["dias_ate"] < 0]
    prox_90 = eventos[(eventos["dias_ate"] >= 0) & (eventos["dias_ate"] <= 90)]
    prox_180 = eventos[(eventos["dias_ate"] > 90) & (eventos["dias_ate"] <= 180)]
    prox_365 = eventos[(eventos["dias_ate"] > 180) & (eventos["dias_ate"] <= 365)]

    l1 = st.columns(4)
    _card_indicador(l1[0], "🔴", len(vencidos), "Vencidos", "mês projetado já passou",
                     STATUS["critical"] if len(vencidos) else STATUS["good"])
    _card_indicador(l1[1], "⚠️", len(prox_90), "Próximos 90 dias", "TBO/HSI se aproximando", STATUS["critical"])
    _card_indicador(l1[2], "🟡", len(prox_180), "Próximos 180 dias", "planejar com antecedência", AMBER)
    _card_indicador(l1[3], "🔵", len(prox_365), "Próximos 365 dias", "horizonte de 1 ano", CYAN)

    st.markdown("##### Filtros")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        anv_f = st.multiselect("Aeronave", sorted(eventos["anv"].dropna().unique(), key=str), key="motores_diag_f_anv")
    with c2:
        unidade_f = st.multiselect("Unidade", sorted(eventos["unidade"].dropna().unique(), key=str), key="motores_diag_f_unidade")
    with c3:
        anos_f = st.multiselect("Ano", sorted(eventos["ano"].dropna().unique()), key="motores_diag_f_ano")
    with c4:
        evento_f = st.multiselect("Evento", sorted(eventos["evento"].dropna().unique()), key="motores_diag_f_evento")
    with c5:
        so_comentario = st.checkbox("Só com comentário", key="motores_diag_f_comentario")

    filtrado = eventos.copy()
    if anv_f:
        filtrado = filtrado[filtrado["anv"].isin(anv_f)]
    if unidade_f:
        filtrado = filtrado[filtrado["unidade"].isin(unidade_f)]
    if anos_f:
        filtrado = filtrado[filtrado["ano"].isin(anos_f)]
    if evento_f:
        filtrado = filtrado[filtrado["evento"].isin(evento_f)]
    if so_comentario:
        filtrado = filtrado[filtrado["comentario"].notna()]
    st.caption(f"Exibindo {len(filtrado)} de {len(eventos)} eventos TBO/HSI")

    # Janela sempre de 2 anos (ano atual + próximo), rolando sozinha
    # conforme o tempo passa — pedido do Wallace em 2026-07-15: "vamos
    # deixar sempre 2 anos na linha do tempo de tbo e hsi" (antes era um
    # intervalo fixo 2026-2030).
    ano_inicio_janela = datetime.now().year
    ano_fim_janela = ano_inicio_janela + 1
    st.markdown(f"##### Linha do tempo — TBO/HSI ({ano_inicio_janela} a {ano_fim_janela})")
    st.caption("Mesmo padrão da Diagonal de Manutenção — barra por mês, cor por tipo de evento, listrado = tem comentário.")
    linha_tempo = filtrado[(filtrado["ano"] >= ano_inicio_janela) & (filtrado["ano"] <= ano_fim_janela)].copy()
    if linha_tempo.empty:
        st.caption("Nenhum evento no período/filtro selecionado.")
    else:
        linha_tempo["rotulo"] = "SN " + linha_tempo["serial"].astype(str) + " — FAB " + linha_tempo["anv"].astype(str)
        linha_tempo["periodo_fim"] = linha_tempo["periodo"] + pd.DateOffset(months=1) - pd.Timedelta(days=1)
        linha_tempo["tem_comentario"] = linha_tempo["comentario"].notna().map({True: "Com comentário", False: "Sem comentário"})
        ordem_y = sorted(linha_tempo["rotulo"].unique(), reverse=True)
        fig = px.timeline(
            linha_tempo, x_start="periodo", x_end="periodo_fim", y="rotulo",
            color="evento", color_discrete_map={"TBO": AMBER, "TBO*": AMBER, "HSI": CYAN},
            pattern_shape="tem_comentario", pattern_shape_map={"Com comentário": "/", "Sem comentário": ""},
            hover_data={"comentario": True, "unidade": True, "evento": True, "rotulo": False, "tem_comentario": False},
            category_orders={"rotulo": ordem_y},
        )
        fig.add_vline(x=hoje, line_dash="dash", line_color=SECONDARY, annotation_text="hoje", annotation_position="top")
        fig.update_layout(xaxis_title="", yaxis_title="", legend_title="")
        layout_grafico(fig, altura=max(280, 28 * linha_tempo["rotulo"].nunique()))
        st.plotly_chart(fig, width="stretch", key="motores_diag_timeline")
        st.caption("Listrado (╱) = célula com comentário anexado na planilha original — passe o mouse pra ler.")

    with st.expander("📋 Tabela completa (todos os marcadores da grade, incl. fora de TBO/HSI)"):
        bruto = df.copy()
        bruto["unidade"] = bruto["serial"].map(mapa_unidade)
        tabela = _preparar_tabela(bruto).rename(columns={
            "serial": "Serial", "anv": "Aeronave", "unidade": "Unidade", "ano": "Ano", "mes": "Mês",
            "evento": "Marcador", "comentario": "Comentário",
        })[["Serial", "Aeronave", "Unidade", "Ano", "Mês", "Marcador", "Comentário"]].sort_values(["Ano", "Mês"])
        st.caption(
            "Inclui marcações \"X\"/\"1\"/números/texto livre cujo significado exato não foi confirmado "
            "com o Wallace — ver 00_Instrucoes/motores.md."
        )
        st.dataframe(tabela, hide_index=True, width="stretch", height=380)
        csv = tabela.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Exportar (CSV)", csv, file_name="motores_diagonal.csv", mime="text/csv", key="motores_diag_csv")

    if historico is not None:
        with st.expander("🕐 Evolução (histórico diário da projeção TBO/HSI)"):
            secao_evolucao(
                historico, chave=["serial", "ano", "mes"], key_slider="motores_diag_evolucao_slider",
                colunas_exibir=["serial", "anv", "ano", "mes", "evento", "comentario"],
                nomes_colunas={
                    "serial": "Serial", "anv": "Aeronave", "ano": "Ano", "mes": "Mês",
                    "evento": "Marcador", "comentario": "Comentário",
                },
                titulo="",
            )


def _aba_os(df):
    if df is None or df.empty:
        st.info("Sem ordens de serviço em andamento carregadas.")
        return

    df = df.assign(status_legivel=df["status"].map(NOMES_STATUS_OS).fillna(df["status"]))
    hoje = pd.Timestamp.now().normalize()
    df["atrasada"] = (df["data_fim_prev"].notna() & (df["data_fim_prev"] < hoje) & df["data_fim_real"].isna()).map({True: "Sim", False: "Não"})
    df["dias_no_status"] = (hoje - df["data_status"]).dt.days

    por_status = df["status"].value_counts()
    atrasadas = int((df["atrasada"] == "Sim").sum())

    l1 = st.columns(5)
    _card_indicador(l1[0], "📋", len(df), "OS em andamento", "total", INK)
    _card_indicador(l1[1], "🏭", int(por_status.get("INT", 0)), "Internadas", "em conserto", AMBER)
    _card_indicador(l1[2], "📥", int(por_status.get("REC", 0)), "Recebidas", "aguardando/recebidas", CYAN)
    _card_indicador(l1[3], "🔴", atrasadas, "Atrasadas", "passou do fim previsto",
                     STATUS["critical"] if atrasadas else STATUS["good"])
    _card_indicador(l1[4], "🔩", df["sn"].nunique(), "Motores envolvidos", "SNs distintos", SECONDARY)

    col1, col2 = st.columns(2)
    with col1:
        st.caption("Distribuição por Status (tempo médio no status, em dias)")
        resumo = df.groupby("status_legivel").agg(quantidade=("os", "count"), dias_medio=("dias_no_status", "mean")).reset_index()
        fig = px.bar(resumo.sort_values("quantidade"), x="quantidade", y="status_legivel", orientation="h",
                     color_discrete_sequence=[AMBER])
        fig.update_traces(
            text=[f"{q} · média {d:.0f}d" for q, d in zip(resumo.sort_values("quantidade")["quantidade"], resumo.sort_values("quantidade")["dias_medio"])],
            textposition="outside", cliponaxis=False,
        )
        fig.update_layout(xaxis_title="", yaxis_title="")
        layout_grafico(fig, altura=230)
        st.plotly_chart(fig, width="stretch", key="motores_os_status")

    with col2:
        st.caption("Distribuição por Unidade executante")
        contagem = df["unidade_exec"].fillna("Não informado").value_counts().reset_index()
        contagem.columns = ["unidade", "quantidade"]
        fig = px.bar(contagem.sort_values("quantidade"), x="quantidade", y="unidade", orientation="h",
                     color_discrete_sequence=[CYAN])
        fig.update_traces(text=contagem.sort_values("quantidade")["quantidade"], textposition="outside", cliponaxis=False)
        fig.update_layout(xaxis_title="", yaxis_title="")
        layout_grafico(fig, altura=230)
        st.plotly_chart(fig, width="stretch", key="motores_os_unidade")

    st.markdown("##### Filtros")
    c1, c2, c3 = st.columns(3)
    with c1:
        status_f = st.multiselect("Status", sorted(df["status_legivel"].dropna().unique()), key="motores_os_f_status")
    with c2:
        unidade_f = st.multiselect("Unidade executante", sorted(df["unidade_exec"].dropna().unique(), key=str), key="motores_os_f_unidade")
    with c3:
        so_atrasadas = st.checkbox("Só atrasadas", key="motores_os_f_atrasada")

    filtrado = df.copy()
    if status_f:
        filtrado = filtrado[filtrado["status_legivel"].isin(status_f)]
    if unidade_f:
        filtrado = filtrado[filtrado["unidade_exec"].isin(unidade_f)]
    if so_atrasadas:
        filtrado = filtrado[filtrado["atrasada"] == "Sim"]
    st.caption(f"Exibindo {len(filtrado)} de {len(df)} ordens de serviço")

    st.markdown("##### Tabela")
    tabela = _preparar_tabela(filtrado, colunas_data=[
        "data_status", "data_recebimento", "data_inicio_prev", "data_fim_prev", "data_inicio_real", "data_fim_real",
    ])
    colunas_ordem = [c for c in COLUNAS_OS_PRINCIPAIS + COLUNAS_OS_DETALHE if c in tabela.columns]
    tabela = tabela[colunas_ordem].rename(columns=NOMES_OS)
    tabela = filtro_colunas(tabela, key_prefix="motores_os")
    st.caption(f"{len(tabela)} linha(s) após os filtros por coluna.")
    st.dataframe(tabela, hide_index=True, width="stretch", height=340)
    csv = tabela.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar (CSV)", csv, file_name="motores_os.csv", mime="text/csv", key="motores_os_csv")
