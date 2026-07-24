"""Horário local (Brasília, America/Sao_Paulo) — usado em vez de
`datetime.now()`/`date.today()` puro sempre que o resultado é MOSTRADO na
tela ("Última atualização: HH:MM") ou usado pra decidir "que dia é hoje"
(ex.: checar se hoje é dia útil, comparar com o relatório mais recente).

Bug real corrigido em 2026-07-24 (Wallace: "acho que o horario da
atualizaaao aparece o utc zero, traz para horario de brasilia") —
`datetime.now()` puro usa o fuso do SISTEMA que está rodando o código, que
varia conforme o ambiente: o Mac do Wallace já é Brasília, mas o GitHub
Actions e o Streamlit Cloud rodam em UTC — então o mesmo código mostrava
horários diferentes (3h de diferença) dependendo de onde executava. Usar
sempre `ZoneInfo("America/Sao_Paulo")` explicitamente elimina essa
dependência do fuso do ambiente.

Não precisa de dependência nova — `zoneinfo` é da biblioteca padrão desde
Python 3.9 (os scripts daqui usam 3.14)."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")


def agora_br():
    """Agora, no horário de Brasília — em vez de `datetime.now()` puro."""
    return datetime.now(FUSO_BRASILIA)


def hoje_br():
    """Data de hoje, no horário de Brasília — em vez de `date.today()` puro."""
    return agora_br().date()


def fromtimestamp_br(timestamp):
    """Converte um timestamp Unix (ex.: mtime de arquivo) pro horário de
    Brasília — em vez de `datetime.fromtimestamp(timestamp)` puro, que usa
    o fuso do sistema local."""
    return datetime.fromtimestamp(timestamp, tz=FUSO_BRASILIA)
