# Instruções — Diagonal de Manutenção

## O que é

Projeção de indisponibilidade futura por aeronave, montada a partir dos
mesmos arquivos "Diagonal de Manutenção"/"Diagonal de Inspeção" que cada
operador manda na pasta do Drive "MAPEM / DIAGONAL / VENCIMENTOS" (mesma
estrutura ano → mês → operador usada em `vencimentos.md`, mas o arquivo de
Diagonal em vez de Controle de Vencimentos).

**Pedido do Wallace:** uma linha do tempo — eixo X o tempo, eixo Y as
aeronaves, mostrando onde cada uma vai estar indisponível a partir de hoje,
com um resumo somado (aeronaves indisponíveis por mês) embaixo.

## Formato da fonte (confirmado pelo Wallace)

Cada operador desenha a grade do seu jeito, mas o sinal é sempre o mesmo:
cada aeronave tem um bloco de 2 linhas — uma linha "HORAS VOO" (acompanha
horas acumuladas por período) e uma linha "INSP. PROG." / "IMPACTO DIAG."
(ou equivalente). **Quando essa segunda linha tem texto numa coluna de
tempo, a aeronave fica indisponível naquele período por causa do que está
escrito ali** — não é preciso adivinhar duração, o próprio texto (código de
inspeção, "IS", "sem motor" etc.) é o motivo.

`"IS"` = **Indisponível por Suprimento** (falta de peça/material), não é
erro nem "Inspeção de Sistema" — confirmado pelo Wallace.

**"Só inspeção mesmo" (confirmado pelo Wallace):** eventos que são só
status/condição — `"IS"` (sozinho, sem código de inspeção junto) e
`"Aeronave sem motor"`/`"sem motor"` — **não entram** como evento de
indisponibilidade programada, mesmo aparecendo na linha "INSP. PROG.". Só
inspeção programada de verdade (código de inspeção, TBO, COR, HSI etc.) vira
evento. Filtro em `RE_NAO_PROGRAMADO`/`eh_programado()` em `diagonal_parse.py`.

## "Real" vs "Programado" (confirmado pelo Wallace: "aparecer a realidade")

A Diagonal de Manutenção é só uma **projeção futura** — não necessariamente
bate com o que está acontecendo agora. Por isso o Gantt combina duas fontes,
lado a lado na mesma linha por aeronave (a matrícula é a chave, não o
operador — os nomes de operador variam entre fontes pra mesma aeronave, ex.:
Diagonal chama de "BABR", Disponibilidade Diária chama de "6º ETA"):

* **Real (hoje)** — tirado do relatório **mais recente** da Disponibilidade
  Diária: toda aeronave com situação diferente de DI/DO (ver
  `disponibilidade_diaria.md` pro significado de cada código) vira uma barra
  até a data prevista (DPE) — ou +14 dias, só de referência visual, se não
  tiver DPE informado. Barra **sólida**.
  **Início da barra (corrigido em 2026-07-16)**: não é mais sempre "hoje" —
  `_inicio_real()` anda pra trás no histórico já carregado de
  Disponibilidade Diária (vários dias, não só o relatório de hoje)
  procurando o primeiro dia em que a aeronave já aparecia com essa MESMA
  situação. Bug achado pelo Wallace: "vi que o inicio ta sempre o dia
  atual" — antes, uma aeronave que já estava "II" há 8 dias aparecia como
  se a inspeção tivesse começado hoje. Se a situação já existia no dia mais
  antigo carregado (histórico só tem alguns dias — a Disponibilidade Diária
  não grava snapshot próprio, ver limitações abaixo), não dá pra saber o
  início de verdade — o motivo mostra um aviso "(em aberto desde antes do
  início do nosso histórico...)" em vez de inventar uma data anterior ao
  que temos.
* **Programado** — a projeção futura de inspeções, vinda da Diagonal de
  Manutenção de cada operador (ver seções acima). Barra **listrada** (`/`,
  `pattern_shape` do Plotly).

Construído ao vivo em `diagonal_manutencao.py` (`_eventos_reais()`), a partir
de `dados["disp_aeronaves"]` — não precisa reprocessar nada, usa o que já
está carregado da Disponibilidade Diária.

