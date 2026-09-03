"""Regras de negócio do MTA — status do recurso, categorias e preparação dos
dados (ver 00_Instrucoes/mta.md). Centralizado aqui pra poder ajustar sem
mexer no extrator nem no dashboard.

2026-09-03 (reformulação pedida pelo Wallace): o eixo da página passou a ser
ATENDIDO x DISPONÍVEL. As classificações viraram configuração (listas de
regras), não if/elif espalhado — pra acrescentar uma atividade nova basta
editar REGRAS_CATEGORIA/REGRAS_SUBCATEGORIA aqui.
"""

import unicodedata

import pandas as pd

from projetos.config.mta_config import (
    TRAMITE_ATENDIDO, TRAMITE_BLOQUEIO, TRAMITE_CANCELADO, TRAMITE_EM_TRAMITE, TRAMITE_PROCESSADO,
)


def normalizar(valor):
    """Maiúsculas, sem acento, sem espaço extra — só pra comparação (nunca
    pra exibição, que usa o valor original)."""
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto or texto.lower() in ("nan", "nat", "none"):
        return None
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return " ".join(sem_acento.upper().split())


def normalizar_valor(valor):
    """Devolve float — aceita número puro ou texto "R$ 1.000.000,00"."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    if not texto:
        return None
    texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def situacao_consolidada(aprovado, tramite):
    """Situação narrativa de cada linha (mantida da versão original — é o
    que aparece na tabela/filtros; NÃO é o que decide disponibilidade, ver
    classificar_status_recurso)."""
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
# STATUS_RECURSO — eixo central da página (Wallace, 2026-09-03).
# ---------------------------------------------------------------------------

STATUS_ATENDIDO = "Atendido"
STATUS_DISPONIVEL = "Disponível"
STATUS_CANCELADO = "Cancelado"
STATUS_BLOQUEADO = "Bloqueado"
STATUS_NAO_APROVADO = "Não aprovado"
STATUS_OUTRO = "Outra situação"

CORES_STATUS_RECURSO = {
    STATUS_ATENDIDO: "good",       # verde
    STATUS_DISPONIVEL: "info",     # azul
    STATUS_CANCELADO: "warning",   # laranja
    STATUS_BLOQUEADO: "warning",
    STATUS_NAO_APROVADO: "critical",  # vermelho
    STATUS_OUTRO: "neutro",
}


def classificar_status_recurso(aprovado, tramite):
    """Status do RECURSO (dinheiro), não da solicitação:

    - Atendido    → Trâmite ATENDIDO ou PROCESSADO (recurso já usado).
    - Cancelado / Bloqueado → têm status próprio: não são disponíveis nem
      atendidos (Wallace, 2026-09-03, item 6 do prompt).
    - Não aprovado → Aprovado = NÃO.
    - Disponível  → Aprovado = SIM e Trâmite vazio.
    - Outra situação → sobra (ex.: Aprovado vazio) — aparece nas exceções,
      nunca é escondida.
    """
    tramite_n = normalizar(tramite)
    aprovado_n = normalizar(aprovado)

    if tramite_n in (normalizar(TRAMITE_ATENDIDO), normalizar(TRAMITE_PROCESSADO)):
        return STATUS_ATENDIDO
    if tramite_n == normalizar(TRAMITE_CANCELADO):
        return STATUS_CANCELADO
    if tramite_n == normalizar(TRAMITE_BLOQUEIO):
        return STATUS_BLOQUEADO
    if aprovado_n == "NAO":
        return STATUS_NAO_APROVADO
    if aprovado_n == "SIM" and tramite_n is None:
        return STATUS_DISPONIVEL
    return STATUS_OUTRO


# ---------------------------------------------------------------------------
# Categoria / Subcategoria / Grupo estratégico — configuração, não if/elif.
# Cada regra: primeira que casar vence (ordem importa). Campos aceitos:
#   atividade_contem / tarefa_contem / para_motores / para_contrato_igual
# Comparação sempre normalizada (maiúscula, sem acento).
# ---------------------------------------------------------------------------

REGRAS_CATEGORIA = [
    {"categoria": "Contrato 005 — VEE ONE", "atividade_contem": ["CNT 005/CELOG-PAMALS"]},
    {"categoria": "Modernização C-98", "atividade_contem": ["MODERNIZA"]},
    {"categoria": "Contrato 006 — RG", "atividade_contem": ["CNT 006/CELOG-PAMASP"]},
    {"categoria": "Contrato 031 — RG", "atividade_contem": ["CNT 031/CELOG-PAMASP"]},
    {"categoria": "Contrato 048 — Material", "atividade_contem": ["CNT 048/CELOG-PAMASP"]},
    {"categoria": "Exchange", "atividade_contem": ["EXCHANGE"]},
    {"categoria": "Requisição CABW", "atividade_contem": ["REQUISICAO CABW"]},
    {"categoria": "Requisição FMS", "atividade_contem": ["REQUISICAO FMS"]},
    {"categoria": "Requisição de Serviço", "atividade_contem": ["REQUISICAO SERVICO"]},
    {"categoria": "Publicações", "atividade_contem": ["REQUISICAO PUBLICACAO"]},
    {"categoria": "Outros contratos", "atividade_contem": ["CNT "]},
    # Códigos pontuais por base (ex.: "2025-BABR-24") — equipamentos avulsos.
    {"categoria": "Requisições específicas / Equipamentos", "atividade_regex": r"^\d{4}-BAB"},
]

REGRAS_SUBCATEGORIA = [
    {"subcategoria": "Consumíveis", "tarefa_contem": ["CONSUMIVE"]},
    {"subcategoria": "Hora de Voo", "tarefa_contem": ["HORA DE VOO"]},
    {"subcategoria": "Revisão Geral PT6", "tarefa_contem": ["REVISAO GERAL", "RG PT6"]},
    {"subcategoria": "Material HSI", "tarefa_contem": ["MATERIAL HSI"]},
    {"subcategoria": "Material PT6", "tarefa_contem": ["MATERIAL REPARO", "MATERIAL PT6", "MATERIAL DIVERSOS"]},
    {"subcategoria": "Exchange", "tarefa_contem": ["EXCHANGE"]},
    {"subcategoria": "Fuel Pump", "tarefa_contem": ["FUEL PUMP"]},
    {"subcategoria": "FCU", "tarefa_contem": ["FCU"]},
    {"subcategoria": "Ignition Exciter", "tarefa_contem": ["IGNITION EXCITER"]},
    {"subcategoria": "CTVR / PTVR", "tarefa_contem": ["CTVR", "PTVR"]},
    {"subcategoria": "Publicações", "tarefa_contem": ["PUBLICAC"]},
    {"subcategoria": "GPS", "tarefa_contem": ["GPS"]},
    {"subcategoria": "Módulo Extra", "tarefa_contem": ["MODULO EXTRA"]},
    {"subcategoria": "Parcela de Modernização", "tarefa_contem": ["MODERNIZA"]},
]

NAO_CLASSIFICADO = "Não classificado"


def _casa_regra(regra, atividade_n, tarefa_n, para_motores_n, para_contrato_n):
    import re

    if "atividade_contem" in regra:
        if not atividade_n or not any(t in atividade_n for t in regra["atividade_contem"]):
            return False
    if "atividade_regex" in regra:
        if not atividade_n or not re.search(regra["atividade_regex"], atividade_n):
            return False
    if "tarefa_contem" in regra:
        if not tarefa_n or not any(t in tarefa_n for t in regra["tarefa_contem"]):
            return False
    if "para_motores" in regra:
        if para_motores_n != normalizar(regra["para_motores"]):
            return False
    if "para_contrato_igual" in regra:
        if para_contrato_n != normalizar(regra["para_contrato_igual"]):
            return False
    return True


def classificar_categoria(atividade, tarefa=None, para_motores=None, para_contrato=None):
    atividade_n = normalizar(atividade)
    tarefa_n = normalizar(tarefa)
    para_motores_n = normalizar(para_motores)
    para_contrato_n = normalizar(para_contrato)
    for regra in REGRAS_CATEGORIA:
        if _casa_regra(regra, atividade_n, tarefa_n, para_motores_n, para_contrato_n):
            return regra["categoria"]
    return NAO_CLASSIFICADO


def classificar_subcategoria(tarefa, atividade=None):
    tarefa_n = normalizar(tarefa)
    atividade_n = normalizar(atividade)
    for regra in REGRAS_SUBCATEGORIA:
        if _casa_regra(regra, atividade_n, tarefa_n, None, None):
            return regra["subcategoria"]
    return NAO_CLASSIFICADO


def relacionado_motor(para_motores, tarefa=None, atividade=None):
    """Marcador transversal — "Para Motores" = SIM é o sinal explícito da
    planilha; texto de PT6/motor reforça (ex.: publicação de PT6A)."""
    if normalizar(para_motores) == "SIM":
        return True
    alvo = f"{normalizar(tarefa) or ''} {normalizar(atividade) or ''}"
    return any(t in alvo for t in ("PT6", "MOTOR", "HSI", "FUEL PUMP", "FCU", "CTVR", "PTVR", "IGNITION EXCITER"))


def relacionado_consumivel(tarefa):
    return "CONSUMIVE" in (normalizar(tarefa) or "")


def classificar_grupo_estrategico(para_motores, tarefa, atividade, categoria=None):
    """Visão TRANSVERSAL (não soma com Categoria — ver item 23 do prompt):
    Motores > Consumíveis > Hora de Voo > a própria categoria."""
    if relacionado_consumivel(tarefa):
        return "Consumíveis"
    if relacionado_motor(para_motores, tarefa, atividade):
        return "Motores"
    if "HORA DE VOO" in (normalizar(tarefa) or ""):
        return "Hora de Voo"
    return categoria or NAO_CLASSIFICADO


ORDEM_GRUPO_ESTRATEGICO = [
    "Motores", "Consumíveis", "Hora de Voo", "Contrato 005 — VEE ONE", "Modernização C-98",
    "Requisição CABW", "Requisição FMS", "Requisição de Serviço", "Publicações",
    "Requisições específicas / Equipamentos", "Outros contratos", NAO_CLASSIFICADO,
]


def prepare_mta_data(df):
    """Etapa central de preparação (item 4 do prompt): normaliza, classifica
    e cria os campos derivados. Não altera nenhum valor original — só
    ACRESCENTA colunas. Vetorizado onde dá; `apply` só onde a regra é
    textual linha a linha (86 linhas, custo irrelevante)."""
    if df is None or df.empty:
        return df

    out = df.copy()
    out["VALOR_NUMERICO"] = out["valor"].apply(normalizar_valor)
    out["STATUS_RECURSO"] = [
        classificar_status_recurso(a, t) for a, t in zip(out["aprovado"], out["tramite"])
    ]
    out["ATENDIDO_BOOL"] = out["STATUS_RECURSO"] == STATUS_ATENDIDO
    out["DISPONIVEL_BOOL"] = out["STATUS_RECURSO"] == STATUS_DISPONIVEL
    out["APROVADO_BOOL"] = out["aprovado"].apply(lambda v: normalizar(v) == "SIM")

    out["CATEGORIA"] = [
        classificar_categoria(a, t, pm, pc)
        for a, t, pm, pc in zip(out["atividade"], out["tarefa"], out["para_motores"], out["para_contrato"])
    ]
    out["SUBCATEGORIA"] = [classificar_subcategoria(t, a) for t, a in zip(out["tarefa"], out["atividade"])]
    out["RELACIONADO_MOTOR"] = [
        relacionado_motor(pm, t, a) for pm, t, a in zip(out["para_motores"], out["tarefa"], out["atividade"])
    ]
    out["RELACIONADO_CONSUMIVEL"] = out["tarefa"].apply(relacionado_consumivel)
    out["GRUPO_ESTRATEGICO"] = [
        classificar_grupo_estrategico(pm, t, a, c)
        for pm, t, a, c in zip(out["para_motores"], out["tarefa"], out["atividade"], out["CATEGORIA"])
    ]

    mes = pd.to_datetime(out["mes_previsto"], errors="coerce")
    out["MES_PLANEJAMENTO"] = mes.dt.to_period("M").astype(str).where(mes.notna(), None)
    return out


def validar_fechamento(df):
    """Item 51 — Atendido + Disponível deve fechar com o Aprovado
    operacional (aprovado que não virou cancelado/bloqueado/exceção).
    Devolve dict com os números e a lista de linhas que não fecham."""
    aprovado = df[df["APROVADO_BOOL"]]
    atendido = aprovado[aprovado["ATENDIDO_BOOL"]]
    disponivel = aprovado[aprovado["DISPONIVEL_BOOL"]]
    excecoes = aprovado[~aprovado["ATENDIDO_BOOL"] & ~aprovado["DISPONIVEL_BOOL"]]

    soma = lambda d: float(d["VALOR_NUMERICO"].sum(skipna=True))
    operacional = soma(atendido) + soma(disponivel)
    return {
        "valor_aprovado_bruto": soma(aprovado),
        "valor_aprovado_operacional": operacional,
        "valor_atendido": soma(atendido),
        "valor_disponivel": soma(disponivel),
        "valor_excecoes": soma(excecoes),
        "qtd_aprovado_bruto": len(aprovado),
        "qtd_atendido": len(atendido),
        "qtd_disponivel": len(disponivel),
        "qtd_excecoes": len(excecoes),
        "fecha": abs(operacional + soma(excecoes) - soma(aprovado)) < 0.01,
        "excecoes": excecoes,
    }
