"""
Carrega os arquivos tratados de 02_Dados_Tratados/ para o dashboard.

O cache é invalidado automaticamente quando o arquivo no disco muda (usamos a
data de modificação do arquivo como parte da chave do cache do Streamlit), sem
precisar reiniciar o app.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

DASHBOARD_ROOT = Path(__file__).resolve().parents[3]
DADOS_TRATADOS = DASHBOARD_ROOT / "02_Dados_Tratados"


@st.cache_data
def _ler_excel(caminho_str, _mtime, **kwargs):
    return pd.read_excel(caminho_str, **kwargs)


@st.cache_data
def _ler_csv(caminho_str, _mtime, **kwargs):
    return pd.read_csv(caminho_str, **kwargs)


def carregar_emergencias():
    caminho = DADOS_TRATADOS / "base_emergencias_tratada.xlsx"
    return _ler_excel(str(caminho), caminho.stat().st_mtime), caminho.stat().st_mtime


def carregar_historico_emergencias():
    """Snapshot diário das emergências em aberto, acumulado desde 2026-07-06
    (não existe histórico anterior a essa data). Ver emergencias.md."""
    caminho = DADOS_TRATADOS / "historico_emergencias.csv"
    if not caminho.exists():
        return pd.DataFrame(columns=[
            "data_snapshot", "numero_emergencia", "om", "matricula_aeronave", "pn",
            "nomenclatura", "situacao", "tpemg", "data_abertura", "prazo_entrega", "dpe", "dias_atraso",
            "estoque",
        ])
    mtime = caminho.stat().st_mtime
    df = _ler_csv(str(caminho), mtime, dtype={"matricula_aeronave": str, "numero_emergencia": str})
    df["data_snapshot"] = pd.to_datetime(df["data_snapshot"])
    return df


def carregar_emergencias_totais():
    """Todo o histórico de emergências (abertas e concluídas) do provedor
    VEE ONE, gerado sob demanda por extrair_historico_completo(). Ver
    emergencias.md — 'Histórico completo (VEE ONE, todas as situações)'."""
    caminho = DADOS_TRATADOS / "historico_completo_emergencias.xlsx"
    if not caminho.exists():
        return pd.DataFrame(), None
    mtime = caminho.stat().st_mtime
    return _ler_excel(str(caminho), mtime), mtime


def carregar_computo_mensal(ano, mes):
    """Cômputo Mensal (aba 1.2 da Pré-RNA) — matriz aeronave x dia calculada
    por calcular_computo_mensal.py. Ver 00_Instrucoes/computo_mensal.md."""
    pasta = DADOS_TRATADOS / "computo_mensal"
    mes_ref = f"{ano}-{mes:02d}"
    caminho_matriz = pasta / f"{mes_ref}_matriz.csv"
    caminho_motivos = pasta / f"{mes_ref}_motivos.csv"
    caminho_resumo = pasta / f"{mes_ref}_resumo.json"
    if not caminho_matriz.exists():
        return None, None, None
    mtime = caminho_matriz.stat().st_mtime
    df_matriz = _ler_csv(str(caminho_matriz), mtime, dtype={"matricula": str})
    try:
        # Mês sem nenhuma negativação grava um motivos.csv vazio (0 bytes) —
        # pd.read_csv quebra com EmptyDataError nesse caso (bug real visto em
        # 2026-07-14, reproduzido com 2025-12, mês sem histórico de emergências).
        df_motivos = (
            _ler_csv(str(caminho_motivos), caminho_motivos.stat().st_mtime, dtype={"matricula": str})
            if caminho_motivos.exists() else pd.DataFrame()
        )
    except pd.errors.EmptyDataError:
        df_motivos = pd.DataFrame()
    import json
    with open(caminho_resumo, encoding="utf-8") as f:
        resumo = json.load(f)
    return df_matriz, df_motivos, resumo


def carregar_devolucoes():
    """Empréstimos/devoluções de material — planilha "Devoluções". Ver
    00_Instrucoes/emprestimos.md. Status "Desconsiderado" (pedido do
    Wallace, 2026-07-13: "arrumei os status desses itens, chama
    desconsiderado, nao entra nunca na conta de nada") é removido aqui,
    antes de qualquer estatística/gráfico/tabela — itens que distorciam
    a soma por quantidade (linhas de quantidade grande já resolvidas por
    outro motivo, não uma devolução real)."""
    caminho = DADOS_TRATADOS / "base_devolucoes_tratada.xlsx"
    if not caminho.exists():
        return pd.DataFrame(), None
    mtime = caminho.stat().st_mtime
    df = _ler_excel(str(caminho), mtime)
    df["pedido_envio"] = pd.to_datetime(df["pedido_envio"], errors="coerce")
    df["data_devolucao"] = pd.to_datetime(df["data_devolucao"], errors="coerce")
    df = df[df["status"] != "Desconsiderado"].copy()
    return df, mtime


def carregar_reparaveis():
    caminho = DADOS_TRATADOS / "base_reparaveis_tratada.xlsx"
    return _ler_excel(str(caminho), caminho.stat().st_mtime), caminho.stat().st_mtime


def _carregar_historico_generico(nome_arquivo, dtype=None):
    """Loader genérico pros históricos diários usados no controle de data
    global (ver components/data_global.py) — todos seguem o mesmo formato
    (1 coluna data_snapshot + colunas específicas da fonte)."""
    caminho = DADOS_TRATADOS / nome_arquivo
    if not caminho.exists():
        return pd.DataFrame(columns=["data_snapshot"])
    mtime = caminho.stat().st_mtime
    return _ler_csv(str(caminho), mtime, dtype=dtype or {})


def carregar_historico_reparaveis():
    """Snapshot diário das OS em aberto — só existe a partir de 2026-07-10
    (dia em que essa gravação começou). Ver 00_Instrucoes/analise_periodo.md."""
    return _carregar_historico_generico("historico_reparaveis.csv", dtype={"os": str})


def carregar_historico_pagamentos():
    """Snapshot diário dos lançamentos de pagamento — só existe a partir de
    2026-07-10. Ver 00_Instrucoes/analise_periodo.md."""
    return _carregar_historico_generico("historico_pagamentos.csv")


def carregar_historico_devolucoes():
    """Snapshot diário dos itens de Empréstimos — só existe a partir de
    2026-07-10. Ver 00_Instrucoes/analise_periodo.md."""
    return _carregar_historico_generico("historico_devolucoes.csv", dtype={"numero_ordem": str})


def carregar_pagamentos():
    caminho = DADOS_TRATADOS / "base_pagamentos_tratada.xlsx"
    mtime = caminho.stat().st_mtime
    df = _ler_excel(str(caminho), mtime, sheet_name="Pagamentos")
    contrato = _ler_excel(str(caminho), mtime, sheet_name="Contrato").iloc[0]
    empenhos = _ler_excel(str(caminho), mtime, sheet_name="Empenhos")
    return df, contrato, empenhos, mtime


def carregar_tudo():
    df_emergencias, mtime_emerg = carregar_emergencias()
    historico_emergencias = carregar_historico_emergencias()
    df_emergencias_totais, mtime_emerg_totais = carregar_emergencias_totais()
    df_devolucoes, mtime_devolucoes = carregar_devolucoes()
    df_reparaveis, mtime_rep = carregar_reparaveis()
    df_pagamentos, contrato, empenhos, mtime_pag = carregar_pagamentos()
    return {
        "emergencias": df_emergencias,
        "historico_emergencias": historico_emergencias,
        "emergencias_totais": df_emergencias_totais,
        "emergencias_totais_atualizado_em": mtime_emerg_totais,
        "devolucoes": df_devolucoes,
        "devolucoes_atualizado_em": mtime_devolucoes,
        "historico_devolucoes": carregar_historico_devolucoes(),
        "reparaveis": df_reparaveis,
        "historico_reparaveis": carregar_historico_reparaveis(),
        "pagamentos": df_pagamentos,
        "historico_pagamentos": carregar_historico_pagamentos(),
        "contrato": contrato,
        "empenhos": empenhos,
        "atualizado_em": max(mtime_emerg, mtime_rep, mtime_pag),
    }
