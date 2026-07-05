"""Acesso ao Google Drive a partir do próprio app Streamlit — separado do
acesso que o Claude tem ao Drive dentro da conversa. Usa uma conta de
serviço (credencial em .secrets/service_account.json, ver
00_Instrucoes/atualizacoes.md na raiz do projeto) só com permissão de
leitura nos arquivos/pastas compartilhados com ela.

API mínima usada pelos botões "Atualizar X" de cada área:
* obter_metadados — checa a versão mais recente no Drive (nome, data de
  modificação) sem baixar o conteúdo.
* baixar_arquivo — baixa o conteúdo. Planilhas Google nativas (RAC, TMOT,
  Emergências, Reparáveis, Pagamentos) precisam de `exportar_como` (viram
  .xlsx); arquivos já enviados como .xlsx/.ods (Vencimentos por Operador)
  são baixados como estão, sem exportar.
* listar_pasta — lista os filhos diretos de uma pasta (usado só pela
  Disponibilidade Diária, que navega ano -> mês -> dia).
"""

from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

CAMINHO_CREDENCIAIS = Path(__file__).resolve().parent.parent / ".secrets" / "service_account.json"
ESCOPOS = ["https://www.googleapis.com/auth/drive.readonly"]

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
TEXTO_MIME = "text/plain"

_servico = None


class DriveSyncError(Exception):
    """Qualquer falha ao falar com o Google Drive — quem chama só precisa
    tratar esse único tipo, sem conhecer a hierarquia de exceções do Google."""


def _obter_servico():
    global _servico
    if _servico is not None:
        return _servico
    if not CAMINHO_CREDENCIAIS.exists():
        raise DriveSyncError(
            f"Credencial do Google não encontrada em {CAMINHO_CREDENCIAIS}. "
            "Ver 00_Instrucoes/atualizacoes.md para o passo a passo de configuração."
        )
    try:
        credenciais = service_account.Credentials.from_service_account_file(
            str(CAMINHO_CREDENCIAIS), scopes=ESCOPOS
        )
        _servico = build("drive", "v3", credentials=credenciais, cache_discovery=False)
    except Exception as e:
        raise DriveSyncError(f"Falha ao autenticar com o Google Drive: {e}") from e
    return _servico


def obter_metadados(file_id):
    """Retorna {"id", "name", "modifiedTime", "mimeType"} sem baixar conteúdo."""
    try:
        servico = _obter_servico()
        return servico.files().get(fileId=file_id, fields="id,name,modifiedTime,mimeType").execute()
    except HttpError as e:
        raise DriveSyncError(f"Falha ao consultar metadados do arquivo {file_id}: {e}") from e


def baixar_arquivo(file_id, exportar_como=None):
    """Baixa o conteúdo do arquivo como bytes. Se `exportar_como` for um
    mimeType (ex.: XLSX_MIME), usa export (obrigatório pra Planilhas/Docs
    nativos do Google); senão baixa o binário como está (arquivo já
    enviado como .xlsx/.ods/.pdf etc.)."""
    try:
        servico = _obter_servico()
        if exportar_como:
            return servico.files().export(fileId=file_id, mimeType=exportar_como).execute()
        return servico.files().get_media(fileId=file_id).execute()
    except HttpError as e:
        raise DriveSyncError(f"Falha ao baixar o arquivo {file_id}: {e}") from e


def listar_pasta(folder_id):
    """Lista os filhos diretos de uma pasta: [{"id","name","mimeType","modifiedTime"}, ...]."""
    try:
        servico = _obter_servico()
        resultado = []
        token = None
        while True:
            resposta = servico.files().list(
                q=f"'{folder_id}' in parents and trashed = false",
                fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
                pageToken=token,
            ).execute()
            resultado.extend(resposta.get("files", []))
            token = resposta.get("nextPageToken")
            if not token:
                break
        return resultado
    except HttpError as e:
        raise DriveSyncError(f"Falha ao listar a pasta {folder_id}: {e}") from e
