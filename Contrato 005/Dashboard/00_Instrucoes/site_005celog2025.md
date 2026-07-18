# Instruções — site separado "005CELOG2025" (acesso da empresa)

## Pedido do Wallace (2026-07-18)

Dar acesso à empresa (VEE ONE) só à parte do Contrato 005, sem ela chegar
perto de Coordenadoria/Projetos. Perguntei se era melhor clonar em outro
site ou só colocar senha por área dentro do mesmo site — Wallace escolheu
**clonar** (deploy separado). Nome do site: **005CELOG2025** (tudo
maiúsculo, como pedido).

## Por que deploy separado (não senha por área no mesmo site)

Streamlit roda tudo num processo só — colocar senha só ao "entrar" numa
área dentro do MESMO app só esconde na tela, não isola de verdade (o
processo já carregou/tem acesso a tudo). Pra um terceiro externo (empresa),
isolamento de verdade é mais seguro: um processo Streamlit **separado**,
que nunca importa nem carrega nenhum código/dado de Coordenadoria ou
Projetos.

## Como funciona (sem duplicar código)

**Não é uma cópia do repositório** — é um **segundo app no Streamlit
Cloud**, apontando pro **mesmo repositório do GitHub**, só que com o
arquivo principal diferente:

- Site principal ("C-98A PAMA-LS"): `app.py` (raiz do repositório).
- Site da empresa ("005CELOG2025"): `Contrato 005/Dashboard/03_Dashboard/app.py`.

Esse segundo arquivo (`03_Dashboard/app.py`) já existia como "runner
standalone" (fallback pra rodar só o Contrato 005 localmente).

**Login por e-mail autorizado + senha única** (2026-07-18, decisão final
do Wallace — inicialmente ficou sem senha, depois: "vamos outorizar meu
email ... a pessoa coloca o email dela e a senha é c98pamals para todo
mundo", confirmado: "so no site do contrato", não mexe no site
principal). `EMAILS_AUTORIZADOS` (lista fixa no código, `app.py`):
- wallacedellaney@gmail.com
- paulo.souza@veeone.com.br
- rcarlos@veeone.com.br
- rezende@veeone.com.br
- claudio.almeida@veeone.com.br
- desiree.barreto@veeone.com.br
- jorgeleite@veeone.com.br

Todos usam a MESMA senha — secret `site_password` (valor `c98pamals`,
igual ao site principal, mas precisa ser colado de novo nos Secrets
**deste** app, não é compartilhado). Login checa e-mail (normalizado —
`.strip().lower()`) contra a lista **e** senha contra o secret; qualquer
um dos dois errado mostra mensagem de erro específica ("E-mail não
autorizado" / "Senha incorreta"). Pra adicionar/remover alguém, é só
editar o `set` `EMAILS_AUTORIZADOS` no código (não precisa de senha
individual por pessoa).

**"Lembrar meu e-mail" (2026-07-18)** — pedido do Wallace: "coloca opcao
para a pessoa salva o email dela e salvar a senha depois que digita".
Checkbox marcado por padrão depois do 1º login: guarda o e-mail em
`st.query_params` (fica na URL — se a pessoa favoritar/salvar o link com
o e-mail, ele já vem preenchido da próxima vez). **A senha não é salva
por nós de propósito** — não é seguro guardar senha em URL/query param;
o campo de senha continua sendo um `type="password"` padrão, que o
próprio navegador (gerenciador de senhas do Chrome/Safari/etc.) já
costuma oferecer pra salvar sozinho depois do primeiro login com
sucesso, sem precisar de nada extra no nosso código.

**Fluxo de 3 telas** (2026-07-18):
1. **Hero + "Entrar →"** (pedido do Wallace: "pode deixar aquele dasborad
   la inicial, clicando para entrar no contrato, com a foto do caravan e
   talz") — reaproveita `home_hero.py` do site principal (mesma foto do
   hangar/Caravan).
2. **Aviso de transparência + "Concordar e continuar →"** (pedido do
   Wallace: "quero colocar um aviso tambem quando clicar e a pessoa
   concordar" — texto fixo em `AVISO_TRANSPARENCIA`, avisando que os dados
   não substituem a informação oficial do fiscal, podem ter ajuste
   manual/pontos em tratativa, e indicando contato com o fiscal em caso de
   dúvida).
3. **Dashboard do Contrato 005** — só depois de "entrou" e "concordou"
   (`st.session_state`), sem senha por trás (é só uma tela de transição,
   não proteção de acesso).

**Páginas escondidas nesse deploy**: nenhuma, desde 2026-07-18. Antes disso,
"Fechamento Mensal" inteiro ficava escondido (Cômputo Mensal, Atrasos,
Apresentação RMA, Ata de Reunião) — pedido do Wallace: "tira no fechamento
mensal, apresntacao da rma" / "e tb tira a producao da ata". Ele voltou
atrás: "volta ele, so nao quero apresentacao rma e ata de reuniao(no site
do contrato), no outro c98 geral tudo" — agora "Fechamento Mensal" aparece
normalmente nos 2 sites, só que **dentro** dele as abas "Apresentação
(RMA)" e "Ata de Reunião" ficam escondidas neste deploy (só "Cômputo
Mensal" e "Atrasos" aparecem aqui); no site principal continuam as 4 abas.
`contrato_app.render()` mantém o parâmetro `paginas_ocultas` (hoje sem uso,
nenhuma página inteira é escondida — deixado no código caso precise
esconder outra página inteira no futuro); o corte fino das 2 abas é feito
dentro de `secoes/fechamento_mensal.py`, checando `dados["modo_externo"]`.

