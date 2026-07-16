# Instruções — Vencimentos

## Princípio geral (definido pelo Wallace): os formatos vão mudar, sempre

Nenhuma fonte de dado aqui (TMOT, Operadores, Disponibilidade Diária, RAC) tem formato garantido estável. Cada operador escreve do seu jeito, cada mês pode vir diferente do anterior, colunas somem/aparecem, convenções de texto mudam (maiúscula/minúscula, abreviação, sigla nova). **Isso é esperado, não uma exceção.**

Regra de trabalho: quando um formato novo ou diferente aparecer, a resposta é **adaptar a ferramenta de leitura** (ajustar o parser, criar um caso novo, achar a lib certa — como foi feito aqui com `odfpy` pra ler `.ods`, ou os vários regex de `vencimentos_parse.py` pra cobrir "5M", "9 Meses", "944 Pousos", "1me8d" etc.), não travar, não inventar o dado, e não presumir silenciosamente que "deve ser igual ao de antes". Se não der pra reconhecer um valor, ele fica de fora e vira inconsistência no log (`06_Logs/`) — nunca um número chutado.

## Estrutura da aba

Dentro da Coordenadoria, "Vencimentos" é um pequeno dashboard interno dividido em duas partes clicáveis:

1. **Operadores** — Controle de Vencimentos por base/operador. Todos os 9 operadores confirmados (BAMN, BABE, CLA, BANT, BABR, PAMA-LS, DACTA II, BACO, BACG) incorporados. Ver seção própria abaixo.
2. **TMOT** — controle de vencimento de itens/peças por hora, pouso ou calendário, fonte única (planilha "Vencimentos", aba C-98U8). Pronta (ver abaixo).

## TMOT — fonte

Google Sheets **"Vencimentos"** (dono `fred_o_m@hotmail.com`, planilha compartilhada com várias frotas), aba **`C-98U8`**. A planilha tem outras abas (A-29T2, C-95A7, C-97A2, G-19U2, IU-93A6, T-25T9, T-27T1, PNs TGCC, Lixos) que não são usadas.

Cópia local só com as colunas usadas (linha 1 "ATUALIZADO DD/MM" removida, linha 2 vira cabeçalho): `01_Bases_Originais/Vencimentos/Vencimentos_C-98U8.xlsx`.

### Atualização automática (a partir de 2026-07-09)

Compartilhada com a conta de serviço (`pamals-drive-reader@...`) e adicionada à
cadência automática — roda junto com Emergências/RAC (seg-sex ~12h, GitHub
Actions e Mac). `extrair_vencimentos.py` ganhou `atualizar_do_drive()`, igual
às outras fontes.

**Bug corrigido nessa migração:** o código lia `wb.active` (a aba "ativa" por
padrão do arquivo) em vez de pedir a aba `C-98U8` pelo nome. Isso nunca deu
problema antes porque a cópia local (`01_Bases_Originais/`) só tinha a aba
C-98U8 mesmo. Mas o arquivo real do Drive tem **10 abas** (uma por frota —
C-97A2, A-29T2, C-95A7, C-98U8, G-19U2, IU-93A6, T-25T9, T-27T1, PNs TGCC,
Lixos), e a aba "ativa" por padrão é **C-97A2**, não a nossa — se a busca
automática tivesse sido ligada sem esse fix, teria extraído os dados errados
(de outra frota) silenciosamente. Corrigido pra sempre referenciar `wb["C-98U8"]`
explicitamente.

**Colunas importantes (definidas pelo Wallace)**: DISPONIBILIDADE, DATAVENC, INSPEÇÃO, PN, SN, MATRÍCULA, OPERADOR, NOMENCLATURADOITEM. As demais colunas da planilha original (CODEMP, INTERVALO, TSN/TSO do item, Monitoração, dados do "conjunto maior", posição do item) não são usadas por ora.

## Como interpretar a coluna DISPONIBILIDADE (confirmado pelo Wallace)

Não existe uma coluna própria dizendo o tipo de vencimento — é preciso inferir pelo **formato** do valor:

| Formato na planilha | Tipo | Como tratamos |
|---|---|---|
| Duração `[h]:mm:ss` (Excel/openpyxl lê como `timedelta`) | **Hora** | Convertido para número de horas (`total_seconds()/3600`), positivo ou negativo. |
| Número puro (int/float) | **Pouso** | Mantido como está — quantidade de pousos. |
| Texto terminando em "m" (ex.: `-368m`) | **Calendário** (meses) | Convertido para dias (`meses × 30`) pra ter unidade única de comparação. |
| Texto terminando em "d" (ex.: `-24d`, `23d`) | **Calendário** (dias) | Mantido em dias. |
| Texto tipo "1me8d" (mês + dia combinados) | **Calendário** (mês+dia) | Convertido pra dias (`mês×30 + dias`), preservando o sinal. |

