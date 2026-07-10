"""
Hero animado da tela inicial — hangar/plataforma de manutenção com o C-98A,
pedido pelo Wallace em 2026-07-09 ("experiência premium, cinematográfica,
estilo Embraer/Airbus/Lockheed").

Renderizado via `st.iframe` com HTML direto (não `st.markdown`) — precisa de
CSS keyframes rodando de forma isolada, sem conflitar com o CSS do resto do
app Streamlit.

## Sobre a foto e a rotação 360°

A imagem (`imagens/hero_hangar.jpg`, recortada de
`imagens/ChatGPT Image 9 de jul. de 2026, 22_53_20.png`) é uma foto/render
ÚNICA, com o avião e o hangar já "assados" juntos no mesmo plano — não é um
recorte isolado do avião com fundo transparente. Isso muda o que é
tecnicamente honesto fazer:

- **Girar só o avião em 3D de verdade não é possível** sem separar o avião
  do fundo (precisaria de uma versão com fundo transparente/recorte, que
  não existe ainda) — tentar mesmo assim giraria um retângulo com pedaço de
  hangar dentro dele flutuando sobre o hangar parado atrás, o que fica
  visivelmente quebrado, não "premium".
- **Girar a cena inteira em 3D também não funciona** — o hangar giraria
  junto, parecendo um cenário de teatro girando, não um avião numa
  plataforma.

Solução aplicada — o que dá pra fazer de verdade com uma foto só, sem
quebrar visualmente: a foto fica fixa como pano de fundo fotográfico, com
um zoom/pan bem lento (efeito "Ken Burns", como documentários/vitrines de
produto usam) pra dar sensação de câmera viva, e tudo que PODE girar de
verdade gira: os anéis de luz âmbar (desenhados em CSS, sobrepostos ao
anel já existente na foto), partículas de poeira flutuando, e um leve
brilho pulsante na hélice (já visível na foto) simulando giro.

Se o Wallace mandar uma versão do avião com fundo transparente (recorte
isolado, sem o hangar junto), aí sim dá pra fazer a rotação 3D de verdade —
o rig pra isso (`transform-style: preserve-3d` + `rotateY` + verso
espelhado) fica documentado aqui embaixo, comentado, pronto pra ligar.
"""

import base64
import random
from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parent
IMAGEM_HERO_PATH = RAIZ / "imagens" / "hero_hangar.jpg"

# Posição aproximada do centro da hélice na foto (% da largura/altura da
# CENA, não da imagem original) — calibrado visualmente pra hero_hangar.jpg.
HELICE_X_PCT = 68.4
HELICE_Y_PCT = 56


def _imagem_base64(caminho):
    dados = Path(caminho).read_bytes()
    ext = Path(caminho).suffix.lstrip(".").lower()
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    return f"data:image/{mime};base64,{base64.b64encode(dados).decode('ascii')}"


def _particulas_html(qtd=22):
    divs = []
    for _ in range(qtd):
        esquerda = random.uniform(2, 96)
        cima = random.uniform(6, 90)
        duracao = random.uniform(14, 28)
        atraso = random.uniform(0, 20)
        tamanho = random.uniform(1.3, 3.0)
        opacidade = random.uniform(0.15, 0.4)
        divs.append(
            f'<div class="particula" style="left:{esquerda:.1f}%; top:{cima:.1f}%; '
            f'width:{tamanho:.1f}px; height:{tamanho:.1f}px; opacity:{opacidade:.2f}; '
            f'animation-duration:{duracao:.1f}s; animation-delay:-{atraso:.1f}s;"></div>'
        )
    return "".join(divs)


