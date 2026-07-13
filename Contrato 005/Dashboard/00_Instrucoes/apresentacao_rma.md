# Instruções — Apresentação (RMA)

## O que é

Gera a apresentação de PowerPoint da RMA (Reunião Mensal de Acompanhamento)
de um mês de referência, puxando os dados da nossa própria plataforma em
vez de pedir pra montar/printar tela por tela todo mês. Script:
`05_Scripts/python/gerar_apresentacao_rma.py`. Botão: aba "Apresentação
(RMA)" dentro de Fechamento Mensal.

**2026-07-13: recriado.** O arquivo (script + esta doc + o botão no site)
tinha sido removido da pasta (Wallace: "vc tirou a parte do slide?" — não
fui eu, presumi ser intencional; resposta: "sim, é para ter"). Recuperado
com alta fidelidade a partir do bytecode ainda em cache
(`__pycache__/gerar_apresentacao_rma.cpython-314.pyc`, compilado em
2026-07-12 — o Python 3.14 é recente demais pros decompiladores existentes
(`decompyle3` etc.) suportarem, então a reconstrução foi via
`dis`/`marshal` direto: docstrings, constantes (cores, índices de slide,
colunas), assinaturas de função e nomes referenciados vieram exatos do
bytecode; a lógica de cada função foi reconstruída a partir disso + do
histórico da conversa) + `RMA_referencia.pptx` baixado de novo do Drive
(pasta de Junho/2026 — "RMA JUNHO.pptx"). Testado de ponta a ponta de
novo (28 slides, sem overflow, sem exceção) antes de considerar pronto.

## Como usa a base

Reaproveita `04_Relatorios/RMA_referencia.pptx` só como BASE de
layout/estilo (índices de slide fixos, ver constantes `SLIDE_*` no
script) — a intenção (Wallace, 2026-07-11) é puxar os DADOS todos da
nossa própria plataforma, com exceção da Utilização (só existe como PDF
externo). Se um mês novo mudar a estrutura de slides da referência (nº de
slides, ordem), os índices `SLIDE_TITULO`/`SLIDE_OBJETIVO`/
`SLIDES_MATRIZ`/`SLIDE_PAGAMENTOS`/`SLIDE_EMPRESTIMOS`/
`SLIDES_REPARAVEIS`/`SLIDE_EMPRESTIMOS_DASHBOARD`/`SLIDE_ATRASOS_DASHBOARD`
no topo do script precisam ser conferidos de novo.

## O que é gerado automaticamente

- **Slide 1 (título) e 2 (objetivo)**: só troca o nome do mês (o mês é um
  RUN isolado no texto), resto intocado.
- **Slides 3 e 10 (Tabela 1.2 — matriz aeronave x dia + MMAM/P/PMAX/IFD)**:
  tabela nativa a partir do Cômputo Mensal (`calcular_computo_mensal.py`),
  mesmas cores (verde = montada, amarelo = desmontada, bege = fora do
  contrato) e os mesmos números já calculados lá (MMAM/P/PMAX/IFD).
- **1 slide por aeronave que negativou** no mês: linha 1/0 do mês +
  tabela das emergências responsáveis.
- **Pagamentos**: tabela nativa (`base_pagamentos_tratada.xlsx`) + resumo
  do contrato (total, liquidado, saldo a faturar).
- **Empréstimos**: 3 slides — estatísticas do mês (3 gráficos: status,
  categoria, top destinos, todos ponderados por quantidade — "as vezes
  uma linha tem 10 ea"), lista completa do mês (paginada, quantas lâminas
  forem necessárias), estatística total (todos os meses).
- **Reparáveis**: 1 slide só de estatísticas (total, com a empresa,
  terceirizadas, bases FAB + 2 gráficos) — sem lista completa (pedido do
  Wallace, "não precisa mandar a lista completa dos reparáveis não").
- **Atrasos**: 2 slides nativos — "Situação Atual" (em aberto agora) e
  "Entregas no Mês de Referência" (resumo + rosca + amostra), mesma lógica
  de `_atrasos()` em `fechamento_mensal.py`.
- **Removido** da referência: os slides-imagem dos antigos dashboards de
  Empréstimos e Atrasos (eram só capturas de tela do nosso próprio site).

## Mantido da referência, sem regenerar (fora do nosso alcance)

Utilização (imagem — fonte é um PDF externo), tabela de faturamento e
notas fiscais.

## Sem "brand" de slide

Uma tentativa de identidade visual (fundo escuro + âmbar) foi feita e
revertida a pedido do Wallace em 2026-07-12 ("ficou péssimo, kkkk, volta
ao normal"). Os gráficos usam a paleta de cor de DADO do site (âmbar/
ciano/verde/vermelho) — isso é cor de gráfico normal, não "brand" de
slide/fundo.

## Bugs já corrigidos (documentados pra não reintroduzir)

- **Duplicidade de nome de parte XML**: sempre inserir TODOS os slides
  novos antes de remover qualquer slide antigo, usando identidade estável
  de elemento XML (não índice inteiro calculado à mão) — ver
  `_slide_em_branco`/`_remover_slides`.
- **Tabela sobrepondo caixa de resumo (Tabela 1.2)**: a altura REAL de uma
  tabela depois de setar `rows[r].height` linha a linha é a soma dessas
  alturas, não o valor "declarado" no `add_table()` — `_construir_tabela_matriz`
  calcula a altura de linha a partir de um orçamento (reserva espaço pra
  caixa de resumo abaixo) em vez de um valor fixo, senão sobrepõe com
  meses de mais aeronaves.
- **Título duplicado ("JUNHOJUNHO")**: o run "RMA " também é
  `.isupper()`, então checar só "é maiúsculo" pra achar o run do mês é
  errado — `_atualizar_titulo_objetivo` checa se o run é exatamente um
  nome de mês (`t.strip() in MESES_PT_MAIUSCULO`).

## Teste manual (fora do site)

```
cd "05_Scripts/python"
python3 gerar_apresentacao_rma.py 2026 6
```

Gera em `02_Dados_Tratados/atas/RMA_Junho_2026_TESTE.pptx`.
