# Instruções — Atualizações (automação real, ativa desde 2026-07-06)

## Status atual

O site tem sua **própria credencial do Google** (conta de serviço
`pamals-drive-reader@pamals-drive-sync.iam.gserviceaccount.com`, chave
guardada como Secret do GitHub, nunca no código) e busca 12 fontes **sozinho,
rodando na nuvem do GitHub (GitHub Actions) e no Mac do Wallace, ao mesmo
tempo** — não depende do Mac estar ligado (o GitHub cobre sozinho), mas se
estiver ligado no horário, busca também.

**Desde 2026-07-09 (a pedido do Wallace): todas as fontes rodam juntas,
de 2 em 2 horas, seg-sex, das 8h às 20h** (`todos` — não é mais 1 horário
por fonte). O motivo: o agendamento gratuito do GitHub atrasa às vezes (ver
"Limitação conhecida" abaixo) — rodando com mais frequência, mesmo que uma
vez atrase ou falhe, a próxima (2h depois) já pega o dado atualizado. Sem
problema rodar sem ter nada novo pra buscar — cada fonte só commita de
verdade se algo mudou (`git status --porcelain`), então rodar toda hora não
gera commit/redeploy à toa.

| Fonte | Script |
|---|---|
| Disponibilidade Diária | `Coordenadoria/05_Scripts/python/extrair_disponibilidade_diaria.py` |
| Emergências | `Contrato 005/Dashboard/05_Scripts/python/extrair_emergencias.py` |
| RAC | `Coordenadoria/05_Scripts/python/extrair_rac.py` |
| Vencimentos TMOT | `Coordenadoria/05_Scripts/python/extrair_vencimentos.py` |
| Pagamentos | `Contrato 005/Dashboard/05_Scripts/python/extrair_pagamentos.py` |
| MTA | `Projetos/05_Scripts/python/extrair_mta.py` |
| TPJL | `Projetos/05_Scripts/python/extrair_tpjl.py` |
| TPJL — Consumo/Estoque/Solicitações | `Projetos/05_Scripts/python/extrair_tpjl_extras.py` |
| Reparáveis | `Contrato 005/Dashboard/05_Scripts/python/extrair_reparaveis.py` |
| Devoluções/Empréstimos | `Contrato 005/Dashboard/05_Scripts/python/extrair_devolucoes.py` |
| Motores | `Coordenadoria/05_Scripts/python/extrair_motores.py` |
| Reajuste | `Contrato 005/Dashboard/05_Scripts/python/extrair_reajuste.py` |
| Vencimentos por Operador, Diagonal de Manutenção | Manual — Wallace pede na conversa |

**Motores entrou em 2026-07-15** (planilha pessoal do Wallace "MOTORES
C-98", compartilhada com a conta de serviço nessa data — ver
`Coordenadoria/00_Instrucoes/motores.md`). Também grava 2 snapshots diários
(`historico_motores_situacao.csv`/`historico_motores_diagonal.csv`), mesmo
padrão do RAC/MTA/TPJL.

Reparáveis e Devoluções entraram na automação em 2026-07-10 (antes eram
manuais) pra alimentar o **controle de data global** do Contrato 005 — ver
`Contrato 005/Dashboard/00_Instrucoes/analise_periodo.md`. Também passaram a
gravar snapshot diário (`historico_reparaveis.csv`/`historico_devolucoes.csv`),
mesmo padrão do RAC/Emergências/MTA/TPJL.

MTA e TPJL também gravam um snapshot diário (`historico_mta.csv`/
`historico_tpjl.csv` em `Projetos/02_Dados_Tratados/`) toda vez que rodam —
alimenta a "barra temporal" (comparação com dias anteriores) no dashboard,
pedida pelo Wallace em 2026-07-09. Ver `Projetos/CLAUDE.md`.

