# Instruções — Atualizações (automação real, ativa desde 2026-07-06)

## Status atual

O site tem sua **própria credencial do Google** (conta de serviço
`pamals-drive-reader@pamals-drive-sync.iam.gserviceaccount.com`, chave
guardada como Secret do GitHub, nunca no código) e busca 4 fontes **sozinho,
rodando na nuvem do GitHub (GitHub Actions)** — não depende do Mac do
Wallace estar ligado, nem de internet dele, nem de mim (Claude) numa
conversa. Definido em `.github/workflows/atualizacoes.yml`:

| Fonte | Dias | Horário | Script |
|---|---|---|---|
| Disponibilidade Diária | Segunda a sexta | 10h | `Coordenadoria/05_Scripts/python/extrair_disponibilidade_diaria.py` |
| Emergências | Segunda a sexta | 12h | `Contrato 005/Dashboard/05_Scripts/python/extrair_emergencias.py` |
| RAC | Segunda a sexta | 12h (junto com Emergências) | `Coordenadoria/05_Scripts/python/extrair_rac.py` |
| Pagamentos | Toda segunda | 10h | `Contrato 005/Dashboard/05_Scripts/python/extrair_pagamentos.py` |
| Reparáveis, Vencimentos (TMOT e por operador), Diagonal de Manutenção | — | — | Manual — Wallace pede na conversa |

Cada horário do cron chama `shared/executar_atualizacao.py <fonte>` (uma vez
por fonte daquele horário — 12h roda emergencias e rac em sequência), que:
1. Roda `python3 <script> --atualizar-do-drive` (busca no Drive, sobrescreve
   a cópia local em `01_Bases_Originais/`, reprocessa).
2. Se algo mudou de verdade no repositório (`git status --porcelain` não
   vazio), commita e dá `git push` sozinho — o Streamlit Cloud detecta o
   push e reimplanta o app automaticamente (~1-2 min).
3. Registra tudo em `shared/automacao.log` (histórico simples, texto) —
   dentro do runner do GitHub, então só aparece no log da própria execução
   em Actions, não fica salvo localmente no Mac.

Também dá pra rodar qualquer uma das 4 fontes **na hora**, manualmente, sem
esperar o horário — aba "Actions" do GitHub → "Atualizações automáticas" →
"Run workflow" → escolher a fonte.

**Histórico:** antes disso (2026-07-06, mesmo dia), essas 3 primeiras fontes
rodavam via `launchd` no Mac do Wallace — funcionava, mas só disparava se o
Mac estivesse ligado e acordado no horário exato. Migrado pra GitHub Actions
a pedido do Wallace (autonomia total); os `.plist` locais foram desativados
e removidos.

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

## Configuração feita (não precisa repetir)

1. Projeto `pamals-drive-sync` no Google Cloud Console, API do Drive ativada.
2. Conta de serviço `pamals-drive-reader` criada, chave JSON baixada.
3. A chave vive como Secret do GitHub (`GOOGLE_SERVICE_ACCOUNT_JSON`, em
   Settings → Secrets and variables → Actions do repositório) — o workflow a
   escreve em `.secrets/service_account.json` só dentro do runner, na hora de
   rodar; nunca fica salva no repositório.
4. Compartilhado como Leitor com `pamals-drive-reader@pamals-drive-sync.iam.gserviceaccount.com`:
   pasta "Atualização de Disponibilidade", planilha "Prazo das emergências - C-98",
   planilha "005/CELOG-PAMALS/2025 online", planilha "Análise crítica de
   emergências C-98 2026" (RAC, adicionada em 2026-07-06).
5. `.github/workflows/atualizacoes.yml` no repositório, com os 3 horários de
   cron + `workflow_dispatch` manual.

Se precisar adicionar uma nova fonte ao agendamento: repetir o passo 4 (Share
com o e-mail da conta de serviço) pra fonte nova, criar a função
`atualizar_do_drive()` no extrator dela (mesmo padrão das já feitas), adicionar
a fonte em `shared/executar_atualizacao.py` (dict `SCRIPTS`) e em
`.github/workflows/atualizacoes.yml` (lista de `options` do `workflow_dispatch`
+ o `if`/`elif` que decide qual fonte roda em qual horário de cron).

## Escopo por fonte — IDs conhecidos

| Fonte | ID/pasta no Drive |
|---|---|
| Emergências (Contrato 005) | `1OuZK024q1kOkKEf6KN18yu2b33mCHwgZfnwFdpELieA` |
| Reparáveis (Contrato 005) | `1dy_U2Pu5mw6se_gsGvPnuiErKlUJbHnE743f5fnSQ4o` |
| Pagamentos (Contrato 005) | `1zV_SQKlcXVYeaqCbV0X-PiWnzdzOZPt5esaXp_4k6_o` |
| RAC (Coordenadoria) | `1o8supQLcHkC1WZZCZDAtuRKGB_VUlQ8qBlYj7racsGQ` |
| Vencimentos TMOT (Coordenadoria) | ver `VENCIMENTOS_PLANILHA_URL` em `coordenadoria/utils.py` |
| Disponibilidade Diária (Coordenadoria) | pasta raiz `1JLrUGunWo5ABsR3WuYo88b2WD4QWoxNH` → ano → mês |
| Vencimentos por Operador (Coordenadoria) | `drive_file_id` no `REGISTRO` — ainda não incorporado |

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
