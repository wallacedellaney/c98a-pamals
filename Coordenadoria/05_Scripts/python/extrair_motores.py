"""
Motores C-98 — extração da planilha "MOTORES C-98" (Google Sheets do Wallace,
pasta pessoal), 4 das 15 abas (escolhidas pelo Wallace em 2026-07-14 — as
demais são cenário/simulação, rascunho ou instrução, não dado):

- **SILOMS** ("Situacao" no arquivo tratado) — situação atual de cada motor
  (por OM/PN/SN), puxada do sistema SILOMS.
- **hélice** ("Helice") — mesma estrutura da SILOMS, só que de hélices.
- **Diagonal Nova** ("Diagonal") — projeção mês a mês (2025-2030) de quando
  cada motor vai bater TBO/HSI, com o comentário/nota da célula (quando
  existir) trazido junto — pedido do Wallace: "ja vi que tem comentarios
  dentro da caixas de tbo, hsi. vamos usar essas informacoes tb".
- **OS** — ordens de serviço de motor em andamento.

Gera 02_Dados_Tratados/base_motores_tratada.xlsx (4 abas: Situacao/Diagonal/
OS/Helice). Ver 00_Instrucoes/motores.md — inclui as decisões de nomeação
das colunas ambíguas (3 colunas "DATA" repetidas com nomes diferentes na
planilha original de SILOMS/Helice — significado exato não confirmado com
o Wallace, nomeadas data_1/data_2 defensivamente).

Fonte é uma planilha PESSOAL do Wallace (dono fred_o_m@hotmail.com),
compartilhada com a conta de serviço em 2026-07-15 — entrou na automação
de 2 em 2h (`atualizar_do_drive()`, ver shared/executar_atualizacao.py).
"""

from datetime import datetime, timedelta

import openpyxl
import pandas as pd

from common import BASES_ORIGINAIS, DADOS_TRATADOS, ESTADO_ATUALIZACOES, registrar_log
from shared import drive_sync, estado

ARQUIVO_FONTE = BASES_ORIGINAIS / "Motores" / "MOTORES_C98.xlsx"

# Planilha pessoal do Wallace — compartilhada com a conta de serviço em
# 2026-07-15 ("ja compartilhei a planilha"), entrou na automação de 2 em 2h.
DRIVE_FILE_ID = "1UJDXA6jG4va51Tpnjd6DrV1kqPMnbY9w-TYlh8Ub0rM"

HISTORICO_SITUACAO = DADOS_TRATADOS / "historico_motores_situacao.csv"
COLUNAS_HISTORICO_SITUACAO = [
    "om", "pn", "sn", "matricula", "parcial_tso", "totais_tsn", "pct_tbo_voada",
    "tbo", "condicao", "motivo",
]

HISTORICO_DIAGONAL = DADOS_TRATADOS / "historico_motores_diagonal.csv"
COLUNAS_HISTORICO_DIAGONAL = ["serial", "anv", "ano", "mes", "evento", "comentario"]

# Índice de coluna (0-based) por campo — mapeado à mão a partir da estrutura
# real de cada aba (não são iguais entre si: SILOMS tem TBO antes de
# Matr.ANV, hélice tem a ordem invertida). "data_1"/"data_2" são as 2
# primeiras das 3 colunas "DATA" repetidas na fonte — significado exato não
# confirmado com o Wallace.
COL_SITUACAO = {
    "om": 6, "projeto": 7, "pn": 8, "tipo": 9, "fabricante": 10,
    "mnt_nivel_parque": 11, "estoque_utilizavel": 12, "estoque_reparavel": 13,
    "sn": 14, "controle": 15, "parcial_tso": 16, "totais_tsn": 17,
    "pct_tbo_voada": 18, "matricula": 19, "tbo": 20,
    "data_1": 21, "data_2": 22, "recolhimento": 23, "condicao": 24,
    "numero_doc": 25, "data_doc": 26, "motivo": 27,
}
LINHA_INICIO_SITUACAO = 4

COL_HELICE = {
    "om": 0, "projeto": 1, "pn": 2, "tipo": 3, "fabricante": 4,
    "mnt_nivel_parque": 5, "estoque_utilizavel": 6, "estoque_reparavel": 7,
    "sn": 8, "controle": 9, "parcial_tso": 10, "totais_tsn": 11,
    "pct_tbo_voada": 12, "tbo": 13, "matricula": 14,
    "data_1": 15, "data_2": 16, "recolhimento": 17, "condicao": 18,
    "numero_doc": 19, "data_doc": 20, "motivo": 21,
}
LINHA_INICIO_HELICE = 3