`shared/executar_atualizacao.py todos` roda as 12 em sequência (uma de cada
vez, sincronizando com o GitHub antes de cada uma — ver `_sincronizar_com_remoto`).
Pra cada fonte:
1. Roda `python3 <script> --atualizar-do-drive` (busca no Drive, sobrescreve
   a cópia local em `01_Bases_Originais/`, reprocessa).
2. Se algo mudou de verdade no repositório, commita e dá `git push` sozinho
   — o Streamlit Cloud detecta o push e reimplanta o app automaticamente
   (~1-2 min).
3. Registra tudo em `shared/automacao.log`.

Também dá pra rodar `todos` ou uma fonte específica **na hora**, manualmente
— aba "Actions" do GitHub → "Atualizações automáticas" → "Run workflow" →
escolher (padrão: `todos`).

## GitHub Actions + launchd no Mac, ao mesmo tempo

Desde 2026-07-08, os dois caminhos rodam juntos (não é mais um ou outro):

- **GitHub Actions** (`.github/workflows/atualizacoes.yml`): 1 cron só,
  `7 11,13,15,17,19,21,23 * * 1-5` (UTC) = 8h07, 10h07, 12h07, 14h07, 16h07,
  18h07, 20h07 local, seg-sex. Minuto quebrado (não hora cheia) de propósito
  — reduz o atraso do agendamento gratuito (ver "Limitação conhecida").
- **Mac (`launchd`)**: 1 arquivo só, `com.pamals.atualizar_tudo.plist`, nos
  mesmos 7 horários (8h, 10h, 12h, 14h, 16h, 18h, 20h local, seg-sex), na
  hora cheia (minuto :00, diferente do GitHub de propósito — reduz a chance
  de os dois tentarem commitar no mesmo segundo).

Antes de 2026-07-09 cada fonte tinha seu próprio horário/`.plist` — foi
simplificado pra "todas de 2 em 2 horas" a pedido do Wallace.

**Proteção adicionada em `shared/executar_atualizacao.py`:** antes de rodar a
extração, o script agora sincroniza com o GitHub (`git fetch` + `git reset
--hard origin/main`) — mas **só se não houver alteração local pendente**
(nunca mexe em trabalho manual em andamento, tipo uma sessão do Claude Code
aberta com edições não commitadas). Isso evita que Mac e GitHub divirjam
quando os dois rodam a mesma fonte em horários próximos — problema real que
aconteceu em 2026-07-08 antes dessa proteção existir (tive que reconciliar
manualmente um push rejeitado por non-fast-forward).

## Limitação conhecida — atraso do agendamento gratuito do GitHub

Confirmado na prática em 2026-07-07: os horários agendados pra 13h/15h UTC
só rodaram de verdade às 19h25/21h06 UTC — **~6h de atraso**. O GitHub avisa
que agendamentos gratuitos podem atrasar em horários de pico, principalmente
na **hora cheia** (todo mundo agenda "às 13h00", por exemplo). Em
2026-07-08, os horários foram trocados pra minutos quebrados (recomendação
oficial do GitHub pra reduzir esse atraso). Mesmo assim, não existe garantia
de horário exato num plano gratuito — por isso, em 2026-07-09, passou a
rodar **todas as fontes de 2 em 2 horas** (seg-sex, 8h-20h) em vez de um
horário fixo por fonte: mesmo que uma execução atrase ou falhe, a próxima
(2h depois) cobre. Se um dia isso ainda não for rápido o suficiente (ex.:
emergência real acontecendo agora), o caminho mais confiável continua sendo
pedir pra mim buscar na conversa, ou disparar manualmente (aba Actions →
"Run workflow").

## Falha observada em 2026-07-07 — 1ª execução agendada não disparou

