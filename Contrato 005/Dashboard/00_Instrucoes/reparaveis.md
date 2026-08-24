# Instruções — Reparáveis

## Fonte

Planilha Google Sheets **"Controle reparáveis C-98"** (conta `ngodoy143@gmail.com`). **Desatualizado** — isso já foi "sem conexão ao vivo, buscar só quando pedido", mas Reparáveis tem busca automática própria desde 2026-07-10 (de 2 em 2h, seg-sex — ver `C-98A PAMALS/00_Instrucoes/atualizacoes.md`). Cópia baixada em:

`01_Bases_Originais/Controles_Reparaveis/Controle reparaveis C-98 (Google Sheets).xlsx`

Aba usada: **`Divulgação`**. As outras 7 abas (Giro Ideal, Atual, Histórico, Empresa, EMPRESA_1, Vee one, Acerto virtual) **não são usadas**.

Essa planilha varia de tamanho a cada atualização (446 linhas em 2026-07-13, abertas e concluídas) — inclui campos que o PDF usado antes não tinha (`UNIDADE SOLIC.`).

## Extração

Ler a aba diretamente (já é planilha, não precisa reconstruir tabela de PDF).

## Colunas importantes (confirmado pelo Wallace)

| Coluna | Significado |
|---|---|
| OS | Número da Ordem de Serviço |
| PN | Part Number da peça |
| CFF | Código do fornecedor/fabricante |
| NOMENCLATURA | Descrição da peça |
| SN | Número de série da peça |
| DATA INICIO | Data de abertura da OS |
| UNIDADE SOLIC. | Base/esquadrão que solicitou (ex.: PAMALS, BAMN, BANT, PAMASP, BABE...) |
| ST_OS | Situação da OS (`REC`, `AUT`, `OS concluída`) |
| TAT SILOMS | Tempo em aberto (dias) segundo o sistema SILOMS |
| TAT (empresa) | Coluna "TAT " sob "INFORMAÇÕES DA EMPRESA" — TAT real reportado pela própria VEE ONE (em dias), só preenchido depois que o item já foi entregue (vem "NÃO APLICÁVEL" enquanto em reparo). Campo tratado: `tat_empresa`. Ver seção própria abaixo. |
| ONDE SE ENCONTRA | Local/empresa onde a peça está (ex.: VEE ONE, LEAP, WILLIAM, uma base, ou "PROCURANDO") |
| RECIBO CASO TENHA | Número do recibo de entrega, quando existe |
| CONDIÇÃO | Situação do reparo (ex.: EM REPARO, REPARADO, CONDENADO, EM QUARENTENA...). **Importante:** em ~17% das OS (as que já têm `RECIBO`), esta coluna traz uma data em vez de texto — **essa data é a data em que o item foi entregue de verdade** (confirmado pelo Wallace em 2026-07-27: "quando tem data na condicao significa que foi a data que foi entregeu"), não uma previsão/estimativa — ver tratamento abaixo. |
| SN TROCADO (EXCHANGE) | Número de série recebido de volta, quando o item foi trocado (exchange) |
| TERMO DE RECEBIMENTO | Identificação do termo, quando emitido |

**Colunas que existem na planilha mas não são extraídas** (confirmado que não interessam): `Qt` (na verdade é só um número sequencial de linha, não quantidade), `OBSERVAÇÃO COORDENADORIA/FISCAL`, `OBSERVAÇÃO VEE ONE`, `Data de devolução empresa`, e o resto do bloco "COMREC/ACERTO VIRTUAL" (Data do Termo, Recebimento do Termo, Solicitar Acerto, OS Concluída, etc.). **`TAT (empresa)` (antiga "TAT REAL", marcada como "ainda não confiável") passou a ser extraída em 2026-07-27** — Wallace confirmou que já está disponível/confiável ("tem o TAT DA EMPRESA AGORA").

## O que extrair

