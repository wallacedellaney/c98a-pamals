"""
Carrega os arquivos tratados de 02_Dados_Tratados/ para o dashboard.

O cache é invalidado automaticamente quando o arquivo no disco muda (usamos a
data de modificação do arquivo como parte da chave do cache do Streamlit), sem
precisar reiniciar o app.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

DASHBOARD_ROOT = Path(__file__).resolve().parents[3]
DADOS_TRATADOS = DASHBOARD_ROOT / "02_Dados_Tratados"


@st.cache_data
def _ler_excel(caminho_str, _mtime, **kwargs):
    return pd.read_excel(caminho_str, **kwargs)


@st.cache_data
def _ler_csv(caminho_str, _mtime, **kwargs):
    return pd.read_csv(caminho_str, **kwargs)


def carregar_emergencias():
    caminho = DADOS_TRATADOS / "base_emergencias_tratada.xlsx"
    return _ler_excel(str(caminho), caminho.stat().st_mtime), caminho.stat().st_mtime


def carregar_historico_emergencias():
    """Snapshot diário das emergências em aberto, acumulado desde 2026-07-06
    (não existe histórico anterior a essa data). Ver emergencias.md."""
    caminho = DADOS_TRATADOS / "historico_emergencias.csv"
    if not caminho.exists():
        return pd.DataFrame(columns=[
            "data_snapshot", "numero_emergencia", "om", "matricula_aeronave", "pn",
            "nomenclatura", "situacao", "tpemg", "data_abertura", "prazo_entrega", "dpe", "dias_atraso",
        ])
    mtime = caminho.stat().st_mtime
    df = _ler_csv(str(caminho), mtime, dtype={"matricula_aeronave": str, "numero_emergencia": str})
    df["data_snapshot"] = pd.to_datetime(df["data_snapshot"])
    return df


def carregar_emergencias_totais():
    """Todo o histórico de emergências (abertas e concluídas) do provedor
    VEE ONE, gerado sob demanda por extrair_historico_completo(). Ver
    emergencias.md — 'Histórico completo (VEE ONE, todas as situações)'."""
    caminho = DADOS_TRATADOS / "historico_completo_emergencias.xlsx"
    if not caminho.exists():
        return pd.DataFrame(), None
    mtime = caminho.stat().st_mtime
    return _ler_excel(str(caminho), mtime), mtime


def carregar_computo_mensal(ano, mes):
    """Cômputo Mensal (aba 1.2 da Pré-RNA) — matriz aeronave x dia calculada
    por calcular_computo_mensal.py. Ver 00_Instrucoes/computo_mensal.md."""
    pasta = DADOS_TRATADOS / "computo_mensal"
    mes_ref = f"{ano}-{mes:02d}"
    caminho_matriz = pasta / f"{mes_ref}_matriz.csv"
    caminho_motivos = pasta / f"{mes_ref}_motivos.csv"
    caminho_resumo = pasta / f"{mes_ref}_resumo.json"
    if not caminho_matriz.exists():
        return None, None, None
    mtime = caminho_matriz.stat().st_mtime
    df_matriz = _ler_csv(str(caminho_matriz), mtime, dtype={"matricula": str})
    df_motivos = (
        _ler_csv(str(caminho_motivos), caminho_motivos.stat().st_mtime, dtype={"matricula": str})
        if caminho_motivos.exists() else pd.DataFrame()
    )
    import json
    with open(caminho_resumo, encoding="utf-8") as f:
        resumo = json.load(f)
    return df_matriz, df_motivos, resumo


def carregar_devolucoes():
    """Empréstimos/devoluções de material — planilha "Devoluções". Ver
    00_Instrucoes/emprestimos.md."""
    caminho = DADOS_TRATADOS / "base_devolucoes_tratada.xlsx"
    if not caminho.exists():
        return pd.DataFrame(), None
    mtime = caminho.stat().st_mtime
    df = _ler_excel(str(caminho), mtime)
    df["pedido_envio"] = pd.to_datetime(df["pedido_envio"], errors="coerce")
    df["data_devolucao"] = pd.to_datetime(df["data_devolucao"], errors="coerce")
    return df, mtime


def carregar_reparaveis():
    caminho = DADOS_TRATADOS / "base_reparaveis_tratada.xlsx"
    return _ler_excel(str(caminho), caminho.stat().st_mtime), caminho.stat().st_mtime


def carregar_pagamentos():
    caminho = DADOS_TRATADOS / "base_pagamentos_tratada.xlsx"
    mtime = caminho.stat().st_mtime
    df = _ler_excel(str(caminho), mtime, sheet_name="Pagamentos")
    contrato = _ler_excel(str(caminho), mtime, sheet_name="Contrato").iloc[0]
    empenhos = _ler_excel(str(caminho), mtime, sheet_name="Empenhos")
    return df, contrato, empenhos, mtime


def carregar_tudo():
    df_emergencias, mtime_emerg = carregar_emergencias()
    historico_emergencias = carregar_historico_emergencias()
    df_emergencias_totais, mtime_emerg_totais = carregar_emergencias_totais()
    df_devolucoes, mtime_devolucoes = carregar_devolucoes()
    df_reparaveis, mtime_rep = carregar_reparaveis()
    df_pagamentos, contrato, empenhos, mtime_pag = carregar_pagamentos()
    return {
        "emergencias": df_emergencias,
        "historico_emergencias": historico_emergencias,
        "emergencias_totais": df_emergencias_totais,
        "emergencias_totais_atualizado_em": mtime_emerg_totais,
        "devolucoes": df_devolucoes,
        "devolucoes_atualizado_em": mtime_devolucoes,
        "reparaveis": df_reparaveis,
        "pagamentos": df_pagamentos,
        "contrato": contrato,
        "empenhos": empenhos,
        "atualizado_em": max(mtime_emerg, mtime_rep, mtime_pag),
    }
