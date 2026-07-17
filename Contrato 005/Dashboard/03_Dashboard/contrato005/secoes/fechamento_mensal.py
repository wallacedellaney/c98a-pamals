"""Página Fechamento Mensal — seletor de mês + 2 subseções: "Cômputo
Mensal" (ver 00_Instrucoes/computo_mensal.md) e "Atrasos" (ver
00_Instrucoes/atrasos.md — regras dadas pelo Wallace em 2026-07-10).
"""

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from contrato005.components.paleta import AMBER, LINE, PANEL, STATUS, layout_grafico
from contrato005.components.utils import ordenar_unicos

ABREV_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

SCRIPTS_PYTHON = Path(__file__).resolve().parents[3] / "05_Scripts" / "python"
if str(SCRIPTS_PYTHON) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PYTHON))

from contrato005.data.carregar_dados import carregar_computo_mensal
from calcular_computo_mensal import _tem_comentario_cancelamento

MESES_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def _opcoes_mes(dados):
    """Todos os meses (ano-mês) presentes no histórico de emergências — o
    padrão selecionado é sempre o MÊS ATUAL (pedido do Wallace em
    2026-07-14: "é para sempre aparecer no mes atual"), não um mês fixo; se
    não houver dado ainda, usa só o mês atual."""
    df = dados.get("emergencias_totais")
    padrao = pd.Timestamp.now().to_period("M")
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
    padrao = pd.Timestamp.now().to_period("M")
    indice_padrao = opcoes.index(padrao) if padrao in opcoes else len(opcoes) - 1

    mes_escolhido = st.selectbox(
        "Mês de referência",
        options=opcoes,
        index=indice_padrao,
        format_func=_formatar_mes,
        key="fecham_mes",
    )

    st.divider()
    aba_computo, aba_atrasos, aba_apresentacao, aba_ata = st.tabs(
        ["Cômputo Mensal", "Atrasos", "Apresentação (RMA)", "Ata de Reunião"]
    )

    with aba_computo:
        _computo_mensal(mes_escolhido)

    with aba_atrasos:
        _atrasos(dados, mes_escolhido)

    with aba_apresentacao:
        _apresentacao_rma(mes_escolhido)

    with aba_ata:
        _ata_reuniao(mes_escolhido)


def _mostrar_motivo_celula(matricula, dia, valor, df_motivos):
    if pd.isna(valor):
        st.info(f"FAB {matricula}, dia {dia}: ainda não decorrido — sem dado calculado.")
        return

    if valor == 1:
        st.markdown(
            f'<div style="background:{PANEL};border:1px solid {LINE};border-left:3px solid {STATUS["good"]};'
            f'border-radius:8px;padding:0.7rem 1rem;">'
            f'<strong>FAB {matricula}, dia {dia}:</strong> montada — sem negativação nesse dia.</div>',
            unsafe_allow_html=True,
        )
        return

    if df_motivos.empty:
        st.warning(f"FAB {matricula}, dia {dia}: desmontada, mas não achei o motivo (inesperado).")
        return

    motivos_aeronave = df_motivos[df_motivos["matricula"] == matricula].copy()
    motivos_aeronave["inicio_dia"] = pd.to_datetime(motivos_aeronave["periodo_no_mes_inicio"]).dt.day
    motivos_aeronave["fim_dia"] = pd.to_datetime(motivos_aeronave["periodo_no_mes_fim"]).dt.day
    encontrados = motivos_aeronave[(motivos_aeronave["inicio_dia"] <= dia) & (motivos_aeronave["fim_dia"] >= dia)]

    if encontrados.empty:
        st.warning(f"FAB {matricula}, dia {dia}: desmontada, mas não achei o motivo (inesperado).")
        return

    linhas_html = ""
    for _, m in encontrados.iterrows():
        cancelamento = m["data_cancelamento"] if pd.notna(m["data_cancelamento"]) else "ainda aberta"
        pn = m["pn"] if pd.notna(m.get("pn")) else "não informado"
        nomenclatura = m["nomenclatura"] if pd.notna(m.get("nomenclatura")) else "não informada"
        linhas_html += (
            f'<div style="margin-top:0.4rem;">'
            f'Emergência <strong>{m["numero_emergencia"]}</strong> ({m["tipo"]}) — '
            f'PN <strong>{pn}</strong> — {nomenclatura}<br>'
            f'aberta em {m["data_abertura"]}, informada em {m["data_info"]}, sem estoque.<br>'
            f'Negativado de {m["periodo_no_mes_inicio"]} até {m["periodo_no_mes_fim"]} · '
            f'cancelamento/conclusão: {cancelamento}</div>'
        )

    st.markdown(
        f'<div style="background:{PANEL};border:1px solid {LINE};border-left:3px solid {STATUS["critical"]};'
        f'border-radius:8px;padding:0.7rem 1rem;">'
        f'<strong>FAB {matricula}, dia {dia}: desmontada</strong>{linhas_html}</div>',
        unsafe_allow_html=True,
    )