COL_OS = {
    "os": 3, "os_origem": 4, "tipo": 5, "status": 6, "data_status": 7,
    "projeto": 8, "data_recebimento": 9, "pn": 10, "cff": 11, "nomenclatura": 12,
    "sn": 13, "matricula": 14, "lote": 15, "item_nao_listado": 16, "solicitante": 17,
    "quantidade": 18, "data_inicio_prev": 19, "data_fim_prev": 20,
    "data_inicio_real": 21, "data_fim_real": 22, "prioridade": 23, "emergencia": 24,
    "unidade_exec": 25, "setor_exec": 26, "solicitacao": 27, "unidade_solic": 28,
    "setor_solic": 29, "pessoa_solicitante": 30, "comentarios": 31,
}
LINHA_INICIO_OS = 4
CAMPOS_DATA_OS = {"data_status", "data_recebimento", "data_inicio_prev", "data_fim_prev", "data_inicio_real", "data_fim_real"}

MESES_ABREV_FONTE = ["JAN", "FEV", "MAR", "ABR", "MAIO", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]
COL_DIAGONAL_META = {"serial": 0, "anv": 1, "tso": 2, "hr_disp": 3, "voo_mensal": 4, "hr_fim_ano_anv": 5, "mes_disp": 6}
COL_DIAGONAL_PRIMEIRO_MES = 7
COL_DIAGONAL_ULTIMA_COLUNA = 79
LINHA_ANO_DIAGONAL = 2
LINHA_MES_DIAGONAL = 3
LINHA_INICIO_DIAGONAL = 4


def _numero(valor):
    """Colunas de horas de motor vêm como datetime.timedelta (Excel/Sheets
    trata "horas:minutos" como duração) — convertido pra float de horas.
    Já numérico passa direto; texto/vazio vira None."""
    if isinstance(valor, timedelta):
        return round(valor.total_seconds() / 3600, 2)
    if isinstance(valor, (int, float)):
        return float(valor)
    return None


def _texto(valor):
    if valor is None:
        return None
    if isinstance(valor, str):
        texto = valor.strip()
        return texto or None
    return valor


def _data(valor):
    return valor if hasattr(valor, "strftime") else None


def _texto_id(valor):
    """PN/SN/Matrícula às vezes vêm como número puro (ex.: 3044000.0) e às
    vezes como texto alfanumérico (ex.: "3104100-01") na mesma coluna — força
    string sempre, sem ".0" no final, pra não misturar tipo na mesma coluna
    (isso quebra o `st.dataframe`/Arrow e a ordenação, mesmo bug já visto em
    outras áreas — ver `ordenar_unicos` no Contrato 005)."""
    if valor is None:
        return None
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    texto = str(valor).strip()
    return texto or None


CAMPOS_HORA = {"parcial_tso", "totais_tsn", "tbo"}
CAMPOS_DATA_SITUACAO = {"data_1", "data_2", "data_doc"}
CAMPOS_ID = {"pn", "sn", "matricula", "numero_doc", "recolhimento", "solicitacao", "emergencia"}


def _extrair_situacao_generico(ws, colunas, linha_inicio):
    linhas = []
    for row in ws.iter_rows(min_row=linha_inicio, values_only=True):
        om = row[colunas["om"]] if colunas["om"] < len(row) else None
        if om in (None, ""):
            continue
        registro = {}
        for campo, idx in colunas.items():
            valor = row[idx] if idx < len(row) else None
            if campo in CAMPOS_HORA:
                registro[campo] = _numero(valor)
            elif campo in CAMPOS_DATA_SITUACAO:
                registro[campo] = _data(valor)
            elif campo in CAMPOS_ID:
                registro[campo] = _texto_id(valor)
            else:
                registro[campo] = _texto(valor)
        linhas.append(registro)
    return pd.DataFrame(linhas, columns=list(colunas.keys()))


def _extrair_os(wb, inconsistencias):
    ws = wb["OS"]
    linhas = []
    ignoradas = 0
    for row in ws.iter_rows(min_row=LINHA_INICIO_OS, values_only=True):
        valor_os = row[COL_OS["os"]] if COL_OS["os"] < len(row) else None
        if valor_os in (None, ""):
            continue
        if not isinstance(valor_os, (int, float)):
            ignoradas += 1  # repetição de cabeçalho/sub-tabela por unidade executante — estrutural, não inconsistência
            continue
        registro = {}
        for campo, idx in COL_OS.items():
            valor = row[idx] if idx < len(row) else None
            if campo in CAMPOS_DATA_OS:
                registro[campo] = _data(valor)
            elif campo in CAMPOS_ID:
                registro[campo] = _texto_id(valor)
            else:
                registro[campo] = _texto(valor)
        linhas.append(registro)
    return pd.DataFrame(linhas, columns=list(COL_OS.keys()))


def _numero_ou_none(valor):
    """'#N/A' (texto de fórmula do Sheets) e False (marcador de ANV vazio)
    viram None — o resto passa por `_numero` (converte timedelta em horas)."""
    if valor in (None, "", False) or (isinstance(valor, str) and valor.strip().upper() in ("#N/A", "#N/D")):
        return None
    return _numero(valor)


