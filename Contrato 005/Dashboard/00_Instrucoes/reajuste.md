# Instruções — Reajuste

## Pedido do Wallace (2026-07-16)

Pediu pra acessar a "Planilha Demonstrativa -2_Reajuste- Contrato
005_CELOG-PAMALS_2025" e trazer "valor do contrato após reajuste, saldo do
módulo 1 2 3". Na sequência, pediu pra criar uma aba própria "Reajuste" no
site com **todas** as informações dessa planilha (não só os 2 valores
iniciais) — "colcoa essa informcao no contrato pra saber o valor ... cria
uma aba chamada reajuste onde tem todas essas infomacoes ai dessa planilha".

## Fonte

Arquivo `.xlsx` real enviado ao Drive pelo Wallace (não Planilha Google
nativa) — "Planilha Demonstrativa -2_Reajuste - Contrato
005_CELOG-PAMALS_2025.xlsx", pasta pessoal do Wallace no Drive.
`DRIVE_FILE_ID = "1R32r4rscXTYGe98R1AFUUG8hqZD-GaWY"`.

Tem 4 abas — só as 2 primeiras são usadas (as outras 2 são cópias antigas
que o próprio Wallace guarda por referência, ignoradas de propósito):

* **"Valor do Contrato"** — indicadores escalares (valor de assinatura,
  execução autorizada, saldo por módulo, índices IPCA, suplementos,
  valor do contrato pós-reajuste, valor da hora de voo) + 2 tabelas de
  Notas Fiscais (uma antes do 1° Reajuste, outra depois).
* **"Cronogroma Físico Financeiro"** (nome com erro de digitação na
  própria planilha — "Cronogroma", não "Cronograma" — mantido assim no
  código de propósito, pra bater com a fonte de verdade) — execução
  mensal por módulo, projetada até 2029, + uma tabela resumo (Proposta
  Comercial x Executado x Reajustado).
* ~~"Cópia de Valor do Contrato"~~ / ~~"Cópia de Cronogroma Físico Fina"~~ —
  ignoradas (snapshots antigos guardados pelo Wallace).

## Por que "após 2° Reajuste" não é um valor novo ainda (2026-07-16)

Na seção do 2° Reajuste, o índice IPCA aparece com **0,00%** e todos os
"Suplemento Contratual" com **R$ 0,00** — o "Valor do Contrato após 2°
Reajuste" (R$ 86.162.536,55) bate exatamente com o "Saldo do Contrato após
1° Reajuste" de antes, sem nenhum acréscimo. Perguntei ao Wallace se isso
era um dado faltando — ele confirmou: **"é pq é apos o 2 reajuste mas ja
inserindo as coisas do ano, o reajuste é so outubro"** — ou seja, o 2°
reajuste (novo índice IPCA) só acontece de verdade no aniversário anual do
contrato (outubro), a planilha só rola a execução pra frente enquanto isso.
Comportamento esperado, não um erro de preenchimento — mostrado no site com
um aviso explicando isso, pra não parecer um valor final.

## Extração (`05_Scripts/python/extrair_reajuste.py`)