def _detalhe_emergencia(registro):
    campos = {
        "numero_emergencia": "Emergência", "pn": "PN", "nomenclatura": "Nomenclatura",
        "matricula_aeronave": "Aeronave", "tpemg": "Tipo",
        "situacao": "Situação", "data_abertura": "Abertura", "data_info": "Informação",
        "prazo_entrega": "Prazo", "atendido_cancelado_fmt": "Cancelamento/conclusão",
        "dias_atraso": "Dias de atraso", "estoque": "Estoque",
    }
    linhas = []
    for campo, rotulo in campos.items():
        valor = registro.get(campo)
        if valor is None or (isinstance(valor, float) and pd.isna(valor)):
            texto = "Não informado"
        else:
            texto = str(valor)
        linhas.append(f'<div style="margin-top:0.3rem;"><strong>{rotulo}:</strong> {texto}</div>')
    st.markdown(
        f'<div style="background:{PANEL};border:1px solid {LINE};border-left:3px solid {AMBER};'
        f'border-radius:8px;padding:0.8rem 1rem;">{"".join(linhas)}</div>',
        unsafe_allow_html=True,
    )


def _atrasos(dados, mes_escolhido):
    st.subheader(f"Atrasos — {_formatar_mes(mes_escolhido)}")
    st.caption(
        "Só emergências do provedor VEE ONE (histórico completo já é filtrado assim). "
        "Ver 00_Instrucoes/atrasos.md."
    )

    df_totais = dados.get("emergencias_totais")
    if df_totais is None or df_totais.empty:
        st.info("Sem dados de emergências carregados ainda — ver aba \"Emergências Totais\".")
        return

    trabalho = df_totais.copy()
    trabalho["atendido_cancelado_dt"] = pd.to_datetime(trabalho["atendido_cancelado"], errors="coerce")
    n_invalidos = int((trabalho["atendido_cancelado"].notna() & trabalho["atendido_cancelado_dt"].isna()).sum())
    trabalho["atendido_cancelado_fmt"] = trabalho["atendido_cancelado_dt"].dt.strftime("%d/%m/%Y")

    # --- 1) Situação atual: o que está em aberto agora, não importa o mês ---
    st.markdown("##### Situação atual (em aberto agora)")
    abertas = trabalho[trabalho["em_aberto"]].copy()
    # Observação da Coordenadoria já indica cancelamento/"não é mais
    # necessário", só falta a baixa formal (Atd/cancelada) — pedido do
    # Wallace (2026-07-17): nem aparecer visualmente aqui, mesma regra do
    # Cômputo Mensal (ver computo_mensal.md).
    abertas = abertas[~abertas["obs_coordenadoria_fiscal"].apply(_tem_comentario_cancelamento)]
    total_abertas = len(abertas)
    atrasadas_agora = int((abertas["dias_atraso"] > 0).sum())
    no_prazo_agora = total_abertas - atrasadas_agora

    c1, c2, c3 = st.columns(3)
    c1.metric("Em aberto (VEE ONE)", total_abertas)
    c2.metric("Dentro do prazo", no_prazo_agora)
    c3.metric("Atrasadas", atrasadas_agora, delta_color="inverse")

    if total_abertas:
        tabela_abertas = abertas[[
            "numero_emergencia", "pn", "nomenclatura", "matricula_aeronave", "tpemg", "situacao",
            "data_abertura", "prazo_entrega", "dias_atraso",
        ]].rename(columns={
            "numero_emergencia": "Emergência", "pn": "PN", "nomenclatura": "Nomenclatura",
            "matricula_aeronave": "Aeronave", "tpemg": "Tipo",
            "situacao": "Situação", "data_abertura": "Abertura", "prazo_entrega": "Prazo",
            "dias_atraso": "Dias de atraso",
        }).sort_values("Dias de atraso", ascending=False)
        st.dataframe(tabela_abertas, hide_index=True, width="stretch", height=min(35 * (len(tabela_abertas) + 1) + 3, 320))
    else:
        st.success("Nenhuma emergência em aberto no momento.")

    st.divider()

    # --- 2) Entregas concluídas/canceladas dentro do mês de referência,
    # não importa quando abriu, aeronave ou tipo (regra do Wallace, 2026-07-10) ---
    st.markdown("##### Entregas no mês de referência (concluídas ou canceladas)")
    st.caption(
        "Todo item VEE ONE cancelado ou concluído dentro do mês — não importa quando abriu, "
        "a aeronave ou o tipo de emergência."
    )

    inicio_mes = mes_escolhido.start_time
    fim_mes = mes_escolhido.end_time
    concluidas_mes = trabalho[
        (~trabalho["em_aberto"])
        & (trabalho["atendido_cancelado_dt"] >= inicio_mes)
        & (trabalho["atendido_cancelado_dt"] <= fim_mes)
    ].copy()

    total_previstas = len(concluidas_mes)
    no_prazo = int((concluidas_mes["dias_atraso"] <= 0).sum())
    atrasadas = total_previstas - no_prazo
    pct = (100 * no_prazo / total_previstas) if total_previstas else 0.0

    resumo_df = pd.DataFrame([{
        "Período de apuração": f"{inicio_mes.strftime('%d/%m')} - {fim_mes.strftime('%d/%m')}",
        "Total de entregas previstas": total_previstas,
        "Entregas no Prazo": no_prazo,
        "QTD Mensal (%)": f"{pct:.2f}".replace(".", ",") + "%",
    }])
    st.dataframe(resumo_df, hide_index=True, width="stretch")

    if n_invalidos:
        st.caption(
            f"⚠️ {n_invalidos} registro(s) com data de cancelamento/conclusão inválida "
            "(texto em vez de data, ex.: \"verificar data\") — não entraram em nenhuma contagem por mês."
        )

    if total_previstas == 0:
        st.info("Nenhuma emergência concluída/cancelada nesse mês.")
        return

    col1, col2 = st.columns([1, 2])
    with col1:
        contagem = pd.DataFrame({
            "situação": ["No prazo", "Atrasado"],
            "quantidade": [no_prazo, atrasadas],
        })
        fig = px.pie(
            contagem, names="situação", values="quantidade", hole=0.55,
            color="situação", color_discrete_map={"No prazo": STATUS["good"], "Atrasado": STATUS["critical"]},
        )
        fig.update_traces(textinfo="value+percent", textfont_size=12)
        layout_grafico(fig, altura=230)
        st.plotly_chart(fig, width="stretch")

    concluidas_mes["situacao_prazo"] = concluidas_mes["dias_atraso"].apply(lambda d: "No prazo" if d <= 0 else "Atrasado")

    with col2:
        c1, c2, c3 = st.columns(3)
        situacao_f = c1.selectbox("Situação", ["Todas", "No prazo", "Atrasado"], key="atrasos_f_situacao")
        tipo_f = c2.multiselect("Tipo", ordenar_unicos(concluidas_mes["tpemg"]), key="atrasos_f_tipo")
        busca = c3.text_input("🔎 Busca (emergência, aeronave)", key="atrasos_f_busca")

    filtrado = concluidas_mes.copy()
    if situacao_f != "Todas":
        filtrado = filtrado[filtrado["situacao_prazo"] == situacao_f]
    if tipo_f:
        filtrado = filtrado[filtrado["tpemg"].isin(tipo_f)]
    if busca:
        b = busca.strip().lower()
        filtrado = filtrado[
            filtrado["numero_emergencia"].astype(str).str.lower().str.contains(b, na=False)
            | filtrado["matricula_aeronave"].astype(str).str.lower().str.contains(b, na=False)
        ]

    st.caption(f"Exibindo {len(filtrado)} de {total_previstas} entregas do mês")
    tabela = filtrado[[
        "numero_emergencia", "pn", "nomenclatura", "matricula_aeronave", "tpemg", "data_abertura",
        "prazo_entrega", "atendido_cancelado_fmt", "dias_atraso", "situacao_prazo",
    ]].rename(columns={
        "numero_emergencia": "Emergência", "pn": "PN", "nomenclatura": "Nomenclatura",
        "matricula_aeronave": "Aeronave", "tpemg": "Tipo",
        "data_abertura": "Abertura", "prazo_entrega": "Prazo",
        "atendido_cancelado_fmt": "Cancelamento/conclusão", "dias_atraso": "Dias de atraso",
        "situacao_prazo": "Situação",
    })
    evento = st.dataframe(
        tabela, hide_index=True, width="stretch", height=min(35 * (len(tabela) + 1) + 3, 420),
        on_select="rerun", selection_mode="single-row", key="atrasos_tabela_mes",
    )
    linhas_sel = evento.selection.get("rows", []) if evento else []
    if linhas_sel:
        _detalhe_emergencia(filtrado.iloc[linhas_sel[0]].to_dict())

    csv = tabela.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar (CSV)", csv, file_name=f"atrasos_{mes_escolhido}.csv", mime="text/csv")


