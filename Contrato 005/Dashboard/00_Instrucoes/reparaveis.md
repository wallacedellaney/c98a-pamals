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
