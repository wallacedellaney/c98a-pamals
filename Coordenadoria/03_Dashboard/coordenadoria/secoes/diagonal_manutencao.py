"""Diagonal de Manutenção — linha do tempo (Gantt) de indisponibilidade por
aeronave. Combina duas fontes, lado a lado na mesma linha por aeronave:
* "Real (hoje)" — situação de verdade, tirada do relatório mais recente da
  Disponibilidade Diária (situação != DI/DO), até a data prevista (DPE) ou
  +14 dias se não houver previsão.
* "Programado" — projeção futura de inspeções, tirada da Diagonal de
  Manutenção de cada operador.
Ver 00_Instrucoes/diagonal_manutencao.md.
"""

from datetime import timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from shared import horario
from coordenadoria.components.filtros import filtro_colunas
from coordenadoria.components.paleta import (
    AMBER, CATEGORICA, COR_SITUACAO, CYAN, INK, LINE, NOME_SITUACAO, PANEL, SECONDARY, layout_grafico,
)
from coordenadoria.utils import atualizar_dados_diagonal_manutencao

FONTE_REAL = "Real (hoje)"
FONTE_PROGRAMADO = "Programado"
FONTE_AJUSTADO = "Programado (ajustado)"
FONTE_MOTOR = "Motor (planilha)"
PATTERN_FONTE = {FONTE_REAL: "", FONTE_PROGRAMADO: "/", FONTE_AJUSTADO: "x"}
COR_OPERADOR_MOTOR = {"TBO": AMBER, "HSI": CYAN, "Simulação": CATEGORICA[2], "Sem evento": "rgba(0,0,0,0)"}

# Frota "dentro do contrato" — pré-selecionada por padrão no filtro de
# Aeronave (pedido do Wallace em 2026-07-14), pra não precisar marcar toda
# vez; continua editável (dá pra tirar/incluir depois, é só o valor
# inicial). Ver 00_Instrucoes/computo_mensal.md pra aeronaves fora do
# contrato (2726, 2730, 2732, 2734) e sem condições (2701, 2706, 2724),
# que ficam de fora dessa lista de propósito.
AERONAVES_PADRAO = {
    "2702", "2703", "2704", "2708", "2709", "2720", "2719", "2721", "2722", "2723",
    "2727", "2728", "2729", "2731", "2733", "2736", "2737", "2738", "2739", "2740",
    "2741", "2742", "2743",
}


def _inicio_real(disp_aeronaves, matricula, situacao_atual, data_mais_recente):
    """Anda pra trás no histórico já carregado de Disponibilidade Diária
    (vários dias, não só o relatório de hoje) procurando o primeiro dia em
    que a aeronave já aparecia com essa MESMA situação — pra não mostrar
    toda indisponibilidade real como se tivesse começado hoje (bug achado
    pelo Wallace em 2026-07-16: "vi que o inicio ta sempre o dia atual").
    Se a situação já existia no dia mais antigo carregado, não dá pra saber
    o início de verdade (pode ser bem anterior a isso) — sinalizado com
    `incerto=True`, sem inventar uma data anterior ao que temos."""
    hist = disp_aeronaves[
        (disp_aeronaves["matricula"] == matricula) & (disp_aeronaves["data_referencia"] <= data_mais_recente)
    ].sort_values("data_referencia")
    inicio = data_mais_recente
    incerto = True
    for data, sit in zip(hist["data_referencia"][::-1], hist["situacao"][::-1]):
        if sit != situacao_atual:
            incerto = False
            break
        inicio = data
    return inicio, incerto


