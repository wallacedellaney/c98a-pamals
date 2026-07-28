"""Escrita atômica de arquivo — evita que um leitor concorrente (dashboard
sendo acessado ao mesmo tempo) veja um arquivo pela metade, no meio de ser
escrito.

Bug real corrigido em 2026-07-28: depois da "verificação ao vivo" (ver
shared/verificacao_ao_vivo.py) passar a rodar em subprocesso a qualquer
momento que alguém abre o site, um usuário do site 005CELOG2025 pegou um
`KeyError` esporádico na tela de Reparáveis numa coluna (`em_aberto`) que
sempre existiu — a causa mais provável é 2 sessões do Streamlit lendo/
escrevendo `base_reparaveis_tratada.xlsx` ao mesmo tempo: `df.to_excel()`
não é atômico (escreve o arquivo por partes, no próprio caminho final), e
uma leitura concorrente pode pegar o arquivo truncado/incompleto no meio
da escrita.

**2ª causa achada no mesmo dia** (o erro voltou depois da 1ª correção): o
nome do arquivo temporário era sempre o mesmo (`destino.tmp`) — se 2
atualizações da MESMA fonte rodassem ao mesmo tempo (2 sessões batendo o
cache de 30min no mesmo instante, cada uma abrindo seu próprio
subprocesso), as 2 escreviam no mesmo arquivo `.tmp` ao mesmo tempo,
embaralhando os bytes uma da outra — aí sim o arquivo final podia sair
corrompido/sem coluna, mesmo com a troca por `os.replace` sendo atômica
(a troca era atômica, mas o CONTEÚDO do temporário já tinha saído
corrompido antes da troca). Corrigido dando um nome único por execução
(PID + sufixo aleatório) — 2 escritas concorrentes agora sempre usam
arquivos temporários diferentes, nunca colidem.

Uso: escrever no caminho temporário devolvido; ao sair do `with` sem
levantar exceção, o arquivo temporário substitui o destino de uma vez só
(`os.replace`, atômico no mesmo sistema de arquivos) — quem lê `destino`
nunca vê um estado parcial, só a versão antiga completa ou a nova completa."""

import os
import uuid
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def caminho_temporario(destino):
    destino = Path(destino)
    tmp = destino.with_name(f"{destino.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")
    try:
        yield tmp
        os.replace(tmp, destino)
    finally:
        tmp.unlink(missing_ok=True)
