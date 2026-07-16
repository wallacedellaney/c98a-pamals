"""
Cômputo Mensal (aba 1.2 da Pré-RNA) — calcula a matriz de aeronave x dia
(1=montada, 0=desmontada) a partir dos registros de emergências AIFP/IPLR
sem estoque, com rastreamento do motivo de cada negativação.

Regra (definida pelo Wallace em 2026-07-08, ver
00_Instrucoes/computo_mensal.md):
- Só AIFP e IPLR entram no cálculo (nenhum outro tipo de emergência).
- Uma aeronave só é negativada (0) quando tem uma AIFP/IPLR aberta E sem
  estoque disponível ao mesmo tempo. Com estoque disponível, não nega.
- Considera qualquer AIFP/IPLR que tenha impactado o mês de referência —
  aberta antes e continuando, aberta durante, ou fechada durante — não só
  o que abriu no mês.
- Início da negativação: próximo dia útil (só pula sáb/dom por enquanto,
  sem feriados) após a "data da informação" da emergência.
- Fim da negativação: data de cancelamento/conclusão (Atd/cancelada) — se
  ainda não tiver, mantém 0 até o último dia já decorrido do mês de
  referência.
- Estoque em branco: não decide sozinho — fica marcado "indefinido" e
  não entra na negativação automática (vira inconsistência pra revisão
  manual). Confirmado que isso não afeta julho/2026 na prática (nenhuma
  AIFP/IPLR ainda aberta tinha estoque em branco).
- Só o site mostra o resultado por enquanto — não escreve na planilha do
  Google Sheets (decisão do Wallace em 2026-07-08).

Fonte da classificação "dentro do contrato" / "fora do contrato" / "sem
condições": RAC (Coordenadoria/02_Dados_Tratados/base_rac_tratada.xlsx) —
não duplicamos essa classificação aqui.
"""

import calendar
import json
from datetime import date, timedelta

import pandas as pd

from common import RAIZ_PROJETO, DADOS_TRATADOS

PASTA_COMPUTO = DADOS_TRATADOS / "computo_mensal"
CAMINHO_RAC = RAIZ_PROJETO / "Coordenadoria" / "02_Dados_Tratados" / "base_rac_tratada.xlsx"
CAMINHO_EMERGENCIAS_HISTORICO = DADOS_TRATADOS / "historico_completo_emergencias.xlsx"

TIPOS_CONSIDERADOS = ("AIFP", "IPLR")


def _proximo_dia_util(data):
    """Pula sábado e domingo — sem feriados por enquanto (decisão do
    Wallace em 2026-07-08)."""
    d = data + timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def _normalizar_estoque(valor):
    if pd.isna(valor):
        return "indefinido"
    v = str(valor).strip().lower()
    if v == "sim":
        return "Sim"
    if v in ("não", "nao"):
        return "Não"
    return "indefinido"


def _classificar_aeronaves():
    """Retorna (aeronaves_pontuadas, aeronaves_fora_listadas) a partir do
    RAC — mesma classificação usada na tela RAC."""
    rac = pd.read_excel(CAMINHO_RAC, sheet_name="Aeronaves")
    rac["matricula"] = rac["matricula"].astype(str)
    pontuadas = sorted(rac.loc[rac["contrato"] == "Dentro do contrato", "matricula"])
    fora_listadas = sorted(rac.loc[
        (rac["contrato"] == "Fora do contrato") & (rac["disponibilidade"] != "Sem condições"),
        "matricula"
    ])
    return pontuadas, fora_listadas


