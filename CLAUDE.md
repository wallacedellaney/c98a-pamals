# C-98A PAMALS

Pasta guarda-chuva com uma única página principal, que dá acesso a 3 áreas:

* **Coordenadoria** — RAC, Disponibilidade Diária, Vencimentos (TMOT + Operadores), Diagonal de Manutenção e Dashboard Geral construídos; Previsão Mensal ainda é só um stub. Ver `Coordenadoria/CLAUDE.md`.
* **Contrato 005/CELOG/2025** — dashboard completo (Visão Geral, Reparáveis, Emergências Abertas, Emergências Totais, Fechamento Mensal, Empréstimos, Pagamentos). Ver `Contrato 005/Dashboard/CLAUDE.md`.
* **Projetos (MTA/TPJL)** — acompanhamento de solicitações do MTA (DIRMAB) e requisições do TPJL (CABW/EUA), ambos filtrados pro C-98. Dashboards completos desde 2026-07-09 (indicadores, gráficos, filtros, tabela, histórico/"barra temporal"). Ver `Projetos/CLAUDE.md`.

## Estrutura

```
C-98A PAMALS/
├── app.py                     <- página principal (menu com as 3 áreas)
├── home_hero.py                <- hero animado da home (hangar/avião), ver docstring
├── imagens/                    <- assets visuais da home (foto do hangar/avião)
├── .streamlit/config.toml     <- tema "Torre de Controle", compartilhado
├── .secrets/                  <- credencial da conta de serviço do Google (nunca commitar)
├── shared/                    <- drive_sync.py + estado.py, usados pelas 3 áreas (ver 00_Instrucoes/atualizacoes.md)
├── 00_Instrucoes/atualizacoes.md  <- atualização sob demanda por fonte, com Drive real
├── Contrato 005/Dashboard/    <- projeto completo do Contrato 005 (ver CLAUDE.md próprio)
├── Coordenadoria/             <- RAC, Disponibilidade Diária, Vencimentos, Diagonal (ver CLAUDE.md próprio)
└── Projetos/                  <- MTA e TPJL, completos (ver CLAUDE.md próprio)
```

## Atualização de dados — automática (9 fontes) + manual (as demais)

Disponibilidade Diária, Emergências, RAC, Vencimentos TMOT, Pagamentos, MTA,
TPJL, Reparáveis e Empréstimos atualizam **sozinhos, de 2 em 2 horas
(seg-sex, 8h-20h), por 2 caminhos ao mesmo tempo** (a pedido do Wallace,
desde 2026-07-09): na nuvem do GitHub
(`.github/workflows/atualizacoes.yml`, GitHub Actions — não depende do Mac
ligado) **e** via `launchd` no Mac do Wallace (se estiver ligado no horário,
busca também) — ver `00_Instrucoes/atualizacoes.md`. O
workflow/script usa a credencial própria do Google (Secret
`GOOGLE_SERVICE_ACCOUNT_JSON`) + `shared/drive_sync.py` +
`shared/executar_atualizacao.py` (sincroniza com o GitHub antes de rodar pra
não divergir, busca, reprocessa, commita e dá push
sozinho — o Streamlit Cloud reimplanta automaticamente). Emergências Totais
(histórico completo) e o Cômputo Mensal (Fechamento Mensal, Contrato 005)
não têm agendamento próprio — recalculam de carona toda vez que Emergências
atualiza. **Reparáveis e Empréstimos entraram na automação em 2026-07-10**
(antes eram manuais — decisão revertida pra alimentar o controle de data
global, ver `Contrato 005/Dashboard/00_Instrucoes/analise_periodo.md`). As
demais fontes (Vencimentos por Operador, Diagonal de Manutenção) continuam
manuais — Wallace pede na conversa. Ver `00_Instrucoes/atualizacoes.md`
para a arquitetura completa e como adicionar uma fonte nova ao agendamento.

## Painel "Fonte dos dados" (rodapé de cada área)

Cada uma das 3 áreas tem, no rodapé do dashboard, um botão pequeno e
centralizado **"ℹ️ Fonte dos dados"** (nome escolhido pelo Wallace em
2026-07-14) — ao clicar, mostra uma tabela (Informação / De onde vem / Como
é atualizado / Frequência / **Última atualização**) com **todas** as fontes
daquela área. A coluna "Última atualização" busca a data de modificação real
do arquivo tratado (via a chave `_chave` de cada linha, mapeada pra uma
chave já carregada por `carregar_dados.py`) — não é um valor fixo; fontes
calculadas na hora (Cômputo Mensal, Apresentação, Ata, Dashboard Geral)
mostram "—". Implementado em `<area>/components/fontes_dados.py` (duplicado
por área, sem import entre pacotes — mesmo motivo de sempre), chamado no fim
do `render()` de `contrato_app.py`/`coordenadoria_app.py`/`projetos_app.py`.
**Manter essa tabela atualizada** sempre que uma fonte mudar de nome, de
mecanismo de atualização (manual → automático) ou de frequência.

**Também existe na página principal** (`app.py::_fontes_dados_geral()`,
pedido do Wallace em 2026-07-14: "quero que coloca na pagina principal
tb") — versão combinada das 3 tabelas, uma embaixo da outra com uma coluna
"Área" a mais. Cada área é carregada com try/except própria: se uma falhar
(ex.: arquivo tratado ainda não gerado), as outras 2 continuam aparecendo
normalmente, sem derrubar a home.

## Comando "executar" / "roda"

Quando o Wallace disser "executa" ou "roda" (sem mais detalhes), fazer:

1. Rodar `Contrato 005/Dashboard/05_Scripts/python/gerar_dados_tratados.py` para regenerar os dados tratados do Contrato 005.
2. Subir (ou reaproveitar) `streamlit run app.py` a partir desta pasta (`C-98A PAMALS/`) na porta 8501 — **não** rodar o `app.py` de dentro de `Contrato 005/Dashboard/03_Dashboard/` diretamente, esse é só um runner standalone de fallback.
3. Devolver o link `http://localhost:8501`.

Isso não busca dados novos do Google Sheets sozinho — ver a seção equivalente em `Contrato 005/Dashboard/CLAUDE.md`.

## Como a página principal chama o Contrato 005

`app.py` (nesta pasta) importa `contrato_app.render()` de dentro de `Contrato 005/Dashboard/03_Dashboard/`, inserindo essa pasta em `sys.path`. Os módulos internos do Contrato 005 (`data`, `secoes`, `components`) ficam dentro do pacote `contrato005` (em `03_Dashboard/contrato005/`) justamente para não colidir com módulos de mesmo nome que a Coordenadoria vier a ter — quando for criar a Coordenadoria, seguir o mesmo padrão (pacote próprio, não módulos soltos `data`/`secoes`/`components`).
