"""
Carrega a planilha "Devoluções" (Google Sheets, aba "DEVOLUÇÃO") e gera
02_Dados_Tratados/base_devolucoes_tratada.xlsx — tela "Empréstimos" no site
(nome pedido pelo Wallace em 2026-07-09; a fonte se chama "Devoluções", mas
a tela é sobre material emprestado/devolvido pra manutenção).

Sem filtro de status na extração — mas pula linhas sem Part Number
(linhas "fantasma" com só um número de ordem arrastado por fórmula e
mais nada preenchido; bug real visto em 2026-07-13, ~330 itens reais,
ver 00_Instrucoes/emprestimos.md).

A aba tem 2 colunas "QTD" (uma em texto com unidade, ex. "01 EA", outra só o
número) e 2 colunas "Status" (uma é detalhe de entrega em texto livre, a
última é o status real OK/Pendente) — nomes de coluna duplicados na
planilha original, renomeados aqui pra ficar claro.
"""


import openpyxl
import pandas as pd

from common import BASES_ORIGINAIS, DADOS_TRATADOS, ESTADO_ATUALIZACOES, registrar_log
from shared import drive_sync, estado, horario

FONTE = BASES_ORIGINAIS / "Devolucoes" / "Devolucoes (Google Sheets).xlsx"
ABA = "DEVOLUÇÃO"

# Ver 00_Instrucoes/emprestimos.md — planilha Google nativa "Devoluções".
DRIVE_FILE_ID = "1czUWXVjQt7fPz7GJgdPp3rsxPn_5Uck44voBsJIiRWI"

COLUNAS = [
    "numero_ordem", "part_number", "descricao", "sn_lt", "categoria",
    "quantidade_texto", "quantidade", "pedido_emg", "motivo", "pj",
    "pedido_envio", "anv", "destino", "nf_gmm", "rastreio", "pn_devolvido",
    "detalhe_entrega", "numero_rc", "nf_devolucao_vee_one", "data_devolucao",
    "observacao_fiscal", "observacao_empresa", "status",
]

# Snapshot diário dos itens (numero_ordem é único por linha, confirmado em
# 2026-07-10) — mesmo padrão de Emergências/RAC/MTA/TPJL. Só existe
# histórico a partir de quando essa gravação começou. Ver
# 00_Instrucoes/analise_periodo.md. "quantidade" acrescentada em 2026-07-23
# pra alimentar "O que mudou de um dia pro outro"/"Histórico da semana" em
# emprestimos.py com quantidade, não só contagem de linhas — snapshots de
# antes dessa data não têm essa coluna (fica NaN, contam como 1 na tela).
HISTORICO_DEVOLUCOES = DADOS_TRATADOS / "historico_devolucoes.csv"
COLUNAS_HISTORICO = [
    "numero_ordem", "part_number", "categoria", "destino", "anv", "status", "quantidade",
]


def _texto(valor):
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _normalizar_status(valor):
    texto = _texto(valor)
    if texto is None:
        return "Pendente"
    if texto.strip().lower() == "ok":
        return "OK"
    return texto


def extrair():
    inconsistencias = []
    linhas = []

    wb = openpyxl.load_workbook(FONTE, data_only=True)
    ws = wb[ABA]

    for i, row in enumerate(ws.iter_rows(min_row=3, max_col=23, values_only=True), start=3):
        # A coluna "Nº de Ordem" (row[0]) vem preenchida por arrasto de
        # fórmula bem além dos itens reais (linhas 332-425 têm só o
        # número sequencial, tudo mais em branco) — bug real visto em
        # 2026-07-13, achado pelo Wallace ("acho que são 416 linhas não,
        # vai até 300 e pouco"). Exigir Part Number também preenchido pra
        # considerar linha real.
        if not row[0] or not row[1]:
            continue

        pedido_emg = row[7]
        if isinstance(pedido_emg, float):
            pedido_emg = str(int(pedido_emg))
        elif pedido_emg is not None:
            pedido_emg = str(pedido_emg).strip()

        linhas.append({
            "numero_ordem": _texto(row[0]),
            "part_number": _texto(row[1]),
            "descricao": _texto(row[2]),
            "sn_lt": _texto(row[3]),
            "categoria": _texto(row[4]),
            "quantidade_texto": _texto(row[5]),
            "quantidade": row[6],
            "pedido_emg": pedido_emg,
            "motivo": _texto(row[8]),
            "pj": _texto(row[9]),
            "pedido_envio": row[10],
            "anv": _texto(row[11]),
            "destino": _texto(row[12]),
            "nf_gmm": _texto(row[13]),
            "rastreio": _texto(row[14]),
            "pn_devolvido": _texto(row[15]),
            "detalhe_entrega": _texto(row[16]),
            "numero_rc": _texto(row[17]),
            "nf_devolucao_vee_one": _texto(row[18]),
            "data_devolucao": row[19],
            "observacao_fiscal": _texto(row[20]),
            "observacao_empresa": _texto(row[21]),
            "status": _normalizar_status(row[22]),
        })

    df = pd.DataFrame(linhas, columns=COLUNAS)
    return df, inconsistencias


def main():
    DADOS_TRATADOS.mkdir(parents=True, exist_ok=True)
    df, inconsistencias = extrair()

    destino = DADOS_TRATADOS / "base_devolucoes_tratada.xlsx"
    df.to_excel(destino, index=False, sheet_name="Devolucoes")

    registrar_log(
        nome_execucao="extrair_devolucoes",
        arquivos_lidos=[str(FONTE)],
        arquivos_gerados=[str(destino)],
        inconsistencias=inconsistencias,
    )

    print(f"{len(df)} itens carregados -> {destino}")
    if inconsistencias:
        print(f"{len(inconsistencias)} inconsistência(s) encontrada(s), ver log em 06_Logs/.")

    return df


def _registrar_historico(df):
    """Acrescenta o snapshot de hoje (1 linha por item) — se já rodou hoje
    antes, substitui só as linhas de hoje (não duplica)."""
    hoje = horario.hoje_br().isoformat()
    novo = df[COLUNAS_HISTORICO].copy()
    novo.insert(0, "data_snapshot", hoje)

    if HISTORICO_DEVOLUCOES.exists():
        historico = pd.read_csv(HISTORICO_DEVOLUCOES, dtype={"numero_ordem": str})
        historico = historico[historico["data_snapshot"] != hoje]
        historico = pd.concat([historico, novo], ignore_index=True)
    else:
        historico = novo
    historico.to_csv(HISTORICO_DEVOLUCOES, index=False)


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
            ESTADO_ATUALIZACOES, "devolucoes",
            remote_modified_time=metadados["modifiedTime"],
            local_updated_at=horario.agora_br().isoformat(),
            status="atualizado",
            record_count=len(df),
            last_error=None,
        )
    except Exception as e:
        estado.atualizar_estado(ESTADO_ATUALIZACOES, "devolucoes", status="erro", last_error=str(e))
        raise
    return estado.obter_entrada(ESTADO_ATUALIZACOES, "devolucoes")


if __name__ == "__main__":
    import sys
    if "--atualizar-do-drive" in sys.argv:
        atualizar_do_drive()
    else:
        main()
