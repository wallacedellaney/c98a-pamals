# Atrasos (Fechamento Mensal)

Regras dadas pelo Wallace em 2026-07-10. Fonte: `historico_completo_emergencias.xlsx`
(já filtrado só VEE ONE — ver `emergencias.md`). Duas seções, dentro da aba
"Atrasos" de Fechamento Mensal (`03_Dashboard/contrato005/secoes/fechamento_mensal.py`,
função `_atrasos`).

## 1. Situação atual (em aberto agora)

Não depende do mês de referência escolhido — sempre mostra o que está
em aberto **agora**, filtrado só VEE ONE (`em_aberto == True`). Indicadores:
total em aberto, dentro do prazo, atrasadas (`dias_atraso > 0`) — mais a
tabela com todas elas.

## 2. Entregas no mês de referência (concluídas ou canceladas)

**Regra central**: pega **todo item VEE ONE cancelado ou concluído dentro
do mês de referência** (`atendido_cancelado` cai entre o 1º e o último dia
do mês) — **não importa quando abriu, a aeronave ou o tipo de emergência**
(AIFP, IPLR, ANCE, etc. — todos entram, diferente do Cômputo Mensal que só
conta AIFP/IPLR).

- **No prazo**: `dias_atraso <= 0` (entregue no dia do prazo ou antes).
- **Atrasado**: `dias_atraso > 0`.
- Resumo no formato pedido pelo Wallace:

  | Período de apuração | Total de entregas previstas | Entregas no Prazo | QTD Mensal (%) |
  |---|---|---|---|
  | 01/07 - 31/07 | 10 | 8 | 80,00% |

- Tabela detalhada abaixo, com filtro por Situação/Tipo/busca e clique na
  linha pra ver o detalhe completo (mesmo padrão de outras telas do site).

## Comentário da Coordenadoria indicando cancelamento (2026-07-17)

Mesma regra do Cômputo Mensal (ver `computo_mensal.md`): se a observação da
Coordenadoria (`obs_coordenadoria_fiscal`) indica cancelamento/"não é mais
necessário" mas o campo oficial `Atd/cancelada` ainda está em branco, a
emergência **não aparece** em "Situação atual (em aberto agora)" — pedido
do Wallace: "nem quero ver elas la, nao aparecer visualmente". Não afeta
"Entregas no mês de referência" (que só mostra itens já com data oficial
de conclusão/cancelamento, então essa regra nunca se aplicaria ali mesmo).

## Tratamento de dados inconsistentes

`atendido_cancelado` às vezes vem como texto em vez de data (ex.:
"verificar data", achado em produção) — esses registros são **excluídos**
da contagem por mês (não dá pra saber a qual mês pertencem) e um aviso
aparece na tela informando quantos foram ignorados. Não interrompe a
página.

## PN e Nomenclatura (2026-07-16)

Pedido do Wallace — ver `computo_mensal.md`, mesma seção. As tabelas de
"Situação atual" e "Entregas no mês de referência", e o painel de detalhe
ao clicar numa linha, agora mostram PN e Nomenclatura logo depois da
Emergência (já vinham na fonte `emergencias_totais`, só não apareciam
aqui).

## Validado em

2026-07-10, julho/2026: 10 entregas no mês, 8 no prazo (80%), 1 registro
com data inválida ignorado, 14 emergências em aberto (11 dentro do prazo,
3 atrasadas).
