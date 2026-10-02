"""Página Rotina — checklist dos itens que ainda dependem de ação manual
todo mês (não entram no agendamento automático de 2 em 2h). Ver
00_Instrucoes/atualizacoes.md, seção "Limitação conhecida — Vencimentos por
Operador e Diagonal de Manutenção".

Vencimentos por Operador é o único item com checagem automática de verdade
(compara mes_fonte de cada operador, já carregado em dados["venc_operadores"],
contra o mês atual). Os outros ficam como lembrete manual porque a fonte não
guarda essa informação (Diagonal) ou porque são ações, não dados pra checar
(Apresentação RMA, Ata, Orçamentos).
"""

from datetime import datetime

import streamlit as st

from coordenadoria.components.paleta import SECONDARY

OPERADORES_ESPERADOS = ["BAMN", "BABE", "CLA", "BANT", "BABR", "PAMA-LS", "DACTA II", "BACO", "BACG"]


def _mes_atual_str():
    agora = datetime.now()
    return f"{agora.year}-{agora.month:02d}"


def _cartao(titulo, status, detalhe):
    borda = {"ok": "borda-ok", "atencao": "borda-atencao", "critica": "borda-critica"}[status]
    emoji = {"ok": "✅", "atencao": "⚠️", "critica": "🔴"}[status]
    st.markdown(
        f'''<div class="coord-card {borda}">
<b>{emoji} {titulo}</b>
<div style="margin-top:0.4rem; color:{SECONDARY}; font-size:0.85rem;">{detalhe}</div>
</div>''',
        unsafe_allow_html=True,
    )


def render(dados):
    st.title("Rotina — Checklist Mensal")
    st.caption(
        "Itens que ainda dependem de ação manual todo mês. O resto (RAC, Disponibilidade "
        "Diária, Vencimentos TMOT, Motores etc.) já roda sozinho — ver 00_Instrucoes/atualizacoes.md."
    )

    mes_atual = _mes_atual_str()

    st.subheader("Vencimentos por Operador")
    venc_operadores = dados.get("venc_operadores")
    if venc_operadores is None or venc_operadores.empty or "mes_fonte" not in venc_operadores.columns:
        _cartao("Vencimentos por Operador", "critica", "Nenhum dado carregado ainda.")
    else:
        mes_por_operador = venc_operadores.groupby("operador")["mes_fonte"].first()
        atrasados = []
        for op in OPERADORES_ESPERADOS:
            mes_fonte = mes_por_operador.get(op)
            if mes_fonte is None:
                atrasados.append(f"{op} (sem dado)")
            elif str(mes_fonte) != mes_atual:
                atrasados.append(f"{op} ({mes_fonte})")
        if not atrasados:
            _cartao("Vencimentos por Operador", "ok", f"Todos os 9 operadores com arquivo de {mes_atual}.")
        else:
            _cartao(
                "Vencimentos por Operador", "atencao",
                f"Atrás do mês atual ({mes_atual}): " + ", ".join(atrasados) +
                ". Pedir arquivo novo na pasta MAPEM/DIAGONAL/VENCIMENTOS do Drive.",
            )

    st.subheader("Diagonal de Manutenção")
    _cartao(
        "Diagonal de Manutenção", "atencao",
        "Sem checagem automática de mês (a fonte não guarda o mês de origem por linha). "
        "Confira manualmente os nomes dos arquivos em 01_Bases_Originais/Diagonal_Manutencao "
        "contra o mês atual, mesma pasta do Drive dos Vencimentos.",
    )

    st.subheader("Fechamento Mensal (Contrato 005)")
    _cartao(
        "Reparáveis — RMA da empresa", "atencao",
        "Confirme que o arquivo \"RMA em andamento {Mês}.xlsx\" / \"Pré RMA C-98 {Mês}-26.xlsx\" "
        "já está na pasta do mês no Drive — sem ele o cruzamento de reparáveis não tem o que achar.",
    )
    _cartao(
        "Financeiro (RMA)", "atencao",
        "Depende do mesmo arquivo \"Pré RMA C-98 {Mês}-26.xlsx\" no Drive — usado pelo botão "
        "\"Buscar valores financeiros no Drive\" em Fechamento Mensal.",
    )
    _cartao(
        "Apresentação (RMA)", "atencao",
        "Gerar o PowerPoint todo mês em Fechamento Mensal > Apresentação (RMA), depois revisar antes de enviar.",
    )
    _cartao(
        "Ata de Reunião", "atencao",
        "Colar a transcrição da reunião no Drive antes de gerar (senão cai no fallback de "
        "transcrição por áudio). Revisar as seções marcadas \"[revisar a partir da transcrição]\" antes de assinar.",
    )

    st.subheader("Orçamentos")
    _cartao(
        "Orçamentos solicitados", "atencao",
        "Conferir os orçamentos pendentes no Drive e as compras fechadas por e-mail.",
    )
