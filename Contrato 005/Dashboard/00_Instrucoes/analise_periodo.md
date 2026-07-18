# Análise de Período

Pedido pelo Wallace em 2026-07-10: "central dinâmica de análise" com slider
de período, comparação automática com o período anterior equivalente,
cards de mudança, gráfico de evolução diária, tabela filtrável, botão de
resumo e uma área "O que mudou?" em linguagem executiva.

## Decisões tomadas (confirmadas com o Wallace antes de construir)

- **Escopo**: só Emergências (Contrato 005) — não cruza com Disponibilidade
  operacional da Coordenadoria (áreas propositalmente separadas no
  projeto). O Wallace confirmou: "cada dado com seu slider" — ou seja, um
  slider de período por tópico/planilha, não uma página única cruzando
  áreas diferentes.
- **"Mudanças na disponibilidade"** → interpretado como mudança no campo
  **Estoque** (Sim/Não) das emergências, não a disponibilidade operacional
  da aeronave (código D/M da Coordenadoria) — mantém o escopo dentro de
  Emergências.
- **Filtro "projeto"** do pedido original → mapeado pra **Tipo** (`tpemg`:
  AIFP/IPLR/ANCE), que é o campo equivalente que existe nos dados de
  emergências (não existe um conceito de "projeto" nessa fonte).

## Fonte de dados

`historico_emergencias.csv` (`Contrato 005/Dashboard/02_Dados_Tratados/`) —
já existia (1 snapshot por dia das emergências em aberto, desde
2026-07-06). Adicionada a coluna **`estoque`** em 2026-07-10 (não existia
antes) — só há mudança de estoque detectável a partir de quando essa coluna
passou a ser gravada.

## Arquitetura

- `contrato005/components/comparacao_periodo.py` — lógica pura (sem
  Streamlit, testável isoladamente): `datas_disponiveis`,
  `periodo_anterior_equivalente`, `diff_periodo`, `linha_do_tempo`.
- `contrato005/secoes/analise_periodo.py` — a página em si (nova aba
  "Análise de Período" na navegação do Contrato 005).

## Como funciona a comparação

1. O Wallace escolhe um intervalo `[início, fim]` no slider (só datas com
   snapshot gravado).
2. `diff_periodo` compara o snapshot de `início` com o de `fim`:
   - **Novas**: emergências presentes em `fim` mas não em `início`.
   - **Concluídas**: presentes em `início` mas não em `fim` (saíram da
     lista de "em aberto" — concluídas ou canceladas).
   - **Entraram em atraso** / **saíram do atraso**: presentes nos dois,
     com `dias_atraso` cruzando 0 (de "no prazo" pra "atrasado" ou o
     contrário).
   - **Mudança de estoque**: presentes nos dois, com `estoque` mudando de
     Sim→Não ou Não→Sim.
3. Automaticamente, calcula o **período anterior equivalente** (mesmo
   tamanho, imediatamente antes) e roda a mesma comparação nele, só pra
   mostrar o delta em cada card (não duplica a seção toda).
4. Se não houver histórico suficiente pro período anterior (comum agora,
   com poucos dias de histórico acumulados), mostra aviso e some com o
   delta — sem quebrar a página.

## Limitações conhecidas

- Só existe histórico a partir de 2026-07-06 (Emergências) — a comparação
  fica mais rica conforme os dias passam.
- Mudança de estoque só é detectável a partir de 2026-07-10 (dia em que a
  coluna passou a ser gravada) — comparações que incluam dias antes disso
  mostram 0 mudanças de estoque mesmo que possa ter havido mudança de
  verdade (dado não existia ainda).

## Desempenho da empresa — 3 gráficos por mês (2026-07-18)

Pedido do Wallace: "coloca tb um historico da MMAM do ano de 2026 e
graficos de desempenho da empresa" — depois "ficou ruim, deixa uma linha
que vai mudando, melhore essa analise da empresa, coloca mais grafico"
(trocado de barra pra linha + 2 gráficos novos). Nova seção no topo da
página (antes do slider de período), `_secao_desempenho()`, 3 indicadores,
todos como gráfico de **linha** com marcadores + linha pontilhada da média
do ano:

1. **MMAM** — lido do Cômputo Mensal já calculado
   (`carregar_historico_mmam()`, só lê `computo_mensal/<ano>-<mes>_resumo.json`,
   não recalcula nada, não duplica `calcular_computo_mensal.py`). Só
   aparece pros meses que já foram calculados.
