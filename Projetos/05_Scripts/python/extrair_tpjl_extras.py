"""
Carrega as 3 planilhas da pasta Drive "Planilhas TPLJ" — Consumo, Estoque e
Solicitações — e gera 02_Dados_Tratados/base_tpjl_extras.xlsx (3 abas:
Consumo/Estoque/Solicitacoes). Ver 00_Instrucoes/tpjl.md, seção "Consumo /
Estoque / Solicitações" (pedido do Wallace em 2026-07-14).

As 3 fontes já vêm filtradas em Projeto = "U8" (confirmado 100% na análise
inicial) — filtramos de novo aqui mesmo assim, defensivamente, porque nenhuma
fonte da Coordenadoria/Projetos tem formato garantido estável de um mês pro
outro (mesmo princípio de Coordenadoria/CLAUDE.md).
"""

from datetime import datetime

import pandas as pd

from common import BASES_ORIGINAIS, DADOS_TRATADOS, ESTADO_ATUALIZACOES, registrar_log
from shared import drive_sync, estado

from projetos.config import tpjl_config as cfg

PJT_FILTRO = cfg.PJT_FILTRO

ARQUIVOS_FONTE = {
    "consumo": BASES_ORIGINAIS / "TPJL_Consumo" / "relatorio_consumo.xlsx",
    "estoque": BASES_ORIGINAIS / "TPJL_Estoque" / "relatorio_estoque.xlsx",
    "solicitacoes": BASES_ORIGINAIS / "TPJL_Solicitacoes" / "relatorio_solicitacoes.xlsx",
}

HISTORICO_SOLICITACOES = DADOS_TRATADOS / "historico_tpjl_solicitacoes.csv"
COLUNAS_HISTORICO_SOLICITACOES = [
    "numero_solicitacao", "pn", "categoria", "quantidade", "tipo", "status",
    "solicitante", "data_criacao", "ultima_atualizacao",
]

COLUNAS_CONSUMO = {
    "Part Number": "pn", "CFF": "cff", "Projeto": "projeto", "Descrição": "descricao",
    "Categoria": "categoria", "Mês Competência": "mes", "Ano Competência": "ano",
    "Qtd Consumo": "qtd_consumo",
}
COLUNAS_ESTOQUE = {
    "Part Number": "pn", "CFF": "cff", "Projeto": "projeto", "Descrição": "descricao",
    "Categoria": "categoria", "Qtd em Estoque": "qtd_estoque", "Setor": "setor", "Unidade": "unidade",
}
COLUNAS_SOLICITACOES = {
    "Nº Solicitação": "numero_solicitacao", "Projeto": "projeto", "Part Number": "pn", "CFF": "cff",
    "Nomenclatura": "nomenclatura", "Categoria": "categoria", "Quantidade": "quantidade",
    "Tipo": "tipo", "Status": "status", "Unidade de Estocagem": "unidade_estocagem",
    "Solicitante": "solicitante", "Data de Criação": "data_criacao", "Última Atualização": "ultima_atualizacao",
}


def _filtrar_u8(df, contexto, inconsistencias):
    fora = df[df["projeto"] != PJT_FILTRO]
    if len(fora):
        inconsistencias.append(f"{contexto}: {len(fora)} linha(s) fora de Projeto={PJT_FILTRO} — excluídas.")
    return df[df["projeto"] == PJT_FILTRO].copy()


def _extrair_consumo(inconsistencias):
    config = cfg.FONTES_EXTRAS["consumo"]
    df = pd.read_excel(ARQUIVOS_FONTE["consumo"], sheet_name=config["aba"])
    df = df.rename(columns=COLUNAS_CONSUMO)[list(COLUNAS_CONSUMO.values())]
    df = _filtrar_u8(df, config["planilha"], inconsistencias)

    duplicadas = df.duplicated().sum()
    if duplicadas:
        inconsistencias.append(
            f"{config['planilha']}: {duplicadas} linha(s) completamente duplicada(s) — removidas "
            "(mesma regra de 'só remover se idêntica' já usada no TPJL, ver tpjl.md)."
        )
        df = df.drop_duplicates().reset_index(drop=True)
    return df


def _extrair_estoque(inconsistencias):
    config = cfg.FONTES_EXTRAS["estoque"]
    df = pd.read_excel(ARQUIVOS_FONTE["estoque"], sheet_name=config["aba"])
    df = df.rename(columns=COLUNAS_ESTOQUE)[list(COLUNAS_ESTOQUE.values())]
    df = _filtrar_u8(df, config["planilha"], inconsistencias)
    return df


def _extrair_solicitacoes(inconsistencias):
    config = cfg.FONTES_EXTRAS["solicitacoes"]
    df = pd.read_excel(ARQUIVOS_FONTE["solicitacoes"], sheet_name=config["aba"])
    df = df.rename(columns=COLUNAS_SOLICITACOES)[list(COLUNAS_SOLICITACOES.values())]
    df = _filtrar_u8(df, config["planilha"], inconsistencias)

    for campo in ("data_criacao", "ultima_atualizacao"):
        convertido = pd.to_datetime(df[campo], format="%d/%m/%Y %H:%M", errors="coerce")
        falhas = convertido.isna() & df[campo].notna()
        if falhas.any():
            inconsistencias.append(
                f"{config['planilha']}: {int(falhas.sum())} valor(es) de '{campo}' fora do formato "
                "DD/MM/AAAA HH:MM — mantidos como texto original, não convertidos."
            )
        df[campo] = convertido
    return df


