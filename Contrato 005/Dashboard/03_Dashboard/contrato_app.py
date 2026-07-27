"""
Dashboard interativo do Contrato 005 — 4 partes navegáveis por botões na parte
de baixo da tela: Visão Geral, Reparáveis, Emergências Abertas, Pagamentos.

Lê somente arquivos de 02_Dados_Tratados/ (ver 00_Instrucoes/dashboard.md).
Identidade visual "Torre de Controle" — ver 00_Instrucoes/00_BRAND/identidade_visual.md.

Exposto como função `render()` para poder ser embutido dentro da página principal
"C-98A PAMALS" (ver ../../../app.py), com um botão de voltar para o menu.
"""

import subprocess
import sys
from pathlib import Path

import streamlit as st

from shared import horario
from shared.verificacao_ao_vivo import criar_verificador
from contrato005.components import data_global
from contrato005.components.fontes_dados import secao_fontes_dados
from contrato005.components.paleta import AMBER, SECONDARY, LINE
from contrato005.data.atualizar_drive import atualizar_fonte
from contrato005.data.carregar_dados import carregar_tudo
from contrato005.secoes import (
    visao_geral, reparaveis, emergencias, emergencias_totais,
    fechamento_mensal, emprestimos, pagamentos, analise_periodo, reajuste,
)

# Verificação ao vivo (2026-07-27, ver shared/verificacao_ao_vivo.py) —
# Emergências, Pagamentos, Reparáveis e Empréstimos também têm
# `atualizar_do_drive()` própria; até agora só a Disponibilidade Diária
# (Coordenadoria) conferia sozinha ao abrir o site. Wallace: "nada roda
# automatico ja descobri, ruim demais ne" — GitHub Actions e o launchd do
# Mac continuam existindo como automação de fundo, mas não são mais a
# única forma do dado ficar em dia. Usa `atualizar_fonte()` (subprocesso,
# já existia pra `atualizar_drive.py`) em vez de importar o extrator
# direto — bug real achado ao testar: Contrato 005, Projetos e
# Coordenadoria têm cada um seu próprio `05_Scripts/python/common.py`, e
# como o site principal carrega as 3 áreas no MESMO processo, importar os
# extratores de mais de uma área ao mesmo tempo fazia elas colidirem no
# nome do módulo `common` (`ImportError: cannot import name
# 'XLSX_PAGAMENTOS' from 'common'` — o Python só permite 1 módulo chamado
# "common" por processo; o `common.py` errado ficava "grudado"). Rodando
# como subprocesso (interpretador novo a cada chamada), cada área monta o
# próprio sys.path do zero, sem esse risco.
_verificar_emergencias = criar_verificador("Emergências", lambda: atualizar_fonte("emergencias"))
_verificar_pagamentos = criar_verificador("Pagamentos", lambda: atualizar_fonte("pagamentos"))
_verificar_reparaveis = criar_verificador("Reparáveis", lambda: atualizar_fonte("reparaveis"))
_verificar_devolucoes = criar_verificador("Empréstimos", lambda: atualizar_fonte("devolucoes"))

PAGINAS = {
    "Visão Geral": visao_geral,
    "Reparáveis": reparaveis,
    "Emergências Abertas": emergencias,
    "Emergências Totais": emergencias_totais,
    "Análise de Período": analise_periodo,
    "Fechamento Mensal": fechamento_mensal,
    "Empréstimos": emprestimos,
    "Pagamentos": pagamentos,
    "Reajuste": reajuste,
}

DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_GERAR_DADOS = DASHBOARD_ROOT / "05_Scripts" / "python" / "gerar_dados_tratados.py"


def _atualizar_dados():
    """Roda de novo a extração a partir do que já está em 01_Bases_Originais/
    (não busca nada novo do Google Drive — isso é feito pelo Claude, sob
    pedido ou por agenda — ver CLAUDE.md)."""
    resultado = subprocess.run(
        [sys.executable, str(SCRIPT_GERAR_DADOS)],
        cwd=str(SCRIPT_GERAR_DADOS.parent),
        capture_output=True,
        text=True,
    )
    st.cache_data.clear()
    if resultado.returncode == 0:
        st.toast("Dados atualizados a partir de 01_Bases_Originais/.", icon="✅")
    else:
        st.error(f"Erro ao atualizar dados:\n\n{resultado.stderr or resultado.stdout}")