No dia seguinte a criar o workflow, o cron das 10h (Disponibilidade Diária)
simplesmente não rodou — confirmado via `GET /repos/.../actions/runs`
(nenhuma execução registrada, nem erro, só a manual do dia anterior). O
workflow estava ativo e configurado certo; isso é uma instabilidade
conhecida do GitHub Actions com a *primeira* ocorrência de um `schedule`
recém-criado (`da3cf8e`, criado em 2026-07-06 depois que o horário das 10h
daquele dia já tinha passado — então 07/07 10h seria o 1º disparo real desse
cron). Resolvido rodando a busca manualmente na conversa. **Se isso
acontecer de novo em dias seguintes**, não é mais esperado — investigar de
verdade (workflow desativado, erro de sintaxe no yaml, etc.), não presumir
que é só o mesmo problema.

Esse mesmo episódio expôs um bug real de parsing (não relacionado ao
agendamento) — ver "Bug corrigido em 2026-07-07" em
`Coordenadoria/00_Instrucoes/disponibilidade_diaria.md`.

## Como cada fonte busca (regra por tipo)

1. `drive_sync.obter_metadados` — checa nome/data de modificação mais recente.
2. `drive_sync.baixar_arquivo` — Planilhas Google nativas (Emergências,
   Pagamentos, RAC, Vencimentos TMOT) exportam como `.xlsx`; a
   Disponibilidade Diária (Google Docs) exporta como texto puro.
   Disponibilidade Diária também precisa navegar pastas (ano → mês →
   documento do dia, via `drive_sync.listar_pasta`) — o nome da pasta do mês
   muda todo mês (ex.: "07 Julho"), por isso o código busca por prefixo do
   número do mês atual, não por um ID fixo.
3. Sobrescreve a cópia local (Disponibilidade Diária é a exceção — nunca
   sobrescreve relatório antigo, sempre salva um arquivo novo por dia).
4. Roda o extrator já existente daquela fonte.
5. Grava o resultado em `estado_atualizacoes.json` (dentro de
   `02_Dados_Tratados/` de cada área): última versão remota, data/hora da
   atualização local, status (`atualizado`/`pendente`/`erro`/`sem_novidade`),
   quantidade de registros, erro (se houver).

Pra RAC especificamente: cada rodada também acrescenta um snapshot do dia
(item a item, por aeronave x PN) em `Coordenadoria/02_Dados_Tratados/historico_rac.csv`
— nunca sobrescreve dias anteriores, só o snapshot do próprio dia (se rodar
2x no mesmo dia). Esse arquivo alimenta a aba "Histórico" na visão individual
de cada aeronave no RAC. Ver `Coordenadoria/00_Instrucoes/rac.md`.

Pra Emergências especificamente: mesmo padrão, mas o snapshot é da lista de
emergências em aberto (`Contrato 005/Dashboard/02_Dados_Tratados/historico_emergencias.csv`)
— alimenta a seção "Novidades desde a última atualização" na tela
"Emergências Abertas" (o que entrou/saiu da lista desde o snapshot anterior).
Ver `Contrato 005/Dashboard/00_Instrucoes/emergencias.md`. Cada rodada de
Emergências também: (1) regenera o histórico completo (abertas+concluídas,
usado por "Emergências Totais") e (2) recalcula o Cômputo Mensal do mês
atual (matriz da Pré-RMA aba 1.2, dentro de "Fechamento Mensal") — nenhuma
das duas tem agendamento próprio, andam de carona com Emergências. Ver
`Contrato 005/Dashboard/00_Instrucoes/computo_mensal.md`.

Pra Disponibilidade Diária especificamente: se não houver relatório novo
ainda (ex.: rodou antes de alguém postar o relatório do dia, ou é fim de
semana — só sai relatório de segunda a sexta, confirmado pelo Wallace), o
status vira `sem_novidade` — não é erro, só não tem nada novo pra buscar
ainda. A comparação "mudanças desde [data anterior]" no site sempre compara
com o **último relatório que existe de verdade** (não um "ontem" fixo) — se
hoje é segunda e só tem relatório até sexta, compara com sexta mesmo.

## Botões manuais no site

Os botões "🔄 Atualizar dados" que ainda existem no site (pras fontes sem
agendamento) continuam só reprocessando localmente o que já está em
`01_Bases_Originais/` — não buscam nada novo sozinhos. Buscar uma versão
nova dessas fontes continua sendo pedir na conversa.

