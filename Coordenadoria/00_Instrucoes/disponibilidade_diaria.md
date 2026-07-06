# Instruções — Disponibilidade Diária

## Fonte

Google Drive, pasta **"Atualização de Disponibilidade"** (id `1JLrUGunWo5ABsR3WuYo88b2WD4QWoxNH`) → ano (ex.: pasta "2026", id `1GUcW8HrIedJKfwNO68nPHaOO1zIn1MeM`) → mês (ex.: "07 Julho", id `10IxiLjPonqd2zw6Vm0pVeAf1CUF1gsRw` — nome do mês muda todo mês, tem que buscar de novo) → um Google Doc por dia, nomeado "Disponibilidade DD/MM". Cada doc é o texto que vira a mensagem de WhatsApp diária de disponibilidade da frota C-98.

**Confirmado pelo Wallace: só sai relatório de segunda a sexta** (sem fim de
semana). Isso é esperado, não é uma falha — ao buscar "o mais recente", não
existir relatório de sábado/domingo é normal. A comparação "mudanças desde
[data anterior]" (na seção own do site) deve sempre comparar com o **último
relatório realmente existente**, seja ele de ontem ou de sexta-feira (se hoje
for segunda) — nunca pular ou tentar inventar um relatório de fim de semana
que não existe.

Não há credencial do Google configurada no app Streamlit (diferente das outras áreas, que leem cópias `.xlsx` locais de Sheets). Por isso, o fluxo aqui é:

1. Quando o Wallace pedir ("atualiza", "busca o mais recente"), o Claude busca no Drive o `.docx` mais recente ainda não salvo localmente e grava o texto em `01_Bases_Originais/Disponibilidade_Diaria/Disponibilidade_DD_MM_AAAA.txt`.
2. O botão "Atualizar dados" do site só reprocessa os `.txt` já salvos localmente (roda `extrair_disponibilidade_diaria.py` + limpa cache) — não busca nada novo sozinho.

Isso é o mesmo padrão já usado no RAC e no Contrato 005 (ver `CLAUDE.md` da Coordenadoria).

Cada relatório processado fica salvo como um arquivo próprio — nunca sobrescrever relatórios antigos, para manter o histórico.

## Formato do relatório (texto)

```
*C-98 - DD/MM/AAAA*
*RESUMO:*
*Disponibilidade*
XX D / XX M
(XX DI / XX DO / XX II / XX IN / XX ITR / XX IS / XX IP)

*Previsão até o final do dia: XX D / XX M*

*Previsão de disponibilidade semanal*
*Disponíveis:* XX
- matricula, matricula, ...
*Montadas:* XX
- matricula, matricula, ...

*Esforço Aéreo*
Anual: HH:MM:SS / HH:MM:SS / XX,XX%

*Motores disponíveis: XX*

*NOME DA UNIDADE*
[ ] matricula - SITUACAO - ocorrência (opcional) - DPE: condição (opcional)
```

## Definições confirmadas (documento "TIPOS_DE_DISPONIBILIDADE_E_EMERGENCIAS", DIRMAB)

* **D — Disponível** = DI + DO.
* **M — Montada** = aeronaves sem AIFP e sem IPLR pendente (independente da situação operacional). **D e M são indicadores independentes — não somam o total da frota.** O relatório só informa o total M da frota, não por aeronave (só sabemos quais aeronaves vão *virar* montadas essa semana, pela lista da "Previsão de disponibilidade semanal").

| Código | Significado |
|---|---|
| DI | Disponível — aeronave e equipamentos de missão totalmente operacionais. |
| DO | Disponível não completamente operacional — pode voar, mas com restrição (ex.: rádio, farol de pouso). |
| II | Indisponível por manutenção **programada** (inspeção prevista). |
| IN | Indisponível por manutenção **não programada** (pane, achado de inspeção). |
| IS | Indisponível por **suprimento** — falta de material (IPLR = paralisa linha de revisão; AIFP = impede o voo). |
| ITR | Indisponível por **transporte** — aguardando material em trânsito. |
| IP | Aparece nos relatórios reais (ex.: "estocada", "acidentada") mas não está definido no documento oficial revisado — tratar como indisponibilidade de longo prazo/permanente até confirmação do Wallace. |
| IE (não visto nos relatórios de 2026) | Indisponível por estocagem — sem previsão de retorno ao projeto. |
| IT (não visto nos relatórios de 2026) | Indisponível por instrumentação (atividade do IPEV). |