def _apresentacao_rma(mes_escolhido):
    st.subheader(f"Apresentação (RMA) — {_formatar_mes(mes_escolhido)}")
    st.caption(
        "Gera a apresentação de PowerPoint da RMA do mês, puxando tudo da nossa própria plataforma "
        "(Cômputo Mensal, Reparáveis, Empréstimos, Pagamentos, Atrasos) — a partir do layout de "
        "`04_Relatorios/RMA_referencia.pptx`. Ver 00_Instrucoes/apresentacao_rma.md. Só o download — "
        "não sobe pro Drive sozinho (a conta de serviço não tem cota própria de armazenamento)."
    )

    ano, mes = mes_escolhido.year, mes_escolhido.month
    if st.button("📊 Gerar Apresentação (RMA)", key="apresentacao_gerar", width="stretch"):
        with st.spinner("Montando a apresentação..."):
            try:
                from shared import drive_sync
                drive_sync.garantir_credencial_arquivo()
                import gerar_apresentacao_rma
                nome_arquivo = f"RMA_{MESES_PT[mes - 1]}_{ano}.pptx"
                caminho_saida = gerar_apresentacao_rma.DADOS_TRATADOS / "atas" / nome_arquivo
                gerar_apresentacao_rma.gerar_apresentacao(ano, mes, caminho_saida)
                st.session_state["apresentacao_gerada_caminho"] = str(caminho_saida)
                st.session_state["apresentacao_gerada_nome"] = nome_arquivo
            except Exception as e:
                st.error(f"Falha ao gerar a apresentação: {e}")

    if st.session_state.get("apresentacao_gerada_caminho"):
        caminho = Path(st.session_state["apresentacao_gerada_caminho"])
        if caminho.exists():
            st.success("Apresentação gerada.")
            with open(caminho, "rb") as f:
                st.download_button(
                    "⬇️ Baixar Apresentação (.pptx)", f.read(),
                    file_name=st.session_state["apresentacao_gerada_nome"],
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                )