def _eventos_reais(disp_aeronaves):
    """Constrói os eventos "de verdade" a partir do relatório mais recente da
    Disponibilidade Diária — aeronaves com situação != DI/DO (ver
    00_Instrucoes/disponibilidade_diaria.md pro significado de cada código).
    `periodo_inicio` é o primeiro dia real (dentro do histórico carregado)
    em que a aeronave já estava nessa situação, não sempre "hoje"."""
    if disp_aeronaves is None or disp_aeronaves.empty:
        return pd.DataFrame(columns=["operador", "aeronave", "periodo_inicio", "periodo_fim", "motivo", "confianca", "fonte"])

    ultima_data = disp_aeronaves["data_referencia"].max()
    hoje_snapshot = disp_aeronaves[disp_aeronaves["data_referencia"] == ultima_data]
    indisponiveis = hoje_snapshot[~hoje_snapshot["situacao"].isin(["DI", "DO"])].copy()
    if indisponiveis.empty:
        return pd.DataFrame(columns=["operador", "aeronave", "periodo_inicio", "periodo_fim", "motivo", "confianca", "fonte"])

    def _fim(row):
        if pd.notna(row["dpe_data"]):
            return row["dpe_data"]
        return row["data_referencia"] + timedelta(days=14)

    def _inicio_e_incerteza(row):
        return _inicio_real(disp_aeronaves, row["matricula"], row["situacao"], row["data_referencia"])

    def _motivo(row, incerto):
        base = row["situacao"]
        if pd.notna(row["ocorrencia"]) and str(row["ocorrencia"]).strip():
            base = f"{row['situacao']}: {row['ocorrencia']}"
        if incerto:
            base += " (em aberto desde antes do início do nosso histórico — data real pode ser anterior)"
        if pd.isna(row["dpe_data"]):
            base += " (sem previsão de retorno — +14d de referência)"
        return base

    inicio_incerteza = indisponiveis.apply(_inicio_e_incerteza, axis=1, result_type="expand")
    indisponiveis["periodo_inicio"] = inicio_incerteza[0]
    indisponiveis["_incerto"] = inicio_incerteza[1]
    indisponiveis["periodo_fim"] = indisponiveis.apply(_fim, axis=1)
    indisponiveis["motivo"] = indisponiveis.apply(lambda r: _motivo(r, r["_incerto"]), axis=1)
    indisponiveis["operador"] = indisponiveis["unidade"]
    indisponiveis["confianca"] = "Real"
    indisponiveis["fonte"] = FONTE_REAL
    return indisponiveis.rename(columns={"matricula": "aeronave"})[
        ["operador", "aeronave", "periodo_inicio", "periodo_fim", "motivo", "confianca", "fonte"]
    ]


EVENTOS_TBO_HSI_MOTOR = {"TBO", "TBO*", "HSI"}


def _eventos_motor(motores_diagonal):
    """Eventos de TBO/HSI vindos da planilha de Motores (Diagonal Nova) —
    aparecem direto na Diagonal de Manutenção das aeronaves, sempre a
    partir da fonte fixa (não a simulação). Pedido do Wallace em
    2026-07-15: "essas informacoes sao sempre vinculada com a planilha de
    motores" + "colocar um quadradinho escrito dentro hsi ou tbo pra
    visualização" — por isso o texto "TBO"/"HSI" vai escrito dentro da
    própria barra (`texto_evento`), e a cor segue o tipo de evento (âmbar/
    ciano), não o operador. Ver 00_Instrucoes/motores.md."""
    colunas = ["operador", "aeronave", "periodo_inicio", "periodo_fim", "motivo", "confianca", "fonte", "texto_evento"]
    if motores_diagonal is None or motores_diagonal.empty:
        return pd.DataFrame(columns=colunas)

    eventos = motores_diagonal[motores_diagonal["evento"].isin(EVENTOS_TBO_HSI_MOTOR)].copy()
    # ANV vazio na fonte (célula `False`) sobrevive ao ida-e-volta pelo
    # Excel como 0 — nenhuma aeronave da frota tem matrícula 0, então é
    # seguro tratar como "sem aeronave vinculada" e descartar.
    eventos = eventos[eventos["anv"].apply(lambda v: pd.notna(v) and v is not False and v != 0)]
    if eventos.empty:
        return pd.DataFrame(columns=colunas)

    eventos["periodo_inicio"] = pd.to_datetime(dict(year=eventos["ano"], month=eventos["mes"], day=1))
    eventos["periodo_fim"] = eventos["periodo_inicio"] + pd.DateOffset(months=1) - pd.Timedelta(days=1)
    eventos["aeronave"] = eventos["anv"].astype(int).astype(str)
    eventos["texto_evento"] = eventos["evento"].str.rstrip("*")
    eventos["operador"] = eventos["texto_evento"]
    eventos["motivo"] = eventos.apply(
        lambda r: f"Motor SN {r['serial']} — {r['evento']}" + (f": {r['comentario']}" if pd.notna(r["comentario"]) else ""),
        axis=1,
    )
    eventos["confianca"] = "Motores (planilha)"
    eventos["fonte"] = FONTE_MOTOR
    return eventos[colunas]


