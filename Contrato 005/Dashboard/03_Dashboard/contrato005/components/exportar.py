"""Exportação genérica de uma tabela (DataFrame) pra XLSX e PDF — usado nos
botões de download de Atrasos/Justificativas (pedido do Wallace, 2026-08-03:
"os dados de atrasos e justificativas de emergencia ter opcao de download em
pdf e xlsx", além do CSV que já existia). Sem dependência de nenhuma área
específica — qualquer seção pode reaproveitar.
"""

import io

import pandas as pd
from fpdf import FPDF
from fpdf.fonts import FontFace

from contrato005.components.paleta import AMBER

# Cor de texto pro PDF (fundo branco) — NÃO usar a paleta INK/PANEL/LINE
# do site (pensada pro tema escuro): um teste real mostrou texto quase
# invisível (cinza muito claro sobre fundo branco) usando a cor INK aqui.
_TEXTO_ESCURO = (30, 30, 30)


def gerar_xlsx_bytes(df, nome_aba="Dados"):
    """DataFrame -> bytes de um .xlsx com 1 aba, colunas com largura
    ajustada ao conteúdo (senão o Excel abre tudo cortado, "###")."""
    nome_aba = nome_aba[:31]  # limite do Excel pra nome de aba
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=nome_aba)
        planilha = writer.sheets[nome_aba]
        for i, coluna in enumerate(df.columns, start=1):
            maior = max([len(str(coluna))] + [len(str(v)) for v in df[coluna].head(200)])
            planilha.column_dimensions[planilha.cell(row=1, column=i).column_letter].width = min(maior + 2, 60)
    return buffer.getvalue()


def _cor_rgb(hex_str):
    hex_str = hex_str.lstrip("#")
    return tuple(int(hex_str[i:i + 2], 16) for i in (0, 2, 4))


# A fonte padrão (Helvetica) só cobre latin-1 — sem fonte Unicode
# empacotada, emoji/travessão quebrariam a geração do PDF
# (FPDFUnicodeEncodingException, achado real gerando o primeiro teste).
# Em vez de embutir uma fonte TTF só pra isso, troca os caracteres comuns
# do site por equivalente em texto puro e descarta qualquer resto que a
# fonte não aguente (nunca quebra, mesmo com emoji novo no futuro).
_SUBSTITUICOES = {
    "—": "-", "–": "-", "✅": "[OK]", "⏳": "[Pendente]", "⚠️": "[!]", "⚠": "[!]",
}


def _texto_seguro(valor):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    texto = str(valor)
    for original, troca in _SUBSTITUICOES.items():
        texto = texto.replace(original, troca)
    return texto.encode("latin-1", errors="ignore").decode("latin-1")


def gerar_pdf_bytes(df, titulo, subtitulo=None):
    """DataFrame -> bytes de um .pdf paisagem (A4), com uma tabela que
    quebra linha automaticamente célula a célula — pensado pra tabelas com
    bastante coluna e texto livre (observações, justificativa)."""
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*_TEXTO_ESCURO)
    pdf.cell(0, 8, _texto_seguro(titulo), new_x="LMARGIN", new_y="NEXT")
    if subtitulo:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 6, _texto_seguro(subtitulo), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*_TEXTO_ESCURO)
    with pdf.table(
        col_widths=None,
        text_align="LEFT",
        line_height=4,
        headings_style=FontFace(emphasis="B", fill_color=_cor_rgb(AMBER), color=(20, 20, 20)),
        borders_layout="ALL",
    ) as tabela:
        linha = tabela.row()
        for coluna in df.columns:
            linha.cell(_texto_seguro(coluna))
        for _, dados_linha in df.iterrows():
            linha = tabela.row()
            for valor in dados_linha:
                linha.cell(_texto_seguro(valor))

    return bytes(pdf.output())
