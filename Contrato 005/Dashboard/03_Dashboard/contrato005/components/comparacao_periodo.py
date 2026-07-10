"""Lógica pura de comparação de período — usada pela página "Análise de
Período" (ver secoes/analise_periodo.py). Compara 2 snapshots do histórico
diário de emergências (historico_emergencias.csv, 1 linha por emergência
em aberto por dia, desde 2026-07-06) pra achar o que mudou entre eles:
novas, concluídas, entraram em atraso, saíram de atraso, mudança de
estoque. Nenhuma função aqui usa Streamlit — só pandas.
"""

import pandas as pd

CHAVE = "numero_emergencia"


def datas_disponiveis(historico):
    if historico is None or historico.empty:
        return []
    return sorted(pd.to_datetime(historico["data_snapshot"]).dt.date.unique())


def _snapshot_mais_proximo(datas_ordenadas, data_alvo):
    """Última data disponível <= data_alvo (None se nenhuma)."""
    candidatas = [d for d in datas_ordenadas if d <= data_alvo]
    return candidatas[-1] if candidatas else None


def periodo_anterior_equivalente(datas_ordenadas, data_inicio, data_fim):
    """Mesmo tamanho de período, imediatamente antes de `data_inicio`.
    Devolve (inicio_anterior, fim_anterior) ou (None, None) se não houver
    histórico suficiente ainda."""
    duracao = (data_fim - data_inicio).days
    fim_anterior_alvo = data_inicio - pd.Timedelta(days=1)
    inicio_anterior_alvo = fim_anterior_alvo - pd.Timedelta(days=duracao)
    fim_anterior = _snapshot_mais_proximo(datas_ordenadas, fim_anterior_alvo)
    inicio_anterior = _snapshot_mais_proximo(datas_ordenadas, inicio_anterior_alvo)
    if fim_anterior is None or inicio_anterior is None or fim_anterior < datas_ordenadas[0]:
        return None, None
    return inicio_anterior, fim_anterior


def _normalizar_estoque(valor):
    texto = str(valor).strip().lower()
    if texto in ("sim", "s"):
        return "sim"
    if texto in ("não", "nao", "n"):
        return "nao"
    return None


def diff_periodo(historico, data_inicio, data_fim):
    """Compara o snapshot de `data_inicio` com o de `data_fim` (ambos
    datetime.date). Devolve um dict de DataFrames: novas, concluidas,
    entraram_atraso, sairam_atraso, estoque_ficou_sem, estoque_passou_ter —
    todos com as colunas originais do historico, prontos pra exibir/filtrar."""
    hist = historico.copy()
    hist["data_snapshot"] = pd.to_datetime(hist["data_snapshot"]).dt.date

    ini = hist[hist["data_snapshot"] == data_inicio].set_index(CHAVE)
    fim = hist[hist["data_snapshot"] == data_fim].set_index(CHAVE)

    chaves_ini, chaves_fim = set(ini.index), set(fim.index)

    novas = fim.loc[sorted(chaves_fim - chaves_ini)].reset_index() if chaves_fim - chaves_ini else fim.iloc[0:0].reset_index()
    concluidas = ini.loc[sorted(chaves_ini - chaves_fim)].reset_index() if chaves_ini - chaves_fim else ini.iloc[0:0].reset_index()

    entraram_atraso, sairam_atraso = [], []
    estoque_ficou_sem, estoque_passou_ter = [], []
    for chave in chaves_ini & chaves_fim:
        a, f = ini.loc[chave], fim.loc[chave]
        atraso_a, atraso_f = a["dias_atraso"], f["dias_atraso"]
        if pd.notna(atraso_a) and pd.notna(atraso_f):
            if atraso_a <= 0 and atraso_f > 0:
                entraram_atraso.append(chave)
            elif atraso_a > 0 and atraso_f <= 0:
                sairam_atraso.append(chave)

        est_a, est_f = _normalizar_estoque(a.get("estoque")), _normalizar_estoque(f.get("estoque"))
        if est_a == "sim" and est_f == "nao":
            estoque_ficou_sem.append(chave)
        elif est_a == "nao" and est_f == "sim":
            estoque_passou_ter.append(chave)

    def _subset(chaves):
        return fim.loc[sorted(chaves)].reset_index() if chaves else fim.iloc[0:0].reset_index()

    return {
        "novas": novas,
        "concluidas": concluidas,
        "entraram_atraso": _subset(entraram_atraso),
        "sairam_atraso": _subset(sairam_atraso),
        "estoque_ficou_sem": _subset(estoque_ficou_sem),
        "estoque_passou_ter": _subset(estoque_passou_ter),
    }


def linha_do_tempo(historico, data_inicio, data_fim):
    """Total de emergências em aberto e total de atrasadas, por dia, entre
    data_inicio e data_fim (inclusive) — pra gráfico de evolução diária."""
    hist = historico.copy()
    hist["data_snapshot"] = pd.to_datetime(hist["data_snapshot"]).dt.date
    janela = hist[(hist["data_snapshot"] >= data_inicio) & (hist["data_snapshot"] <= data_fim)]
    if janela.empty:
        return pd.DataFrame(columns=["data", "total_aberto", "total_atrasado"])
    agrupado = janela.groupby("data_snapshot").apply(
        lambda g: pd.Series({
            "total_aberto": len(g),
            "total_atrasado": int((g["dias_atraso"] > 0).sum()),
        }),
        include_groups=False,
    ).reset_index().rename(columns={"data_snapshot": "data"})
    return agrupado.sort_values("data")
