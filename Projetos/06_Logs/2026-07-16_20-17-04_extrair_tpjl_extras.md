# Execução: extrair_tpjl_extras

Data: 2026-07-16 20:17:04

## Arquivos lidos
- /home/runner/work/c98a-pamals/c98a-pamals/Projetos/01_Bases_Originais/TPJL_Consumo/relatorio_consumo.xlsx
- /home/runner/work/c98a-pamals/c98a-pamals/Projetos/01_Bases_Originais/TPJL_Estoque/relatorio_estoque.xlsx
- /home/runner/work/c98a-pamals/c98a-pamals/Projetos/01_Bases_Originais/TPJL_Solicitacoes/relatorio_solicitacoes.xlsx

## Arquivos gerados
- /home/runner/work/c98a-pamals/c98a-pamals/Projetos/02_Dados_Tratados/base_tpjl_extras.xlsx

## Inconsistências encontradas
- relatorio_consumo: 412 linha(s) completamente duplicada(s) — removidas (mesma regra de 'só remover se idêntica' já usada no TPJL, ver tpjl.md).
- relatorio_solicitacoes: 596 valor(es) de 'ultima_atualizacao' fora do formato DD/MM/AAAA HH:MM — mantidos como texto original, não convertidos.

## Erros
- nenhum

## Próximas ações recomendadas
- nenhuma
