"""Lê os relatórios diários de disponibilidade (texto colado do WhatsApp/SILOMS,
salvo em .txt) de 01_Bases_Originais/Disponibilidade_Diaria/ e gera
02_Dados_Tratados/base_disponibilidade_diaria.xlsx.

Formato de origem (ver 00_Instrucoes/disponibilidade_diaria.md):
* Título: "*C-98 - DD/MM/AAAA*"
* Resumo: "XX D / XX M" seguido de "(XX DI / XX DO / XX II / XX IN / XX ITR / XX IS / XX IP)"
* "*Previsão até o final do dia: XX D / XX M*"
* "*Previsão de disponibilidade semanal*" com blocos "*Disponíveis:* XX" e
  "*Montadas:* XX", cada um seguido de uma linha "- matricula, matricula, ..."
  com as aeronaves que entram nessa previsão.
* "*Esforço Aéreo*" / "Anual: HH:MM:SS / HH:MM:SS / XX,XX%"
* "*Motores disponíveis: XX*"
* Um bloco por unidade: linha "*NOME DA UNIDADE*" seguida de linhas
  "[ ] MATRICULA - SITUACAO - ocorrência (opcional) - DPE: ... (opcional)"

Cada aeronave DENTRO de uma unidade tem uma situação (DI, DO, II, IN, ITR, IS,
IP — ver 00_Instrucoes/disponibilidade_diaria.md para o significado de cada
uma). O relatório não informa "montada" por aeronave individualmente (só o
total M da frota) — por isso a tabela Aeronaves não tem essa coluna; ver
instruções.
"""

import re
from datetime import date, datetime

import pandas as pd

from common import BASES_ORIGINAIS, DADOS_TRATADOS, ESTADO_ATUALIZACOES, registrar_log
from shared import drive_sync, estado

PASTA_ORIGEM = BASES_ORIGINAIS / "Disponibilidade_Diaria"

# Ver 00_Instrucoes/disponibilidade_diaria.md — pasta "Atualização de
# Disponibilidade" → ano → mês (nome do mês muda todo mês, tem que buscar
# de novo) → um Google Doc por dia.
PASTA_RAIZ_DRIVE_ID = "1JLrUGunWo5ABsR3WuYo88b2WD4QWoxNH"
RE_NOME_DOC = re.compile(r"Disponibilidade\s+(\d{2})/(\d{2})")

RE_TITULO = re.compile(r"^\*C-98\s*-\s*(\d{2}/\d{2}/\d{4})\*$")
RE_RESUMO_DM = re.compile(r"^(\d+)\s*D\s*/\s*(\d+)\s*M$")
RE_CODIGOS = re.compile(
    r"^\((\d+)\s*DI\s*/\s*(\d+)\s*DO\s*/\s*(\d+)\s*II\s*/\s*(\d+)\s*IN\s*/\s*(\d+)\s*ITR\s*/\s*(\d+)\s*IS\s*/\s*(\d+)\s*IP\)$"
)
RE_PREVISAO_FIM_DIA = re.compile(r"^\*Previsão até o final do dia:\s*(\d+)\s*D\s*/\s*(\d+)\s*M\*$")
RE_DISPONIVEIS_SEMANA = re.compile(r"^\*Disponíveis:\*\s*(\d+)$")
RE_MONTADAS_SEMANA = re.compile(r"^\*Montadas:\*\s*(\d+)$")
RE_ESFORCO = re.compile(r"^Anual:\s*([\d:]+)\s*/\s*([\d:]+)\s*/\s*([\d,]+)%$")
RE_MOTORES = re.compile(r"^\*Motores disponíveis:\s*(\d+)\*$")
RE_UNIDADE = re.compile(r"^\*([^*]+)\*$")
RE_AERONAVE = re.compile(r"^\[\s?\]\s*(\d{3,4})\s*-\s*([A-Z]{1,3})(?:\s*-\s*(.*))?$")
RE_DPE_SPLIT = re.compile(r"\s*-\s*DPE\s*:\s*", re.IGNORECASE)
RE_DATA_COMPLETA = re.compile(r"^(\d{2})/(\d{2})/(\d{4})")
RE_DATA_CURTA = re.compile(r"^(\d{2})/(\d{2})$")