def _mapa_situacao_hoje(disp_aeronaves):
    """Situação de hoje (DI/DO/II/IN/ITR/IS/IP) por matrícula, a partir do
    relatório mais recente da Disponibilidade Diária. Pedido do Wallace em
    2026-07-15: "vamos colcoar a condicao da aeronave no dia ... colcoando
    di, do, IN, IS (informacoes da disp)"."""
    if disp_aeronaves is None or disp_aeronaves.empty:
        return {}
    ultima_data = disp_aeronaves["data_referencia"].max()
    hoje_snapshot = disp_aeronaves[disp_aeronaves["data_referencia"] == ultima_data]
    return dict(zip(hoje_snapshot["matricula"].astype(str), hoje_snapshot["situacao"]))


def _previsao_situacao_7dias(disp_aeronaves, df_programado, aeronaves_alvo, hoje):
    """Previsão da situação (DI/DO/II/IN/ITR/IS/IP) de cada aeronave-alvo
    para os próximos 7 dias (hoje + 6) — pedido do Wallace em 2026-07-16,
    substitui o resumo mensal de eventos ("ficou ruim"): "pegar a mensagem
    diaria analisar ela e colocar ali a previsao po dia com base na mensagem
    diaria, base vai ser sempre ela, se tiver previsao de inspcao programado
    (diagonal) pode inserir tb".

    A base é sempre a situação real do relatório mais recente (mensagem
    diária) — dia 0 (hoje) usa exatamente o código do relatório, sem
    nenhuma suposição. Pros dias seguintes, 2 regras de projeção (nossas,
    pra estimar o que a mensagem ainda não cobre — o relatório do dia
    seguinte, quando chegar, é sempre a fonte real):
    1. Aeronave indisponível hoje mantém o mesmo código até a Data Prevista
       de Entrega (DPE, ou +14 dias de referência se não houver) — no dia
       seguinte à DPE, assume que volta a "DI" (disponibilidade plena).
    2. Aeronave disponível hoje (DI/DO) que tiver uma inspeção programada
       da Diagonal de Manutenção (fonte "Programado") cobrindo aquele dia
       passa a "II" (indisponível por manutenção programada) nesse dia."""
    dias = [hoje + pd.Timedelta(days=i) for i in range(7)]

    situacao_atual, retorno_previsto = {}, {}
    if disp_aeronaves is not None and not disp_aeronaves.empty:
        ultima_data = disp_aeronaves["data_referencia"].max()
        hoje_snapshot = disp_aeronaves[disp_aeronaves["data_referencia"] == ultima_data].copy()
        hoje_snapshot["matricula"] = hoje_snapshot["matricula"].astype(str)
        for _, row in hoje_snapshot.iterrows():
            matricula = row["matricula"]
            situacao_atual[matricula] = row["situacao"]
            if row["situacao"] not in ("DI", "DO"):
                retorno_previsto[matricula] = (
                    row["dpe_data"] if pd.notna(row["dpe_data"]) else row["data_referencia"] + timedelta(days=14)
                )

    eventos_programados = {}
    if df_programado is not None and not df_programado.empty:
        for aeronave, grupo in df_programado.groupby("aeronave"):
            eventos_programados[aeronave] = list(zip(grupo["periodo_inicio"], grupo["periodo_fim"]))

    def _tem_inspecao_programada(aeronave, dia):
        return any(inicio <= dia <= fim for inicio, fim in eventos_programados.get(aeronave, []))

    linhas = []
    for dia in dias:
        for aeronave in aeronaves_alvo:
            situacao_base = situacao_atual.get(aeronave, "DI")
            if dia == hoje:
                situacao = situacao_base
            elif aeronave in retorno_previsto and pd.Timestamp(dia) <= pd.Timestamp(retorno_previsto[aeronave]):
                # ainda dentro da previsão de retorno (DPE ou +14d) — mantém o
                # mesmo código de indisponibilidade de hoje.
                situacao = situacao_base
            elif situacao_base in ("DI", "DO"):
                # já estava disponível hoje (com ou sem restrição) — sem
                # informação nova, continua exatamente como estava, não reseta
                # pra "DI" (evita apagar a restrição "DO" sem motivo).
                situacao = situacao_base
            else:
                # estava indisponível e já passou da previsão de retorno —
                # assume disponibilidade plena.
                situacao = "DI"
            if situacao in ("DI", "DO") and _tem_inspecao_programada(aeronave, dia):
                situacao = "II"
            linhas.append({"dia": dia, "aeronave": aeronave, "situacao": situacao})

    return pd.DataFrame(linhas)


