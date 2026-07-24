"""
Carrega as planilhas "TPOB - Controle CABW 2025" e "TPOB - Controle CABW
2026" (Google Sheets, aba "COORDENADORES") e gera
02_Dados_Tratados/base_tpjl_tratada.xlsx — só registros PJT = U8. Ver
00_Instrucoes/tpjl.md.

2025 e 2026 ficam SEPARADOS (decisão do Wallace em 2026-07-09) — cada ano
numa aba própria do arquivo tratado ("TPJL_2025"/"TPJL_2026"), sem fundir
numa tabela única. Cada ano tem seu próprio mapeamento de coluna (ver
projetos/config/tpjl_config.py — a aba de 2025 tem 2 colunas extras sem uso
real que a de 2026 não tem).
"""

from datetime import datetime

import openpyxl
import pandas as pd

from common import BASES_ORIGINAIS, DADOS_TRATADOS, ESTADO_ATUALIZACOES, registrar_log
from shared import drive_sync, estado, horario

from projetos.config import tpjl_config as cfg
from projetos.regras.tpjl_regras import normalizar, status_atual, situacao_previsao

PASTA_FONTE = BASES_ORIGINAIS / "TPJL"
ARQUIVOS_FONTE = {
    2025: PASTA_FONTE / "TPOB - Controle CABW 2025 (Google Sheets).xlsx",
    2026: PASTA_FONTE / "TPOB - Controle CABW 2026 (Google Sheets).xlsx",
}

HISTORICO_TPJL = DADOS_TRATADOS / "historico_tpjl.csv"
COLUNAS_HISTORICO = ["ano", "numero_requisicao", "pn", "status_atual", "valor_total", "situacao_previsao", "dias_atraso"]

COLUNAS = [
    "numero_requisicao", "nd", "pjt", "pn", "descricao", "qtd", "valor_unit", "valor_total",
    "status_comprar", "status_11g", "status", "status_atual",
    "previsao_empenho", "situacao_previsao", "dias_atraso",
    "dpe", "observacao_coordenadores",
]


def _texto(valor):
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _numero(valor, contexto, inconsistencias, campo):
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    inconsistencias.append(f"{campo} inválido (não numérico) em {contexto}: {valor!r} — não somado.")
    return None


def _data(valor):
    """Datas válidas viram datetime; texto (ex. "IMEDIATO") ou vazio ficam
    como estão — não pode derrubar a extração (ver 00_Instrucoes/tpjl.md)."""
    if isinstance(valor, datetime):
        return valor
    return valor


def _extrair_ano(ano, inconsistencias):
    config = cfg.FONTES[ano]
    caminho = ARQUIVOS_FONTE[ano]
    col = config["colunas"]

    wb = openpyxl.load_workbook(caminho, data_only=True)
    ws = wb[cfg.ABA]

    linhas = []
    lidos = 0
    for i, row in enumerate(ws.iter_rows(min_row=2, max_col=config["max_col"], values_only=True), start=2):
        if row[col["numero_requisicao"]] is None:
            continue
        lidos += 1
        pjt = _texto(row[col["pjt"]])
        if normalizar(pjt) != cfg.PJT_FILTRO:
            continue

        contexto = f"{config['planilha']}, linha {i} (Nº Requisição={row[col['numero_requisicao']]})"
        status_val = _texto(row[col["status"]])
        status_11g_val = _texto(row[col["status_11g"]])
        status_comprar_val = _texto(row[col["status_comprar"]])
        atual = status_atual(status_val, status_11g_val, status_comprar_val)
        previsao = _data(row[col["previsao_empenho"]])
        sit_previsao, dias_atraso = situacao_previsao(previsao, atual)

        linhas.append({
            "numero_requisicao": _texto(row[col["numero_requisicao"]]),
            "nd": _texto(row[col["nd"]]),
            "pjt": pjt,
            "pn": _texto(row[col["pn"]]),
            "descricao": _texto(row[col["descricao"]]),
            "qtd": _numero(row[col["qtd"]], contexto, inconsistencias, "QTD"),
            "valor_unit": _numero(row[col["valor_unit"]], contexto, inconsistencias, "Valor Unit"),
            "valor_total": _numero(row[col["valor_total"]], contexto, inconsistencias, "Valor Total"),
            "status_comprar": status_comprar_val,
            "status_11g": status_11g_val,
            "status": status_val,
            "status_atual": atual,
            "previsao_empenho": previsao,
            "situacao_previsao": sit_previsao,
            "dias_atraso": dias_atraso,
            "dpe": _data(row[col["dpe"]]),
            "observacao_coordenadores": _texto(row[col["observacao_coordenadores"]]),
        })

    df = pd.DataFrame(linhas, columns=COLUNAS)
    return df, lidos


