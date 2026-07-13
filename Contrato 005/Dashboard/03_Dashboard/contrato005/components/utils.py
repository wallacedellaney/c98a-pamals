"""Utilidades pequenas e genéricas, compartilhadas entre as seções."""


def ordenar_unicos(serie):
    """`sorted(serie.dropna().unique())`, mas seguro contra colunas com
    tipos misturados (ex.: PN com valores numéricos e texto na mesma
    planilha) — `sorted()` puro quebra com `TypeError: '<' not supported
    between instances of 'int' and 'str'` nesse caso (bug real visto em
    2026-07-13 na tela Reparáveis, depois de uma atualização de dados).
    Ordena pela representação em string, mas devolve os valores originais."""
    return sorted(serie.dropna().unique(), key=str)
