# Instruções — Ata de Reunião (RMA)

## Pedido do Wallace

2026-07-13: criar um processo repetível + um botão no site (Fechamento
Mensal) que sempre gera um rascunho da Ata de Reunião mensal, buscando: o
áudio da reunião, a "apresentação do mês" (dados da própria plataforma) e
usando o modelo estrutural da Ata assinada de maio/2026. Resposta às duas
perguntas de esclarecimento (2026-07-13): o botão gera um `.docx` pra
**baixar e editar** (não mostra rascunho editável na tela), e é um **botão
único com aviso de espera** (não dois passos separados).

Script: `05_Scripts/python/gerar_ata_reuniao.py`. Botão: aba "Ata de
Reunião" dentro de Fechamento Mensal (`secoes/fechamento_mensal.py`).

## O que é automático

- **Indicadores oficiais (MMAM, Pontuação Obtida, PMAX, IFD)** — vêm da
  planilha `RMA em andamento {MÊS}.xlsx` (Drive, mesma pasta do
  Fechamento Mensal do mês), abas **1.2** e **4.1**, **não** recalculados
  por nós. Isso evita a pequena divergência já conhecida entre o Cômputo
  Mensal automático do site (baseado só nas emergências AIFP/IPLR) e o
  número oficial da empresa — ver `computo_mensal.md`. Exemplo real
  (Junho/2026): nosso cômputo automático deu P=615/IFD=0,9, a planilha
  oficial "RMA em andamento" deu P=624/IFD=0,95 — a Ata usa sempre a
  planilha oficial.
- **Horas de voo e valores do Módulo 1** — aba **1.1** (horas
  voadas/faturadas do mês) e **4.1** (valor unitário da hora, valor bruto,
  IFD aplicado, multa, total) da mesma planilha.
- **Aeronaves com desempenho negativo** — junta o Cômputo Mensal já
  calculado pelo site (`02_Dados_Tratados/computo_mensal/{ano}-{mes}_motivos.csv`)
  com `historico_completo_emergencias.xlsx`, pra gerar o bloco de texto por
  aeronave/emergência (PN, nomenclatura, categoria, datas, atraso/antecipação,
  AWB, observação) no mesmo formato da Ata de maio.
- **Notas Fiscais** — lista as pendentes de pagamento, de
  `base_pagamentos_tratada.xlsx`.