def extrair():
    inconsistencias = []
    dados = {
        "consumo": _extrair_consumo(inconsistencias),
        "estoque": _extrair_estoque(inconsistencias),
        "solicitacoes": _extrair_solicitacoes(inconsistencias),
    }
    return dados, inconsistencias


def main():
    DADOS_TRATADOS.mkdir(parents=True, exist_ok=True)
    dados, inconsistencias = extrair()

    destino = DADOS_TRATADOS / "base_tpjl_extras.xlsx"
    with pd.ExcelWriter(destino) as writer:
        dados["consumo"].to_excel(writer, index=False, sheet_name="Consumo")
        dados["estoque"].to_excel(writer, index=False, sheet_name="Estoque")
        dados["solicitacoes"].to_excel(writer, index=False, sheet_name="Solicitacoes")

    registrar_log(
        nome_execucao="extrair_tpjl_extras",
        arquivos_lidos=[str(c) for c in ARQUIVOS_FONTE.values()],
        arquivos_gerados=[str(destino)],
        inconsistencias=inconsistencias,
    )

    for chave, df in dados.items():
        print(f"{chave}: {len(df)} linha(s) válida(s) -> {destino} (aba {chave.capitalize()})")
    if inconsistencias:
        print(f"{len(inconsistencias)} inconsistência(s) encontrada(s), ver log em 06_Logs/.")

    return dados


def _registrar_historico_solicitacoes(df_solicitacoes):
    """Acrescenta o snapshot de hoje (1 linha por Nº Solicitação) — se já
    rodou hoje antes, substitui só as linhas de hoje (não duplica). Base pra
    barra temporal pedida pelo Wallace em 2026-07-14 ("opcao de rolagem ...
    buscando um historico e mostrando a evolucao"), mesmo componente já
    usado em MTA/TPJL (`projetos/components/evolucao.py`). Só existe
    história a partir do dia em que essa função passou a rodar."""
    hoje = datetime.now().date().isoformat()
    novo = df_solicitacoes[COLUNAS_HISTORICO_SOLICITACOES].copy()
    novo["data_criacao"] = novo["data_criacao"].astype(str)
    novo["ultima_atualizacao"] = novo["ultima_atualizacao"].astype(str)
    novo.insert(0, "data_snapshot", hoje)

    if HISTORICO_SOLICITACOES.exists():
        historico = pd.read_csv(HISTORICO_SOLICITACOES)
        historico = historico[historico["data_snapshot"] != hoje]
        historico = pd.concat([historico, novo], ignore_index=True)
    else:
        historico = novo
    historico.to_csv(HISTORICO_SOLICITACOES, index=False)


def _arquivo_mais_recente_da_pasta(folder_id):
    """Lista a subpasta e retorna o metadado do arquivo com modifiedTime mais
    recente — Wallace sobe um arquivo novo (nome com timestamp) a cada
    atualização, nunca sobrescreve o mesmo ID (2026-07-16)."""
    arquivos = drive_sync.listar_pasta(folder_id)
    arquivos = [a for a in arquivos if a.get("mimeType") != "application/vnd.google-apps.folder"]
    if not arquivos:
        raise RuntimeError(f"Nenhum arquivo encontrado na pasta {folder_id}.")
    return max(arquivos, key=lambda a: a["modifiedTime"])


def atualizar_do_drive():
    """Busca a versão mais recente das 3 planilhas no Google Drive (o
    arquivo mais novo de cada subpasta — ver FONTES_EXTRAS), sobrescreve as
    cópias locais e reprocessa. Se uma falhar, as outras continuam sendo
    tentadas — qualquer falha marca status "erro" no estado. Ver
    00_Instrucoes/atualizacoes.md (raiz)."""
    erros = []
    metadados_por_fonte = {}
    for chave, config in cfg.FONTES_EXTRAS.items():
        try:
            mais_recente = _arquivo_mais_recente_da_pasta(config["drive_folder_id"])
            metadados_por_fonte[chave] = mais_recente
            conteudo = drive_sync.baixar_arquivo(mais_recente["id"])
            ARQUIVOS_FONTE[chave].parent.mkdir(parents=True, exist_ok=True)
            ARQUIVOS_FONTE[chave].write_bytes(conteudo)
        except Exception as e:
            erros.append(f"{chave}: {e}")

    try:
        dados = main()
        _registrar_historico_solicitacoes(dados["solicitacoes"])
    except Exception as e:
        estado.atualizar_estado(ESTADO_ATUALIZACOES, "tpjl_extras", status="erro", last_error=str(e))
        raise

    total = sum(len(df) for df in dados.values())
    if erros:
        estado.atualizar_estado(
            ESTADO_ATUALIZACOES, "tpjl_extras", status="erro",
            last_error="; ".join(erros),
            local_updated_at=datetime.now().isoformat(),
            record_count=total,
        )
        raise RuntimeError("; ".join(erros))

    modificado_mais_recente = max(m["modifiedTime"] for m in metadados_por_fonte.values())
    estado.atualizar_estado(
        ESTADO_ATUALIZACOES, "tpjl_extras",
        remote_modified_time=modificado_mais_recente,
        local_updated_at=datetime.now().isoformat(),
        status="atualizado",
        record_count=total,
        record_count_consumo=len(dados["consumo"]),
        record_count_estoque=len(dados["estoque"]),
        record_count_solicitacoes=len(dados["solicitacoes"]),
        last_error=None,
    )
    return estado.obter_entrada(ESTADO_ATUALIZACOES, "tpjl_extras")


if __name__ == "__main__":
    import sys
    if "--atualizar-do-drive" in sys.argv:
        atualizar_do_drive()
    else:
        main()
