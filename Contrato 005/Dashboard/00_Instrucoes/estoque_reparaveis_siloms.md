# Reparáveis pelo estoque do SILOMS (aba "Reparáveis")

Pedido do fiscal em 09/11/2026: controlar os reparáveis pelo histórico de estoque do SILOMS.
Regra: a baixa é só de consumíveis. Os reparáveis são só computados, num controle separado a partir do estoque inicial do SILOMS (ata da RMA de setembro, 13/10/2026).

## Fontes (Drive, pasta do Contrato 005)

- **Relatório de estoque calculado** (`Relatriodeestoquecalculado.xlsx`, id `1wgmK2uXg4yjrTiY4kcCO3SB8_5a-nDGb`).
  - Fica em Outros › ESTOQUE (`1Fz_sHBPrcQ0_795pngtBMTXrB9OlwAnV`), com dados de 02/09/2026.
  - Aba `levantamentoOficio`. O fiscal deixou o filtro em OM `304 - PAMALS` e setor `U0 - TSAU`.
  - Colunas: saldo em 10/02/2025, entradas e saídas desde então, estoque atual.
  - A aba `SQL` guarda a query do SILOMS. Pela cláusula HAVING, só entram os itens com saldo > 0 em 10/02/2025.
- **Estoque do dia**: `relatorio-siloms-stock-AAAAMMDD-HHMMSS.xlsx`, posto pelo fiscal no fechamento do mês.
  - A de 09/11/2026 está em Fechamento mensal/2026/10 OUTUBRO, id `1WL0f7hca75zwY_J4MJuXlg4rZ1DEF_Ia`.
  - Cabeçalho na linha 4: Projeto, PN, CFF, Nomenclatura, Unidade, Setor, Tipo de saldo (Utilizável/Reparável), Quantidade.
- **Quem é reparável**:
  - os PNs de `02_Dados_Tratados/base_reparaveis_tratada.xlsx` (OS do SILOMS);
  - os PNs com CAT R/T na planilha Devoluções (`1czUWXVjQt7fPz7GJgdPp3rsxPn_5Uck44voBsJIiRWI`, aba DEVOLUÇÃO).
- A conta de serviço não lê as pastas ESTOQUE e Auditoria. Para ler esses arquivos, baixar pelo conector do Drive.

## Como gerar

```
python3 "Contrato 005/Dashboard/05_Scripts/python/montar_aba_reparaveis_estoque.py" <estoque_calculado.xlsx> <relatorio-siloms-stock.xlsx> <saida.xlsx>
```

- **Em cima, o resumo:** uma linha por reparável com movimentação, com:
  - quanto tinha em 10/02/2025, entradas e saídas;
  - estoque calculado e conferência por fórmula;
  - estoque de hoje e diferença;
  - nº de OS e de lançamentos na planilha Devoluções.
- **Embaixo, o histórico por item:** "tinha em 10/02/2025" e, em ordem de data:
  - as OS de reparo (abertura e entrega com recibo);
  - os envios e devoluções da planilha Devoluções;
  - os totais do SILOMS.
- **Datas da planilha Devoluções:** ler com `UNFORMATTED_VALUE`. Serial é data real; texto vem como dd/mm/aa(aa) e só é lido como m/d quando o 2º campo passa de 12.

## Resultado de 09/11/2026

- 45 reparáveis do TSAU tiveram movimentação desde 10/02/2025.
- Em 23 deles o estoque de 09/11 difere do calculado, que é de 02/09. Explicar pelas movimentações de set–nov antes de cobrar.
- O arquivo gerado foi salvo em ~/Downloads/Reparaveis_TSAU_historico_2026-11-09.xlsx.
- **Pendente:** colar como aba "Reparáveis" no próprio Relatório de estoque calculado, pelo Google Planilhas na conta wallacedellaney@, que é a dona do arquivo.
- **Pendente:** rascunho à VEE ONE, com todos em cópia, encaminhando o relatório "para conhecimento", dizendo que o fiscal vai trabalhar nesse controle para os reparáveis.
  - A VEE ONE não tem acesso ao arquivo. O Wallace compartilha, ou se manda um recorte.

