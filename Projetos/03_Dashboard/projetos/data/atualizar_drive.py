"""Ponte entre o dashboard (03_Dashboard/) e os extratores (05_Scripts/python/)
pra atualização sob demanda vinda do Google Drive — mesmo padrão do Contrato
005 (ver contrato005/data/atualizar_drive.py). Cada fonte roda como
subprocesso em modo `--atualizar-do-drive`, com botão próprio (sem "atualizar
tudo", pedido do Wallace em 2026-07-09 — ver 00_Instrucoes/mta.md/tpjl.md)."""

import subprocess
import sys
from pathlib import Path

import streamlit as st

from shared import estado

DASHBOARD_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = DASHBOARD_ROOT / "05_Scripts" / "python"
ESTADO_ATUALIZACOES = DASHBOARD_ROOT / "02_Dados_Tratados" / "estado_atualizacoes.json"

FONTES = [
    ("mta", "MTA", SCRIPTS_DIR / "extrair_mta.py"),
    ("tpjl", "TPJL", SCRIPTS_DIR / "extrair_tpjl.py"),
]


def estado_de(chave):
    return estado.obter_entrada(ESTADO_ATUALIZACOES, chave)


def atualizar_fonte(chave):
    """Roda o extrator daquela fonte em modo Drive; levanta RuntimeError com
    a mensagem já registrada em estado_atualizacoes.json se falhar."""
    script = next(s for c, _, s in FONTES if c == chave)
    subprocess.run(
        [sys.executable, str(script), "--atualizar-do-drive"],
        cwd=str(script.parent),
        capture_output=True,
        text=True,
    )
    st.cache_data.clear()
    entrada = estado_de(chave)
    if entrada["status"] == "erro":
        raise RuntimeError(entrada.get("last_error") or "erro desconhecido")
