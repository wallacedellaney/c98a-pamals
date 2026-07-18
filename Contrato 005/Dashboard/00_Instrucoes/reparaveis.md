# Instruções — Reparáveis

## Fonte

Planilha Google Sheets **"Controle reparáveis C-98"** (conta `ngodoy143@gmail.com`), mesma lógica de emergências/pagamentos: sem conexão ao vivo, buscar de novo só quando pedido. Cópia baixada em:

`01_Bases_Originais/Controles_Reparaveis/Controle reparaveis C-98 (Google Sheets).xlsx`

Aba usada: **`Divulgação`**. As outras 7 abas (Giro Ideal, Atual, Histórico, Empresa, EMPRESA_1, Vee one, Acerto virtual) **não são usadas**.

Essa planilha varia de tamanho a cada atualização (446 linhas em 2026-07-13, abertas e concluídas) — inclui campos que o PDF usado antes não tinha (`UNIDADE SOLIC.`).

## Extração

Ler a aba diretamente (já é planilha, não precisa reconstruir tabela de PDF).

## Colunas importantes (confirmado pelo Wallace)

| Coluna | Significado |
|---|---|
| OS | Número da Ordem de Serviço |
| PN | Part Number da peça |
| CFF | Código do fornecedor/fabricante |
| NOMENCLATURA | Descrição da peça |
| SN | Número de série da peça |
| DATA INICIO | Data de abertura da OS |
| UNIDADE SOLIC. | Base/esquadrão que solicitou (ex.: PAMALS, BAMN, BANT, PAMASP, BABE...) |
| ST_OS | Situação da OS (`REC`, `AUT`, `OS concluída`) |
| TAT SILOMS | Tempo em aberto (dias) segundo o sistema SILOMS |
| ONDE SE ENCONTRA | Local/empresa onde a peça está (ex.: VEE ONE, LEAP, WILLIAM, uma base, ou "PROCURANDO") |
| RECIBO CASO TENHA | Número do recibo de entrega, quando existe |
| CONDIÇÃO | Situação do reparo (ex.: EM REPARO, REPARADO, CONDENADO, EM QUARENTENA...). **Importante:** em ~17% das OS (as que já têm `RECIBO`), esta coluna traz uma data (prevista de devolução) em vez de texto — ver tratamento abaixo. |
| SN TROCADO (EXCHANGE) | Número de série recebido de volta, quando o item foi trocado (exchange) |
| TERMO DE RECEBIMENTO | Identificação do termo, quando emitido |

**Colunas que existem na planilha mas não são extraídas** (confirmado que não interessam): `Qt` (na verdade é só um número sequencial de linha, não quantidade), `TAT REAL` (a própria planilha marca como "ainda não confiável"), `OBSERVAÇÃO COORDENADORIA/FISCAL`, `OBSERVAÇÃO VEE ONE`, `Data de devolução empresa`, e o resto do bloco "COMREC/ACERTO VIRTUAL" (Data do Termo, Recebimento do Termo, Solicitar Acerto, OS Concluída, etc.).

## O que extrair

* OS, PN, CFF, nomenclatura, SN (e SN trocado, quando houver exchange);
* unidade solicitante;
* situação (ST_OS) e condição (reparo);
* onde se encontra;
* data início, TAT SILOMS;
* recibo e termo de recebimento.

## Regra de OS em aberto

Manter apenas OS cuja situação (`ST_OS`) seja diferente de "OS concluída" (`REC` e `AUT` entram).

## Regras de tratamento

* Datas convertidas para tipo data.
* Normalizar `CONDIÇÃO` (variações de grafia, ex.: "DEVOLVIDO NO ESTADO" vs "DEVOLVODO NO ESTADO").
* **Quando `CONDIÇÃO` contém uma data em vez de texto de status**: mover esse valor para um campo separado `data_retorno_prevista` e deixar `condicao` vazio para essa linha (não somar a data à contagem "OS por condição").
* Colunas com tipo misto (texto/número, ex.: CFF) viram texto na exibição do dashboard, sem alterar o dado tratado.
* **PN sempre normalizado pra texto na extração** (`parse_texto_pn` em `extrair_reparaveis.py`) — bug real visto em 2026-07-13: uma OS nova com PN só numérico foi lida como `int` pelo openpyxl, deixando a coluna com tipos mistos (`int` e `str`) e quebrando `sorted()` no Streamlit Cloud (`TypeError: '<' not supported between instances of 'int' and 'str'`), além da conversão pra Arrow do `st.dataframe`. Diferente do caso do CFF acima, aqui a correção é NA EXTRAÇÃO (dado tratado já sai só como texto), não só na exibição — e a mesma correção foi replicada em `extrair_emergencias.py` (coluna PN também existe lá). Ver também `components/utils.py::ordenar_unicos`, usado em 7 telas como defesa adicional contra esse mesmo padrão de bug com qualquer outra coluna.

## Filtros no dashboard

PN, situação, condição, onde se encontra e unidade solicitante — todos filtráveis na tela "Reparáveis".

## Estatísticas de TAT (2026-07-18)

Pedido do Wallace, nos dois sites (principal e 005CELOG2025): seção fixa
no topo da tela (não depende dos filtros abaixo), sempre sobre todas as OS
em aberto (`em_aberto == True`).

**Regra "entregue x com eles"**: quando `onde_se_encontra` é um destes
valores exatos — `BABE, BAMN, BABV, BAPV, BABR, BANT, PAMA-LS, BACO, BASM,
BACG, EEAR` (constante `LOCAIS_ENTREGUES` em `reparaveis.py`) — o item **já
foi entregue** pelo fornecedor (VEE ONE) pra unidade/base, só falta
encerrar a burocracia da OS (ainda conta como "em aberto" no SILOMS, mas
não é mais atraso de reparo de verdade). Qualquer outro valor (`VEE ONE`,
`WILLIAM`, `LEAP`, `PROCURANDO`, `AV AERONAUTICA`, `AMA - VEE ONE`, vazio,
etc.) conta como **"com eles"** — ainda não entregue.

**Atenção, `"V1 PAMA-LS"` ≠ `"PAMA-LS"`**: são valores diferentes na fonte
— `"V1 PAMA-LS"` **não** entra em `LOCAIS_ENTREGUES` (fica em "com eles"),
confirmado pelo Wallace: "obs: v1 pamals esta com eles ainda". Por isso o
match é por **igualdade exata**, nunca por "contém" — um match por
substring pegaria "V1 PAMA-LS" por engano.

**Prazo contratual de TAT**: `PRAZO_CONTRATUAL_TAT_DIAS = 110` (dias),
confirmado pelo Wallace. "Fora do prazo" = `tat_siloms > 110`. "Vence este
mês" = `data_inicio + 110 dias` cai no mês/ano atual **e** ainda não
passou de 110 dias (senão já estaria em "fora do prazo", não "vence
este mês").

Cards mostrados: Abertos (geral) + Média de TAT geral (todos os abertos,
incluindo os que só faltam burocracia — pedido explícito do Wallace, pra
não esconder esse tempo do TAT médio); Com eles (quantidade) + Média de
TAT só desse grupo; Fora do prazo contratual; Vencem o prazo este mês.
Dentro de um expander ("Mais estatísticas"): TAT médio por
`onde_se_encontra` (tabela + gráfico de barras horizontal, com uma linha
vertical marcando os 110 dias) — sugestão própria pra responder "pense em
outras estatísticas que podemos fazer", mostra onde o item costuma ficar
parado por mais tempo.
