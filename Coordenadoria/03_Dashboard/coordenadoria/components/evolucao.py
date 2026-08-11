"""Componente de "barra temporal" — slider de datas + comparação (novos/
removidos/alterados) entre o dia escolhido e o snapshot mais recente. Mesmo
componente já usado em Projetos (`projetos/components/evolucao.py`) —
duplicado aqui em vez de importado de lá (sem import entre pacotes de áreas
diferentes, ver C-98A PAMALS/CLAUDE.md). Primeiro uso na Coordenadoria:
Motores (2026-07-14, pedido do Wallace: "vai ter historico pq vai ter
atualizacao diaria").

Só existe história a partir do dia em que a gravação começou — não há como
reconstruir o passado.

**Detalhe "o que era → o que virou" (pedido do Wallace em 2026-08-11)**: a
aba "Alterados" não mostrava só o valor atual de cada item mudado, sem dar
pra saber o que tinha mudado de fato. Agora `calcular_evolucao` também monta
uma tabela campo a campo (`detalhe`) com o valor de cada campo antes e
depois, exibida na aba "Alterados" abaixo da tabela resumo. (Mesma mudança
espelhada em `Projetos/03_Dashboard/projetos/components/evolucao.py`.)
"""

import pandas as pd
import streamlit as st


def _formatar_valor(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    if isinstance(v, str) and v.strip() == "":
        return "—"
    if isinstance(v, pd.Timestamp):
        return v.strftime("%d/%m/%Y")
    return str(v)


def selecionar_data_comparacao(historico, key):
    """Mostra o slider de datas disponíveis (exceto a mais recente, que é o
    "hoje" usado como referência) e devolve (data_escolhida, data_mais_recente)
    — ou (None, None) se ainda não há histórico suficiente."""
    if historico is None or historico.empty:
        st.info("Histórico ainda não começou a ser gravado — vai aparecer aqui a partir da próxima atualização.")
        return None, None

    datas = sorted(historico["data_snapshot"].unique())
    if len(datas) < 2:
        inicio = pd.Timestamp(datas[0]).strftime("%d/%m/%Y")
        st.info(f"Histórico começou em {inicio} — ainda não há um dia anterior pra comparar. "
                "A barra fica utilizável conforme os dias forem passando.")
        return None, None

    mais_recente = datas[-1]
    opcoes = datas[:-1]
    if len(opcoes) == 1:
        # st.select_slider com 1 única opção quebra no navegador ("RangeError:
        # min (0) is equal/bigger than max (0)" — o slider JS não aceita
        # min==max) — achado pelo Wallace em 2026-07-16 (TPJL). Só 2 dias de
        # histórico ainda não dá pra arrastar nada mesmo, usa o único direto.
        escolhida = opcoes[0]
        st.caption(f"Só 1 dia anterior disponível ainda ({pd.Timestamp(escolhida).strftime('%d/%m/%Y')}) — a barra de arrastar aparece a partir do 3° dia de histórico.")
    else:
        escolhida = st.select_slider(
            f"Arraste pra comparar um dia anterior com hoje ({pd.Timestamp(mais_recente).strftime('%d/%m/%Y')})",
            options=opcoes,
            value=opcoes[0],
            format_func=lambda d: pd.Timestamp(d).strftime("%d/%m/%Y"),
            key=key,
        )
    return escolhida, mais_recente


def calcular_evolucao(historico, chave, data_escolhida, data_atual, nomes_colunas=None):
    """Compara o snapshot de `data_escolhida` com o de `data_atual` usando
    `chave` (lista de colunas) como identificador do item. Devolve
    (novos, removidos, alterados, detalhe) — os 3 primeiros são DataFrames no
    formato do snapshot atual (ou do anterior, no caso de removidos);
    `detalhe` é uma tabela campo a campo (Item/Campo/Era/Virou) só com os
    campos que de fato mudaram em cada item alterado."""
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
    linhas_detalhe = []
    for chave_valor in comuns:
        linha_ant = anterior_idx.loc[chave_valor]
        linha_atu = atual_idx.loc[chave_valor]
        if isinstance(linha_ant, pd.DataFrame):
            linha_ant = linha_ant.iloc[0]
        if isinstance(linha_atu, pd.DataFrame):
            linha_atu = linha_atu.iloc[0]
        campos_mudados = [c for c in colunas_comparar if str(linha_ant[c]) != str(linha_atu[c])]
        if campos_mudados:
            alteradas.append(chave_valor)
            rotulo_item = " / ".join(
                f"{(nomes_colunas or {}).get(c, c)} {linha_atu[c]}" for c in chave
            )
            for c in campos_mudados:
                linhas_detalhe.append({
                    "Item": rotulo_item,
                    "Campo": (nomes_colunas or {}).get(c, c),
                    "Era": _formatar_valor(linha_ant[c]),
                    "Virou": _formatar_valor(linha_atu[c]),
                })

    alterados = atual[atual["_chave"].isin(alteradas)].drop(columns="_chave") if alteradas else atual.iloc[0:0].drop(columns="_chave")
    detalhe = pd.DataFrame(linhas_detalhe, columns=["Item", "Campo", "Era", "Virou"])
    return novos, removidos, alterados, detalhe


def secao_evolucao(historico, chave, key_slider, colunas_exibir, nomes_colunas=None, titulo="Evolução"):
    """Seção completa: slider + 3 blocos (novos/removidos/alterados)."""
    if titulo:
        st.markdown(f"##### {titulo}")
    data_escolhida, data_atual = selecionar_data_comparacao(historico, key_slider)
    if data_escolhida is None:
        return

    novos, removidos, alterados, detalhe = calcular_evolucao(historico, chave, data_escolhida, data_atual, nomes_colunas)
    escolhida_fmt = pd.Timestamp(data_escolhida).strftime("%d/%m/%Y")
    atual_fmt = pd.Timestamp(data_atual).strftime("%d/%m/%Y")
    st.caption(f"Comparando {escolhida_fmt} → {atual_fmt}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Novos", len(novos))
    c2.metric("Removidos", len(removidos))
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
            st.dataframe(novos[colunas_exibir].rename(columns=nomes_colunas or {}), hide_index=True, width="stretch", height=260)
    with aba_removidos:
        if removidos.empty:
            st.caption("Nenhum item removido.")
        else:
            st.dataframe(removidos[colunas_exibir].rename(columns=nomes_colunas or {}), hide_index=True, width="stretch", height=260)
    with aba_alterados:
        if alterados.empty:
            st.caption("Nenhum item alterado.")
        else:
            st.dataframe(alterados[colunas_exibir].rename(columns=nomes_colunas or {}), hide_index=True, width="stretch", height=260)
            st.markdown('<div style="margin-top:10px;font-size:13px;font-weight:600;">O que era → o que virou</div>', unsafe_allow_html=True)
            st.dataframe(detalhe, hide_index=True, width="stretch", height=min(260, 46 + 35 * len(detalhe)))
