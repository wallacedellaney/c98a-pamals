"""Justificativas de atrasos escritas pela empresa (VEE ONE) no fechamento
mensal — planilha Google Sheets própria (criada em 2026-07-30, ver
00_Instrucoes/atrasos.md), compartilhada como EDITOR com a conta de
serviço (diferente da maioria das planilhas do projeto, que são só
Leitor — mesmo padrão do log de acessos, ver shared/drive_sync.py).

Wallace, 2026-07-31: "todas as colunas de entregas ja fica no drive igual
do site, so fica pendente a justificativa, ai da o check quando eles
escreverem a justificativa" — a planilha espelha TODAS as colunas da tabela
"Entregas no mês de referência" do site (mesmos rótulos, pra abrir direto
no Google Sheets sem tradução), com Justificativa vazia e Status "Pendente"
até a empresa escrever algo (aí vira "Preenchida", tanto na planilha quanto
no próprio site).

Chave de cada linha: (Emergência, Mês de referência) — a mesma emergência
pode ganhar uma justificativa por mês de fechamento (o "mês de referência"
muda a cada fechamento).
"""

import pandas as pd

from shared import drive_sync

PLANILHA_JUSTIFICATIVAS_ID = "1W0lpuy-qkVreZdxYEnthWF56UKyZqfm2LiUwc2RM1mo"

COLUNAS_ENTREGA = [
    "Emergência", "PN", "Nomenclatura", "Aeronave", "Tipo", "Abertura", "Prazo",
    "Cancelamento/conclusão", "Dias de atraso", "Situação", "Obs. Coordenadoria", "Obs. VEE ONE",
]
COLUNAS = ["Mês de referência"] + COLUNAS_ENTREGA + ["Justificativa (empresa)", "Status", "Atualizado em"]

STATUS_PENDENTE = "⏳ Pendente"
STATUS_PREENCHIDA = "✅ Preenchida"


def carregar_justificativas():
    """Lê a planilha inteira. Devolve DataFrame vazio (mesmas colunas) se a
    planilha ainda não estiver compartilhada como Editor, sem dado ainda, ou
    qualquer outra falha de acesso — nunca quebra a página de Atrasos por
    causa disso."""
    try:
        drive_sync.garantir_credencial_arquivo()
        aba = drive_sync.primeira_aba(PLANILHA_JUSTIFICATIVAS_ID)
        linhas = drive_sync.ler_linhas(PLANILHA_JUSTIFICATIVAS_ID, aba)
    except Exception:
        # Não só DriveSyncError — qualquer falha aqui (credencial, planilha
        # ainda não compartilhada, erro de rede) não pode derrubar a página
        # de Atrasos inteira (achado real em produção, 2026-07-31: um
        # AttributeError não coberto por "except DriveSyncError" quebrava
        # o site — ver drive_sync.py).
        return pd.DataFrame(columns=COLUNAS)
    if not linhas or len(linhas) < 2:
        return pd.DataFrame(columns=COLUNAS)
    cabecalho, *resto = linhas
    # A API do Sheets corta células vazias no fim de cada linha (ex.: uma
    # linha "Pendente" tem "Atualizado em", a última coluna, vazio) — sem
    # completar de volta, pd.DataFrame quebra com "N columns passed, data
    # had M columns" (achado real testando o round-trip em 2026-07-31).
    n = len(cabecalho)
    resto_completo = [linha + [""] * (n - len(linha)) for linha in resto]
    df = pd.DataFrame(resto_completo, columns=cabecalho)
    for coluna in COLUNAS:
        if coluna not in df.columns:
            df[coluna] = ""
    return df[COLUNAS]


def _montar_linhas_mes(mes_referencia, tabela_entregas, justificativas_por_emergencia, todas_salvas):
    """Monta as linhas do mês a partir de `tabela_entregas` (mesmas colunas
    exibidas no site, ver COLUNAS_ENTREGA) + a justificativa de cada
    emergência: usa `justificativas_por_emergencia` quando tem uma entrada
    pra aquela emergência (edição vinda do dashboard), senão preserva o que
    já estava salvo no Drive (escrito direto na planilha ou em uma
    sincronização anterior)."""
    salvas_mes = todas_salvas[todas_salvas["Mês de referência"] == mes_referencia].set_index("Emergência")

    linhas = tabela_entregas.copy()
    linhas["Emergência"] = linhas["Emergência"].astype(str)
    linhas["Mês de referência"] = mes_referencia

    def _texto_atual(emergencia):
        if emergencia in justificativas_por_emergencia:
            return str(justificativas_por_emergencia[emergencia] or "").strip()
        if emergencia in salvas_mes.index:
            return str(salvas_mes.loc[emergencia, "Justificativa (empresa)"] or "").strip()
        return ""

    textos = linhas["Emergência"].apply(_texto_atual)
    linhas["Justificativa (empresa)"] = textos
    linhas["Status"] = textos.apply(lambda t: STATUS_PREENCHIDA if t else STATUS_PENDENTE)

    def _atualizado_em(emergencia, texto):
        if not texto:
            return ""
        if emergencia in salvas_mes.index:
            anterior = str(salvas_mes.loc[emergencia, "Justificativa (empresa)"] or "").strip()
            if anterior == texto:
                return str(salvas_mes.loc[emergencia, "Atualizado em"] or "")
        return pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")

    linhas["Atualizado em"] = [_atualizado_em(e, t) for e, t in zip(linhas["Emergência"], textos)]
    return linhas[COLUNAS]


def _matriz_segura(df):
    """Converte cada célula pra string pura, célula a célula — nunca confia
    só no `.astype(str)` do DataFrame inteiro. Qualquer valor "vazio" (NaN,
    None, NaT, pd.NA) vira string vazia explicitamente via `pd.isna`, em vez
    de depender da conversão automática do pandas. Existe porque um valor
    não-string (ex.: float NaN) chegando no corpo da requisição HTTP pro
    Sheets faz o `json.dumps` da lib do Google serializar como token cru
    `NaN`, que o parser estrito do Google rejeita como "Invalid JSON
    payload" (achado real em produção, 2026-07-31 — a causa exata não foi
    localizada com certeza, então a defesa aqui é blindar por célula em vez
    de confiar no cast do DataFrame)."""
    linhas = []
    for linha in df.values.tolist():
        linhas.append(["" if pd.isna(v) else str(v) for v in linha])
    return linhas


def sincronizar_mes(mes_referencia, tabela_entregas, justificativas_por_emergencia=None):
    """Espelha TODAS as colunas de "entregas" do mês no Drive (igual ao
    site) — chamada automaticamente assim que aparece uma emergência do mês
    ainda não espelhada, e também no clique de "Salvar justificativas" (aí
    com `justificativas_por_emergencia` = o que a empresa acabou de editar
    no dashboard). Preserva os outros meses já salvos e qualquer
    justificativa já escrita que não esteja em `justificativas_por_emergencia`."""
    todas = carregar_justificativas()
    outros_meses = todas[todas["Mês de referência"] != mes_referencia]
    linhas_mes = _montar_linhas_mes(
        mes_referencia, tabela_entregas, justificativas_por_emergencia or {}, todas
    )
    completo = pd.concat([outros_meses, linhas_mes], ignore_index=True)
    drive_sync.garantir_credencial_arquivo()
    aba = drive_sync.primeira_aba(PLANILHA_JUSTIFICATIVAS_ID)
    valores = [COLUNAS] + _matriz_segura(completo[COLUNAS])
    drive_sync.sobrescrever_aba(PLANILHA_JUSTIFICATIVAS_ID, aba, valores)
