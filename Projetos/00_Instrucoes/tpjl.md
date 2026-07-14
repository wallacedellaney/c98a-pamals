# TPJL — Controle CABW

Especificação completa dada pelo Wallace em 2026-07-09. Ver `Projetos/CLAUDE.md`
para status de implementação. Nome exibido no site: "TPJL — Controle CABW".

## Fontes

- "TPOB - Controle CABW 2025" (`1zkBB77PXvzRTg-8n-tgNAYX8lJB8KozPvuyGiNtARsA`)
- "TPOB - Controle CABW 2026" (`1Mf_R70IDJ9auysySW1oATGt3TSrPZE081-O3nB930lc`)

Ambas compartilhadas com a conta de serviço em 2026-07-09. Aba usada
inicialmente: "COORDENADORES".

**Filtro obrigatório**: só registros com PJT = U8 (== C-98, mesma convenção já
usada em Vencimentos TMOT).

## 2025 e 2026 separados (não unificados)

**Mudança de decisão do Wallace em 2026-07-09**: não unificar as 2 planilhas
numa massa só. Cada ano é extraído e tratado como sua própria base (2 abas
no arquivo tratado: "TPJL_2025" e "TPJL_2026", cada uma com a coluna **Ano da
fonte** só pra identificação/exibição). O dashboard mostra os dois anos lado
a lado — abas "2025", "2026" e "Comparativo" (ver seção Experiência visual) —
em vez de uma tabela única fundida. Não excluir registros só por terem o
mesmo PN. Só remover linha quando for duplicação **completamente idêntica**
dentro da mesma fonte/ano.

## Campos

Nº Requisição, T, PJT, PN, Descrição, QTD, Valor Unit, Valor Total, Status
Comprar, Status 11G, Status, Previsão p/ Empenho, DPE, Observação
Coordenadores.

## Status atual (campo calculado)

3 colunas de acompanhamento na planilha (Status Comprar, Status 11G, Status)
são preservadas originais. Campo calculado **Status atual** = último status
preenchido, prioridade da direita pra esquerda: 1) Status, 2) Status 11G,
3) Status Comprar. Normalização só pra comparação/agrupamento (texto original
preservado). Tratar "Cancelada"/"Cancelado" como o mesmo grupo visual.

Valores esperados: Aguardando validação, Em cotação, Empenho solicitado,
Recebida na comissão, Mapa gerado, Mapa aprovado, Validada, Embarcado,
Empenhado, Cancelado, Item fracassado, Item deserto, Aguardando intenção,
Sem informação.

## Indicadores

Total de requisições U8, quantidade total de itens, valor total, registros
2025, registros 2026, empenhos solicitados/aprovados/empenhados, em cotação,
mapas gerados/aprovados, cancelados, itens fracassados/desertos, sem
previsão, previsões vencidas, sem observação dos coordenadores.

**Pendência**: não considerar como pendência os já classificados como
Empenhado, Cancelado, Item deserto, Item fracassado — regra centralizada
numa função de negócio única (pra ajustar depois sem espalhar lógica).

## Controle de previsão

Converter "Previsão p/ Empenho" pra data quando o conteúdo for data válida.
Textos como "IMEDIATO"/"EMPENHADO"/vazio não podem causar erro. Classificação:
No prazo, Vencido, Sem data definida, Concluído, Cancelado. Vencido = data
anterior a hoje + não empenhado + não cancelado + não deserto/fracassado.
Mostrar dias de atraso nos vencidos.

## Gráficos

1. Distribuição por Status atual
2. Valor total por Status atual
3. Previsões de empenho por mês
4. Comparação 2025 x 2026
5. Valor total por ano
6. Registros vencidos por situação
7. Funil simplificado: Solicitação → Cotação → Validação → Mapa → Empenho
   solicitado → Empenho aprovado → Empenhado (não forçar etapa quando o texto
   não permitir identificar).

## Filtros

Ano, Status atual, Status Comprar, Status 11G, Status, Situação da previsão,
Previsão por mês, DPE. Busca por Nº requisição, PN, Descrição. "Projeto: U8"
fixo no cabeçalho.

## Tabela operacional

Ano, Nº requisição, PJT, PN, Descrição, Quantidade, Valor unitário, Valor
total, Status Comprar, Status 11G, Status, Status atual, Previsão para
empenho, Situação da previsão, Dias de atraso, DPE, Observação dos
coordenadores. Destaque discreto: previsões vencidas, sem previsão, sem
observação, empenhados, cancelados, desertos/fracassados. Clique na linha
abre painel lateral com histórico do registro.

## Atualização

Botão próprio "Atualizar TPJL" — lê 2025 e 2026 no mesmo processo (2
chamadas ao Drive, uma por planilha), mas apresenta o resultado de cada
fonte separadamente (registros lidos/válidos por fonte) e grava cada ano em
sua própria aba do arquivo tratado. Indicador de carregamento, sem clique
duplo, erro tratado sem derrubar a página — se só um dos dois anos falhar
ao buscar, o outro continua atualizado.

## Experiência visual — 2025/2026 separados

Dentro da página "TPJL — Controle CABW": 3 abas —

- **2025** — indicadores + gráficos + tabela operacional só do ano.
- **2026** — idem, só do ano.
- **Comparativo** — indicadores lado a lado, gráfico "Valor total por ano" e
  "Comparação 2025 x 2026" (itens 4/5 da seção Gráficos), sem misturar as
  tabelas operacionais dos dois anos numa só.

## Consumo / Estoque / Solicitações (2026-07-14)

