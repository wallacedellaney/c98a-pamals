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
  **imagem** (não tabela nativa — pedido do Wallace em 2026-07-13, "a
  imagem [...] ficou ruim, vamos colocar como uma foto que a gente produz
  com base no fechamento e com base na aba 1.2 da rma"), renderizada com
  Pillow (`_renderizar_matriz_imagem`, mesmo padrão dos anexos da Ata de
  Reunião). A grade aeronave x dia (verde/amarelo/bege) e a linha "Média
  Diária" vêm do Cômputo Mensal local (`df_matriz_mes`, calculado por nós);
  os 4 números do resumo (MMAM/P/PMAX/IFD) vêm da planilha oficial "RMA em
  andamento {MÊS}.xlsx" no Drive — mesma fonte que a Ata de Reunião usa
  (`extrair_indicadores_rma`, importado de `gerar_ata_reuniao.py`), **não**
  do resumo salvo por `calcular_computo_mensal.py` (que parou de gravar
  esses 4 campos e, de qualquer forma, tinha uma pequena divergência
  conhecida vs. o número oficial — ver `computo_mensal.md`).
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

## Removido (era conteúdo copiado, não produzido por nós)

**2026-07-13**: Wallace — "lembra que as informações do slide são todas
produzidas pela gente, o que tiver copiado tira". Achado um bug real: os
slides 3-8 da referência (6 lâminas, tabelas com as emergências REAIS da
empresa pra aeronaves específicas daquele mês) nunca eram removidos —
ficavam sobrando no arquivo final, ao lado dos nossos slides novos por
aeronave. Também os slides 10-12 (Utilização — fonte é um PDF externo,
fora do nosso alcance —, tabela de Faturamento e Notas Fiscais) são só
imagem copiada da apresentação real deles, nunca regenerada por nós.
Os dois grupos agora são removidos sempre (`SLIDES_COPIADOS_EXTRAS = (10,
11, 12)` + `elementos_aeronave_antigos`, mesmo padrão de identidade
estável de elemento XML). Se um dia produzirmos Utilização/Faturamento/
Notas Fiscais nós mesmos, trocar a remoção por um slide nativo.

## Sem "brand" de slide

Uma tentativa de identidade visual (fundo escuro + âmbar) foi feita e
revertida a pedido do Wallace em 2026-07-12 ("ficou péssimo, kkkk, volta
ao normal"). Os gráficos usam a paleta de cor de DADO do site (âmbar/
ciano/verde/vermelho) — isso é cor de gráfico normal, não "brand" de
slide/fundo.

## Bugs já corrigidos (documentados pra não reintroduzir)

- **`python-pptx` faltando no `requirements.txt` do site publicado**
  (2026-07-14, achado pelo Wallace: "apreserntacao mensal deu Falha ao
  gerar a apresentação: No module named 'pptx'"): `gerar_apresentacao_rma.py`
  é importado DIRETO no processo do Streamlit (`import gerar_apresentacao_rma`
  em `fechamento_mensal.py`, não via subprocess) — então precisa das MESMAS
  dependências do app no ambiente de deploy (Streamlit Cloud instala do zero
  a partir do `requirements.txt` da raiz, diferente do Mac local, que já
  tinha tudo instalado). O `requirements.txt` raiz só listava
  streamlit/pandas/openpyxl/plotly/odfpy/google — faltava `python-pptx`
  (Apresentação), e também `python-docx`/`Pillow` (usados por
  `gerar_ata_reuniao.py`, importado do mesmo jeito pela aba "Ata de
  Reunião" — teria quebrado igual na sequência). Adicionados os 3 no
  `requirements.txt` raiz e no de `03_Dashboard/`.
- **`motivos.csv` vazio quebrava com `EmptyDataError`** (2026-07-14, achado
  pelo Wallace: "checa a apresentação de slide, deu erro"): um mês sem
  nenhuma negativação de aeronave (ex.: 2025-12, fora do período com
  histórico de emergências) grava um `_motivos.csv` de 0 bytes —
  `pd.read_csv` direto quebrava. `_carregar_dados_mes` agora trata
  `pd.errors.EmptyDataError` como "nenhuma aeronave negativou" (mesmo
  resultado do `ValueError` já esperado pra esse caso), mesma correção
  aplicada em `gerar_ata_reuniao.py` e no `carregar_computo_mensal` do site.
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
