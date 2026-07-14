# MTA — Acompanhamento e Solicitações

Especificação completa dada pelo Wallace em 2026-07-09. Ver `Projetos/CLAUDE.md`
para status de implementação.

## Fonte

Planilha Google Sheets "MTA - Acompanhamento e Solicitações"
(`1ZdV1PX4ujqPgQNGk7f_WPkvA42aArVkGS59TVW78zhs`, compartilhada com a conta de
serviço em 2026-07-09), aba "Solicitações".

**Filtro obrigatório**: só registros do projeto C-98. A planilha tem 2 campos
"Projeto" (um no bloco do coordenador, outro no bloco de dados da atividade)
— aplicar o filtro C-98 quando o valor estiver presente em qualquer um dos
dois, sem duplicar linha quando os dois batem.

## Campos

**Bloco do coordenador**: Projeto, Linha, Aprovado, Ação, Trâmite, Data
Pedido, Dígito, Rodada em que foi solicitado o atendimento, Preenchimento da
TGCO.

**Bloco de dados da atividade**: Projeto, Atividade, Tarefa, Valor,
Executora, ND, Pacote, Para Contrato, Para Motores, Mês previsto.

Preservar os valores originais; campos normalizados são só pra exibição/análise.

## Indicadores (topo)

Total de solicitações C-98, aprovadas, não aprovadas, atendidas, em trâmite,
sem andamento informado, valor total, valor previsto para contrato, valor
relacionado a motores. Moeda em formato brasileiro (`R$ 1.234.567,89`); nunca
somar célula vazia/texto/inválida.

## Situação consolidada (campo calculado, não altera a planilha)

- Trâmite = "ATENDIDO" → **Atendido**
- Trâmite = "EM TRÂMITE" → **Em trâmite**
- Aprovado = "SIM" e Trâmite vazio → **Aprovado, aguardando atendimento**
- Aprovado = "NÃO" → **Não aprovado**
- Demais → **Sem informação**

Comparação ignora maiúsculas/minúsculas, espaços extras e acentuação. Manter
"Aprovado"/"Trâmite" originais disponíveis na tabela.

## Gráficos

1. Distribuição por situação consolidada
2. Valores por mês previsto
3. Valores por executora
4. Barras por pacote
5. Resumo por destinação: contrato / motores / demais

Todos respondem aos filtros da página.

## Filtros

Situação consolidada, Aprovado, Trâmite, Executora, Atividade, Pacote, Para
Contrato, Para Motores, Mês previsto. Busca por Linha, Dígito, Atividade,
Tarefa. "Projeto: C-98" fixo no cabeçalho.

## Tabela operacional

Linha, Situação consolidada, Aprovado, Trâmite, Data do pedido, Dígito,
Rodada de atendimento, Preenchimento da TGCO, Atividade, Tarefa, Valor,
Executora, Pacote, Para Contrato, Para Motores, Mês previsto. Ordenação,
filtro, pesquisa, paginação, exportação, painel de detalhes ao clicar na
linha (campos vazios = "Não informado").

**Filtro por coluna na própria tabela (2026-07-14, pedido do Wallace):**
expander "🔍 Filtros por coluna" logo acima da tabela — um multiselect por
coluna já formatada pra exibição (estilo AutoFiltro do Excel), além dos
filtros de topo já existentes (Situação/Executora/Pacote/Mês/busca).
Componente `projetos/components/filtros.py::filtro_colunas` — duplicado do
mesmo componente já usado na Diagonal de Manutenção da Coordenadoria (não
importado de lá, por causa da regra de não misturar pacotes entre áreas).
O painel de detalhes ao clicar numa linha busca o registro completo em
`filtrado` pela **Linha** (chave única), não pela posição — a posição muda
depois do filtro por coluna reduzir a tabela.

Cores de status discretas: verde (atendido), azul/amarelo (em andamento),
cinza (sem informação), vermelho discreto (não aprovado/pendência relevante).

## Atualização

Botão próprio "Atualizar MTA" — mostra última atualização, duração,
registros lidos, registros válidos após filtro, erro (se houver). Indicador
de carregamento, sem clique duplo.
