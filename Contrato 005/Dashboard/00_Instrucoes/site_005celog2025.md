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

**Sem senha por enquanto** (decisão do Wallace em 2026-07-18: "por
enquanto sem senha, o dela vou pensar uma forma mais segura com email e
talz") — chegou a ter uma tela de login própria (secret
`site_password_005celog2025`) por um instante durante a configuração,
removida antes do primeiro deploy real a pedido do Wallace. Se um dia
quiser adicionar autenticação de verdade (por e-mail/domínio da empresa,
por exemplo), é só pedir — o padrão de tela de login já existe no site
principal (`C-98A PAMALS/app.py`) pra copiar.

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

**Páginas escondidas nesse deploy**: "Fechamento Mensal" (Cômputo Mensal,
Atrasos, Apresentação RMA, Ata de Reunião) — pedido do Wallace: "tira no
fechamento mensal, apresntacao da rma" / "e tb tira a producao da ata".
`contrato_app.render()` ganhou o parâmetro `paginas_ocultas` (só usado por
este deploy — o site principal continua chamando `render()` sem esse
parâmetro, mostrando tudo).

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

## Bug corrigido em 2026-07-18 — seta de expandir sidebar aparecendo no hero

Wallace: "no dasborad do lado do aviao tem um uma seta de um lado e do
outro, tira isso kkk" — faltava `initial_sidebar_state="collapsed"` no
`st.set_page_config()` deste app (o site principal já tinha) — sem isso,
o Streamlit reserva a barra lateral e mostra uma setinha de expandir no
canto, bem ao lado do hero. Corrigido (+ CSS `[data-testid="collapsedControl"]
{display: none;}` de reforço).

## Testado (2026-07-18)

Via `AppTest`: dashboard completo carrega direto (sem tela de login), sem
exceção.