* OS, PN, CFF, nomenclatura, SN (e SN trocado, quando houver exchange);
* unidade solicitante;
* situação (ST_OS) e condição (reparo);
* onde se encontra;
* data início, TAT SILOMS, TAT empresa;
* recibo e termo de recebimento.

## Regra de OS em aberto

Manter apenas OS cuja situação (`ST_OS`) seja diferente de "OS concluída" (`REC` e `AUT` entram).

## Regras de tratamento

* Datas convertidas para tipo data.
* Normalizar `CONDIÇÃO` (variações de grafia, ex.: "DEVOLVIDO NO ESTADO" vs "DEVOLVODO NO ESTADO").
* **Quando `CONDIÇÃO` contém uma data em vez de texto de status**: mover esse valor para um campo separado `data_entrega` e deixar `condicao` vazio para essa linha (não somar a data à contagem "OS por condição"). Renomeado de `data_retorno_prevista` em 2026-07-27 — o valor é a data real de entrega, não uma previsão (ver tabela de colunas acima).
* Colunas com tipo misto (texto/número, ex.: CFF) viram texto na exibição do dashboard, sem alterar o dado tratado.
* **PN sempre normalizado pra texto na extração** (`parse_texto_pn` em `extrair_reparaveis.py`) — bug real visto em 2026-07-13: uma OS nova com PN só numérico foi lida como `int` pelo openpyxl, deixando a coluna com tipos mistos (`int` e `str`) e quebrando `sorted()` no Streamlit Cloud (`TypeError: '<' not supported between instances of 'int' and 'str'`), além da conversão pra Arrow do `st.dataframe`. Diferente do caso do CFF acima, aqui a correção é NA EXTRAÇÃO (dado tratado já sai só como texto), não só na exibição — e a mesma correção foi replicada em `extrair_emergencias.py` (coluna PN também existe lá). Ver também `components/utils.py::ordenar_unicos`, usado em 7 telas como defesa adicional contra esse mesmo padrão de bug com qualquer outra coluna.

## "Onde se encontra" vazio (2026-07-18)

Pedido do Wallace: "onde se encontra, quando tiver vazio, a empresa ainda
nao passou, esta em processo interno da empresa ou nao foi informado por
ela, pensa numa forma de escrever isso e colocar la tb". Preenchido logo
na entrada de `render()` (não só na exibição) com o texto **"Em processo
interno / não informado pela empresa"** (constante `LOCAL_NAO_INFORMADO`
em `reparaveis.py`) — aparece assim no filtro "Onde se encontra", na
tabela e no gráfico "TAT médio por local".

Efeito colateral bom, achado ao implementar: antes, essas linhas (vazias)
eram **descartadas silenciosamente** do gráfico/tabela "TAT médio por
local", porque o `groupby` do pandas ignora grupos `NaN` por padrão — 42
itens que não apareciam em lugar nenhum desse gráfico. Não muda a
classificação "Com a empresa e terceirizados" (vazio já contava como isso
antes, continua contando).

## Filtros no dashboard

PN, situação, condição, onde se encontra e unidade solicitante — todos filtráveis na tela "Reparáveis".

## Estatísticas de TAT (2026-07-18)

Pedido do Wallace, nos dois sites (principal e 005CELOG2025): seção fixa
no topo da tela (não depende dos filtros abaixo), sempre sobre todas as OS
em aberto (`em_aberto == True`).

**Regra "entregue x com eles"**: quando `onde_se_encontra` é um destes
valores exatos — `BABE, BAMN, BABV, BAPV, BABR, BANT, PAMA-LS, BACO, BASM,
BACG, EEAR` (constante `LOCAIS_ENTREGUES` em `reparaveis.py`) — o item **já
foi entregue** pelo fornecedor (VEE ONE) pra unidade/base, só falta
encerrar a burocracia da OS (ainda conta como "em aberto" no SILOMS, mas
não é mais atraso de reparo de verdade). Qualquer outro valor (`VEE ONE`,
`WILLIAM`, `LEAP`, `PROCURANDO`, `AV AERONAUTICA`, `AMA - VEE ONE`, vazio,
etc.) conta como **"com a empresa e terceirizados"** — ainda não entregue.