TITULOS_CONHECIDOS = {"RESUMO:", "Disponibilidade", "Previsão de disponibilidade semanal", "Esforço Aéreo"}


def _parse_dpe(texto, ano_referencia):
    """Tenta achar uma data concreta (DD/MM ou DD/MM/AAAA) no texto do DPE.
    Se não achar, retorna (None, texto) — condição em texto livre, sem inventar data."""
    if not texto:
        return None, None
    m = RE_DATA_COMPLETA.match(texto.strip())
    if m:
        d, mth, y = m.groups()
        try:
            return date(int(y), int(mth), int(d)), texto
        except ValueError:
            return None, texto
    m = RE_DATA_CURTA.match(texto.strip())
    if m:
        d, mth = m.groups()
        try:
            return date(ano_referencia, int(mth), int(d)), texto
        except ValueError:
            return None, texto
    return None, texto


def _parse_lista_matriculas(linha):
    if not linha:
        return []
    linha = linha.lstrip("-").strip().rstrip(".")
    return [m.strip() for m in linha.split(",") if m.strip()]


def parse_relatorio(caminho):
    linhas = [l.strip() for l in caminho.read_text(encoding="utf-8-sig").splitlines()]
    linhas = [l for l in linhas if l != ""]

    resumo = {}
    aeronaves = []
    unidade_atual = None
    i = 0
    while i < len(linhas):
        linha = linhas[i]

        m = RE_TITULO.match(linha)
        if m:
            d, mth, y = m.group(1).split("/")
            resumo["data_referencia"] = date(int(y), int(mth), int(d))
            i += 1
            continue

        m = RE_RESUMO_DM.match(linha)
        if m and "disponiveis_hoje" not in resumo:
            resumo["disponiveis_hoje"] = int(m.group(1))
            resumo["montadas_hoje"] = int(m.group(2))
            i += 1
            continue

        m = RE_CODIGOS.match(linha)
        if m:
            resumo["di"], resumo["do_"], resumo["ii"], resumo["in_"], resumo["itr"], resumo["is_"], resumo["ip"] = (
                int(x) for x in m.groups()
            )
            i += 1
            continue

        m = RE_PREVISAO_FIM_DIA.match(linha)
        if m:
            resumo["previsao_fim_dia_disponiveis"] = int(m.group(1))
            resumo["previsao_fim_dia_montadas"] = int(m.group(2))
            i += 1
            continue

        m = RE_DISPONIVEIS_SEMANA.match(linha)
        if m:
            resumo["previsao_semana_disponiveis_qtd"] = int(m.group(1))
            prox = linhas[i + 1] if i + 1 < len(linhas) else ""
            if prox.startswith("-"):
                resumo["previsao_semana_disponiveis_novas"] = ", ".join(_parse_lista_matriculas(prox))
                i += 2
                continue
            resumo["previsao_semana_disponiveis_novas"] = ""
            i += 1
            continue

        m = RE_MONTADAS_SEMANA.match(linha)
        if m:
            resumo["previsao_semana_montadas_qtd"] = int(m.group(1))
            prox = linhas[i + 1] if i + 1 < len(linhas) else ""
            if prox.startswith("-"):
                resumo["previsao_semana_montadas_novas"] = ", ".join(_parse_lista_matriculas(prox))
                i += 2
                continue
            resumo["previsao_semana_montadas_novas"] = ""
            i += 1
            continue

        m = RE_ESFORCO.match(linha)
        if m:
            resumo["esforco_anual_previsto"] = m.group(1)
            resumo["esforco_anual_realizado"] = m.group(2)
            resumo["esforco_percentual"] = float(m.group(3).replace(",", "."))
            i += 1
            continue

        m = RE_MOTORES.match(linha)
        if m:
            resumo["motores_disponiveis"] = int(m.group(1))
            i += 1
            continue

        m = RE_AERONAVE.match(linha)
        if m and unidade_atual is not None:
            matricula, situacao, resto = m.groups()
            ocorrencia, dpe_texto = None, None
            if resto:
                partes = RE_DPE_SPLIT.split(resto, maxsplit=1)
                ocorrencia = partes[0].strip() or None
                if len(partes) > 1:
                    dpe_texto = partes[1].strip()
            dpe_data, dpe_condicao = _parse_dpe(dpe_texto, resumo["data_referencia"].year)
            aeronaves.append({
                "matricula": matricula,
                "unidade": unidade_atual,
                "situacao": situacao,
                "ocorrencia": ocorrencia,
                "dpe_data": dpe_data,
                "dpe_condicao": dpe_condicao if dpe_data is None else None,
                "dpe_texto_original": dpe_texto,
            })
            i += 1
            continue

        m = RE_UNIDADE.match(linha)
        if m and m.group(1) not in TITULOS_CONHECIDOS:
            unidade_atual = m.group(1)
            i += 1
            continue

        i += 1

    return resumo, aeronaves


