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
        "Informação": "Emergências (Abertas)",
        "De onde vem": 'Planilha Google Sheets "Prazo das emergências - C-98" (aba "Prazos das emergências")',
        "Como é atualizado": "Busca automática no Drive + reprocessa",
        "Frequência": "A cada 2h, seg-sex 8h-20h",
    },
    {
        "Informação": "Emergências Totais (histórico completo)",
        "De onde vem": "Mesma fonte de Emergências (provedor VEE ONE, todas as situações)",
        "Como é atualizado": "Recalculado junto quando Emergências atualiza",
        "Frequência": "Junto com Emergências",
    },
    {
        "Informação": "Reparáveis",
        "De onde vem": 'Planilha Google Sheets "Controle reparáveis C-98" (aba "Divulgação")',
        "Como é atualizado": "Busca automática no Drive + reprocessa",
        "Frequência": "A cada 2h, seg-sex 8h-20h",
    },
    {
        "Informação": "Empréstimos",
        "De onde vem": 'Planilha Google Sheets "Devoluções"',
        "Como é atualizado": "Busca automática no Drive + reprocessa",
        "Frequência": "A cada 2h, seg-sex 8h-20h",
    },
    {
        "Informação": "Pagamentos",
        "De onde vem": 'Planilha Google Sheets "005 CELOG 2025" (aba "Controle de Pagamentos")',
        "Como é atualizado": "Busca automática no Drive + reprocessa",
        "Frequência": "A cada 2h, seg-sex 8h-20h",
    },
    {
        "Informação": "Análise de Período",
        "De onde vem": "Histórico diário de Emergências já carregado",
        "Como é atualizado": "Sem fonte própria — acompanha Emergências",
        "Frequência": "Junto com Emergências",
    },
    {
        "Informação": "Cômputo Mensal (Fechamento Mensal)",
        "De onde vem": "Calculado a partir de Emergências + classificação do RAC (Coordenadoria)",
        "Como é atualizado": 'Recalcula sozinho quando Emergências atualiza, ou botão "Recalcular"',
        "Frequência": "Junto com Emergências / sob pedido",
    },
    {
        "Informação": "Apresentação (RMA)",
        "De onde vem": 'Nossa própria base (Cômputo/Empréstimos/Reparáveis/Pagamentos/Atrasos) + planilha oficial "RMA em andamento" (Drive)',
        "Como é atualizado": "Gerada na hora, por clique no botão",
        "Frequência": "Sob demanda (manual)",
    },
    {
        "Informação": "Ata de Reunião",
        "De onde vem": 'Transcrição/áudio da reunião (Drive) + planilha "RMA em andamento" (Drive) + nossa própria base',
        "Como é atualizado": "Gerada na hora, por clique no botão",
        "Frequência": "Sob demanda (manual)",
    },
]


def secao_fontes_dados():
    st.divider()
    _, col, _ = st.columns([1, 2, 1])
    with col:
        with st.expander("ℹ️ Fonte dos dados", expanded=False):
            st.dataframe(pd.DataFrame(FONTES), hide_index=True, width="stretch")
