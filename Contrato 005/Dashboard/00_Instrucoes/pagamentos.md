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

* Se existir **Ordem de Pagamento** preenchida → **Pago**.
* Se só tiver **Faturado** preenchido, sem Ordem de Pagamento → **Faturado, aguardando pagamento**.
* Se estiver como **Pendente** → falta algo para fechar (pode ser recebimento de itens em aberto, ou é apenas uma previsão ainda não fechada — o texto da coluna `Empenho`/observação ajuda a identificar qual dos dois casos é).

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
