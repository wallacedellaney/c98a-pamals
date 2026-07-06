# C-98A PAMALS

Pasta guarda-chuva com uma única página principal, que dá acesso a 2 áreas:

* **Coordenadoria** — ainda não desenvolvida. Ver `Coordenadoria/CLAUDE.md`.
* **Contrato 005/CELOG/2025** — dashboard completo (emergências, reparáveis, pagamentos). Ver `Contrato 005/Dashboard/CLAUDE.md`.

## Estrutura

```
C-98A PAMALS/
├── app.py                     <- página principal (menu com as 2 áreas)
├── .streamlit/config.toml     <- tema "Torre de Controle", compartilhado
├── .secrets/                  <- credencial da conta de serviço do Google (nunca commitar)
├── shared/                    <- drive_sync.py + estado.py, usados pelas 2 áreas (ver 00_Instrucoes/atualizacoes.md)
├── 00_Instrucoes/atualizacoes.md  <- atualização sob demanda por fonte, com Drive real
├── Contrato 005/Dashboard/    <- projeto completo do Contrato 005 (ver CLAUDE.md próprio)
└── Coordenadoria/             <- esqueleto vazio, a desenvolver junto
```

## Atualização de dados — automática (3 fontes) + manual (as demais)

Disponibilidade Diária (seg-sex 10h), Emergências (seg-sex 12h) e Pagamentos
(toda segunda 10h) atualizam **sozinhos**, via `launchd` no Mac do Wallace +
`shared/drive_sync.py` (credencial própria, `.secrets/service_account.json`)
+ `shared/executar_atualizacao.py` (busca, reprocessa, commita e dá push
sozinho — o Streamlit Cloud reimplanta automaticamente). As demais fontes
(Reparáveis, Vencimentos, RAC, Diagonal de Manutenção) continuam manuais —
Wallace pede na conversa. Ver `00_Instrucoes/atualizacoes.md` para a
arquitetura completa e como adicionar uma fonte nova ao agendamento.

## Comando "executar" / "roda"

Quando o Wallace disser "executa" ou "roda" (sem mais detalhes), fazer:

1. Rodar `Contrato 005/Dashboard/05_Scripts/python/gerar_dados_tratados.py` para regenerar os dados tratados do Contrato 005.
2. Subir (ou reaproveitar) `streamlit run app.py` a partir desta pasta (`C-98A PAMALS/`) na porta 8501 — **não** rodar o `app.py` de dentro de `Contrato 005/Dashboard/03_Dashboard/` diretamente, esse é só um runner standalone de fallback.
3. Devolver o link `http://localhost:8501`.

Isso não busca dados novos do Google Sheets sozinho — ver a seção equivalente em `Contrato 005/Dashboard/CLAUDE.md`.

## Como a página principal chama o Contrato 005

`app.py` (nesta pasta) importa `contrato_app.render()` de dentro de `Contrato 005/Dashboard/03_Dashboard/`, inserindo essa pasta em `sys.path`. Os módulos internos do Contrato 005 (`data`, `secoes`, `components`) ficam dentro do pacote `contrato005` (em `03_Dashboard/contrato005/`) justamente para não colidir com módulos de mesmo nome que a Coordenadoria vier a ter — quando for criar a Coordenadoria, seguir o mesmo padrão (pacote próprio, não módulos soltos `data`/`secoes`/`components`).
