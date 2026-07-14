"""Painel discreto "Fonte dos dados" — botão pequeno, centralizado, no
rodapé do dashboard (pedido do Wallace em 2026-07-14: "coloca bem pequeno...
no centro inferior explicando de forma tabelado quando clicar, de onde vem
cada informação, como é atualizado, qual a frequência"). Nome escolhido pelo
Claude (Wallace pediu: "primeiro como chamar").

Tabela mantida à mão aqui — reflete o que está documentado em
00_Instrucoes/ e no CLAUDE.md da raiz (seção "Atualização de dados").
Atualizar esta lista junto de qualquer mudança na automação/fontes. Duplicado
por área (mesmo motivo de sempre: sem import entre pacotes de áreas
diferentes — ver C-98A PAMALS/CLAUDE.md).

Nome final "Fonte dos dados" escolhido pelo Wallace (proposta inicial do
Claude era "De onde vêm os dados")."""

import pandas as pd
import streamlit as st

FONTES = [
    {
        "Informação": "RAC (configuração das aeronaves)",
        "De onde vem": 'Planilha Google Sheets "Análise crítica de emergências C-98 2026"',
        "Como é atualizado": "Busca automática no Drive + reprocessa",
        "Frequência": "A cada 2h, seg-sex 8h-20h",
    },
    {
        "Informação": "Disponibilidade Diária",
        "De onde vem": 'Google Drive, pasta "Atualização de Disponibilidade" (1 documento por dia)',
        "Como é atualizado": "Busca automática no Drive + reprocessa",
        "Frequência": "A cada 2h, seg-sex 8h-20h",
    },
    {
        "Informação": "Vencimentos — TMOT",
        "De onde vem": 'Planilha Google Sheets "Vencimentos", aba C-98U8',
        "Como é atualizado": "Busca automática no Drive + reprocessa",
        "Frequência": "A cada 2h, seg-sex 8h-20h",
    },
    {
        "Informação": "Vencimentos — Operadores",
        "De onde vem": 'Arquivo próprio de cada operador (9 no total), pasta Drive "MAPEM / DIAGONAL / VENCIMENTOS"',
        "Como é atualizado": "Buscado manualmente, sob pedido ao Claude",
        "Frequência": "Manual (sem data fixa)",
    },
    {
        "Informação": "Diagonal de Manutenção",
        "De onde vem": 'Mesma pasta Drive dos operadores (arquivo "Diagonal de Manutenção"/"Diagonal de Inspeção")',
        "Como é atualizado": "Buscado manualmente, sob pedido ao Claude",
        "Frequência": "Manual (sem data fixa)",
    },
    {
        "Informação": "Dashboard Geral",
        "De onde vem": "Combina RAC + Disponibilidade Diária + Vencimentos + Diagonal",
        "Como é atualizado": "Sem fonte própria — acompanha as 4 acima",
        "Frequência": "Acompanha as fontes acima",
    },
    {
        "Informação": "Previsão Mensal",
        "De onde vem": "Ainda não definida (stub)",
        "Como é atualizado": "—",
        "Frequência": "—",
    },
]


def secao_fontes_dados():
    st.divider()
    _, col, _ = st.columns([1, 2, 1])
    with col:
        with st.expander("ℹ️ Fonte dos dados", expanded=False):
            st.dataframe(pd.DataFrame(FONTES), hide_index=True, width="stretch")
