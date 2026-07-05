"""
Extrai a planilha de pagamentos (aba 'CONTROLE DE PAGAMENTOS', complementada pela
aba 'EMPENHOS') e gera 02_Dados_Tratados/base_pagamentos_tratada.xlsx.

Regras de tratamento vêm de 00_Instrucoes/pagamentos.md.
"""

import re
import warnings
from datetime import datetime

import openpyxl
import pandas as pd

from common import XLSX_PAGAMENTOS, DADOS_TRATADOS, ESTADO_ATUALIZACOES, registrar_log
from shared import drive_sync, estado

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

# Ver 00_Instrucoes/atualizacoes.md — planilha Google nativa
# "005/CELOG-PAMALS/2025 online", dono wallacedellaney@gmail.com.
DRIVE_FILE_ID = "1zV_SQKlcXVYeaqCbV0X-PiWnzdzOZPt5esaXp_4k6_o"

# Colunas C..N da aba Controle de Pagamentos (mesma estrutura nos dois blocos de
# lançamentos: mensal e por módulo/orçamento). Ver pagamentos.md.
COLS_PAGAMENTO = [
    "modulo", "referencia", "numero_recibo", "numero_nota_fiscal", "data",
    "empenho", "observacao", "vencimento", "valor_nfs", "ordem_pagamento",
    "faturado", "pendente",
]


def extrair_contrato(ws):
    return {
        "numero_contrato": ws["D5"].value,
        "ug_executora": ws["E5"].value,
        "ug_responsavel": ws["F5"].value,
        "ug_fiscalizadora": ws["G5"].value,
        "status": ws["J5"].value,
        "valor_total_contrato": ws["N5"].value,
        "valor_a_empenhar": ws["O5"].value,
        "valor_empenhado": ws["P5"].value,
        "valor_liquidado": ws["Q5"].value,
        "saldo_a_faturar": ws["R5"].value,
        "fornecedor": ws["S5"].value,
    }


def parse_valor_monetario(valor):
    """Alguns lançamentos vêm como número, outros como texto 'R$ 1.234,56' (ver pagamentos.md)."""
    if pd.isna(valor):
        return None, False
    if isinstance(valor, (int, float)):
        return float(valor), False
    texto = str(valor).replace("R$", "").strip().replace(".", "").replace(",", ".")
    try:
        return float(texto), True
    except ValueError:
        return None, True


def padronizar_valores_monetarios(df, inconsistencias):
    for coluna in ("valor_nfs", "faturado", "pendente"):
        valores_convertidos = []
        for idx, valor in df[coluna].items():
            novo_valor, era_texto = parse_valor_monetario(valor)
            valores_convertidos.append(novo_valor)
            if era_texto:
                inconsistencias.append(
                    f"Coluna '{coluna}' na referência {df.at[idx, 'referencia']} veio como texto "
                    f"('{valor}') em vez de número; convertido para {novo_valor}."
                )
        df[coluna] = valores_convertidos
    return df


def situacao_pagamento(row):
    if pd.notna(row["ordem_pagamento"]):
        return "Pago"
    if pd.notna(row["valor_nfs"]) or pd.notna(row["faturado"]):
        return "Faturado, aguardando pagamento"
    if pd.notna(row["pendente"]):
        return "Pendente"
    return "Sem lançamento"


def extrair_bloco(ws, primeira_linha, ultima_linha):
    linhas = []
    for row in ws.iter_rows(min_row=primeira_linha, max_row=ultima_linha, min_col=3, max_col=14, values_only=True):
        linhas.append(dict(zip(COLS_PAGAMENTO, row)))
    df = pd.DataFrame(linhas)
    df["modulo"] = df["modulo"].ffill()
    return df


def extrair_empenhos(wb):
    ws = wb["EMPENHOS"]
    empenhos = {}
    for row in ws.iter_rows(min_row=4, values_only=True):
        ne = row[0]
        if not ne:
            continue
        empenhos[str(ne).strip()] = {
            "valor_empenhado": row[10],   # coluna K
            "saldo": row[11],             # coluna L
            "responsavel": row[26],       # coluna AA
            "justificativa": row[27],     # coluna AB
        }
    return empenhos


def empenhos_para_dataframe(empenhos):
    linhas = [{"numero_empenho": ne, **dados} for ne, dados in empenhos.items()]
    return pd.DataFrame(linhas, columns=["numero_empenho", "valor_empenhado", "saldo", "responsavel", "justificativa"])


