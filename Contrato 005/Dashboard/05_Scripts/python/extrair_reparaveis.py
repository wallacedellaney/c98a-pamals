"""
Carrega a tabela de reparáveis C-98 a partir da planilha do Google Sheets
(aba 'Divulgação') e gera 02_Dados_Tratados/base_reparaveis_tratada.xlsx.

Campos importantes (confirmado pelo Wallace): OS, PN, CFF, NOMENCLATURA, SN,
DATA INICIO, UNIDADE SOLIC., ST_OS, TAT SILOMS, ONDE SE ENCONTRA,
RECIBO CASO TENHA, CONDIÇÃO, SN TROCADO (EXCHANGE), TERMO DE RECEBIMENTO.
Colunas fora dessa lista (Qt, TAT REAL, observações, bloco de acerto virtual
além do Termo de Recebimento) não são extraídas.

Regras de tratamento vêm de 00_Instrucoes/reparaveis.md.
"""

import re
import warnings
from datetime import datetime

import openpyxl
import pandas as pd

from common import BASES_ORIGINAIS, DADOS_TRATADOS, ESTADO_ATUALIZACOES, registrar_log
from shared import drive_sync, estado

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

FONTE = BASES_ORIGINAIS / "Controles_Reparaveis" / "Controle reparaveis C-98 (Google Sheets).xlsx"
ABA = "Divulgação"

# Ver 00_Instrucoes/atualizacoes.md — planilha Google nativa "Controle
# reparáveis C-98", dono ngodoy143@gmail.com.
DRIVE_FILE_ID = "1dy_U2Pu5mw6se_gsGvPnuiErKlUJbHnE743f5fnSQ4o"

COLUNAS = [
    "os", "pn", "cff", "nomenclatura", "sn", "data_inicio", "unidade_solicitante",
    "situacao", "tat_siloms", "onde_se_encontra", "recibo", "condicao",
    "data_retorno_prevista", "sn_trocado_exchange", "termo_recebimento",
]

# Snapshot diário das OS em aberto — mesmo padrão de Emergências/RAC/MTA/TPJL.
# Só existe histórico a partir de quando essa gravação começou (não dá pra
# reconstruir o passado). Ver 00_Instrucoes/analise_periodo.md.
HISTORICO_REPARAVEIS = DADOS_TRATADOS / "historico_reparaveis.csv"
COLUNAS_HISTORICO = [
    "os", "pn", "nomenclatura", "unidade_solicitante", "situacao",
    "condicao", "onde_se_encontra", "tat_siloms",
]

DATA_RE = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}$")

# Grafias diferentes para o mesmo estado, encontradas na planilha (ver reparaveis.md)
CONDICOES_PADRONIZADAS = {
    "DEVOLVODO NO ESTADO": "DEVOLVIDO NO ESTADO",
    "DEVOLViDO NO ESTADO": "DEVOLVIDO NO ESTADO",
    "EM REPARO ": "EM REPARO",
    "condenado": "CONDENADO",
}


def parse_data(valor):
    if valor is None or valor == "":
        return None, None
    if hasattr(valor, "date"):
        return valor.date(), None
    texto = str(valor).strip()
    if DATA_RE.match(texto):
        dia, mes, ano = texto.split("/")
        try:
            return pd.Timestamp(year=int(ano), month=int(mes), day=int(dia)).date(), None
        except ValueError:
            return texto, f"data em formato inesperado: '{texto}'"
    return texto, f"data em formato inesperado: '{texto}'"


def parse_inteiro(valor):
    try:
        return int(valor)
    except (ValueError, TypeError):
        return None


