# Projetos (MTA / TPJL)

Área nova (criada em 2026-07-09), mesma estrutura de pastas das outras 2 áreas
(`00_Instrucoes/`, `01_Bases_Originais/`, `02_Dados_Tratados/`, `03_Dashboard/`,
`05_Scripts/`, `06_Logs/`, `99_Backup/`).

Diferente de Coordenadoria e Contrato 005 (abas lado a lado), a navegação aqui
é **seleção → dashboard do projeto → voltar**: a página inicial
"Acompanhamento de Projetos" tem 2 cards clicáveis (MTA, TPJL); cada um abre
seu próprio dashboard, com botão de voltar pra seleção ou pro menu principal.

## Escopo (dado pelo Wallace em 2026-07-09, especificação completa)

* **MTA** — Módulo de Trabalho Anual, processo junto à DIRMAB de onde vêm os
  recursos do projeto. Fonte: planilha "MTA - Acompanhamento e Solicitações"
  (aba "Solicitações"), filtrada só por C-98. Ver `00_Instrucoes/mta.md`.
* **TPJL** — onde são inseridas as requisições de compra do projeto,
  geralmente atendidas pela CABW (EUA), com prazo de chegada longo. Exibido
  como "TPJL — Controle CABW". Fontes: "TPOB - Controle CABW 2025" e "TPOB -
  Controle CABW 2026" (aba "COORDENADORES"), unificadas, filtradas só por
  PJT = U8. Ver `00_Instrucoes/tpjl.md`.

## Status (2026-07-09)

* **Etapa 1** (análise + plano de arquivos) — feita.
* **Etapa 2** (página de seleção com os 2 cards, dados simulados) — feita:
  `03_Dashboard/projetos_app.py` + `projetos/secoes/selecao.py`. Cards mostram
  números simulados (marcados como tal) até as Etapas 3-6 ligarem os dados
  reais.
* **Etapa 3-4** (MTA: extração + filtro C-98 + indicadores) — feita e
  validada (81 solicitações C-98 de 944 linhas totais, R$ 88,2M em valor
  total). `05_Scripts/python/extrair_mta.py` + `projetos/secoes/mta.py` +
  `projetos/config/mta_config.py` + `projetos/regras/mta_regras.py`.
  Planilha compartilhada com a conta de serviço e acesso confirmado
  (`1ZdV1PX4ujqPgQNGk7f_WPkvA42aArVkGS59TVW78zhs`).
  **Nota de dado real**: a coluna "Para Contrato" na planilha não tem
  Sim/Não (só "Para Motores" tem) — guarda texto de categoria (REQUISIÇÃO/
  SOB DEMANDA/HORA DE VOO/PARCELA FIXA). Decisão do Wallace (2026-07-09):
  manter o texto como está e mostrar por categoria, sem forçar Sim/Não.
* **Etapa 5-6** (TPJL: extração + filtro U8) — feita e validada. **Mudança
  de decisão do Wallace em 2026-07-09**: 2025 e 2026 NÃO são unificados numa
  massa só — cada ano fica em sua própria aba do arquivo tratado
  (`TPJL_2025`/`TPJL_2026`) e o dashboard mostra 3 abas ("2025", "2026",
  "Comparativo"). 185 requisições U8 em 2025, 39 em 2026 (224 total).
  `05_Scripts/python/extrair_tpjl.py` + `projetos/secoes/tpjl.py` +
  `projetos/config/tpjl_config.py` + `projetos/regras/tpjl_regras.py`.
  Planilhas compartilhadas e acesso confirmado:
  2025 = `1zkBB77PXvzRTg-8n-tgNAYX8lJB8KozPvuyGiNtARsA`,
  2026 = `1Mf_R70IDJ9auysySW1oATGt3TSrPZE081-O3nB930lc`.
  **Nota de dado real**: a aba "COORDENADORES" de 2025 tem 2 colunas extras
  (duplicatas de Status Comprar/Status 11G sem uso real — sempre vazias ou
  0) que a de 2026 não tem; cada ano tem seu próprio mapeamento de coluna em
  `tpjl_config.py`. "Em cotação" no dashboard também agrupa "Selecionada
  para Cotação" (grafia real da planilha).
* **Etapa 7** (ligar os cards da seleção aos dados reais) — feita (MTA e
  TPJL já mostram números reais nos cards da seleção, não mais simulados).
* **Feedback do Wallace em 2026-07-09 sobre gráficos**: sempre priorizar
  **valor (R$)** em vez de quantidade de solicitações, com o valor escrito
  direto na barra (não só no hover) — aplicado no MTA; e criar uma visão de
  "o que já chegou x o que ainda falta" por categoria (Parcela Fixa,
  Motores, Hora de Voo etc.), que virou a seção "O que já chegou x o que
  ainda falta" no MTA. Aplicar o mesmo princípio em qualquer gráfico novo
  (já aplicado nos gráficos de valor do TPJL desde o início).
