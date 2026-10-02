"""Integração simples com a API REST do Trello (key+token), usada pelos
scripts de extração pra avisar automaticamente quando um dado muda de
verdade (não a cada execução — só quando o valor realmente é diferente do
que já estava registrado).

Credenciais em .secrets/trello_credentials.json (fora do git, mesmo padrão
do service_account.json do Drive). Se o arquivo não existir (ex.: ambiente
do GitHub Actions, que não tem esse secret), as funções aqui falham em
silêncio — a notificação é um efeito colateral, nunca pode derrubar a
extração principal.
"""

import json
from pathlib import Path

import requests

CAMINHO_CREDENCIAIS = Path(__file__).resolve().parent.parent / ".secrets" / "trello_credentials.json"


def _credenciais():
    if not CAMINHO_CREDENCIAIS.exists():
        return None
    try:
        with open(CAMINHO_CREDENCIAIS) as f:
            return json.load(f)
    except Exception:
        return None


def comentar_cartao(card_id_ou_shortlink, texto):
    """Posta um comentário no card do Trello. Nunca levanta exceção — se a
    credencial não existir ou a chamada falhar, só retorna False."""
    cred = _credenciais()
    if not cred:
        return False
    try:
        resp = requests.post(
            f"https://api.trello.com/1/cards/{card_id_ou_shortlink}/actions/comments",
            params={"key": cred["key"], "token": cred["token"], "text": texto},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False