**Atenção, `"V1 PAMA-LS"` ≠ `"PAMA-LS"`**: são valores diferentes na fonte
— `"V1 PAMA-LS"` **não** entra em `LOCAIS_ENTREGUES` (fica em "com a empresa e terceirizados"),
confirmado pelo Wallace: "obs: v1 pamals esta com eles ainda". Por isso o
match é por **igualdade exata**, nunca por "contém" — um match por
substring pegaria "V1 PAMA-LS" por engano.

**Prazo contratual de TAT**: `PRAZO_CONTRATUAL_TAT_DIAS = 110` (dias),
confirmado pelo Wallace. "Fora do prazo" = `tat_siloms > 110`. "Vence este
mês" = `data_inicio + 110 dias` cai no mês/ano atual **e** ainda não
passou de 110 dias (senão já estaria em "fora do prazo", não "vence
este mês"). **Só sobre "Com a empresa e terceirizados"** (2026-07-18,
Wallace: "o prazo dentro e fora do prazo so os que estao com a
empresa") — item já entregue (só falta burocracia) não conta mais contra
o prazo contratual, mesmo que o TAT dele já passe de 110 dias.

Cards mostrados: Abertos (geral) + Média de TAT geral (todos os abertos,
incluindo os que só faltam burocracia — pedido explícito do Wallace, pra
não esconder esse tempo do TAT médio); Com a empresa e terceirizados
(quantidade) + Média de TAT só desse grupo; Fora do prazo contratual;
Vencem o prazo este mês.

**Renomeado em 2026-07-18** — "Com eles" virou "Com a empresa e
terceirizados" (Wallace: "po, nao escreve com eles kkk, deixa mais
padrao, escreve com a empresa e tercerizados") — nome mais formal pra
apresentar, mesmo grupo/regra de antes.

**Gráficos adicionados em 2026-07-18** (Wallace: "coloca uns graficos
tb"), sempre visíveis (não escondidos em expander): 2 donuts lado a lado
("Com a empresa e terceirizados" x "Entregue, falta burocracia"; "Dentro"
x "Fora do prazo contratual") + gráfico de barras horizontal de TAT médio
por `onde_se_encontra` (com uma linha vertical marcando os 110 dias) —
sugestão própria pra responder "pense em outras estatísticas que podemos
fazer", mostra onde o item costuma ficar parado por mais tempo. A tabela
com os números fica num expander opcional embaixo do gráfico.

**Card de TAT real da empresa (2026-07-27)** — desde que `tat_empresa`
passou a ser extraído (Wallace: "tem o TAT DA EMPRESA AGORA"), 2 cards a
mais: "Itens com TAT real da empresa (já entregues)" (quantidade) + "Média
de TAT real — empresa" (média de `tat_empresa`). Diferente dos cards de
prazo contratual acima (que olham só `abertos`, com base em `tat_siloms` —
o único TAT disponível enquanto o item ainda está em andamento), esses 2
novos cards olham a base **inteira** (abertos + concluídos), porque
`tat_empresa` só existe depois que o item já foi entregue — é uma medida
retrospectiva (real, reportada pela empresa), não do que está em
andamento agora.

**Complemento com a RMA em andamento (2026-08-12)** — Wallace: "tem uns OS
que foram entregues (a burocracia provavelmente ainda tá aberta) [...] vc
vai na planilha de controle dos reparáveis busca essas OS [...] atualiza
onde que tá, data de devolução pela empresa, número do recibo, só deixar
registrado que essa informação veio da RMA de julho da empresa". A
"planilha geral" (Controle de Reparáveis) pode demorar a fechar a
burocracia de uma OS mesmo depois da empresa já ter devolvido de verdade
— a RMA em andamento do mês (aba 1.8 "Materiais reparáveis devolvidos no
mês de referência" + aba 1.10 "Controle de Ordens de Serviço abertas até
o mês de referência") já mostra isso antes. `extrair_reparaveis_rma.py`
cruza as 2 abas (OS da 1.8 → busca Data da devolução/Nº do Recibo/Operador
na 1.10) e salva em `02_Dados_Tratados/reparaveis_complemento_rma.xlsx`
(acumulado por mês, upsert por OS+mês — nunca sobrescreve a planilha geral
nem a base tratada, só complementa na exibição). Botão "🔄 Complementar com
a RMA em andamento do mês" na tela de Reparáveis (`_secao_complemento_rma`
em `reparaveis.py`) busca no Drive (mesma pasta "Fechamentos mensais" >
ano > mês já usada por Financeiro/Apresentação/Ata RMA) e roda o
cruzamento pro mês escolhido. Na tabela principal, as 3 colunas mescladas
aparecem como "ONDE SE ENCONTRA"/"Data de devolução empresa"/"RECIBO CASO
TENHA", e uma coluna "Fonte" mostra "RMA {Mês}/{Ano}" quando o valor veio
de lá (vazia = só da planilha geral). **Não muda `situacao`/`em_aberto`**
— só os 3 campos, como pedido; a classificação "entregue, falta
burocracia" (`LOCAIS_ENTREGUES`) já reconhece automaticamente o valor
complementado de "onde_se_encontra" (normalizado de "PAMALS" pra
"PAMA-LS", mesma grafia da planilha geral). OS que a 1.8 diz que foi
devolvida mas não tem devolução/recibo/local nem na própria 1.10 (ou nem
aparece lá) vira inconsistência no log — não inventamos o dado.

## Reorganização da tela (2026-08-24)

Pedido do Wallace: "vamos melhorar o controle de reparaveis, as
informacoes deles, o layort, as cores os filtros, pensa ai oq podemos
fazer". Levantei o que existia (cards/gráficos/tabela numa coluna única
gigante, tudo âmbar mesmo em número ruim, filtro só por valor exato, sem
exportar) e propus uma lista — confirmado com o Wallace via pergunta:
reorganizar em abas (recomendado) + ranking das mais atrasadas + coluna
"dias até vencer" + botão de exportar.

**3 abas** (`render()`) em vez de coluna única: **"📊 Visão Geral"**
(`_secao_estatisticas_tat` — cards, donuts, ranking, gráfico por local),
**"📋 Tabela / Consulta"** (`_secao_tabela` — busca, filtros, tabela,
distribuição por condição, complemento RMA) e **"📅 Histórico"**
(`_secao_historico_mensal`, sem mudança de conteúdo).

**Cores condicionais** (Wallace: "as cores" + depois, vendo o gráfico:
"tem um negocio de cor la de onde ta, ta um laranjao") — antes todo card/
barra usava a cor de marca (âmbar), mesmo em número ruim. Agora:
`_card_metrica()` (novo helper, HTML customizado — `st.metric` não deixa
colorir só o valor) usa `STATUS["critical"]` nos cards "Fora do prazo
contratual" e "Vencem o prazo este mês" quando > 0; o gráfico "TAT médio
por local" colore cada barra individualmente (`STATUS["critical"]`/
`STATUS["good"]`, nunca AMBER como status — regra da paleta) conforme
passa ou não dos 110 dias contratuais. Linha da tabela principal também
ganhou destaque vermelho sutil quando fora do prazo ou condenado
(`_cor_linha`, mesma técnica de Styler+DataFrame pré-formatado pra texto
usada no Cômputo Mensal em 2026-08-20).

