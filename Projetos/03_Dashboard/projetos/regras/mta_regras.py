"""Regras de negócio do MTA — situação consolidada (ver 00_Instrucoes/mta.md)
e disponibilidade financeira (ver 00_Instrucoes/mta.md, seção "Disponibilidade
financeira", pedido do Wallace em 2026-09-03). Centralizado aqui pra poder
ajustar sem mexer no extrator nem no dashboard."""

import math
import unicodedata

from projetos.config.mta_config import TRAMITE_ATENDIDO, TRAMITE_EM_TRAMITE, TRAMITE_PROCESSADO


def normalizar(valor):
    """Maiúsculas, sem acento, sem espaço extra — só pra comparação (nunca
    pra exibição, que usa o valor original).

    2026-09-03: célula vazia lida direto do openpyxl (extrator) vem como
    `None`, mas a MESMA célula relida depois via `pd.read_excel` (dashboard,
    ver carregar_dados.py) vem como `float('nan')` — sem o check de NaN
    aqui, `esta_disponivel()`/`tem_providencia_tgco()` (mta_regras.py)
    tratavam Trâmite/TGCO vazios como um texto real ("NAN"), zerando
    "Disponível geral" na tela. Achado testando a página de verdade, não
    só lendo o arquivo."""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
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


# ---------------------------------------------------------------------------
# Disponibilidade financeira (2026-09-03, pedido do Wallace) — 4 perguntas
# gerenciais: quanto foi aprovado, quanto já foi usado, quanto ainda tá
# disponível, e desse disponível, quanto já tem providência da TGCO vs tá
# livre de verdade. Regras propositalmente simples e auditáveis (direto de
# Aprovado/Trâmite/Preenchimento da TGCO, sem depender de
# `situacao_consolidada`, que existe pra outro propósito — mostrar a
# situação narrativa de cada linha, não decidir disponibilidade).
# ---------------------------------------------------------------------------

def esta_utilizado(tramite):
    """Dinheiro já usado — Trâmite = ATENDIDO ou PROCESSADO (ver
    TRAMITE_PROCESSADO em mta_config.py)."""
    t = normalizar(tramite)
    return t in (normalizar(TRAMITE_ATENDIDO), normalizar(TRAMITE_PROCESSADO))


def esta_disponivel(aprovado, tramite):
    """Aprovado = SIM e Trâmite vazio — aprovado mas ainda não usado nem
    cancelado/bloqueado. Não inclui EM TRÂMITE de propósito (Wallace,
    2026-09-03: só criar esse estado se houver linha real nele — hoje não
    há nenhuma)."""
    return normalizar(aprovado) == "SIM" and normalizar(tramite) is None


def tem_providencia_tgco(preenchimento_tgco):
    """Dentro do disponível: já tem alguma nota da TGCO (ATENDER, ATENDER
    SET, REMANEJAR, "ATENDER com 20XV" etc.) — indica que já existe um
    próximo passo programado, mesmo sem ainda ter virado Trâmite."""
    return normalizar(preenchimento_tgco) is not None


def grupo_estrategico(atividade, tarefa, para_motores):
    """Destinação estratégica do dinheiro — dimensão INDEPENDENTE de
    "Para Contrato" (categoria operacional: Hora de Voo/Sob Demanda/
    Parcela Fixa/Requisição), pra não somar as duas juntas (uma linha de
    Hora de Voo do Contrato 005 e uma linha "Motores" não são a mesma
    coisa, mas também não são categorias que se somam sem sobreposição —
    ver 00_Instrucoes/mta.md).

    Prioridade de decisão (2026-09-03, achado ao cruzar a planilha real):
    1. "Para Motores" = SIM sempre vira Motores, não importa a atividade —
       é o único campo explícito da planilha pra isso, mais confiável que
       adivinhar pelo texto da atividade.
    2. Tarefa contendo "Consumíve" — linhas de "Requisições Consumíveis"
       existem tanto na atividade "Requisição CABW" quanto "Requisição
       FMS" (2 canais de aquisição diferentes pro MESMO tipo de destinação
       — mesma coisa que se compra, caminho administrativo diferente).
    3. Daí em diante, por texto da Atividade — contrato nomeado > padrão
       genérico "Outros contratos" > "Outros" (códigos pontuais de base,
       ex. "2025-BABR-24").

    Conferido linha a linha contra a planilha real em 2026-09-03: cobre
    100% do valor sem sobra nem duplicata (soma dos grupos = soma total)."""
    if normalizar(para_motores) == "SIM":
        return "Motores"
    tarefa_n = normalizar(tarefa) or ""
    if "CONSUMIVE" in tarefa_n:
        return "Consumíveis"
    atividade_n = normalizar(atividade) or ""
    if atividade_n.startswith("CNT 005"):
        return "Contrato 005"
    if "MODERNIZA" in atividade_n:
        return "Modernização"
    if atividade_n == "REQUISICAO CABW":
        return "Requisição CABW"
    if atividade_n == "REQUISICAO FMS":
        return "Requisição FMS"
    if atividade_n == "REQUISICAO SERVICO":
        return "Requisição de Serviço"
    if atividade_n == "REQUISICAO PUBLICACAO":
        return "Publicações"
    if atividade_n.startswith("CNT "):
        return "Outros contratos"
    return "Outros"


ORDEM_GRUPO_ESTRATEGICO = [
    "Motores", "Consumíveis", "Contrato 005", "Modernização", "Requisição CABW",
    "Requisição de Serviço", "Requisição FMS", "Publicações", "Outros contratos", "Outros",
]
