"""
Carrega os arquivos tratados de 02_Dados_Tratados/ para o dashboard de
Projetos (MTA e TPJL). Enquanto os extratores (Etapas 3 e 5) não existirem,
os dois vêm vazios (`None`) — a tela de seleção mostra dados simulados nesse
caso (ver secoes/selecao.py).
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from shared import estado

DASHBOARD_ROOT = Path(__file__).resolve().parents[3]
DADOS_TRATADOS = DASHBOARD_ROOT / "02_Dados_Tratados"
ESTADO_ATUALIZACOES = DADOS_TRATADOS / "estado_atualizacoes.json"
CONTRATO005_DADOS_TRATADOS = DASHBOARD_ROOT.parent / "Contrato 005" / "Dashboard" / "02_Dados_Tratados"
COORDENADORIA_DADOS_TRATADOS = DASHBOARD_ROOT.parent / "Coordenadoria" / "02_Dados_Tratados"


@st.cache_data
def _ler_excel(caminho_str, _mtime, **kwargs):
    return pd.read_excel(caminho_str, **kwargs)


@st.cache_data
def _ler_csv(caminho_str, _mtime, **kwargs):
    return pd.read_csv(caminho_str, **kwargs)


def carregar_historico_mta():
    caminho = DADOS_TRATADOS / "historico_mta.csv"
    if not caminho.exists():
        return pd.DataFrame(columns=[
            "data_snapshot", "linha", "situacao_consolidada", "aprovado", "tramite",
            "valor", "executora", "pacote", "para_contrato", "para_motores",
        ])
    return _ler_csv(str(caminho), caminho.stat().st_mtime, dtype={"linha": str})


def carregar_historico_tpjl():
    caminho = DADOS_TRATADOS / "historico_tpjl.csv"
    if not caminho.exists():
        return pd.DataFrame(columns=[
            "data_snapshot", "ano", "numero_requisicao", "pn", "status_atual",
            "valor_total", "situacao_previsao", "dias_atraso",
        ])
    return _ler_csv(str(caminho), caminho.stat().st_mtime, dtype={"numero_requisicao": str, "pn": str, "ano": str})


def carregar_mta():
    caminho = DADOS_TRATADOS / "base_mta_tratada.xlsx"
    if not caminho.exists():
        return None, None
    mtime = caminho.stat().st_mtime
    return _ler_excel(str(caminho), mtime), mtime


def carregar_tpjl():
    """2025 e 2026 ficam em abas separadas do mesmo arquivo (decisão do
    Wallace em 2026-07-09 — não fundir os anos). Devolve {2025: df, 2026: df}."""
    caminho = DADOS_TRATADOS / "base_tpjl_tratada.xlsx"
    if not caminho.exists():
        return None, None
    mtime = caminho.stat().st_mtime
    dados = {
        2025: _ler_excel(str(caminho), mtime, sheet_name="TPJL_2025"),
        2026: _ler_excel(str(caminho), mtime, sheet_name="TPJL_2026"),
    }
    for df in dados.values():
        df["previsao_empenho"] = pd.to_datetime(df["previsao_empenho"], errors="coerce")
        df["dpe"] = pd.to_datetime(df["dpe"], errors="coerce")
    return dados, mtime


def carregar_historico_tpjl_solicitacoes():
    """Snapshot diário de Solicitações (barra temporal, pedido do Wallace em
    2026-07-14) — só existe a partir do dia em que essa gravação começou."""
    caminho = DADOS_TRATADOS / "historico_tpjl_solicitacoes.csv"
    if not caminho.exists():
        return pd.DataFrame(columns=[
            "data_snapshot", "numero_solicitacao", "pn", "categoria", "quantidade",
            "tipo", "status", "solicitante", "data_criacao", "ultima_atualizacao",
        ])
    return _ler_csv(str(caminho), caminho.stat().st_mtime, dtype={"numero_solicitacao": str, "pn": str})


def carregar_tpjl_extras():
    """Consumo/Estoque/Solicitações — 3 fontes extras da pasta Drive
    "Planilhas TPLJ" incorporadas em 2026-07-14, ver 00_Instrucoes/tpjl.md."""
    caminho = DADOS_TRATADOS / "base_tpjl_extras.xlsx"
    if not caminho.exists():
        return None, None
    mtime = caminho.stat().st_mtime
    consumo = _ler_excel(str(caminho), mtime, sheet_name="Consumo")
    estoque = _ler_excel(str(caminho), mtime, sheet_name="Estoque")
    solicitacoes = _ler_excel(str(caminho), mtime, sheet_name="Solicitacoes")
    solicitacoes["data_criacao"] = pd.to_datetime(solicitacoes["data_criacao"], errors="coerce")
    solicitacoes["ultima_atualizacao"] = pd.to_datetime(solicitacoes["ultima_atualizacao"], errors="coerce")
    dados = {"consumo": consumo, "estoque": estoque, "solicitacoes": solicitacoes}
    return dados, mtime


def carregar_empenhos_contrato005():
    """Lê os empenhos reais (número/valor/saldo, aba "Empenhos") e o
    cronograma físico financeiro (aba "CronogramaMensal") já tratados pelo
    Contrato 005 — usados na análise de saldo do MTA (Hora de Voo) pra
    cruzar a fila de solicitações com o que já é empenho de verdade e o
    saldo real. Leitura direta do arquivo tratado da outra área (só
    dados, sem import de pacote — mesma regra de sempre entre áreas). Ver
    Contrato 005/Dashboard/00_Instrucoes/reajuste.md."""
    caminho_pagamentos = CONTRATO005_DADOS_TRATADOS / "base_pagamentos_tratada.xlsx"
    caminho_reajuste = CONTRATO005_DADOS_TRATADOS / "base_reajuste_tratada.xlsx"
    if not caminho_pagamentos.exists() or not caminho_reajuste.exists():
        return None
    empenhos = _ler_excel(str(caminho_pagamentos), caminho_pagamentos.stat().st_mtime, sheet_name="Empenhos")
    cronograma = _ler_excel(str(caminho_reajuste), caminho_reajuste.stat().st_mtime, sheet_name="CronogramaMensal")
    indicadores = _ler_excel(str(caminho_reajuste), caminho_reajuste.stat().st_mtime, sheet_name="Indicadores")

    # Saldo da autorização do contrato inteiro (Módulo 1+2+3) — quanto ainda
    # PODE ser empenhado dentro do que já foi autorizado, bem maior que o
    # saldo dos empenhos já emitidos (aba "Empenhos") porque cobre a
    # autorização toda, não só os NEs já formalizados. Wallace, 2026-07-28:
    # "pega meus saldos que tenho modulo 2 e modulo 3 para entrar na conta
    # geral" — usa o rótulo "após 2° Reajuste" (único, não se repete entre
    # seções, ao contrário de "após 1° Reajuste").
    linha_saldo = indicadores[indicadores["indicador"] == "Saldo do Contrato após 2° Reajuste"]
    saldo_geral_contrato = float(linha_saldo["valor"].iloc[0]) if not linha_saldo.empty else None

    # Valor real da hora de voo (Reajuste) — usado pra calcular o consumo
    # mensal a partir de horas restantes, não do valor em R$ das parcelas.
    # Wallace, 2026-07-28: "media de gasto nao é do cronograma é o real,
    # quantas horas falta no ano? [...] divide por quantos meses nao paguei
    # e multiplica pela hora de voo (valor)". Rótulo único (não se repete).
    linha_hv = indicadores[indicadores["indicador"] == "Valor da hora de voo após 2° Reajuste"]
    valor_hora_voo = float(linha_hv["valor"].iloc[0]) if not linha_hv.empty else None

    # Histórico diário da aba Empenhos — Wallace, 2026-07-28: pode ter
    # atraso entre o MTA marcar "Atendido" e o empenho real aparecer aqui;
    # com o snapshot diário, "o dinheiro nunca some" mesmo com esse delay
    # (sempre dá pra achar quando um NE apareceu/mudou de saldo). Ver
    # Contrato 005/Dashboard/05_Scripts/python/extrair_pagamentos.py.
    caminho_historico_empenhos = CONTRATO005_DADOS_TRATADOS / "historico_empenhos.csv"
    historico_empenhos = (
        _ler_csv(str(caminho_historico_empenhos), caminho_historico_empenhos.stat().st_mtime,
                 dtype={"numero_empenho": str})
        if caminho_historico_empenhos.exists() else pd.DataFrame(columns=[
            "data_snapshot", "numero_empenho", "valor_empenhado", "saldo", "responsavel", "justificativa",
        ])
    )

    return {
        "empenhos": empenhos,
        "cronograma_mensal": cronograma,
        "saldo_geral_contrato": saldo_geral_contrato,
        "valor_hora_voo": valor_hora_voo,
        "historico_empenhos": historico_empenhos,
    }


def _horas_para_decimal(texto):
    """"10070:00"/"5063:50" (formato H:MM da Disponibilidade Diária) -> horas
    decimais (10070.0 / 5063.83...)."""
    if pd.isna(texto):
        return None
    horas, minutos = str(texto).split(":")
    return int(horas) + int(minutos) / 60


def carregar_esforco_anual():
    """Horas de Hora de Voo previstas x realizadas no ano, da Disponibilidade
    Diária (Coordenadoria) — Wallace, 2026-07-28: "horas nao voadas e
    extraida na disp diaria, tem a quantidade disponivel ai ainda". Fonte
    mais real (voo de verdade, cresce dia a dia) do que somar "1000 HV" do
    texto das parcelas do MTA (que é só o que foi orçado/parcelado, não o
    que de fato voou). Usa o relatório mais recente. Leitura direta do
    arquivo tratado da outra área (só dados, sem import de pacote)."""
    caminho = COORDENADORIA_DADOS_TRATADOS / "base_disponibilidade_diaria.xlsx"
    if not caminho.exists():
        return None
    relatorios = _ler_excel(str(caminho), caminho.stat().st_mtime, sheet_name="Relatorios")
    if relatorios.empty:
        return None
    ultimo = relatorios.sort_values("data_referencia").iloc[-1]
    previsto = _horas_para_decimal(ultimo["esforco_anual_previsto"])
    realizado = _horas_para_decimal(ultimo["esforco_anual_realizado"])
    if previsto is None or realizado is None:
        return None
    return {
        "data_referencia": ultimo["data_referencia"],
        "horas_previstas": previsto,
        "horas_realizadas": realizado,
        "horas_nao_voadas": previsto - realizado,
    }


def carregar_tudo():
    df_mta, mtime_mta = carregar_mta()
    df_tpjl, mtime_tpjl = carregar_tpjl()
    df_tpjl_extras, mtime_tpjl_extras = carregar_tpjl_extras()
    return {
        "mta": df_mta,
        "mta_atualizado_em": mtime_mta,
        "mta_estado": estado.obter_entrada(ESTADO_ATUALIZACOES, "mta"),
        "mta_historico": carregar_historico_mta(),
        "empenhos_contrato005": carregar_empenhos_contrato005(),
        "esforco_anual": carregar_esforco_anual(),
        "tpjl": df_tpjl,
        "tpjl_atualizado_em": mtime_tpjl,
        "tpjl_estado": estado.obter_entrada(ESTADO_ATUALIZACOES, "tpjl"),
        "tpjl_historico": carregar_historico_tpjl(),
        "tpjl_extras": df_tpjl_extras,
        "tpjl_extras_atualizado_em": mtime_tpjl_extras,
        "tpjl_extras_estado": estado.obter_entrada(ESTADO_ATUALIZACOES, "tpjl_extras"),
        "tpjl_extras_historico_solicitacoes": carregar_historico_tpjl_solicitacoes(),
    }
