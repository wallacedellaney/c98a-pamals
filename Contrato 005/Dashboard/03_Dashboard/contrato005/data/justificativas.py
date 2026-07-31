"""Justificativas de atrasos escritas pela empresa (VEE ONE) no fechamento
mensal — planilha Google Sheets própria (criada em 2026-07-30, ver
00_Instrucoes/atrasos.md), compartilhada como EDITOR com a conta de
serviço (diferente da maioria das planilhas do projeto, que são só
Leitor — mesmo padrão do log de acessos, ver shared/drive_sync.py).

Chave de cada justificativa: (numero_emergencia, mes_referencia) — a mesma
emergência pode ganhar uma justificativa por mês de fechamento (o "mês de
referência" muda a cada fechamento). Só gravamos linhas com justificativa
não vazia, pra não inflar a planilha com uma linha por emergência concluída
todo mês, mesmo sem nada escrito.
"""

import pandas as pd

from shared import drive_sync

PLANILHA_JUSTIFICATIVAS_ID = "1W0lpuy-qkVreZdxYEnthWF56UKyZqfm2LiUwc2RM1mo"
COLUNAS = ["numero_emergencia", "mes_referencia", "justificativa_empresa", "atualizado_em"]


def carregar_justificativas():
    """Lê todas as justificativas já salvas. Devolve DataFrame vazio (mesmas
    colunas) se a planilha ainda não estiver compartilhada como Editor, sem
    aba/dado ainda, ou qualquer outra falha de acesso — nunca quebra a
    página de Atrasos por causa disso."""
    try:
        aba = drive_sync.primeira_aba(PLANILHA_JUSTIFICATIVAS_ID)
        linhas = drive_sync.ler_linhas(PLANILHA_JUSTIFICATIVAS_ID, aba)
    except drive_sync.DriveSyncError:
        return pd.DataFrame(columns=COLUNAS)
    if not linhas or len(linhas) < 2:
        return pd.DataFrame(columns=COLUNAS)
    cabecalho, *resto = linhas
    df = pd.DataFrame(resto, columns=cabecalho)
    for coluna in COLUNAS:
        if coluna not in df.columns:
            df[coluna] = ""
    return df[COLUNAS]


def salvar_justificativas_mes(mes_referencia, numeros_emergencia, textos, agora_str):
    """Substitui as justificativas do mês `mes_referencia` (todas as outras
    permanecem intactas) pelas linhas em `numeros_emergencia`/`textos` que
    tiverem texto não vazio."""
    todas = carregar_justificativas()
    outras = todas[todas["mes_referencia"] != mes_referencia]
    novas = pd.DataFrame({
        "numero_emergencia": [str(n) for n in numeros_emergencia],
        "mes_referencia": mes_referencia,
        "justificativa_empresa": [str(t).strip() for t in textos],
        "atualizado_em": agora_str,
    })
    novas = novas[novas["justificativa_empresa"] != ""]
    completo = pd.concat([outras, novas], ignore_index=True)
    aba = drive_sync.primeira_aba(PLANILHA_JUSTIFICATIVAS_ID)
    linhas = [COLUNAS] + completo[COLUNAS].astype(str).values.tolist()
    drive_sync.sobrescrever_aba(PLANILHA_JUSTIFICATIVAS_ID, aba, linhas)
