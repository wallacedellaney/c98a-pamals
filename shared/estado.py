"""Persistência simples de status de atualização (JSON), sem nenhuma lógica
de área — usado por Contrato 005 e Coordenadoria, cada um com seu próprio
arquivo `estado_atualizacoes.json` dentro de `02_Dados_Tratados/`.

Cada fonte guarda: remote_modified_time, local_updated_at, status
("atualizado" | "pendente" | "erro"), record_count, last_error.
"""

import json
import os
import tempfile
from pathlib import Path


def ler_estado(caminho: Path) -> dict:
    """Carrega o JSON; retorna {} se o arquivo ainda não existir (primeira vez)."""
    caminho = Path(caminho)
    if not caminho.exists():
        return {}
    with caminho.open(encoding="utf-8") as f:
        return json.load(f)


def atualizar_estado(caminho: Path, chave: str, subchave: str = None, **campos) -> dict:
    """Carrega o estado inteiro, atualiza só a entrada de `chave` (ou
    `chave.subchave`, pra casos aninhados como cada operador de
    Vencimentos), grava atômico (arquivo temporário + os.replace) e
    devolve o dict inteiro atualizado."""
    caminho = Path(caminho)
    estado = ler_estado(caminho)

    if subchave is None:
        entrada = estado.setdefault(chave, {})
        entrada.update(campos)
    else:
        grupo = estado.setdefault(chave, {})
        entrada = grupo.setdefault(subchave, {})
        entrada.update(campos)

    caminho.parent.mkdir(parents=True, exist_ok=True)
    fd, caminho_temp = tempfile.mkstemp(dir=str(caminho.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(estado, f, ensure_ascii=False, indent=2)
        os.replace(caminho_temp, caminho)
    finally:
        if os.path.exists(caminho_temp):
            os.remove(caminho_temp)

    return estado


def obter_entrada(caminho: Path, chave: str, subchave: str = None) -> dict:
    """Lê só a entrada de uma fonte (ou de um operador aninhado). Devolve um
    estado "pendente" (nunca atualizado por aqui) se ainda não existir."""
    estado = ler_estado(caminho)
    padrao = {
        "remote_modified_time": None,
        "local_updated_at": None,
        "status": "pendente",
        "record_count": None,
        "last_error": None,
    }
    if subchave is None:
        return {**padrao, **estado.get(chave, {})}
    return {**padrao, **estado.get(chave, {}).get(subchave, {})}
