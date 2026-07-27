"""Fábrica de "verificação ao vivo" — generaliza o mecanismo criado em
2026-07-23 pra Disponibilidade Diária (ver
Coordenadoria/00_Instrucoes/disponibilidade_diaria.md) pra QUALQUER fonte
que já tenha uma função `atualizar_do_drive()`.

Motivo (2026-07-27, Wallace: "nada roda automatico ja descobri, ruim demais
ne"): GitHub Actions (agendamento gratuito, best-effort, pode pular
horários) e o `launchd` do Mac (trava de vez em quando com erro de
configuração, precisa ser recarregado manualmente) já se mostraram os 2
não confiáveis o bastante sozinhos, repetidas vezes, mesmo depois de várias
correções pontuais. Em vez de continuar caçando cada falha isolada, cada
fonte que tem `atualizar_do_drive()` passa a se verificar sozinha sempre
que o site é aberto — o usuário nem precisa saber que a automação externa
falhou, porque o próprio acesso ao site já corrige.

Cada fonte usa `criar_verificador(...)` pra gerar uma função cacheada (30min
por padrão, compartilhada entre todo mundo que acessar — pra não bater no
Drive a cada clique) chamada no `render()` de cada `<area>_app.py`, ANTES
de `carregar_tudo()` — assim o dado já sai fresco na primeira renderização,
sem precisar de `st.rerun()`."""

import streamlit as st

from shared import horario


def _rodar(atualizar_fn, dia_util_only):
    agora = horario.agora_br()
    if dia_util_only and agora.weekday() >= 5:
        return {"tentou": False, "motivo": "fim de semana", "verificado_em": agora}
    try:
        resultado = atualizar_fn()
        return {"tentou": True, "resultado": resultado, "verificado_em": agora}
    except Exception as e:
        return {"tentou": True, "erro": str(e), "verificado_em": agora}


def criar_verificador(nome_fonte, atualizar_fn, dia_util_only=True, ttl=1800):
    """Devolve uma função `st.cache_data`-cacheada que garante `nome_fonte`
    atualizada, buscando no Drive na hora se necessário (uma vez a cada
    `ttl` segundos, compartilhado entre sessões). Nunca deixa a página
    quebrar por causa disso — qualquer erro só fica guardado no dict
    devolvido, pra quem chamar decidir se mostra aviso."""

    @st.cache_data(ttl=ttl, show_spinner=f"Verificando {nome_fonte} no Drive...")
    def _verificador():
        return _rodar(atualizar_fn, dia_util_only)

    return _verificador
