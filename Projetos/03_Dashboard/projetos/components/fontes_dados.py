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
Claude era "De onde vêm os dados").

**Coluna "Última atualização" (2026-07-14, pedido do Wallace: "cria uma
coluna que busca a ultima vez que foi atualizado so para saber")** — busca a
data de modificação real do arquivo tratado (`_chave` aponta pra uma chave
de `dados`, já carregada por `carregar_dados.py`), não um valor fixo."""

import pandas as pd
import streamlit as st

from shared import horario

FONTES = [
    {
        "Informação": "MTA — Acompanhamento e Solicitações",
        "De onde vem": 'Planilha Google Sheets "MTA - Acompanhamento e Solicitações" (aba "Solicitações")',
        "Como é atualizado": "Busca automática no Drive + reprocessa",
        "Frequência": "A cada 2h, seg-sex 8h-20h",
        "_chave": "mta_atualizado_em",
    },
    {
        "Informação": "TPJL — Requisições (2025/2026)",
        "De onde vem": 'Planilhas "TPOB - Controle CABW 2025" e "2026" (aba "COORDENADORES")',
        "Como é atualizado": "Busca automática no Drive + reprocessa",
        "Frequência": "A cada 2h, seg-sex 8h-20h",
        "_chave": "tpjl_atualizado_em",
    },
    {
        "Informação": "TPJL — Consumo / Estoque / Solicitações",
        "De onde vem": '3 arquivos na pasta Drive "Planilhas TPLJ"',
        "Como é atualizado": "Botão no site (ainda sem compartilhamento configurado com a conta de serviço — busca real pendente)",
        "Frequência": "Manual, por enquanto",
        "_chave": "tpjl_extras_atualizado_em",
    },
]


def _formatar(mtime):
    if not mtime:
        return "—"
    return horario.fromtimestamp_br(mtime).strftime("%d/%m/%Y %H:%M")


def secao_fontes_dados(dados):
    st.divider()
    _, col, _ = st.columns([1, 2, 1])
    with col:
        with st.expander("ℹ️ Fonte dos dados", expanded=False):
            linhas = [
                {k: v for k, v in fonte.items() if k != "_chave"}
                | {"Última atualização": _formatar(dados.get(fonte["_chave"]) if fonte["_chave"] else None)}
                for fonte in FONTES
            ]
            st.dataframe(pd.DataFrame(linhas), hide_index=True, width="stretch")
