# Instruções — Empréstimos (planilha "Devoluções")

## Fonte

Planilha Google Sheets **"Devoluções"** (conta `aux.coord.c98@gmail.com`), aba **"DEVOLUÇÃO"** (a mais atual — a planilha também tem "DEVOLUÇÃO COMPLETO" (mais antiga), "HISTORICO", "Tabela dinâmica 2", "ESTOQUE VEE ONE" e "Dados de PN", nenhuma dessas usada por enquanto).

330 linhas de dados reais (linha 1 = título/data, linha 2 = cabeçalho, dados a partir da linha 3). Já compartilhada com a conta de serviço da automação (`pamals-drive-reader@...`) — não precisou de nova permissão.

**⚠️ 2026-07-13: bug real na extração, corrigido.** A extração original
só pulava a linha se `numero_ordem` (Nº de Ordem, coluna A) estivesse
vazio — mas a planilha tinha esse número arrastado por fórmula bem além
dos itens de verdade, deixando **94 linhas totalmente em branco** (só o
número sequencial, 332 a 425, tudo mais vazio) contadas como itens reais
"Pendente" — inflando o total pra 424 em vez dos 330 reais. Achado pelo
Wallace ("acho que são 416 linhas não, vai até 300 e pouco" — 416 já
tinha o "Desconsiderado" descontado, mas ainda incluía essas 94 linhas
fantasma). Corrigido exigindo Part Number também preenchido pra
considerar a linha real (`extrair_devolucoes.py`).

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
| Status (2ª, última) | `status` | **o status real** — "OK"/"Ok" (normalizado pra "OK"), vazio (normalizado pra "Pendente"), ou **"Desconsiderado"** (novo em 2026-07-13 — ver seção própria abaixo) |

Sem filtro na extração — as 424 linhas entram, o filtro é só no dashboard (por Status, Categoria, Destino, busca livre).

## Status "Desconsiderado" — nunca entra em nenhuma conta

**2026-07-13**: o Wallace percebeu que "eles devolveram quase nada"
(olhando o card "% concluído" por linha, 8%) enquanto a estatística por
**quantidade** mostrava quase metade devolvida (912 de 1.952) — a causa:
poucas linhas de status "OK" tinham quantidade GIGANTE (500 GM de um
parafuso, três linhas de 100 EA cada), inflando a soma por quantidade
sem representar a realidade (a devolução daquelas linhas específicas não
era uma devolução real de material emprestado). O Wallace corrigiu na
própria planilha "Devoluções", criando o status **"Desconsiderado"**
pra essas linhas: "arrumei os status desses itens, chama desconsiderado,
nao entra nunca na conta de nada".

Filtrado (`df = df[df["status"] != "Desconsiderado"]`) logo depois de
carregar os dados, nos 3 lugares que leem `base_devolucoes_tratada.xlsx`
direto — nunca aparece em estatística, gráfico, card ou total de nenhum
dos três:
- Site: `contrato005/data/carregar_dados.py::carregar_devolucoes()`
  (usado por `emprestimos.py` E pelo card de Empréstimos em
  `visao_geral.py`, ambos automaticamente).
- Apresentação (RMA): `gerar_apresentacao_rma.py::_carregar_dados_emprestimos()`.
  Ata de Reunião: `gerar_ata_reuniao.py::carregar_emprestimos_mes()`.

Depois da correção (8 linhas viraram "Desconsiderado"): Total de itens
416 (era 424), Total de quantidade 1.099 (era 1.952), Devolvidos OK
(quantidade) caiu de 912 pra **59** — agora bate com a percepção real do
Wallace.

**Confirmado que "Desconsiderado" já não aparece em lugar nenhum** —
inclusive na tabela "Todos os itens" (filtro acontece antes de qualquer
uso do dataframe, `carregar_devolucoes()`), testado explicitamente com
`AppTest` em 2026-07-13.