def extrair():
    inconsistencias = []
    arquivos = sorted(PASTA_ORIGEM.glob("*.txt"))
    if not arquivos:
        raise FileNotFoundError(f"Nenhum relatório .txt encontrado em {PASTA_ORIGEM}")

    relatorios = []
    todas_aeronaves = []
    for caminho in arquivos:
        resumo, aeronaves = parse_relatorio(caminho)
        if "data_referencia" not in resumo:
            inconsistencias.append(f"{caminho.name}: não encontrei a data de referência (título).")
            continue
        resumo["arquivo"] = caminho.name
        relatorios.append(resumo)
        for a in aeronaves:
            a["data_referencia"] = resumo["data_referencia"]
        todas_aeronaves.extend(aeronaves)

    df_relatorios = pd.DataFrame(relatorios).sort_values("data_referencia").reset_index(drop=True)
    df_aeronaves = pd.DataFrame(todas_aeronaves).sort_values(["data_referencia", "unidade", "matricula"]).reset_index(drop=True)

    # soma de situações declaradas (DI+DO+II+IN+ITR+IS+IP) deve bater com a
    # quantidade de aeronaves listadas naquele relatório — checagem de
    # consistência (ver secao 31 do briefing).
    for _, rel in df_relatorios.iterrows():
        soma_codigos = rel[["di", "do_", "ii", "in_", "itr", "is_", "ip"]].sum()
        qtd_listada = len(df_aeronaves[df_aeronaves["data_referencia"] == rel["data_referencia"]])
        if soma_codigos != qtd_listada:
            inconsistencias.append(
                f"{rel['arquivo']}: soma dos códigos ({soma_codigos}) != aeronaves listadas ({qtd_listada})."
            )

    return df_relatorios, df_aeronaves, inconsistencias


def main():
    DADOS_TRATADOS.mkdir(parents=True, exist_ok=True)
    df_relatorios, df_aeronaves, inconsistencias = extrair()

    destino = DADOS_TRATADOS / "base_disponibilidade_diaria.xlsx"
    with pd.ExcelWriter(destino) as writer:
        df_relatorios.to_excel(writer, index=False, sheet_name="Relatorios")
        df_aeronaves.to_excel(writer, index=False, sheet_name="Aeronaves")

    registrar_log(
        nome_execucao="extrair_disponibilidade_diaria",
        arquivos_lidos=[str(p) for p in sorted(PASTA_ORIGEM.glob("*.txt"))],
        arquivos_gerados=[str(destino)],
        inconsistencias=inconsistencias,
    )

    print(f"{len(df_relatorios)} relatório(s), {len(df_aeronaves)} aeronaves-linha -> {destino}")
    if inconsistencias:
        print(f"{len(inconsistencias)} inconsistência(s) encontrada(s), ver log em 06_Logs/.")

    return df_relatorios


def _achar_subpasta(pasta_id, prefixo):
    """Acha, dentro de `pasta_id`, a subpasta cujo nome começa com `prefixo`
    (ex.: prefixo="2026" acha a pasta do ano; prefixo="07 " acha "07 Julho").
    Se não achar por prefixo, cai pra maior nome em ordem alfabética (os
    nomes de ano/mês já ordenam certo como texto)."""
    filhos = drive_sync.listar_pasta(pasta_id)
    pastas = [f for f in filhos if f["mimeType"] == "application/vnd.google-apps.folder"]
    candidatos = [f for f in pastas if f["name"].strip().startswith(prefixo)]
    if candidatos:
        return candidatos[0]
    return sorted(pastas, key=lambda f: f["name"])[-1] if pastas else None


