"""Componente de "barra temporal" — desde 2026-07-10, MTA e TPJL guardam um
snapshot diário (`historico_mta.csv`/`historico_tpjl.csv`, gravado dentro de
`atualizar_do_drive()` de cada extrator). Esse componente monta o slider de
datas + a comparação (novos/removidos/alterados) entre o dia escolhido e o
snapshot mais recente. Pedido do Wallace em 2026-07-09: "arrastar e ver a
evolução na planilha, sempre atualizado no padrão das outras" (mesmo
princípio já usado no histórico de RAC/Emergências, só que aqui com um
controle de arrastar em vez de selecionar aeronave/data fixa).

Só existe história a partir do dia em que a automação começou a gravar —
não há como reconstruir o passado.
"""

import pandas as pd
import streamlit as st

from projetos.components.paleta import INK, LINE, PANEL, SECONDARY, STATUS


def selecionar_data_comparacao(historico, key):
    """Mostra o slider de datas disponíveis (exceto a mais recente, que é o
    "hoje" usado como referência) e devolve (data_escolhida, data_mais_recente)
    — ou (None, None) se ainda não há histórico suficiente."""
    if historico is None or historico.empty:
        st.info("Histórico ainda não começou a ser gravado — vai aparecer aqui a partir da próxima "
                "atualização automática (a cada 2h, seg-sex).")
        return None, None

    datas = sorted(historico["data_snapshot"].unique())
    if len(datas) < 2:
        inicio = pd.Timestamp(datas[0]).strftime("%d/%m/%Y")
        st.info(f"Histórico começou em {inicio} — ainda não há um dia anterior pra comparar. "
                "A barra fica utilizável conforme os dias forem passando.")
        return None, None

    mais_recente = datas[-1]
    opcoes = datas[:-1]
    escolhida = st.select_slider(
        f"Arraste pra comparar um dia anterior com hoje ({pd.Timestamp(mais_recente).strftime('%d/%m/%Y')})",
        options=opcoes,
        value=opcoes[0],
        format_func=lambda d: pd.Timestamp(d).strftime("%d/%m/%Y"),
        key=key,
    )
    return escolhida, mais_recente


def calcular_evolucao(historico, chave, data_escolhida, data_atual):
    """Compara o snapshot de `data_escolhida` com o de `data_atual` usando
    `chave` (lista de colunas) como identificador do item. Devolve
    (novos, removidos, alterados) — cada um um DataFrame no formato do
    snapshot atual (ou do anterior, no caso de removidos)."""
    anterior = historico[historico["data_snapshot"] == data_escolhida].copy()
    atual = historico[historico["data_snapshot"] == data_atual].copy()

    anterior["_chave"] = anterior[chave].astype(str).agg("|".join, axis=1)
    atual["_chave"] = atual[chave].astype(str).agg("|".join, axis=1)

    chaves_anteriores = set(anterior["_chave"])
    chaves_atuais = set(atual["_chave"])

    novos = atual[atual["_chave"].isin(chaves_atuais - chaves_anteriores)].drop(columns="_chave")
    removidos = anterior[anterior["_chave"].isin(chaves_anteriores - chaves_atuais)].drop(columns="_chave")

    comuns = chaves_atuais & chaves_anteriores
    colunas_comparar = [c for c in atual.columns if c not in ("data_snapshot", "_chave", *chave)]

    anterior_idx = anterior.set_index("_chave")
    atual_idx = atual.set_index("_chave")
    alteradas = []
    for chave_valor in comuns:
        linha_ant = anterior_idx.loc[chave_valor]
        linha_atu = atual_idx.loc[chave_valor]
        if isinstance(linha_ant, pd.DataFrame):
            linha_ant = linha_ant.iloc[0]
        if isinstance(linha_atu, pd.DataFrame):
            linha_atu = linha_atu.iloc[0]
        if any(str(linha_ant[c]) != str(linha_atu[c]) for c in colunas_comparar):
            alteradas.append(chave_valor)

    alterados = atual[atual["_chave"].isin(alteradas)].drop(columns="_chave") if alteradas else atual.iloc[0:0].drop(columns="_chave")
    return novos, removidos, alterados


def secao_evolucao(historico, chave, key_slider, colunas_exibir, nomes_colunas=None):
    """Seção completa: slider + 3 blocos (novos/removidos/alterados)."""
    st.markdown('<div class="pj-titulo-secao">Evolução</div>', unsafe_allow_html=True)
    data_escolhida, data_atual = selecionar_data_comparacao(historico, key_slider)
    if data_escolhida is None:
        return

    novos, removidos, alterados = calcular_evolucao(historico, chave, data_escolhida, data_atual)
    escolhida_fmt = pd.Timestamp(data_escolhida).strftime("%d/%m/%Y")
    atual_fmt = pd.Timestamp(data_atual).strftime("%d/%m/%Y")
    st.caption(f"Comparando {escolhida_fmt} → {atual_fmt}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Novos", len(novos))
    c2.metric("Removidos/concluídos", len(removidos))
    c3.metric("Alterados", len(alterados))

    if novos.empty and removidos.empty and alterados.empty:
        st.success(f"Nenhuma mudança entre {escolhida_fmt} e {atual_fmt}.")
        return

    aba_novos, aba_removidos, aba_alterados = st.tabs([
        f"Novos ({len(novos)})", f"Removidos ({len(removidos)})", f"Alterados ({len(alterados)})",
    ])
    with aba_novos:
        if novos.empty:
            st.caption("Nenhum item novo.")
        else:
            tabela = novos[colunas_exibir].rename(columns=nomes_colunas or {})
            st.dataframe(tabela, hide_index=True, width="stretch", height=260)
    with aba_removidos:
        if removidos.empty:
            st.caption("Nenhum item removido/concluído.")
        else:
            tabela = removidos[colunas_exibir].rename(columns=nomes_colunas or {})
            st.dataframe(tabela, hide_index=True, width="stretch", height=260)
    with aba_alterados:
        if alterados.empty:
            st.caption("Nenhum item alterado.")
        else:
            tabela = alterados[colunas_exibir].rename(columns=nomes_colunas or {})
            st.dataframe(tabela, hide_index=True, width="stretch", height=260)