def cruzar_empenhos(df, empenhos):
    saldos, valores, responsaveis, justificativas = [], [], [], []
    inconsistencias = []

    for _, row in df.iterrows():
        empenho_cell = row["empenho"]
        nes = [n.strip() for n in re.split(r"[,\n]", str(empenho_cell)) if n.strip()] if pd.notna(empenho_cell) else []

        encontrados = [empenhos[ne] for ne in nes if ne in empenhos]
        nao_encontrados = [ne for ne in nes if ne and ne not in empenhos]
        for ne in nao_encontrados:
            inconsistencias.append(f"Empenho '{ne}' (referência {row['referencia']}) não encontrado na aba EMPENHOS.")

        saldos.append(sum(e["saldo"] for e in encontrados if e["saldo"]) or None)
        valores.append(sum(e["valor_empenhado"] for e in encontrados if e["valor_empenhado"]) or None)
        responsaveis.append("; ".join(sorted({e["responsavel"] for e in encontrados if e["responsavel"]})) or None)
        justificativas.append("; ".join(sorted({e["justificativa"] for e in encontrados if e["justificativa"]})) or None)

    df["empenho_saldo"] = saldos
    df["empenho_valor_empenhado"] = valores
    df["empenho_responsavel"] = responsaveis
    df["empenho_justificativa"] = justificativas
    return df, inconsistencias


def main():
    DADOS_TRATADOS.mkdir(parents=True, exist_ok=True)
    inconsistencias = []

    wb = openpyxl.load_workbook(XLSX_PAGAMENTOS, data_only=True)
    ws = wb["CONTROLE DE PAGAMENTOS"]

    contrato = extrair_contrato(ws)

    bloco_mensal = extrair_bloco(ws, 9, 26)
    bloco_mensal["tipo_registro"] = "mensal"

    bloco_modulo = extrair_bloco(ws, 28, 39)
    bloco_modulo["tipo_registro"] = "orcamento"

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning)
        df = pd.concat([bloco_mensal, bloco_modulo], ignore_index=True)
    df = df[df[["numero_recibo", "numero_nota_fiscal", "valor_nfs", "faturado", "pendente"]].notna().any(axis=1)]
    df = df.reset_index(drop=True)

    df = padronizar_valores_monetarios(df, inconsistencias)
    df["situacao"] = df.apply(situacao_pagamento, axis=1)

    empenhos = extrair_empenhos(wb)
    df, inconsistencias_empenho = cruzar_empenhos(df, empenhos)
    inconsistencias.extend(inconsistencias_empenho)
    df_empenhos = empenhos_para_dataframe(empenhos)

    destino = DADOS_TRATADOS / "base_pagamentos_tratada.xlsx"
    with pd.ExcelWriter(destino) as writer:
        pd.DataFrame([contrato]).to_excel(writer, index=False, sheet_name="Contrato")
        df.to_excel(writer, index=False, sheet_name="Pagamentos")
        df_empenhos.to_excel(writer, index=False, sheet_name="Empenhos")

    registrar_log(
        nome_execucao="extrair_pagamentos",
        arquivos_lidos=[str(XLSX_PAGAMENTOS)],
        arquivos_gerados=[str(destino)],
        inconsistencias=inconsistencias,
        proximas_acoes=["Revisar empenhos não encontrados na aba EMPENHOS."] if inconsistencias else None,
    )

    print(f"{len(df)} lançamentos de pagamento extraídos -> {destino}")
    if inconsistencias:
        print(f"{len(inconsistencias)} inconsistência(s) encontrada(s), ver log em 06_Logs/.")

    return df


def atualizar_do_drive():
    """Busca a versão mais recente direto do Google Drive, sobrescreve a
    cópia local e reprocessa. Ver 00_Instrucoes/atualizacoes.md."""
    try:
        metadados = drive_sync.obter_metadados(DRIVE_FILE_ID)
        conteudo = drive_sync.baixar_arquivo(DRIVE_FILE_ID, exportar_como=drive_sync.XLSX_MIME)
        XLSX_PAGAMENTOS.parent.mkdir(parents=True, exist_ok=True)
        XLSX_PAGAMENTOS.write_bytes(conteudo)
        df = main()
        estado.atualizar_estado(
            ESTADO_ATUALIZACOES, "pagamentos",
            remote_modified_time=metadados["modifiedTime"],
            local_updated_at=datetime.now().isoformat(),
            status="atualizado",
            record_count=len(df),
            last_error=None,
        )
    except Exception as e:
        estado.atualizar_estado(ESTADO_ATUALIZACOES, "pagamentos", status="erro", last_error=str(e))
        raise
    return estado.obter_entrada(ESTADO_ATUALIZACOES, "pagamentos")


if __name__ == "__main__":
    import sys
    if "--atualizar-do-drive" in sys.argv:
        atualizar_do_drive()
    else:
        main()
