# Instruções — RAC (configuração das aeronaves)

## Fonte

Planilha Google Sheets **"Análise crítica de emergências C-98 2026"** (conta `aux.coord.c98@gmail.com`). **Desatualizado** — isso já foi "sem conexão ao vivo, buscar só quando pedido", mas desde 2026-07-06 o RAC tem busca automática própria (de 2 em 2h, seg-sex — ver `C-98A PAMALS/00_Instrucoes/atualizacoes.md`). Cópia baixada em:

`01_Bases_Originais/RAC/Analise critica de emergencias C-98 2026 (Google Sheets).xlsx`

Aba usada: **`Rac`**. O arquivo tem outras abas (Pns, Relat. SILOMS, Controle EMG, Rac ANCE, Importação do SILOMS, Cancelamento de emg antigas, ANV IS, PREVISAO3M) que **não são usadas** por enquanto.

## Objetivo da planilha

Controlar a configuração das aeronaves e identificar quais materiais faltam para cada uma ficar completa. Serve pra coordenação acompanhar de forma centralizada: disponibilidade, contrato, materiais faltantes, prioridades de aquisição/reparo/transferência.

## Estrutura da aba Rac

É uma matriz: **linhas = materiais** (PN), **colunas = aeronaves**, no cruzamento aparece a **quantidade que falta** daquele material para aquela aeronave.

* **Linha 1**: matrícula da aeronave (a partir da coluna G). A cor de fundo *aparente* vem de **formatação condicional** do Google Sheets (baseada na linha 3, não é uma cor fixa na célula); a cor da fonte indica se está no contrato.
* **Linha 2**: unidade/esquadrão da aeronave (ex.: 6º ETA, CLA, PAMALS, BAPV, DACTA2...).
* **Linha 3**: contagem de pendências daquela aeronave — é o que decide a cor de fundo condicional (ver abaixo). Recalculamos nosso próprio total a partir da matriz, não usamos este valor diretamente além de decidir a cor.
* **Linha 4**: outro contador-resumo (não usado na extração).
* **Linha 5 em diante**: uma linha por PN. Colunas A-E = Núm, PN, Nomenclatura, Sum, Cont. Da coluna G em diante, o valor é a quantidade que falta daquele PN para aquela aeronave. Vazio ou 0 = não falta nada daquele item pra aquela aeronave.

## Cores (confirmado pelo Wallace)

A cor de fundo da matrícula (linha 1) é decidida por **formatação condicional** com base na linha 3 — por isso a leitura direta da célula (`cell.fill`) não reflete a cor real exibida; é preciso avaliar a regra.

| Condição | Cor exibida | Significado |
|---|---|---|
| Fundo estático coral (`#E06666`) | Coral | Aeronave **Sem condições** |
| Sem fundo estático, linha 3 = 0 | Verde | Aeronave **Montada** |
| Sem fundo estático, linha 3 > 0 | Laranja/amarelo (`#FFE599`) | Aeronave **Desmontada** |

**Nomenclatura:** "Disponível" foi renomeado para **"Montada"** no site — "Disponível" vai ser usado depois para outro conceito (disponibilidade operacional, ainda não definida).

| Cor da fonte | Significado |
|---|---|
| Vermelha (`#FF0000`) | Aeronave **fora do contrato** |
| Preta/padrão | Aeronave **dentro do contrato** |

**Regra de contrato:** uma aeronave é considerada **fora do contrato** se a fonte da matrícula for vermelha **ou** se estiver Sem condições (fundo coral estático) — mesmo com fonte preta. Contagem atual (30 aeronaves):

| Disponibilidade | Contrato | Quantidade | Matrículas |
|---|---|---|---|
| Montada | Dentro do contrato | 20 | 2702, 2703, 2704, 2708, 2709, 2719, 2720, 2722, 2727, 2729, 2731, 2733, 2736, 2737, 2738, 2739, 2740, 2741, 2742, 2743 |
| Desmontada | Dentro do contrato | 3 | 2721, 2723, 2728 |
| Desmontada | Fora do contrato | 4 | 2732, 2730, 2734, 2726 |
| Sem condições | Fora do contrato | 3 | 2701, 2706, 2724 |

## O que extrair

Duas tabelas, salvas em `02_Dados_Tratados/base_rac_tratada.xlsx`:

1. **Aeronaves** — uma linha por aeronave: matrícula, unidade, disponibilidade, contrato (dentro/fora), total de pendências (nº de PNs distintos faltando), soma de unidades faltantes.
2. **Pendencias** — uma linha por combinação aeronave × PN com falta > 0: matrícula, unidade, PN, nomenclatura, quantidade faltante.

## Objetivo no site (definido pelo Wallace)

**Não copiar a aparência da planilha.** Transformar em visualização clara e rápida que permita ver imediatamente:

* total de aeronaves montadas x desmontadas x sem condições;
* aeronaves dentro x fora do contrato;
* quantidade de pendências de cada aeronave;
* percentual de completude de cada matrícula;
* quais itens estão impedindo uma aeronave específica de ficar completa (visão individual por aeronave);
* quais materiais afetam o maior número de aeronaves (PN mais crítico).

Usar indicadores, filtros, tabelas-resumo e uma visão individual por aeronave — não uma cópia em grade da planilha original.

### Regra de detalhe por contrato (atualizada pelo Wallace em 2026-07-06)

