# Instruções — Pagamentos

## Fonte

Planilha Google Sheets **"005/CELOG-PAMALS/2025 online"** (conta `wallacedellaney@gmail.com`), mesma lógica das emergências: sem conexão ao vivo, buscar de novo só quando pedido. Cópia baixada em:

`01_Bases_Originais/005_CELOG_2025/005_CELOG-PAMALS_2025 online.xlsx`

Aba principal: `CONTROLE DE PAGAMENTOS`
Aba complementar: `EMPENHOS`

## Estrutura da aba Controle de Pagamentos

### Dados do contrato (bloco fixo, no topo da aba)

Número Contrato, UG Executora, UG Responsável, UG Fiscalizadora, Prazo Final de Execução, Prazo Final de Vigência, Status, Valor Total do Contrato, Valor a Empenhar, Valor Empenhado, Valor Liquidado, Saldo (Valor a Faturar), Fornecedor.

### Tabela de pagamentos

A aba tem duas visões da mesma informação, com as mesmas colunas:

1. Por período/mês (ex.: FEV/25, MAR/25, ABR/25...);
2. Por módulo/orçamento (ex.: "Módulo II – Orçamento 06 (Hélice)", "Módulo III – Orçamento 17 Manuais").

Colunas:

| Coluna | Significado |
|---|---|
| Módulo | Número do módulo do contrato (1, 2 ou 3) |
| Referência | Mês (ex.: FEV/25) ou descrição do orçamento/módulo |
| Nº recibo | Número do recibo |
| Nº | Número da nota fiscal |
| Data | Data da nota/lançamento |
| Empenho | Número(s) de empenho (NE) vinculados, ou texto de observação (ex.: "Aprovado e aguardando itens") quando ainda não há empenho |
| Vencimento | Data de vencimento |
| Valor das Nfs | Valor da nota fiscal |
| Ordem de Pagamento | Número da ordem de pagamento, quando já paga |
| Faturado | Valor faturado |
| Pendente | Valor ainda pendente |

## O que extrair

* módulo (1, 2 ou 3 — é a informação mais importante para diferenciar os grupos);
* mês/referência;
* valor da nota (Valor das Nfs);
* valor faturado;
* valor pendente;
* situação (ver regra abaixo);
* datas relevantes (Data, Vencimento).

## Regra de situação do pagamento

* Se existir **Ordem de Pagamento** preenchida **com um número de ordem de verdade** (padrão `AAAANPnnnnnn`, ex.: `2026NP401058`) → **Pago**.
* Se só tiver **Faturado** preenchido, sem uma ordem de pagamento de verdade → **Faturado, aguardando pagamento**.
* Se estiver como **Pendente** → falta algo para fechar (pode ser recebimento de itens em aberto, ou é apenas uma previsão ainda não fechada — o texto da coluna `Empenho`/observação ajuda a identificar qual dos dois casos é).

**Atenção**: às vezes a coluna "Ordem de Pagamento" vem preenchida só com o
texto **"Faturado"** (sem número de ordem nenhum) — isso NÃO é uma ordem de
pagamento de verdade, é só um placeholder indicando que a nota foi faturada
mas ainda não paga. Por isso a regra confere o **formato** do valor (padrão
`AAAANPnnnnnn`), não só se a célula está preenchida — bug real visto em
2026-07-18 (Wallace: "Módulo III – Orçamento 19 GPS ... nao vi nos
pgamemtos"), onde esse lançamento (e também "JUNHO/26", no bloco mensal)
apareciam classificados como "Pago" por engano.

## Bug corrigido em 2026-07-18 — lançamento novo não aparecia nos Pagamentos

O lançamento "Módulo III – Orçamento 19 GPS" (NF 1882, empenho
2025NE001065, 26/06/2026) tinha sido acrescentado como uma linha nova
(linha 40) na planilha original, mas a extração (`extrair_pagamentos.py`)
tinha os limites do bloco "por módulo/orçamento" fixos em número de linha
(`9 a 26` pro bloco mensal, `28 a 39` pro bloco por módulo) — a linha nova
ficou fora do intervalo e nunca era lida.

**Corrigido**: os limites de cada bloco agora são descobertos
dinamicamente (`localizar_headers()` acha as 2 linhas de cabeçalho
"Referência" na planilha; `fim_do_bloco()` acha onde o último bloco
termina, procurando a primeira sequência de linhas totalmente em branco),
em vez de números fixos — assim, novas linhas que o Wallace acrescentar
no futuro (em qualquer um dos 2 blocos) entram automaticamente na próxima
extração, sem precisar mexer no código de novo.

## Aba EMPENHOS (complementar)

Cruzar pelo número de empenho: coluna `Empenho` (aba Controle de Pagamentos) ↔ coluna `NE` (aba Empenhos).

Trazer da aba Empenhos:

* saldo do empenho;
* valor empenhado;
* responsável;
* justificativa.

Salvar a lista de empenhos também como aba própria (`Empenhos`) no arquivo tratado — não só cruzada com pagamentos, para dar uma visão dedicada no dashboard.

## No dashboard

* **Resumo rápido por módulo**: 3 botões (Módulo 1/2/3); ao clicar, mostra o total de Valor das NFs/Faturado/Pendente só daquele módulo, sem precisar filtrar a tabela.
* **Empenhos**: seção própria dentro da tela de Pagamentos, com busca por número de empenho (NE) e totais de valor empenhado/saldo — escondida no deploy externo "005CELOG2025" (ver `site_005celog2025.md`).

## Situação dos pagamentos + Ordem de Pagamento/Observação (2026-07-18)

Pedido do Wallace: "tem coisa que so ta faturado, tem coisa que foi pago,
tem a ordem de pagamento e observacoes la, vamos apresentar". A regra de
`situacao_pagamento()` (Pago / Faturado, aguardando pagamento / Pendente /
Sem lançamento) já existia na extração, mas não tinha um resumo visual —
agora tem uma seção "Situação dos pagamentos" (tabela quantidade/valor por
situação + gráfico de barras horizontal) logo antes da tabela principal.
A tabela principal ganhou 2 colunas que já existiam na fonte mas não
apareciam: **Ordem de Pagamento** e **Observação**.

## Bug corrigido em 2026-07-18 — formatação de moeda (separador confuso)

Wallace: "o pedenten nos dois dasbord ta assim 40,817... parece que é 40
reais". Causa: todo valor em R$ era formatado com `f"R$ {valor:,.2f}"`
(estilo americano — vírgula pro milhar, ponto pro decimal), dando "R$
40,817.16". Lendo à brasileira (vírgula = decimal), isso parece "R$
40,82" em vez dos R$ 40.817,16 reais. Corrigido em todo o Contrato 005:
novo `formatar_moeda()`/`formatar_numero()` em
`contrato005/components/utils.py` (troca separador de milhar/decimal pro
padrão brasileiro: "R$ 40.817,16"), usado em Visão Geral, Pagamentos e
Reajuste (inclusive os índices IPCA, que tinham o mesmo problema). Gráficos
Plotly com eixo/hover em R$ (Pagamentos, Reajuste) ganharam
`fig.update_layout(separators=",.")` pelo mesmo motivo.
