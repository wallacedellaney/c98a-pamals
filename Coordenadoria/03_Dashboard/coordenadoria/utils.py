"""Utilidades compartilhadas entre as páginas da Coordenadoria."""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

DASHBOARD_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_GERAR_RAC = DASHBOARD_ROOT / "05_Scripts" / "python" / "extrair_rac.py"
SCRIPT_GERAR_DISPONIBILIDADE = DASHBOARD_ROOT / "05_Scripts" / "python" / "extrair_disponibilidade_diaria.py"
SCRIPT_GERAR_VENCIMENTOS = DASHBOARD_ROOT / "05_Scripts" / "python" / "extrair_vencimentos.py"
SCRIPT_GERAR_VENCIMENTOS_OPERADORES = DASHBOARD_ROOT / "05_Scripts" / "python" / "extrair_vencimentos_operadores.py"
SCRIPT_GERAR_DIAGONAL_MANUTENCAO = DASHBOARD_ROOT / "05_Scripts" / "python" / "extrair_diagonal_manutencao.py"
SCRIPT_GERAR_MOTORES = DASHBOARD_ROOT / "05_Scripts" / "python" / "extrair_motores.py"

RAC_PLANILHA_URL = "https://docs.google.com/spreadsheets/d/1o8supQLcHkC1WZZCZDAtuRKGB_VUlQ8qBlYj7racsGQ/edit"
DISPONIBILIDADE_PASTA_URL = "https://drive.google.com/drive/folders/1JLrUGunWo5ABsR3WuYo88b2WD4QWoxNH"
VENCIMENTOS_PLANILHA_URL = "https://docs.google.com/spreadsheets/d/178vQ-lRP52sw30kQArqcsQGXfj2OLblaFCgjIXWFIl8/edit"

# Sys.path pro Scripts da Coordenadoria — permite `import
# extrair_disponibilidade_diaria` direto, sem subprocesso, dentro de
# garantir_disponibilidade_atualizada() (ver abaixo).
SCRIPTS_PYTHON = DASHBOARD_ROOT / "05_Scripts" / "python"
if str(SCRIPTS_PYTHON) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PYTHON))


@st.cache_data(ttl=1800, show_spinner="Verificando relatório mais recente no Drive...")
def garantir_disponibilidade_atualizada():
    """"Sempre busca o dia de hj e atualiza" (pedido do Wallace em
    2026-07-23) — em vez de esperar o ciclo automático de 2 em 2h (que já se
    mostrou não 100% confiável, ver 00_Instrucoes/atualizacoes.md), checa o
    Drive na hora, se hoje for dia útil e ainda não tiver sido verificado
    nos últimos 30min (`ttl` do cache — compartilhado entre todo mundo que
    usar a Coordenadoria, pra não bater no Drive toda hora).

    Chamada em `coordenadoria_app.py`, ANTES de `carregar_tudo()` — não só
    na página "Disponibilidade Diária" (onde foi criada originalmente).
    Motivo: a Diagonal de Manutenção e o Dashboard Geral também usam
    `disp_aeronaves`/`disp_relatorios` (ex.: "Previsão de situação — próximos
    7 dias"), e ficavam com dado desatualizado sempre que o Wallace abria
    essas páginas sem antes visitar Disponibilidade Diária na mesma sessão
    (bug real visto em 2026-07-23: "nao ta batendo com a disp diaria, tem
    que ir atualizando ne"). Chamando aqui, central, TODA página da
    Coordenadoria se beneficia, e como isso roda antes de `carregar_tudo()`,
    o dado já sai fresco na primeira renderização — sem precisar de
    `st.rerun()`.

    Nunca deixa a página quebrar por causa disso — qualquer erro só fica
    guardado no dict devolvido, pra quem chamar decidir se mostra aviso."""
    agora = datetime.now()
    if agora.weekday() >= 5:
        return {"tentou": False, "motivo": "fim de semana — não sai relatório", "verificado_em": agora}
    try:
        from shared import drive_sync
        import extrair_disponibilidade_diaria as edd
        drive_sync.garantir_credencial_arquivo()
        resultado = edd.atualizar_do_drive()
        return {"tentou": True, "resultado": resultado, "verificado_em": agora}
    except Exception as e:
        return {"tentou": True, "erro": str(e), "verificado_em": agora}


