"""Compila a "Diagonal de Manutenção" (projeção de inspeções/indisponibilidade
por aeronave ao longo do tempo) de cada operador num único arquivo tratado.
Ver 00_Instrucoes/diagonal_manutencao.md.

Granularidade: a maioria dos operadores é semanal (com rótulo "Semana N") ou
usa faixas de dias sem rótulo padronizado — nesses casos guardamos só o mês
(perde a semana exata, mas evita inventar uma correspondência que a fonte não
dá com segurança). BAMN é mensal por natureza (4 colunas por mês, sem rótulo
de semana). PAMA-LS continua vindo por texto simplificado — seus registros são
marcados com confianca="aproximada". O BACG passou a usar a planilha íntegra
recebida em julho/2026.
"""

import re
from pathlib import Path

import pandas as pd

from common import BASES_ORIGINAIS, DADOS_TRATADOS, registrar_log
from diagonal_parse import ler_grade_generica, periodo_para_datas, RE_PLACEHOLDER, RE_NAO_PROGRAMADO

DIAGONAL_DIR = BASES_ORIGINAIS / "Diagonal_Manutencao"

REGISTRO_GRADE = [
    {"operador": "BANT", "arquivo": DIAGONAL_DIR / "BANT" / "DIAGONAL_C-98_e_Controle_de_Itens_JUL2026.xlsx", "aba": "DIAGONAL C-98"},
    {"operador": "DACTA II", "arquivo": DIAGONAL_DIR / "DACTA_II" / "Diagonal_de_Inspecao_CINDACTA-II_JUL2026.ods", "aba": "DIAGONAL 2026"},
    {"operador": "BABR", "arquivo": DIAGONAL_DIR / "BABR" / "Diagonal_do_C98_6ETA_GLOG-BR_JULHO2026.xlsx", "aba": "DIAGONAL 2026"},
    {"operador": "BABE", "arquivo": DIAGONAL_DIR / "BABE" / "Controle_Diagonal_BABE_JUL2026.xlsx", "aba": "DIAGONAL 2026"},
    {"operador": "BACO", "arquivo": DIAGONAL_DIR / "BACO" / "Controle_Diagonal_BACO_JUL2026.xlsx", "aba": "DIAGONAL 2026"},
    {"operador": "BACG", "arquivo": DIAGONAL_DIR / "BACG" / "Controle_Diagonal_BACG_JUL2026.xlsx", "aba": "DIAGONAL 2025"},
    {"operador": "CLA", "arquivo": DIAGONAL_DIR / "CLA" / "Controle_de_Diagonal_CLA_JUN26_A_OUT26.xlsx", "aba": "JUN"},
]

BAMN_ARQUIVO = DIAGONAL_DIR / "BAMN" / "Diagonal_de_Manutencao_C98_JULHO_2026.ods"

# PAMA-LS: o binário original não transferiu íntegro. Dados reconstruídos a
# partir de texto simplificado — a atribuição exata mês-a-mês é aproximada,
# não uma leitura direta de coluna. Marcados com confianca="aproximada".
EVENTOS_APROXIMADOS = [
    {"operador": "PAMA-LS", "aeronave": "2704", "ano_mes": "2021-06", "motivo": "ID5-15-03 ID5-15-06 ID5-15-08 ID5-15-20 TR DE MOTOR 2706 INSP 1 COR"},
    {"operador": "PAMA-LS", "aeronave": "2704", "ano_mes": "2021-10", "motivo": "ID5-15-0A ID5-15-01 ID5-15-02 ID5-15-07 ID5-15-09 ID5-15-11 ID5-15-21 IM1800 (1800)"},
    {"operador": "PAMA-LS", "aeronave": "2704", "ano_mes": "2024-04", "motivo": "ID5-15-06 ID5-15-15 BM100 (1900)"},
    {"operador": "PAMA-LS", "aeronave": "2704", "ano_mes": "2024-08", "motivo": "ID5-15-0A ID5-15-12 ID5-15-MG IM2000 (2000) INSP 2 MOLAS TPP LPS3"},
]