**Gráfico "TAT médio por local" ficou clicável** (Wallace: "quero que
tudo seja clicavel nessa parte") — `st.plotly_chart(..., on_select="rerun",
selection_mode="points")`; clicar numa barra guarda o local em
`st.session_state["rep_filtro_local_pendente"]`, que `_secao_tabela()`
consome logo no início (antes do multiselect "Onde se encontra" ser
instanciado nesse mesmo rerun) e aplica como filtro na aba "Tabela /
Consulta" — funciona porque as 3 abas do Streamlit rodam o script inteiro
sempre (só a exibição é escondida via CSS), não é lazy-load.

**Bug mudo corrigido** (mesmo já achado no Cômputo Mensal, 2026-08-20):
célula vazia (None/NaN/NaT) na tabela aparecia como o texto literal
"None" em vez de branco — o Streamlit ignora o `na_rep` do Styler nessa
versão. `_tabela_para_texto()` agora converte TODAS as colunas pra texto
antes de estilizar (antes era só uma lista fixa de 7 colunas, "condicao"
tinha ficado de fora).

**Novidades que não existiam:**
- Busca por texto livre (nomenclatura/PN/SN/OS), combinável com os
  multiselects existentes.
- Atalho "Mostrar só fora do prazo contratual" (checkbox).
- Ranking das 10 OS mais atrasadas (só "com a empresa/terceirizados"),
  linha vermelha quando > 110 dias.
- Coluna "Dias até vencer o prazo" (110 − TAT SILOMS) na tabela principal
  — só preenchida pra quem ainda está com a empresa/terceirizados (mesma
  regra do prazo contratual); quem já foi entregue fica em branco.
- Botão "⬇️ Exportar (XLSX)" da tabela já filtrada
  (`gerar_xlsx_bytes`, reaproveitado de `components/exportar.py`).
- Nomes de coluna da tabela principal padronizados (Title Case em tudo,
  antes misturava `os`/`pn` minúsculo com `ONDE SE ENCONTRA` maiúsculo).

Testado ao vivo no preview: abas, cores, clique-filtra-outra-aba, busca,
exportar e ranking — todos funcionando.

## Refinamento visual — brief completo de 20 itens (2026-08-24)

Wallace mandou um brief de design completo ("Refinamento visual e
organização do dashboard C-98") pedindo pra manter TODA a identidade
atual (dark mode, laranja, fonte, abas, dados, cálculos) e só melhorar
hierarquia/organização/cores semânticas — "quero a sensação de: é
exatamente o mesmo dashboard, mas agora foi revisado por um bom designer
de produto". Dado o tamanho do brief (20 seções, cobrindo o dashboard
inteiro), apliquei em 2 frentes:

**1. Compartilhado/global** (`contrato005/components/paleta.py`,
`contrato_app.py`, `contrato005/components/data_global.py`) — propaga
pra TODAS as páginas do Contrato 005 automaticamente:
- `paleta.py` ganhou `ESPACO` (tokens de espaçamento), `metrica_html()`
  (card de métrica em HTML puro com cor semântica — necessário porque o
  CSS global força `[data-testid="stMetricValue"]` pra AMBER com
  `!important`, então um `st.metric()` normal não pode ficar vermelho/
  verde) e `titulo_bloco()` (cabeçalho pequeno pra agrupar métricas
  relacionadas).
- `contrato_app.py`: expanders ganharam cara de painel (fundo/borda
  consistentes com os gráficos).
- `data_global.py`: hierarquia mais clara no controle de data — "DATA
  ANALISADA" grande em cima, nota pequena embaixo, slider sem rótulo
  grande (não compete mais com os indicadores da página).

**2. Reparáveis** (`reparaveis.py`) — página piloto, já reorganizada em
abas em 2026-08-24 (ver seção acima); recebeu o refinamento completo do
brief:
- **Blocos visuais** (Volume/Prazo contratual/TAT/Entregues) — cada um
  com `titulo_bloco()`, em vez da sequência solta de 8 cards do mesmo
  peso.
- **Textos metodológicos** movidos pra dentro do expander "ℹ️ Entenda os
  critérios dos indicadores" — a área principal só tem 1 frase curta.
- **Donuts** com mesma altura (260px) e legenda embaixo/centralizada (não
  mais afastada à direita, padrão do Plotly).
- **Ranking "Top 10 mais atrasadas"**: reordenado (TAT primeiro, Unidade
  por último — menor peso visual); número do TAT em vermelho negrito;
  fundo vermelho SÓ pro extremo (> 2x o prazo contratual, 220 dias) — não
  a linha inteira só por estar no ranking.
- **Gráfico "TAT médio por local"**: corrigido — antes toda barra era
  vermelha/verde, mesmo sem passar do prazo; agora só quem passa de 110
  dias fica vermelho (`STATUS["critical"]`), quem está dentro fica num
  âmbar translúcido (`AMBER + "66"`, identidade discreta, não alarme).
  **Linha vertical dos 110 dias também corrigida** — estava vermelha
  (parecia problema), agora é âmbar (é só a referência do prazo).
- **Tabela principal**: OS/PN/Nomenclatura fixas na rolagem horizontal
  (`column_config` com `pinned=True`, suportado nativo pelo Streamlit
  1.58 — só funciona com segurança porque `_tabela_para_texto()` já
  limpa todo NaN antes); linha "fora do prazo" com fundo vermelho BEM
  suave (10% opacidade, era mais forte); "condenado" virou um destaque
  DIFERENTE (só a célula "Condição" em vermelho negrito, não a linha
  inteira — antes usava o mesmo tom do "fora do prazo", misturando 2
  significados numa cor só).
- **Legenda da tabela** virou expander "ℹ️ Como interpretar esta tabela",
  organizado em tópicos (antes era um parágrafo corrido comprido).
- **Distribuição por condição**: virou expander, ordenado crescente
  (maior no topo do gráfico horizontal), com rótulo de valor em cada
  barra.
- **Histórico mensal**: gráfico mais alto (320px, era ~200px), mais
  espaço entre barras (`bargap=0.3`) — mesma cor laranja de sempre.

Testado ao vivo no preview: os 4 blocos, expanders, donuts alinhados,
ranking colorido corretamente, barras condicionais, linha do prazo
âmbar, tabela com coluna fixa, legendas em expander e histórico — tudo
funcionando, print por print.

**Não aplicado ainda** (fora do escopo desta rodada, mesmo padrão fica
pronto pra reaproveitar): Emergências Abertas/Totais, Fechamento Mensal,
Empréstimos, Pagamentos, Reajuste, e as áreas Coordenadoria/Projetos
(cada uma com seu próprio `paleta.py`, sem import cruzado, mesmo motivo
de sempre) — o brief pedia revisão de "todo o dashboard", mas o volume
de páginas exigiria várias rodadas; Reparáveis serviu de piloto/exemplo
concreto porque foi literalmente a página usada em todos os exemplos do
brief.

## Ajuste rápido de clareza (2026-08-24, mesmo dia)

Wallace, depois de eu explicar a diferença "com a empresa" x "entregue
(falta burocracia)" na conversa: "queria que deixasse mais claro, parece
que tem muita informacao na tela principal tb ne". Dois ajustes na aba
"Visão Geral":

- **Legenda visual (selos coloridos)** logo abaixo do rádio de escopo —
  🟠 "Com a empresa e terceirizados — ainda não voltou" / 🟢 "Entregue —
  já voltou, falta só fechar a OS no SILOMS". Antes só existia como texto
  corrido (agora reforçado com cor, igual às cores já usadas nos cards/
  donuts/barras — funciona como a "legenda mestra" delas).
- **Donuts + Top 10 mais atrasadas + gráfico "TAT médio por local"**
  foram pra dentro de um único expander "📊 Ver gráficos e detalhamento",
  fechado por padrão — a aba "Visão Geral" agora só mostra, de cara, os 4
  blocos de números (Volume/Prazo/TAT/Entregues) + a legenda, que é
  exatamente o "entender em poucos segundos" que já era o objetivo do
  brief de refinamento. Tudo o mais continua exatamente igual, só
  escondido até alguém clicar. Altura da página caiu de ~4400px pra
  ~2670px na aba Visão Geral (testado ao vivo).