Todas as aeronaves (dentro **e** fora do contrato) mostram a lista detalhada
de pendências (PN, nomenclatura, quantidade de cada item) na visão
individual — a restrição que existia antes (só total pras "fora do
contrato") foi removida a pedido do Wallace. Pras "fora do contrato", a tela
só mostra um aviso de contexto ("é só pra referência, não faz parte do
escopo do contrato") acima da mesma tabela detalhada.

Os dados tratados (`Pendencias`) sempre foram completos pras duas situações
— a restrição antiga era só na camada de exibição do dashboard.

## Regra de agrupamento no site (definida pelo Wallace)

Aeronaves **"Sem condições" nunca entram no grupo "sem pendências"/regulares**, mesmo quando `total_pendencias` é 0 — elas ficam sempre na área de prioridade/atenção, junto com as Desmontadas. Só entram na seção "regulares" (recolhida) as aeronaves **Montadas** (que por definição já têm 0 pendência).

## Histórico por aeronave (a partir de 2026-07-06)

O RAC sempre sobrescreveu a cópia local a cada busca — não existe histórico
anterior a 2026-07-06. A partir dessa data, toda vez que a atualização
automática roda (seg-sex 12h, ver `00_Instrucoes/atualizacoes.md`), o script
também acrescenta um **snapshot do dia, item a item** (matrícula, PN,
nomenclatura, quantidade faltante) em
`02_Dados_Tratados/historico_rac.csv` — nunca sobrescreve dias anteriores, só
substitui o snapshot do próprio dia se rodar de novo na mesma data (evita
duplicar).

Na visão individual de cada aeronave (RAC → clicar numa aeronave), a aba
**"Histórico"** mostra: gráfico de evolução do total de PNs distintos
faltantes ao longo dos dias registrados, e um seletor pra ver o detalhe
item a item de um dia específico.

Enquanto o histórico for curto (poucos dias registrados), o gráfico vai
parecer "vazio"/pouco informativo — isso é esperado, ele cresce sozinho a
cada dia útil.

### Cruzamento com a Disponibilidade Diária (a partir de 2026-07-06)

A tabela "Pendências x situação operacional, por dia" (na aba Histórico)
mostra, lado a lado, o total de PNs faltantes daquele dia **e** a situação
operacional (DI/DO/II/IN/ITR/IS/IP) da mesma aeronave na Disponibilidade
Diária do mesmo dia — dá pra ver, por exemplo, se uma aeronave ficou
indisponível justamente nos dias em que tinha mais pendência de material.

A coluna "Situação (Disponibilidade)" só aparece nas datas em que **as duas**
fontes têm dado daquele dia (RAC desde 2026-07-06, Disponibilidade só
seg-sex) — mostra "—" quando falta uma das duas. Aeronaves **sem nenhuma
pendência** no RAC nunca aparecem em `historico_rac.csv` (só registramos
PN com falta > 0), então não têm com o que cruzar — isso é esperado, não é
falha de coleta.

## Evolução diária + histórico da frota inteira (2026-07-23)

Pedido do Wallace: "coloca uma evolucao diaria e historico na RAC tb"
(mesmo princípio já usado em Disponibilidade Diária/Empréstimos, mas aqui
pra frota inteira, não uma aeronave de cada vez — o histórico por
aeronave já existia, ver seção acima). Nova aba **"Evolução"** na tela RAC
(`coordenadoria/secoes/rac.py::_secao_evolucao`), ao lado de "Aeronaves",
"Materiais críticos" e "Matriz RAC":

- **Evolução diária**: 3 gráficos de linha a partir do mesmo
  `historico_rac.csv` (agrupado por dia, sem filtrar por aeronave) — PNs
  distintos faltantes, aeronaves afetadas e unidades faltantes totais, por
  dia.
- **"O que mudou de um dia para o outro"**: compara os 2 últimos dias com
  snapshot salvo, por chave **matrícula + PN** — mostra quantas pendências
  são novas (apareceram) e quantas foram resolvidas (item chegou ou a
  aeronave saiu de pendência), com expander pra ver os itens de cada
  grupo.
- **Histórico diário (resumo)**: tabela com uma linha por dia (Data, PNs
  distintos, Aeronaves afetadas, Unidades faltantes), mais recente
  primeiro, exportável em CSV.

## Decisões já tomadas (não usar % de completude)

Em vez de "% de completude" (sem base de cálculo confiável — a planilha só traz o que falta, não um total de itens exigidos por aeronave), usar **faixas por quantidade de unidades faltantes**:

* Sem pendências;
* 1 a 5 unidades faltantes;
* 6 a 15 unidades faltantes;
* Mais de 15 unidades faltantes.

Implementado em `paleta.py` (`faixa_pendencia`, `ORDEM_FAIXAS`).

## "Pontos de atenção" só considera aeronaves dentro do contrato (2026-07-15)

Pedido do Wallace: "ajeita o dashboard inteiro com as novas informacoes,
tira coisas das aeronaves fora do contrato nos pontos de atencao".
`_pontos_atencao()` (RAC e Dashboard Geral) filtra `aeronaves` por
`contrato == "Dentro do contrato"` antes de montar qualquer item da lista
(sem condições, top pendências, PN mais crítico) — aeronave fora do
contrato já tem seu próprio quantitativo em outro lugar da tela (cards),
não precisa repetir aqui. No Dashboard Geral, os alertas de Disponibilidade
Diária e Diagonal de Manutenção também passaram a excluir aeronaves fora
do contrato (cruzando pela matrícula com o RAC), pro "pontos de atenção"
ficar consistente em todas as fontes que ele combina.
