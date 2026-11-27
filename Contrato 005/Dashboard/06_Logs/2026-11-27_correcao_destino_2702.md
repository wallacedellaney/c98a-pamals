# Correção de destino das emergências do 2702 — 27/11/2026

Pedido do fiscal: alterar o site para respeitar o comentário das emergências 386260013673 e 386260013674, geradas para atender a aeronave 2743.

- Fontes lidas: histórico completo de emergências, RAC e arquivos do cômputo de novembro, na revisão remota vigente.
- Correção: excluir somente essas ocorrências da negativação da origem, sem remover o 2702 do contrato nem criar penalidade no 2743. Regra aplicada ao cálculo oficial e à linha VEE ONE.
- Dados regenerados: matriz, motivos, resumo e linha VEE ONE de novembro, mantendo o limite já publicado de 26/11/2026. Nenhuma atualização de planilha ou fabricação de dados dos dias seguintes.
- Conferência real: apenas 2702 nos dias 25 e 26 passa de 0 para 1; motivos de 23 para 21; MMAM de 79,56% para 79,88%. Todas as outras células da matriz e o conjunto contratual foram preservados.
- Testes: quatro casos de regressão, com falha reproduzida antes da correção e sucesso depois; destino igual e comentário genérico/ausente preservam impedimentos válidos.
- Erros: nenhum nos testes finais. Inconsistências: nenhuma adicional na base regenerada.
- Próximas ações: conferir implantação automática dos dois sites; futuras extrações reaplicam a regra.
