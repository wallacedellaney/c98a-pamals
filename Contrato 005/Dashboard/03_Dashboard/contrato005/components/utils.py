"""Utilidades pequenas e genéricas, compartilhadas entre as seções."""

import pandas as pd


def formatar_moeda(valor):
    """"R$ 40.817,16" (separador de milhar '.', decimal ',') — não
    `f"R$ {valor:,.2f}"` puro, que dá "R$ 40,817.16" (estilo americano).
    Achado pelo Wallace em 2026-07-18: "o pedenten nos dois dasbord ta
    assim 40,817... parece que é 40 reais" — lendo à brasileira, a vírgula
    do formato americano passa a impressão de que R$ 40.817,16 é só
    R$ 40,82."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "—"
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def formatar_numero(valor, casas=2):
    """Mesma correção de `formatar_moeda`, mas sem o "R$" — pra números
    grandes que não são dinheiro (ex.: índice IPCA), que sofrem a mesma
    confusão de separador se formatados com `:,.Nf}` puro."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "—"
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


AVISO_MMAM_PREVIA = (
    "⚠️ **Esta MMAM é uma prévia**, calculada automaticamente a partir dos "
    "registros de emergências AIFP/IPLR sem estoque disponível na "
    "plataforma — não é o valor oficial da Pré-RMA. Como é calculada: cada "
    "aeronave dentro do contrato começa negativada (0) no próximo dia útil "
    "após a data da informação de uma emergência AIFP/IPLR sem estoque, e "
    "volta a montada (1) no dia do cancelamento/conclusão; sem estoque "
    "disponível, não nega. **Pode divergir do valor real** porque não "
    "considera ajustes manuais feitos direto na planilha oficial (Pré-RMA) "
    "nem eventuais feriados (só pula sábado/domingo). Ver "
    "00_Instrucoes/computo_mensal.md."
)


def ordenar_unicos(serie):
    """`sorted(serie.dropna().unique())`, mas seguro contra colunas com
    tipos misturados (ex.: PN com valores numéricos e texto na mesma
    planilha) — `sorted()` puro quebra com `TypeError: '<' not supported
    between instances of 'int' and 'str'` nesse caso (bug real visto em
    2026-07-13 na tela Reparáveis, depois de uma atualização de dados).
    Ordena pela representação em string, mas devolve os valores originais."""
    return sorted(serie.dropna().unique(), key=str)