def extrair():
    inconsistencias = []
    linhas = []

    wb = openpyxl.load_workbook(FONTE, data_only=True)
    ws = wb[ABA]

    for row in ws.iter_rows(min_row=5, max_col=20, values_only=True):
        if not row[1]:
            continue

        os_num = row[1]
        situacao = str(row[8] or "").strip()

        data_inicio, erro_data = parse_data(row[6])
        if erro_data:
            inconsistencias.append(f"OS {os_num}: {erro_data}")

        condicao_bruta = row[16]
        # Quando a OS já tem recibo (foi enviada a uma base), a coluna CONDIÇÃO às
        # vezes traz a data prevista de devolução em vez de um status em texto.
        if hasattr(condicao_bruta, "date"):
            condicao = None
            data_retorno_prevista = condicao_bruta.date() if hasattr(condicao_bruta, "date") else condicao_bruta
        else:
            condicao_texto = str(condicao_bruta or "").strip()
            if condicao_texto and DATA_RE.match(condicao_texto):
                condicao = None
                data_retorno_prevista, erro_retorno = parse_data(condicao_texto)
                if erro_retorno:
                    inconsistencias.append(f"OS {os_num}: {erro_retorno} (em CONDIÇÃO)")
            else:
                condicao = CONDICOES_PADRONIZADAS.get(condicao_texto, condicao_texto) or None
                data_retorno_prevista = None

        linhas.append({
            "os": os_num,
            "pn": row[2],
            "cff": row[3],
            "nomenclatura": row[4],
            "sn": row[5],
            "data_inicio": data_inicio,
            "unidade_solicitante": row[7],
            "situacao": situacao,
            "tat_siloms": parse_inteiro(row[9]),
            "onde_se_encontra": row[14],
            "recibo": row[15],
            "condicao": condicao,
            "data_retorno_prevista": data_retorno_prevista,
            "sn_trocado_exchange": row[17],
            "termo_recebimento": row[19],
            "em_aberto": situacao != "OS concluída",
        })

    df = pd.DataFrame(linhas, columns=COLUNAS + ["em_aberto"])

    duplicadas = df[df.duplicated(subset=["os"], keep=False)]
    if not duplicadas.empty:
        for os_num in duplicadas["os"].unique():
            inconsistencias.append(f"OS {os_num} aparece mais de uma vez na extração.")

    return df, inconsistencias


def main():
    DADOS_TRATADOS.mkdir(parents=True, exist_ok=True)
    df, inconsistencias = extrair()

    destino = DADOS_TRATADOS / "base_reparaveis_tratada.xlsx"
    df.to_excel(destino, index=False, sheet_name="Reparaveis")

    registrar_log(
        nome_execucao="extrair_reparaveis",
        arquivos_lidos=[str(FONTE)],
        arquivos_gerados=[str(destino)],
        inconsistencias=inconsistencias,
        proximas_acoes=["Revisar OS duplicadas e datas com formato inesperado."] if inconsistencias else None,
    )

    print(f"{len(df)} OS carregadas -> {destino}")
    if inconsistencias:
        print(f"{len(inconsistencias)} inconsistência(s) encontrada(s), ver log em 06_Logs/.")

    return df


def _registrar_historico(df):
    """Acrescenta o snapshot de hoje (1 linha por OS em aberto) — se já
    rodou hoje antes, substitui só as linhas de hoje (não duplica)."""
    hoje = datetime.now().date().isoformat()
    novo = df[COLUNAS_HISTORICO].copy()
    novo.insert(0, "data_snapshot", hoje)

    if HISTORICO_REPARAVEIS.exists():
        historico = pd.read_csv(HISTORICO_REPARAVEIS, dtype={"os": str})
        historico = historico[historico["data_snapshot"] != hoje]
        historico = pd.concat([historico, novo], ignore_index=True)
    else:
        historico = novo
    historico.to_csv(HISTORICO_REPARAVEIS, index=False)


def atualizar_do_drive():
    """Busca a versão mais recente direto do Google Drive, sobrescreve a
    cópia local e reprocessa. Ver 00_Instrucoes/atualizacoes.md."""
    try:
        metadados = drive_sync.obter_metadados(DRIVE_FILE_ID)
        conteudo = drive_sync.baixar_arquivo(DRIVE_FILE_ID, exportar_como=drive_sync.XLSX_MIME)
        FONTE.parent.mkdir(parents=True, exist_ok=True)
        FONTE.write_bytes(conteudo)
        df = main()
        _registrar_historico(df)
        estado.atualizar_estado(
            ESTADO_ATUALIZACOES, "reparaveis",
            remote_modified_time=metadados["modifiedTime"],
            local_updated_at=datetime.now().isoformat(),
            status="atualizado",
            record_count=len(df),
            last_error=None,
        )
    except Exception as e:
        estado.atualizar_estado(ESTADO_ATUALIZACOES, "reparaveis", status="erro", last_error=str(e))
        raise
    return estado.obter_entrada(ESTADO_ATUALIZACOES, "reparaveis")


if __name__ == "__main__":
    import sys
    if "--atualizar-do-drive" in sys.argv:
        atualizar_do_drive()
    else:
        main()