**Detalhe interno escondido dentro das páginas que continuam visíveis**
(`contrato_app.render(..., modo_externo=True)`, gravado em
`dados["modo_externo"]` pra cada seção conferir sozinha):
- **Painel "Fonte dos dados"** (rodapé) — pedido do Wallace: "tira a fonte
  de dados, desse".
- **Empenhos** (dentro de Pagamentos — expander inteiro + coluna
  "empenho_responsavel" da tabela principal) — pedido do Wallace: "tira
  empenho do pagamento tb, ela nao precis saber".

## Configuração no Streamlit Cloud (ação do Wallace)

Nome do app escolhido: **`contrato005`** (o Streamlit Cloud não aceita
nome/URL começando com número, por isso não deu pra usar "005celog2025"
como nome do app — o título "005CELOG2025" continua aparecendo dentro do
site, isso não muda).

1. Criar um **novo app** no Streamlit Cloud (share.streamlit.io → "New app").
2. Repositório: o mesmo do site principal (`wallacedellaney/c98a-pamals`).
3. Branch: `main`.
4. **Main file path**: `Contrato 005/Dashboard/03_Dashboard/app.py` (não
   `app.py` da raiz — esse é o site principal).
5. Nome do app / URL: `contrato005`.
6. **Secret deste app** (Settings → Secrets — **não é compartilhado** com
   o site principal, precisa ser colado de novo aqui):
   ```
   GOOGLE_SERVICE_ACCOUNT_JSON = '''
   { ... mesmo conteúdo já usado no site principal ... }
   '''
   ```
   Necessário pros botões "🔄 Atualizar dados", "Apresentação (RMA)" e
   "Ata de Reunião" (ver
   `atualizacoes.md`/`apresentacao_rma.md`/`ata_reuniao.md`) — sem ele,
   esses botões dão o mesmo erro de credencial já visto e corrigido no
   site principal.

## Atualização de dados — automática, sem configurar nada a mais

