# Instruções — Atualizações (agendamento automático + sob demanda)

## Status atual (o que está ativo hoje)

Os botões "🔄 Atualizar dados" (Contrato 005 e Coordenadoria) continuam como
sempre foram: só reprocessam localmente o que já está em
`01_Bases_Originais/` — não buscam nada novo do Drive sozinhos.

Buscar dados novos do Drive é feito pelo **Claude, automaticamente, por
agendamento** (`CronCreate`, ver seção abaixo) pras fontes com horário fixo,
ou **manualmente, quando o Wallace pedir na conversa**, pras demais.

**Tentativa anterior descartada:** a Fase 1 chegou a dar ao próprio site uma
credencial própria do Google (conta de serviço) com botões individuais de
"Atualizar X" no dashboard — foi revertida a pedido do Wallace (o problema
real foi um bug de UX: `st.rerun()` era chamado logo após mostrar um erro,
apagando a mensagem antes de ser lida, e parecendo que "quebrou tudo"). O
código de infraestrutura (`shared/drive_sync.py`, `shared/estado.py`,
`atualizar_do_drive()` nos 3 extratores do Contrato 005) continua no
projeto, mas **não está conectado a nenhum botão** — só é usado se/quando
decidirmos retomar essa abordagem.

## Agendamento — decisão pendente (retomar em 2026-07-06)

Tentamos criar 3 jobs de agendamento (`CronCreate`) em 2026-07-05:

| Fonte | Área | Dias | Horário |
|---|---|---|---|
| Disponibilidade Diária | Coordenadoria | Segunda a sexta | 10h |
| Emergências | Contrato 005 | Segunda a sexta | 12h |
| Pagamentos | Contrato 005 | Toda segunda | 10h |
| Reparáveis | Contrato 005 | — | Manual (Wallace avisa na conversa) |
| Vencimentos TMOT | Coordenadoria | — | Manual (Wallace avisa na conversa) |
| RAC, Vencimentos por Operador | Coordenadoria | — | Manual (ainda não definido) |

**Foram cancelados antes de valer a pena manter**, porque descobrimos um
problema sério: esses jobs só existem **dentro da sessão do Claude Code que
os criou** — se o Wallace desliga o PC ou fecha o terminal (o que ele faz
normalmente à noite), a sessão morre e o agendamento some por completo, não
"pausa". Não sobrevive a religar o computador. Isso não resolve o pedido
original (rodar sozinho, mesmo desligando à noite).

**Duas saídas discutidas:**
1. **Configuração de verdade** (conta de serviço do Google + agendamento no
   próprio Mac via `cron`/`launchd`) — roda de verdade sozinho, sobrevive a
   desligar o PC (só precisa o Mac estar ligado no horário agendado, não
   precisa do Claude Code aberto). Dá mais trabalho de configurar (Fase 0,
   ~15min, ver seção "Arquitetura da tentativa anterior" abaixo — o código
   `shared/drive_sync.py`/`shared/estado.py` já está pronto pra isso).
2. **Manual, sob pedido** — sem agendamento, volta a ser o Wallace pedindo
   na conversa quando quiser atualizar cada fonte (igual já era antes).

Decisão adiada — "amanhã retomamos essa parte" (Wallace, 2026-07-05).

## Arquitetura da tentativa anterior (Fase 1, dormant)

Antes o próprio site tinha sua **própria credencial do Google** (uma conta de
serviço, separada do acesso que o Claude tem ao Drive dentro da conversa) e
conseguia checar e baixar versões novas sozinho, quando o usuário clicava em
"Atualizar X" — sem precisar pedir pro Claude. Essa parte foi revertida (ver
acima), mas o código continua disponível caso decidamos retomar.

Módulo compartilhado: `shared/drive_sync.py` (fala com o Drive) e
`shared/estado.py` (persiste status por fonte em JSON). Usados por ambas as
áreas (Contrato 005 e Coordenadoria) — ver `C-98A PAMALS/CLAUDE.md`.

