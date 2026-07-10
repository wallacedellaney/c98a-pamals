"""Configuração central do TPJL — nomes/IDs/colunas num só lugar. Ver
00_Instrucoes/tpjl.md. 2025 e 2026 continuam SEPARADOS (decisão do Wallace em
2026-07-09) — cada ano tem seu próprio mapeamento de coluna porque a aba
"COORDENADORES" de 2025 tem 2 colunas extras (duplicadas/sem uso, ver
extrair_tpjl.py) que a de 2026 não tem."""

ABA = "COORDENADORES"
PJT_FILTRO = "U8"

FONTES = {
    2025: {
        "drive_file_id": "1zkBB77PXvzRTg-8n-tgNAYX8lJB8KozPvuyGiNtARsA",
        "planilha": "TPOB - Controle CABW 2025",
        "colunas": {
            "numero_requisicao": 0, "nd": 1, "pjt": 2, "pn": 3, "descricao": 4,
            "qtd": 5, "valor_unit": 6, "valor_total": 7,
            "status_comprar": 8, "status_11g": 9,
            # índices 10/11 na planilha real de 2025 são uma dupla extra
            # STATUS COMPRAER/STATUS 11G sem uso real (valores sempre None/0
            # nas linhas conferidas) — ignorados de propósito.
            "status": 12, "previsao_empenho": 13, "dpe": 14, "observacao_coordenadores": 15,
        },
        "max_col": 16,
    },
    2026: {
        "drive_file_id": "1Mf_R70IDJ9auysySW1oATGt3TSrPZE081-O3nB930lc",
        "planilha": "TPOB - Controle CABW 2026",
        "colunas": {
            "numero_requisicao": 0, "nd": 1, "pjt": 2, "pn": 3, "descricao": 4,
            "qtd": 5, "valor_unit": 6, "valor_total": 7,
            "status_comprar": 8, "status_11g": 9,
            "status": 10, "previsao_empenho": 11, "dpe": 12, "observacao_coordenadores": 13,
        },
        "max_col": 14,
    },
}

# Status considerados "finais" — não contam mais como pendência nem como
# vencido (ver tpjl_regras.py). "Cancelada"/"Cancelado" já chegam agrupados
# pelo status_atual.
STATUS_FINAIS = {"Empenhado", "Cancelado", "Item Deserto", "Item Fracassado"}
