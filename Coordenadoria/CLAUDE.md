# Coordenadoria

Área em construção — vamos aos poucos, na conversa. Não presumir escopo, fontes de dados ou indicadores sem perguntar ao Wallace antes.

Segue a mesma estrutura de pastas do Contrato 005 (`00_Instrucoes/`, `01_Bases_Originais/`, `02_Dados_Tratados/`, `03_Dashboard/`, `04_Relatorios/`, `05_Scripts/`, `06_Logs/`, `99_Backup/`).

## Princípio geral: os formatos das fontes vão mudar, sempre

Nenhuma fonte de dado da Coordenadoria (RAC, Disponibilidade Diária, Vencimentos/TMOT, Vencimentos/Operadores) tem formato garantido estável — cada planilha/relatório pode vir escrito diferente do mês anterior, cada operador/base escreve do seu jeito. **Isso é esperado, não uma exceção.** Quando aparecer um formato novo ou diferente do que já foi tratado: adaptar a ferramenta de leitura (ajustar o parser, tratar o caso novo, buscar a lib certa), nunca travar, nunca inventar o dado, e nunca presumir silenciosamente que "deve ser igual a antes". O que não for reconhecido fica de fora e vira inconsistência registrada em `06_Logs/`. Ver `00_Instrucoes/vencimentos.md` para o caso mais detalhado disso na prática.

## Frentes em andamento

* **RAC** (configuração de aeronaves — o que falta para cada uma ficar completa) — ver `00_Instrucoes/rac.md`. Extração pronta (`05_Scripts/python/extrair_rac.py`, atualização automática seg-sex 12h) e dashboard construído (`03_Dashboard/coordenadoria/secoes/rac.py`), incluindo histórico por aeronave (snapshot diário desde 2026-07-06) cruzado com a situação de Disponibilidade do mesmo dia.
* **Disponibilidade Diária** — situação operacional do dia a dia (D/M, códigos DI/DO/II/IN/ITR/IS/IP), a partir dos relatórios diários do Drive (busca automática seg-sex 10h). Ver `00_Instrucoes/disponibilidade_diaria.md`. Construído: indicadores, distribuição por situação, previsão semanal, comparação com o relatório anterior, alertas, painel por unidade, histórico/linha do tempo por aeronave (cruzado com pendências do RAC), exportação em CSV. Falta: importação manual com validação dentro do site, comparação entre duas datas quaisquer (hoje só compara com o relatório imediatamente anterior), exportação em PDF, configuração de siglas/cores.
* **Vencimentos** — mini-dashboard com duas partes: **TMOT** (planilha única "Vencimentos"/C-98U8, pronta) e **Operadores** (Controle de Vencimentos por base — todos os 9 operadores confirmados incorporados: BAMN, BABE, CLA, BANT, BABR, PAMA-LS, DACTA II, BACO, BACG). Ver `00_Instrucoes/vencimentos.md`.
* **Diagonal de Manutenção** — linha do tempo (Gantt) de indisponibilidade projetada por aeronave, a partir de hoje, com resumo mensal embaixo. Todos os 9 operadores incorporados (PAMA-LS/BACG com confiança "aproximada" — binário não transferiu íntegro). Ver `00_Instrucoes/diagonal_manutencao.md`.
* **Previsão Mensal** — stub, escopo ainda não definido.
* **Dashboard geral** — construído: visão gerencial combinando RAC, Disponibilidade Diária, Vencimentos (TMOT + Operadores) e Diagonal de Manutenção, com pontos de atenção e atalhos pras 4 áreas.

## Padrão de módulos Python

Como esta pasta compartilha o processo Streamlit com o Contrato 005 (via `C-98A PAMALS/app.py`), qualquer código do dashboard da Coordenadoria deve ficar num pacote próprio (ex.: `03_Dashboard/coordenadoria/`), nunca em módulos soltos `data`/`secoes`/`components` — para não colidir com os mesmos nomes já usados pelo Contrato 005. Ver `C-98A PAMALS/CLAUDE.md`.