Em qualquer um dos tipos, **DISPONIBILIDADE negativa = item vencido** (já passou do limite) por aquela quantidade de horas/pousos/dias. `disponibilidade_texto` guarda o texto original (só preenchido pra Calendário) pra exibição — `disponibilidade_valor` é sempre o número usado pra filtro/ordenação (dias no caso de Calendário).

`DATAVENC` é sempre uma data-calendário (projeção), nas 3 categorias — usada como referência complementar, não como o campo principal de cada tipo.

Duas linhas da planilha (na época da extração) tinham DISPONIBILIDADE lida como um `datetime` de 1899 (ex.: `21:10`, `17:35`) — parece erro de digitação/formatação na origem (deveria ser uma duração, não um horário). Não inventamos conversão pra esses casos — ficam de fora e registrados como inconsistência no log.

`OPERADOR` = unidade/esquadrão responsável pelo item (ex.: PAMALS, 7ETA, CLA, 1/5GAV, DACTA II) — é um dado desta própria planilha TMOT, não tem relação com a futura seção "Operadores" do mini-dashboard (que é uma fonte diferente, ainda não definida).

## O que extrair

`extrair_vencimentos.py` gera `02_Dados_Tratados/base_vencimentos_tratada.xlsx`, aba **TMOT**: matrícula, operador, PN, SN, nomenclatura, inspeção (código do tipo de inspeção/tarefa), tipo_vencimento (Hora/Pouso/Calendário), disponibilidade_valor, disponibilidade_texto, data_vencimento, vencido (bool).

## Operadores — fonte

Google Drive, pasta **"MAPEM / DIAGONAL / VENCIMENTOS"** → ano → mês → uma subpasta por operador/base. Operadores confirmados pelo Wallace: **BAMN, BABE, CLA, BANT, BABR, PAMA-LS, DACTA II, BACO, BACG**.

**Regra de busca (definida pelo Wallace):** sempre pegar o mês mais recente disponível; se um operador específico não mandou arquivo naquele mês, buscar no mês anterior **só daquele operador**, até achar. Cada operador é independente nisso.

**Só buscamos o arquivo "Controle de Vencimentos"** de cada operador (não MAPEM nem Diagonal de Inspeção, que são relatórios diferentes que também ficam nessas pastas).

### BABR × PAMA-LS (confirmado pelo Wallace)

A pasta do Drive chamada "PAMA-LS" (maio) e a pasta "BABR" (abril/junho) pareciam ter o mesmo conteúdo (aeronaves 2709, 2720, 2721, sempre com nome de arquivo "GLOG-BR"). O Wallace confirmou: **isso é a base BABR mesmo** — a pasta só mudou de nome ao longo dos meses. A **2704 é a única aeronave que é de fato do PAMA-LS**, e vem num arquivo à parte, por aeronave (`3 - VENCIMENTOS 2704 -MAIO2026.xlsx`, na própria pasta "PAMA-LS" de maio).

### Cada operador escreve diferente (confirmado na prática)

