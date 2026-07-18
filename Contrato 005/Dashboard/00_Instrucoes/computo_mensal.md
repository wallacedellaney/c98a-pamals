# Instruções — Cômputo Mensal (aba 1.2 da Pré-RMA)

## Objetivo

Calcular automaticamente, a partir dos registros de emergências já existentes no site, uma **prévia** da matriz aeronave x dia (1 = montada, 0 = desmontada) usada na aba **"1.2 - Média Mensal de Aeronaves Montadas (MMAM) e Índice Final de Desempenho (IFD)"** da planilha pessoal do Wallace **"Pré RMA C-98 \<Mês\>-\<AA\>.xlsx"** (Google Drive, pasta "Fechamentos Mensais" → "Pré-RMA").

**Essa planilha é pessoal do Wallace, não está compartilhada com a conta de serviço da automação** — por isso não tem busca automática do Drive aqui (diferente das outras fontes). Por enquanto, o resultado só aparece no site (Contrato 005 → Fechamento Mensal → Cômputo Mensal) — não escreve na planilha do Google Sheets (decisão do Wallace em 2026-07-08; pode mudar depois).

## Regras (definidas pelo Wallace em 2026-07-08)

1. **Só entram AIFP e IPLR** — nenhum outro tipo de emergência (ANCE etc.) afeta o cômputo.
2. **Só nega (0) quando as duas condições valem ao mesmo tempo**: existe uma AIFP/IPLR aberta **e** não existe estoque disponível (`Estoque` = "Não"). Com estoque disponível ("Sim"), não nega.
3. **Considera qualquer AIFP/IPLR que impactou o mês de referência** — aberta antes e continuando, aberta durante, ou fechada durante — não só o que abriu no mês.
4. **Início da negativação**: próximo dia útil (só pula sábado/domingo por enquanto, sem feriados — decisão do Wallace) depois da **data da informação** (`INFO EMG`, não a data de abertura).
5. **Fim da negativação**: no **dia do cancelamento/conclusão em si, a aeronave já volta a ser 1** — o último dia negativado é o dia anterior à data de cancelamento. Se ainda não tiver cancelamento, mantém 0 até o último dia já decorrido do mês.
6. **Estoque em branco**: não decide sozinho — vira inconsistência ("revisar manualmente"), não entra na negativação automática. Confirmado que isso não afetou julho/2026 na prática (nenhuma AIFP/IPLR ainda aberta tinha estoque em branco).
7. **Classificação de aeronave** (dentro do contrato / fora do contrato listada / sem condições) vem do RAC (`Coordenadoria/02_Dados_Tratados/base_rac_tratada.xlsx`) — não duplicada aqui. Só as "dentro do contrato" são pontuadas; as "fora do contrato" (2726, 2730, 2732, 2734) aparecem listadas sem pontuação, igual na planilha oficial; as "sem condições" (2701, 2706, 2724) nem aparecem.
8. **Comentário da Coordenadoria indicando cancelamento (2026-07-17)**: se a
   observação da Coordenadoria (`obs_coordenadoria_fiscal`) contém termos como
   "cancel" (Cancelado/Cancelada/Cancelamento, pelo operador, pelo
   suprimentista, duplicidade etc. — qualquer motivo) ou "não é/será/ser mais
   necessário"/"não necessária", a emergência **inteira não negativa nenhum
   dia** — tratada como se a aeronave estivesse montada o período todo,
   **mesmo os dias que já tinham negativado antes de uma eventual data
   oficial de cancelamento chegar**. Pedido do Wallace: "sempre que tiver
   algum comentario escrito nas observacoes da coordenadoria: cancelado pelo
   operador, cancelado pelo suprimentista, demanda nao necessaria mais e
   outras variaveis nao computar, contar como montada" — inicialmente só
   aplicado quando faltava a data oficial, depois confirmado com o exemplo
   real da emergência **329260019180** (FAB 2709, "OBS DO CANCELAMENTO
   SOLICITADO PELO SUPRIMENTISTA DO GLOG BR") que deve desconsiderar o
   período **inteiro**, mesmo já tendo data oficial de cancelamento (16/07) —
   os 8 dias negativados antes dela (08 a 15/07) também viram "montada".
   Achado nesse mesmo exemplo: o termo original era `"cancelad"`, que não
   pega "CANCELAMENTO" (tem "m" onde "cancelad" espera "d") — trocado pra
   `"cancel"` (sem sufixo), que cobre Cancelado/Cancelada/Cancelamento.
   **Silencioso** — a pedido do Wallace ("nao quero nem que aparece la no
   fechamento mensal"), não vira nota em "inconsistências" nem aparece em
   nenhum outro lugar da tela — só deixa de negativar, sem deixar rastro
   visível na interface.

## Implementação

`Contrato 005/Dashboard/05_Scripts/python/calcular_computo_mensal.py`:
- `calcular_mes(ano, mes)` — lê `historico_completo_emergencias.xlsx` (ver `emergencias.md`) + a classificação do RAC, aplica as regras acima, salva em `02_Dados_Tratados/computo_mensal/`:
  - `<AAAA>-<MM>_matriz.csv` — matricula, dia, montada (0/1).
  - `<AAAA>-<MM>_motivos.csv` — uma linha por período de negativação, com toda a rastreabilidade pedida (emergência, tipo, datas, estoque).
  - `<AAAA>-<MM>_resumo.json` — MMAM prévia, aeronaves pontuadas/fora, inconsistências.
- `carregar_mes(ano, mes)` — lê de volta os 3 arquivos.

Tela: `03_Dashboard/contrato005/secoes/fechamento_mensal.py`, aba "Cômputo Mensal" — botão "Recalcular" (roda `calcular_mes` na hora), métricas (MMAM prévia, aeronaves pontuadas, dias já decorridos/total do mês), gráfico de evolução diária, matriz colorida (verde/vermelho) mostrando o **mês inteiro** (1 ao último dia, igual à planilha oficial — dias ainda não decorridos ficam em branco), com sábado/domingo destacados em cinza no cabeçalho e no fundo das células vazias, valores sem casa decimal, colunas estreitas pra caber o mês inteiro sem rolar. **Clicar numa célula** mostra uma caixa com o motivo (número da emergência, tipo, datas, período negativado) ou confirma que a aeronave ficou montada naquele dia. Tabela de justificativa completa embaixo, exportação em CSV.

## Validação (julho/2026, calculado em 2026-07-08)

Comparado célula a célula com a planilha oficial (8 dias já decorridos, 23 aeronaves = 184 células): **bateu em 183 de 184** (99,5%). A única aeronave onde a prévia divergiu foi a **2739** (planilha oficial marca o dia 8 como negativado; não foi encontrado nenhum registro de emergência AIFP/IPLR que explique isso — provavelmente um ajuste manual feito direto na planilha, sem uma emergência formal por trás). MMAM prévia calculada: 97,28% (oficial, com o ajuste manual do 2739: 96,74%).

## Seletor de mês (compartilhado por toda a página Fechamento Mensal)

O seletor de "Mês de referência" no topo de `fechamento_mensal.py::render()`
vale pras 4 abas (Cômputo Mensal, Atrasos, Apresentação RMA, Ata de Reunião).
**2026-07-14, correção**: o padrão selecionado estava fixo em junho/2026
(`pd.Period("2026-06", ...)`, hardcoded) — Wallace: "é para sempre aparecer
no mes atual". Trocado pra `pd.Timestamp.now().to_period("M")` em
`_opcoes_mes()` e `render()`, então o mês atual real sempre aparece
selecionado (e sempre aparece na lista de opções, mesmo sem nenhuma
emergência registrada nele ainda).

## PN e Nomenclatura na justificativa (2026-07-16)

Pedido do Wallace: "no fechamento mensal do lado da emergencia trazer o PN
e depois a nomenclatura em tudo que tiver ... justificativa". O motivo da
negativação (`calcular_mes` → `_motivos.csv`) já vinha com o número da
emergência, mas não o PN/Nomenclatura do item — a fonte
(`historico_completo_emergencias.xlsx`) sempre teve essas 2 colunas, só
não estavam sendo copiadas pro cômputo. Adicionadas logo depois de
"Emergência" (PN primeiro, Nomenclatura depois — ordem pedida) em:
o card de motivo ao clicar numa célula da matriz, a tabela "Justificativa
das negativações", e as tabelas/detalhe de "Atrasos" (situação atual,
entregas do mês). Meses já calculados precisaram ser recalculados uma vez
pra essas 2 colunas aparecerem retroativamente (`calcular_mes` de novo
pra cada mês em cache).

## Aviso de prévia (2026-07-18)

Pedido do Wallace: "escreve que pode ter diferenca do real por se tratar
do computo automatico e desconsiderando ajuste manuais, e explica la como
é calculado, tanto no fechamento mensal tanto na analise do periodo".
Texto único (`AVISO_MMAM_PREVIA` em `contrato005/components/utils.py`,
compartilhado pra não duplicar), mostrado em `st.info()` logo abaixo do
card "MMAM prévia" em 2 lugares: Fechamento Mensal → Cômputo Mensal, e
Análise de Período → seção "Desempenho da empresa". Explica a regra de
cálculo (dia útil após data da informação até cancelamento/conclusão,
sem estoque) e avisa que não considera ajustes manuais feitos direto na
planilha oficial (Pré-RMA) nem feriados.

## Matriz — % por dia e aeronaves fora do contrato (2026-07-17)

Pedido do Wallace: "coloca a porcetnagem em baixo de cada dia" + "as
aeronaves fora do contrato vc coloca la [na matriz], ajeitar ... coloca em
baixo, sem preencher nada". A matriz aeronave x dia ganhou 2 tipos de linha
extra, sempre no final:

- **"% Montadas"** — a mesma % usada no gráfico de evolução acima, uma por
  dia, em negrito com uma borda separando do resto.
- **Uma linha por aeronave fora do contrato** (`aeronaves_fora_listadas`) —
  todas as células em branco (sem 0/1, sem cor de fundo), só a matrícula
  aparece na linha — não pontuam, só ficam visíveis pra referência (antes
  só apareciam citadas numa legenda de texto embaixo da matriz).

Nenhuma das duas linhas responde ao clique (não tem "motivo de
negativação" — clicar nelas não faz nada).

## Limitações conhecidas

- **A planilha "Pré RMA" não é buscada automaticamente** — só o `historico_completo_emergencias.xlsx` que alimenta o cálculo.
- **O cálculo em si (`calcular_mes`) já roda sozinho** (a partir de 2026-07-09) — toda vez que a atualização automática de Emergências roda (seg-sex ~12h, GitHub e Mac), `extrair_emergencias.atualizar_do_drive()` também chama `calcular_mes(ano, mes)` pro mês atual, logo depois de regenerar o histórico completo. O botão "Recalcular" no site continua existindo pra rodar na hora, se quiser.
- **Sem feriados no cálculo de dia útil** — só pula sábado/domingo. Se isso importar, avisar o Wallace pra decidir se vale manter uma lista de feriados.
- **Não escreve na Pré-RMA real** — é só uma conferência no site. Pra automatizar a escrita de verdade, precisaria: (1) compartilhar o arquivo com a conta de serviço como Editor, e (2) construir a escrita via API do Google Sheets (mais arriscado — pode mexer em célula errada, tem que preservar fórmulas).
- **Ajustes manuais na planilha oficial não são capturados** — como visto no caso do 2739, alguém pode marcar uma aeronave como desmontada na planilha real sem que exista uma emergência formal registrada no site. A prévia sempre vai refletir só o que está nos registros de emergência.