def _dados_motor_aeronave(aeronave, diagonal_meta, situacao):
    """Motor(es) vinculado(s) a uma aeronave — cruza pelo ANV da Diagonal
    Nova (metadados de planejamento: Hr disponível, Voo mensal, Mês
    disponível), com condição/%TBO voada vindo da Situação (SILOMS) via SN.
    Ver 00_Instrucoes/motores.md."""
    if diagonal_meta is None or diagonal_meta.empty:
        return []
    try:
        anv_num = float(aeronave)
    except (TypeError, ValueError):
        return []
    linhas = diagonal_meta[diagonal_meta["anv"] == anv_num]
    resultado = []
    for _, meta in linhas.iterrows():
        sit = situacao[situacao["sn"] == meta["serial"]] if situacao is not None and not situacao.empty else pd.DataFrame()
        resultado.append({
            "serial": meta["serial"],
            "hr_disp": meta["hr_disp"],
            "voo_mensal": meta["voo_mensal"],
            "mes_disp": meta["mes_disp"],
            "condicao": sit.iloc[0]["condicao"] if not sit.empty else None,
            "pct_tbo_voada": sit.iloc[0]["pct_tbo_voada"] if not sit.empty else None,
        })
    return resultado


def _rotulo_motor(aeronave, diagonal_meta, situacao):
    """Resumo curto do motor pra escrever direto no rótulo da aeronave no
    Gantt (pedido do Wallace em 2026-07-15: "ta dificil de ver a
    informacao do motor na diagonal geral, deixa de forma mais visivel,
    escreve la") — sem precisar abrir o expander pra ver o básico (SN e
    %TBO); o expander continua só pra simular horas de voo."""
    motores_aer = _dados_motor_aeronave(aeronave, diagonal_meta, situacao)
    if not motores_aer:
        return "sem motor vinculado"
    partes = []
    for m in motores_aer:
        if pd.notna(m["pct_tbo_voada"]):
            partes.append(f"SN {m['serial']} ({m['pct_tbo_voada']:.0f}% TBO)")
        else:
            partes.append(f"SN {m['serial']}")
    return " · ".join(partes)


NOME_SITUACAO_CURTO = {
    "DI": "Disponível", "DO": "Disp. c/ restrição", "II": "Manut. programada",
    "IN": "Manut. não programada", "ITR": "Aguardando transporte",
    "IS": "Aguardando suprimento", "IP": "Indisp. prolongada",
}


