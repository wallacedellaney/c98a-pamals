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
- Formato do arquivo: **.docx** (igual às versões anteriores na pasta Auditoria) — **não** é PDF. Uma cópia vai para a pasta do mês em "Fechamento mensal" (ex.: `09 SETEMBRO`, a mesma pasta onde fica a RMA Finalizada).
- O PDF que vai para o fechamento é o da **RMA completa da empresa** (`RMA ... Finalizada.pdf`), não o da auditoria. Só conferir se já está lá; não precisa gerar.

### Depois da auditoria: registrar na planilha "Devoluções" e avisar o fiscal (2026-10-08)
1. **Escrever na planilha** (aba "DEVOLUÇÃO"), seguindo o padrão que já está nas células:
   - Coluna **"Observação Fiscal"** (U): **acrescentar** (nunca apagar o que já existe) um trecho no formato
     `Auditoria Consumíveis — DD/MM/AAAA (vN): <o que o recibo mostra> — <quem recebeu / data / local, quando houver>.`
     Ex. real da v4: `Auditoria Consumíveis — 01/10/2026 (v4): recibo 135/FAB/25 confirma devolução — recebido por Jomilson José da Silva (SO) em 08/10/2025, Base Aérea de Natal.`
   - Coluna **"Status"** final (W): "OK" só para **devolução real confirmada** (célula verde); emergência/MAPEM/condenado/sem motivo/recibo não encontrado ficam **vazias** (amarelo = entregaram mas não foi aceito como devolução); "Desconsiderado" só para a isenção de colisão com pássaros (linhas 4-10).
2. **Responder ao fiscal (Wallace) aqui no chat**, nesta ordem:
   - avisar **o que foi escrito** na planilha (quais linhas, qual texto);
   - **resumo comparando com a versão anterior** da auditoria (o que mudou de categoria, linhas novas no universo, recibos que apareceram/sumiram);
   - **lista das linhas que podem receber "OK"** (devolução real confirmada e ainda sem OK) — perguntar antes de marcar, a decisão é do fiscal.
3. Depois rodar `extrair_devolucoes.py --atualizar-do-drive` para o site (tela Empréstimos) refletir a planilha.

## Gatilho para o futuro
Sempre que o Wallace disser algo como "checar RMA" / "atualizar RMA" / "fazer a auditoria":
1. Reparáveis (1.8/1.9/1.10) — rodar `atualizar_do_mes`, lembrar dos condenados (1.9).
2. Devoluções: colar 1.13 (Finalizada) na aba "RMA" da planilha Devoluções, propagar pra aba "DEVOLUÇÃO".
3. Fazer a auditoria de Consumíveis (CAT=C, RC preenchido) seguindo o padrão acima, novo arquivo .docx no Drive (pasta Auditoria + cópia no Fechamento mensal do mês). Conferir se o PDF da RMA completa está no fechamento.
4. Registrar o resultado na planilha "Devoluções" (Observação Fiscal + Status) e responder ao fiscal no chat: o que foi escrito, comparação com a versão anterior e quais linhas podem receber "OK".
5. Depois de tudo, atualizar os sites/dashboards (reparáveis e devoluções) com os dados novos.