* **Etapa 8** (revisão de responsividade/erros/desempenho) — pendente.
* **Revisão visual completa (2026-07-09)**: tema centralizado em
  `projetos/components/paleta.py` (única fonte da paleta/tipografia/grid
  pra MTA e TPJL — mesma cor, mesma fonte, sem variação entre os dois,
  conforme pedido). Paleta escura profissional (fundo `#0B1118`, laranja
  `#F4A62A` como cor de marca/destaque, azul/verde/amarelo/vermelho como
  status fixos, nunca roxo/ciano soltos). Corrigido: bug de `</div>`
  aparecendo na tela (painel de detalhe agora é uma única chamada
  `st.markdown`, nunca dividido em várias); indicadores truncados (agora em
  cards HTML com quebra de linha livre); container com `max-width: 1560px`
  pra não precisar de zoom; gráfico "Registros vencidos por situação" do
  TPJL corrigido (não mostra mais "Sem data definida"/"Cancelado" como se
  fossem vencidos — virou "Distribuição por situação da previsão", com
  "Vencidos" numa seção própria com estado vazio); funil do TPJL substituído
  por "Distribuição por etapa do processo" (sem simular conversão que a
  planilha não permite calcular); TPJL ganhou uma 4ª aba "Visão consolidada"
  (2025+2026 juntos) antes de "2025"/"2026"/"Comparativo".

## Descrição da página de seleção (2026-07-14)

Subtítulo de "Acompanhamento de Projetos" (`projetos/secoes/selecao.py`)
atualizado pra citar Consumo/Estoque/Solicitações do TPJL — Wallace: "arruma
a definicao do acompanhamento do projeto" (a descrição antiga só mencionava
"requisições do TPJL", desatualizada depois que essas 3 fontes entraram).

## Atualização de dados

Cada módulo tem botão próprio ("Atualizar MTA", "Atualizar TPJL") — **sem**
botão geral, a pedido do Wallace. Segue o mesmo padrão de
`main()`/`atualizar_do_drive()` das outras áreas (ver `00_Instrucoes/atualizacoes.md`,
raiz do projeto). **Desde 2026-07-09, MTA e TPJL entraram na cadência
automática "todos de 2 em 2 horas"** (`shared/executar_atualizacao.py` +
GitHub Actions + launchd) — pedido pelo Wallace pra alimentar o histórico
sozinho, sem depender de clique manual.

## Histórico / "barra temporal" (2026-07-09)

Pedido do Wallace: "uma barra temporal a partir de hoje, arrastando mostra a
evolução na planilha, sempre atualizada no padrão das outras" (mesmo
princípio do histórico diário de RAC/Emergências). Implementado:

- `extrair_mta.py`/`extrair_tpjl.py` gravam um snapshot do dia
  (`historico_mta.csv`/`historico_tpjl.csv` em `02_Dados_Tratados/`) toda
  vez que `atualizar_do_drive()` roda — idempotente (roda de novo no mesmo
  dia substitui as linhas de hoje, não duplica).
- `projetos/components/evolucao.py` — componente genérico (`secao_evolucao`)
  com `st.select_slider` das datas disponíveis + comparação (novos/
  removidos/alterados) entre o dia escolhido e o snapshot mais recente.
  Usado no fim da página do MTA e em cada aba do TPJL (com o histórico
  filtrado por ano nas abas "2025"/"2026").
- **Só existe história a partir de 2026-07-09** (dia em que a gravação
  começou) — não há como reconstruir o passado. Com 1 dia só de histórico,
  a seção mostra uma mensagem explicando que ainda não dá pra comparar (a
  barra "aparece" de verdade a partir do 2º dia de execução automática).
- **Bug corrigido em 2026-07-16** — achado pelo Wallace na aba Solicitações
  do TPJL (histórico começou em 2026-07-14, só 2 dias gravados: 14 e 16,
  sem o 15): com exatamente **2** dias de histórico, `opcoes` (dias
  disponíveis pra comparar, excluindo o mais recente) tem só 1 item —
  `st.select_slider` com uma única opção quebra no navegador
  (`RangeError: min (0) is equal/bigger than max (0)`, o slider JS não
  aceita min==max). Corrigido em `evolucao.py` (Projetos **e**
  Coordenadoria, mesmo componente duplicado nas 2 áreas): com exatamente 1
  opção, usa ela direto (sem criar o slider) e mostra uma legenda
  explicando que a barra de arrastar só aparece a partir do 3° dia de
  histórico.

## Padrão de módulos Python

Pacote próprio `03_Dashboard/projetos/` (não módulos soltos `data`/`secoes`/
`components`) — mesma razão documentada no `CLAUDE.md` raiz: evitar colisão
de nomes com os pacotes `contrato005`/`coordenadoria` que compartilham o
mesmo processo Streamlit.
