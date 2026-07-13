# Execução: fix_pn_tipo_misto_sorted_arrow

Data: 2026-07-13 15:22:32

## Arquivos lidos
- reparaveis.py (crash reportado no Streamlit Cloud)

## Arquivos gerados
- contrato005/components/utils.py (novo: ordenar_unicos)
- 7 arquivos de secoes/ atualizados pra usar ordenar_unicos em vez de sorted() direto
- extrair_reparaveis.py e extrair_emergencias.py: nova parse_texto_pn() normaliza PN pra string na extração
- base_reparaveis_tratada.xlsx e base_emergencias_tratada.xlsx regenerados com PN 100% string

## Inconsistências encontradas
- TypeError: sorted() quebrava com PN misto int/str (coluna pn com célula só-numérica lida como int pelo openpyxl); mesma causa também quebrava a conversão pra Arrow do st.dataframe.

## Erros
- nenhum

## Próximas ações recomendadas
- Nenhuma — causa raiz corrigida na extração, não só nas telas.
