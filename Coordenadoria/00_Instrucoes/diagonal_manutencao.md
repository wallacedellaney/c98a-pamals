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
  desde a data do relatório até a data prevista (DPE) — ou +14 dias, só de
  referência visual, se não tiver DPE informado. Barra **sólida**.
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