## Granularidade — varia por operador

| Operador | Granularidade | Particularidade |
|---|---|---|
| BANT, BABR, BACO, BABE, CLA | Semanal ("Semana N") ou por faixa de dias | Cabeçalho de mês pode vir uma vez só no topo ou repetido por bloco de aeronave (BABE repete; BANT/BABR/BACO/CLA vem uma vez). Matrícula pode estar na linha "HORAS VOO" (BANT/BABR/BACO) OU na linha "INSP. PROG." (BABE) — o parser checa as duas. |
| DACTA II | Semanal, mas cabeçalho de mês com espaçamento irregular (ex.: "DEZEMBRO" seguido de uma coluna de TSN antes do próximo mês) | Atribuição de semana pode ficar levemente imprecisa nessas transições — aceito como aproximação razoável. |
| BAMN | Mensal (4 colunas por mês, sem rótulo de semana) — vem numa aba "DIAGONAL" dentro do arquivo combinado, com células mescladas verticalmente (matrícula/esquadrão só na primeira linha do bloco) | Reaproveita a leitura merge-aware já usada em vencimentos_parse. |
| BACG | Semanal desde julho/2026 — a planilha íntegra passou a ser recebida e substituiu a reconstrução aproximada usada anteriormente. |
| PAMA-LS | **Aproximada** — o binário original não transferiu íntegro do Drive; os dados disponíveis continuam reconstruídos a partir de texto simplificado. A correspondência exata "código → mês" pode ter perdido precisão na conversão. Marcado com `confianca="aproximada"` na base tratada — não inventamos uma correspondência que não temos certeza. |

`CLA` tinha um bloco de exemplo/modelo no topo do arquivo ("XX:XX",
"INSP-XXX") que **não é dado real** — filtrado automaticamente (ver
`RE_PLACEHOLDER` em `diagonal_parse.py`). Os dados reais de CLA (aeronave
2723) ficam mais abaixo na mesma planilha.

## O que extrair

`extrair_diagonal_manutencao.py` gera `02_Dados_Tratados/base_diagonal_manutencao.xlsx`,
aba **Diagonal**: operador, aeronave, período_início, período_fim, motivo,
confiança (`exata` = tinha rótulo "Semana N"; `mensal` = só o mês, sem
semana; `aproximada` = PAMA-LS/BACG, ver acima).

Parser compartilhado em `diagonal_parse.py` (`ler_grade_generica`, usado por
todos os operadores com arquivo próprio em grade — xlsx via openpyxl, ods via
odfpy) + um leitor dedicado só pra BAMN (`_ler_bamn`, dentro do próprio
`extrair_diagonal_manutencao.py`, por causa das células mescladas e ordem de
colunas diferente) + uma lista fixa `EVENTOS_APROXIMADOS` somente pro PAMA-LS.

## Atualização de julho/2026

Fontes novas incorporadas para BANT, DACTA II, BABR, BABE, BACO, BAMN e
BACG. O BACG passou de aproximado para leitura direta da planilha. CLA foi
mantido na fonte de junho (ela já cobre até outubro) e PAMA-LS permaneceu na
última fonte aproximada, pois esses dois operadores não tinham arquivo novo na
pasta mensal consultada em 14/07/2026. A consolidação também passou a remover
duplicatas exatas de operador/aeronave/período/motivo/confiança, necessárias
porque a grade do BANT repete alguns textos em células mescladas.

## Site

Página "Diagonal de Manutenção" na Coordenadoria (entre Disponibilidade
Diária e Vencimentos) — Gantt (Plotly `timeline`), corte em "hoje" (só mostra
eventos com fim >= hoje), filtro por operador, por **aeronave** (multiselect,
pra incluir/excluir aeronaves específicas do gráfico — pedido do Wallace em
2026-07-14) e por quantos meses à frente olhar, resumo de aeronaves
indisponíveis por mês, e tabela detalhada com filtro por coluna.