def render_hero(altura=440):
    if not IMAGEM_HERO_PATH.exists():
        st.info("Imagem do hero não encontrada em imagens/hero_hangar.jpg.")
        return

    fundo = _imagem_base64(IMAGEM_HERO_PATH)
    html = f"""
    <!doctype html>
    <html>
    <head>
    <meta charset="utf-8" />
    <style>
        * {{ box-sizing: border-box; }}
        html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; background: transparent; overflow: hidden; }}

        .cena {{
            position: relative; width: 100%; height: {altura}px;
            border-radius: 20px; overflow: hidden;
            background: #05070a;
            animation: fade-in 1.1s ease-out;
        }}
        @keyframes fade-in {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}

        .foto {{
            position: absolute; inset: 0;
            background-image: url('{fundo}');
            background-size: cover; background-position: center;
            image-rendering: -webkit-optimize-contrast;
            animation: kenburns 55s ease-in-out infinite alternate;
        }}
        /* Zoom bem discreto — a foto tem 1536px de largura, quase igual à
           largura máxima do container (1440px); um zoom exagerado ampliaria
           além da resolução real da imagem e ficaria com aparência borrada. */
        @keyframes kenburns {{
            0%   {{ transform: scale(1.0) translate(0, 0); }}
            100% {{ transform: scale(1.025) translate(-0.5%, -0.4%); }}
        }}

        .vinheta {{
            position: absolute; inset: 0;
            background:
                radial-gradient(ellipse 90% 70% at 50% 40%, transparent 55%, rgba(5,7,10,0.55) 100%),
                linear-gradient(180deg, rgba(5,7,10,0.12) 0%, transparent 18%, transparent 78%, rgba(5,7,10,0.35) 100%),
                linear-gradient(90deg, rgba(5,7,10,0.85) 0%, transparent 7%, transparent 93%, rgba(5,7,10,0.85) 100%);
            pointer-events: none;
        }}

        /* --- Anéis de luz sobrepostos ao anel já pintado na foto --- */
        .plataforma-wrap {{
            position: absolute; left: 60%; bottom: 2%; transform: translateX(-50%);
            width: 46%; aspect-ratio: 640 / 130; pointer-events: none;
        }}
        .anel {{
            position: absolute; left: 50%; top: 50%; border-radius: 50%;
            border: 1px solid rgba(244,166,42,0.38);
            box-shadow: 0 0 16px rgba(244,166,42,0.16);
        }}
        .anel-1 {{ width: 96%; height: 96%; margin-left: -48%; margin-top: -48%;
                   transform: perspective(600px) rotateX(74deg) rotate(0deg);
                   animation: girar-anel 42s linear infinite; }}
        .anel-2 {{ width: 66%; height: 66%; margin-left: -33%; margin-top: -33%;
                   border-color: rgba(93,199,209,0.20);
                   transform: perspective(600px) rotateX(74deg) rotate(0deg);
                   animation: girar-anel-inverso 60s linear infinite; }}
        @keyframes girar-anel {{ from {{ transform: perspective(600px) rotateX(74deg) rotate(0deg); }}
                                  to   {{ transform: perspective(600px) rotateX(74deg) rotate(360deg); }} }}
        @keyframes girar-anel-inverso {{ from {{ transform: perspective(600px) rotateX(74deg) rotate(360deg); }}
                                           to   {{ transform: perspective(600px) rotateX(74deg) rotate(0deg); }} }}

        /* --- Brilho pulsante sobre a hélice já existente na foto --- */
        .helice-glow {{
            position: absolute; left: {HELICE_X_PCT}%; top: {HELICE_Y_PCT}%;
            width: 5.5%; aspect-ratio: 1; transform: translate(-50%, -50%);
            border-radius: 50%;
            background: radial-gradient(circle, rgba(244,166,42,0.5), rgba(244,166,42,0) 70%);
            filter: blur(2px);
            animation: helice-pulso 1.1s ease-in-out infinite;
            pointer-events: none;
        }}
        @keyframes helice-pulso {{ 0%, 100% {{ opacity: 0.35; }} 50% {{ opacity: 0.8; }} }}

        /* --- Partículas de poeira --- */
        .particula {{
            position: absolute; border-radius: 50%;
            background: radial-gradient(circle, rgba(244,166,42,0.9), rgba(244,166,42,0));
            animation-name: flutuar; animation-timing-function: ease-in-out; animation-iteration-count: infinite;
            pointer-events: none;
        }}
        @keyframes flutuar {{
            0%   {{ transform: translate(0, 0); }}
            50%  {{ transform: translate(6px, -16px); }}
            100% {{ transform: translate(0, 0); }}
        }}
    </style>
    </head>
    <body>
        <div class="cena">
            <div class="foto"></div>
            <div class="plataforma-wrap">
                <div class="anel anel-1"></div>
                <div class="anel anel-2"></div>
            </div>
            <div class="helice-glow"></div>
            {_particulas_html()}
            <div class="vinheta"></div>
        </div>
    </body>
    </html>
    """
    st.iframe(html, height=altura, width="stretch")


# ---------------------------------------------------------------------------
# Rig de rotação 3D real (documentado, não usado hoje) — ligar quando existir
# uma foto do avião ISOLADO, com fundo transparente:
#
#   .aviao-perspectiva { perspective: 1800px; }
#   .aviao-rotor { transform-style: preserve-3d; animation: girar 46s linear infinite; }
#   @keyframes girar { from { transform: rotateY(0deg); } to { transform: rotateY(360deg); } }
#   .aviao-face { position:absolute; inset:0; backface-visibility: hidden; }
#   .aviao-face.verso { transform: rotateY(180deg) scaleX(-1); }  /* mesma foto espelhada */
#
# O hangar continua como fundo fixo (não gira); só o recorte do avião entra
# nesse rig, sobre a plataforma.
# ---------------------------------------------------------------------------