def _extrair_diagonal_metadados(wb):
    """1 linha por motor (serial) com os campos de planejamento já calculados
    na própria planilha: TSO, Hr disp (horas disponíveis até o próximo
    evento), Voo mensal (média mensal de horas de voo assumida) e Mês disp
    (= Hr disp / Voo mensal). Pedido do Wallace em 2026-07-14/15: expor
    "Voo mensal" como campo editável na Diagonal de Manutenção, pra poder
    simular "e se eu voar mais/menos por mês" sem mexer na planilha
    original (essa fica sempre fixa, seguindo o histórico real)."""
    ws = wb["Diagonal Nova"]
    linhas = []
    for row in ws.iter_rows(min_row=LINHA_INICIO_DIAGONAL, values_only=True):
        serial_valor = row[COL_DIAGONAL_META["serial"]] if COL_DIAGONAL_META["serial"] < len(row) else None
        if not isinstance(serial_valor, str):
            continue
        linhas.append({
            "serial": _texto(serial_valor),
            "anv": _numero_ou_none(row[COL_DIAGONAL_META["anv"]]),
            "tso": _numero_ou_none(row[COL_DIAGONAL_META["tso"]]),
            "hr_disp": _numero_ou_none(row[COL_DIAGONAL_META["hr_disp"]]),
            "voo_mensal": _numero_ou_none(row[COL_DIAGONAL_META["voo_mensal"]]),
            "hr_fim_ano_anv": _numero_ou_none(row[COL_DIAGONAL_META["hr_fim_ano_anv"]]),
            "mes_disp": _numero_ou_none(row[COL_DIAGONAL_META["mes_disp"]]),
        })
    return pd.DataFrame(linhas, columns=["serial", "anv", "tso", "hr_disp", "voo_mensal", "hr_fim_ano_anv", "mes_disp"])


def _extrair_diagonal(wb, inconsistencias):
    ws = wb["Diagonal Nova"]
    linha_ano = [c.value for c in ws[LINHA_ANO_DIAGONAL]]
    linha_mes = [c.value for c in ws[LINHA_MES_DIAGONAL]]

    mapa_mes = {}
    ano_atual = None
    for idx in range(COL_DIAGONAL_PRIMEIRO_MES, COL_DIAGONAL_ULTIMA_COLUNA):
        if idx < len(linha_ano) and linha_ano[idx] is not None:
            ano_atual = int(linha_ano[idx])
        mes_nome = str(linha_mes[idx]).strip() if idx < len(linha_mes) and linha_mes[idx] else None
        if mes_nome in MESES_ABREV_FONTE:
            mapa_mes[idx] = (ano_atual, MESES_ABREV_FONTE.index(mes_nome) + 1)

    linhas = []
    for row in ws.iter_rows(min_row=LINHA_INICIO_DIAGONAL):
        serial_valor = row[COL_DIAGONAL_META["serial"]].value if COL_DIAGONAL_META["serial"] < len(row) else None
        if not isinstance(serial_valor, str):
            continue
        anv_valor = row[COL_DIAGONAL_META["anv"]].value if COL_DIAGONAL_META["anv"] < len(row) else None
        for idx, (ano, mes) in mapa_mes.items():
            if idx >= len(row):
                continue
            cell = row[idx]
            if cell.value in (None, ""):
                continue
            linhas.append({
                "serial": _texto(serial_valor),
                "anv": anv_valor,
                "ano": ano,
                "mes": mes,
                # sempre string — a grade mistura marcadores de evento (TBO/
                # HSI/TBO*/X) com números e texto livre na mesma coluna;
                # sem isso a coluna fica com tipo misto e quebra a
                # serialização Arrow do st.dataframe.
                "evento": str(cell.value).strip() if cell.value is not None else None,
                "comentario": cell.comment.text.strip() if cell.comment else None,
            })
    return pd.DataFrame(linhas, columns=["serial", "anv", "ano", "mes", "evento", "comentario"])


def extrair():
    inconsistencias = []
    wb = openpyxl.load_workbook(ARQUIVO_FONTE, data_only=True)
    df_situacao = _extrair_situacao_generico(wb["SILOMS"], COL_SITUACAO, LINHA_INICIO_SITUACAO)
    df_helice = _extrair_situacao_generico(wb["hélice"], COL_HELICE, LINHA_INICIO_HELICE)
    df_os = _extrair_os(wb, inconsistencias)
    df_diagonal = _extrair_diagonal(wb, inconsistencias)
    df_diagonal_meta = _extrair_diagonal_metadados(wb)
    return {
        "situacao": df_situacao, "diagonal": df_diagonal, "os": df_os, "helice": df_helice,
        "diagonal_meta": df_diagonal_meta,
    }, inconsistencias