def atualizar_do_drive():
    """Busca o relatório diário mais recente ainda não salvo localmente,
    direto do Drive (sem eu precisar estar numa conversa) — ver
    00_Instrucoes/disponibilidade_diaria.md. Nunca sobrescreve relatório
    antigo; se não achar nada novo (ex.: fim de semana, ou relatório do dia
    ainda não publicado), não é erro — só não faz nada."""
    try:
        agora = datetime.now()
        pasta_ano = _achar_subpasta(PASTA_RAIZ_DRIVE_ID, str(agora.year))
        if pasta_ano is None:
            raise drive_sync.DriveSyncError(f"Pasta do ano {agora.year} não encontrada.")
        pasta_mes = _achar_subpasta(pasta_ano["id"], f"{agora.month:02d} ")
        if pasta_mes is None:
            raise drive_sync.DriveSyncError(f"Pasta do mês {agora.month:02d} não encontrada em {pasta_ano['name']}.")

        filhos = drive_sync.listar_pasta(pasta_mes["id"])
        docs = [(f, RE_NOME_DOC.search(f["name"])) for f in filhos]
        docs = [(f, m) for f, m in docs if m]
        if not docs:
            # Mesmo sem relatório novo pra buscar, reprocessa o que já existe
            # localmente — garante que a planilha tratada nunca fique
            # desatualizada em relação aos .txt já salvos (bug corrigido em
            # 2026-07-08: essa função podia "achar que não tinha nada a
            # fazer" e nunca chamar main(), deixando o site desatualizado
            # mesmo com o relatório certo já salvo localmente).
            df_relatorios = main()
            estado.atualizar_estado(ESTADO_ATUALIZACOES, "disponibilidade_diaria",
                                     status="sem_novidade", last_error=None,
                                     local_updated_at=datetime.now().isoformat(),
                                     record_count=len(df_relatorios))
            return {"status": "sem_novidade", "motivo": "nenhum relatório na pasta do mês atual",
                    "record_count": len(df_relatorios)}

        doc, m = max(docs, key=lambda par: int(par[1].group(1)))
        dia, mes = m.group(1), m.group(2)
        nome_local = f"Disponibilidade_{dia}_{mes}_{agora.year}.txt"
        caminho = PASTA_ORIGEM / nome_local

        novo = not caminho.exists()
        if novo:
            conteudo = drive_sync.baixar_arquivo(doc["id"], exportar_como=drive_sync.TEXTO_MIME)
            # utf-8-sig: o Google Docs exporta texto puro com um BOM no início,
            # que quebrava o parser (RE_TITULO não batia na 1ª linha) — descoberto
            # em 2026-07-07, na 1ª busca real feita por este caminho automático.
            texto = conteudo.decode("utf-8-sig") if isinstance(conteudo, bytes) else conteudo
            PASTA_ORIGEM.mkdir(parents=True, exist_ok=True)
            caminho.write_text(texto, encoding="utf-8")

        # Sempre reprocessa, novo ou não — ver comentário acima sobre o bug
        # de 2026-07-08 (planilha tratada podia ficar desatualizada mesmo
        # com o .txt certo já salvo).
        df_relatorios = main()

        if novo:
            estado.atualizar_estado(
                ESTADO_ATUALIZACOES, "disponibilidade_diaria",
                remote_modified_time=doc["modifiedTime"],
                local_updated_at=datetime.now().isoformat(),
                status="atualizado", record_count=len(df_relatorios), last_error=None,
            )
            return {"status": "atualizado", "arquivo": nome_local, "record_count": len(df_relatorios)}

        estado.atualizar_estado(ESTADO_ATUALIZACOES, "disponibilidade_diaria",
                                 status="sem_novidade", last_error=None,
                                 local_updated_at=datetime.now().isoformat(),
                                 record_count=len(df_relatorios))
        return {"status": "sem_novidade", "arquivo": nome_local, "record_count": len(df_relatorios)}
    except Exception as e:
        estado.atualizar_estado(ESTADO_ATUALIZACOES, "disponibilidade_diaria", status="erro", last_error=str(e))
        raise


if __name__ == "__main__":
    import sys
    if "--atualizar-do-drive" in sys.argv:
        print(atualizar_do_drive())
    else:
        main()