def extrair():
    inconsistencias = []
    resultados = {}
    for ano in cfg.FONTES:
        df, lidos = _extrair_ano(ano, inconsistencias)
        resultados[ano] = (df, lidos)
    return resultados, inconsistencias


def main():
    DADOS_TRATADOS.mkdir(parents=True, exist_ok=True)
    resultados, inconsistencias = extrair()

    destino = DADOS_TRATADOS / "base_tpjl_tratada.xlsx"
    with pd.ExcelWriter(destino) as writer:
        for ano, (df, _lidos) in resultados.items():
            df.to_excel(writer, index=False, sheet_name=f"TPJL_{ano}")

    registrar_log(
        nome_execucao="extrair_tpjl",
        arquivos_lidos=[str(c) for c in ARQUIVOS_FONTE.values()],
        arquivos_gerados=[str(destino)],
        inconsistencias=inconsistencias,
    )

    for ano, (df, lidos) in resultados.items():
        print(f"{ano}: {len(df)} requisições U8 válidas de {lidos} linhas lidas -> {destino} (aba TPJL_{ano})")
    if inconsistencias:
        print(f"{len(inconsistencias)} inconsistência(s) encontrada(s), ver log em 06_Logs/.")

    return resultados


def _registrar_historico(resultados):
    """Acrescenta o snapshot de hoje (1 linha por requisição U8, dos 2
    anos juntos) — se já rodou hoje antes, substitui só as linhas de hoje
    (não duplica). Base pra barra temporal pedida pelo Wallace em
    2026-07-09 — só existe história a partir do dia em que essa função
    passou a rodar."""
    hoje = horario.hoje_br().isoformat()
    partes = []
    for ano, (df, _lidos) in resultados.items():
        parte = df.copy()
        parte["ano"] = ano
        partes.append(parte[COLUNAS_HISTORICO])
    novo = pd.concat(partes, ignore_index=True)
    novo.insert(0, "data_snapshot", hoje)

    if HISTORICO_TPJL.exists():
        historico = pd.read_csv(HISTORICO_TPJL)
        historico = historico[historico["data_snapshot"] != hoje]
        historico = pd.concat([historico, novo], ignore_index=True)
    else:
        historico = novo
    historico.to_csv(HISTORICO_TPJL, index=False)


def atualizar_do_drive():
    """Busca a versão mais recente das 2 planilhas (2025 e 2026) no Google
    Drive, sobrescreve as cópias locais e reprocessa. Se uma falhar, a outra
    continua sendo tentada — mas qualquer falha marca status "erro" no
    estado. Ver 00_Instrucoes/atualizacoes.md (raiz)."""
    erros = []
    metadados_por_ano = {}
    for ano, config in cfg.FONTES.items():
        try:
            metadados_por_ano[ano] = drive_sync.obter_metadados(config["drive_file_id"])
            conteudo = drive_sync.baixar_arquivo(config["drive_file_id"], exportar_como=drive_sync.XLSX_MIME)
            ARQUIVOS_FONTE[ano].parent.mkdir(parents=True, exist_ok=True)
            ARQUIVOS_FONTE[ano].write_bytes(conteudo)
        except Exception as e:
            erros.append(f"{ano}: {e}")

    try:
        resultados = main()
        _registrar_historico(resultados)
    except Exception as e:
        estado.atualizar_estado(ESTADO_ATUALIZACOES, "tpjl", status="erro", last_error=str(e))
        raise

    total = sum(len(df) for df, _ in resultados.values())
    if erros:
        estado.atualizar_estado(
            ESTADO_ATUALIZACOES, "tpjl", status="erro",
            last_error="; ".join(erros),
            local_updated_at=horario.agora_br().isoformat(),
            record_count=total,
        )
        raise RuntimeError("; ".join(erros))

    modificado_mais_recente = max(m["modifiedTime"] for m in metadados_por_ano.values())
    estado.atualizar_estado(
        ESTADO_ATUALIZACOES, "tpjl",
        remote_modified_time=modificado_mais_recente,
        local_updated_at=horario.agora_br().isoformat(),
        status="atualizado",
        record_count=total,
        record_count_2025=len(resultados[2025][0]),
        record_count_2026=len(resultados[2026][0]),
        last_error=None,
    )
    return estado.obter_entrada(ESTADO_ATUALIZACOES, "tpjl")


if __name__ == "__main__":
    import sys
    if "--atualizar-do-drive" in sys.argv:
        atualizar_do_drive()
    else:
        main()