- **Controle de Empréstimos** (Anexo A) e **Controle de Reparáveis** (Anexo
  B) — tabelas completas anexadas ao final do documento (igual ao padrão
  da Ata de maio, que também usa "Anexo A/B" em vez de tabela no corpo),
  de `base_devolucoes_tratada.xlsx` (filtrado pelo mês de `pedido_envio`)
  e `base_reparaveis_tratada.xlsx` (só os itens em aberto). **Os dois
  anexos (A e B) são IMAGENS** (renderizadas com Pillow,
  `_renderizar_tabela_imagem`), não tabelas nativas do Word — pedido do
  Wallace em 2026-07-13 ("queria tipo imagem para caber melhor igual ta
  no exemplo"): a Ata assinada de maio também traz os anexos como
  captura de tela, não tabela editável. **Paginadas** (`_construir_anexo_imagem_paginado()`,
  45 linhas por página, com "(página X de Y)" entre elas) em vez de uma
  imagem gigante só — pedido do Wallace, mesma conversa ("divide para
  caber tudo, acho que imagem dividida fica melhor"), depois de ver o
  Anexo A inteiro numa imagem só. Pra Junho/2026: Anexo A (48 linhas) = 2
  páginas, Anexo B (323 linhas, em aberto) = 8 páginas.
- **Apuração de Entregas (IMR)** — mesma regra da aba "Atrasos" do site
  (`_atrasos`, ponto 2): tudo concluído/cancelado dentro do mês de
  referência, não importa quando abriu.

## O que NÃO é automático (fica marcado pra revisão)

Seções que dependem de julgamento humano — não dá pra confiar numa
transcrição automática de áudio pra virar prosa formal de um documento
assinado: Abertura e Objetivo (prosa), discussão dos Módulos 2/3, MAPEM,
Encerramento, e a tabela de Pendências e Encaminhamentos. Ficam marcadas em
vermelho/itálico `[revisar a partir da transcrição]` no `.docx` gerado. A
transcrição completa do áudio vai anexada ao final do documento
("Transcrição da Reunião — rascunho automático") pra ele usar de
referência ao completar essas seções no Word.

## Transcrição — manual (preferida) ou por áudio (fallback)

**Desde 2026-07-13, o Wallace prefere escrever a transcrição ele mesmo** e
salvar na pasta do mês no Drive, num arquivo com "transcri" no nome
(Google Doc nativo, ou um `.docx`/`.txt` enviado) — `_baixar_transcricao_manual()`
procura esse arquivo primeiro e usa o texto dele diretamente, SEM rodar
Whisper (mais rápido, sem gastar os ~10 min de processamento, e sem
depender do modelo pesado). Só cai pro áudio+Whisper automaticamente se
não achar nenhum arquivo de transcrição na pasta do mês — esse caminho
continua funcionando (documentado abaixo) como reserva, mas não é mais o
fluxo principal esperado.

## Transcrição por áudio (fallback, se não houver transcrição manual)

Testado em 2026-07-13 com o áudio real de Junho/2026 (7,2 min,
`PALS Prefeitura de Aeronáutica de Lagoa Santa 3.m4a`):

- **Whisper local** (`openai-whisper`), modelo **"medium"** — testado
  contra o modelo "base" (mais rápido, mas errava números importantes tipo
  o valor do IFD e o total de horas voadas). O "medium" acertou "830 horas
  e 35 minutos" e "R$ 24.962,38" batendo exatamente com os números reais
  da planilha oficial. Ainda assim, nomes próprios e termos técnicos podem
  sair errados — é um rascunho, não texto final.
- **ffmpeg**: não tem Homebrew nem `ffmpeg`/`ffprobe` instalados neste Mac.
  Usamos `imageio-ffmpeg` (baixa um binário estático via pip, sem sudo).
- **Certificados SSL**: o Python.org deste Mac não vem com bundle de
  certificados próprio — o download do modelo Whisper falhava com
  `CERTIFICATE_VERIFY_FAILED`. Corrigido apontando `SSL_CERT_FILE` pro
  bundle do pacote `certifi`.
- **Custo**: ~10 minutos de processamento (CPU, local) por reunião,
  incluindo ~6 min de download do modelo na PRIMEIRA vez (depois fica em
  cache local, só a transcrição em si demora, ~4-5 min pra 7 min de áudio).
- **Cache**: a transcrição de cada mês fica salva em
  `02_Dados_Tratados/atas/transcricao_{ano}-{mes}.txt` — clicar de novo no
  botão não reprocessa o áudio (usa o cache), a menos que o arquivo seja
  apagado ou `forcar_transcricao=True` seja passado.

**⚠️ Limitação conhecida, ainda não resolvida**: o modelo Whisper "medium"
(~1,5 GB) e o `torch` são dependências pesadas. Isso funciona bem rodando
localmente no Mac do Wallace (`streamlit run app.py`), mas provavelmente
**não** funciona no Streamlit Community Cloud (limite de RAM do plano
gratuito) — se o botão for usado a partir do site publicado na nuvem, pode
falhar por falta de memória. Recomendação: usar esse botão rodando
localmente por enquanto; se precisar funcionar a partir da nuvem, avaliar
um modelo menor ("small") ou um serviço de transcrição externo.

## Onde os arquivos são buscados no Drive

Pasta raiz "Fechamentos mensais" (`1PT5b2iqt2KVNmBjf1HDHPwcTLYHUNNjI`) →
pasta do ano (nome exato, ex. "2026") → pasta do mês (nome contém o mês
por extenso, ex. "06 JUNHO"). Dentro da pasta do mês, procura por
mimeType `audio/*` (áudio) e por um arquivo `.xlsx` cujo nome contém "RMA
em andamento" (case-insensitive). Já compartilhado com a conta de serviço
(`pamals-drive-reader@pamals-drive-sync.iam.gserviceaccount.com`) —
confirmado em 2026-07-13, sem precisar de nova permissão.

## Teste manual (fora do site)

```
cd "05_Scripts/python"
python3 gerar_ata_reuniao.py 2026 6
```

Gera em `02_Dados_Tratados/atas/Ata_RMA_Junho_2026_rascunho.docx`.
