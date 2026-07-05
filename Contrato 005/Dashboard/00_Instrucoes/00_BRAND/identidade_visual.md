# Identidade Visual — Dashboard Contrato 005 (C-98)

Direção aprovada: **Torre de Controle**. Fundo escuro de sala de radar, âmbar de aviso de painel, ciano de escopo, números em monoespaçada tabular como um HUD. Assume que quem abre o dashboard está operando, não só lendo um relatório.

## Paleta

| Token | Hex | Uso |
|---|---|---|
| `bg` | `#10151b` | Fundo geral do app |
| `panel` | `#161d24` | Fundo de cards/painéis |
| `ink` | `#eef2f4` | Texto primário |
| `secondary` | `#7e93a1` | Texto secundário, labels, legendas |
| `line` | `#2a343d` | Bordas, divisores, grade |
| `amber` (accent) | `#f2a93b` | Cor de marca / destaque principal — nav ativa, marca, ênfase |
| `cyan` | `#5fd0d9` | Destaque secundário — relógio/data, séries secundárias em gráfico |
| `good` (status) | `#4fb477` | Indicador positivo (ex.: no prazo, pago) |
| `critical` (status) | `#e2564f` | Indicador crítico (ex.: atrasado, condenado) |

Regra: `amber`/`cyan` são cor de marca — não usar como cor de status. `good`/`critical` são reservadas para estado — nunca usar como cor de série qualquer.

## Tipografia

Fonte única, monoespaçada, em todo o dashboard (dados e texto): `"SF Mono", "Roboto Mono", ui-monospace, Menlo, monospace`.

* Números de indicador: `font-variant-numeric: tabular-nums`, peso 600, sem decoração.
* Labels/eyebrows: uppercase, `letter-spacing: 0.08em–0.14em`, tamanho pequeno (~0.6–0.7rem), cor `secondary`.
* Texto corrido (observações, tabelas): mesma família monoespaçada, peso 400.

## Componentes

* **Marca**: círculo com borda `amber` (1.5px) contendo "98", ao lado do nome "C-98 / OPS" + subtítulo "CONTRATO 005 · CELOG-PAMALS" em `secondary`.
* **Cards/painéis**: fundo `panel`, borda 1px `line`, cantos levemente arredondados (3px — não usar `rounded-lg` genérico). Label uppercase em `secondary`, valor grande tabular em `ink` (ou `good`/`critical` quando for daquele tipo).
* **Navegação (4 abas na base)**: uppercase, letter-spacing, cor `secondary`; aba ativa em `amber` com sublinhado de 2px.
* **Gráficos**: barras/linhas em `amber` como cor primária de magnitude; `cyan` como segunda série quando necessário; `good`/`critical` só para status binário (ex.: no prazo x atrasado). Fundo do gráfico transparente/`panel`, grade em `line`, texto em `secondary`.

## O que não fazer

* Não usar gradientes, sombras pesadas ou cantos muito arredondados — a estética é de painel de instrumento, não de app consumer.
* Não introduzir uma quinta cor de destaque — usar `amber`/`cyan`/`good`/`critical` cobre os casos.
* Não usar fonte serifada em lugar nenhum.