**Gráfico "por linha x por quantidade" (pedido do Wallace, mesma
conversa)**: 2 gráficos de rosca lado a lado, "Devolvido: por linha
(itens/pedidos)" e "Devolvido: por quantidade (unidades)" — mesmos dados
(Pendente x OK), uma visão conta linha e a outra soma quantidade, pra
comparar os dois de propósito e não se enganar com uma linha de
quantidade grande distorcendo a leitura (foi exatamente isso que
aconteceu antes da correção do "Desconsiderado").

## Por que "Empréstimos" e não "Devoluções"

A pedido do Wallace (2026-07-09): a fonte se chama "Devoluções", mas a tela no site chama "Empréstimos" — é sobre material retirado do estoque/emprestado e o que ainda falta devolver (Status = Pendente), não só o que já foi devolvido.

## Tela

`03_Dashboard/contrato005/secoes/emprestimos.py`, menu do Contrato 005:
- Visual no topo: 5 cards — "Total de itens (linhas)", "Total de quantidade", "Emprestados, pendentes (quantidade)", "Devolvidos, OK (quantidade)", "% concluído" — + 3 gráficos (pizza de status, barra por categoria, barra por top destinos), **todos ponderados por quantidade** (ver seção "Ponderado por quantidade" abaixo).
- **Evolução mensal (a partir de 2026-07-09, por quantidade desde 2026-07-13)**: 2 linhas do tempo lado a lado — "Empréstimos por mês" (soma quantidade por mês de `pedido_envio`, a data em que o item saiu do estoque) e "Devoluções por mês" (soma quantidade por mês de `data_devolucao`). São datas diferentes de propósito — a maioria dos itens tem `pedido_envio` preenchido (324 de 424) mas poucos têm `data_devolucao` (30 de 424, a maior parte ainda está pendente).
- Tabela completa embaixo, **sem filtro por padrão** (mostra os 424 itens) — com filtro por Status (Todos/Pendente/OK — esse é "o filtro do OK" pedido), Categoria, Destino e busca livre (PN/descrição/aeronave).
- Exportação em CSV.

**⚠️ 2026-07-13: regressão encontrada e corrigida.** A ponderação por
quantidade (feita em 2026-07-12) tinha sumido do arquivo — voltou a
contar só linhas (`.value_counts()`), sem multiplicar pela coluna
`quantidade`. Provavelmente foi revertida junto com a mesma reversão que
apagou o gerador de Apresentação (RMA) nessa janela de tempo (ver
`apresentacao_rma.md`). Reaplicada a pedido do Wallace ("tem q
multiplicar as linhas pela quantidade, ai a gente consegue ver quantos
itens foram emprestados e quantos foram devolvidos") — agora inclui
também "Emprestados, pendentes" e "Devolvidos, OK" em quantidade (não só
"Total de quantidade" geral), respondendo direto a essa pergunta.

## Visão Geral (card resumo)

**2026-07-13**: o card de Empréstimos na Visão Geral (`secoes/visao_geral.py`)
só mostrava "Total de itens" (contagem de linhas) — era a única tela que
tinha ficado de fora quando a ponderação por quantidade foi aplicada em
todo o resto (site, apresentação, Ata). Corrigido: agora mostra "Total de
itens (linhas)" e "Total de quantidade" lado a lado, e o gráfico de pizza
"Empréstimos: status" também pesa por quantidade (`quantidade_efetiva`),
igual à tela de Empréstimos.

## Atualização

`extrair_devolucoes.py` segue o mesmo padrão das outras fontes com credencial própria (`atualizar_do_drive()`, xlsx binário, sem risco de bug de encoding). **Ainda não está no agendamento automático** — roda manual por enquanto (`python3 extrair_devolucoes.py --atualizar-do-drive`, ou pedir na conversa). Perguntar ao Wallace se quer adicionar a uma cadência quando fizer sentido.
