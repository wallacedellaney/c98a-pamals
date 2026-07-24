"""
Carrega a planilha "MTA - Acompanhamento e Solicitações" (Google Sheets, aba
"Solicitações") e gera 02_Dados_Tratados/base_mta_tratada.xlsx — só registros
do projeto C-98. Ver 00_Instrucoes/mta.md.

A planilha tem 2 campos "Projeto" (bloco do coordenador e bloco de dados da
atividade) — considera C-98 quando qualquer um dos dois for exatamente
"C-98" (comparação sem acento/maiúsculas/espaço), sem duplicar linha quando
os dois baterem (é sempre 1 linha = 1 registro, o filtro só decide se entra
ou não).
"""

from datetime import datetime

import openpyxl
import pandas as pd

from common import BASES_ORIGINAIS, DADOS_TRATADOS, ESTADO_ATUALIZACOES, registrar_log
from shared import drive_sync, estado, horario

from projetos.config import mta_config as cfg
from projetos.regras.mta_regras import normalizar, situacao_consolidada

FONTE = BASES_ORIGINAIS / "MTA" / "MTA - Acompanhamento e Solicitacoes (Google Sheets).xlsx"
HISTORICO_MTA = DADOS_TRATADOS / "historico_mta.csv"
COLUNAS_HISTORICO = [
    "linha", "situacao_consolidada", "aprovado", "tramite", "valor",
    "executora", "pacote", "para_contrato", "para_motores",
]

COLUNAS = [
    "linha", "projeto_coordenador", "projeto_atividade", "situacao_consolidada",
    "aprovado", "acao", "tramite", "data_pedido", "digito", "rodada",
    "preenchimento_tgco", "observacao_coordenador", "impactos_nao_atendimento",
    "atividade", "tarefa", "valor", "executora", "nd", "pacote",
    "para_contrato", "para_motores", "mes_previsto",
]


def _texto(valor):
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _inteiro(valor):
    if valor is None:
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _rodada(valor):
    if valor is None:
        return None
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip() or None


def _valor_monetario(valor, contexto, inconsistencias):
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    inconsistencias.append(f"Valor inválido (não numérico) em {contexto}: {valor!r} — não somado.")
    return None


def _data(valor, contexto, inconsistencias):
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor
    inconsistencias.append(f"Data inválida em {contexto}: {valor!r} — descartada, mantida como não informada.")
    return None


def extrair():
    inconsistencias = []
    linhas = []

    wb = openpyxl.load_workbook(FONTE, data_only=True)
    ws = wb[cfg.ABA]

    for i, row in enumerate(ws.iter_rows(min_row=cfg.PRIMEIRA_LINHA_DADOS, max_col=cfg.MAX_COL, values_only=True), start=cfg.PRIMEIRA_LINHA_DADOS):
        if all(v is None for v in row):
            continue

        projeto_coordenador = _texto(row[cfg.COL_PROJETO_COORDENADOR])
        projeto_atividade = _texto(row[cfg.COL_PROJETO_ATIVIDADE])
        eh_c98 = (
            normalizar(projeto_coordenador) == cfg.PROJETO_FILTRO
            or normalizar(projeto_atividade) == cfg.PROJETO_FILTRO
        )
        if not eh_c98:
            continue

        contexto = f"linha da planilha {i} (Linha={row[cfg.COL_LINHA]})"
        aprovado = _texto(row[cfg.COL_APROVADO])
        tramite = _texto(row[cfg.COL_TRAMITE])

        linhas.append({
            "linha": _inteiro(row[cfg.COL_LINHA]),
            "projeto_coordenador": projeto_coordenador,
            "projeto_atividade": projeto_atividade,
            "situacao_consolidada": situacao_consolidada(aprovado, tramite),
            "aprovado": aprovado,
            "acao": _texto(row[cfg.COL_ACAO]),
            "tramite": tramite,
            "data_pedido": _data(row[cfg.COL_DATA_PEDIDO], contexto, inconsistencias),
            "digito": _texto(row[cfg.COL_DIGITO]),
            "rodada": _rodada(row[cfg.COL_RODADA]),
            "preenchimento_tgco": _texto(row[cfg.COL_PREENCHIMENTO_TGCO]),
            "observacao_coordenador": _texto(row[cfg.COL_OBSERVACAO_COORDENADOR]),
            "impactos_nao_atendimento": _texto(row[cfg.COL_IMPACTOS_NAO_ATENDIMENTO]),
            "atividade": _texto(row[cfg.COL_ATIVIDADE]),
            "tarefa": _texto(row[cfg.COL_TAREFA]),
            "valor": _valor_monetario(row[cfg.COL_VALOR], contexto, inconsistencias),
            "executora": _texto(row[cfg.COL_EXECUTORA]),
            "nd": _texto(row[cfg.COL_ND]),
            "pacote": _texto(row[cfg.COL_PACOTE]),
            "para_contrato": _texto(row[cfg.COL_PARA_CONTRATO]),
            "para_motores": _texto(row[cfg.COL_PARA_MOTORES]),
            "mes_previsto": _data(row[cfg.COL_MES_PREVISTO], contexto, inconsistencias),
        })

    df = pd.DataFrame(linhas, columns=COLUNAS)
    return df, inconsistencias