def _secao_detalhe_aeronave(aeronaves, diagonal_meta, situacao, hoje, rac_aeronaves, rac_pendencias, mapa_situacao_hoje):
    """Painel discreto — 1 expander por aeronave (colapsado por padrão),
    consolidando: motor vinculado (+ simulação "e se eu voar mais/menos
    por mês"), pendências do RAC e situação de hoje (Disponibilidade
    Diária). Pedido do Wallace em 2026-07-15: "pensem em ser clicavel a
    coluna Y (quadradinho com a aeronave clicavel), ai ali se tiver
    faltando algum item aparece tb ... a gente soma a [informação de]
    disponibilidade colocando di, do, in, is" + pedido original de
    2026-07-15 sobre o simulador de horas de voo (mantido aqui dentro).
    A planilha de Motores (Diagonal Nova) continua sempre fixa, só a
    simulação de voo é editável (não grava em nenhum arquivo)."""
    with st.expander("🔍 Detalhe da aeronave (motor, RAC, disponibilidade)"):
        eventos_ajustados = []
        cols = st.columns(3)
        for i, aeronave in enumerate(aeronaves):
            motores_aer = _dados_motor_aeronave(aeronave, diagonal_meta, situacao) if diagonal_meta is not None else []
            situacao_hoje = mapa_situacao_hoje.get(aeronave)
            with cols[i % 3]:
                with st.expander(f"🔍 FAB {aeronave}"):
                    if situacao_hoje:
                        st.caption(f"**Situação hoje:** {situacao_hoje} — {NOME_SITUACAO_CURTO.get(situacao_hoje, situacao_hoje)}")
                    else:
                        st.caption("**Situação hoje:** sem relatório de Disponibilidade Diária pra essa aeronave.")

                    if rac_pendencias is not None and not rac_pendencias.empty:
                        pend_aer = rac_pendencias[rac_pendencias["matricula"].astype(str) == str(aeronave)]
                        if pend_aer.empty:
                            st.caption("**RAC:** sem pendências.")
                        else:
                            st.caption(f"**RAC:** {len(pend_aer)} item(ns) faltando (sem DPE — o RAC não tem essa informação):")
                            for _, p in pend_aer.sort_values("quantidade_faltante", ascending=False).head(6).iterrows():
                                st.caption(f"　• {p['pn']} — {p['nomenclatura']} ({int(p['quantidade_faltante'])} un.)")
                            if len(pend_aer) > 6:
                                st.caption(f"　… mais {len(pend_aer) - 6} item(ns), ver aba RAC.")

                    if not motores_aer:
                        st.caption("**Motor:** sem motor vinculado nos dados de planejamento (Diagonal Nova).")
                        continue
                    for m in motores_aer:
                        pct_txt = f" · {m['pct_tbo_voada']:.0f}% TBO voada" if pd.notna(m["pct_tbo_voada"]) else ""
                        st.caption(f"**Motor:** SN {m['serial']} — {m['condicao'] or '—'}{pct_txt}")
                        if pd.isna(m["voo_mensal"]) or pd.isna(m["hr_disp"]):
                            st.caption("Sem dado de planejamento (Voo mensal/Hr disponível) pra esse motor.")
                            continue
                        st.caption(
                            f"Voo mensal atual: {m['voo_mensal']:.1f} h/mês · Hr disponível: {m['hr_disp']:.0f} h · "
                            f"Previsão original: {m['mes_disp']:.1f} mês(es)"
                        )
                        novo_voo = st.number_input(
                            "Simular horas de voo por mês", min_value=1.0, value=float(m["voo_mensal"]), step=1.0,
                            key=f"diagonal_voo_mensal_{aeronave}_{m['serial']}",
                        )
                        if abs(novo_voo - m["voo_mensal"]) > 0.01:
                            novos_meses = m["hr_disp"] / novo_voo
                            nova_data = hoje + pd.DateOffset(days=round(novos_meses * 30.44))
                            st.info(
                                f"Nova previsão: **{novos_meses:.1f} mês(es)** → ~{nova_data.strftime('%d/%m/%Y')} "
                                f"(original: {m['mes_disp']:.1f} mês(es))"
                            )
                            eventos_ajustados.append({
                                "operador": "Simulação", "aeronave": aeronave,
                                "periodo_inicio": hoje, "periodo_fim": nova_data,
                                "motivo": f"TBO/HSI ajustado (SN {m['serial']}): {novo_voo:.0f}h/mês simulado (original {m['voo_mensal']:.0f}h/mês)",
                                "confianca": "Simulado", "fonte": FONTE_AJUSTADO,
                            })
        return eventos_ajustados