Pedido do Wallace: "puxaar mais 3 informcacoes que sao as 3 planilhas que
estao na pasta planilhas TPLJ, que sao informacoes consumo, estoque e
solciitacoes ... estruture uma forma de colcoar tudo nessa parte, no mesmo
layout das coisas que estao ai, inclusive dentro". Não são um projeto novo —
são 3 fontes extras **dentro** da mesma página "TPJL — Controle CABW", 3
abas a mais depois de "Comparativo": **Consumo**, **Estoque**,
**Solicitações**. Cada uma com seu próprio botão "Atualizar" (mesmo padrão
das outras fontes — sem "atualizar tudo").

### Fontes (pasta Drive "Planilhas TPLJ", 3 subpastas)

- **Consumo** — `relatorio_consumo_*.xlsx` (`1guih043Q3hNZOMx3YQX6LD4h2wSqUd20`).
  Histórico mensal de consumo: Part Number, CFF, Projeto, Descrição,
  Categoria (C/R/T), Mês Competência, Ano Competência, Qtd Consumo.
- **Estoque** — `relatorio_estoque_*.xlsx` (`1mmVUl8QO5PHecu56Goqw0WUbvwdMAhqU`).
  Situação atual: Part Number, CFF, Projeto, Descrição, Categoria (C/R/T),
  Qtd em Estoque, Setor (TSAU/TSAU2/SUTI/TSAM/ESUP/TSAS/SALI/TSUI), Unidade
  (base/operador — nomenclatura em parte igual à de Vencimentos, ex. BAMN/
  BABE/BACG/CLA/BABR/BANT/BACO/DACTA II, mais códigos que só aparecem aqui:
  PAMALS, BASM, PAMASP, EEAR, PAMAGL, BABV, EPCAR, PAMB, BAAN, BAPV, CCA SJ,
  BAGL, GEIV).
- **Solicitações** — `relatorio_solicitacoes_*.xlsx`
  (`1J0Yi7JdWYHgqaCxS-Vnv9o2ViHG8jm0T`). Log de pedidos: Nº Solicitação,
  Projeto, Part Number, CFF, Nomenclatura, Categoria (C/T/R/P), Quantidade,
  Tipo (Emergência/Caderno de Compras/Pedido Normal/Outros/Reposição de
  Estoque), Status (Finalizada/Pendente/Aprovada/Negada/Atender/Deletado),
  Unidade de Estocagem, Solicitante, Data de Criação, Última Atualização
  (texto "DD/MM/AAAA HH:MM" na fonte, convertido pra data/hora no
  tratamento).

Arquivos reais `.xlsx` enviados ao Drive (não Planilhas Google nativas) —
baixados sem `exportar_como`, mesmo padrão de Vencimentos por Operador.

**"Categoria" (C/R/T/P), "Setor" e "Unidade" ficam exatamente como a
planilha escreve** — o significado exato de cada sigla não foi confirmado
com o Wallace, então não convertemos pra um rótulo "amigável" inventado.

Todas as 3 já vêm 100% filtradas em Projeto = "U8" na própria fonte
(confirmado na extração) — filtramos de novo mesmo assim, defensivamente,
por princípio (formato de fonte pode mudar a qualquer mês).

**Consumo teve 412 linhas completamente duplicadas** (idênticas em todas as
colunas) na extração inicial — removidas, mesma regra já usada no TPJL
principal ("só remover linha quando for duplicação completamente idêntica
dentro da mesma fonte").

### Extração

`05_Scripts/python/extrair_tpjl_extras.py` — gera
`02_Dados_Tratados/base_tpjl_extras.xlsx` (3 abas: Consumo/Estoque/
Solicitacoes). Config em `projetos/config/tpjl_config.py::FONTES_EXTRAS`.
Botão único "Atualizar" nas 3 abas novas (mesmo `atualizar_fonte("tpjl_extras")`,
já que é 1 script/1 arquivo tratado com 3 abas — mesmo padrão de Pagamentos
no Contrato 005). Ainda **não** entrou na cadência automática de 2 em 2h —
manual por enquanto (ver `00_Instrucoes/atualizacoes.md`, raiz, se/quando
formos automatizar).

### Cada aba nova (Consumo/Estoque/Solicitações)

Mesmo padrão visual das abas 2025/2026 (indicadores em cards, filtros,
gráficos, tabela operacional com exportação CSV) — sem histórico/"barra
temporal" (não pedido pro Wallace nessas 3 fontes).

- **Consumo**: indicadores (linhas, quantidade total, PNs distintos, período
  coberto); filtros (Ano, Mês, Categoria, busca PN/Descrição); gráficos
  (quantidade por ano, quantidade por categoria, top 10 PN mais consumidos);
  tabela + CSV.
- **Estoque**: indicadores (itens, quantidade total, PNs distintos, nº de
  unidades); filtros (Unidade, Setor, Categoria, busca PN/Descrição);
  gráficos (quantidade por unidade — top 10, quantidade por setor, top 10 PN
  com mais estoque); tabela + CSV.
- **Solicitações**: indicadores (total, pendentes, aprovadas, finalizadas,
  negadas); filtros (Tipo, Status, Solicitante, busca Nº/PN/Nomenclatura);
  gráficos (distribuição por Status — cores fixas em
  `paleta.py::COR_STATUS_SOLICITACAO`, distribuição por Tipo, top 10
  solicitantes, solicitações por mês de criação); tabela + CSV.

Implementado em `projetos/secoes/tpjl_extras.py`, chamado a partir de 3 abas
novas em `projetos/secoes/tpjl.py::render()`.
