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
    df_reparaveis, mtime_rep = carregar_reparaveis()
    df_pagamentos, contrato, empenhos, mtime_pag = carregar_pagamentos()
    return {
        "emergencias": df_emergencias,
        "historico_emergencias": historico_emergencias,
        "emergencias_totais": df_emergencias_totais,
        "emergencias_totais_atualizado_em": mtime_emerg_totais,
        "reparaveis": df_reparaveis,
        "pagamentos": df_pagamentos,
        "contrato": contrato,
        "empenhos": empenhos,
        "atualizado_em": max(mtime_emerg, mtime_rep, mtime_pag),
    }