def atualizar_dados_rac():
    """Roda de novo a extração do RAC a partir do que já está em 01_Bases_Originais/
    (não busca nada novo do Google Drive — isso continua manual)."""
    resultado = subprocess.run(
        [sys.executable, str(SCRIPT_GERAR_RAC)],
        cwd=str(SCRIPT_GERAR_RAC.parent),
        capture_output=True,
        text=True,
    )
    st.cache_data.clear()
    if resultado.returncode == 0:
        st.toast("Dados do RAC atualizados.", icon="✅")
    else:
        st.error(f"Erro ao atualizar dados do RAC:\n\n{resultado.stderr or resultado.stdout}")


def atualizar_dados_disponibilidade():
    """Reprocessa os relatórios .txt já salvos em 01_Bases_Originais/Disponibilidade_Diaria/
    (buscar um relatório novo no Drive é feito pelo Claude na conversa, não por aqui)."""
    resultado = subprocess.run(
        [sys.executable, str(SCRIPT_GERAR_DISPONIBILIDADE)],
        cwd=str(SCRIPT_GERAR_DISPONIBILIDADE.parent),
        capture_output=True,
        text=True,
    )
    st.cache_data.clear()
    if resultado.returncode == 0:
        st.toast("Dados de disponibilidade atualizados.", icon="✅")
    else:
        st.error(f"Erro ao atualizar disponibilidade diária:\n\n{resultado.stderr or resultado.stdout}")


def atualizar_dados_vencimentos():
    """Reprocessa a cópia local de 01_Bases_Originais/Vencimentos/ (buscar uma
    versão nova no Drive é feito pelo Claude na conversa, não por aqui)."""
    resultado = subprocess.run(
        [sys.executable, str(SCRIPT_GERAR_VENCIMENTOS)],
        cwd=str(SCRIPT_GERAR_VENCIMENTOS.parent),
        capture_output=True,
        text=True,
    )
    st.cache_data.clear()
    if resultado.returncode == 0:
        st.toast("Dados de vencimentos (TMOT) atualizados.", icon="✅")
    else:
        st.error(f"Erro ao atualizar vencimentos:\n\n{resultado.stderr or resultado.stdout}")


def atualizar_dados_vencimentos_operadores():
    """Reprocessa os arquivos por operador já salvos em
    01_Bases_Originais/Vencimentos/Operadores/ (buscar arquivos novos no
    Drive é feito pelo Claude na conversa, não por aqui)."""
    resultado = subprocess.run(
        [sys.executable, str(SCRIPT_GERAR_VENCIMENTOS_OPERADORES)],
        cwd=str(SCRIPT_GERAR_VENCIMENTOS_OPERADORES.parent),
        capture_output=True,
        text=True,
    )
    st.cache_data.clear()
    if resultado.returncode == 0:
        st.toast("Dados de vencimentos por operador atualizados.", icon="✅")
    else:
        st.error(f"Erro ao atualizar vencimentos por operador:\n\n{resultado.stderr or resultado.stdout}")


def atualizar_dados_diagonal_manutencao():
    """Reprocessa as grades de Diagonal de Manutenção já salvas localmente
    (buscar arquivos novos no Drive é feito pelo Claude na conversa, não por
    aqui)."""
    resultado = subprocess.run(
        [sys.executable, str(SCRIPT_GERAR_DIAGONAL_MANUTENCAO)],
        cwd=str(SCRIPT_GERAR_DIAGONAL_MANUTENCAO.parent),
        capture_output=True,
        text=True,
    )
    st.cache_data.clear()
    if resultado.returncode == 0:
        st.toast("Dados de Diagonal de Manutenção atualizados.", icon="✅")
    else:
        st.error(f"Erro ao atualizar Diagonal de Manutenção:\n\n{resultado.stderr or resultado.stdout}")


def atualizar_dados_motores():
    """Reprocessa a cópia local de 01_Bases_Originais/Motores/ (buscar uma
    versão nova no Drive — planilha pessoal do Wallace, ainda sem
    compartilhamento confirmado com a conta de serviço — é feito pelo Claude
    na conversa, não por aqui)."""
    resultado = subprocess.run(
        [sys.executable, str(SCRIPT_GERAR_MOTORES)],
        cwd=str(SCRIPT_GERAR_MOTORES.parent),
        capture_output=True,
        text=True,
    )
    st.cache_data.clear()
    if resultado.returncode == 0:
        st.toast("Dados de Motores atualizados.", icon="✅")
    else:
        st.error(f"Erro ao atualizar Motores:\n\n{resultado.stderr or resultado.stdout}")
