"""Leitura dos relatórios SILOMS da pasta V2 TPLJ, restritos ao projeto U8."""

from datetime import datetime
from io import BytesIO
from pathlib import Path
import re
from zipfile import BadZipFile

import pandas as pd

from shared import drive_sync
from shared.escrita_atomica import caminho_temporario

PASTA_DRIVE = "1uX2LOwZw4zO0PpStD4G6u_SCIjYTZPsZ"
PASTA_LOCAL = Path(__file__).resolve().parents[3] / "01_Bases_Originais" / "TPJL_V2"
FONTES = {
    "consumo": ("Consumo", "1ERwy2djU0nvp4yzH-PG6PLFagfPt-B6N", "consumption", {"Competência", "Consumo", "Unidade"}),
    "estoque": ("Estoque", "1bW2czO8BixxvW5DTpH_gtvSpf-0R5qGy", "stock", {"Tipo de saldo", "Quantidade", "Unidade", "Setor"}),
    "requisicoes": ("Requisições emitidas", "1WfyYTi7FJ7tcEFIEafIWUFkh3jq3yOoh", "requisitions", {"Requisição", "Plano", "Quantidade", "Emitida em", "Previsão de entrega", "Unidade de criação", "Unidade de destino", "Status da requisição", "Status do plano"}),
    "pedidos": ("Pedidos de suprimento", "1qWPl7QJB584SmLXwRottbRpoOHpI54wY", "supply-orders", {"Pedido", "Qtd. pedida", "Qtd. autorizada", "Qtd. atendida", "Criado em", "Conclusão", "Tipo", "Status"}),
    "os": ("Ordens de serviço", "12a_e1dYWIkKAV2SxjoJuYZAD3oRWceqf", "service-orders", {"OS", "Quantidade", "Qtd. concluída", "Qtd. condenada", "Criada em", "Fim previsto", "Unidade executante", "Setor executante", "Prioridade", "Tipo", "Status"}),
}


def ler_relatorio(conteudo, chave):
    try:
        return _ler_xlsx(conteudo, chave)
    except BadZipFile as exc:
        raise ValueError("O arquivo não é um XLSX válido.") from exc


def _ler_xlsx(conteudo, chave):
    with pd.ExcelFile(BytesIO(conteudo), engine="openpyxl") as arquivo:
        meta = pd.read_excel(arquivo, header=None, nrows=3).fillna("")
        df = pd.read_excel(
            arquivo, header=3,
            dtype={c: "string" for c in ("PN", "CFF", "OS", "Pedido", "Plano", "Requisição")},
        )
    df.columns = df.columns.str.strip()
    obrigatorias = {"Projeto", "PN", "CFF", "Nomenclatura", *FONTES[chave][3]}
    falta = obrigatorias.difference(df.columns)
    if falta:
        raise ValueError(f"Colunas ausentes: {', '.join(sorted(falta))}.")
    if meta.shape[1] < 2 or list(meta.iloc[1:3, 0]) != ["Filtros", "Obtido em"]:
        raise ValueError("O cabeçalho do relatório SILOMS não foi reconhecido.")
    u8 = df["Projeto"].astype("string").str.strip().str.upper().eq("U8").fillna(False)
    if not df.empty and not u8.any():
        raise ValueError("O relatório não contém registros do projeto U8.")
    return df.loc[u8].reset_index(drop=True), str(meta.iat[1, 1]), str(meta.iat[2, 1])


def sincronizar_fonte(chave):
    """Escolhe a exportação mais recente pelo carimbo no nome, incluindo subpastas."""
    _, pasta, tipo, _ = FONTES[chave]
    padrao = re.compile(rf"relatorio-siloms-{tipo}-(\d{{8}}-\d{{6}})\.xlsx", re.I)
    pendentes = [pasta]
    visitadas = set()
    candidatos = []
    while pendentes:
        pasta = pendentes.pop()
        if pasta in visitadas:
            continue
        visitadas.add(pasta)
        for arquivo in drive_sync.listar_pasta(pasta):
            if arquivo["mimeType"] == "application/vnd.google-apps.folder":
                pendentes.append(arquivo["id"])
                continue
            match = padrao.fullmatch(arquivo["name"])
            if match and arquivo["mimeType"] == drive_sync.XLSX_MIME:
                candidatos.append((match[1], arquivo.get("modifiedTime", ""), arquivo["id"]))
    if not candidatos:
        raise ValueError("Nenhuma exportação SILOMS com o nome esperado foi encontrada no Drive.")
    conteudo = drive_sync.baixar_arquivo(max(candidatos)[2])
    registrar_posicao(chave, conteudo)
    destino = PASTA_LOCAL / f"{chave}.xlsx"
    destino.parent.mkdir(parents=True, exist_ok=True)
    with caminho_temporario(destino) as tmp:
        tmp.write_bytes(conteudo)


def registrar_posicao(chave, conteudo):
    """Guarda a última extração válida de cada competência de extração."""
    _, _, extraido = ler_relatorio(conteudo, chave)
    data = datetime.strptime(extraido, "%d/%m/%Y %H:%M:%S")
    destino = PASTA_LOCAL / "historico" / chave / f"{data:%Y-%m}.xlsx"
    if destino.exists():
        _, _, anterior = ler_relatorio(destino.read_bytes(), chave)
        if datetime.strptime(anterior, "%d/%m/%Y %H:%M:%S") >= data:
            return
    destino.parent.mkdir(parents=True, exist_ok=True)
    with caminho_temporario(destino) as tmp:
        tmp.write_bytes(conteudo)