def render(ao_voltar=None, paginas_ocultas=(), modo_externo=False):
    """`paginas_ocultas`: nomes de PAGINAS pra não mostrar (nem no menu nem
    na navegação) — usado pelo deploy separado "005CELOG2025" (acesso da
    empresa) pra esconder "Fechamento Mensal" (Cômputo Mensal/Atrasos/
    Apresentação RMA/Ata de Reunião são conteúdo interno, não pra empresa
    ver — pedido do Wallace em 2026-07-18: "tira no fechamento mensal,
    apresntacao da rma"). O site principal continua chamando render() sem
    esse parâmetro, mostrando tudo.

    `modo_externo`: sinaliza pras próprias seções (via `dados["modo_externo"]`)
    esconder detalhe interno que não muda de página pra página só de olhar
    PAGINAS_OCULTAS — hoje usado por `pagamentos.py` (Empenhos) e pelo
    painel "Fonte dos dados" no fim desta função. Pedido do Wallace:
    "tira a fonte de dados, desse" / "tira empenho do pagamento tb, ela
    nao precis saber"."""
    paginas = {k: v for k, v in PAGINAS.items() if k not in paginas_ocultas}

    if "pagina" not in st.session_state or st.session_state["pagina"] not in paginas:
        st.session_state["pagina"] = next(iter(paginas))

    # Verificação ao vivo — antes de carregar qualquer dado, garante que as
    # 4 fontes estão em dia (busca no Drive na hora se necessário). Roda
    # nos 2 sites (principal e 005CELOG2025), já que os dois chamam este
    # `render()`.
    _verificar_emergencias()
    _verificar_pagamentos()
    _verificar_reparaveis()
    _verificar_devolucoes()

    dados = carregar_tudo()
    dados["modo_externo"] = modo_externo

    st.markdown(
        f"""
        <style>
        .c98-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 0.9rem;
            margin-bottom: 1.3rem;
            border-bottom: 1px solid {LINE};
        }}
        .c98-header .brand {{ display: flex; align-items: center; gap: 0.7rem; }}
        .c98-header .mark {{
            width: 2rem; height: 2rem;
            border: 1.5px solid {AMBER};
            border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-size: 0.72rem; font-weight: 700; color: {AMBER};
        }}
        .c98-header .name {{ font-size: 0.95rem; font-weight: 600; letter-spacing: 0.03em; }}
        .c98-header .name small {{
            display: block; font-size: 0.68rem; color: {SECONDARY};
            letter-spacing: 0.08em; font-weight: 400; margin-top: 0.15rem;
        }}
        .c98-header .clock {{ font-size: 0.78rem; color: {SECONDARY}; letter-spacing: 0.03em; }}

        h1 {{
            font-size: 1rem !important;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            font-weight: 600 !important;
            color: {SECONDARY} !important;
        }}

        /* Os dados (números/tabelas) são o protagonista — os gráficos só apoiam. */
        [data-testid="stMetricValue"] {{
            font-size: 2rem !important;
            font-weight: 700 !important;
            color: {AMBER} !important;
        }}
        [data-testid="stMetricLabel"] {{
            font-size: 0.72rem !important;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: {SECONDARY} !important;
        }}

        .c98-nav {{
            margin-top: 2rem;
            padding-top: 0.8rem;
            border-top: 1px solid {LINE};
        }}
        </style>

        <div class="c98-header">
            <div class="brand">
                <div class="mark">98</div>
                <div class="name">C-98 / OPS<small>CONTRATO 005 · CELOG-PAMALS · VEE ONE</small></div>
            </div>
            <div class="clock">HOJE {horario.agora_br().strftime('%d/%m/%Y')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_voltar, col_atualizar = st.columns([4, 1])
    with col_voltar:
        if ao_voltar is not None:
            if st.button("← Voltar ao menu"):
                ao_voltar()
                st.rerun()
    with col_atualizar:
        if st.button("🔄 Atualizar dados", width="stretch"):
            with st.spinner("Atualizando..."):
                _atualizar_dados()
            st.rerun()

    data_global.render_seletor_global(dados)
    st.divider()

    paginas[st.session_state["pagina"]].render(dados)

    st.markdown('<div class="c98-nav"></div>', unsafe_allow_html=True)
    nav_cols = st.columns(len(paginas))
    for col, nome in zip(nav_cols, paginas):
        with col:
            ativo = nome == st.session_state["pagina"]
            if st.button(nome, key=f"nav_{nome}", width="stretch",
                         type="primary" if ativo else "secondary"):
                st.session_state["pagina"] = nome
                st.rerun()

    st.caption(f"Dados atualizados em {horario.fromtimestamp_br(dados['atualizado_em']).strftime('%d/%m/%Y %H:%M')}")

    if not modo_externo:
        secao_fontes_dados(dados)