Busca por **rótulo de texto exato na coluna A** (não por número de linha
fixo) — mais resistente a o Wallace inserir/remover linha na planilha
pessoal dele. Alguns rótulos se repetem entre a seção do 1° e do 2°
Reajuste (ex. "Índice IPCA em Out/2024", "Suplemento Contratual Módulo 1")
— desambiguado por **ocorrência** (1ª = seção do 1° Reajuste, 2ª = seção do
2°), preservando a ordem de cima pra baixo da planilha. Rótulos que já
trazem o número do reajuste no próprio texto (ex. "Valor do Contrato após
1° Reajuste") são únicos e não precisam de desambiguação.

`main()` gera `02_Dados_Tratados/base_reajuste_tratada.xlsx`, 4 abas:
- **Indicadores**: linha/indicador/valor, na ordem da planilha (rótulos
  repetidos preservados, não colapsados — não presumimos qual seção cada
  um "deveria" representar além da ordem real).
- **NotasFiscais**: período (Antes/Após o 1° Reajuste) + colunas da
  planilha (nota fiscal, valor, descrição, módulo, orçamento, autorização,
  aprovação, emissão, vencimento).
- **CronogramaMensal**: mês x módulo 1/2/3 + flag `apos_1_reajuste`.
- **CronogramaResumo**: tabela final (Proposta Comercial/Total
  Executado/Saldo sem Reajuste/Saldo e Valor por Módulo após 1°
  Reajuste/Valor total a executar e do contrato após 1° reajuste).

**Bug de dado na fonte, tratado**: uma Nota Fiscal (Módulo 3, Ofício
13/Fiscalização/1218) veio como texto `"R$ 58.868,35"` em vez de número —
só essa célula — convertida explicitamente (`_valor_monetario`) pra não
virar coluna com tipo misto (float + string), que quebra o Arrow no
Streamlit (mesma classe de bug já vista em Motores/outras áreas).

**Quirk de posição, tratado só na exibição**: nas 2 últimas linhas do
resumo do cronograma ("Valor total a executar após o 1° reajuste", "Valor
total do contrato após 1° reajuste."), o Wallace escreveu o valor 1 coluna
à direita do normal (coluna "Módulo 3" em vez de uma coluna de total) — a
extração preserva isso fielmente (não inventa uma coluna "Total" que a
fonte não tem), mas a tela (`secoes/reajuste.py`) rotula essas 2 células
como "Módulo 3/Total" pra não confundir com o Módulo 3 de verdade.

## Site — `03_Dashboard/contrato005/secoes/reajuste.py`

Nova aba "Reajuste" (depois de "Pagamentos"), em `contrato_app.py`. Seções:

1. **Valor do Contrato** — 3 métricas (assinatura, após 1° Reajuste, após
   2° Reajuste) + aviso sobre o 2° reajuste ainda não aplicado.
2. **Saldo por módulo** — tabela com as 5 fases (assinatura, saldo até
   08/10/25, após 1° Reajuste, saldo até 08/10/26, após 2° Reajuste).
3. **Detalhamento por reajuste** — 2 abas (1° Reajuste aplicado / 2°
   Reajuste projeção): índices IPCA, % do reajuste, suplementos por
   módulo, valor da hora de voo antes/depois.
4. **Notas fiscais consideradas** — tabela filtrável por período/módulo.
5. **Cronograma físico financeiro** — gráfico de barras empilhadas por
   módulo (2025-2029, linha vertical marcando o 1° Reajuste) + tabela
   mensal completa e o resumo Proposta Comercial x Executado, ambos em
   expander.

**Visão Geral** ganhou um 3° card no grupo "Financeiro e Fechamento"
("Reajuste" — valor do contrato após 1° reajuste + atalho pra aba
completa), atendendo o pedido "colcoa essa informação no contrato pra
saber o valor" sem duplicar toda a tela ali.

## Atualização automática (a partir de 2026-07-16)

Compartilhada pelo Wallace com a conta de serviço
(`pamals-drive-reader@pamals-drive-sync.iam.gserviceaccount.com`) no mesmo
dia — testado com `--atualizar-do-drive` na hora, funcionou de primeira.
Cadastrada em `shared/executar_atualizacao.py` (`SCRIPTS["reajuste"]`) e na
opção do `workflow_dispatch` — entra no ciclo de 2 em 2h (seg-sex, 8h-20h)
junto com as outras fontes.

## Teste manual (fora do site)

```
cd "05_Scripts/python"
python3 extrair_reajuste.py
```

Gera em `02_Dados_Tratados/base_reajuste_tratada.xlsx`. Validado em
2026-07-16: 54 indicadores, 16 notas fiscais, 57 meses de cronograma.
