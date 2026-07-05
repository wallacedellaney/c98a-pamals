"""Carrega os dados tratados da Coordenadoria (02_Dados_Tratados/) para o dashboard."""

from pathlib import Path

import pandas as pd
import streamlit as st

DASHBOARD_ROOT = Path(__file__).resolve().parents[3]
DADOS_TRATADOS = DASHBOARD_ROOT / "02_Dados_Tratados"


@st.cache_data
def _ler_excel(caminho_str, _mtime, **kwargs):
    return pd.read_excel(caminho_str, **kwargs)


def carregar_rac():
    caminho = DADOS_TRATADOS / "base_rac_tratada.xlsx"
    mtime = caminho.stat().st_mtime
    aeronaves = _ler_excel(str(caminho), mtime, sheet_name="Aeronaves")
    pendencias = _ler_excel(str(caminho), mtime, sheet_name="Pendencias")
    return aeronaves, pendencias, mtime


def carregar_disponibilidade_diaria():
    caminho = DADOS_TRATADOS / "base_disponibilidade_diaria.xlsx"
    if not caminho.exists():
        return pd.DataFrame(), pd.DataFrame(), None
    mtime = caminho.stat().st_mtime
    relatorios = _ler_excel(str(caminho), mtime, sheet_name="Relatorios")
    aeronaves = _ler_excel(str(caminho), mtime, sheet_name="Aeronaves")
    relatorios["data_referencia"] = pd.to_datetime(relatorios["data_referencia"])
    aeronaves["data_referencia"] = pd.to_datetime(aeronaves["data_referencia"])
    return relatorios, aeronaves, mtime


def carregar_vencimentos():
    caminho = DADOS_TRATADOS / "base_vencimentos_tratada.xlsx"
    if not caminho.exists():
        return pd.DataFrame(), None
    mtime = caminho.stat().st_mtime
    tmot = _ler_excel(str(caminho), mtime, sheet_name="TMOT")
    return tmot, mtime


def carregar_vencimentos_operadores():
    caminho = DADOS_TRATADOS / "base_vencimentos_operadores.xlsx"
    if not caminho.exists():
        return pd.DataFrame(), None
    mtime = caminho.stat().st_mtime
    df = _ler_excel(str(caminho), mtime, sheet_name="Operadores")
    return df, mtime


def carregar_diagonal_manutencao():
    caminho = DADOS_TRATADOS / "base_diagonal_manutencao.xlsx"
    if not caminho.exists():
        return pd.DataFrame(), None
    mtime = caminho.stat().st_mtime
    df = _ler_excel(str(caminho), mtime, sheet_name="Diagonal")
    df["periodo_inicio"] = pd.to_datetime(df["periodo_inicio"])
    df["periodo_fim"] = pd.to_datetime(df["periodo_fim"])
    return df, mtime


def carregar_tudo():
    aeronaves, pendencias, mtime_rac = carregar_rac()
    disp_relatorios, disp_aeronaves, mtime_disp = carregar_disponibilidade_diaria()
    tmot, mtime_venc = carregar_vencimentos()
    venc_operadores, mtime_venc_op = carregar_vencimentos_operadores()
    diagonal, mtime_diagonal = carregar_diagonal_manutencao()
    return {
        "rac_aeronaves": aeronaves,
        "rac_pendencias": pendencias,
        "atualizado_em": mtime_rac,
        "disp_relatorios": disp_relatorios,
        "disp_aeronaves": disp_aeronaves,
        "disp_atualizado_em": mtime_disp,
        "venc_tmot": tmot,
        "venc_atualizado_em": mtime_venc,
        "venc_operadores": venc_operadores,
        "venc_operadores_atualizado_em": mtime_venc_op,
        "diagonal": diagonal,
        "diagonal_atualizado_em": mtime_diagonal,
    }