| Operador | Arquivo | Particularidades |
|---|---|---|
| CLA | `.xlsx`, aba única | Seções "POR HORA/POR POUSO/POR CALENDÁRIO" marcadas, mas **misturadas** (ex.: uma linha "5M" aparece dentro da seção "POR HORA") — por isso o tipo real de cada linha é decidido pelo formato do valor, não pela seção. Datas tipo "XXXXXXXX" = sem estimativa (viram data nula, não inventamos). **Incorporado.** |
| DACTA II | `.ods` | Só abre certo com leitura bruta de célula (o pandas/openpyxl padrão quebra tentando interpretar "3321:35" como horário). Horas em texto puro "3321:35", pousos "944 Pousos", meses "9 Meses"/"01 Mês", datas "out/2033" (abreviação em português + ano). **Incorporado.** |
| BABR | `.xlsx` (nome do arquivo "GLOG-BR") | Igual à DACTA II nos valores (horas/pousos/meses por extenso), mas datas já vêm como data real (Excel). Aeronaves 2709, 2720, 2721. **Incorporado.** |
| BABE | `.xlsx` | Mesmo layout com seções; esse mês só tinha 2 itens reais (seção "POR HORA" veio vazia). **Incorporado.** |
| PAMA-LS | `.xlsx` (arquivo "VENCIMENTOS 2704", maio) | Formato bem diferente: **sem** seções POR HORA/POUSO/CALENDÁRIO — o tipo é sempre inferido pelo formato do valor. A coluna AERONAVE fica vazia em cada linha porque a matrícula (só a 2704) já vem fixada no cabeçalho/título do arquivo. Tem valores híbridos tipo "949:30 OU 24M" (qual vencer primeiro) que ficam de fora por serem ambíguos — não escolhemos um dos dois sem instrução. **Incorporado** (parser dedicado: `_processar_linhas_aeronave_fixa`). |
| BACO | `.xlsx` em formato padrão igual aos outros; o PDF de mesmo nome é só uma versão duplicada. Atualizado com a fonte de julho/2026. **Incorporado.** |
| BAMN | vem numa aba (`VENCIMENTO`) dentro do arquivo "Diagonal de Manutenção" (que também tem abas `DIAGONAL` e `MAPEM`) — não um arquivo próprio. Ordem de colunas diferente (NOMENCLATURA/PN/SN/ESPECIALIDADE/AERONAVE/...), matrícula **sem** prefixo "FAB" (só o número puro), usa **células mescladas verticalmente** pra nomenclatura (o valor vale pra várias linhas de baixo — tratado com um leitor de ODS dedicado que "puxa pra baixo" o último valor real da coluna). Tem formatos de valor extras: sufixo "A"/"Anos" (ex.: "10A" = 10 anos), "Nm e Nd" com espaços (ex.: "-4m e 11D"), datas "MM/AA" sem dia (ex.: "03/27" = março/2027). **Incorporado** (parser dedicado: `_processar_linhas_bamn` + `_ler_ods_mesclado`). |
| BACG | A fonte de julho/2026 veio íntegra em `.xlsx`, aba "Controle de Vencimentos", só com AERONAVE sem prefixo "FAB" (igual à BAMN) — substituiu o CSV reconstruído de abril. Tem muitos itens com DISPONIBILIDADE **"O/C"** (On Condition — sem vencimento programado por hora/pouso/calendário): tratado como `"Condição"`, não como erro. **Incorporado** (`xlsx_aba_bare`). |
| BANT | arquivo único (`DIAGONAL E VENC ITENS...xlsx`) com 3 abas (`DIAGONAL C-98`, `Controle de Vencimento de Itens`, `Panes`) — a aba certa (a do meio) já usa a ordem de colunas **padrão**, com cabeçalho na linha 4 (as 3 linhas antes são notas soltas, ignoradas naturalmente porque não têm aeronave válida) e AERONAVE em número puro (int, sem "FAB"), igual à BACG/BAMN. Trouxe 4 formatos de valor novos: hora com **ponto de milhar** ("4.938:00"), hora **anotada com equivalente em meses entre parênteses** ("1.337:20 (19,8 M)" — o parêntese é descartado, só informativo), **"ANV S/ MOTOR"/variações de "NÃO INSTALADO(A/S)"** (item não instalado no momento, sem vencimento aplicável — novo tipo `"Não instalado"`) e **"VENCIDA"** (a fonte escreveu que já venceu mas não deu o valor — novo tipo `"Vencido (sem valor)"`, com `vencido=True` mesmo sem número, ver `vencido_de()`). A coluna de data trouxe "JUL / 27" (mês/ano com espaço em volta da barra — regex ajustado) e 4 datas com anos 1930/1931/1935 (bug de formatação na origem — uma "data estimada de vencimento" nunca é histórica; datas com ano < 2000 são tratadas como ausentes, não inventamos). **Incorporado** (tipo `xlsx_aba_bare` no `REGISTRO`, reaproveitando `_processar_linhas` com aba e regex de matrícula configuráveis). |

Todos os 9 operadores confirmados estão incorporados.

### Atualização de julho/2026

Fontes novas incorporadas para BANT, DACTA II, BABR, BACO, BAMN e BACG.
O BACG passou do CSV reconstruído de abril para leitura direta do XLSX de
julho. CLA permaneceu em junho e PAMA-LS em maio por não terem arquivo novo na
pasta mensal. A BABE enviou arquivo de julho, mas as duas linhas vieram sem
DISPONIBILIDADE; para não inventar valores, o consolidado mantém a última fonte
utilizável, de junho. O parser passou a reconhecer `N/A` como "Não aplicável"
e horas com milissegundos, como `-99:00:00.000`. Duplicatas integralmente
idênticas também são removidas na consolidação.

### Tipos de vencimento "especiais" (além de Hora/Pouso/Calendário)

Alguns operadores escrevem valores que não são vencimento nenhum, mas são categorias reais e reconhecidas (não erro, não dado ausente):

