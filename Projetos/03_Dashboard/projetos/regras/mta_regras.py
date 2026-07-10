"""Regras de negócio do MTA — situação consolidada (ver 00_Instrucoes/mta.md).
Centralizado aqui pra poder ajustar sem mexer no extrator nem no dashboard."""

import unicodedata

from projetos.config.mta_config import TRAMITE_ATENDIDO, TRAMITE_EM_TRAMITE


def normalizar(valor):
    """Maiúsculas, sem acento, sem espaço extra — só pra comparação (nunca
    pra exibição, que usa o valor original)."""
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return " ".join(sem_acento.upper().split())


def situacao_consolidada(aprovado, tramite):
    """Ver 00_Instrucoes/mta.md — regras dadas pelo Wallace em 2026-07-09."""
    aprovado_n = normalizar(aprovado)
    tramite_n = normalizar(tramite)

    if tramite_n == normalizar(TRAMITE_ATENDIDO):
        return "Atendido"
    if tramite_n == normalizar(TRAMITE_EM_TRAMITE):
        return "Em trâmite"
    if aprovado_n == "SIM" and tramite_n is None:
        return "Aprovado, aguardando atendimento"
    if aprovado_n == "NAO":
        return "Não aprovado"
    return "Sem informação"


COR_SITUACAO = {
    "Atendido": "good",
    "Em trâmite": "warning",
    "Aprovado, aguardando atendimento": "warning",
    "Não aprovado": "critical",
    "Sem informação": "neutro",
}
