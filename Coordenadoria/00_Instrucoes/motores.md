# Motores

Pedido do Wallace em 2026-07-14: "busca essa planilha pra mim MOTORES C-98"
→ "cria no nosso site" (dashboard "Motores" da Coordenadoria, não uma pasta
no Drive) → escopo confirmado: "SILOMS (situação atual), Diagonal Nova
(projeção TBO), OS (ordens de serviço), Hélice, entao, quero q seja bem
completo, ja vi que tem comentarios dentro da caixas de tbo, hsi. vamos usar
essas informacoes tb".

## Fonte

Planilha **pessoal do Wallace** "MOTORES C-98" (Google Sheets, dono
`fred_o_m@hotmail.com`, `1UJDXA6jG4va51Tpnjd6DrV1kqPMnbY9w-TYlh8Ub0rM`) —
tem **15 abas**, das quais **4 foram escolhidas** pro dashboard (as outras
são cenário/simulação — CENARIO 2027 10%, CENÁRIO SIGADAER, Cenários,
Diagonal antiga — ou rascunho/instrução — INSTRUÇÕES, SLIDES, Página6/7,
Historico, motores totais):

- **SILOMS** → aba "Situacao" no arquivo tratado. Situação atual de cada
  motor (por OM/PN/SN) puxada do sistema SILOMS — TSO/TSN, %TBO voada,
  condição (APL/OS/REPARA/RECOLH/REMOV).
- **hélice** → aba "Helice". Mesma estrutura da SILOMS, pra hélices.
- **Diagonal Nova** → aba "Diagonal". Projeção mês a mês (2025-2030) de
  quando cada motor vai bater TBO/HSI — a versão "Diagonal" (mais antiga,
  12/05/2025) não foi usada, o Wallace confirmou só a "Nova".
- **OS** → aba "OS". Ordens de serviço de motor em andamento.

