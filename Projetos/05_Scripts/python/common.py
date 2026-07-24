"""Caminhos e utilidades compartilhadas pelos scripts de extração/tratamento da área Projetos."""

import sys
from pathlib import Path

DASHBOARD_ROOT = Path(__file__).resolve().parents[2]

# Raiz do projeto (C-98A PAMALS/) — permite `from shared import drive_sync,
# estado` a partir de qualquer script desta pasta, mesmo rodando como
# subprocesso (sem herdar o sys.path do processo Streamlit pai).
RAIZ_PROJETO = DASHBOARD_ROOT.parent
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

# Permite `from projetos.config import mta_config` etc a partir dos scripts
# de extração (que rodam fora do processo Streamlit, sem o sys.path do app).
DASHBOARD_PACOTE = DASHBOARD_ROOT / "03_Dashboard"
if str(DASHBOARD_PACOTE) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_PACOTE))

from shared import horario  # noqa: E402 — precisa vir depois do sys.path.insert acima

BASES_ORIGINAIS = DASHBOARD_ROOT / "01_Bases_Originais"
DADOS_TRATADOS = DASHBOARD_ROOT / "02_Dados_Tratados"
LOGS = DASHBOARD_ROOT / "06_Logs"
ESTADO_ATUALIZACOES = DADOS_TRATADOS / "estado_atualizacoes.json"


def registrar_log(nome_execucao, arquivos_lidos, arquivos_gerados, inconsistencias, erros=None, proximas_acoes=None):
    """Grava um log de execução em 06_Logs/, no mesmo formato das outras áreas."""
    LOGS.mkdir(parents=True, exist_ok=True)
    ts = horario.agora_br().strftime("%Y-%m-%d_%H-%M-%S")
    caminho = LOGS / f"{ts}_{nome_execucao}.md"

    linhas = [
        f"# Execução: {nome_execucao}",
        "",
        f"Data: {horario.agora_br().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Arquivos lidos",
        *[f"- {a}" for a in arquivos_lidos],
        "",
        "## Arquivos gerados",
        *[f"- {a}" for a in arquivos_gerados],
        "",
        "## Inconsistências encontradas",
        *([f"- {i}" for i in inconsistencias] or ["- nenhuma"]),
        "",
        "## Erros",
        *([f"- {e}" for e in (erros or [])] or ["- nenhum"]),
        "",
        "## Próximas ações recomendadas",
        *([f"- {p}" for p in (proximas_acoes or [])] or ["- nenhuma"]),
        "",
    ]
    caminho.write_text("\n".join(linhas), encoding="utf-8")
    return caminho
