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

Precisa de secrets PRÓPRIOS neste deploy (Streamlit Cloud → Settings →
Secrets deste app, separado do site principal):
- `site_password_005celog2025` — senha de acesso desta área.
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
# atualizar_drive.py e pelos botões de Apresentação/Ata) mesmo rodando este
# app isolado, sem o C-98A PAMALS/app.py principal.
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

st.set_page_config(page_title="005CELOG2025", page_icon="🛡️", layout="wide")


def _tela_login():
    st.markdown(
        """
        <style>
            #MainMenu {display: none;}
            footer {display: none;}
            header {display: none;}
            [data-testid="stToolbar"] {display: none;}
            .stApp {
                background:
                    radial-gradient(circle at 8% 20%, rgba(245, 158, 11, 0.16), transparent 28%),
                    radial-gradient(circle at 93% 88%, rgba(245, 158, 11, 0.18), transparent 26%),
                    radial-gradient(circle at 50% 0%, rgba(30, 41, 59, 0.9), transparent 34%),
                    linear-gradient(135deg, #05070b 0%, #0b1117 42%, #111827 100%);
                color: #f9fafb;
            }
            .login-titulo { text-align: center; font-size: 26px; font-weight: 900; letter-spacing: 2px; margin-top: 14vh; }
            .login-sub { text-align: center; color: #9ca3af; font-size: 14px; margin-bottom: 24px; }
            div.stButton > button {
                width: 100%;
                border-radius: 14px;
                border: 1px solid rgba(245, 158, 11, 0.75);
                background: rgba(15, 23, 42, 0.7);
                color: #f59e0b;
                font-weight: 800;
            }
            div.stButton > button:hover {
                background: #f59e0b;
                color: #111827;
                border: 1px solid #f59e0b;
            }
        </style>
        <div class="login-titulo">005CELOG2025</div>
        <div class="login-sub">Acesso restrito — digite a senha pra continuar.</div>
        """,
        unsafe_allow_html=True,
    )
    _, col, _ = st.columns([1, 1, 1])
    with col:
        senha = st.text_input("Senha", type="password", key="login_senha", label_visibility="collapsed",
                               placeholder="Senha de acesso")
        if st.button("Entrar", key="login_botao"):
            if senha == st.secrets.get("site_password_005celog2025"):
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Senha incorreta.")


if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    _tela_login()
    st.stop()

render()
