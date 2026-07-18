"""
Runner standalone do dashboard do Contrato 005 — deploy próprio, separado do
site principal "C-98A PAMA-LS", pra dar acesso à empresa (VEE ONE) só a essa
área, sem tocar em Coordenadoria/Projetos. Pedido do Wallace em 2026-07-18:
"vamos entao preparar so a parte do contrato ... o site vamos chamar de
005CELOG2025". Decisão (vs. senha só ao entrar na área dentro do site
principal): deploy separado no Streamlit Cloud, mesmo repositório do GitHub,
apontando pra este arquivo — isolamento de verdade (processo próprio, nunca
importa código/dado de Coordenadoria/Projetos), em vez de só esconder na
tela. Ver 00_Instrucoes/site_005celog2025.md.

Atualiza sozinho, no mesmo ciclo automático de 2 em 2h já existente (mesmo
repositório/dados — não precisa de nenhuma automação nova).

**Sem tela de login por enquanto** (decisão do Wallace em 2026-07-18: "por
enquanto sem senha, o dela vou pensar uma forma mais segura com email e
talz") — só uma tela inicial com o hero (foto do Caravan/hangar, pedido do
Wallace: "pode deixar aquele dasborad la inicial, clicando para entrar no
contrato, com a foto do caravan e talz", reaproveitando `home_hero.py` do
site principal) e um botão "Entrar".

Precisa de secret PRÓPRIO neste deploy (Streamlit Cloud → Settings →
Secrets deste app, separado do site principal):
- `GOOGLE_SERVICE_ACCOUNT_JSON` — mesma credencial do Google usada no site
  principal, precisa ser configurada de novo aqui (Secrets não são
  compartilhados entre apps do Streamlit Cloud) — necessária pros botões
  "Apresentação (RMA)"/"Ata de Reunião"/"Atualizar dados".
"""

import sys
from pathlib import Path

import streamlit as st

from contrato_app import render

RAIZ = Path(__file__).resolve().parents[3]
# Permite `from shared import drive_sync, estado` (usado por
# atualizar_drive.py e pelos botões de Apresentação/Ata) e `import
# home_hero` (hero da tela inicial), mesmo rodando este app isolado, sem o
# C-98A PAMALS/app.py principal.
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from home_hero import render_hero

st.set_page_config(page_title="005CELOG2025", page_icon="🛡️", layout="wide")


def _tela_inicial():
    st.markdown(
        """
        <style>
            #MainMenu {display: none;}
            footer {display: none;}
            header {display: none;}
            [data-testid="stToolbar"] {display: none;}
            .stApp { background: #0B1118; color: #F3F6F9; }
            .block-container { max-width: 1100px; padding-top: 3rem; }
            .cel-titulo {
                text-align: center; font-size: 28px; font-weight: 900;
                letter-spacing: 2px; color: #F3F6F9; margin-bottom: 6px;
            }
            .cel-sub {
                text-align: center; color: #A6B2C1; font-size: 14.5px; margin-bottom: 26px;
            }
            div.stButton > button {
                width: 100%; height: 50px; border-radius: 12px;
                border: 1px solid rgba(244,166,42,0.6);
                background: rgba(244,166,42,0.08); color: #F4A62A;
                font-weight: 800; font-size: 15px; margin-top: 22px;
            }
            div.stButton > button:hover {
                background: #F4A62A; color: #0B1118; border-color: #F4A62A;
            }
        </style>
        <div class="cel-titulo">005CELOG2025</div>
        <div class="cel-sub">Contrato 005/CELOG-PAMALS/2025 — acompanhamento do contrato</div>
        """,
        unsafe_allow_html=True,
    )
    render_hero()
    _, col, _ = st.columns([1, 1, 1])
    with col:
        if st.button("Entrar →", key="cel_entrar"):
            st.session_state["entrou"] = True
            st.rerun()


if "entrou" not in st.session_state:
    st.session_state["entrou"] = False

if not st.session_state["entrou"]:
    _tela_inicial()
    st.stop()

render()