## Movimentos do SILOMS (09/11/2026, 15h)

- **Arquivo:** "Movimento entrada TSAU 10-02-25 a 09-11-26.xls", na pasta Fechamento mensal/2026/10 OUTUBRO/Estoque (id `1BhALptlNJwzlTTJ6ij_VMt13Blf51AHs`).
  - Tem 2.124 linhas, todas com setor destino TSAU, de 11/02/2025 a 09/11/2026.
  - Só tem as entradas. As 52 linhas com Tp "S" são ajustes internos do TSAU.
  - **Faltam as saídas do TSAU para as bases.** Pedir o relatório com setor de origem TSAU.
- **Colunas:**
  - **Coluna B (Tp):** E = entrada; S = saída.
  - **Coluna F (St):** é o status do movimento, não a categoria.
    - R = realizado: sempre tem Dt. Contábil, e é o mesmo filtro `ST_MOVIMENTO='R'` da query.
    - A = aberto; C = cancelado; E = estornado.
    - Consumíveis também aparecem com R.
  - **Coluna E (Razão):** I é a entrada de reparo; LEP = OS externa, segundo o Wallace. Vem do LEP, com "reparo/revisão geral", quase sempre com Ctrl EQP. Os outros códigos:
    - C: vem do TSEP;
    - 5: vem da CABW;
    - T: transferência de base;
    - X: vem do LEP/LLM;
    - F: ajuste.
- **Universo da aba:**
  - os reparáveis do controle de OS e da planilha Devoluções (CAT R/T);
  - mais os PNs com entrada de reparo (Razão I, St R) no TSAU.
  - Em 09/11: 171 itens, dos quais 113 não estavam no calculado (sem saldo em 10/02/2025).
- **O que o script faz com os movimentos (4º argumento, .csv ou .xls com xlrd):**
  - põe os movimentos no histórico de cada item;
  - soma as entradas por razão no resumo;
  - cria a aba "Movimentos reparáveis".
- **Entradas do calculado x movimentos:** em vários itens, as entradas do calculado não batem com os movimentos, qualquer que seja a data de corte. Para as entradas, usar os movimentos.

## Saídas (09/11/2026, 16h)

- **Arquivo:** "movimentosEstoque.xls", na mesma pasta Estoque (id `1KvXJIeza6X-IZAOPzWJVj6GA98VHJVMQ`).
  - Tem 3.752 linhas, de todos os projetos, e quase todas com Ctrl EQP.
  - **Período: de 10/02/2026 a 09/11/2026.** Faltam as saídas de 10/02/2025 a 09/02/2026.
- **O que o script usa:**
  - filtra Prj U8 (313 linhas);
  - saídas com origem PAMALS/TSAU (166 linhas, em geral razão T, para as bases);
  - entradas com destino TSAU, sem repetir o nº do Movimento.
  - 5º argumento: `[saidas.csv|.xls]`.
- **Resultado:**
  - 233 reparáveis com movimentação;
  - 216 eventos de saída e 438 retornos de OS externa no histórico.
  - O histórico fecha o ciclo de cada SN: OS aberta → retorno da OS externa (LEP) → saída do TSAU para a base.

## Saídas completas (09/11/2026, 16h30)

- **Arquivo:** "movimentosEstoque (2).xls", na pasta Estoque (id `1sR1zcZNlIaIQFVMiGmSD84x_xEJecPxX`).
  - Tem 20 MB e 40.902 linhas, de 10/02/2025 a 09/11/2026, com todos os tipos de Ctrl.
  - O conector do Drive só baixa até 10 MB. Baixar pela conta de serviço: `shared.drive_sync.baixar_arquivo(id)` devolve os bytes.
