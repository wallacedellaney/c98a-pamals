"""Roda a atualização automática de uma ou de todas as fontes — chamado pelo
agendamento do macOS (launchd) e do GitHub Actions, sem precisar de mim
(Claude) numa conversa. Se algo mudou de verdade, commita e envia pro GitHub
sozinho, pra o Streamlit Cloud atualizar.

Uso: python3 executar_atualizacao.py <fonte|todos>

"todos" roda as 5 fontes em sequência, uma de cada vez, sincronizando com o
GitHub antes de cada uma — usado pelo agendamento de 2 em 2 horas (seg-sex,
a pedido do Wallace em 2026-07-09, pra contornar o atraso do agendamento
gratuito do GitHub: rodando com mais frequência, mesmo que uma vez atrase,
a próxima já pega o dado atualizado).

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
    "rac": RAIZ / "Coordenadoria" / "05_Scripts" / "python" / "extrair_rac.py",
    "vencimentos_tmot": RAIZ / "Coordenadoria" / "05_Scripts" / "python" / "extrair_vencimentos.py",
    "mta": RAIZ / "Projetos" / "05_Scripts" / "python" / "extrair_mta.py",
    "tpjl": RAIZ / "Projetos" / "05_Scripts" / "python" / "extrair_tpjl.py",
}


def _registrar(texto):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(texto)


def _sincronizar_com_remoto():
    """Sincroniza com o GitHub antes de rodar — necessário porque agora tanto
    o GitHub Actions quanto o launchd do Mac do Wallace rodam essa mesma
    fonte, e podem divergir se um commitar sem o outro saber (já aconteceu em
    2026-07-08). Só reseta se não houver alteração local pendente — nunca
    mexe em trabalho manual em andamento (ex.: sessão do Claude Code aberta)."""
    status = subprocess.run(["git", "status", "--porcelain"], cwd=str(RAIZ), capture_output=True, text=True)
    if status.stdout.strip():
        _registrar("Há alterações locais pendentes — não sincronizei antes de rodar (para não mexer em trabalho manual).\n")
        return
    subprocess.run(["git", "fetch", "origin"], cwd=str(RAIZ), capture_output=True, text=True)
    subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=str(RAIZ), capture_output=True, text=True)


def _executar_uma(fonte):
    script = SCRIPTS[fonte]
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    _sincronizar_com_remoto()

    resultado = subprocess.run(
        [sys.executable, str(script), "--atualizar-do-drive"],
        cwd=str(script.parent), capture_output=True, text=True,
    )
    _registrar(f"\n=== {agora} — {fonte} (returncode={resultado.returncode}) ===\n{resultado.stdout}\n")
    if resultado.stderr:
        _registrar(f"STDERR:\n{resultado.stderr}\n")

    if resultado.returncode != 0:
        _registrar("FALHOU — não commitando.\n")
        return False

    status = subprocess.run(["git", "status", "--porcelain"], cwd=str(RAIZ), capture_output=True, text=True)
    if not status.stdout.strip():
        _registrar("Nada novo pra commitar (sem alteração de arquivo).\n")
        return True

    subprocess.run(["git", "add", "-A"], cwd=str(RAIZ), check=True)
    mensagem = f"Atualização automática: {fonte} ({datetime.now().strftime('%d/%m/%Y %H:%M')})"
    subprocess.run(["git", "commit", "-m", mensagem], cwd=str(RAIZ), check=True)
    push = subprocess.run(["git", "push", "origin", "main"], cwd=str(RAIZ), capture_output=True, text=True)
    if push.returncode != 0:
        _registrar(f"COMMIT OK mas PUSH FALHOU:\n{push.stderr}\n")
        return False
    _registrar("Commitado e enviado pro GitHub com sucesso.\n")
    return True


def main():
    opcoes = list(SCRIPTS) + ["todos"]
    if len(sys.argv) < 2 or sys.argv[1] not in opcoes:
        print(f"Uso: python3 {sys.argv[0]} <{'|'.join(opcoes)}>")
        sys.exit(1)

    alvo = sys.argv[1]
    fontes = list(SCRIPTS) if alvo == "todos" else [alvo]

    ok_geral = True
    for fonte in fontes:
        ok = _executar_uma(fonte)
        ok_geral = ok_geral and ok

    if not ok_geral:
        sys.exit(1)


if __name__ == "__main__":
    main()
