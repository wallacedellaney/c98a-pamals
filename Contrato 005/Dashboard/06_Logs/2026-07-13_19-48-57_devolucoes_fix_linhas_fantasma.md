# Execução: devolucoes_fix_linhas_fantasma

Data: 2026-07-13 19:48:57

## Arquivos lidos
- extrair_devolucoes.atualizar_do_drive()

## Arquivos gerados
- extrair_devolucoes.py (exige Part Number preenchido, não só numero_ordem)
- base_devolucoes_tratada.xlsx (330 itens, era 424)
- 00_Instrucoes/emprestimos.md

## Inconsistências encontradas
- 94 linhas totalmente em branco (numero_ordem 332-425 arrastado por fórmula) eram contadas como itens Pendente reais, inflando o total. Achado pelo Wallace.

## Erros
- nenhum

## Próximas ações recomendadas
- nenhuma