**Aeronave pré-selecionada por padrão (2026-07-14)**: o filtro de Aeronave já
vem marcado com as 23 aeronaves "dentro do contrato"
(`AERONAVES_PADRAO` em `diagonal_manutencao.py`) — 2702, 2703, 2704, 2708,
2709, 2719, 2720, 2721, 2722, 2723, 2727, 2728, 2729, 2731, 2733, 2736,
2737, 2738, 2739, 2740, 2741, 2742, 2743. Deixa de fora, de propósito, as
fora do contrato (2726, 2730, 2732, 2734) e sem condições (2701, 2706,
2724) — ver `computo_mensal.md`. É só o valor inicial: continua editável,
dá pra marcar/desmarcar normalmente depois.

## Motores por aeronave + simulação de horas de voo (2026-07-15)

Pedido do Wallace: "vamos tentar inserir de forma inteligente essas
ifnormacoes de motor la na diagonal das aeronaves, de forma discreta, que
so aparece os detalhes se eu clicar, insere tb uma forma [...] da media
mensal de horas de voo por aeronave, no qual eu consiga clicar e se eu
alterar ali, ajeita a possicao da na diagonal geral, a do motor é fixa
seguindo sempre a tabela original com o historico".

Painel "🔧 Motores por aeronave" — 1 expander colapsado por aeronave (grade
de 3 colunas, discreto, só mostra o motor se clicar), logo acima do Gantt.
Cada expander mostra o motor vinculado àquela aeronave (SN, condição, %TBO
voada — via `motores_situacao`, cruzando pelo SN) e os dados de
planejamento da Diagonal Nova (`motores_diagonal_meta`: Hr disponível, Voo
mensal, Mês disponível), cruzando pelo **ANV** (não precisa de matrícula →
SN, a Diagonal Nova já tem o ANV direto).

**Simulação "e se eu voar mais/menos por mês"**: campo editável "Simular
horas de voo por mês" dentro do expander, começando no valor atual (Voo
mensal da planilha). Se o valor digitado for diferente do original,
recalcula `novos_meses = Hr disponível / novo valor` e projeta uma nova
data (`hoje + novos_meses de DateOffset`) — **só como "e se", nunca grava
em nenhum arquivo** (a planilha de Motores/Diagonal Nova continua sempre
fixa, seguindo o histórico real, exatamente como o Wallace pediu). Quando
existe um ajuste, um evento extra aparece no Gantt com fonte "Programado
(ajustado)"/operador "Simulação", padrão visual xadrez (╳) — ver
`FONTE_AJUSTADO`/`PATTERN_FONTE` em `diagonal_manutencao.py`.

Implementado em `_dados_motor_aeronave()` (cruzamento) e
`_secao_motores_por_aeronave()` (painel + recálculo), ambos em
`coordenadoria/secoes/diagonal_manutencao.py`. Fonte da extração:
`extrair_motores.py::_extrair_diagonal_metadados()` (aba "DiagonalMeta" do
arquivo tratado) — ver `00_Instrucoes/motores.md`.

**Rótulo da aeronave já traz o motor escrito (2026-07-15)** — Wallace: "ta
dificil de ver a informacao do motor na diagonal geral, deixa de forma
mais visivel, escreve la". `_rotulo_motor()` monta um resumo curto (ex.:
"SN PCE-PC2050 (12% TBO)") que vira parte do rótulo do eixo Y do Gantt
("FAB 2702 — SN PCE-PC2050 (12% TBO)") — sem precisar clicar em nada. O
expander de simulação continua existindo só pra quem quiser mexer nas
horas de voo.

**Painel do simulador virou 1 único expander fechado (2026-07-15)** —
Wallace: "deixa ele minimizado, ai quando clicr que aparce as aeronaves
para simular". Antes cada aeronave já aparecia com seu próprio expander
solto na tela; agora tudo fica dentro de um expander externo único "🔧
Simulador de horas de voo por aeronave", fechado por padrão — só abre a
grade de aeronaves depois de clicar nele.

## Eventos TBO/HSI da planilha de Motores, direto no Gantt (2026-07-15)

