# Instruções — Indicadores

> Proposta inicial — a validar. Fórmulas usam os nomes de campo definidos em `emergencias.md`, `reparaveis.md` e `pagamentos.md`.

## Emergências Atuais

| Indicador | Fórmula |
|---|---|
| Total em aberto | contagem de registros com `ST_EMG` ≠ "Concluída" e `Atd/cancelada` vazio |
| Emergências atrasadas | contagem, dentre as em aberto, com `DIAS ATRASO` > 0 |
| % atrasadas | atrasadas ÷ total em aberto |
| Atraso médio (dias) | média de `DIAS ATRASO` entre as atrasadas |
| Idade média (dias) | média de `DIAS CORRIDOS` entre as em aberto |
| Emergências por provedor | contagem agrupada por `Provedor` |
| Emergências por aeronave | contagem agrupada por `MATR` |

## Reparáveis

| Indicador | Fórmula |
|---|---|
| Total de OS em aberto | contagem de registros com `ST_OS` ≠ "OS concluída" |
| Tempo médio em aberto (dias) | média de `TAT SILOMS` entre as OS em aberto |
| OS por condição | contagem agrupada por `CONDIÇÃO` (Em Reparo, Reparado, Condenado, Em Quarentena, Procurando...) |
| % condenados | contagem com `CONDIÇÃO` = "Condenado" ÷ total de OS em aberto |
| OS por localização | contagem agrupada por `ONDE SE ENCONTRA` (empresa/base/local atual) |

## Pagamentos

| Indicador | Fórmula |
|---|---|
| Total faturado | soma de `Faturado` |
| Total pendente | soma de `Pendente` |
| Total pago | soma de `Faturado` onde `Ordem de Pagamento` está preenchida |
| Saldo do contrato | `Saldo (Valor a Faturar)` do bloco de dados do contrato |
| % executado do contrato | `Valor Liquidado` ÷ `Valor Total do Contrato` |
| Valor por módulo | soma de `Valor das Nfs` agrupada por `Módulo` |
| Evolução mensal | soma de `Valor das Nfs` agrupada por `Referência` (mês) |

## Pendências

* Confirmar se os indicadores acima são os que devem aparecer no dashboard, ou se faltam/sobram itens.
* Definir se cada indicador aparece como número único (card) ou como gráfico (série/barra) — isso deve ser refletido em `dashboard.md` depois de validado aqui.
