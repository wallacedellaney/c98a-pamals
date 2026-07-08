"""
Carrega a tabela de emergências C-98 a partir da planilha do Google Sheets
(aba 'Prazos das emergências') e gera 02_Dados_Tratados/base_emergencias_tratada.xlsx.

Só limpa tipos (datas/números) e normaliza texto truncado — não pré-filtra por
situação: os filtros (aberta/concluída, aeronave, provedor etc.) são feitos no
próprio dashboard. Ver 00_Instrucoes/emergencias.md.

A planilha é privada; não há conexão ao vivo. Quando os dados mudarem no
Google Sheets, peça para buscar de novo — o arquivo local é baixado por fora
deste script e salvo em 01_Bases_Originais/Prazo_Emergencias_C98/.
"""

import warnings
from datetime import datetime

import openpyxl
import pandas as pd

from common import BASES_ORIGINAIS, DADOS_TRATADOS, ESTADO_ATUALIZACOES, registrar_log
from shared import drive_sync, estado

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

FONTE = BASES_ORIGINAIS / "Prazo_Emergencias_C98" / "Prazo das emergencias - C-98 (Google Sheets).xlsx"
ABA = "Prazos das emergências"

# Ver 00_Instrucoes/atualizacoes.md — planilha Google nativa "Prazo das
# emergências - C-98", dono aux.coord.c98@gmail.com.
DRIVE_FILE_ID = "1OuZK024q1kOkKEf6KN18yu2b33mCHwgZfnwFdpELieA"

# Um snapshot por dia das emergências em aberto — não existe histórico
# anterior a 2026-07-06, pois a base sempre sobrescreveu a cópia local até
# então. Ver 00_Instrucoes/emergencias.md.
HISTORICO_EMERGENCIAS = DADOS_TRATADOS / "historico_emergencias.csv"
COLUNAS_HISTORICO = [
    "numero_emergencia", "om", "matricula_aeronave", "pn", "nomenclatura",
    "situacao", "tpemg", "data_abertura", "prazo_entrega", "dpe", "dias_atraso",
]

COLUNAS = [
    "om_emg", "om", "numero_emergencia", "pn", "nomenclatura", "categoria",
    "matricula_aeronave", "situacao", "tpemg", "data_abertura",
    "data_info", "quantidade", "unidade_medida", "prazo_entrega", "dpe",
    "atendido_cancelado", "dias_atraso", "dias_corridos", "estoque",
    "retirado_empresa_recibo_obrigatorio", "obs_coordenadoria_fiscal",
    "obs_vee_one", "provedor", "awb", "prev_entrega", "mensagem_operador",
]

# Truncamentos que já vêm assim na própria planilha de origem (não é um
# problema de extração) — ver emergencias.md.
SITUACOES_TRUNCADAS = {
    "Providência tom": "Providência tomada",
    "Aguardando solu": "Aguardando solução",
    "Atendido parcia": "Atendido parcialmente",
}


def parse_data(valor):
    if valor is None or valor == "":
        return None, None
    if hasattr(valor, "date"):
        return valor.date(), None
    texto = str(valor).strip()
    for fmt in ("%d/%m/%Y", "%m/%d/%Y"):
        try:
            return pd.to_datetime(texto, format=fmt).date(), None
        except ValueError:
            continue
    return texto, f"data em formato inesperado: '{texto}'"


def parse_inteiro(valor):
    try:
        return int(valor)
    except (ValueError, TypeError):
        return None


def extrair(historico_completo=False):
    """Se historico_completo=False (padrão): só emergências em aberto do
    provedor VEE ONE (os 3 filtros de sempre). Se True: TODO o histórico da
    planilha (abertas e concluídas, qualquer Atd/cancelada), filtrando só por
    Provedor = VEE ONE — usado por extrair_historico_completo()."""
    inconsistencias = []
    linhas = []

    wb = openpyxl.load_workbook(FONTE, data_only=True)
    ws = wb[ABA]

    for row in ws.iter_rows(min_row=3, max_col=27, values_only=True):
        if not row[0]:
            continue

        situacao_bruta = str(row[7] or "").strip()
        situacao = SITUACOES_TRUNCADAS.get(situacao_bruta, situacao_bruta)

        if str(row[22] or "").strip() != "VEE ONE":
            continue  # só interessa o provedor do Contrato 005 (VEE ONE)

        if not historico_completo:
            if situacao == "Emg concluída":
                continue  # ignorar emergências já concluídas — só interessa o que está em aberto
            if str(row[15] or "").strip():
                continue  # Atd/cancelada tem que estar em branco (só espaços/vazio)

        data_abertura, erro1 = parse_data(row[9])
        data_info, erro2 = parse_data(row[10])
        prazo_entrega, erro3 = parse_data(row[13])
        dpe, erro4 = parse_data(row[14])
        for erro in (erro1, erro2, erro3, erro4):
            if erro:
                inconsistencias.append(f"Emergência {row[2]}: {erro}")

        atendido_cancelado = str(row[15] or "").strip()

        linhas.append({
            "om_emg": row[0],
            "om": row[1],
            "numero_emergencia": row[2],
            "pn": row[3],
            "nomenclatura": row[4],
            "categoria": row[5],
            "matricula_aeronave": row[6],
            "situacao": situacao,
            "tpemg": row[8],
            "data_abertura": data_abertura,
            "data_info": data_info,
            "quantidade": parse_inteiro(row[11]),
            "unidade_medida": row[12],
            "prazo_entrega": prazo_entrega,
            "dpe": dpe,
            "atendido_cancelado": atendido_cancelado,
            "dias_atraso": parse_inteiro(row[16]),
            "dias_corridos": parse_inteiro(row[17]),
            "estoque": row[18],
            "retirado_empresa_recibo_obrigatorio": row[19],
            "obs_coordenadoria_fiscal": str(row[20] or "").replace("\n", " ").strip(),
            "obs_vee_one": str(row[21] or "").replace("\n", " ").strip(),
            "provedor": row[22],
            "awb": row[24],
            "prev_entrega": row[25],
            "mensagem_operador": row[26],
            "em_aberto": situacao != "Emg concluída" and not atendido_cancelado,
        })

    df = pd.DataFrame(linhas, columns=COLUNAS + ["em_aberto"])
    return df, inconsistencias


