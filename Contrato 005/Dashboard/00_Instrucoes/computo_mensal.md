# Instruções — Cômputo Mensal (aba 1.2 da Pré-RNA)

## Objetivo

Calcular automaticamente, a partir dos registros de emergências já existentes no site, uma **prévia** da matriz aeronave x dia (1 = montada, 0 = desmontada) usada na aba **"1.2 - Média Mensal de Aeronaves Montadas (MMAM) e Índice Final de Desempenho (IFD)"** da planilha pessoal do Wallace **"Pré RMA C-98 \<Mês\>-\<AA\>.xlsx"** (Google Drive, pasta "Fechamentos Mensais" → "Pré-RNA").

**Essa planilha é pessoal do Wallace, não está compartilhada com a conta de serviço da automação** — por isso não tem busca automática do Drive aqui (diferente das outras fontes). Por enquanto, o resultado só aparece no site (Contrato 005 → Fechamento Mensal → Cômputo Mensal) — não escreve na planilha do Google Sheets (decisão do Wallace em 2026-07-08; pode mudar depois).

## Regras (definidas pelo Wallace em 2026-07-08)

1. **Só entram AIFP e IPLR** — nenhum outro tipo de emergência (ANCE etc.) afeta o cômputo.
2. **Só nega (0) quando as duas condições valem ao mesmo tempo**: existe uma AIFP/IPLR aberta **e** não existe estoque disponível (`Estoque` = "Não"). Com estoque disponível ("Sim"), não nega.
3. **Considera qualquer AIFP/IPLR que impactou o mês de referência** — aberta antes e continuando, aberta durante, ou fechada durante — não só o que abriu no mês.
4. **Início da negativação**: próximo dia útil (só pula sábado/domingo por enquanto, sem feriados — decisão do Wallace) depois da **data da informação** (`INFO EMG`, não a data de abertura).
5. **Fim da negativação**: no **dia do cancelamento/conclusão em si, a aeronave já volta a ser 1** — o último dia negativado é o dia anterior à data de cancelamento. Se ainda não tiver cancelamento, mantém 0 até o último dia já decorrido do mês.
6. **Estoque em branco**: não decide sozinho — vira inconsistência ("revisar manualmente"), não entra na negativação automática. Confirmado que isso não afetou julho/2026 na prática (nenhuma AIFP/IPLR ainda aberta tinha estoque em branco).
7. **Classificação de aeronave** (dentro do contrato / fora do contrato listada / sem condições) vem do RAC (`Coordenadoria/02_Dados_Tratados/base_rac_tratada.xlsx`) — não duplicada aqui. Só as "dentro do contrato" são pontuadas; as "fora do contrato" (2726, 2730, 2732, 2734) aparecem listadas sem pontuação, igual na planilha oficial; as "sem condições" (2701, 2706, 2724) nem aparecem.

## Implementação

`Contrato 005/Dashboard/05_Scripts/python/calcular_computo_mensal.py`:
- `calcular_mes(ano, mes)` — lê `historico_completo_emergencias.xlsx` (ver `emergencias.md`) + a classificação do RAC, aplica as regras acima, salva em `02_Dados_Tratados/computo_mensal/`:
  - `<AAAA>-<MM>_matriz.csv` — matricula, dia, montada (0/1).
  - `<AAAA>-<MM>_motivos.csv` — uma linha por período de negativação, com toda a rastreabilidade pedida (emergência, tipo, datas, estoque).
  - `<AAAA>-<MM>_resumo.json` — MMAM prévia, aeronaves pontuadas/fora, inconsistências.
- `carregar_mes(ano, mes)` — lê de volta os 3 arquivos.

Tela: `03_Dashboard/contrato005/secoes/fechamento_mensal.py`, aba "Cômputo Mensal" — botão "Recalcular" (roda `calcular_mes` na hora), métricas (MMAM prévia, aeronaves pontuadas, dias já decorridos/total do mês), gráfico de evolução diária, matriz colorida (verde/vermelho) mostrando o **mês inteiro** (1 ao último dia, igual à planilha oficial — dias ainda não decorridos ficam em branco), com sábado/domingo destacados em cinza no cabeçalho e no fundo das células vazias, tabela de justificativa, exportação em CSV.

## Validação (julho/2026, calculado em 2026-07-08)

Comparado célula a célula com a planilha oficial (8 dias já decorridos, 23 aeronaves = 184 células): **bateu em 183 de 184** (99,5%). A única aeronave onde a prévia divergiu foi a **2739** (planilha oficial marca o dia 8 como negativado; não foi encontrado nenhum registro de emergência AIFP/IPLR que explique isso — provavelmente um ajuste manual feito direto na planilha, sem uma emergência formal por trás). MMAM prévia calculada: 97,28% (oficial, com o ajuste manual do 2739: 96,74%).

## Limitações conhecidas

- **A planilha "Pré RMA" não é buscada automaticamente** — o `historico_completo_emergencias.xlsx` que alimenta o cálculo, esse sim, já atualiza sozinho (junto da atualização automática de Emergências, seg-sex ~12h, tanto no GitHub quanto no Mac — ver `atualizacoes.md`). Mas o cálculo do Cômputo Mensal em si (`calcular_mes`) precisa ser rodado — pelo botão "Recalcular" no site, por enquanto — não está agendado.
- **Sem feriados no cálculo de dia útil** — só pula sábado/domingo. Se isso importar, avisar o Wallace pra decidir se vale manter uma lista de feriados.
- **Não escreve na Pré-RNA real** — é só uma conferência no site. Pra automatizar a escrita de verdade, precisaria: (1) compartilhar o arquivo com a conta de serviço como Editor, e (2) construir a escrita via API do Google Sheets (mais arriscado — pode mexer em célula errada, tem que preservar fórmulas).
- **Ajustes manuais na planilha oficial não são capturados** — como visto no caso do 2739, alguém pode marcar uma aeronave como desmontada na planilha real sem que exista uma emergência formal registrada no site. A prévia sempre vai refletir só o que está nos registros de emergência.