**Compartilhada com a conta de serviço em 2026-07-15** ("ja compartilhei a
planilha") — `extrair_motores.py::atualizar_do_drive()` busca direto do
Drive, `DRIVE_FILE_ID = "1UJDXA6jG4va51Tpnjd6DrV1kqPMnbY9w-TYlh8Ub0rM"`.
Entrou na automação de 2 em 2h (`shared/executar_atualizacao.py` +
GitHub Actions + launchd, ver `CLAUDE.md` raiz) — antes disso era só
reprocessamento local.

## Estrutura real da fonte (cada aba é diferente)

Cada uma das abas SILOMS/hélice tem um **layout de colunas diferente**
(ex.: SILOMS tem "TBO" antes de "Matr.ANV", hélice tem a ordem invertida) —
mapeadas por posição em `extrair_motores.py` (`COL_SITUACAO`/`COL_HELICE`),
não por nome (a fonte repete o rótulo "DATA" 3 vezes com significados
diferentes, então mapear por nome não funciona).

**3 colunas "DATA" duplicadas em SILOMS/hélice** — significado exato de
cada uma **não confirmado com o Wallace**. Nomeadas defensivamente:
`data_1`, `data_2` (as 2 primeiras) e `data_doc` (a que acompanha
`numero_doc`, essa com significado claro — data do documento de
recolhimento/OS). Se o Wallace confirmar o que são `data_1`/`data_2`,
atualizar aqui e os nomes de coluna.

**OS tem sub-tabelas repetidas** — a aba tem um bloco por unidade
executante (cada um com seu próprio cabeçalho "Unidade/Setor executante:
..." + repetição da linha de cabeçalho de coluna no meio da planilha).
`_extrair_os` filtra isso exigindo que a coluna "OS" seja um número —
qualquer linha de cabeçalho repetido tem texto ali, é descartada como
estrutura (não conta como inconsistência).

**PN/SN/Matrícula/Nº Doc às vezes vêm como número puro, às vezes como texto
alfanumérico**, na mesma coluna — força string sempre via `_texto_id()`,
sem ".0" no final, senão quebra a serialização Arrow do `st.dataframe` e a
ordenação dos filtros (mesmo bug já visto em outras áreas, ver
`ordenar_unicos` no Contrato 005).

## Diagonal Nova — grade de eventos + comentários de célula

7 colunas de metadado (Serial, ANV, TSO, Hr disp, Voo mensal, HR até fim do
ano da ANV, Mês disp) + 72 colunas de mês (JAN-DEZ × 2025-2030) + uma
coluna final "Observações". Cada célula de mês pode conter um marcador —
mas a grade real **mistura tipos de marcador na mesma coluna**:

- `TBO`/`TBO*`/`HSI` — eventos de manutenção de verdade (só esses entram
  nos indicadores/gráfico do dashboard).
- `X`, `1` — algum tipo de marcador binário (significado exato **não
  confirmado** — aparecem 77 e 65 vezes respectivamente).
- Números soltos (ex.: `57.1`, `22.5`) e texto livre (ex.: "Recolhido por
  pane 12/06. Aguardando DPE do PAMASP") — anotações sem estrutura fixa.

Todos os tipos aparecem na **tabela completa** da aba Diagonal do
dashboard (coluna "Marcador" — só dentro do expander "Tabela completa"),
mas só TBO/HSI/TBO\* contam nos cards e na linha do tempo — pra não
inventar significado pros outros marcadores.

**Linha do tempo (2026-07-14, redesenho executivo — pedido original do
Wallace era uma matriz Serial × Mês, depois refeito como linha do tempo
pra bater com a spec de reorganização executiva da página; 2026-07-15,
virou Gantt — "mesmo padrao da diagoanl [de manutenção]" — barra de 1 mês
por evento, `y="SN {serial} — FAB {ANV}"`, cor por TBO (âmbar) / HSI
(ciano), listrado (`pattern_shape`) na barra que tem comentário anexado —
passar o mouse mostra o comentário, a unidade e o tipo de evento. Linha
vertical tracejada marca "hoje". 4 cards acima classificam os eventos por
proximidade (Vencido, Próximos 90/180/365 dias).

**Janela sempre de 2 anos (2026-07-15)** — Wallace: "vamos deixar sempre 2
anos na linha do tempo de tbo e hsi". Antes era um intervalo fixo
(2026-2030); agora é sempre **ano atual + próximo** (`datetime.now().year`
até `+1`), rolando sozinho conforme os anos passam — não precisa mexer no
código de novo ano que vier.

**Comentários de célula** (pedido do Wallace: "ja vi que tem comentarios
dentro da caixas de tbo, hsi. vamos usar essas informacoes tb") — a
planilha tem 59 comentários no total (25 na Diagonal Nova), texto livre com
número de AT (Autorização Técnica), horas restantes, observações
operacionais. Lidos via `cell.comment.text` (openpyxl) e trazidos na coluna
"comentario"/"Comentário" — **só existem no arquivo `.xlsx` exportado do
Google Sheets** (comentários simples/"notas", não comentários encadeados
modernos — se o Wallace um dia migrar pra comentário encadeado do Sheets, a
exportação pra xlsx pode parar de trazer o texto, checar de novo nesse
caso).

## Dashboard

`03_Dashboard/coordenadoria/secoes/motores.py`. **Redesenho executivo em
2026-07-14** (spec detalhada do Wallace) — cabeçalho enxuto (título, fonte,
última atualização, botão "Atualizar dados", sem duplicar a navegação
principal do rodapé) + **4 subabas**:

- **Visão Geral** / **Hélices** (mesma função `_aba_visao_geral`,
  parametrizada): 5 cards (total, aplicados, em manutenção/outra condição,
  próximos do TBO/HSI, vencidos) coloridos por **faixa de risco** —
  `_faixa_risco(pct_tbo_voada)`: Vencido (vermelho, ≥100%), Atenção
  (amarelo, 80-99%), Normal (verde, <80%); barras horizontais por condição
  (no lugar da rosca); lista "⚠️ Atenção imediata" com os motores mais
  críticos; filtros numa linha só (OM, Condição, Situação/faixa, busca);
  tabela completa **dentro de um expander** (`filtro_colunas` +
  exportação CSV); evolução (histórico) também num expander.
- **Diagonal TBO/HSI**: 4 cards (Vencidos, Próximos 90/180/365 dias — a
  partir de `dias_ate = (periodo - hoje).days`, sem depender de status
  externo); **linha do tempo no mesmo padrão da Diagonal de Manutenção**
  (`px.timeline`/Gantt: barra de 1 mês por evento, `y=SN — FAB ANV`, cor
  por TBO/HSI, **listrado** (`pattern_shape`) na barra que tem comentário
  anexado — mesmo mecanismo visual usado lá pra "Real x Programado" —,
  linha vertical tracejada em "hoje", comentário/unidade no hover) de 2026
  a 2030; filtros numa linha só (Aeronave, Unidade — cruzada com a
  Situação via serial=SN —, Ano, Evento, só com comentário); marcações
  fora de TBO/HSI/TBO\* (X/1/números/texto livre) só aparecem dentro do
  expander "Tabela completa", nunca na visão inicial.
- **Ordens de Serviço**: status traduzido (`NOMES_STATUS_OS`: INT→
  "Internado (em conserto)", REC→"Recebida", SOL→"Solicitada" — melhor
  interpretação, não confirmada literalmente com o Wallace); 5 cards
  (total, internadas, recebidas, atrasadas — `data_fim_prev < hoje` sem
  `data_fim_real` —, motores distintos); gráfico por Status já mostra o
  tempo médio no status (dias) no rótulo da barra; tabela com datas
  dd/mm/aaaa e colunas principais primeiro (`COLUNAS_OS_PRINCIPAIS`).

**Padronização geral** (`_preparar_tabela`, `_fmt_data`/`_fmt_horas`/
`_fmt_pct`/`_encurtar_fabricante`): "None"/NaN vira "—" em qualquer tabela
exibida; horas formatadas com "h" (ex.: "1.234 h"); datas sempre
dd/mm/aaaa; nome de fabricante encurtado (tira o código CFF do início,
trunca em ~28 caracteres); qualquer coluna de texto livre com valor
numérico solto (ex.: "motivo" com `315.0`) é normalizada pra string antes
do `fillna` — senão quebra a serialização Arrow do `st.dataframe` (mesmo
bug de tipo misto já visto em outras áreas, ver `ordenar_unicos` no
Contrato 005).

**"Previsão" (perdas TBO/HSI/PNP, produção, capacidade planejada) ficou de
fora** — precisa de outras abas da planilha original (CENARIO 2027 10%,
CENÁRIO SIGADAER, Cenários) ainda não extraídas; decisão confirmada com o
Wallace em 2026-07-14 ("Só as 4 abas agora").

Botão "🔄 Atualizar dados" no site reprocessa a cópia local
(`coordenadoria.utils.atualizar_dados_motores`) — mesmo padrão de
RAC/Disponibilidade/Vencimentos TMOT: quem busca a versão nova do Drive é
só o ciclo automático de 2 em 2h (`atualizar_do_drive()`, ver seção
"Fonte" acima), o botão do site é só pra reprocessar na hora sem esperar o
próximo ciclo.

## Histórico / "barra temporal" (2026-07-14)

Pedido do Wallace: "vai ter historico pq vai ter atualizacao diaria". Snapshot
diário da **Situação** (motores, 1 linha por SN) em
`02_Dados_Tratados/historico_motores_situacao.csv`, gravado dentro de
`main()` (roda toda vez que a extração roda — botão "Atualizar dados" do
site ou pedido na conversa) — idempotente, substitui só as linhas de hoje se
rodar de novo no mesmo dia. Só a Situação tem histórico por enquanto (Hélice/
OS/Diagonal não — Diagonal já é uma projeção futura, não teria sentido
"evoluir no tempo" do mesmo jeito).

Componente `coordenadoria/components/evolucao.py` — **primeiro uso desse
padrão na Coordenadoria** (mesmo componente já usado em MTA/TPJL, na área
Projetos; duplicado aqui em vez de importado de lá, sem import entre
pacotes de áreas). Slider de datas + novos/removidos/alterados, exibido no
fim da aba "Situação (motores)". Só existe história a partir de 2026-07-14
(dia em que a gravação começou).

## Aba DiagonalMeta (2026-07-15) — metadados de planejamento por motor

`_extrair_diagonal_metadados()` — 1 linha por serial com as colunas de
planejamento das 7 primeiras colunas da Diagonal Nova (que a extração de
eventos, acima, ignorava): TSO, **Hr disponível** (horas até o próximo
TBO/HSI), **Voo mensal** (média mensal de horas de voo assumida na
planilha), Hr até fim do ano da ANV, **Mês disponível** (= Hr disponível ÷
Voo mensal — confirmado batendo com a conta). Usada pela Diagonal de
Manutenção pra mostrar o motor de cada aeronave e simular "e se eu voar
mais/menos por mês" — ver `00_Instrucoes/diagonal_manutencao.md`, seção
"Motores por aeronave + simulação de horas de voo". "#N/A" (fórmula do
Sheets) e ANV vazio (`False`) viram `None`.

Os eventos TBO/HSI/TBO\* (não os metadados) também aparecem direto, como
barra de verdade, no Gantt da Diagonal de Manutenção — ver
`00_Instrucoes/diagonal_manutencao.md`, seção "Eventos TBO/HSI da planilha
de Motores, direto no Gantt".

## Histórico da Diagonal (2026-07-15)

Igual ao histórico da Situação, mas pros eventos TBO/HSI/TBO\* projetados —
`_registrar_historico_diagonal()` grava 1 snapshot por dia em
`historico_motores_diagonal.csv` (chave: serial+ano+mês), exibido num
expander "🕐 Evolução" na aba "Diagonal TBO/HSI" do dashboard de Motores.
Motivo: a projeção pode mudar de um dia pro outro (mês empurrado, virou
HSI em vez de TBO, comentário novo) — pedido do Wallace: "mostrar na
diagonal dos motores tb, um historico de evolucao".

## Bug corrigido em 2026-07-23 — coluna "Motivo" quebrava o Arrow (int puro)

Achado numa checagem geral do site (pedido do Wallace: "sobe e documenta
tudo, faz um check em todos site e documentacao"): a tela de Motores dava
um aviso de conversão Arrow (`ArrowTypeError: Expected bytes, got a 'int'
object`, coluna "Motivo") ao carregar a tabela "Situação". Já existia uma
correção pra esse mesmo tipo de problema (valor numérico solto numa coluna
de texto livre, ex.: "315.0" em vez de texto — ver comentário em
`motores.py`), mas ela só tratava valores já como `float` — um valor que
chegasse como `int` puro (não float) continuava quebrando. Corrigido:
o mesmo tratamento agora cobre `int` e `float` juntos.

## Bug corrigido em 2026-07-23 — eixo Y cortando aeronaves na linha do tempo

Wallace: "na linha do tempo da diagonal dos motores, o eixo y, alguns
estao cortando as aeronaves". O Plotly, num eixo Y categórico com muitas
categorias (1 por SN+matrícula), às vezes decide sozinho mostrar só
alguns rótulos (pula no meio) quando acha que não tem altura suficiente
pra todos — mesmo a altura do gráfico já sendo calculada dinamicamente
(`max(280, 28 * quantidade_de_rotulos)`). Corrigido forçando
`tickmode="array"` com a lista completa de rótulos (`tickvals`/`ticktext`)
+ `automargin=True` — garante que **todas** as aeronaves aparecem, sem
depender da heurística automática do Plotly. Mesma correção aplicada na
Diagonal de Manutenção (`diagonal_manutencao.py`), que usa o mesmo padrão
de gráfico e tinha o mesmo risco, mesmo sem o Wallace ter reportado lá.

## Pendências / a confirmar com o Wallace

- Significado exato de `data_1`/`data_2` (SILOMS/hélice) — hoje só rótulos
  neutros.
- Significado dos marcadores `X`/`1` na grade da Diagonal Nova (hoje só
  aparecem na tabela completa, fora dos indicadores).
