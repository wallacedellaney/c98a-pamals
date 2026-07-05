"""Filtro genérico por coluna (estilo AutoFiltro do Excel) — um multiselect
por coluna da tabela, dentro de um expander, aplicável a qualquer DataFrame já
formatado pra exibição."""

import streamlit as st


def filtro_colunas(df, key_prefix, titulo="🔍 Filtros por coluna"):
    """Mostra um multiselect por coluna de `df` (dentro de um expander) e
    retorna o DataFrame já filtrado pelas seleções feitas."""
    if df.empty:
        return df

    with st.expander(titulo):
        selecoes = {}
        colunas = st.columns(3)
        for i, coluna in enumerate(df.columns):
            with colunas[i % 3]:
                valores = sorted(df[coluna].dropna().unique().tolist(), key=str)
                escolhidos = st.multiselect(str(coluna), valores, key=f"{key_prefix}_col_{coluna}")
                if escolhidos:
                    selecoes[coluna] = escolhidos

    filtrado = df
    for coluna, escolhidos in selecoes.items():
        filtrado = filtrado[filtrado[coluna].isin(escolhidos)]
    return filtrado