## Configuração (feita uma única vez)

1. Criar um projeto no [Google Cloud Console](https://console.cloud.google.com/).
2. Ativar a **Google Drive API** nesse projeto.
3. Criar uma **conta de serviço** (IAM e administrador > Contas de serviço).
4. Gerar uma **chave JSON** pra essa conta de serviço.
5. Compartilhar (como Leitor/Visualizador) cada planilha/pasta do Drive que o
   site precisa acessar com o e-mail da conta de serviço
   (`...@...iam.gserviceaccount.com`).
6. Salvar o arquivo `.json` baixado em: **`C-98A PAMALS/.secrets/service_account.json`**
   (essa pasta está no `.gitignore` — nunca deve ser commitada nem compartilhada).

Sem esse arquivo no lugar, qualquer botão "Atualizar" mostra um erro claro
pedindo pra configurar a credencial — não trava o resto do site.

## Como cada botão funciona

1. Consulta os metadados do arquivo no Drive (`drive_sync.obter_metadados`) —
   nome e data de modificação mais recente.
2. Baixa o conteúdo (`drive_sync.baixar_arquivo`) — Planilhas Google nativas
   são exportadas como `.xlsx`; arquivos já enviados como `.xlsx`/`.ods`
   (caso dos Vencimentos por Operador) são baixados como estão.
3. Sobrescreve a cópia local em `01_Bases_Originais/`.
4. Roda o extrator já existente daquela fonte.
5. Grava o resultado em `estado_atualizacoes.json` (dentro de
   `02_Dados_Tratados/` de cada área): última versão remota, data/hora da
   atualização local, status (`atualizado`/`pendente`/`erro`), quantidade de
   registros, erro (se houver).

**Nenhum botão faz isso sozinho ao abrir a página** — só quando clicado.
"Última versão encontrada" reflete o que foi visto na última vez que o
botão foi clicado, não uma checagem em tempo real.

## Escopo por fonte (registrado em cada script/REGISTRO)

| Fonte | Tipo de arquivo no Drive | ID |
|---|---|---|
| Emergências (Contrato 005) | Planilha Google nativa | `1OuZK024q1kOkKEf6KN18yu2b33mCHwgZfnwFdpELieA` |
| Reparáveis (Contrato 005) | Planilha Google nativa | `1dy_U2Pu5mw6se_gsGvPnuiErKlUJbHnE743f5fnSQ4o` |
| Pagamentos (Contrato 005) | Planilha Google nativa | `1zV_SQKlcXVYeaqCbV0X-PiWnzdzOZPt5esaXp_4k6_o` |
| RAC (Coordenadoria) | Planilha Google nativa | ver `RAC_PLANILHA_URL` em `coordenadoria/utils.py` |
| Vencimentos TMOT (Coordenadoria) | Planilha Google nativa | ver `VENCIMENTOS_PLANILHA_URL` em `coordenadoria/utils.py` |
| Disponibilidade Diária (Coordenadoria) | Pasta (ano/mês/dia, Google Docs) | ainda não incorporado (Fase 3) |
| Vencimentos por Operador (Coordenadoria) | Arquivos por operador, `drive_file_id` no `REGISTRO` | ainda não incorporado (Fase 4) |

## Limitação conhecida — Vencimentos por Operador

O botão "Atualizar operador" (quando construído, Fase 4) só reconfere e
rebaixa o **mesmo arquivo já configurado** pra aquele operador (por ID fixo).
Ele não descobre sozinho um mês novo, uma pasta diferente, ou navega dentro
de abas escondidas — isso é uma tarefa manual, feita pelo Claude na conversa
(igual era feito antes desta funcionalidade existir), porque cada operador
manda num formato diferente e às vezes exige investigação (ver
`Coordenadoria/00_Instrucoes/vencimentos.md`).
