# Instruções — Emergências C-98

## Fonte

Planilha Google Sheets **"Prazo das emergências - C-98"** (conta `aux.coord.c98@gmail.com`, arquivo privado — não é compartilhado por link).

Aba usada: **`Prazos das emergências`** (a primeira aba). As outras 7 abas do arquivo (Cópia de Prazos, Relatório SILOMS atual, Histórico de emergências, Atualização Vee One - Atual, Histórico de Atualizações Vee One, Banco de dados, Estatística) **não são usadas**.

Essa planilha tem histórico completo desde 2022 (~1.150 linhas, abertas e concluídas) — bem mais completa que o PDF que era usado antes.

**Sem conexão ao vivo:** a planilha é privada, então o dashboard não busca sozinho. Quando os dados mudarem no Google Sheets, peça para buscar de novo — uma cópia é baixada e salva em:

`01_Bases_Originais/Prazo_Emergencias_C98/Prazo das emergencias - C-98 (Google Sheets).xlsx`

## Extração

Ler a aba diretamente (já é uma planilha, não precisa reconstruir tabela de PDF). Aplicar 3 filtros na extração (não são só filtros de dashboard — ficam de fora do arquivo tratado):

* `ST_EMG` ≠ "Emg concluída";
* `Provedor` = "VEE ONE" exatamente (a planilha tem outros provedores — ex.: "PAMA-LS (FORA DO CONTRATO)", "ATM (PAMA-LS)", "PAMA-LS", "PAMA-SP" — que não são do Contrato 005/VEE ONE);
* `Atd/cancelada` em branco (só espaço/vazio — algumas linhas têm data preenchida mesmo sem estar como "Emg concluída", essas saem também).

Com isso, de ~1.150 linhas históricas sobram só as emergências realmente em aberto do provedor do contrato (17 na última carga).

## Colunas da aba "Prazos das emergências"

| Coluna | Significado |
|---|---|
| OM_EMG | Organização Militar / base da emergência (ex.: 313, 329, 384, 396, 419, 304, 685, 690) |
| OM | Sigla da unidade/base (ex.: BAMN, BABR, PAMA-LS, DACTA II, BABE, CLA, PAMA-SP, BANT, BACG) |
| EMERGÊNCIA | Número do processo de emergência |
| PN | Part Number da peça |
| NOMENCLATURA | Descrição da peça |
| CAT | Categoria (T / C / R) |
| MATR | Matrícula da aeronave |
| ST_EMG | Situação (valores vistos: "Providência tomada", "Aguardando solução", "Atendido parcialmente", "Expedido total", "Emg concluída" — ignorada) |
| TPEMG | **Tipo de emergência — define o prazo de atendimento (SLA) do contrato.** `AIFP` = até 6 dias corridos (144h); `IPLR` = até 10 dias corridos (240h); `ANCE` = até 30 dias corridos (conforme categoria da MMEL). AIFP e IPLR têm prazo bem mais apertado que ANCE — por isso são destacados no dashboard. |
| DT_EMG | Data de abertura da emergência |
| INFO EMG | Data da última informação/atualização |
| QT_EMG | Quantidade solicitada |
| UE | Unidade de medida (EA, BX, HD...) |
| PRAZO DE ENTREGA | Data-limite de entrega |
| DPE | Data prevista de entrega |
| Atd/cancelada | Se preenchido, indica "Atendida" ou "Cancelada"; se vazio, ainda está em aberto |
| DIAS ATRASO | Dias de atraso em relação ao prazo (negativo = ainda dentro do prazo; algumas emergências antigas, abertas desde 2022 e nunca fechadas, aparecem com milhares de dias de atraso — não é erro) |
| DIAS CORRIDOS | Dias corridos desde a abertura |
| Estoque | Indicador de disponibilidade em estoque |
| Retirado pela empresa? / Obrigatório Recibo. | Sim / Não |
| OBSERVAÇÃO COORDENADORIA / FISCAL | Texto livre com histórico de tratativas |
| OBSERVAÇÃO VEE ONE | Texto livre com histórico de tratativas do provedor |
| Provedor | Empresa/fornecedor responsável |
| AWB | Número do conhecimento aéreo (frete), quando houve envio |
| Prev Entrega | Segunda data de previsão (além da DPE) |
| Mensagem para operador | Texto livre |

## Regras de tratamento

* Datas convertidas para tipo data.
* Normalizar `ST_EMG` truncado (já vem truncado assim na própria planilha, não é problema de extração): "Providência tom" → "Providência tomada", "Aguardando solu" → "Aguardando solução", "Atendido parcia" → "Atendido parcialmente".
* `DIAS ATRASO` negativo = ainda dentro do prazo; positivo = atrasado.
* Não alterar o conteúdo das colunas de observação (texto livre), só limpar espaços/quebras indevidas.

## Filtros no dashboard

Os 3 filtros acima já reduzem a base na extração (não no dashboard). Dentro do que sobra, aeronave, situação, TPEMG e faixa de atraso ainda podem ser filtrados na tela "Emergências Abertas" (provedor já é sempre VEE ONE, então esse filtro não é necessário na tela).

Linhas com `TPEMG` = "AIFP" ou "IPLR" ficam destacadas na tabela — são as de prazo mais curto.