Wallace: "onde tem a diagonal das aeronaves quando for hsi ou tbo, colocar
um quadradinho escrito dentro hsi ou tbo para visualizacao, essas
informacoes sao sempre vinculada com a planilha de motores". `_eventos_motor()`
pega os eventos TBO/HSI/TBO\* de `motores_diagonal` (Diagonal Nova, sempre a
fonte fixa, nunca a simulação) e escreve o texto direto no Gantt, na mesma
linha da aeronave (via ANV):

- Cor por tipo de evento — âmbar = TBO, ciano = HSI (`COR_OPERADOR_MOTOR`).
- Hover com o SN do motor + comentário da célula, quando existir.

**Ajuste em 2026-07-15**: a 1ª versão desenhava uma barra do mês inteiro
(igual Real/Programado). Wallace: "o tbo e hsi coloca so o ponto de
inicio, nao coloca o mes inteiro, pq geralmente tem a troca de motor, é so
para estar escrito tbo ou hsi msm, sem linha pontinha ou bolinha" — trocado
por um `go.Scatter(mode="text")` só com o texto "TBO"/"HSI" no dia 1 do mês
projetado, **sem barra, sem marcador, sem padrão de linha** (o padrão
pontilhado que existia foi removido de `PATTERN_FONTE`) — só a palavra
escrita no ponto exato de início.

**Bug corrigido**: a coluna "aeronave" vinha com tipos diferentes entre as
3 fontes (Disponibilidade/Diagonal de operador = int, Motores = string) —
misturado isso fazia `.unique()` tratar `2722` (int) e `"2722"` (str) como
valores diferentes, duplicando a aeronave nos filtros e derrubando a
página com `StreamlitDuplicateElementKey` (chave repetida no expander do
simulador). Corrigido forçando string em toda a coluna `aeronave` logo
depois do `pd.concat`. Também descartado ANV = 0 (célula vazia/`False` na
planilha original vira `0` depois do ida-e-volta pelo Excel — nenhuma
aeronave da frota tem essa matrícula).

## Histórico de evolução da projeção (Motores, 2026-07-15)

Wallace: "mostrar na diagonal dos motores tb, um historico de evolucao" —
a projeção de TBO/HSI pode mudar de um dia pro outro (mês empurrado, virou
HSI em vez de TBO, comentário novo/editado). `extrair_motores.py::
_registrar_historico_diagonal()` grava 1 snapshot por dia dos eventos
TBO/HSI/TBO\* em `historico_motores_diagonal.csv` (chave: serial+ano+mês),
mesmo padrão da Situação. Exibido num expander "🕐 Evolução" na aba
"Diagonal TBO/HSI" de Motores (não na Diagonal de Manutenção — lá o foco é
a aeronave, o histórico da projeção do motor fica na página de Motores).

## Todas as aeronaves + condição do dia + detalhe unificado (2026-07-15)

Pedido do Wallace: "nessa diagonal das aeroanves vamos colcoar todas
aeronave, vamos colcoar a condicao da aeronave no dia, pensem em ser
clicavel a coluna Y (quadradinho com a aeronave clicavel), ai ali se tiver
faltando algum item aparece tb, o DPE do item, na linha x, a gente soma a
[informação de] disponibilidade colcoando di, do, IN, IS". Esclarecido com
o Wallace: "todas aeronave" = todas as 23 dentro do contrato (não fora do
contrato); o "clicável" = o painel de detalhe por aeronave (expander),
mostrando RAC (pendências) + Disponibilidade Diária (situação de hoje) +
Motor, tudo junto.

- **Todas as 23 aeronaves dentro do contrato sempre aparecem como linha no
  Gantt** (`aeronaves_alvo`), mesmo sem nenhum evento de indisponibilidade
  real/programado/motor no período — antes, uma aeronave 100% disponível
  sem eventos simplesmente não tinha linha. Linha "espaço reservado"
  (`operador="Sem evento"`, cor `rgba(0,0,0,0)` — totalmente transparente)
  garante a categoria no eixo Y sem desenhar nenhuma barra visível; fica de
  fora do resumo mensal e da tabela detalhada (não é indisponibilidade de
  verdade).
