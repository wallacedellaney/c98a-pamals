"""Regras de negócio do TPJL — status atual, pendência e situação da
previsão (ver 00_Instrucoes/tpjl.md). Centralizado aqui pra ajustar sem
mexer no extrator nem no dashboard."""

import unicodedata
from datetime import datetime

from projetos.config.tpjl_config import STATUS_FINAIS


def normalizar(valor):
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return " ".join(sem_acento.upper().split())


def _agrupar_cancelado(texto):
    """"Cancelada"/"Cancelado" (e variações) viram um grupo visual só —
    mantém a grafia original mais comum ("Cancelado") pro campo calculado."""
    if normalizar(texto) in ("CANCELADA", "CANCELADO"):
        return "Cancelado"
    return texto


def status_atual(status, status_11g, status_comprar):
    """Último status preenchido, prioridade da direita pra esquerda: Status
    > Status 11G > Status Comprar. Ver 00_Instrucoes/tpjl.md."""
    for valor in (status, status_11g, status_comprar):
        if valor is not None and str(valor).strip():
            return _agrupar_cancelado(valor)
    return "Sem informação"


def eh_pendencia(status_atual_valor):
    """Não conta como pendência quando já está numa situação final
    (Empenhado, Cancelado, Item Deserto, Item Fracassado)."""
    return normalizar(status_atual_valor) not in {normalizar(s) for s in STATUS_FINAIS}


def situacao_previsao(previsao_empenho, status_atual_valor, hoje=None):
    """Classifica: No prazo, Vencido, Sem data definida, Concluído, Cancelado.
    `previsao_empenho` pode ser datetime, texto (ex. "IMEDIATO") ou None —
    texto/None nunca derruba a classificação, só vira "Sem data definida"."""
    hoje = hoje or datetime.now()
    status_n = normalizar(status_atual_valor)

    if status_n == "CANCELADO":
        return "Cancelado", None
    if status_n == "EMPENHADO":
        return "Concluído", None

    if not isinstance(previsao_empenho, datetime):
        return "Sem data definida", None

    if not eh_pendencia(status_atual_valor):
        return "Concluído", None

    if previsao_empenho.date() < hoje.date():
        dias_atraso = (hoje.date() - previsao_empenho.date()).days
        return "Vencido", dias_atraso

    return "No prazo", None


COR_SITUACAO_PREVISAO = {
    "No prazo": "good",
    "Vencido": "critical",
    "Sem data definida": "neutro",
    "Concluído": "good",
    "Cancelado": "neutro",
}
