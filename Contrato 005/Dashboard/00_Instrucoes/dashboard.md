# Instruções — Dashboard

## Objetivo

Dashboard interativo do Contrato 005, com visão consolidada e atualizada dos três frentes do contrato: emergências, reparáveis e pagamentos.

## Estrutura geral

O dashboard tem **4 partes**, navegáveis por botões clicáveis na parte de baixo da tela:

1. Visão Geral (resumo das 3 áreas abaixo)
2. Reparáveis
3. Emergências Abertas
4. Pagamentos

Cada seção só pode ler dados de `02_Dados_Tratados/`. Nunca ler diretamente de `01_Bases_Originais/`.

---

## 0. Visão Geral

Tela inicial do dashboard. Mostra um resumo consolidado com os principais indicadores das 3 áreas (ver `indicadores.md`), por exemplo:

* total de emergências abertas e quantas atrasadas;
* total de OS de reparáveis em aberto e por condição;
* total faturado/pendente do contrato.

Cada resumo deve linkar/levar para a seção detalhada correspondente ao ser clicado.

---

## 1. Reparáveis

Fonte de dados: `02_Dados_Tratados/base_reparaveis_tratada.xlsx`

Campos exibidos:

* OS;
* PN e nomenclatura;
* SN (e SN trocado, quando houver exchange);
* situação (ST_OS);
* condição (reparo);
* onde se encontra (empresa/base/local atual);
* datas (data início, TAT SILOMS);
* progresso do acerto virtual, quando preenchido.

Filtros disponíveis:

* situação (ST_OS);
* condição;
* onde se encontra.

Mostrar somente Ordens de Serviço em aberto (ST_OS diferente de "OS concluída"). Ver detalhes em `reparaveis.md`.

> Esta fonte não traz cliente/base solicitante nem quantidade — esses campos não estão disponíveis no momento.

---

## 2. Emergências Abertas

Fonte de dados: `02_Dados_Tratados/base_emergencias_tratada.xlsx`

Campos exibidos:

* OM / OM_EMG (base e organização militar);
* matrícula da aeronave (MATR);
* PN e nomenclatura da peça;
* situação (ST_EMG);
* prazo de entrega e DPE;
* dias de atraso / dias corridos;
* provedor;
* observações (coordenadoria/fiscal e VEE ONE).

Filtros disponíveis:

* aeronave (MATR);
* OM / base;
* situação (ST_EMG);
* provedor;
* faixa de dias de atraso.

Mostrar somente emergências em aberto (ST_EMG diferente de "Concluída" e não atendidas/canceladas). Ver regra completa em `emergencias.md`.

---

## 3. Pagamentos

Fonte de dados: `02_Dados_Tratados/base_pagamentos_tratada.xlsx`

Campos exibidos:

* módulo (1, 2 ou 3);
* mês/referência;
* nota fiscal (Nº) e recibo;
* valor da nota (Valor das Nfs);
* valor faturado;
* valor pendente;
* situação (Pago / Faturado, aguardando pagamento / Pendente);
* datas relevantes (Data, Vencimento);
* dados do empenho vinculado (saldo, responsável, justificativa — vindos da aba Empenhos).

Filtros disponíveis:

* módulo;
* situação;
* mês/período.

Ver regra de situação e cruzamento com Empenhos em `pagamentos.md`.

---

## Indicadores (KPIs)

As fórmulas e definições de cada indicador exibido no dashboard estão em `indicadores.md`. O dashboard deve consumir os indicadores já calculados, não recalcular regras de negócio dentro da camada visual.

## Atualização

O dashboard é atualizado sempre que houver novos arquivos em `02_Dados_Tratados/`. Não gerar gráfico a partir de dado tratado desatualizado — verificar data do arquivo antes de exibir.