def _ler_bamn():
    """Grade mensal (4 colunas por mês, sem rótulo de semana) dentro da aba
    'DIAGONAL' do arquivo combinado da BAMN, com células mescladas
    verticalmente (mesma técnica de leitura usada em vencimentos_parse pra
    esse mesmo arquivo)."""
    from odf.opendocument import load
    from odf.table import Table, TableRow
    from odf.text import P

    def texto_celula(cell):
        return "".join(
            node.data for p in cell.getElementsByType(P) for node in p.childNodes if node.nodeType == node.TEXT_NODE
        )

    doc = load(str(BAMN_ARQUIVO))
    tabelas = [t for t in doc.spreadsheet.getElementsByType(Table) if t.getAttribute("name").strip() == "DIAGONAL"]
    if not tabelas:
        return []
    tabela = tabelas[0]

    ultimo_valor_col = {}
    linhas = []
    for linha_odf in tabela.getElementsByType(TableRow):
        valores = []
        col_idx = 0
        for filho in linha_odf.childNodes:
            repete = int(filho.getAttribute("numbercolumnsrepeated") or 1)
            if filho.qname[1] == "covered-table-cell":
                for _ in range(repete):
                    valores.append(ultimo_valor_col.get(col_idx))
                    col_idx += 1
            else:
                texto = texto_celula(filho) or None
                for _ in range(min(repete, 1)):
                    ultimo_valor_col[col_idx] = texto
                    valores.append(texto)
                    col_idx += 1
        linhas.append(valores)

    if not linhas:
        return []

    cabecalho = linhas[0]
    # meses aparecem a cada 4 colunas a partir da coluna 4 (0-based), ex.:
    # "JAN – 25", None, None, None, "FEV – 25", ...
    mes_por_col = {}
    ano_atual_padrao = None
    mes_atual = None
    MESES_ABREV = {
        "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
        "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12,
    }
    for col in range(4, len(cabecalho)):
        v = cabecalho[col]
        if isinstance(v, str) and "–" in v:
            partes = v.split("–")
            abrev = partes[0].strip()[:3].upper()
            ano_sufixo = partes[1].strip()[:2]
            if abrev in MESES_ABREV:
                mes_atual = MESES_ABREV[abrev]
                ano_atual_padrao = "20" + ano_sufixo
        if mes_atual:
            mes_por_col[col] = (ano_atual_padrao, mes_atual)

    eventos = []
    matricula_anterior = None
    for linha in linhas[1:]:
        matricula = linha[0].strip() if isinstance(linha[0], str) and linha[0].strip() else None
        if not matricula or not matricula.isdigit():
            continue
        if matricula == matricula_anterior:
            continue  # segunda linha do par (horas acumuladas) — só a primeira importa
        matricula_anterior = matricula
        vistos_no_mes = {}
        for col, (ano, mes) in mes_por_col.items():
            if col >= len(linha):
                continue
            val = linha[col]
            if not isinstance(val, str) or not val.strip():
                continue
            texto = val.strip()
            if re.match(r"^-?\d{1,3}:\d{2}$", texto) or RE_PLACEHOLDER.match(texto):
                continue  # só hora acumulada, não é um evento
            if RE_NAO_PROGRAMADO.match(texto):
                continue  # "IS"/"sem motor" — status, não inspeção programada (Wallace confirmou)
            chave = (ano, mes)
            vistos_no_mes.setdefault(chave, set()).add(texto)
        for (ano, mes), textos in vistos_no_mes.items():
            eventos.append((matricula, f"{ano}-{mes:02d}", None, "; ".join(sorted(textos))))
    return eventos


def extrair():
    inconsistencias = []
    linhas = []

    for reg in REGISTRO_GRADE:
        if not reg["arquivo"].exists():
            inconsistencias.append(f"{reg['operador']}: arquivo não encontrado em {reg['arquivo']}.")
            continue
        try:
            eventos = ler_grade_generica(reg["arquivo"], reg["aba"])
        except Exception as e:
            inconsistencias.append(f"{reg['operador']}: falha ao ler a grade ({e}).")
            continue
        if not eventos:
            inconsistencias.append(f"{reg['operador']}: nenhum evento de diagonal encontrado (planilha pode estar sem preenchimento).")
        for matricula, ano_mes, semana, motivo in eventos:
            inicio, fim = periodo_para_datas(ano_mes, semana)
            linhas.append({
                "operador": reg["operador"],
                "aeronave": matricula,
                "periodo_inicio": inicio,
                "periodo_fim": fim,
                "motivo": motivo,
                "confianca": "exata" if semana else "mensal",
            })

    try:
        eventos_bamn = _ler_bamn()
        for matricula, ano_mes, semana, motivo in eventos_bamn:
            inicio, fim = periodo_para_datas(ano_mes, semana)
            linhas.append({
                "operador": "BAMN",
                "aeronave": matricula,
                "periodo_inicio": inicio,
                "periodo_fim": fim,
                "motivo": motivo,
                "confianca": "mensal",
            })
    except Exception as e:
        inconsistencias.append(f"BAMN: falha ao ler a grade ({e}).")

    for evento in EVENTOS_APROXIMADOS:
        inicio, fim = periodo_para_datas(evento["ano_mes"], None)
        linhas.append({
            "operador": evento["operador"],
            "aeronave": evento["aeronave"],
            "periodo_inicio": inicio,
            "periodo_fim": fim,
            "motivo": evento["motivo"],
            "confianca": "aproximada",
        })

    df = pd.DataFrame(linhas)
    if not df.empty:
        # Algumas grades repetem o mesmo texto em células mescladas/espelhadas.
        # Isso não representa dois eventos: no Gantt produziria barras e
        # contagens duplicadas. Só removemos cópias integralmente idênticas.
        df = (
            df.drop_duplicates(
                subset=["operador", "aeronave", "periodo_inicio", "periodo_fim", "motivo", "confianca"]
            )
            .sort_values(["periodo_inicio", "operador", "aeronave", "motivo"])
            .reset_index(drop=True)
        )
    return df, inconsistencias


def main():
    DADOS_TRATADOS.mkdir(parents=True, exist_ok=True)
    df, inconsistencias = extrair()

    destino = DADOS_TRATADOS / "base_diagonal_manutencao.xlsx"
    df.to_excel(destino, index=False, sheet_name="Diagonal")

    registrar_log(
        nome_execucao="extrair_diagonal_manutencao",
        arquivos_lidos=[str(r["arquivo"]) for r in REGISTRO_GRADE] + [str(BAMN_ARQUIVO)],
        arquivos_gerados=[str(destino)],
        inconsistencias=inconsistencias,
    )

    print(f"{len(df)} eventos de {df['operador'].nunique() if not df.empty else 0} operador(es) -> {destino}")
    if inconsistencias:
        print(f"{len(inconsistencias)} inconsistência(s) encontrada(s), ver log em 06_Logs/.")


if __name__ == "__main__":
    main()
