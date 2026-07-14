"""
Entrada da área "Projetos" — página de seleção (MTA / TPJL) e os 2 dashboards
específicos. Diferente de Coordenadoria/Contrato 005 (abas lado a lado), aqui
a navegação é: seleção → dashboard do projeto → voltar à seleção → voltar ao
menu principal. Ver 00_Instrucoes/ (mta.md, tpjl.md) e CLAUDE.md desta pasta.

Tema visual centralizado em projetos/components/paleta.py (injetar_tema) —
revisão completa pedida pelo Wallace em 2026-07-09.

Exposto como função `render()` para ser embutido na página principal "C-98A
PAMALS" (ver ../../app.py), com um botão de voltar.
"""

import streamlit as st

from projetos.components import paleta
from projetos.components.fontes_dados import secao_fontes_dados
from projetos.data.carregar_dados import carregar_tudo
from projetos.secoes import selecao, mta, tpjl

PAGINAS = {"MTA": mta, "TPJL": tpjl}


def render(ao_voltar=None):
    if "projetos_pagina" not in st.session_state:
        st.session_state["projetos_pagina"] = None

    paleta.injetar_tema()
    dados = carregar_tudo()
    pagina = st.session_state["projetos_pagina"]

    col_voltar, _ = st.columns([2, 3])
    with col_voltar:
        if pagina is None:
            if ao_voltar is not None and st.button("← Voltar ao menu principal", key="proj_voltar_menu", width="stretch"):
                ao_voltar()
                st.rerun()
        else:
            if st.button("← Projetos", key="proj_voltar_selecao", width="stretch"):
                st.session_state["projetos_pagina"] = None
                st.rerun()

    if pagina is None:
        selecao.render(dados)
    else:
        PAGINAS[pagina].render(dados)

    secao_fontes_dados(dados)