def render(dados):
    st.title("Diagonal de Manutenção")
    st.caption(
        "Linha do tempo por aeronave: sólido = situação real hoje (Disponibilidade "
        "Diária), listrado = projeção futura de inspeção programada (Diagonal de "
        "Manutenção)."
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔄 Atualizar dados", key="diagonal_atualizar"):
            with st.spinner("Reprocessando dados locais..."):
                atualizar_dados_diagonal_manutencao()
            st.rerun()

    df_programado = dados["diagonal"].copy()
    if not df_programado.empty:
        df_programado["fonte"] = FONTE_PROGRAMADO
    df_real = _eventos_reais(dados.get("disp_aeronaves"))
    df_motor = _eventos_motor(dados.get("motores_diagonal"))
    df = pd.concat([df_real, df_programado, df_motor], ignore_index=True)
    df["texto_evento"] = df["texto_evento"].fillna("") if "texto_evento" in df.columns else ""
    # aeronave precisa ser sempre string — as 3 fontes guardam tipos
    # diferentes (int/float/str), e misturado isso faz o .unique() tratar
    # 2722 (int) e "2722" (str) como valores diferentes, duplicando a
    # aeronave nos filtros/expanders mais adiante.
    def _aeronave_str(v):
        if pd.isna(v):
            return None
        return str(int(v)) if isinstance(v, float) and float(v).is_integer() else str(v)
    df["aeronave"] = df["aeronave"].apply(_aeronave_str)
    if not df_programado.empty:
        df_programado["aeronave"] = df_programado["aeronave"].apply(_aeronave_str)

    if df.empty:
        st.info("Nenhum dado carregado ainda. Peça ao Claude para buscar a Diagonal de Manutenção de cada operador.")
        return

    if dados["diagonal_atualizado_em"]:
        atualizado = horario.fromtimestamp_br(dados["diagonal_atualizado_em"]).strftime("%d/%m/%Y %H:%M")
        st.caption(f"Última atualização dos dados (Diagonal): **{atualizado}**")
    if not df_real.empty:
        st.caption(f"Situação real de hoje: **{df_real['periodo_inicio'].max().strftime('%d/%m/%Y')}** ({len(df_real)} aeronave(s) indisponível(is) no último relatório de Disponibilidade Diária)")

    # Horário de Brasília explícito, não `pd.Timestamp.now()` puro — esse
    # usa o fuso do sistema que roda o código (UTC no GitHub Actions/
    # Streamlit Cloud), o que já causou a "Previsão de situação — próximos
    # 7 dias" não bater com a Disponibilidade Diária (bug real, 2026-07-24).
    hoje = pd.Timestamp(horario.hoje_br())

    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        operadores = st.multiselect("Operador", sorted(df["operador"].unique()), key="diagonal_filtro_operador")
    with c2:
        opcoes_aeronave = sorted(df["aeronave"].dropna().unique(), key=str)
        padrao_aeronave = [a for a in opcoes_aeronave if str(a) in AERONAVES_PADRAO]
        aeronaves_f = st.multiselect(
            "Aeronave", opcoes_aeronave, default=padrao_aeronave, key="diagonal_filtro_aeronave"
        )
    with c3:
        meses_a_frente = st.slider("Meses à frente", min_value=1, max_value=18, value=6, key="diagonal_meses")

    # Aeronaves-alvo: sempre TODAS as selecionadas (ou as 23 dentro do
    # contrato, se o filtro estiver limpo) — pedido do Wallace em
    # 2026-07-15: "vamos colcoar todas aeronave" — cada uma vira uma linha
    # no Gantt mesmo sem nenhum evento de indisponibilidade.
    aeronaves_alvo = aeronaves_f if aeronaves_f else padrao_aeronave
    if not aeronaves_alvo:
        st.caption("Nenhuma aeronave selecionada.")
        return

    limite = hoje + pd.DateOffset(months=meses_a_frente)
    filtrado = df[(df["periodo_fim"] >= hoje) & (df["periodo_inicio"] <= limite)].copy()
    if operadores:
        filtrado = filtrado[filtrado["operador"].isin(operadores)]
    filtrado = filtrado[filtrado["aeronave"].isin(aeronaves_alvo)]

    diagonal_meta = dados.get("motores_diagonal_meta")
    situacao_motores = dados.get("motores_situacao")
    mapa_situacao_hoje = _mapa_situacao_hoje(dados.get("disp_aeronaves"))

    st.divider()
    eventos_ajustados = _secao_detalhe_aeronave(
        aeronaves_alvo, diagonal_meta, situacao_motores, hoje,
        dados.get("rac_aeronaves"), dados.get("rac_pendencias"), mapa_situacao_hoje,
    )
    if eventos_ajustados:
        filtrado = pd.concat([filtrado, pd.DataFrame(eventos_ajustados)], ignore_index=True)

    # Uma linha por aeronave (não por operador+aeronave): as duas fontes às
    # vezes nomeiam o operador diferente pra mesma aeronave (ex.: Diagonal diz
    # "BABR", Disponibilidade Diária diz "6º ETA") — a matrícula é o dado que
    # não muda entre fontes, então é ela que decide a linha no gráfico.
    # O rótulo já traz o motor (SN + %TBO) e a situação de hoje (DI/DO/II/
    # IN/ITR/IS/IP) escritos direto — pedido do Wallace em 2026-07-15,
    # "escreve la" / "colcoar a condicao da aeronave no dia" — sem precisar
    # clicar em nada pro básico.
    def _rotulo_completo(aeronave):
        sit = mapa_situacao_hoje.get(str(aeronave))
        sit_txt = f"[{sit}] " if sit else ""
        motor_txt = _rotulo_motor(aeronave, diagonal_meta, situacao_motores)
        return f"FAB {aeronave} {sit_txt}— {motor_txt}"

    todas_aeronaves = sorted(set(aeronaves_alvo) | set(filtrado["aeronave"].dropna().unique()), key=str)
    mapa_rotulo = {a: _rotulo_completo(a) for a in todas_aeronaves}
    filtrado["aeronave_label"] = filtrado["aeronave"].map(mapa_rotulo)

    # Aeronave-alvo sem nenhum evento no período ainda precisa de uma linha
    # no Gantt — um "espaço reservado" transparente (sem cor visível)
    # garante a categoria no eixo Y mesmo com 0 evento de verdade.
    aeronaves_com_evento = set(filtrado["aeronave"].dropna().unique())
    aeronaves_sem_evento = [a for a in aeronaves_alvo if a not in aeronaves_com_evento]
    if aeronaves_sem_evento:
        reservados = pd.DataFrame([{
            "operador": "Sem evento", "aeronave": a,
            "periodo_inicio": hoje, "periodo_fim": hoje + pd.Timedelta(hours=1),
            "motivo": "Sem indisponibilidade registrada no período/filtro selecionado.",
            "confianca": "—", "fonte": FONTE_REAL, "texto_evento": "",
            "aeronave_label": mapa_rotulo[a],
        } for a in aeronaves_sem_evento])
        filtrado = pd.concat([filtrado, reservados], ignore_index=True)

    if filtrado.empty:
        st.caption("Nenhuma aeronave/evento no período/filtro selecionado.")
        return

    st.divider()
    st.caption(
        f"{len(aeronaves_alvo)} aeronave(s) exibida(s) · {len(aeronaves_com_evento)} com indisponibilidade "
        f"(real ou projetada) · {len(filtrado) - len(aeronaves_sem_evento)} evento(s) na janela selecionada"
    )

    # Eventos de motor (TBO/HSI) não viram barra de mês inteiro — geralmente
    # tem troca de motor no meio do período, então a barra mentiria sobre a
    # duração. Pedido do Wallace em 2026-07-15: "coloca so o ponto de
    # inicio, nao coloca o mes inteiro ... e so para estar escrito tbo ou
    # hsi msm, sem linha pontinha ou bolinha" — só o texto "TBO"/"HSI"
    # marcado no ponto de início, sem barra/marcador de forma nenhuma.
    barras = filtrado[filtrado["fonte"] != FONTE_MOTOR].copy()
    pontos_motor = filtrado[filtrado["fonte"] == FONTE_MOTOR].copy()

    ordem_y = sorted(filtrado["aeronave_label"].unique(), reverse=True)
    fig = px.timeline(
        barras, x_start="periodo_inicio", x_end="periodo_fim", y="aeronave_label",
        color="operador", color_discrete_map=COR_OPERADOR_MOTOR, color_discrete_sequence=CATEGORICA,
        pattern_shape="fonte", pattern_shape_map=PATTERN_FONTE,
        hover_data={"motivo": True, "confianca": True, "fonte": True, "operador": True, "aeronave_label": False},
        category_orders={"aeronave_label": ordem_y},
    )
    for evento_tipo, cor in (("TBO", AMBER), ("HSI", CYAN)):
        pontos = pontos_motor[pontos_motor["texto_evento"] == evento_tipo]
        if pontos.empty:
            continue
        fig.add_scatter(
            x=pontos["periodo_inicio"], y=pontos["aeronave_label"], mode="text",
            text=pontos["texto_evento"], textposition="middle right",
            textfont=dict(color=cor, size=11, family="Arial Black"),
            hovertext=pontos["motivo"], hoverinfo="text", showlegend=False, name=evento_tipo,
        )
    fig.add_vline(x=hoje, line_dash="dash", line_color=SECONDARY, annotation_text="hoje", annotation_position="top")
    fig.update_layout(xaxis_title="", yaxis_title="", legend_title="Operador")
    # Mesmo bug real visto na Diagonal dos Motores em 2026-07-23 (Wallace:
    # "o eixo y, alguns estao cortando as aeronaves") — sem isso, o Plotly
    # às vezes "afina" o eixo Y sozinho e pula rótulo no meio quando acha
    # que não tem altura suficiente. Forçar tickmode="array" com todos os
    # rótulos garante que nenhuma aeronave some.
    fig.update_yaxes(type="category", tickmode="array", tickvals=ordem_y, ticktext=ordem_y, automargin=True)
    layout_grafico(fig, altura=max(280, 28 * filtrado["aeronave_label"].nunique()))
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Listrado (╱) = projeção futura (Programado) · sólido = situação real de hoje · "
        "\"TBO\"/\"HSI\" escrito (âmbar/ciano), sem barra, marca só o início do mês previsto "
        "pela planilha de Motores (a barra inteira enganaria, geralmente troca de motor no meio) · "
        "xadrez (╳), operador \"Simulação\" = previsão recalculada com as horas de voo ajustadas "
        "no painel \"🔍 Detalhe da aeronave\" acima · linha sem barra nenhuma = sem indisponibilidade "
        "no período. Rótulo da aeronave já traz a situação de hoje (Disponibilidade Diária) entre "
        "colchetes e o motor vinculado (SN + % TBO)."
    )

    # Linhas "espaço reservado" (aeronave sem nenhum evento) não são
    # indisponibilidade de verdade — fora do resumo e da tabela.
    eventos_reais = filtrado[filtrado["operador"] != "Sem evento"]

    st.divider()
    st.caption(
        "Previsão de situação — próximos 7 dias, com base na Disponibilidade Diária de hoje "
        "(+ inspeção programada da Diagonal, se houver)"
    )
    previsao = _previsao_situacao_7dias(dados.get("disp_aeronaves"), df_programado, aeronaves_alvo, hoje)
    if previsao.empty:
        st.caption("Sem dado de Disponibilidade Diária pra montar a previsão.")
    else:
        resumo7 = previsao.groupby(["dia", "situacao"]).size().reset_index(name="qtd_aeronaves")
        colunas_dia = [d.strftime("%d/%m") for d in sorted(previsao["dia"].unique())]
        pivot = resumo7.pivot_table(
            index="situacao", columns=resumo7["dia"].dt.strftime("%d/%m"), values="qtd_aeronaves",
            fill_value=0, aggfunc="sum",
        )
        pivot = pivot.reindex(index=[c for c in COR_SITUACAO if c in pivot.index], columns=colunas_dia, fill_value=0)
        pivot.loc["D (DI+DO)"] = pivot.reindex(["DI", "DO"]).fillna(0).sum()
        pivot = pivot.astype(int)
        pivot.index = [NOME_SITUACAO.get(i, i) for i in pivot.index]
        pivot.index.name = "Situação"
        st.dataframe(pivot, width="stretch")
        st.caption(
            "Colunas = dias (hoje até hoje+6). Hoje vem direto do relatório mais recente. Dias "
            "seguintes são estimativa: aeronave indisponível hoje mantém a mesma situação até a Data "
            "Prevista de Entrega (ou +14 dias, sem previsão), depois assume \"Disponível\"; aeronave "
            "disponível com inspeção programada prevista pra esse dia (Diagonal) entra como "
            "\"Manutenção programada\". Última linha soma Disponível (DI) + Disponível c/ restrição (DO)."
        )

    st.divider()
    tabela = eventos_reais[["fonte", "operador", "aeronave", "periodo_inicio", "periodo_fim", "motivo", "confianca"]].rename(columns={
        "fonte": "Fonte", "operador": "Operador", "aeronave": "Aeronave", "periodo_inicio": "Início",
        "periodo_fim": "Fim", "motivo": "Motivo", "confianca": "Confiança",
    }).sort_values("Início")
    tabela = filtro_colunas(tabela, key_prefix="diagonal")
    st.caption(f"{len(tabela)} item(ns) após os filtros por coluna.")
    st.dataframe(tabela, hide_index=True, width="stretch")
