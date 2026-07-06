# Instruções — Atualizações (automação real, ativa desde 2026-07-06)

## Status atual

O site tem sua **própria credencial do Google** (conta de serviço
`pamals-drive-reader@pamals-drive-sync.iam.gserviceaccount.com`, chave em
`.secrets/service_account.json`, fora do git) e busca 3 fontes **sozinho,
todo dia útil, sem precisar de mim (Claude) numa conversa** — agendado no
próprio Mac do Wallace via `launchd`:

| Fonte | Dias | Horário | Script | Agendamento (`~/Library/LaunchAgents/`) |
|---|---|---|---|---|
| Disponibilidade Diária | Segunda a sexta | 10h | `Coordenadoria/05_Scripts/python/extrair_disponibilidade_diaria.py` | `com.pamals.disponibilidade.plist` |
| Emergências | Segunda a sexta | 12h | `Contrato 005/Dashboard/05_Scripts/python/extrair_emergencias.py` | `com.pamals.emergencias.plist` |
| Pagamentos | Toda segunda | 10h | `Contrato 005/Dashboard/05_Scripts/python/extrair_pagamentos.py` | `com.pamals.pagamentos.plist` |
| Reparáveis, Vencimentos (TMOT e por operador), RAC, Diagonal de Manutenção | — | — | Manual — Wallace pede na conversa | — |

Cada agendamento chama `shared/executar_atualizacao.py <fonte>`, que:
1. Roda `python3 <script> --atualizar-do-drive` (busca no Drive, sobrescreve
   a cópia local em `01_Bases_Originais/`, reprocessa).
2. Se algo mudou de verdade no repositório (`git status --porcelain` não
   vazio), commita e dá `git push` sozinho — o Streamlit Cloud detecta o
   push e reimplanta o app automaticamente (~1-2 min).
3. Registra tudo em `shared/automacao.log` (histórico simples, texto).

**Limitação real (do próprio macOS, não do nosso código):** `launchd` só
dispara se o Mac estiver ligado e acordado no horário exato — se estiver
desligado ou dormindo às 10h/12h, aquele dia simplesmente não roda (sem
"catch-up" automático depois). Não tem solução fácil pra isso sem deixar o
Mac ligado o dia todo.

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

## Configuração feita (2026-07-06, não precisa repetir)

1. Projeto `pamals-drive-sync` no Google Cloud Console, API do Drive ativada.
2. Conta de serviço `pamals-drive-reader` criada, chave JSON baixada e salva
   em `.secrets/service_account.json` (permissão 600, fora do git).
3. Compartilhado como Leitor com `pamals-drive-reader@pamals-drive-sync.iam.gserviceaccount.com`:
   pasta "Atualização de Disponibilidade", planilha "Prazo das emergências - C-98",
   planilha "005/CELOG-PAMALS/2025 online".
4. 3 arquivos `.plist` em `~/Library/LaunchAgents/`, carregados com
   `launchctl load`.

Se precisar adicionar uma nova fonte ao agendamento: repetir o passo 3 (Share
com o e-mail da conta de serviço) pra fonte nova, criar a função
`atualizar_do_drive()` no extrator dela (mesmo padrão dos 3 já feitos), e um
novo `.plist` em `~/Library/LaunchAgents/`.

## Escopo por fonte — IDs conhecidos

| Fonte | ID/pasta no Drive |
|---|---|
| Emergências (Contrato 005) | `1OuZK024q1kOkKEf6KN18yu2b33mCHwgZfnwFdpELieA` |
| Reparáveis (Contrato 005) | `1dy_U2Pu5mw6se_gsGvPnuiErKlUJbHnE743f5fnSQ4o` |
| Pagamentos (Contrato 005) | `1zV_SQKlcXVYeaqCbV0X-PiWnzdzOZPt5esaXp_4k6_o` |
| RAC (Coordenadoria) | ver `RAC_PLANILHA_URL` em `coordenadoria/utils.py` |
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