def calcular_mes(ano, mes, hoje=None):
    hoje = hoje or date.today()
    primeiro_dia = date(ano, mes, 1)
    ultimo_dia_mes = calendar.monthrange(ano, mes)[1]
    ultimo_dia_calculado = hoje.day if (ano == hoje.year and mes == hoje.month) else ultimo_dia_mes
    fim_mes = date(ano, mes, ultimo_dia_mes)

    pontuadas, fora_listadas = _classificar_aeronaves()

    emergencias = pd.read_excel(CAMINHO_EMERGENCIAS_HISTORICO)
    emergencias["matricula_aeronave"] = emergencias["matricula_aeronave"].astype(str)
    emergencias = emergencias[emergencias["tpemg"].isin(TIPOS_CONSIDERADOS)].copy()

    emergencias["data_abertura"] = pd.to_datetime(emergencias["data_abertura"], errors="coerce").dt.date
    emergencias["data_info"] = pd.to_datetime(emergencias["data_info"], errors="coerce").dt.date
    emergencias["atendido_cancelado_dt"] = pd.to_datetime(emergencias["atendido_cancelado"], errors="coerce")

    inconsistencias = []
    periodos = []

    for _, row in emergencias.iterrows():
        matricula = row["matricula_aeronave"]
        if matricula not in pontuadas:
            continue  # só aeronaves dentro do contrato entram no cômputo

        data_abertura = row["data_abertura"]
        data_info = row["data_info"]
        estoque = _normalizar_estoque(row["estoque"])
        atendido_bruto = row["atendido_cancelado"]
        atendido_dt = row["atendido_cancelado_dt"]

        cancelado_sem_data_valida = (
            pd.notna(atendido_bruto) and str(atendido_bruto).strip() != "" and pd.isna(atendido_dt)
        )
        if cancelado_sem_data_valida:
            inconsistencias.append(
                f"Emergência {row['numero_emergencia']} (FAB {matricula}): campo 'Atd/cancelada' tem "
                f"valor não reconhecido como data ('{atendido_bruto}') — tratada como já encerrada antes "
                f"do mês de referência (não entra no cômputo). Verificar manualmente."
            )
            continue

        data_fim_emergencia = atendido_dt.date() if pd.notna(atendido_dt) else None

        if data_abertura is None or data_abertura > fim_mes:
            continue
        if data_fim_emergencia is not None and data_fim_emergencia < primeiro_dia:
            continue

        if estoque == "indefinido":
            inconsistencias.append(
                f"Emergência {row['numero_emergencia']} (FAB {matricula}, {row['tpemg']}): campo "
                f"'Estoque' em branco — não negativada automaticamente, revisar manualmente."
            )
            continue

        if estoque == "Sim":
            continue

        if data_info is None:
            inconsistencias.append(
                f"Emergência {row['numero_emergencia']} (FAB {matricula}): sem 'data da informação' — "
                f"não deu pra calcular o início da negativação."
            )
            continue

        inicio_negativacao = _proximo_dia_util(data_info)
        # No dia do cancelamento/conclusão em si, a aeronave já volta a ser
        # montada (1) — por isso o último dia negativado é o dia ANTERIOR
        # à data de cancelamento, não a própria data.
        fim_negativacao = (
            (data_fim_emergencia - timedelta(days=1)) if data_fim_emergencia
            else date(ano, mes, ultimo_dia_calculado)
        )

        inicio_efetivo = max(inicio_negativacao, primeiro_dia)
        fim_efetivo = min(fim_negativacao, date(ano, mes, ultimo_dia_calculado))

        if inicio_efetivo > fim_efetivo:
            continue

        periodos.append({
            "matricula": matricula,
            "numero_emergencia": row["numero_emergencia"],
            "pn": row.get("pn"),
            "nomenclatura": row.get("nomenclatura"),
            "tipo": row["tpemg"],
            "data_abertura": data_abertura,
            "data_info": data_info,
            "estoque": estoque,
            "inicio_negativacao": inicio_negativacao,
            "data_cancelamento": data_fim_emergencia,
            "periodo_no_mes_inicio": inicio_efetivo,
            "periodo_no_mes_fim": fim_efetivo,
        })

    # Mostra o mês inteiro (1 a último dia do mês, igual à planilha oficial)
    # — dias ainda não decorridos ficam em branco (None), não 0 nem 1.
    linhas_matriz = []
    for matricula in pontuadas:
        periodos_aeronave = [p for p in periodos if p["matricula"] == matricula]
        for dia in range(1, ultimo_dia_mes + 1):
            data_dia = date(ano, mes, dia)
            if dia > ultimo_dia_calculado:
                montada = None
            else:
                negativada = any(
                    p["periodo_no_mes_inicio"] <= data_dia <= p["periodo_no_mes_fim"] for p in periodos_aeronave
                )
                montada = 0 if negativada else 1
            linhas_matriz.append({
                "matricula": matricula, "dia": dia,
                "fim_de_semana": data_dia.weekday() >= 5,
                "montada": montada,
            })

    df_matriz = pd.DataFrame(linhas_matriz)
    df_motivos = pd.DataFrame(periodos)

    if not df_matriz.empty:
        media_diaria = df_matriz.dropna(subset=["montada"]).groupby("dia")["montada"].mean() * 100
        mmam_previa = round(media_diaria.mean(), 2) if len(media_diaria) else None
    else:
        mmam_previa = None

    resumo = {
        "ano": ano, "mes": mes,
        "aeronaves_pontuadas": pontuadas,
        "aeronaves_fora_listadas": fora_listadas,
        "ultimo_dia_calculado": ultimo_dia_calculado,
        "ultimo_dia_mes": ultimo_dia_mes,
        "mmam_previa": mmam_previa,
        "inconsistencias": inconsistencias,
    }

    PASTA_COMPUTO.mkdir(parents=True, exist_ok=True)
    mes_ref = f"{ano}-{mes:02d}"
    df_matriz.to_csv(PASTA_COMPUTO / f"{mes_ref}_matriz.csv", index=False)
    df_motivos.to_csv(PASTA_COMPUTO / f"{mes_ref}_motivos.csv", index=False)
    with open(PASTA_COMPUTO / f"{mes_ref}_resumo.json", "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=2, default=str)

    return df_matriz, df_motivos, resumo


def carregar_mes(ano, mes):
    mes_ref = f"{ano}-{mes:02d}"
    caminho_matriz = PASTA_COMPUTO / f"{mes_ref}_matriz.csv"
    caminho_motivos = PASTA_COMPUTO / f"{mes_ref}_motivos.csv"
    caminho_resumo = PASTA_COMPUTO / f"{mes_ref}_resumo.json"
    if not caminho_matriz.exists():
        return None, None, None
    df_matriz = pd.read_csv(caminho_matriz, dtype={"matricula": str})
    df_motivos = pd.read_csv(caminho_motivos, dtype={"matricula": str}) if caminho_motivos.exists() else pd.DataFrame()
    with open(caminho_resumo, encoding="utf-8") as f:
        resumo = json.load(f)
    return df_matriz, df_motivos, resumo


if __name__ == "__main__":
    import sys
    ano = int(sys.argv[1]) if len(sys.argv) > 1 else date.today().year
    mes = int(sys.argv[2]) if len(sys.argv) > 2 else date.today().month
    df_matriz, df_motivos, resumo = calcular_mes(ano, mes)
    print(f"{len(df_matriz)} linhas na matriz, {len(df_motivos)} período(s) de negativação, "
          f"MMAM prévia: {resumo['mmam_previa']}%")
    if resumo["inconsistencias"]:
        print(f"{len(resumo['inconsistencias'])} inconsistência(s):")
        for i in resumo["inconsistencias"]:
            print(" -", i)
