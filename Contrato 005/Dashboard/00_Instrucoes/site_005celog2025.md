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
standalone" (fallback pra rodar só o Contrato 005 localmente) — só ganhou
uma tela de senha própria (2026-07-18), igual ao site principal, mas com
secret separado.

## Configuração no Streamlit Cloud (ação do Wallace)

1. Criar um **novo app** no Streamlit Cloud (share.streamlit.io → "New app").
2. Repositório: o mesmo do site principal (`wallacedellaney/c98a-pamals`).
3. Branch: `main`.
4. **Main file path**: `Contrato 005/Dashboard/03_Dashboard/app.py` (não
   `app.py` da raiz — esse é o site principal).
5. Nome do app / URL: algo com "005celog2025" (o Streamlit Cloud gera a URL
   a partir do nome escolhido).
6. **Secrets deste app** (Settings → Secrets — **não são compartilhados**
   com o site principal, precisam ser colados de novo aqui):
   ```
   site_password_005celog2025 = "escolher uma senha aqui"
   GOOGLE_SERVICE_ACCOUNT_JSON = '''
   { ... mesmo conteúdo já usado no site principal ... }
   '''
   ```
   O `GOOGLE_SERVICE_ACCOUNT_JSON` é necessário pros botões "🔄 Atualizar
   dados", "Apresentação (RMA)" e "Ata de Reunião" (ver
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

## Testado (2026-07-18)

Via `AppTest`: tela de login carrega sem erro, e o dashboard completo
(pós-senha) carrega sem exceção.