- **Filtros:**
  - Prj U8 e origem PAMALS/TSAU: 3.210 saídas.
  - Só os PNs com Ctrl EQP entram no universo, para não puxar consumíveis.
- **Conferência por item:** Tinha em 10/02/2025 + entradas − saídas, comparado com o estoque de hoje.
  - Fica nas colunas T e U do resumo, por fórmula.
  - Em 09/11: **208 de 239 fecham**.
  - Dos 31 que não fecham, 21 estão fora do calculado (saldo inicial tomado como 0).
  - Causas prováveis: PN parecido com outro CFF ou sufixo (30-182 x 30-182A), movimento entre subsetores do TSAU, ou saldo reparável no estoque de hoje.

## Onde fica: planilha Devoluções (09/11/2026, 17h)

Pedido do Wallace: "quero tudo junto lá no Devoluções". O controle fica nas abas "Reparáveis – *" da planilha Devoluções, sheetIds 891093601 a 891093604.

**Como publicar:**

```
python3 "Contrato 005/Dashboard/05_Scripts/python/publicar_reparaveis_devolucoes.py" <xlsx do montar> <relatorio-siloms-stock.xlsx> <entradas.csv> <saidas.csv>
```

O script grava pela conta de serviço e reescreve as quatro abas inteiras.

**As quatro abas:**
- **Saldos:** um item por linha, com os itens que não fecham no topo.
  - Saldo recalculado = inicial + entradas − saídas, por fórmula.
  - Situação: Fecha, A explicar ou Justificada.
  - A coluna L ("Justificativa", amarela) é preenchida à mão.
  - Link "ver" leva ao histórico do item.
- **Histórico:** formato longo, um evento por linha, filtrável por PN.
  - Cada PN começa no saldo inicial e termina no saldo SILOMS de hoje.
  - Cores: azul para os saldos, laranja para as saídas, verde para o retorno de OS externa, lilás para a OS.
- **Evidências:** só os itens que não fecham, com a causa provável calculada sozinha. Possíveis causas:
  - fora do calculado;
  - PN parecido no estoque;
  - saldo do tipo Reparável;
  - movimento não realizado;
  - subsetor do TSAU.
  - A coluna H é preenchida à mão.
- **Mov. SILOMS:** todos os movimentos do U8 desses PNs.
  - "Efeito no TSAU" vale +q nas entradas R e −q nas saídas R.

**Cuidados:**
- **Antes de republicar,** salvar o que estiver preenchido em Saldos!L e Evidências!H. O script não preserva essas colunas.
- **Conferir a numeração das linhas:** em 09/11 nada estava preenchido. O backup das abas antigas está no scratchpad da sessão.
- **Aba RMA:** foi arrumada (cabeçalho, congelamento, datas dd/mm/aaaa).
- **Cópias antigas no Relatório de estoque calculado:** as abas "Reparáveis" e "Movimentos reparáveis" ficaram desatualizadas. A fonte agora é a Devoluções.

## O que mais foi feito em 09/11/2026 (fechamento de outubro)

- **RMA de outubro conferida:**
  - reparáveis pela OS (`extrair_reparaveis_rma`: 684 OS, 12 entregues, 0 condenadas);
  - auditoria v6 dos consumíveis;
  - RMA Finalizada e auditoria na pasta 10 OUTUBRO.
- **Planilha Devoluções:**
  - observações do fiscal na coluna U, no formato "Fiscal DD/MM/AAAA: ...";
  - status padronizado na W ("OK", "Reparável – computado", "Reparável – pendente");
  - o recibo 598/FAB/26 não está no Drive.
- **Rascunhos no Gmail:**
  - à Desirée, com toda a VEE ONE em cópia, sobre a RMA de outubro;
  - à 3S Islania, sobre os reparáveis em AGD INSPEÇÃO do Controle GERAL, com retorno até 13/11.
- **Atualizados:** vencimentos, diagonal e MAPEM de outubro, e o site inteiro.
