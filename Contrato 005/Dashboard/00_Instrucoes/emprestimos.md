# Instruções — Empréstimos (planilha "Devoluções")

## Fonte

Planilha Google Sheets **"Devoluções"** (conta `aux.coord.c98@gmail.com`), aba **"DEVOLUÇÃO"** (a mais atual — a planilha também tem "DEVOLUÇÃO COMPLETO" (mais antiga), "HISTORICO", "Tabela dinâmica 2", "ESTOQUE VEE ONE" e "Dados de PN", nenhuma dessas usada por enquanto).

424 linhas de dados (linha 1 = título/data, linha 2 = cabeçalho, dados a partir da linha 3). Já compartilhada com a conta de serviço da automação (`pamals-drive-reader@...`) — não precisou de nova permissão.

## Estrutura da aba "DEVOLUÇÃO"

A planilha tem **2 colunas "QTD" e 2 colunas "Status"** (nomes duplicados na origem) — renomeadas na extração pra ficar claro:

| Coluna na planilha | Nome tratado | Observação |
|---|---|---|
| Nº de Ordem | `numero_ordem` | |
| Part Number | `part_number` | |
| Descrição | `descricao` | |
| SN/LT | `sn_lt` | |
| CAT | `categoria` | C (consumo), T (troca?), R (reparável) |
| QTD (1ª) | `quantidade_texto` | com unidade, ex. "01 EA", "500 GM" |
| QTD (2ª) | `quantidade` | só o número |
| Pedido / EMG | `pedido_emg` | número do pedido/emergência |
| Motivo | `motivo` | |
| PJ | `pj` | código de projeto/autorização |
| Pedido de envio | `pedido_envio` | data |
| ANV | `anv` | matrícula da aeronave (às vezes "*" ou vazio) |
| Destino | `destino` | unidade/base (BANT, BABR, BABE...) |
| NF / GMM | `nf_gmm` | |
| Rastreio | `rastreio` | |
| PN devolvido | `pn_devolvido` | |
| Status (1ª) | `detalhe_entrega` | texto livre, tipo "ENTREGUE NA BABR 1 EA" — nota de entrega, não é o status final |
| Nº da RC | `numero_rc` | |
| NF de devolução VEE ONE | `nf_devolucao_vee_one` | |
| Data de Devolução | `data_devolucao` | |
| Observação Fiscal | `observacao_fiscal` | texto livre |
| Observação Empresa | `observacao_empresa` | texto livre |
| Status (2ª, última) | `status` | **o status real** — "OK"/"Ok" (normalizado pra "OK") ou vazio (normalizado pra "Pendente") |

Sem filtro na extração — as 424 linhas entram, o filtro é só no dashboard (por Status, Categoria, Destino, busca livre).

## Por que "Empréstimos" e não "Devoluções"

A pedido do Wallace (2026-07-09): a fonte se chama "Devoluções", mas a tela no site chama "Empréstimos" — é sobre material retirado do estoque/emprestado e o que ainda falta devolver (Status = Pendente), não só o que já foi devolvido.

## Tela

`03_Dashboard/contrato005/secoes/emprestimos.py`, menu do Contrato 005:
- Visual no topo: cards (total, pendentes, OK, % concluído) + 3 gráficos (pizza de status, barra por categoria, barra por top destinos).
- Tabela completa embaixo, **sem filtro por padrão** (mostra os 424 itens) — com filtro por Status (Todos/Pendente/OK — esse é "o filtro do OK" pedido), Categoria, Destino e busca livre (PN/descrição/aeronave).
- Exportação em CSV.

## Atualização

`extrair_devolucoes.py` segue o mesmo padrão das outras fontes com credencial própria (`atualizar_do_drive()`, xlsx binário, sem risco de bug de encoding). **Ainda não está no agendamento automático** — roda manual por enquanto (`python3 extrair_devolucoes.py --atualizar-do-drive`, ou pedir na conversa). Perguntar ao Wallace se quer adicionar a uma cadência quando fizer sentido.
