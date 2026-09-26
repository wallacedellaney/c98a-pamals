"""
Cômputo Mensal (aba 1.2 da Pré-RMA) — calcula a matriz de aeronave x dia
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
from shared import horario

PASTA_COMPUTO = DADOS_TRATADOS / "computo_mensal"
CAMINHO_RAC = RAIZ_PROJETO / "Coordenadoria" / "02_Dados_Tratados" / "base_rac_tratada.xlsx"
CAMINHO_EMERGENCIAS_HISTORICO = DADOS_TRATADOS / "historico_completo_emergencias.xlsx"

TIPOS_CONSIDERADOS = ("AIFP", "IPLR")

# Termos que, aparecendo na observação da Coordenadoria (fiscal), indicam que
# a emergência não deve negativar NENHUM dia (regra do Wallace, 2026-07-17:
# "cancelado pelo operador, cancelado pelo suprimentista, demanda nao
# necessaria mais e outras variaveis nao computar, contar como montada" —
# depois confirmado com o exemplo real da emergência 329260019180: mesmo os
# dias que já tinham negativado ANTES da data oficial de cancelamento
# chegar também viram "montada", não só dali pra frente). "cancelad" pega
# Cancelado/Cancelada/Cancelamento (qualquer motivo — operador,
# suprimentista, duplicidade etc.), os outros pegam "não é/será/ser mais
# necessário" e variações de "não necessária". Silencioso — não vira nota
# em "inconsistências" nem aparece em nenhum lugar do Fechamento Mensal.
# "cancel" (não "cancelad") de propósito — pega também "CANCELAMENTO"
# (bug achado com o exemplo real 329260019180: "OBS DO CANCELAMENTO
# SOLICITADO PELO SUPRIMENTISTA", que "cancelad" não pegava).
TERMOS_CANCELAMENTO_OBSERVACAO = [
    "cancel", "não é mais necess", "não será mais necess",
    "não ser mais necess", "não necessári",
]

# Termos que, aparecendo na observação da Coordenadoria (fiscal), indicam que
# o próprio fiscal decidiu NÃO aplicar avaliação negativa a essa ocorrência
# (ex.: enquanto analisa argumentos técnicos apresentados pela contratada) —
# mesmo efeito prático do cancelamento pro cômputo (não negativa nenhum dia),
# mas o motivo é outro (decisão do fiscal, não a emergência ter deixado de
# existir). Regra confirmada pelo Wallace em 2026-09-23 com o exemplo real da
# emergência 313260018708 (FAB 2741, PASSENGER DOOR): comentário do fiscal
# diz "durante essa análise, não será aplicada avaliação negativa à empresa
# quanto a essa ocorrência". Silencioso, mesmo padrão de
# TERMOS_CANCELAMENTO_OBSERVACAO — não vira nota em "inconsistências". Se a
# análise concluir e o fiscal decidir negativar afinal, o jeito de reverter é
# tirar essa frase do comentário (ou reescrevê-lo) na planilha de origem.
TERMOS_ISENCAO_AVALIACAO_NEGATIVA = [
    "não será aplicada avaliação negativa", "não serão aplicadas avaliações negativas",
    "sem aplicação de avaliação negativa", "não haverá avaliação negativa",
]


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


def _tem_comentario_cancelamento(observacao):
    if pd.isna(observacao):
        return False
    texto = str(observacao).strip().lower()
    return any(termo in texto for termo in TERMOS_CANCELAMENTO_OBSERVACAO)


def _tem_isencao_avaliacao_negativa(observacao):
    if pd.isna(observacao):
        return False
    texto = str(observacao).strip().lower()
    return any(termo in texto for termo in TERMOS_ISENCAO_AVALIACAO_NEGATIVA)


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
    hoje = hoje or horario.hoje_br()
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

        # Comentário da Coordenadoria indica cancelamento pelo
        # operador/suprimentista/"não é mais necessário" — desconsidera a
        # negativação INTEIRA dessa emergência, mesmo os dias que já tinham
        # negativado antes da data oficial de cancelamento chegar (regra
        # confirmada pelo Wallace em 2026-07-17 com o exemplo real da
        # emergência 329260019180: 8 dias negativados antes do cancelamento
        # oficial também devem virar "montada"). Silencioso — não vira nota
        # em "inconsistências" (pedido do Wallace).
        if _tem_comentario_cancelamento(row.get("obs_coordenadoria_fiscal")):
            continue

        # Fiscal decidiu explicitamente não aplicar avaliação negativa a essa
        # ocorrência (ver TERMOS_ISENCAO_AVALIACAO_NEGATIVA acima) — mesmo
        # tratamento silencioso do cancelamento, mas motivo diferente.
        if _tem_isencao_avaliacao_negativa(row.get("obs_coordenadoria_fiscal")):
            continue

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

    # Mantém a linha "real VEE ONE" (e o CSV que a Disponibilidade Diária
    # lê) sempre em sincronia com o oficial — achado pelo Wallace,
    # 2026-08-17: "a linha montada real vee one tá parada, não acompanhou
    # as outras". Antes só era recalculada quando alguém abria a página do
    # Fechamento Mensal (Cômputo Mensal); `calcular_mes()` já roda sozinho
    # de carona toda vez que Emergências atualiza (2 em 2h) — agora essa
    # atualização automática recalcula as duas juntas, não só a oficial.
    calcular_media_diaria_vee_one(ano, mes, hoje)

    return df_matriz, df_motivos, resumo


def calcular_media_diaria_vee_one(ano, mes, hoje=None):
    """Segunda linha "real da VEE ONE" pro gráfico "Evolução da % de
    aeronaves montadas no mês" — pedido do Wallace, 2026-08-14: "cria
    apenas uma linha da média mensal real da VEE ONE, desconsiderando se
    tem estoque ou não e desconsiderando negócio de dia útil, [quando]
    abre a emergência já começa a negativar" — e depois, precisando: "tipo
    assim, começa a contar na data da emergência, sem ser da informação, o
    da real vee one" (2026-08-14, corrige a 1ª versão que usava a data da
    informação). Mesma base de emergências AIFP/IPLR e mesma classificação
    "dentro do contrato" de `calcular_mes`, só que:
    - negativa sempre que a emergência está aberta, **estoque ou não**
      (a regra oficial só negativa sem estoque — aqui não olha o campo);
    - início da negativação é a própria **data de abertura** (não a data
      da informação), **sem** pular pro próximo dia útil (a regra oficial
      usa data da informação + pula sáb/dom).
    Fim da negativação (dia anterior ao cancelamento) e a exclusão de
    emergência cancelada (comentário da Coordenadoria) continuam iguais —
    só estoque, referência de início e dia útil mudam. Só devolve a série
    diária (% montadas por dia) — não grava matriz 0/1 em disco, é só pra
    essa linha extra do gráfico, não substitui o Cômputo Mensal oficial."""
    hoje = hoje or horario.hoje_br()
    primeiro_dia = date(ano, mes, 1)
    ultimo_dia_mes = calendar.monthrange(ano, mes)[1]
    ultimo_dia_calculado = hoje.day if (ano == hoje.year and mes == hoje.month) else ultimo_dia_mes
    fim_mes = date(ano, mes, ultimo_dia_mes)

    pontuadas, _ = _classificar_aeronaves()

    emergencias = pd.read_excel(CAMINHO_EMERGENCIAS_HISTORICO)
    emergencias["matricula_aeronave"] = emergencias["matricula_aeronave"].astype(str)
    emergencias = emergencias[emergencias["tpemg"].isin(TIPOS_CONSIDERADOS)].copy()
    emergencias["data_abertura"] = pd.to_datetime(emergencias["data_abertura"], errors="coerce").dt.date
    emergencias["atendido_cancelado_dt"] = pd.to_datetime(emergencias["atendido_cancelado"], errors="coerce")

    periodos = []
    for _, row in emergencias.iterrows():
        matricula = row["matricula_aeronave"]
        if matricula not in pontuadas:
            continue
        if _tem_comentario_cancelamento(row.get("obs_coordenadoria_fiscal")):
            continue

        # Fiscal decidiu explicitamente não aplicar avaliação negativa a essa
        # ocorrência (ver TERMOS_ISENCAO_AVALIACAO_NEGATIVA acima) — mesmo
        # tratamento silencioso do cancelamento, mas motivo diferente.
        if _tem_isencao_avaliacao_negativa(row.get("obs_coordenadoria_fiscal")):
            continue

        data_abertura = row["data_abertura"]
        atendido_dt = row["atendido_cancelado_dt"]
        data_fim_emergencia = atendido_dt.date() if pd.notna(atendido_dt) else None

        if data_abertura is None or data_abertura > fim_mes:
            continue
        if data_fim_emergencia is not None and data_fim_emergencia < primeiro_dia:
            continue

        # Data de abertura, não a data da informação — sem pular pro
        # próximo dia útil, ao contrário da regra oficial.
        inicio_negativacao = data_abertura
        fim_negativacao = (
            (data_fim_emergencia - timedelta(days=1)) if data_fim_emergencia
            else date(ano, mes, ultimo_dia_calculado)
        )
        inicio_efetivo = max(inicio_negativacao, primeiro_dia)
        fim_efetivo = min(fim_negativacao, date(ano, mes, ultimo_dia_calculado))
        if inicio_efetivo > fim_efetivo:
            continue

        periodos.append({"matricula": matricula, "inicio": inicio_efetivo, "fim": fim_efetivo})

    linhas = []
    for dia in range(1, ultimo_dia_calculado + 1):
        data_dia = date(ano, mes, dia)
        negativadas = {p["matricula"] for p in periodos if p["inicio"] <= data_dia <= p["fim"]}
        pct = 100 * (len(pontuadas) - len(negativadas)) / len(pontuadas) if pontuadas else None
        linhas.append({"dia": dia, "montada": pct})

    df = pd.DataFrame(linhas)

    # Grava um CSV pequeno (dia/montada %) — pedido do Wallace, 2026-08-14:
    # a Disponibilidade Diária (Coordenadoria) também vai plotar essa linha
    # num gráfico próprio, e não pode importar scripts do Contrato 005 no
    # mesmo processo Python (mesmo motivo do bug do common.py corrigido
    # antes — cada área tem seu próprio common.py, colidem se os 2
    # diretórios de scripts entrarem no sys.path juntos). Lendo só o CSV,
    # sem import cruzado.
    PASTA_COMPUTO.mkdir(parents=True, exist_ok=True)
    df.to_csv(PASTA_COMPUTO / f"{ano}-{mes:02d}_vee_one.csv", index=False)

    return df


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



# ---------------------------------------------------------------------------
# Cálculo RETROATIVO (fev-nov/2025) — trabalho pedido pelo Wallace em
# 2026-09-23/25: "queria ter [a matriz de montadas] desde o início do
# contrato... é para ter igual o fechamento mensal, montar aquele jogo de
# montadas 0 e 1 desde fevereiro de 2025" + "nao muda a geral principal
# nossa de pontuação, isso é só para trabalho retroativo".
#
# Diferenças em relação ao `calcular_mes()` oficial:
# - Não existe campo "Estoque" preenchido antes de meados de 2026 — usa a
#   mesma regra da linha "real VEE ONE" (`calcular_media_diaria_vee_one`):
#   negativa toda AIFP/IPLR aberta (com ou sem estoque), começando na
#   própria data de abertura, sem pular pro próximo dia útil.
# - O roster "dentro do contrato" NÃO vem do RAC de hoje (que só reflete a
#   composição ATUAL da frota) — vem de um histórico reconstruído à mão
#   junto com o Wallace, mês a mês, a partir da aba "1.2" (hand-made) de
#   cada RMA mensal no Drive ("Fechamentos mensais"), confirmando aeronave
#   por aeronave nas planilhas RMA_2025-*.xlsx. Ver ROSTER_RETROATIVO
#   abaixo — cada mês foi conferido e confirmado pelo Wallace um por um.
# - Fevereiro, março e abril/2025 são o período de adaptação do contrato
#   (regra TR item 16.10.7): índice de montagem forçado em 1, sem
#   negativação nenhuma — não roda o cálculo de emergências pra esses 3
#   meses, só marca a matriz inteira como montada.
# - Escreve em pasta separada (`computo_mensal_retroativo/`) — nunca
#   mexe nos arquivos do Cômputo Mensal oficial (`computo_mensal/`).
# ---------------------------------------------------------------------------

PASTA_COMPUTO_RETROATIVO = DADOS_TRATADOS / "computo_mensal_retroativo"

MESES_ADAPTACAO_RETROATIVO = {(2025, 2), (2025, 3), (2025, 4)}

# Correções manuais, caso a caso — pedido do Wallace em 2026-09-25: "vamos
# corrigindo manualmente cada caso", confirmado comparando com as
# apresentações "RMA <mês>.pptx" / "Análise média mensal aeronaves
# montadas.pptx" que o Wallace monta todo mês no Drive (pasta do mês em
# "Fechamentos mensais") — essas apresentações são o dado real, conferido
# pelo fiscal, e servem de gabarito pra validar o cálculo retroativo.
#
# Override de "data_info": usa essa data no lugar da que está na planilha,
# pra emergências que foram reclassificadas de ANCE pra AIFP/IPLR bem
# depois da abertura real (nossa base só guarda o tpemg ATUAL, sem
# histórico de quando mudou).
CORRECOES_DATA_INFO_RETROATIVO = {
    # 313250017063 (FAB 2736, LOW L SWITCH): aberta 24/09/2025 como ANCE
    # (não negativa) — só virou AIFP em 09/10/2025, depois do prazo já
    # vencido (ver obs_coordenadoria_fiscal). Confirmado batendo exato com
    # as apresentações de setembro E outubro usando 09/10 como data_info.
    "313250017063": date(2025, 10, 9),
}

# Override da data de atendido/cancelado — pra emergências cuja data na
# planilha de hoje foi corrigida/lançada bem depois do mês fechar (a
# planilha de emergências é viva, continua sendo editada com atraso), então
# não reflete mais a data real de quando a aeronave voltou a montar naquele
# mês específico.
CORRECOES_ATENDIDO_RETROATIVO = {
    # 313250016987 (FAB 2741): planilha de hoje mostra atendido em
    # 30/10/2025, mas a apresentação de outubro (feita em 06/11, antes da
    # correção tardia) mostra "Atd/cancelada" em branco e a observação diz
    # "Material recebido... dia 27/10/2025" — a aeronave voltou a montar no
    # dia 28/10, não dia 31.
    "313250016987": date(2025, 10, 27),
}

# Emergências cujo comentário bate no filtro de cancelamento
# (TERMOS_CANCELAMENTO_OBSERVACAO, ex.: "cancel...") mas que na verdade são
# só o fechamento ADMINISTRATIVO depois do material já ter sido entregue —
# não uma isenção real (o operador não devolveu/dispensou o item, só
# encerrou o processo no sistema depois). Nesses casos o filtro de
# cancelamento está incorreto e o período de negativação real deve contar.
EMERGENCIAS_FORCAR_INCLUSAO_RETROATIVO = {
    # 386250012956 (FAB 2743, nov/2025): "Emergência cancelada pela BACO em
    # 05/12. AWB ... entregue em 02/12" — cancelamento é só o fechamento
    # depois da entrega (02/12), não isenção. A apresentação de novembro
    # confirma negativação de 28 a 30/11 (antes do cancelamento).
    "386250012956",
}

# Emergências que o fiscal decidiu tratar como ANCE "para todos os fins"
# (não negativa nada) — mesmo espírito de TERMOS_ISENCAO_AVALIACAO_NEGATIVA,
# mas com uma frase que a lista atual não pega ("tratando a emergencia
# internamente como ANCE... o fiscal vai tratar essa emergência para todos
# os fins como ANCE"). Só no retroativo por enquanto (não mexe no termo
# oficial usado por calcular_mes, que é "a geral principal" — pedido do
# Wallace de não mudar isso sem confirmar primeiro).
#
# 313250016991, 313250017010, 313250017009 (FAB 2737, set/2025): "o
# operador abriu a emergência como IPLR/AIFP mas em determinados momentos
# do mês voou a aeronave (tratando a emergencia internamente como ANCE),
# para não prejudicar a empresa o fiscal vai tratar essa emergência para
# todos os fins como ANCE. 1T Wallace 01.10" — confirmado comparando com a
# apresentação de setembro, que só negativa 2737 a partir da 4ª emergência
# (313250017060), sem o comentário ANCE.
EMERGENCIAS_EXCLUIDAS_RETROATIVO = {
    "313250016991", "313250017010", "313250017009",
}

# Emergências que devem ser excluídas só em MESES específicos — casos onde
# a apresentação de um mês simplesmente não lista a emergência (o fiscal
# não contou ela naquele mês por algum motivo não documentado), mas ela
# segue válida/contando nos outros meses em que aparece normalmente.
#
# 685250010033 (FAB 2728): fica "Providência tom" de out/2025 até jan/2026
# na planilha (só o recibo assinado do cartão GPS demorou pra fechar
# formalmente) — conta normal em setembro/outubro (bate com a apresentação
# desses meses), mas NÃO aparece na apresentação de novembro pra 2728 (a
# matriz de novembro mostra 2728 montada nos dias 1-6, quando essa
# emergência já estava aberta há semanas).
#
# 396250014964 (FAB 2733): mesma situação — "Providência tom" desde
# jul/2025, conta normal até outubro, mas não aparece na apresentação de
# novembro pra 2733.
EMERGENCIAS_EXCLUIDAS_RETROATIVO_POR_MES = {
    (2025, 11): {"685250010033", "396250014964"},
}

# Emergências cujo "Atd/cancelada" na planilha de hoje foi preenchido bem
# depois do mês fechar (comparado com a apresentação daquele mês, que
# mostra a coluna em branco = ainda aberta na época) — trata como se ainda
# estivesse aberta pro cálculo retroativo daquele mês (nunca libera
# sozinha, só quando o mês acaba ou vira o mês seguinte).
EMERGENCIAS_FORCAR_AINDA_ABERTA_RETROATIVO = {
    # 304250074908 (FAB 2704, nov/2025): planilha de hoje mostra atendido
    # em 28/11, mas a apresentação de novembro (feita em 04/12, DEPOIS do
    # dia 28) mostra a coluna em branco — se tivesse sido atendido mesmo em
    # 28/11, a apresentação já teria essa data. A matriz de novembro
    # confirma 2704 desmontada até o fim do mês (dia 30).
    "304250074908",
    # 396250015798 (FAB 2733, nov/2025): mesmo padrão — planilha de hoje
    # mostra atendido em 24/11 (mesmo dia da info, o que zerava o período
    # no cálculo), mas a apresentação mostra a coluna em branco e a matriz
    # confirma 2733 desmontada de 25 a 30/11.
    "396250015798",
}

# Emergências transferidas de uma aeronave pra outra no meio do mês — nossa
# base só guarda a matrícula FINAL, sem histórico de qual aeronave estava
# com o item em cada período. Reconstruído a partir dos comentários da
# apresentação de novembro/2025 ("Emg transferida do 2722 para o 2719 em
# 24/11", etc.) — todas as 3 emergências abaixo foram transferidas do 2722
# pro 2719 no mesmo dia (24/11/2025): o 2722 fica negativado até o próprio
# dia da transferência (inclusive), o 2719 (matrícula que já está gravada
# na planilha) só a partir do próximo dia útil depois da transferência.
TRANSFERENCIAS_RETROATIVO = {
    "685250010201": {"matricula_origem": "2722", "data_transferencia": date(2025, 11, 24)},
    "685250010202": {"matricula_origem": "2722", "data_transferencia": date(2025, 11, 24)},
    "685250010206": {"matricula_origem": "2722", "data_transferencia": date(2025, 11, 24)},
}

# Roster "dentro do contrato" mês a mês, reconstruído com o Wallace a partir
# da aba "1.2" de cada RMA (2026-09-25) — fevereiro é o próprio roster da
# aba 1.2 de fev/2025 (mesmo sendo mês de adaptação, listado aqui só pra
# referência/consistência); março e abril não têm roster confiável (aba 1.2
# ausente em março, RMA de abril nem existe em xlsx no Drive) — não importa
# pro resultado porque os 2 são meses de adaptação (tudo = 1 de qualquer
# forma). Dezembro/2025 em diante já é coberto pelo Cômputo Mensal oficial
# (Estoque passou a ser preenchido) — não precisa de versão retroativa.
ROSTER_RETROATIVO = {
    (2025, 2): ["2702", "2703", "2704", "2708", "2719", "2722", "2723", "2727", "2729",
                "2731", "2736", "2737", "2738", "2739", "2740", "2741", "2742", "2743"],
    (2025, 5): ["2702", "2703", "2704", "2708", "2709", "2719", "2722", "2723", "2727", "2728",
                "2729", "2731", "2733", "2736", "2737", "2738", "2739", "2740", "2741", "2742", "2743"],
    (2025, 6): ["2702", "2703", "2704", "2708", "2709", "2719", "2722", "2723", "2727", "2728",
                "2729", "2731", "2733", "2736", "2737", "2738", "2739", "2740", "2741", "2742", "2743"],
    (2025, 7): ["2702", "2703", "2704", "2708", "2709", "2719", "2722", "2723", "2727", "2728",
                "2729", "2731", "2733", "2736", "2737", "2738", "2739", "2740", "2741", "2742", "2743"],
    (2025, 8): ["2702", "2703", "2704", "2708", "2709", "2719", "2720", "2722", "2723", "2727", "2728",
                "2729", "2731", "2733", "2736", "2737", "2738", "2739", "2740", "2741", "2742", "2743"],
    (2025, 9): ["2702", "2703", "2704", "2708", "2709", "2719", "2720", "2722", "2723", "2727", "2728",
                "2729", "2731", "2733", "2736", "2737", "2738", "2739", "2740", "2741", "2742", "2743"],
    (2025, 10): ["2702", "2703", "2704", "2708", "2709", "2719", "2720", "2721", "2722", "2723", "2727",
                 "2728", "2729", "2731", "2733", "2736", "2737", "2738", "2739", "2740", "2741", "2742", "2743"],
    (2025, 11): ["2702", "2703", "2704", "2708", "2709", "2719", "2720", "2721", "2722", "2723", "2727",
                 "2728", "2729", "2731", "2733", "2736", "2737", "2738", "2739", "2740", "2741", "2742", "2743"],
}


def calcular_mes_retroativo(ano, mes):
    """Mesmo formato de saída do `calcular_mes()` oficial (matriz, motivos,
    resumo), mas pro período fev-nov/2025, usando o roster histórico de
    ROSTER_RETROATIVO em vez do RAC de hoje.

    Regra de negativação (validada em 2026-09-25 contra 29 combinações
    aeronave/mês tiradas das apresentações reais "RMA <mês>.pptx" —
    18/29 bateram exato de cara, o resto são os casos manuais corrigidos
    acima ou transferências de emergência entre aeronaves ainda não
    reconstruídas): MESMA regra do `calcular_mes()` oficial — início =
    próximo dia útil após a "data da informação" (não a abertura!), o
    próprio dia do atendimento ainda conta negativado, libera no dia
    seguinte — só SEM checar o campo Estoque (que não existia antes de
    dez/2025, então toda AIFP/IPLR conta como "sem estoque" = sempre
    negativa). A primeira versão desta função usava a data de abertura sem
    pular dia útil (igual a linha "real VEE ONE" do gráfico) — trocada
    porque batia muito pior com os dados reais (14/29 vs 18/29 de cara, e a
    diferença nos casos que já bateram exato ficava em 1-2 dias, não
    aleatória)."""
    ultimo_dia_mes = calendar.monthrange(ano, mes)[1]
    primeiro_dia = date(ano, mes, 1)
    fim_mes = date(ano, mes, ultimo_dia_mes)

    adaptacao = (ano, mes) in MESES_ADAPTACAO_RETROATIVO
    pontuadas = ROSTER_RETROATIVO.get((ano, mes)) or ROSTER_RETROATIVO[(2025, 2)]

    periodos = []
    inconsistencias = []

    if not adaptacao:
        emergencias = pd.read_excel(CAMINHO_EMERGENCIAS_HISTORICO)
        emergencias["matricula_aeronave"] = emergencias["matricula_aeronave"].astype(str)
        emergencias = emergencias[emergencias["tpemg"].isin(TIPOS_CONSIDERADOS)].copy()
        emergencias["data_info"] = pd.to_datetime(emergencias["data_info"], errors="coerce").dt.date
        emergencias["atendido_cancelado_dt"] = pd.to_datetime(emergencias["atendido_cancelado"], errors="coerce")

        for _, row in emergencias.iterrows():
            matricula = row["matricula_aeronave"]
            numero_emg = str(row["numero_emergencia"])
            forcar_inclusao = numero_emg in EMERGENCIAS_FORCAR_INCLUSAO_RETROATIVO
            if matricula not in pontuadas and numero_emg not in TRANSFERENCIAS_RETROATIVO:
                continue
            if numero_emg in EMERGENCIAS_EXCLUIDAS_RETROATIVO:
                continue
            if numero_emg in EMERGENCIAS_EXCLUIDAS_RETROATIVO_POR_MES.get((ano, mes), set()):
                continue
            if not forcar_inclusao and _tem_comentario_cancelamento(row.get("obs_coordenadoria_fiscal")):
                continue
            if not forcar_inclusao and _tem_isencao_avaliacao_negativa(row.get("obs_coordenadoria_fiscal")):
                continue

            data_info = CORRECOES_DATA_INFO_RETROATIVO.get(numero_emg, row["data_info"])
            atendido_dt = row["atendido_cancelado_dt"]
            if numero_emg in EMERGENCIAS_FORCAR_AINDA_ABERTA_RETROATIVO:
                data_fim_emergencia = None
            else:
                data_fim_emergencia = (
                    CORRECOES_ATENDIDO_RETROATIVO.get(numero_emg)
                    or (atendido_dt.date() if pd.notna(atendido_dt) else None)
                )

            if data_info is None or data_info > fim_mes:
                continue
            if data_fim_emergencia is not None and data_fim_emergencia < primeiro_dia:
                continue

            inicio_negativacao = _proximo_dia_util(data_info)
            # O próprio dia do atendimento/cancelamento ainda conta como
            # negativado — só libera (volta a 1) no dia SEGUINTE. Validado
            # contra as apresentações reais (ver docstring da função).
            fim_negativacao = data_fim_emergencia or date(ano, mes, ultimo_dia_mes)

            transferencia = TRANSFERENCIAS_RETROATIVO.get(numero_emg)
            candidatos = []
            if transferencia:
                # Emergência transferida de uma aeronave pra outra no meio
                # do mês — divide em 2 períodos: um pra aeronave de origem
                # (até o dia da transferência, inclusive), outro pra
                # aeronave final gravada na planilha (a partir do próximo
                # dia útil depois da transferência).
                data_transf = transferencia["data_transferencia"]
                candidatos.append((
                    transferencia["matricula_origem"],
                    inicio_negativacao,
                    min(fim_negativacao, data_transf),
                ))
                candidatos.append((
                    matricula,
                    max(inicio_negativacao, _proximo_dia_util(data_transf)),
                    fim_negativacao,
                ))
            else:
                candidatos.append((matricula, inicio_negativacao, fim_negativacao))

            for matricula_periodo, inicio, fim in candidatos:
                if matricula_periodo not in pontuadas:
                    continue
                inicio_efetivo = max(inicio, primeiro_dia)
                fim_efetivo = min(fim, date(ano, mes, ultimo_dia_mes))
                if inicio_efetivo > fim_efetivo:
                    continue
                periodos.append({
                    "matricula": matricula_periodo,
                    "numero_emergencia": row["numero_emergencia"],
                    "pn": row.get("pn"),
                    "nomenclatura": row.get("nomenclatura"),
                    "tipo": row["tpemg"],
                    "data_info": data_info,
                    "data_cancelamento": data_fim_emergencia,
                    "periodo_no_mes_inicio": inicio_efetivo,
                    "periodo_no_mes_fim": fim_efetivo,
                })

    linhas_matriz = []
    for matricula in pontuadas:
        periodos_aeronave = [p for p in periodos if p["matricula"] == matricula]
        for dia in range(1, ultimo_dia_mes + 1):
            data_dia = date(ano, mes, dia)
            if adaptacao:
                montada = 1
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
        media_diaria = df_matriz.groupby("dia")["montada"].mean() * 100
        mmam_previa = round(media_diaria.mean(), 2)
    else:
        mmam_previa = None

    resumo = {
        "ano": ano, "mes": mes,
        "aeronaves_pontuadas": pontuadas,
        "adaptacao": adaptacao,
        "ultimo_dia_mes": ultimo_dia_mes,
        "ultimo_dia_calculado": ultimo_dia_mes,
        "mmam_previa": mmam_previa,
        "inconsistencias": inconsistencias,
    }

    PASTA_COMPUTO_RETROATIVO.mkdir(parents=True, exist_ok=True)
    mes_ref = f"{ano}-{mes:02d}"
    df_matriz.to_csv(PASTA_COMPUTO_RETROATIVO / f"{mes_ref}_matriz.csv", index=False)
    df_motivos.to_csv(PASTA_COMPUTO_RETROATIVO / f"{mes_ref}_motivos.csv", index=False)
    with open(PASTA_COMPUTO_RETROATIVO / f"{mes_ref}_resumo.json", "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=2, default=str)

    return df_matriz, df_motivos, resumo


def carregar_mes_retroativo(ano, mes):
    mes_ref = f"{ano}-{mes:02d}"
    caminho_matriz = PASTA_COMPUTO_RETROATIVO / f"{mes_ref}_matriz.csv"
    caminho_motivos = PASTA_COMPUTO_RETROATIVO / f"{mes_ref}_motivos.csv"
    caminho_resumo = PASTA_COMPUTO_RETROATIVO / f"{mes_ref}_resumo.json"
    if not caminho_matriz.exists():
        return None, None, None
    df_matriz = pd.read_csv(caminho_matriz, dtype={"matricula": str})
    try:
        df_motivos = pd.read_csv(caminho_motivos, dtype={"matricula": str}) if caminho_motivos.exists() else pd.DataFrame()
    except pd.errors.EmptyDataError:
        # Mês de adaptação (sem nenhuma negativação) grava um CSV vazio
        # (0 linhas, 0 colunas) — read_csv não aceita isso.
        df_motivos = pd.DataFrame()
    with open(caminho_resumo, encoding="utf-8") as f:
        resumo = json.load(f)
    return df_matriz, df_motivos, resumo

if __name__ == "__main__":
    import sys
    ano = int(sys.argv[1]) if len(sys.argv) > 1 else horario.hoje_br().year
    mes = int(sys.argv[2]) if len(sys.argv) > 2 else horario.hoje_br().month
    df_matriz, df_motivos, resumo = calcular_mes(ano, mes)
    print(f"{len(df_matriz)} linhas na matriz, {len(df_motivos)} período(s) de negativação, "
          f"MMAM prévia: {resumo['mmam_previa']}%")
    if resumo["inconsistencias"]:
        print(f"{len(resumo['inconsistencias'])} inconsistência(s):")
        for i in resumo["inconsistencias"]:
            print(" -", i)