## Botões "Atualizar X" (MTA, TPJL, Emergências, Reparáveis, Pagamentos) —
## 3 lugares onde a credencial do Google precisa existir

Esses botões **buscam de verdade** no Drive (`--atualizar-do-drive`),
diferente dos botões manuais acima. Rodam o extrator como um **subprocesso
separado** (`subprocess.run`), que só enxerga credencial em **arquivo**, não
em `st.secrets` (que só existe dentro do processo Streamlit que o chamou).
Por isso a credencial precisa "existir" de 3 formas diferentes, uma por
ambiente de execução:

1. **Mac do Wallace** — o arquivo `.secrets/service_account.json` já existe
   direto no disco (colocado manualmente uma vez, no início do projeto).
2. **GitHub Actions** — o workflow escreve esse mesmo arquivo dentro do
   runner, toda execução, a partir do Secret `GOOGLE_SERVICE_ACCOUNT_JSON`
   do repositório (ver "Configuração feita" abaixo).
3. **Streamlit Cloud (site publicado)** — descoberto quebrado em 2026-07-10
   (Wallace clicou "Atualizar MTA" no site e deu erro "Credencial não
   encontrada"): o app publicado nunca tinha esse arquivo, porque só o
   GitHub Actions escrevia ele, não o Streamlit Cloud. Corrigido com
   `shared/drive_sync.garantir_credencial_arquivo()` — chamada antes de
   cada `subprocess.run` nos 3 `atualizar_drive.py` (Contrato 005,
   Projetos) — que cria o arquivo sozinha a partir de `st.secrets` **se
   ele ainda não existir**. Só funciona se o Secret
   `GOOGLE_SERVICE_ACCOUNT_JSON` também estiver salvo nas **Secrets do
   próprio Streamlit Cloud** (Settings → Secrets do app — sistema
   **separado** do GitHub Secrets, precisa configurar os dois; feito em
   2026-07-10).

## Configuração feita (não precisa repetir)

1. Projeto `pamals-drive-sync` no Google Cloud Console, API do Drive ativada.
2. Conta de serviço `pamals-drive-reader` criada, chave JSON baixada.
3. A chave vive como Secret em **2 lugares separados** (GitHub e Streamlit
   Cloud não compartilham nada — precisa configurar nos dois):
   - Secret do GitHub (`GOOGLE_SERVICE_ACCOUNT_JSON`, em Settings → Secrets
     and variables → Actions do repositório) — o workflow a escreve em
     `.secrets/service_account.json` só dentro do runner, na hora de rodar.
   - Secret do Streamlit Cloud (app → Settings → Secrets, mesma chave
     `GOOGLE_SERVICE_ACCOUNT_JSON`, valor colado como string TOML multi-linha
     `'''...'''`) — configurado em 2026-07-10, necessário pros botões
     "Atualizar X" funcionarem no site publicado (ver seção acima).
   Nunca fica salva no repositório em texto puro nos dois casos.
4. Compartilhado como Leitor com `pamals-drive-reader@pamals-drive-sync.iam.gserviceaccount.com`:
   pasta "Atualização de Disponibilidade", planilha "Prazo das emergências - C-98",
   planilha "005/CELOG-PAMALS/2025 online", planilha "Análise crítica de
   emergências C-98 2026" (RAC, 2026-07-06), planilha "Vencimentos" (TMOT,
   2026-07-09).
5. `.github/workflows/atualizacoes.yml` no repositório — 1 cron (de 2 em 2h,
   seg-sex) + `workflow_dispatch` manual (padrão `todos`).
6. `~/Library/LaunchAgents/com.pamals.atualizar_tudo.plist` no Mac, nos
   mesmos horários (minuto diferente do GitHub de propósito).