def main():
    DADOS_TRATADOS.mkdir(parents=True, exist_ok=True)
    df, inconsistencias = extrair()

    destino = DADOS_TRATADOS / "base_mta_tratada.xlsx"
    df.to_excel(destino, index=False, sheet_name="MTA")

    registrar_log(
        nome_execucao="extrair_mta",
        arquivos_lidos=[str(FONTE)],
        arquivos_gerados=[str(destino)],
        inconsistencias=inconsistencias,
    )

    print(f"{len(df)} solicitações C-98 carregadas -> {destino}")
    if inconsistencias:
        print(f"{len(inconsistencias)} inconsistência(s) encontrada(s), ver log em 06_Logs/.")

    return df


def _registrar_historico(df):
    """Acrescenta o snapshot de hoje (1 linha por solicitação C-98) — se já
    rodou hoje antes, substitui só as linhas de hoje (não duplica). Base pra
    barra temporal pedida pelo Wallace em 2026-07-09 — só existe história a
    partir do dia em que essa função passou a rodar."""
    hoje = horario.hoje_br().isoformat()
    novo = df[COLUNAS_HISTORICO].copy()
    novo.insert(0, "data_snapshot", hoje)

    if HISTORICO_MTA.exists():
        historico = pd.read_csv(HISTORICO_MTA, dtype={"linha": str})
        historico = historico[historico["data_snapshot"] != hoje]
        historico = pd.concat([historico, novo], ignore_index=True)
    else:
        historico = novo
    historico.to_csv(HISTORICO_MTA, index=False)


def atualizar_do_drive():
    """Busca a versão mais recente direto do Google Drive, sobrescreve a
    cópia local e reprocessa. Ver 00_Instrucoes/atualizacoes.md (raiz)."""
    try:
        metadados = drive_sync.obter_metadados(cfg.DRIVE_FILE_ID)
        conteudo = drive_sync.baixar_arquivo(cfg.DRIVE_FILE_ID, exportar_como=drive_sync.XLSX_MIME)
        FONTE.parent.mkdir(parents=True, exist_ok=True)
        FONTE.write_bytes(conteudo)
        df = main()
        _registrar_historico(df)
        estado.atualizar_estado(
            ESTADO_ATUALIZACOES, "mta",
            remote_modified_time=metadados["modifiedTime"],
            local_updated_at=horario.agora_br().isoformat(),
            status="atualizado",
            record_count=len(df),
            last_error=None,
        )
    except Exception as e:
        estado.atualizar_estado(ESTADO_ATUALIZACOES, "mta", status="erro", last_error=str(e))
        raise
    return estado.obter_entrada(ESTADO_ATUALIZACOES, "mta")


if __name__ == "__main__":
    import sys
    if "--atualizar-do-drive" in sys.argv:
        atualizar_do_drive()
    else:
        main()
