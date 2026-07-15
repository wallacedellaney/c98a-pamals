"""Carrega os dados tratados da Coordenadoria (02_Dados_Tratados/) para o dashboard."""

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


def carregar_rac():
    caminho = DADOS_TRATADOS / "base_rac_tratada.xlsx"
    mtime = caminho.stat().st_mtime
    aeronaves = _ler_excel(str(caminho), mtime, sheet_name="Aeronaves")
    pendencias = _ler_excel(str(caminho), mtime, sheet_name="Pendencias")
    return aeronaves, pendencias, mtime


def carregar_historico_rac():
    """Snapshot diário item a item das pendências do RAC, acumulado desde
    2026-07-06 (não existe histórico anterior a essa data). Ver rac.md."""
    caminho = DADOS_TRATADOS / "historico_rac.csv"
    if not caminho.exists():
        return pd.DataFrame(columns=["data", "matricula", "unidade", "pn", "nomenclatura", "quantidade_faltante"])
    mtime = caminho.stat().st_mtime
    df = _ler_csv(str(caminho), mtime, dtype={"matricula": str})
    df["data"] = pd.to_datetime(df["data"])
    return df


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


def carregar_motores():
    """Situação de motores (SILOMS), projeção TBO/HSI (Diagonal Nova), OS e
    hélices — planilha pessoal "MOTORES C-98" (Drive do Wallace). Ver
    00_Instrucoes/motores.md."""
    caminho = DADOS_TRATADOS / "base_motores_tratada.xlsx"
    if not caminho.exists():
        return None, None, None, None, None, None
    mtime = caminho.stat().st_mtime
    # dtype=str nos campos identificadores — sem isso, o pandas relê "2702"
    # do Excel como número (openpyxl/Excel não guarda "isso é texto" pra
    # string puramente numérica), quebrando a ordenação/serialização Arrow
    # mais adiante (mesmo bug já visto em outras áreas do projeto).
    dtype_id = {"pn": str, "sn": str, "matricula": str, "numero_doc": str, "recolhimento": str}
    situacao = _ler_excel(str(caminho), mtime, sheet_name="Situacao", dtype=dtype_id)
    diagonal = _ler_excel(str(caminho), mtime, sheet_name="Diagonal", dtype={"serial": str})
    os_df = _ler_excel(str(caminho), mtime, sheet_name="OS", dtype={
        **dtype_id, "solicitacao": str, "emergencia": str, "cff": str, "os_origem": str,
    })
    helice = _ler_excel(str(caminho), mtime, sheet_name="Helice", dtype=dtype_id)
    diagonal_meta = _ler_excel(str(caminho), mtime, sheet_name="DiagonalMeta", dtype={"serial": str})
    for df in (situacao, diagonal, os_df, helice):
        for coluna in df.columns:
            if coluna.startswith("data_") or coluna == "data_status" or coluna.endswith("_prev") or coluna.endswith("_real"):
                df[coluna] = pd.to_datetime(df[coluna], errors="coerce")
    return situacao, diagonal, os_df, helice, diagonal_meta, mtime


def carregar_historico_motores_situacao():
    """Snapshot diário da Situação de motores (barra temporal, pedido do
    Wallace em 2026-07-14: "vai ter historico pq vai ter atualizacao
    diaria") — só existe a partir do dia em que essa gravação começou."""
    caminho = DADOS_TRATADOS / "historico_motores_situacao.csv"
    if not caminho.exists():
        return pd.DataFrame(columns=[
            "data_snapshot", "om", "pn", "sn", "matricula", "parcial_tso", "totais_tsn",
            "pct_tbo_voada", "tbo", "condicao", "motivo",
        ])
    return _ler_csv(str(caminho), caminho.stat().st_mtime, dtype={"sn": str, "matricula": str, "pn": str})


def carregar_historico_motores_diagonal():
    """Snapshot diário dos eventos TBO/HSI/TBO* projetados (barra temporal,
    pedido do Wallace em 2026-07-15: "mostrar na diagonal dos motores tb,
    um historico de evolucao") — só existe a partir do dia em que essa
    gravação começou."""
    caminho = DADOS_TRATADOS / "historico_motores_diagonal.csv"
    if not caminho.exists():
        return pd.DataFrame(columns=["data_snapshot", "serial", "anv", "ano", "mes", "evento", "comentario"])
    return _ler_csv(str(caminho), caminho.stat().st_mtime, dtype={"serial": str})


def carregar_tudo():
    aeronaves, pendencias, mtime_rac = carregar_rac()
    historico_rac = carregar_historico_rac()
    disp_relatorios, disp_aeronaves, mtime_disp = carregar_disponibilidade_diaria()
    tmot, mtime_venc = carregar_vencimentos()
    venc_operadores, mtime_venc_op = carregar_vencimentos_operadores()
    diagonal, mtime_diagonal = carregar_diagonal_manutencao()
    motores_situacao, motores_diagonal, motores_os, motores_helice, motores_diagonal_meta, mtime_motores = carregar_motores()
    return {
        "rac_aeronaves": aeronaves,
        "rac_pendencias": pendencias,
        "rac_historico": historico_rac,
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
        "motores_situacao": motores_situacao,
        "motores_diagonal": motores_diagonal,
        "motores_os": motores_os,
        "motores_helice": motores_helice,
        "motores_diagonal_meta": motores_diagonal_meta,
        "motores_atualizado_em": mtime_motores,
        "motores_historico_situacao": carregar_historico_motores_situacao(),
        "motores_historico_diagonal": carregar_historico_motores_diagonal(),
    }
