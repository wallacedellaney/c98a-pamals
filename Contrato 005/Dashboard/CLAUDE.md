# Fluxo Operacional Obrigatório

> Este projeto agora vive dentro da pasta guarda-chuva `C-98A PAMALS/`, que tem
> sua própria página principal (menu com "Coordenadoria" e "Contrato
> 005/CELOG/2025"). Ver `C-98A PAMALS/CLAUDE.md` para o comando "executar"
> correto — ele sobe `C-98A PAMALS/app.py`, não o `app.py` desta pasta.
> **Desde 2026-07-18, `03_Dashboard/app.py` também é o ponto de entrada de
> um segundo deploy real no Streamlit Cloud** ("005CELOG2025", acesso da
> empresa VEE ONE só a esta área — senha própria, separada do site
> principal) — não é mais só um fallback de teste local. Ver
> `00_Instrucoes/site_005celog2025.md`.

## Comando "executar" / "roda"

Ver `C-98A PAMALS/CLAUDE.md`. Resumo: regenerar dados com `05_Scripts/python/gerar_dados_tratados.py`, depois subir `C-98A PAMALS/app.py` (não o `app.py` desta pasta) na porta 8501.

**O comando "executar" em si não busca dados novos do Google Sheets** — só reprocessa o que já está em `01_Bases_Originais/`. Emergências, Pagamentos, Reparáveis e Empréstimos já têm busca automática própria (de 2 em 2h, seg-sex — ver `C-98A PAMALS/00_Instrucoes/atualizacoes.md`), separada do "executar". **Reparáveis deixou de ser manual em 2026-07-10** (decisão revertida a pedido do Wallace, pra alimentar o histórico diário usado no controle de data global — ver `00_Instrucoes/analise_periodo.md`).

---

Sempre que receber uma tarefa neste projeto, siga esta ordem:

## 1. Ler instruções principais

Leia primeiro este arquivo:

`CLAUDE.md`

Entenda o objetivo geral do projeto antes de executar qualquer ação.

---

## 2. Verificar instruções complementares

Depois, verifique se existem arquivos na pasta:

`00_Instrucoes/`

Leia todos os arquivos `.md` relevantes para a tarefa.

Exemplos:

* `dashboard.md`
* `pagamentos.md`
* `reparaveis.md`
* `emergencias.md`
* `indicadores.md`

Se houver conflito entre qualquer arquivo e o `CLAUDE.md`, siga o `CLAUDE.md`.

---

## 3. Localizar bases originais

Procure as planilhas ou PDFs somente na pasta:

`01_Bases_Originais/`

Subpastas esperadas:

`01_Bases_Originais/005_CELOG_2025/`

`01_Bases_Originais/Controles_Reparaveis/`

`01_Bases_Originais/Prazo_Emergencias_C98/`

Nunca altere arquivos dessa pasta.

---

## 4. Extrair dados

Extraia os dados conforme a finalidade da tarefa:

### Pagamentos

Fonte:

`01_Bases_Originais/005_CELOG_2025/`

Aba principal:

`Controle de Pagamentos`

Coletar:

* módulo;
* nota fiscal;
* valor da nota;
* valor faturado;
* valor pendente;
* situação;
* datas relevantes.

### Reparáveis

Fonte:

Planilha Google Sheets "Controle reparáveis C-98" (aba "Divulgação"), privada, sem conexão ao vivo. Cópia baixada fica em `01_Bases_Originais/Controles_Reparaveis/`.

Coletar somente Ordens de Serviço em aberto (ST_OS diferente de "OS concluída").

Coletar:

* OS, PN, CFF, nomenclatura, SN (e SN trocado, quando houver exchange);
* unidade solicitante;
* situação (ST_OS) e condição (reparo);
* onde se encontra;
* data início, TAT SILOMS;
* recibo e termo de recebimento.

Ver `reparaveis.md` para a lista completa e o que fica de fora (Qt, TAT REAL, observações, bloco de acerto virtual).

### Emergências C-98

Fonte:

Planilha Google Sheets "Prazo das emergências - C-98" (aba "Prazos das emergências"), privada — mas **com busca automática própria** (seg-sex ~12h, GitHub Actions + Mac, credencial de serviço). Cópia baixada fica em `01_Bases_Originais/Prazo_Emergencias_C98/`.

Ler a aba e aplicar 3 filtros na extração: ST_EMG ≠ "Emg concluída", Provedor = "VEE ONE", Atd/cancelada em branco. Ver `emergencias.md`.


---

## 5. Tratar dados

Antes de consolidar, padronize:

* datas;
* valores monetários;
* nomes de empresas;
* clientes;
* aeronaves;
* status;
* textos;
* campos vazios;
* duplicidades.

Registre inconsistências encontradas.

---

## 6. Salvar dados tratados

Salve os arquivos tratados somente em:

`02_Dados_Tratados/`

Arquivos esperados:

`base_pagamentos_tratada.xlsx`

`base_reparaveis_tratada.xlsx`

`base_emergencias_tratada.xlsx`

`dados_tratados.xlsx`

`inconsistencias_encontradas.xlsx`

---

## 7. Gerar dashboard

Crie ou atualize o dashboard somente a partir dos dados da pasta:

`02_Dados_Tratados/`

Salvar resultado em:

`03_Dashboard/`

Nunca criar gráfico usando diretamente as bases originais.

O dashboard é interativo e dividido em partes, navegáveis por botões/abas na parte de baixo da tela:

* **Visão Geral** — resumo consolidado com os indicadores principais de todas as áreas abaixo (Reparáveis, Emergências, Empréstimos, Fechamento Mensal, Pagamentos), atualizado em 2026-07-09;
* **Reparáveis** — dados tratados de `base_reparaveis_tratada.xlsx`;
* **Emergências Abertas** — dados tratados de `base_emergencias_tratada.xlsx`;
* **Emergências Totais** — histórico completo (abertas + concluídas, VEE ONE) de `historico_completo_emergencias.xlsx`, ver `00_Instrucoes/emergencias.md`;
* **Análise de Período** — central dinâmica sobre o histórico diário de emergências: slider de intervalo, comparação automática com o período anterior equivalente, cards (novas/concluídas/entraram-saíram de atraso/mudança de estoque), gráfico de evolução diária, tabela filtrável, botão "Gerar resumo" e narrativa "O que mudou?" — ver `00_Instrucoes/analise_periodo.md`;
* **Fechamento Mensal** — seletor de mês + 4 subseções: **"Cômputo Mensal"** (ver `00_Instrucoes/computo_mensal.md` — prévia automática da matriz aeronave x dia da Pré-RNA a partir das emergências AIFP/IPLR), **"Atrasos"** (ver `00_Instrucoes/atrasos.md` — situação atual em aberto + entregas concluídas/canceladas no mês de referência, todos os tipos/aeronaves, com % no prazo), **"Apresentação (RMA)"** (ver `00_Instrucoes/apresentacao_rma.md` — gera os slides "por aeronave que negativou" do PowerPoint mensal a partir da nossa própria plataforma; botão de download, não sobe pro Drive sozinho) e **"Ata de Reunião"** (ver `00_Instrucoes/ata_reuniao.md` — gera rascunho .docx a partir de uma transcrição da reunião no Drive (escrita à mão pelo Wallace, preferida; ou o áudio, transcrito localmente com Whisper, como reserva) + planilha oficial "RMA em andamento" no Drive + dados tratados próprios; anexos de Empréstimos/Reparáveis em imagem paginada; desde 2026-07-13, testado só pra Junho/2026);
* **Empréstimos** — material retirado do estoque/emprestado e pendente de devolução, de `base_devolucoes_tratada.xlsx` (fonte: planilha "Devoluções"), ver `00_Instrucoes/emprestimos.md`;
* **Pagamentos** — dados tratados de `base_pagamentos_tratada.xlsx`;
* **Reajuste** — valor do contrato, saldo por módulo (1/2/3) e cronograma físico financeiro a partir da "Planilha Demonstrativa -2_Reajuste-" pessoal do Wallace (Drive, ainda não automatizada) — ver `00_Instrucoes/reajuste.md`.

Cada seção deve poder ser filtrada e navegada de forma independente.

---

## 8. Gerar relatórios

Quando solicitado, salve relatórios em:

`04_Relatorios/`

Exemplos:

`relatorio_financeiro.pdf`

`relatorio_operacional.pdf`

`pendencias_emergencias.pdf`

---

## 9. Usar scripts

Scripts devem ficar em:

`05_Scripts/`

Antes de criar novo script, verificar se já existe algum que possa ser reutilizado.

---

## 10. Registrar execução

Ao final de cada tarefa, registre em:

`06_Logs/`

Informar:

* data da execução;
* arquivos lidos;
* arquivos gerados;
* erros encontrados;
* inconsistências;
* próximas ações recomendadas.

---

## 11. Backup

Antes de alterações grandes, criar cópia em:

`99_Backup/`

Nunca excluir arquivos sem autorização.
