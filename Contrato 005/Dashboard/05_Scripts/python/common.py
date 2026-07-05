"""Caminhos e utilidades compartilhadas pelos scripts de extração/tratamento."""

import sys
from pathlib import Path
from datetime import datetime

DASHBOARD_ROOT = Path(__file__).resolve().parents[2]

# Raiz do projeto (C-98A PAMALS/) — permite `from shared import drive_sync,
# estado` a partir de qualquer script desta pasta, mesmo rodando como
# subprocesso (sem herdar o sys.path do processo Streamlit pai).
RAIZ_PROJETO = DASHBOARD_ROOT.parent.parent
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

BASES_ORIGINAIS = DASHBOARD_ROOT / "01_Bases_Originais"
DADOS_TRATADOS = DASHBOARD_ROOT / "02_Dados_Tratados"
LOGS = DASHBOARD_ROOT / "06_Logs"
ESTADO_ATUALIZACOES = DADOS_TRATADOS / "estado_atualizacoes.json"

XLSX_PAGAMENTOS = BASES_ORIGINAIS / "005_CELOG_2025" / "005_CELOG-PAMALS_2025 online.xlsx"


def registrar_log(nome_execucao, arquivos_lidos, arquivos_gerados, inconsistencias, erros=None, proximas_acoes=None):
    """Grava um log de execução em 06_Logs/, no formato pedido pelo CLAUDE.md (passo 10)."""
    LOGS.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    caminho = LOGS / f"{ts}_{nome_execucao}.md"

    linhas = [
        f"# Execução: {nome_execucao}",
        "",
        f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
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
