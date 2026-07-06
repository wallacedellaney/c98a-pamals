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
    df_reparaveis, mtime_rep = carregar_reparaveis()
    df_pagamentos, contrato, empenhos, mtime_pag = carregar_pagamentos()
    return {
        "emergencias": df_emergencias,
        "historico_emergencias": historico_emergencias,
        "reparaveis": df_reparaveis,
        "pagamentos": df_pagamentos,
        "contrato": contrato,
        "empenhos": empenhos,
        "atualizado_em": max(mtime_emerg, mtime_rep, mtime_pag),
    }