* **`"Condição"`** (BACG, `"O/C"`/"ON CONDITION") — item monitorado por condição (inspeção visual/funcional), sem hora/pouso/calendário programado.
* **`"Não instalado"`** (BANT, `"ANV S/ MOTOR"`, `"NÃO INSTALADO(A/S)"`) — item/motor que não está instalado na aeronave no momento.
* **`"Vencido (sem valor)"`** (BANT, `"VENCIDA"`) — a fonte informou que já passou do vencimento, mas não disse por quanto; `vencido=True` é setado mesmo com `disponibilidade_valor=None`.
* **`"Não aplicável"`** (BAMN, `"N/A"`) — a própria fonte informa que não há vencimento aplicável; fica sem valor numérico e não vira inconsistência.

Nenhum desses vira inconsistência no log — são reconhecidos por `classificar_disponibilidade`, só não têm um valor numérico de disponibilidade. O site (`vencimentos.py`) hoje só tem 3 abas fixas (Hora/Pouso/Calendário, conforme pedido original do Wallace) — itens desses tipos entram na contagem total de itens da base, mas não aparecem em nenhuma aba específica ainda (`_status_vencimento` usa o próprio nome do tipo como situação, pra não travar nem hardcodar uma string por tipo novo). Se aparecer mais operador com esses padrões, ou se o Wallace quiser vê-los numa aba própria, é só pedir.

### Interpretação de valor e data (`vencimentos_parse.py`, compartilhado com o TMOT)

Mesma lógica do TMOT (Hora = timedelta ou "HH:MM" texto; Pouso = número puro ou "P"/"Pouso(s)"; Calendário = "M"/"Mês(es)"/"D"/"Dia(s)"/mês+dia combinados, tudo convertido pra dias), mais um parser de data que aceita `DD/MM/AAAA` **ou** abreviação portuguesa do mês + ano (`out/2033`, `mar/2028`).

`AERONAVE` vem como "FAB2723" ou "FAB 2742" — normalizado pra matrícula pura ("2723").

### O que extrair

`extrair_vencimentos_operadores.py` lê os arquivos salvos em `01_Bases_Originais/Vencimentos/Operadores/<OPERADOR>/` (registrados manualmente no dicionário `REGISTRO` do script — atualizar ali quando buscar um arquivo novo) e gera `02_Dados_Tratados/base_vencimentos_operadores.xlsx`, aba **Operadores**: operador, mês de origem, arquivo de origem, seção da planilha (referência), especialidade, nomenclatura, PN, SN, matrícula, tipo de vencimento, disponibilidade (valor e texto), data de vencimento, vencido.

## Site — o que foi pedido (Wallace)

* Dividir em 3 partes: vencimento por hora, por pouso, por calendário.
* Em cada parte, uma **linha do tempo arrastável** — um filtro de intervalo (slider) pra selecionar uma faixa de horas/pousos/dias e ver só os itens naquela faixa.
* A parte "Operadores" fica de fora por enquanto (fonte ainda não definida) — só um card clicável reservando o lugar.

## Filtro inicial da aba Operadores (2026-07-16)

Pedido do Wallace: ajustar o filtro inicial (o padrão ao abrir a tela, não
trava — tudo continua editável) das 3 abas (Por hora/Por pouso/Por
calendário) dentro de Vencimentos → Operadores:

1. **Aeronave**: só as aeronaves **dentro do contrato** vêm pré-selecionadas
   (cruzando `matricula` com `rac_aeronaves["contrato"]`, mesmo campo usado
   no RAC/Dashboard Geral) — as fora do contrato ficam de fora do padrão,
   mas dá pra adicionar de volta no multiselect.
2. **Situação**: só **Vencido** e **Próximo** vêm marcados por padrão — os
   outros valores possíveis (`Ok`, `Condição`, `Não instalado`, `Não
   aplicável`, ver seção "Tipos de vencimento especiais" acima) ficam fora
   do padrão, mas continuam no multiselect pra quem quiser ver.
3. **Nomenclatura — checkbox "Ocultar motor/hélice"** (marcado por padrão):
   esconde itens de motor/hélice, já cobertos pela página **Motores**.
   Confirmado com o Wallace que é por **conteúdo** (não só início do texto)
   — por isso "BERÇO DO MOTOR" também entra (contém "MOTOR"), mesmo não
   começando com o termo. Termos usados (`TERMOS_MOTOR_HELICE_OCULTOS` em
   `vencimentos.py`): DISK, ANEL DO, ENGI, MOTOR, HUB, IMPELLER, HÉLICE, KIT
   HSI. **"ENGI" (não "ENGINE")** de propósito — a nomenclatura
   `RING AY-ENGI` vem truncada na própria fonte (falta o "NE" final), e sem
   isso esse item não seria escondido. `RING SNAP – ANEL FRENO` (peça de
   freio) fica de fora do padrão de propósito — não contém nenhum desses
   termos. 131 dos 780 itens da base (na conferência de 2026-07-16) batem
   com algum termo.