Se precisar adicionar uma nova fonte ao agendamento: repetir o passo 4 (Share
com o e-mail da conta de serviço) pra fonte nova, criar a função
`atualizar_do_drive()` no extrator dela (mesmo padrão das já feitas), e
adicionar a fonte em `shared/executar_atualizacao.py` (dict `SCRIPTS`) — ela
já entra automaticamente em `todos`. Só precisa mexer em
`.github/workflows/atualizacoes.yml` se quiser adicionar a opção no
`workflow_dispatch` manual (não obrigatório, é só pra poder rodar ela sozinha
sob demanda).

## Escopo por fonte — IDs conhecidos

| Fonte | ID/pasta no Drive |
|---|---|
| Emergências (Contrato 005) | `1OuZK024q1kOkKEf6KN18yu2b33mCHwgZfnwFdpELieA` |
| Reparáveis (Contrato 005) | `1dy_U2Pu5mw6se_gsGvPnuiErKlUJbHnE743f5fnSQ4o` |
| Pagamentos (Contrato 005) | `1zV_SQKlcXVYeaqCbV0X-PiWnzdzOZPt5esaXp_4k6_o` |
| RAC (Coordenadoria) | `1o8supQLcHkC1WZZCZDAtuRKGB_VUlQ8qBlYj7racsGQ` |
| Vencimentos TMOT (Coordenadoria) | `178vQ-lRP52sw30kQArqcsQGXfj2OLblaFCgjIXWFIl8` — compartilhada e automatizada em 2026-07-09 |
| Disponibilidade Diária (Coordenadoria) | pasta raiz `1JLrUGunWo5ABsR3WuYo88b2WD4QWoxNH` → ano → mês |
| Vencimentos por Operador (Coordenadoria) | `drive_file_id` no `REGISTRO` — ainda não incorporado |
| Devoluções/Empréstimos (Contrato 005) | `1czUWXVjQt7fPz7GJgdPp3rsxPn_5Uck44voBsJIiRWI` — manual, ver `Contrato 005/Dashboard/00_Instrucoes/emprestimos.md` |
| MTA (Projetos) | `1ZdV1PX4ujqPgQNGk7f_WPkvA42aArVkGS59TVW78zhs` — compartilhada e automatizada em 2026-07-09 |
| TPJL 2025 (Projetos) | `1zkBB77PXvzRTg-8n-tgNAYX8lJB8KozPvuyGiNtARsA` — compartilhada e automatizada em 2026-07-09 |
| TPJL 2026 (Projetos) | `1Mf_R70IDJ9auysySW1oATGt3TSrPZE081-O3nB930lc` — compartilhada e automatizada em 2026-07-09 |
| TPJL Consumo (Projetos) | pasta `1ERwy2djU0nvp4yzH-PG6PLFagfPt-B6N` (subpasta de "Planilhas TPLJ") — pega sempre o arquivo mais recente |
| TPJL Estoque (Projetos) | pasta `1bW2czO8BixxvW5DTpH_gtvSpf-0R5qGy` (subpasta de "Planilhas TPLJ") — pega sempre o arquivo mais recente |
| TPJL Solicitações (Projetos) | pasta `1Tn9OxLm2NBG8UD3If44I4QqgtBpAw0ht` (subpasta de "Planilhas TPLJ") — pega sempre o arquivo mais recente |
| Motores (Coordenadoria) | planilha pessoal do Wallace, compartilhada e automatizada em 2026-07-15 |
| Reajuste (Contrato 005) | `1R32r4rscXTYGe98R1AFUUG8hqZD-GaWY` — planilha pessoal do Wallace, compartilhada e automatizada em 2026-07-16 |

## Achado e corrigido em 2026-07-17 — ordem RAC x Emergências no ciclo

