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

from shared.verificacao_ao_vivo import criar_verificador
from projetos.components import paleta
from projetos.components.fontes_dados import secao_fontes_dados
from projetos.data.atualizar_drive import atualizar_fonte
from projetos.data.carregar_dados import carregar_tudo
from projetos.secoes import selecao, mta, tpjl

# Verificação ao vivo (2026-07-27, ver shared/verificacao_ao_vivo.py) —
# mesmo mecanismo já usado em Coordenadoria/Contrato 005: confere sozinho
# ao abrir o site, sem depender só do GitHub Actions/launchd (Wallace:
# "nada roda automatico ja descobri, ruim demais ne"). Usa
# `atualizar_fonte()` (subprocesso, já existia em `atualizar_drive.py`) em
# vez de importar o extrator direto — evita colisão de módulo `common`
# entre as 3 áreas quando rodam no mesmo processo (ver comentário
# equivalente em contrato_app.py, mesmo bug real achado ao testar).
_verificar_mta = criar_verificador("MTA", lambda: atualizar_fonte("mta"))
_verificar_tpjl = criar_verificador("TPJL", lambda: atualizar_fonte("tpjl"))
_verificar_tpjl_extras = criar_verificador("TPJL Extras", lambda: atualizar_fonte("tpjl_extras"))

PAGINAS = {"MTA": mta, "TPJL": tpjl}


def render(ao_voltar=None):
    if "projetos_pagina" not in st.session_state:
        st.session_state["projetos_pagina"] = None

    paleta.injetar_tema()
    _verificar_mta()
    _verificar_tpjl()
    _verificar_tpjl_extras()
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