- **Rótulo da aeronave** ganhou a situação de hoje entre colchetes —
  `_mapa_situacao_hoje()` pega o código (DI/DO/II/IN/ITR/IS/IP) do
  relatório mais recente da Disponibilidade Diária. Ex.: "FAB 2702 [DI] —
  SN PCE-PC2050 (12% TBO)".
- **Painel "🔍 Detalhe da aeronave (motor, RAC, disponibilidade)"**
  (renomeado de "🔧 Simulador de horas de voo por aeronave" — mesmo
  expander único fechado por padrão, grade de 3 colunas por dentro) agora
  mostra, por aeronave: situação de hoje (nome completo, não só o código),
  pendências do RAC (PN, nomenclatura, quantidade faltante — top 6 + "ver
  aba RAC" se tiver mais), e o motor vinculado (com o simulador de horas
  de voo que já existia).
  **Gap real de dado**: o RAC (`extrair_rac.py`) não tem nenhum campo de
  DPE — é uma matriz PN × aeronave só com quantidade faltante, sem data
  prevista de entrega. Mostrado assim mesmo (sem inventar a data), com o
  aviso "sem DPE — o RAC não tem essa informação" ao lado de cada lista de
  pendências. Se um dia precisar do DPE de verdade, teria que vir de outro
  lugar (ex.: cruzar com Emergências do Contrato 005, que tem prazo de
  entrega — não implementado ainda, é outra área/pacote).

## Previsão de situação — próximos 7 dias (2026-07-16, substitui o resumo mensal)

Pedido do Wallace: "soma de eventos por mes ficou ruim, colcoa previsao de
IN DO DI,IS pelos proximos 7 dias, coloca o dia de hoje ai vc ja e os
proximos, tipo pegar a mensagem diaria analisar ela e colocar ali a
previsao po dia com base na mensagem diaria, base vai ser sempre ela, se
tiver previsao de inspcao programado (diagonal) pode inserir tb".
**Importante**: só o gráfico embaixo do Gantt principal foi trocado (o
antigo "Aeronaves indisponíveis por mês, soma de eventos na janela") — o
Gantt em si, o painel de detalhe e a tabela não mudaram.

`_previsao_situacao_7dias()`: tabela quantitativa (não gráfico de barras —
trocado em 2026-07-16 a pedido do Wallace: "ficou ruim o visual de ver,
acho melhor por quantitativo"), colunas = dias (hoje até hoje+6), linhas =
situação (DI/DO/II/IN/ITR/IS/IP, nomes completos de `paleta.NOME_SITUACAO`),
célula = quantidade de aeronaves-alvo naquela situação naquele dia. Última
linha soma **D (DI+DO)** — mesma convenção "D = DI+DO" já usada na
Disponibilidade Diária.

- **Hoje (dia 0) é sempre o código real** do relatório mais recente da
  Disponibilidade Diária — a "base" pedida pelo Wallace, sem nenhuma
  suposição.
- **Dias seguintes são projeção** (a mensagem em si não tem previsão
  dia-a-dia, só "previsão até o final do dia" e um total semanal — por
  isso projetamos, deixando bem claro na legenda que é estimativa):
  1. Aeronave indisponível hoje mantém o mesmo código até a Data Prevista
     de Entrega (`dpe_data`, ou +14 dias de referência sem previsão) —
     depois disso assume "DI" (disponibilidade plena).
  2. Aeronave já disponível hoje (DI ou DO) continua exatamente como
     estava — **não** reseta a "DI" sozinha (evitaria apagar uma restrição
     "DO" sem informação nova pra isso).
  3. Se tiver uma inspeção programada da própria Diagonal de Manutenção
     (fonte "Programado") cobrindo aquele dia, e a aeronave estiver
     disponível (DI/DO), ela entra como "II" (indisponível por manutenção
     programada) nesse dia — pedido do Wallace: "se tiver previsao de
     inspcao programado (diagonal) pode inserir tb".
- Quando o relatório do dia seguinte chegar de verdade, ele sempre
  substitui a projeção (a Disponibilidade Diária continua sendo a única
  fonte de verdade pro "hoje" de cada dia, esse gráfico só estima o que
  ela ainda não cobre).