**Sim, atualiza sozinho** — confirmado com o Wallace ("vai atualizar ele
automatico ne?"). O site da empresa lê os mesmos arquivos de
`02_Dados_Tratados/` do mesmo repositório; o ciclo automático já existente
(GitHub Actions + Mac, de 2 em 2h, ver `00_Instrucoes/atualizacoes.md` da
raiz) já commita/dá push nesses arquivos — e como os 2 apps do Streamlit
Cloud observam o mesmo repositório, **os 2 reimplantam sozinhos** a cada
push, sem precisar de nenhuma automação nova nem de segunda configuração.

## O que a empresa vê

Só as abas do Contrato 005 (Visão Geral, Reparáveis, Emergências
Abertas/Totais, Análise de Período, Fechamento Mensal, Empréstimos,
Pagamentos, Reajuste) — sem botão "← Voltar ao menu" (não existe menu
principal nesse deploy, `render()` é chamado sem `ao_voltar`).

## Bug corrigido em 2026-07-18 — "Error installing requirements" no deploy

Primeiro deploy real falhou: `error: Failed to parse: '005/Dashboard/03_Dashboard/requirements.txt'`
(log completo em "Manage app" → terminal). Causa: existia um
`Contrato 005/Dashboard/03_Dashboard/requirements.txt` (cópia quase igual
ao da raiz, só faltando `odfpy`) — o Streamlit Cloud acha esse arquivo
primeiro (mesma pasta do main file) e monta o comando de instalação com o
caminho completo, mas **o espaço em "Contrato 005" quebra o parsing**
(vira 2 argumentos: "Contrato" e "005/Dashboard/..."). O site principal
nunca bateu nisso porque o `app.py` dele fica na raiz do repositório —
sem espaço no caminho até o `requirements.txt`.

**Corrigido**: apagado o `requirements.txt` local (não fazia falta, era
cópia incompleta do da raiz) — sem ele, o Streamlit Cloud sobe um nível
até achar o `requirements.txt` da raiz do repositório (sem espaço no
caminho, já testado e funcionando no site principal). Se um dia precisar
de um pacote só deste deploy, adicionar direto no `requirements.txt` da
raiz (compartilhado pelos 2 sites) em vez de recriar um local — evita
esse mesmo bug de novo.

## Bug corrigido em 2026-07-18 — seta de expandir sidebar aparecendo no hero

Wallace: "no dasborad do lado do aviao tem um uma seta de um lado e do
outro, tira isso kkk" — faltava `initial_sidebar_state="collapsed"` no
`st.set_page_config()` deste app (o site principal já tinha) — sem isso,
o Streamlit reserva a barra lateral e mostra uma setinha de expandir no
canto, bem ao lado do hero. Corrigido (+ CSS `[data-testid="collapsedControl"]
{display: none;}` de reforço).

## Histórico de acessos (2026-07-18)

Pedido do Wallace: "consigo criar um historico de acesso so para mim? quero
saber quem logou". Cada login bem-sucedido grava uma linha
(`data/hora`, `e-mail`) numa Planilha Google própria — não dá pra guardar
só "dentro" do site porque esse deploy reinicia sozinho a cada atualização
automática de dados (2 em 2h), o que apagaria qualquer arquivo local.

- Planilha precisa de uma aba chamada **"Acessos"**, compartilhada como
  **Editor** (não só Leitor, diferente de todas as outras planilhas do
  projeto) com a conta de serviço
  (`pamals-drive-reader@pamals-drive-sync.iam.gserviceaccount.com`).
- ID da planilha vai no secret `planilha_log_acessos_id` deste app
  (Settings → Secrets) — sem esse secret, o site funciona normal, só não
  grava/mostra nada.
- Só **wallacedellaney@gmail.com** vê o histórico — expander "📋 Histórico
  de acessos" no fim do dashboard, some pros outros e-mails.
- `shared/drive_sync.py` ganhou `adicionar_linha()`/`ler_linhas()` (API do
  Google Sheets v4) e o escopo `ESCOPOS` passou a incluir
  `.../auth/spreadsheets` (além do `drive.readonly` já existente) — só dá
  escrita de verdade em arquivos compartilhados como Editor, o resto do
  Drive continua só leitura.

## Testado (2026-07-18)

Via `AppTest`: dashboard completo carrega direto (sem tela de login), sem
exceção.
