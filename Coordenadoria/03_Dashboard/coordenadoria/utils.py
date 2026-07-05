"""Utilidades compartilhadas entre as páginas da Coordenadoria."""

import subprocess
import sys
from pathlib import Path

import streamlit as st

DASHBOARD_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_GERAR_RAC = DASHBOARD_ROOT / "05_Scripts" / "python" / "extrair_rac.py"
SCRIPT_GERAR_DISPONIBILIDADE = DASHBOARD_ROOT / "05_Scripts" / "python" / "extrair_disponibilidade_diaria.py"
SCRIPT_GERAR_VENCIMENTOS = DASHBOARD_ROOT / "05_Scripts" / "python" / "extrair_vencimentos.py"
SCRIPT_GERAR_VENCIMENTOS_OPERADORES = DASHBOARD_ROOT / "05_Scripts" / "python" / "extrair_vencimentos_operadores.py"
SCRIPT_GERAR_DIAGONAL_MANUTENCAO = DASHBOARD_ROOT / "05_Scripts" / "python" / "extrair_diagonal_manutencao.py"

RAC_PLANILHA_URL = "https://docs.google.com/spreadsheets/d/1o8supQLcHkC1WZZCZDAtuRKGB_VUlQ8qBlYj7racsGQ/edit"
DISPONIBILIDADE_PASTA_URL = "https://drive.google.com/drive/folders/1JLrUGunWo5ABsR3WuYo88b2WD4QWoxNH"
VENCIMENTOS_PLANILHA_URL = "https://docs.google.com/spreadsheets/d/178vQ-lRP52sw30kQArqcsQGXfj2OLblaFCgjIXWFIl8/edit"


def atualizar_dados_rac():
    """Roda de novo a extração do RAC a partir do que já está em 01_Bases_Originais/
    (não busca nada novo do Google Drive — isso continua manual)."""
    resultado = subprocess.run(
        [sys.executable, str(SCRIPT_GERAR_RAC)],
        cwd=str(SCRIPT_GERAR_RAC.parent),
        capture_output=True,
        text=True,
    )
    st.cache_data.clear()
    if resultado.returncode == 0:
        st.toast("Dados do RAC atualizados.", icon="✅")
    else:
        st.error(f"Erro ao atualizar dados do RAC:\n\n{resultado.stderr or resultado.stdout}")


def atualizar_dados_disponibilidade():
    """Reprocessa os relatórios .txt já salvos em 01_Bases_Originais/Disponibilidade_Diaria/
    (buscar um relatório novo no Drive é feito pelo Claude na conversa, não por aqui)."""
    resultado = subprocess.run(
        [sys.executable, str(SCRIPT_GERAR_DISPONIBILIDADE)],
        cwd=str(SCRIPT_GERAR_DISPONIBILIDADE.parent),
        capture_output=True,
        text=True,
    )
    st.cache_data.clear()
    if resultado.returncode == 0:
        st.toast("Dados de disponibilidade atualizados.", icon="✅")
    else:
        st.error(f"Erro ao atualizar disponibilidade diária:\n\n{resultado.stderr or resultado.stdout}")


def atualizar_dados_vencimentos():
    """Reprocessa a cópia local de 01_Bases_Originais/Vencimentos/ (buscar uma
    versão nova no Drive é feito pelo Claude na conversa, não por aqui)."""
    resultado = subprocess.run(
        [sys.executable, str(SCRIPT_GERAR_VENCIMENTOS)],
        cwd=str(SCRIPT_GERAR_VENCIMENTOS.parent),
        capture_output=True,
        text=True,
    )
    st.cache_data.clear()
    if resultado.returncode == 0:
        st.toast("Dados de vencimentos (TMOT) atualizados.", icon="✅")
    else:
        st.error(f"Erro ao atualizar vencimentos:\n\n{resultado.stderr or resultado.stdout}")


def atualizar_dados_vencimentos_operadores():
    """Reprocessa os arquivos por operador já salvos em
    01_Bases_Originais/Vencimentos/Operadores/ (buscar arquivos novos no
    Drive é feito pelo Claude na conversa, não por aqui)."""
    resultado = subprocess.run(
        [sys.executable, str(SCRIPT_GERAR_VENCIMENTOS_OPERADORES)],
        cwd=str(SCRIPT_GERAR_VENCIMENTOS_OPERADORES.parent),
        capture_output=True,
        text=True,
    )
    st.cache_data.clear()
    if resultado.returncode == 0:
        st.toast("Dados de vencimentos por operador atualizados.", icon="✅")
    else:
        st.error(f"Erro ao atualizar vencimentos por operador:\n\n{resultado.stderr or resultado.stdout}")


def atualizar_dados_diagonal_manutencao():
    """Reprocessa as grades de Diagonal de Manutenção já salvas localmente
    (buscar arquivos novos no Drive é feito pelo Claude na conversa, não por
    aqui)."""
    resultado = subprocess.run(
        [sys.executable, str(SCRIPT_GERAR_DIAGONAL_MANUTENCAO)],
        cwd=str(SCRIPT_GERAR_DIAGONAL_MANUTENCAO.parent),
        capture_output=True,
        text=True,
    )
    st.cache_data.clear()
    if resultado.returncode == 0:
        st.toast("Dados de Diagonal de Manutenção atualizados.", icon="✅")
    else:
        st.error(f"Erro ao atualizar Diagonal de Manutenção:\n\n{resultado.stderr or resultado.stdout}")
