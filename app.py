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

RAIZ = Path(__file__).resolve().parent
CONTRATO_005_DASHBOARD = RAIZ / "Contrato 005" / "Dashboard" / "03_Dashboard"
COORDENADORIA_DASHBOARD = RAIZ / "Coordenadoria" / "03_Dashboard"

# Permite `from shared import drive_sync, estado` a partir das duas áreas.
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

st.set_page_config(
    page_title="C-98A PAMA-LS",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

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
        [data-testid="stAppViewBlockContainer"] {padding-top: 1.2rem !important;}

        .stApp {
            background:
                radial-gradient(circle at 8% 20%, rgba(245, 158, 11, 0.16), transparent 28%),
                radial-gradient(circle at 93% 88%, rgba(245, 158, 11, 0.18), transparent 26%),
                radial-gradient(circle at 50% 0%, rgba(30, 41, 59, 0.9), transparent 34%),
                linear-gradient(135deg, #05070b 0%, #0b1117 42%, #111827 100%);
            color: #f9fafb;
        }

        .block-container {
            max-width: 1320px;
            padding-bottom: 2rem;
        }

        .home-shell {
            position: relative;
        }

        .home-shell::before {
            content: "";
            position: fixed;
            left: -180px;
            top: 260px;
            width: 520px;
            height: 520px;
            border: 1px solid rgba(245, 158, 11, 0.11);
            border-radius: 50%;
            box-shadow:
                0 0 0 45px rgba(245, 158, 11, 0.025),
                0 0 0 95px rgba(245, 158, 11, 0.018),
                0 0 0 150px rgba(245, 158, 11, 0.012);
            pointer-events: none;
        }

        .home-shell::after {
            content: "";
            position: fixed;
            right: -240px;
            top: 95px;
            width: 620px;
            height: 620px;
            border: 1px solid rgba(245, 158, 11, 0.10);
            border-radius: 50%;
            box-shadow:
                0 0 0 52px rgba(245, 158, 11, 0.020),
                0 0 0 105px rgba(245, 158, 11, 0.014),
                0 0 0 165px rgba(245, 158, 11, 0.010);
            pointer-events: none;
        }

        .topbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 58px;
            padding: 4px 2px;
        }

        .brand-left {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 17px;
            font-weight: 850;
            letter-spacing: 0.4px;
            color: #f9fafb;
        }

        .brand-mark {
            width: 32px;
            height: 32px;
            border-radius: 10px;
            border: 1px solid rgba(245, 158, 11, 0.55);
            display: flex;
            align-items: center;
            justify-content: center;
            color: #f59e0b;
            background: rgba(245, 158, 11, 0.08);
            box-shadow: 0 0 22px rgba(245, 158, 11, 0.12);
            font-size: 17px;
        }

        .top-status {
            padding: 10px 16px;
            border-radius: 999px;
            background: rgba(15, 23, 42, 0.62);
            border: 1px solid rgba(148, 163, 184, 0.18);
            color: #9ca3af;
            font-size: 13px;
            letter-spacing: 0.2px;
        }

        .top-status strong {
            color: #f59e0b;
        }

        .hero {
            text-align: center;
            margin-top: 4px;
            margin-bottom: 8px;
        }

        .hero-kicker {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 14px;
            border-radius: 999px;
            background: rgba(245, 158, 11, 0.08);
            border: 1px solid rgba(245, 158, 11, 0.24);
            color: #f6c66c;
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.35px;
            margin-bottom: 22px;
        }

        .hero h1 {
            margin: 0;
            font-size: clamp(42px, 4.8vw, 68px);
            line-height: 1.02;
            font-weight: 950;
            letter-spacing: 3px;
            color: #f9fafb;
            text-shadow: 0 18px 60px rgba(0,0,0,0.55);
        }

        .hero h1 span {
            color: #f59e0b;
            text-shadow: 0 0 36px rgba(245, 158, 11, 0.20);
        }

        .hero h2 {
            margin-top: 14px;
            margin-bottom: 18px;
            color: #9ca3af;
            font-size: clamp(18px, 1.65vw, 24px);
            font-weight: 650;
            letter-spacing: 0.3px;
        }

        .hero p {
            max-width: 815px;
            margin: 0 auto;
            color: #d1d5db;
            font-size: 17px;
            line-height: 1.75;
            font-weight: 430;
        }

        .hero p strong {
            color: #f59e0b;
            font-weight: 850;
        }

        .pills {
            display: flex;
            justify-content: center;
            align-items: stretch;
            flex-wrap: wrap;
            gap: 14px;
            margin: 34px auto 40px auto;
        }

        .pill {
            min-width: 165px;
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 13px 18px;
            border-radius: 999px;
            background:
                linear-gradient(145deg, rgba(15,23,42,0.82), rgba(17,24,39,0.70));
            border: 1px solid rgba(148, 163, 184, 0.16);
            box-shadow:
                0 16px 38px rgba(0,0,0,0.25),
                inset 0 1px 0 rgba(255,255,255,0.04);
            color: #d1d5db;
        }

        .pill-icon {
            width: 28px;
            height: 28px;
            border-radius: 9px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #cbd5e1;
            font-size: 15px;
        }

        .pill-title {
            font-size: 13px;
            color: #cbd5e1;
            line-height: 1.2;
            font-weight: 650;
        }

        .pill-value {
            margin-top: 3px;
            font-size: 13px;
            color: #f59e0b;
            line-height: 1.2;
            font-weight: 850;
        }

        .portal-card {
            min-height: 300px;
            border-radius: 26px;
            padding: 32px 34px 26px 34px;
            position: relative;
            overflow: hidden;
            background:
                linear-gradient(145deg, rgba(31, 41, 55, 0.78), rgba(15, 23, 42, 0.82));
            border: 1px solid rgba(245, 158, 11, 0.30);
            box-shadow:
                0 30px 80px rgba(0,0,0,0.34),
                inset 0 1px 0 rgba(255,255,255,0.055);
            margin-bottom: 18px;
        }

        .portal-card::before {
            content: "";
            position: absolute;
            top: 0;
            left: 14%;
            width: 72%;
            height: 2px;
            background: linear-gradient(90deg, transparent, rgba(245,158,11,0.95), transparent);
            box-shadow: 0 0 22px rgba(245,158,11,0.55);
        }

        .portal-card::after {
            content: "";
            position: absolute;
            right: -70px;
            top: -70px;
            width: 190px;
            height: 190px;
            border-radius: 50%;
            background: rgba(245, 158, 11, 0.06);
            filter: blur(2px);
        }

        .card-head {
            display: flex;
            align-items: flex-start;
            gap: 24px;
            position: relative;
            z-index: 2;
        }

        .card-icon {
            min-width: 88px;
            width: 88px;
            height: 88px;
            border-radius: 999px;
            border: 1px solid rgba(245, 158, 11, 0.72);
            background:
                radial-gradient(circle, rgba(245,158,11,0.16), rgba(245,158,11,0.04));
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 36px;
            color: #f59e0b;
            box-shadow:
                0 0 34px rgba(245,158,11,0.13),
                inset 0 1px 0 rgba(255,255,255,0.06);
        }

        .card-title {
            color: #f9fafb;
            font-size: 27px;
            line-height: 1.18;
            font-weight: 900;
            margin-top: 2px;
            margin-bottom: 12px;
            letter-spacing: 0.1px;
        }

        .card-title.gold {
            color: #f59e0b;
        }

        .card-description {
            color: #cbd5e1;
            font-size: 16px;
            line-height: 1.65;
            margin-bottom: 18px;
        }

        .card-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }

        .tag {
            padding: 6px 10px;
            border-radius: 999px;
            background: rgba(245, 158, 11, 0.075);
            border: 1px solid rgba(245, 158, 11, 0.18);
            color: #f6c66c;
            font-size: 12px;
            font-weight: 700;
        }

        div.stButton > button {
            width: 100%;
            height: 54px;
            border-radius: 14px;
            border: 1px solid rgba(245, 158, 11, 0.75);
            background: rgba(15, 23, 42, 0.7);
            color: #f59e0b;
            font-size: 16px;
            font-weight: 800;
            letter-spacing: 0.2px;
            transition: all 0.18s ease-in-out;
        }

        div.stButton > button:hover {
            background: #f59e0b;
            color: #111827;
            border: 1px solid #f59e0b;
            box-shadow: 0 0 28px rgba(245, 158, 11, 0.26);
        }

        .footer-home {
            text-align: center;
            margin-top: 30px;
            color: #8b95a5;
            font-size: 14px;
            line-height: 1.75;
        }

        .footer-home strong {
            color: #f59e0b;
        }

        @media (max-width: 900px) {
            .hero h1 {
                font-size: 40px;
            }

            .card-head {
                flex-direction: column;
            }
        }
    </style>
    """, unsafe_allow_html=True)


def _menu_principal():
    _aplicar_css_home()

    # HTML em uma linha só, sem indentação: uma linha em branco no meio faz o
    # Markdown do Streamlit sair do "modo HTML" e tratar o resto como texto/código.
    st.markdown(
        '<div class="home-shell">'
        '<div class="topbar">'
        '<div class="brand-left"><div class="brand-mark">🛡️</div><div>C-98A PAMA-LS</div></div>'
        '<div class="top-status">Sistema interno de apoio à gestão • <strong>Ambiente Streamlit</strong></div>'
        '</div>'
        '<section class="hero">'
        '<div class="hero-kicker">✦ Portal gerencial integrado</div>'
        '<h1>C-98A <span>PAMA-LS</span></h1>'
        '<h2>Portal Gerencial de Coordenação e Contrato</h2>'
        '<p>Acompanhamento operacional, controle contratual, pagamentos, emergências, '
        'notas fiscais e indicadores do <strong>Contrato 005/CELOG/2025</strong>.</p>'
        '</section>'
        '<div class="pills">'
        '<div class="pill"><div class="pill-icon">📅</div><div><div class="pill-title">Contrato Ativo</div>'
        '<div class="pill-value">005/CELOG/2025</div></div></div>'
        '<div class="pill"><div class="pill-icon">🛡️</div><div><div class="pill-title">Vigência</div>'
        '<div class="pill-value">2025</div></div></div>'
        '<div class="pill"><div class="pill-icon">👥</div><div><div class="pill-title">Gestão Integrada</div>'
        '<div class="pill-value">Coordenação + Contrato</div></div></div>'
        '<div class="pill"><div class="pill-icon">📊</div><div><div class="pill-title">Indicadores</div>'
        '<div class="pill-value">Tempo real</div></div></div>'
        '<div class="pill"><div class="pill-icon">✅</div><div><div class="pill-title">Conformidade</div>'
        '<div class="pill-value">Governança e Controle</div></div></div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown(
            '<div class="portal-card"><div class="card-head">'
            '<div class="card-icon">👥</div>'
            '<div><div class="card-title">Coordenadoria</div>'
            '<div class="card-description">Painel de gestão da coordenação operacional, '
            'acompanhamento de demandas, comunicação institucional, disponibilidade, '
            'inspeções, panes, DPE e DPI.</div>'
            '<div class="card-meta"><div class="tag">Operacional</div><div class="tag">Demandas</div>'
            '<div class="tag">Disponibilidade</div></div>'
            '</div></div></div>',
            unsafe_allow_html=True,
        )
        if st.button("Acessar Coordenadoria  →", key="btn_coordenadoria", width="stretch"):
            st.session_state["area"] = "coordenadoria"
            st.rerun()

    with col2:
        st.markdown(
            '<div class="portal-card"><div class="card-head">'
            '<div class="card-icon">📄</div>'
            '<div><div class="card-title gold">Contrato 005/CELOG/2025</div>'
            '<div class="card-description">Gestão contratual, execução financeira, pagamentos, '
            'notas fiscais, emergências, reparáveis, recibos, pendências e indicadores de desempenho.</div>'
            '<div class="card-meta"><div class="tag">Pagamentos</div><div class="tag">Notas fiscais</div>'
            '<div class="tag">Emergências</div></div>'
            '</div></div></div>',
            unsafe_allow_html=True,
        )
        if st.button("Acessar Contrato 005/CELOG/2025  →", key="btn_contrato", width="stretch"):
            st.session_state["area"] = "contrato"
            st.rerun()

    st.markdown(
        '<div class="footer-home">🛡️ <strong>Governança</strong> • Transparência • Eficiência • '
        'Responsabilidade<br>Sistema PAMA-LS • Gestão integrada para resultados</div>',
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


if st.session_state["area"] is None:
    _menu_principal()
elif st.session_state["area"] == "coordenadoria":
    _area_coordenadoria()
elif st.session_state["area"] == "contrato":
    _area_contrato()