**DPE** = Data Prevista de Entrega/liberação. Pode ser uma data (`DD/MM` ou `DD/MM/AAAA`) ou uma condição em texto livre (ex.: "Aguarda DPE do PAMASP", "A ser definido", "02 dias após chegada do item") — quando não há data concreta, **não inventamos uma data**, guardamos a condição como texto.

## Cobertura da frota

O relatório diário lista tipicamente **29 das 30 aeronaves** da frota RAC — falta a **2701** (Sem condições / acidentada no RAC), que aparentemente não entra no acompanhamento operacional diário. Confirmar com o Wallace se isso é sempre assim.

## O que extrair

`extrair_disponibilidade_diaria.py` lê todos os `.txt` de `01_Bases_Originais/Disponibilidade_Diaria/` e gera `02_Dados_Tratados/base_disponibilidade_diaria.xlsx` com duas abas:

1. **Relatorios** — uma linha por dia: contagens (D, M, DI, DO, II, IN, ITR, IS, IP), previsão até o final do dia, previsão semanal (quantidade + matrículas que devem transicionar), esforço aéreo anual (previsto/realizado/%), motores disponíveis.
2. **Aeronaves** — uma linha por aeronave x relatório: matrícula, unidade, situação, ocorrência (texto livre), DPE (data, se identificada, ou condição em texto).

Checagem de consistência automática: soma dos códigos (DI+DO+II+IN+ITR+IS+IP) do resumo deve bater com a quantidade de aeronaves listadas naquele relatório — se não bater, entra como inconsistência no log.

## Escopo da primeira versão do site (definido pelo Wallace)

Wallace pediu uma especificação bastante ampla (34 seções: importação manual de relatório com tela de validação, comparação entre datas quaisquer, histórico/linha do tempo por aeronave, exportação em PDF/Excel, configuração de siglas/cores, etc.). Construímos em fases:

**Fase 1 (feita)**: cabeçalho com data de referência, indicadores principais (D, M, % disponibilidade, previsão do dia, motores, esforço aéreo), distribuição por situação (DI/DO/II/IN/ITR/IS/IP), previsão semanal, comparação simples com o relatório imediatamente anterior (variação de D/M e mudanças de situação por aeronave), alertas classificados (crítico/atenção/programado), painel por unidade com aeronaves (cards clicáveis), busca e filtros.

**Feito em 2026-07-06**: página de detalhe por aeronave (clicar no card, no painel por unidade) com 2 abas — "Situação atual" (situação/ocorrência/DPE do relatório mais recente) e "Histórico" (linha do tempo de situação por relatório + tabela completa, exportável em CSV). Ver seção "Histórico por aeronave" abaixo.

**Próximas fases (não feitas ainda)**: importação manual de novo relatório com tela de validação dentro do site (por ora a entrada é sempre via Claude, ver acima), comparação entre duas datas quaisquer, exportação em PDF, tela de configuração de siglas e cores.

## Histórico por aeronave (a partir de 2026-07-06)

Diferente do RAC, aqui o histórico **já existia sem querer**: cada relatório
vira um `.txt` próprio (nunca sobrescreve o anterior), e
`extrair_disponibilidade_diaria.py` já lia todos os arquivos salvos e montava
uma linha por aeronave x relatório na aba "Aeronaves" — só faltava uma tela
pra mostrar isso, que foi construída agora (ver acima).

O histórico só cobre os relatórios que já foram efetivamente salvos
localmente (ver seção "Fonte") — não há relatório de fim de semana, então a
linha do tempo pula sábados/domingos normalmente, e isso é esperado.

Identidade visual: reaproveita os mesmos componentes/cores/tipografia já usados no RAC e no restante do site (ver `Contrato 005/Dashboard/00_Instrucoes/00_BRAND/identidade_visual.md`).