def _ata_reuniao(mes_escolhido):
    st.subheader(f"Ata de Reunião — {_formatar_mes(mes_escolhido)}")
    st.caption(
        "Gera automaticamente um rascunho editável (.docx) da Ata de Reunião mensal, buscando sempre no Drive: "
        "o áudio da reunião (transcrito localmente, ~10 min na primeira vez do mês) e a planilha oficial "
        "'RMA em andamento' (horas de voo, MMAM/Pontuação/IFD, valores já com o Índice de Desempenho aplicado). "
        "Reparáveis, Empréstimos, Pagamentos e a apuração de entregas vêm da nossa própria base tratada. "
        "Ver 00_Instrucoes/ata_reuniao.md."
    )
    st.warning(
        "⚠️ Seções que dependem de julgamento humano (abertura/objetivo, discussão dos Módulos 2/3, MAPEM, "
        "encerramento e a tabela de Pendências) ficam marcadas '[revisar a partir da transcrição]' — a transcrição "
        "completa vai anexada ao final do documento. Revisar e assinar somente depois de completar essas seções."
    )

    ano, mes = mes_escolhido.year, mes_escolhido.month
    if st.button("📝 Gerar Ata de Reunião", key="ata_gerar", width="stretch"):
        with st.spinner("Buscando áudio e planilha no Drive, transcrevendo (pode levar ~10 min na primeira vez deste mês) e montando o documento..."):
            try:
                from shared import drive_sync
                drive_sync.garantir_credencial_arquivo()
                import gerar_ata_reuniao
                nome_arquivo = f"Ata_RMA_{MESES_PT[mes - 1]}_{ano}_rascunho.docx"
                caminho_saida = gerar_ata_reuniao.DADOS_TRATADOS / "atas" / nome_arquivo
                gerar_ata_reuniao.gerar_ata(ano, mes, caminho_saida)
                st.session_state["ata_gerada_caminho"] = str(caminho_saida)
                st.session_state["ata_gerada_nome"] = nome_arquivo
            except Exception as e:
                st.error(f"Falha ao gerar a Ata: {e}")

    if st.session_state.get("ata_gerada_caminho"):
        caminho = Path(st.session_state["ata_gerada_caminho"])
        if caminho.exists():
            st.success("Ata gerada — revisar as seções marcadas antes de assinar.")
            with open(caminho, "rb") as f:
                st.download_button(
                    "⬇️ Baixar Ata (.docx)", f.read(),
                    file_name=st.session_state["ata_gerada_nome"],
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )


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
    st.caption(
        "Clique numa célula pra ver o motivo da negativação (ou confirmar que ficou montada). "
        "Aeronaves fora do contrato aparecem em baixo, sem pontuação (linhas em branco)."
    )
    pivot = df_matriz.pivot(index="matricula", columns="dia", values="montada")

    mapa_rotulo = {}
    fins_de_semana = set()
    for dia in pivot.columns:
        wd = date(mes_escolhido.year, mes_escolhido.month, int(dia)).weekday()
        rotulo = f"{dia} {ABREV_SEMANA[wd]}"
        mapa_rotulo[dia] = rotulo
        if wd >= 5:
            fins_de_semana.add(rotulo)

    # % de montadas por dia (a mesma média usada no gráfico de evolução
    # acima) — pedido do Wallace: "coloca a porcetnagem em baixo de cada
    # dia", uma linha resumo no final da própria matriz.
    percentual_dia = df_matriz.dropna(subset=["montada"]).groupby("dia")["montada"].mean().mul(100)
    pivot.loc["% Montadas"] = percentual_dia

    # Aeronaves fora do contrato aparecem como linha em branco (sem
    # pontuação, sem preencher nada) — pedido do Wallace: "ajeitar as
    # aeronaves fora do contrato, coloca em baixo, sem preencher nada".
    aeronaves_fora = resumo["aeronaves_fora_listadas"]
    for m in aeronaves_fora:
        pivot.loc[m] = pd.Series(float("nan"), index=pivot.columns, dtype="float64")

    pivot = pivot.rename(columns=mapa_rotulo)

    def _cor_linha(row):
        matricula = row.name
        estilos = []
        for coluna, v in row.items():
            if matricula == "% Montadas":
                estilos.append("font-weight: 700; border-top: 2px solid " + LINE + ";")
            elif matricula in aeronaves_fora:
                estilos.append("color: " + STATUS["critical"] + "44;")
            elif pd.isna(v):
                estilos.append(f"background-color: {LINE}" if coluna in fins_de_semana else "")
            else:
                cor = STATUS["good"] if v == 1 else STATUS["critical"]
                estilos.append(f"background-color: {cor}55")
        return estilos

    styler = pivot.style.format(precision=0, na_rep="").apply(_cor_linha, axis=1)
    styler = styler.format(lambda v: "" if pd.isna(v) else f"{v:.0f}%", subset=pd.IndexSlice[["% Montadas"], :])

    altura_tabela = min(35 * (len(pivot) + 1) + 3, 700)
    colunas_config = {
        coluna: st.column_config.NumberColumn(width="small") for coluna in pivot.columns
    }
    evento = st.dataframe(
        styler, width="stretch", height=altura_tabela,
        column_config=colunas_config,
        on_select="rerun", selection_mode="single-cell", key="computo_matriz_selecao",
    )

    celulas = evento.selection.get("cells", []) if evento else []
    if celulas:
        linha_idx, coluna_rotulo = celulas[0]
        matricula_sel = pivot.index[linha_idx]
        # Linha de % ou aeronave fora do contrato não têm motivo de
        # negativação — não faz sentido nenhum pra essas linhas.
        if matricula_sel != "% Montadas" and matricula_sel not in aeronaves_fora:
            dia_sel = int(coluna_rotulo.split()[0])
            valor_sel = pivot.iloc[linha_idx][coluna_rotulo]
            _mostrar_motivo_celula(matricula_sel, dia_sel, valor_sel, df_motivos)

    st.markdown("##### Justificativa das negativações")
    if df_motivos.empty:
        st.success("Nenhuma negativação no período — todas as aeronaves pontuadas ficaram montadas.")
    else:
        tabela = df_motivos.rename(columns={
            "matricula": "Matrícula", "numero_emergencia": "Emergência", "pn": "PN",
            "nomenclatura": "Nomenclatura", "tipo": "Tipo",
            "data_abertura": "Data abertura", "data_info": "Data informação", "estoque": "Estoque",
            "inicio_negativacao": "Início negativação", "data_cancelamento": "Cancelamento/conclusão",
            "periodo_no_mes_inicio": "Negativado de", "periodo_no_mes_fim": "Negativado até",
        }).fillna("ainda aberto")
        st.dataframe(tabela, hide_index=True, width="stretch")

    csv = df_matriz.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar matriz (CSV)", csv,
                        file_name=f"computo_mensal_{mes_escolhido}.csv", mime="text/csv")
