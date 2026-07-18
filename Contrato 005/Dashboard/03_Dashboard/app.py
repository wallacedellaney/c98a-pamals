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
talz") — o fluxo é: 1) hero (foto do Caravan/hangar, reaproveitando
`home_hero.py` do site principal) + botão "Entrar", 2) aviso de
transparência + botão "Concordar", 3) dashboard. "Fechamento Mensal"
(Cômputo Mensal/Atrasos/Apresentação RMA/Ata de Reunião) fica **escondido**
nesse deploy — conteúdo interno, não pra empresa ver (pedido do Wallace:
"tira no fechamento mensal, apresntacao da rma" / "e tb tira a producao da
ata").

Precisa de secret PRÓPRIO neste deploy (Streamlit Cloud → Settings →
Secrets deste app, separado do site principal):
- `GOOGLE_SERVICE_ACCOUNT_JSON` — mesma credencial do Google usada no site
  principal, precisa ser configurada de novo aqui (Secrets não são
  compartilhados entre apps do Streamlit Cloud) — necessária pro botão
  "Atualizar dados".
"""

import sys
from pathlib import Path

import streamlit as st

from contrato_app import render

RAIZ = Path(__file__).resolve().parents[3]
# Permite `from shared import drive_sync, estado` (usado por
# atualizar_drive.py) e `import home_hero` (hero da tela inicial), mesmo
# rodando este app isolado, sem o C-98A PAMALS/app.py principal.
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from home_hero import render_hero

PAGINAS_OCULTAS = {"Fechamento Mensal"}

AVISO_TRANSPARENCIA = (
    "As informações aqui buscam melhorar a transparência junto à empresa — "
    "não substituem as informações oficiais passadas pelo fiscal do "
    "contrato. Podem existir ajustes manuais ou pontos ainda em tratativa. "
    "Os dados são atualizados automaticamente. Em caso de dúvidas, entre em "
    "contato com o fiscal do contrato."
)

st.set_page_config(page_title="005CELOG2025", page_icon="🛡️", layout="wide")


def _estilo_tela_inicial():
    st.markdown(
        """
        <style>
            #MainMenu {display: none;}
            footer {display: none;}
            header {display: none;}
            [data-testid="stToolbar"] {display: none;}
            .stApp { background: #0B1118; color: #F3F6F9; }
            .block-container { max-width: 100% !important; padding: 2.2rem 2.5rem 2.5rem; }
            .cel-titulo {
                text-align: center; font-size: 28px; font-weight: 900;
                letter-spacing: 2px; color: #F3F6F9; margin-bottom: 6px;
            }
            .cel-sub {
                text-align: center; color: #A6B2C1; font-size: 14.5px; margin-bottom: 26px;
            }
            .cel-aviso {
                background: rgba(244,166,42,0.06); border: 1px solid rgba(244,166,42,0.3);
                border-radius: 14px; padding: 1.3rem 1.6rem; color: #D7DEE5;
                font-size: 14.5px; line-height: 1.7; max-width: 640px; margin: 0 auto;
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
        """,
        unsafe_allow_html=True,
    )


def _tela_inicial():
    _estilo_tela_inicial()
    st.markdown(
        """
        <div class="cel-titulo">005CELOG2025</div>
        <div class="cel-sub">Contrato 005/CELOG-PAMALS/2025 — acompanhamento do contrato</div>
        """,
        unsafe_allow_html=True,
    )
    render_hero()
    _, col, _ = st.columns([3, 1, 3])
    with col:
        if st.button("Entrar →", key="cel_entrar"):
            st.session_state["entrou"] = True
            st.rerun()


def _tela_aviso():
    _estilo_tela_inicial()
    st.markdown('<div class="cel-titulo">Antes de continuar</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cel-aviso">{AVISO_TRANSPARENCIA}</div>', unsafe_allow_html=True)
    _, col, _ = st.columns([3, 1, 3])
    with col:
        if st.button("Concordar e continuar →", key="cel_concordar"):
            st.session_state["concordou"] = True
            st.rerun()


if "entrou" not in st.session_state:
    st.session_state["entrou"] = False
if "concordou" not in st.session_state:
    st.session_state["concordou"] = False

if not st.session_state["entrou"]:
    _tela_inicial()
    st.stop()

if not st.session_state["concordou"]:
    _tela_aviso()
    st.stop()

render(paginas_ocultas=PAGINAS_OCULTAS)