Wallace corrigiu na planilha do RAC uma classificação errada (4 aeronaves
que tinham sido marcadas "Dentro do contrato" por engano voltaram pra
"Fora do contrato"). Rodei a busca manual do RAC na hora e o Cômputo
Mensal (Fechamento Mensal, Contrato 005) recalculou certo (23 aeronaves
pontuadas). **Mas o ciclo automático seguinte trouxe de volta o número
errado (27)** — causa: dentro de `SCRIPTS`, "emergencias" rodava ANTES de
"rac", e `calcular_mes()` (Cômputo Mensal) é disparado automaticamente
*dentro* de `extrair_emergencias.atualizar_do_drive()` — ou seja, o
recálculo lia a classificação do RAC de ANTES da correção chegar (o "rac"
daquele mesmo ciclo só rodava depois). Corrigido: `SCRIPTS` agora tem
"rac" antes de "emergencias", pra qualquer mudança de classificação
(dentro/fora do contrato) já valer no mesmo ciclo em que é buscada, não só
no próximo (até 2h de atraso a mais).

## Achado e corrigido em 2026-07-16 — TPJL Extras fora do agendamento

Numa checagem geral do site (pedido do Wallace: "checa todo nosso site,
documentacao, atualizacao"), achado que `extrair_tpjl_extras.py`
(Consumo/Estoque/Solicitações) já tinha `atualizar_do_drive()` escrito
desde 2026-07-14, mas nunca tinha sido cadastrado em `SCRIPTS` de
`shared/executar_atualizacao.py` — por isso nunca rodava no ciclo de 2 em 2
horas, só ficou parado na primeira extração manual (`estado_atualizacoes.json`
mostrava `tpjl_extras` desatualizado há 2 dias enquanto as outras fontes do
mesmo arquivo mostravam poucos minutos). Adicionado ao dict `SCRIPTS` e à
opção do `workflow_dispatch`.

Primeiro teste real (`--atualizar-do-drive` manual) deu erro 404 nos 3
`drive_file_id` fixos — mas o Wallace explicou o motivo: **essa fonte não
funciona por sobrescrita de arquivo, ele baixa manualmente do sistema de
origem e sobe um arquivo NOVO em cada subpasta a cada atualização** (nome
com timestamp, ex. `relatorio_consumo_20260713_235207.xlsx`, ID novo toda
vez). Corrigido: `FONTES_EXTRAS` (`projetos/config/tpjl_config.py`) trocou
`drive_file_id` fixo por `drive_folder_id` (as 3 subpastas de "Planilhas
TPLJ" — Consumo/Estoque/Solicitações), e `atualizar_do_drive()` agora lista
a subpasta (`drive_sync.listar_pasta`) e sempre baixa o arquivo com
`modifiedTime` mais recente — mesmo padrão já usado pela Disponibilidade
Diária. Testado de verdade (`--atualizar-do-drive`): funcionou, `status:
"atualizado"` no estado.

## Limitação conhecida — Vencimentos por Operador e Diagonal de Manutenção

Continuam manuais. Cada operador manda num formato/pasta diferente e às
vezes exige investigação (aba escondida, arquivo corrompido, mês anterior) —
isso é trabalho de julgamento feito por mim na conversa, não dá pra
automatizar num agendamento fixo. Ver `Coordenadoria/00_Instrucoes/vencimentos.md`
e `diagonal_manutencao.md`.

## Histórico — tentativas anteriores (mantido por contexto)

* **UI com botão + credencial própria (Fase 1, 2026-07-04/05):** o site
  chegou a ter botões individuais "Atualizar X" usando a mesma credencial —
  foi revertido a pedido do Wallace por um bug de UX (`st.rerun()` logo após
  erro apagava a mensagem, parecendo que "quebrou tudo"). O agendamento
  automático (este documento) substituiu essa abordagem — não precisa mais
  de botão, já roda sozinho.
* **Agendamento via `CronCreate` (sessão do Claude Code, 2026-07-05):**
  tentamos primeiro um agendamento "dentro da conversa" — descobrimos que
  esses jobs só existem enquanto a sessão do Claude Code ficar aberta (não
  sobrevive a desligar o PC), então foram cancelados antes de valer a pena
  manter. A automação de verdade (este documento) resolve isso de vez.