def _registrar_historico_situacao(df_situacao):
    """Acrescenta o snapshot de hoje (1 linha por SN) — se já rodou hoje
    antes, substitui só as linhas de hoje (não duplica). Pedido do Wallace em
    2026-07-14: "vai ter historico pq vai ter atualizacao diaria" — grava
    toda vez que a extração roda (botão do site ou pedido na conversa),
    mesmo padrão de RAC/MTA/TPJL. Só existe história a partir do dia em que
    essa função passou a rodar."""
    hoje = datetime.now().date().isoformat()
    novo = df_situacao[COLUNAS_HISTORICO_SITUACAO].copy()
    novo.insert(0, "data_snapshot", hoje)

    if HISTORICO_SITUACAO.exists():
        historico = pd.read_csv(HISTORICO_SITUACAO)
        historico = historico[historico["data_snapshot"] != hoje]
        historico = pd.concat([historico, novo], ignore_index=True)
    else:
        historico = novo
    historico.to_csv(HISTORICO_SITUACAO, index=False)


def _registrar_historico_diagonal(df_diagonal):
    """Acrescenta o snapshot de hoje dos eventos TBO/HSI/TBO* projetados (1
    linha por serial/ano/mês) — mesmo padrão da Situação. Pedido do Wallace
    em 2026-07-15: "mostrar na diagonal dos motores tb, um historico de
    evolucao" — a projeção pode mudar de um dia pro outro (mês empurrado,
    virou HSI em vez de TBO, comentário novo), então vale acompanhar."""
    hoje = datetime.now().date().isoformat()
    eventos = df_diagonal[df_diagonal["evento"].isin({"TBO", "TBO*", "HSI"})]
    novo = eventos[COLUNAS_HISTORICO_DIAGONAL].copy()
    novo.insert(0, "data_snapshot", hoje)

    if HISTORICO_DIAGONAL.exists():
        historico = pd.read_csv(HISTORICO_DIAGONAL)
        historico = historico[historico["data_snapshot"] != hoje]
        historico = pd.concat([historico, novo], ignore_index=True)
    else:
        historico = novo
    historico.to_csv(HISTORICO_DIAGONAL, index=False)


def main():
    DADOS_TRATADOS.mkdir(parents=True, exist_ok=True)
    dados, inconsistencias = extrair()

    destino = DADOS_TRATADOS / "base_motores_tratada.xlsx"
    with pd.ExcelWriter(destino) as writer:
        dados["situacao"].to_excel(writer, index=False, sheet_name="Situacao")
        dados["diagonal"].to_excel(writer, index=False, sheet_name="Diagonal")
        dados["os"].to_excel(writer, index=False, sheet_name="OS")
        dados["helice"].to_excel(writer, index=False, sheet_name="Helice")
        dados["diagonal_meta"].to_excel(writer, index=False, sheet_name="DiagonalMeta")

    _registrar_historico_situacao(dados["situacao"])
    _registrar_historico_diagonal(dados["diagonal"])

    registrar_log(
        nome_execucao="extrair_motores",
        arquivos_lidos=[str(ARQUIVO_FONTE)],
        arquivos_gerados=[str(destino)],
        inconsistencias=inconsistencias,
    )

    for chave, df in dados.items():
        print(f"{chave}: {len(df)} linha(s) -> {destino} (aba {chave.capitalize()})")
    if inconsistencias:
        print(f"{len(inconsistencias)} inconsistência(s) encontrada(s), ver log em 06_Logs/.")

    return dados


def atualizar_do_drive():
    """Busca a versão mais recente direto do Google Drive, sobrescreve a
    cópia local e reprocessa. Ver 00_Instrucoes/atualizacoes.md."""
    try:
        metadados = drive_sync.obter_metadados(DRIVE_FILE_ID)
        conteudo = drive_sync.baixar_arquivo(DRIVE_FILE_ID, exportar_como=drive_sync.XLSX_MIME)
        ARQUIVO_FONTE.parent.mkdir(parents=True, exist_ok=True)
        ARQUIVO_FONTE.write_bytes(conteudo)
        dados = main()
        estado.atualizar_estado(
            ESTADO_ATUALIZACOES, "motores",
            remote_modified_time=metadados["modifiedTime"],
            local_updated_at=datetime.now().isoformat(),
            status="atualizado",
            record_count=len(dados["situacao"]),
            last_error=None,
        )
    except Exception as e:
        estado.atualizar_estado(ESTADO_ATUALIZACOES, "motores", status="erro", last_error=str(e))
        raise
    return estado.obter_entrada(ESTADO_ATUALIZACOES, "motores")


if __name__ == "__main__":
    import sys
    if "--atualizar-do-drive" in sys.argv:
        atualizar_do_drive()
    else:
        main()
