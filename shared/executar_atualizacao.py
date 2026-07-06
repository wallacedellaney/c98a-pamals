"""Roda a atualização automática de uma fonte — chamado pelo agendamento do
macOS (launchd), sem precisar de mim (Claude) numa conversa. Se algo mudou de
verdade, commita e envia pro GitHub sozinho, pra o Streamlit Cloud atualizar.

Uso: python3 executar_atualizacao.py <disponibilidade_diaria|emergencias|pagamentos>

Ver 00_Instrucoes/atualizacoes.md (raiz do projeto).
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LOG = RAIZ / "shared" / "automacao.log"

SCRIPTS = {
    "disponibilidade_diaria": RAIZ / "Coordenadoria" / "05_Scripts" / "python" / "extrair_disponibilidade_diaria.py",
    "emergencias": RAIZ / "Contrato 005" / "Dashboard" / "05_Scripts" / "python" / "extrair_emergencias.py",
    "pagamentos": RAIZ / "Contrato 005" / "Dashboard" / "05_Scripts" / "python" / "extrair_pagamentos.py",
}


def _registrar(texto):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(texto)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in SCRIPTS:
        print(f"Uso: python3 {sys.argv[0]} <{'|'.join(SCRIPTS)}>")
        sys.exit(1)

    fonte = sys.argv[1]
    script = SCRIPTS[fonte]
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    resultado = subprocess.run(
        [sys.executable, str(script), "--atualizar-do-drive"],
        cwd=str(script.parent), capture_output=True, text=True,
    )
    _registrar(f"\n=== {agora} — {fonte} (returncode={resultado.returncode}) ===\n{resultado.stdout}\n")
    if resultado.stderr:
        _registrar(f"STDERR:\n{resultado.stderr}\n")

    if resultado.returncode != 0:
        _registrar(f"FALHOU — não commitando.\n")
        sys.exit(1)

    status = subprocess.run(["git", "status", "--porcelain"], cwd=str(RAIZ), capture_output=True, text=True)
    if not status.stdout.strip():
        _registrar("Nada novo pra commitar (sem alteração de arquivo).\n")
        return

    subprocess.run(["git", "add", "-A"], cwd=str(RAIZ), check=True)
    mensagem = f"Atualização automática: {fonte} ({datetime.now().strftime('%d/%m/%Y %H:%M')})"
    subprocess.run(["git", "commit", "-m", mensagem], cwd=str(RAIZ), check=True)
    push = subprocess.run(["git", "push", "origin", "main"], cwd=str(RAIZ), capture_output=True, text=True)
    if push.returncode != 0:
        _registrar(f"COMMIT OK mas PUSH FALHOU:\n{push.stderr}\n")
        sys.exit(1)
    _registrar(f"Commitado e enviado pro GitHub com sucesso.\n")


if __name__ == "__main__":
    main()
