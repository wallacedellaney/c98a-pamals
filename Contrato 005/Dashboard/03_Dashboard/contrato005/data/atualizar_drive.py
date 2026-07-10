"""Ponte entre o dashboard (03_Dashboard/) e os extratores (05_Scripts/python/)
pra atualização sob demanda vinda do Google Drive. As duas pastas são
árvores de módulo separadas (não dá pra importar os extratores direto), então
cada fonte roda como subprocesso, igual o botão "Atualizar dados" já fazia —
só que agora em modo `--atualizar-do-drive` (busca no Drive antes de
reprocessar). Ver 00_Instrucoes/atualizacoes.md (raiz do projeto).
"""

import subprocess
import sys
from pathlib import Path

import streamlit as st

from shared import drive_sync, estado

DASHBOARD_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = DASHBOARD_ROOT / "05_Scripts" / "python"
ESTADO_ATUALIZACOES = DASHBOARD_ROOT / "02_Dados_Tratados" / "estado_atualizacoes.json"

FONTES = [
    ("emergencias", "Emergências", SCRIPTS_DIR / "extrair_emergencias.py"),
    ("reparaveis", "Reparáveis", SCRIPTS_DIR / "extrair_reparaveis.py"),
    ("pagamentos", "Pagamentos", SCRIPTS_DIR / "extrair_pagamentos.py"),
]


def estado_de(chave):
    return estado.obter_entrada(ESTADO_ATUALIZACOES, chave)


def atualizar_fonte(chave):
    """Roda o extrator daquela fonte em modo Drive; levanta RuntimeError com
    a mensagem já registrada em estado_atualizacoes.json se falhar."""
    script = next(s for c, _, s in FONTES if c == chave)
    drive_sync.garantir_credencial_arquivo()
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


def atualizar_tudo():
    """Roda as 3 fontes em sequência; se alguma falhar, levanta uma exceção
    agregada (as outras já ficam atualizadas mesmo assim)."""
    erros = []
    for chave, nome, _ in FONTES:
        try:
            atualizar_fonte(chave)
        except Exception as e:
            erros.append((nome, str(e)))
    if not erros:
        return

    mensagens_unicas = {msg for _, msg in erros}
    if len(mensagens_unicas) == 1:
        nomes = ", ".join(nome for nome, _ in erros)
        raise RuntimeError(f"{nomes}: {mensagens_unicas.pop()}")
    raise RuntimeError("\n".join(f"{nome}: {msg}" for nome, msg in erros))
