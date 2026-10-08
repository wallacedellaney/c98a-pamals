# Auditoria de Consumíveis e atualização de Devoluções (2026-10-08)

Processo padrão sempre que o Wallace pedir para "checar a RMA" / "atualizar a RMA". Junta três frentes que usam abas diferentes do mesmo arquivo `RMA ... Finalizada.xlsx` (anexo mensal recebido por e-mail da empresa VEE ONE):

## 1. Reparáveis (abas 1.8, 1.9, 1.10) — já automatizado
Ver `reparaveis.md`, seção "Complemento com a RMA em andamento". Rodar `atualizar_do_mes(ano, mes)` em `extrair_reparaveis_rma.py`. Cruza:
- 1.8 — devolvidos no mês
- 1.9 — **condenados** (não esquecer: entram no complemento mas não contam como devolução útil)
- 1.10 — controle acumulado de OS abertas

## 2. Devoluções (aba 1.13 da RMA) — planilha "Devoluções" no Drive
A aba **1.13 — "Devolução de itens atendidos pelo estoque FAB"** da RMA é o espelho cumulativo (mesma lógica da 1.10: acumulado, não só do mês) da planilha Google Sheets **"Devoluções"** (`fileId 1czUWXVjQt7fPz7GJgdPp3rsxPn_5Uck44voBsJIiRWI`, aba **RMA** dentro dela é o cole bruto dessa tabela 1.13; aba **DEVOLUÇÃO** é a cópia de trabalho onde entram as colunas extras de auditoria fiscal).

Colunas que batem 1:1 entre a aba 1.13 da RMA e a aba "RMA"/"DEVOLUÇÃO" da planilha: Nº de Ordem, Part Number, Descrição, SN/LT, QTD, CAT, GMM/Pedido de envio FAB, Data de Envio FAB, Rastreio, ANV atendida, Destino, PN devolvido, Status, Recibo/Nº da RC, NF de devolução, Data de Devolução.

**Passo**: colar a aba 1.13 da RMA (versão **Finalizada**, nunca a Pré-RMA — mesmo bug que já corrigimos nos reparáveis, ver `extrair_reparaveis_rma.py`) na aba "RMA" da planilha "Devoluções", e então propagar PN devolvido/Status/Nº da RC/Data de Devolução novos ou alterados para a aba de trabalho "DEVOLUÇÃO" (sem sobrescrever o que já foi preenchido manualmente na auditoria fiscal — Observação Fiscal, Observação Empresa, Status final da coluna W).

## 3. Auditoria Consumíveis (mensal, documento no Drive)
Pasta Drive **Auditoria** (`folderId 1azF4106GmWXE2NNzGrLqAy8jlBDSuqMV`, dentro de `Contrato 005/CELOG-PAMALS/2025`). Um arquivo por mês, nome `Auditoria Consumíveis - <Mês>/<Ano> (vN)`, incrementando a versão (vN) a cada nova rodada no mesmo mês. Guardar também uma cópia na pasta "Fechamento mensal" do mês correspondente.

**Padrão do documento** (ver versões "Setembro v3" e "Outubro v4" já no Drive):
- Universo: linhas da aba "DEVOLUÇÃO" com **CAT = "C"** (Consumível) **e Nº da RC preenchido** — a cada rodada nova, o universo pode crescer (v4 ampliou de 19 para 34 linhas incluindo as que já estavam "OK" e nunca tinham sido conferidas contra o recibo real).
- Cruzamento: PN devolvido + S/N + Data de Devolução contra o **conteúdo real** de cada Termo de Recebimento / Recibo de Entrega no Drive (abrir o link e ler o PDF, não só confiar no que a empresa preencheu).
- Categorias de resultado (seções do documento, cada uma com tabela e contagem):
  1. CONFIRMADO — devolução real
  2. CONFIRMADO, MAS NÃO FOI DEVOLUÇÃO — usado para atender emergência (material saiu, não voltou)
  3. CONFIRMADO, MAS NÃO FOI DEVOLUÇÃO — usado em MAPEM
  4. CONFIRMADO — item condenado / sucata (não é devolução de material útil)
  5. Entrega sem motivo especificado no recibo
  6. Recibo não encontrado no Drive
  7. Resumo (tabela com a contagem de cada categoria + total)
- Depois de escrever o documento, registrar as mesmas observações na coluna **"Observação Fiscal"** (U) da aba "DEVOLUÇÃO", e ajustar a coluna **"Status"** (W): "Desconsiderado" só para isenção por colisão de pássaros; as reclassificadas como "não foi devolução" (emergência/MAPEM) voltam para **vazio** na coluna de status antigo (Q) ou recebem cor amarela; cor verde = aceito como devolução.
- **Exportar para PDF**: converter o `.xlsx`/`.docx` para PDF e ajustar a área de impressão/paginação (orientação, largura de colunas) para que as tabelas não quebrem de forma estranha entre páginas.

## Gatilho para o futuro
Sempre que o Wallace disser algo como "checar RMA" / "atualizar RMA" / "fazer a auditoria":
1. Reparáveis (1.8/1.9/1.10) — rodar `atualizar_do_mes`, lembrar dos condenados (1.9).
2. Devoluções: colar 1.13 (Finalizada) na aba "RMA" da planilha Devoluções, propagar pra aba "DEVOLUÇÃO".
3. Fazer a auditoria de Consumíveis (CAT=C, RC preenchido) seguindo o padrão acima, novo arquivo no Drive (pasta Auditoria + cópia no Fechamento mensal), exportar PDF.
4. Depois de tudo, atualizar os sites/dashboards (reparáveis e devoluções) com os dados novos.
