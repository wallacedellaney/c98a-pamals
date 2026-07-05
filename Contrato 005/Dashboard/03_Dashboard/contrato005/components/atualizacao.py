"""Card de status + botão "Atualizar X" — mostra última versão encontrada no
Drive, última atualização local, status e erro (se houver). Ver
00_Instrucoes/atualizacoes.md (raiz do projeto) para a arquitetura completa.
"""

from datetime import datetime

import streamlit as st

from contrato005.components.paleta import INK, LINE, PANEL, SECONDARY, STATUS

COR_STATUS = {"atualizado": STATUS["good"], "erro": STATUS["critical"], "pendente": SECONDARY}
LABEL_STATUS = {"atualizado": "Atualizado", "erro": "Erro", "pendente": "Pendente"}


def _formatar(timestamp_iso):
    if not timestamp_iso:
        return "—"
    try:
        texto = timestamp_iso.replace("Z", "+00:00")
        return datetime.fromisoformat(texto).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return timestamp_iso


def card_status_atualizacao(nome, estado_atual, on_click, key):
    """Renderiza nome + badge de status + versão remota + atualização local +
    contagem/erro + botão. `on_click` faz o trabalho (buscar no Drive,
    reprocessar, persistir estado) e pode levantar exceção — o card trata."""
    status = estado_atual.get("status", "pendente")
    cor = COR_STATUS.get(status, SECONDARY)
    label = LABEL_STATUS.get(status, status)

    with st.container():
        st.markdown(
            f"""<div style="background:{PANEL};border:1px solid {LINE};border-radius:10px;
            padding:0.8rem 1rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div style="font-weight:700;color:{INK};">{nome}</div>
                <div style="color:{cor};font-weight:700;font-size:0.85rem;">● {label}</div>
            </div>
            <div style="color:{SECONDARY};font-size:0.82rem;margin-top:0.35rem;">
                Última versão encontrada: {_formatar(estado_atual.get('remote_modified_time'))}<br>
                Atualizado no sistema em: {_formatar(estado_atual.get('local_updated_at'))}
                {f"· {estado_atual['record_count']} registro(s)" if estado_atual.get('record_count') is not None else ""}
            </div>
            {f'<div style="color:{STATUS["critical"]};font-size:0.8rem;margin-top:0.3rem;">{estado_atual["last_error"]}</div>' if estado_atual.get('last_error') else ""}
            </div>""",
            unsafe_allow_html=True,
        )
        if st.button(f"🔄 Atualizar {nome}", key=key, width="stretch"):
            with st.spinner(f"Atualizando {nome}..."):
                try:
                    on_click()
                except Exception as e:
                    st.error(f"Falha ao atualizar {nome}: {e}")
                    st.stop()
            st.toast(f"{nome} atualizado.", icon="✅")
            st.rerun()