2. **% de entregas no prazo por mês** — recalculado ao vivo a partir de
   `emergencias_totais`, agrupado pelo mês de `atendido_cancelado`, mesma
   regra da aba Atrasos (`dias_atraso <= 0` = no prazo). Diferente do
   MMAM, dá pra montar pra qualquer mês já concluído sem depender de um
   cálculo salvo, porque a data de conclusão já está na própria fonte.
3. **Novas emergências abertas por mês** — contagem por mês de
   `data_abertura`, mesma fonte.

Cada gráfico só aparece se tiver dado de 2026 suficiente (senão a seção
mostra um aviso ou fica menor, nunca quebra).

Se um dia quiser mais indicadores, avisar.

## Controle de data global (pedido do Wallace em 2026-07-10, follow-up)

Depois de construir a Análise de Período, o Wallace pediu um controle de
data **global**: arrastar 1 slider no topo do Contrato 005 e sincronizar
"todos os cards, gráficos e tabelas" das outras abas com aquele dia.

**Limitação real explicada e confirmada com o Wallace antes de construir**:
só Emergências tinha histórico diário guardado — Reparáveis, Pagamentos e
Empréstimos nunca guardaram um retrato por dia (só o estado atual). O
Wallace escolheu a opção mais trabalhosa: **criar histórico diário pras 3
fontes também**, em vez de deixá-las de fora do controle de data.

### O que foi feito

1. **Histórico diário novo** em `extrair_reparaveis.py`,
   `extrair_pagamentos.py` e `extrair_devolucoes.py` (mesmo padrão de
   `_registrar_historico()` já usado em Emergências/RAC/MTA/TPJL) — gera
   `historico_reparaveis.csv`, `historico_pagamentos.csv`,
   `historico_devolucoes.csv` em `02_Dados_Tratados/`. **Só existe a partir
   de 2026-07-10** (dia em que essa gravação começou pra essas 3 fontes).
2. **Reparáveis e Empréstimos entraram na cadência automática** (2 em 2h,
   `shared/executar_atualizacao.py`) — antes, Reparáveis era
   deliberadamente manual ("sem conexão ao vivo"); essa decisão foi
   revertida a pedido do Wallace, porque sem atualização automática o
   histórico nunca cresceria sozinho.
3. **`contrato005/components/data_global.py`** — módulo novo com:
   - `render_seletor_global(dados)` — o slider no topo (chamado 1x em
     `contrato_app.py`, antes de despachar pra página ativa), grava a data
     em `st.session_state["data_global"]`.
   - `mostrar_snapshot_se_necessario(dados, chave_fonte)` — chamado no
     início do `render()` de Reparáveis, Pagamentos, Empréstimos e
     Emergências Abertas. Se a data global for uma data passada **e**
     aquela fonte específica tiver snapshot daquele dia, substitui a
     página inteira por uma visão histórica reduzida (só os campos
     gravados no snapshot) e devolve `True` (a página faz `return` nesse
     caso). Se for "hoje"/mais recente, ou a fonte não tiver dado
     daquele dia específico, devolve `False` e a página renderiza
     **exatamente como sempre renderizou** — zero mudança de lógica pro
     caso comum.
   - `mostrar_nota_historica_se_necessario(dados)` — versão "leve" usada só
     na Visão Geral: não substitui a página (ela mistura várias fontes,
     não dá pra reconstruir sem duplicar toda a lógica dos cards), só
     avisa que os números ali são sempre atuais.

### Por que "preserva a lógica existente" (pedido explícito do Wallace)

Cada página ganhou só 2-3 linhas no topo do `render()` (a chamada de guarda
+ import). Nenhuma lógica de renderização normal foi alterada — pra "hoje",
o comportamento é idêntico a antes de 2026-07-10.

### Limitação que continua valendo

- **Visão Geral** não tem versão histórica própria (mistura Emergências +
  Reparáveis + Pagamentos + Empréstimos numa lógica só) — mostra um aviso
  em vez de fingir reconstruir tudo.
- **Fechamento Mensal** e **Análise de Período** continuam com seus
  próprios seletores (mês / intervalo), não usam o controle global — são
  semanticamente diferentes (mês vs intervalo arbitrário) e já resolvem
  esse mesmo problema de outro jeito.
- A visão histórica de cada fonte é **reduzida** (só os campos que o
  snapshot daquele dia guardou, não a tabela completa) — mesma limitação
  já documentada pro histórico de MTA/TPJL/Emergências.
