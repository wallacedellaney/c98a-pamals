"""Configuração central do MTA — nomes/IDs/colunas num só lugar (pedido do
Wallace, ver 00_Instrucoes/mta.md seção 7). Mudar aqui, não espalhado pelo
extrator/dashboard."""

PLANILHA = "MTA - Acompanhamento e Solicitações"
ABA = "Solicitações"
DRIVE_FILE_ID = "1ZdV1PX4ujqPgQNGk7f_WPkvA42aArVkGS59TVW78zhs"

PROJETO_FILTRO = "C-98"

# Índices de coluna (0-based) na aba "Solicitações", linha de cabeçalho = 2.
# A planilha real tem 2 campos "Projeto" (bloco coordenador e bloco
# atividade) — ver 00_Instrucoes/mta.md.
COL_PROJETO_COORDENADOR = 0
COL_LINHA = 1
COL_APROVADO = 2
COL_ACAO = 3
COL_TRAMITE = 4
COL_DATA_PEDIDO = 5
COL_DIGITO = 6
COL_RODADA = 7
COL_PREENCHIMENTO_TGCO = 8
COL_OBSERVACAO_COORDENADOR = 9
COL_IMPACTOS_NAO_ATENDIMENTO = 10
COL_PROJETO_ATIVIDADE = 11
COL_ATIVIDADE = 12
COL_TAREFA = 13
COL_VALOR = 14
COL_EXECUTORA = 15
COL_ND = 16
COL_PACOTE = 17
COL_PARA_CONTRATO = 18
COL_PARA_MOTORES = 19
COL_MES_PREVISTO = 20

MAX_COL = 21
LINHA_CABECALHO = 2
PRIMEIRA_LINHA_DADOS = 3

# Status finais — não contam mais como "sem andamento".
TRAMITE_ATENDIDO = "ATENDIDO"
TRAMITE_EM_TRAMITE = "EM TRÂMITE"