def main():
    DADOS_TRATADOS.mkdir(parents=True, exist_ok=True)
    df, inconsistencias = extrair()

    destino = DADOS_TRATADOS / "base_emergencias_tratada.xlsx"
    df.to_excel(destino, index=False, sheet_name="Emergencias")

    registrar_log(
        nome_execucao="extrair_emergencias",
        arquivos_lidos=[str(FONTE)],
        arquivos_gerados=[str(destino)],
        inconsistencias=inconsistencias,
        proximas_acoes=["Revisar datas com formato inesperado."] if inconsistencias else None,
    )

    print(f"{len(df)} emergências carregadas -> {destino}")
    if inconsistencias:
        print(f"{len(inconsistencias)} inconsistência(s) encontrada(s), ver log em 06_Logs/.")

    return df


def extrair_historico_completo():
    """Todo o histórico da planilha (abertas e concluídas, desde 2022),
    filtrando só por Provedor = VEE ONE — sem os filtros de 'em aberto' que
    `main()` aplica. Preparação pedida pelo Wallace em 2026-07-06 pra um uso
    futuro ainda não definido. Ver 00_Instrucoes/emergencias.md."""
    DADOS_TRATADOS.mkdir(parents=True, exist_ok=True)
    df, inconsistencias = extrair(historico_completo=True)

    destino = DADOS_TRATADOS / "historico_completo_emergencias.xlsx"
    df.to_excel(destino, index=False, sheet_name="Emergencias")

    registrar_log(
        nome_execucao="extrair_historico_completo_emergencias",
        arquivos_lidos=[str(FONTE)],
        arquivos_gerados=[str(destino)],
        inconsistencias=inconsistencias,
    )

    print(f"{len(df)} emergências (histórico completo, VEE ONE) -> {destino}")
    if inconsistencias:
        print(f"{len(inconsistencias)} inconsistência(s) encontrada(s), ver log em 06_Logs/.")

    return df


def _registrar_historico(df):
    """Acrescenta o snapshot de hoje das emergências em aberto — se já rodou
    hoje antes, substitui só as linhas de hoje (não duplica)."""
    hoje = datetime.now().date().isoformat()
    abertas = df[df["em_aberto"]]
    novo = abertas[COLUNAS_HISTORICO].copy()
    novo.insert(0, "data_snapshot", hoje)

    if HISTORICO_EMERGENCIAS.exists():
        historico = pd.read_csv(HISTORICO_EMERGENCIAS, dtype={"matricula_aeronave": str, "numero_emergencia": str})
        historico = historico[historico["data_snapshot"] != hoje]
        historico = pd.concat([historico, novo], ignore_index=True)
    else:
        historico = novo
    historico.to_csv(HISTORICO_EMERGENCIAS, index=False)


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
        # Mantém o histórico completo (aba usada pelo Cômputo Mensal e por
        # "Emergências Totais") sempre em dia — antes só era gerado sob
        # demanda e podia ficar desatualizado por dias (achado em 2026-07-08).
        extrair_historico_completo()
        estado.atualizar_estado(
            ESTADO_ATUALIZACOES, "emergencias",
            remote_modified_time=metadados["modifiedTime"],
            local_updated_at=datetime.now().isoformat(),
            status="atualizado",
            record_count=len(df),
            last_error=None,
        )
    except Exception as e:
        estado.atualizar_estado(ESTADO_ATUALIZACOES, "emergencias", status="erro", last_error=str(e))
        raise
    return estado.obter_entrada(ESTADO_ATUALIZACOES, "emergencias")


if __name__ == "__main__":
    import sys
    if "--atualizar-do-drive" in sys.argv:
        atualizar_do_drive()
    else:
        main()
