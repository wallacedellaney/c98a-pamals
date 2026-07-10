"""
Página principal "C-98A PAMA-LS" — ponto de entrada único que dá acesso às áreas:

* Coordenadoria (em desenvolvimento)
* Contrato 005/CELOG/2025 (dashboard completo, em Contrato 005/Dashboard/03_Dashboard/)

Navegação por st.session_state + st.button (não por query param — a versão com
`<a href="?page=...">` causou problema e foi revertida).

Identidade visual "Torre de Controle" — ver
"Contrato 005/Dashboard/00_Instrucoes/00_BRAND/identidade_visual.md".
"""

import sys
from pathlib import Path

import streamlit as st

from home_hero import render_hero

RAIZ = Path(__file__).resolve().parent
CONTRATO_005_DASHBOARD = RAIZ / "Contrato 005" / "Dashboard" / "03_Dashboard"
COORDENADORIA_DASHBOARD = RAIZ / "Coordenadoria" / "03_Dashboard"
PROJETOS_DASHBOARD = RAIZ / "Projetos" / "03_Dashboard"

# Permite `from shared import drive_sync, estado` a partir das duas áreas.
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

st.set_page_config(
    page_title="C-98A PAMA-LS",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


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
        <div class="login-titulo">C-98A PAMA-LS</div>
        <div class="login-sub">Acesso restrito — digite a senha pra continuar.</div>
        """,
        unsafe_allow_html=True,
    )
    _, col, _ = st.columns([1, 1, 1])
    with col:
        senha = st.text_input("Senha", type="password", key="login_senha", label_visibility="collapsed",
                               placeholder="Senha de acesso")
        if st.button("Entrar", key="login_botao"):
            if senha == st.secrets.get("site_password"):
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Senha incorreta.")


if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    _tela_login()
    st.stop()

if "area" not in st.session_state:
    st.session_state["area"] = None


def _voltar_ao_menu():
    st.session_state["area"] = None


def _aplicar_css_home():
    st.markdown("""
    <style>
        /* Remove aparência padrão desnecessária do Streamlit (display:none tira
           o elemento do fluxo — visibility:hidden deixaria o espaço vazio reservado). */
        #MainMenu {display: none;}
        footer {display: none;}
        header {display: none;}
        [data-testid="stToolbar"] {display: none;}
        [data-testid="stDecoration"] {display: none;}
        [data-testid="stAppViewContainer"] {padding-top: 0 !important;}
        [data-testid="stAppViewBlockContainer"] {padding-top: 1.1rem !important;}

        .stApp { background: #0B1118; color: #F3F6F9; }

        .block-container { max-width: 1440px; padding-bottom: 2.2rem; }

        .topbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding: 12px 18px;
            background: rgba(20,25,35,0.55);
            border: 1px solid rgba(244,166,42,0.16);
            border-radius: 14px;
        }

        .brand-left {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 16px;
            font-weight: 800;
            letter-spacing: 0.2px;
            color: #F3F6F9;
        }

        .brand-mark {
            width: 32px; height: 32px; border-radius: 50%;
            background: rgba(244,166,42,0.12); border: 1px solid rgba(244,166,42,0.4);
            display: flex; align-items: center; justify-content: center;
            color: #F4A62A;
        }

        .top-pill {
            padding: 6px 13px;
            border-radius: 999px;
            background: rgba(244,166,42,0.08);
            border: 1px solid rgba(244,166,42,0.22);
            color: #F6C66C;
            font-size: 12.5px;
            font-weight: 700;
            margin-left: 10px;
        }

        .top-right { display: flex; align-items: center; gap: 14px; color: #A6B2C1; font-size: 13px; }

        .top-online {
            display: inline-flex; align-items: center; gap: 6px;
            color: #3DBB83; font-weight: 700; font-size: 13px;
        }
        .top-online .ponto {
            width: 8px; height: 8px; border-radius: 50%; background: #3DBB83;
            box-shadow: 0 0 0 0 rgba(61,187,131,0.6);
            animation: pulsar 1.8s ease-out infinite;
        }
        @keyframes pulsar {
            0%   { box-shadow: 0 0 0 0 rgba(61,187,131,0.55); }
            70%  { box-shadow: 0 0 0 7px rgba(61,187,131,0); }
            100% { box-shadow: 0 0 0 0 rgba(61,187,131,0); }
        }

        .hero-wrap {
            margin-bottom: 26px; border-radius: 20px; overflow: hidden;
            border: 1px solid rgba(244,166,42,0.16);
            box-shadow: 0 30px 70px rgba(0,0,0,0.45);
            animation: subir 0.9s ease-out;
        }
        @keyframes subir { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

        .cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 26px;
            align-items: stretch;
        }

        .portal-card {
            border-radius: 18px;
            padding: 26px 26px 22px 26px;
            background: rgba(20,25,35,0.70);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            border: 1px solid rgba(244,166,42,0.22);
            box-shadow: 0 20px 46px rgba(0,0,0,0.30);
            display: flex; flex-direction: column;
            height: 100%;
            transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
            animation: subir 0.9s ease-out;
        }
        .portal-card:hover {
            transform: translateY(-4px);
            border-color: rgba(244,166,42,0.55);
            box-shadow: 0 26px 60px rgba(0,0,0,0.4), 0 0 0 1px rgba(244,166,42,0.12), 0 0 30px rgba(244,166,42,0.10);
        }

        .card-icone {
            width: 44px; height: 44px; border-radius: 50%;
            background: rgba(244,166,42,0.12); border: 1px solid rgba(244,166,42,0.35);
            display: flex; align-items: center; justify-content: center;
            color: #F4A62A; margin-bottom: 14px;
        }

        .card-title {
            color: #F3F6F9;
            font-size: 20px;
            line-height: 1.2;
            font-weight: 800;
            margin-bottom: 10px;
        }

        .card-title.gold { color: #F4A62A; }

        .card-description {
            color: #A6B2C1;
            font-size: 14.5px;
            line-height: 1.6;
            margin-bottom: 16px;
            flex-grow: 1;
        }

        .card-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 18px;
        }

        .tag {
            padding: 5px 11px;
            border-radius: 999px;
            background: rgba(244,166,42,0.08);
            border: 1px solid rgba(244,166,42,0.22);
            color: #F6C66C;
            font-size: 11.5px;
            font-weight: 700;
        }

        div.stButton > button {
            width: 100%;
            height: 48px;
            border-radius: 11px;
            border: 1px solid rgba(244,166,42,0.55);
            background: rgba(244,166,42,0.06);
            color: #F4A62A;
            font-size: 14.5px;
            font-weight: 750;
            transition: all 250ms ease;
        }

        div.stButton > button:hover {
            background: #F4A62A;
            color: #0B1118;
            border-color: #F4A62A;
            box-shadow: 0 0 26px rgba(244,166,42,0.35);
            transform: translateY(-1px);
        }

        .footer-home {
            text-align: center;
            max-width: 820px;
            margin: 6px auto 0 auto;
            color: #718096;
            font-size: 12.5px;
            line-height: 1.7;
        }

        @media (max-width: 900px) {
            .cards-grid { grid-template-columns: 1fr; }
        }
    </style>
    """, unsafe_allow_html=True)


_ICONE_AVIAO = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                '<line x1="22" y1="2" x2="11" y2="13"></line>'
                '<polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>')
_ICONE_PESSOAS = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                  'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                  '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
                  '<path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>')
_ICONE_DOCUMENTO = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                    '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
                    '<polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/>'
                    '<line x1="16" y1="17" x2="8" y2="17"/></svg>')
_ICONE_PASTA = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>')


def _menu_principal():
    _aplicar_css_home()

    st.markdown(
        f'<div class="topbar">'
        f'<div class="brand-left"><div class="brand-mark">{_ICONE_AVIAO}</div>'
        f'<div>C-98A PAMA-LS</div>'
        f'<div class="top-pill">Ambiente Streamlit</div></div>'
        f'<div class="top-right">Sistema interno de apoio à gestão'
        f'<span class="top-online"><span class="ponto"></span>Online</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="hero-wrap">', unsafe_allow_html=True)
    render_hero()
    st.markdown('</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3, gap="medium")

    with col1:
        st.markdown(
            f'<div class="portal-card"><div class="card-icone">{_ICONE_PESSOAS}</div>'
            '<div class="card-title">Coordenadoria</div>'
            '<div class="card-description">Painel de gestão da coordenação operacional, '
            'acompanhamento de demandas, comunicação institucional, disponibilidade, '
            'inspeções, panes, DPE e DPI.</div>'
            '<div class="card-meta"><div class="tag">Operacional</div><div class="tag">Demandas</div>'
            '<div class="tag">Disponibilidade</div></div>'
            '</div>',
            unsafe_allow_html=True,
        )
        if st.button("Acessar Coordenadoria  →", key="btn_coordenadoria", width="stretch"):
            st.session_state["area"] = "coordenadoria"
            st.rerun()

    with col2:
        st.markdown(
            f'<div class="portal-card"><div class="card-icone">{_ICONE_DOCUMENTO}</div>'
            '<div class="card-title gold">Contrato 005/CELOG/2025</div>'
            '<div class="card-description">Gestão contratual, execução financeira, pagamentos, '
            'notas fiscais, emergências, reparáveis, recibos, pendências e indicadores de desempenho.</div>'
            '<div class="card-meta"><div class="tag">Pagamentos</div><div class="tag">Notas fiscais</div>'
            '<div class="tag">Emergências</div></div>'
            '</div>',
            unsafe_allow_html=True,
        )
        if st.button("Acessar Contrato 005/CELOG/2025  →", key="btn_contrato", width="stretch"):
            st.session_state["area"] = "contrato"
            st.rerun()

    with col3:
        st.markdown(
            f'<div class="portal-card"><div class="card-icone">{_ICONE_PASTA}</div>'
            '<div class="card-title">Acompanhamento de Projetos</div>'
            '<div class="card-description">Solicitações do MTA junto à DIRMAB e requisições de '
            'compra do TPJL (CABW/EUA) — acompanhamento próprio para os projetos C-98.</div>'
            '<div class="card-meta"><div class="tag">MTA</div><div class="tag">TPJL</div>'
            '<div class="tag">CABW</div></div>'
            '</div>',
            unsafe_allow_html=True,
        )
        if st.button("Acessar Acompanhamento de Projetos  →", key="btn_projetos", width="stretch"):
            st.session_state["area"] = "projetos"
            st.rerun()

    st.markdown(
        '<div class="footer-home">Acompanhamento centralizado da frota C-98 — RAC, disponibilidade diária, '
        'vencimentos e diagonal de manutenção (Coordenadoria); emergências, reparáveis, empréstimos, '
        'pagamentos e fechamento mensal (Contrato 005/CELOG/2025); solicitações MTA e requisições '
        'TPJL/CABW (Acompanhamento de Projetos).</div>',
        unsafe_allow_html=True,
    )


def _area_coordenadoria():
    if str(COORDENADORIA_DASHBOARD) not in sys.path:
        sys.path.insert(0, str(COORDENADORIA_DASHBOARD))
    from coordenadoria_app import render
    render(ao_voltar=_voltar_ao_menu)


def _area_contrato():
    if str(CONTRATO_005_DASHBOARD) not in sys.path:
        sys.path.insert(0, str(CONTRATO_005_DASHBOARD))
    from contrato_app import render
    render(ao_voltar=_voltar_ao_menu)


def _area_projetos():
    if str(PROJETOS_DASHBOARD) not in sys.path:
        sys.path.insert(0, str(PROJETOS_DASHBOARD))
    from projetos_app import render
    render(ao_voltar=_voltar_ao_menu)


if st.session_state["area"] is None:
    _menu_principal()
elif st.session_state["area"] == "coordenadoria":
    _area_coordenadoria()
elif st.session_state["area"] == "contrato":
    _area_contrato()
elif st.session_state["area"] == "projetos":
    _area_projetos()
