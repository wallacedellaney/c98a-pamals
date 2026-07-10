"""Selo de status + botão "Atualizar X", compacto (não uma caixa grande —
pedido do Wallace em 2026-07-09). Ver 00_Instrucoes/atualizacoes.md (raiz)."""

from datetime import datetime

import streamlit as st

from projetos.components.paleta import selo

LABEL_STATUS = {"atualizado": "Atualizado", "erro": "Erro", "pendente": "Pendente"}
COR_STATUS = {"atualizado": "good", "erro": "critical", "pendente": "neutro"}


def _formatar(timestamp_iso):
    if not timestamp_iso:
        return None
    try:
        texto = timestamp_iso.replace("Z", "+00:00")
        return datetime.fromisoformat(texto).strftime("%d/%m/%Y às %H:%M")
    except ValueError:
        return timestamp_iso


def status_atualizacao_html(estado_atual):
    """HTML (string) do selo + texto de última atualização/registros — pra
    embutir dentro do cabeçalho da página (cabecalho_pagina), sem caixa
    própria."""
    status = estado_atual.get("status", "pendente")
    partes = [selo(LABEL_STATUS.get(status, status), COR_STATUS.get(status, "neutro"))]

    atualizado = _formatar(estado_atual.get("local_updated_at"))
    if atualizado:
        partes.append(f"Atualizado em {atualizado}")
    if estado_atual.get("record_count") is not None:
        partes.append(f"{estado_atual['record_count']} registro(s) válido(s)")

    linha = " · ".join(partes)
    erro_html = ""
    if estado_atual.get("last_error"):
        erro_html = f'<div style="margin-top:4px;">{selo("Erro: " + str(estado_atual["last_error"])[:120], "critical")}</div>'
    return f'<div>{linha}</div>{erro_html}'


def botao_atualizar(nome, on_click, key):
    """Botão de atualização — mostra "Atualizando..." durante a chamada e
    trata erro sem deixar HTML solto na tela."""
    if st.button(f"Atualizar {nome}", key=key, width="stretch"):
        with st.spinner(f"Atualizando dados de {nome}..."):
            try:
                on_click()
            except Exception as e:
                st.error(f"Falha ao atualizar {nome}: {e}")
                st.stop()
        st.toast(f"{nome} atualizado.", icon="✅")
        st.rerun()
