"""Interpretação compartilhada dos valores de "Controle de Vencimentos" — usada
tanto pelo TMOT (planilha única C-98U8) quanto pelo compilador por operador
(cada operador escreve os valores de um jeito diferente, ver
00_Instrucoes/vencimentos.md).

Regra confirmada pelo Wallace: a coluna DISPONIBILIDADE não tem uma coluna
própria de "tipo" — é preciso inferir pelo FORMATO do valor. Isso vale mesmo
quando a planilha já tem seções "POR HORA/POR POUSO/POR CALENDÁRIO" marcadas,
porque alguns operadores misturam linhas de tipos diferentes dentro da mesma
seção (ex.: CLA tem uma linha "5M" dentro da seção "POR HORA").
"""

import re
from datetime import date

RE_MES_DIA = re.compile(r"^(-?)(\d+)\s*m\s*e\s*(\d+)\s*d$", re.IGNORECASE)
RE_MES = re.compile(r"^(-?\d+(?:[.,]\d+)?)\s*(?:m|m[eê]s(?:es)?)\.?$", re.IGNORECASE)
RE_DIA = re.compile(r"^(-?\d+(?:[.,]\d+)?)\s*d(?:ias?)?\.?$", re.IGNORECASE)
RE_ANO = re.compile(r"^(-?\d+(?:[.,]\d+)?)\s*a(?:no)?(?:s)?\.?$", re.IGNORECASE)
RE_POUSO = re.compile(r"^(-?\d+(?:[.,]\d+)?)\s*p(?:ouso)?(?:s)?\.?$", re.IGNORECASE)
# Hora aceita tanto dígitos corridos ("3321:35") quanto com ponto de milhar
# ("4.938:00", visto na BANT) — os dois formatos convivem na mesma fonte.
RE_HORA_TEXTO = re.compile(r"^-?(\d{1,3}(?:\.\d{3})+|\d{1,5}):\d{2}(?::\d{2})?$")
RE_NUMERO_PURO = re.compile(r"^-?\d+(?:[.,]\d+)?$")
# Algumas linhas da BANT anotam o equivalente em meses entre parênteses
# depois do valor de horas (ex.: "1.337:20 (19,8 M)") — é só informativo,
# a hora antes do parêntese já é o valor real.
RE_ANOTACAO_FINAL = re.compile(r"\s*\([^()]*\)\s*$")

# "On Condition" (BACG): item monitorado por condição, sem vencimento
# programado por hora/pouso/calendário — não é dado ausente/errado, é uma
# categoria própria e reconhecida (aviação de manutenção).
VALORES_ON_CONDITION = {"O/C", "ON CONDITION", "ON-CONDITION", "ONCONDITION"}

# "Não instalado" (BANT): item/motor que não está instalado na aeronave no
# momento — não tem vencimento a calcular, não é dado ausente/errado.
VALORES_NAO_INSTALADO = {"ANV S/ MOTOR", "NÃO INSTALADO", "NÃO INSTALADA", "NÃO INSTALADOS", "NÃO INSTALADAS", "SEM MOTOR"}

# "Vencida" (BANT): a fonte escreveu que já venceu, mas sem informar o valor
# (quanto passou do limite) — sabemos que é vencido, não sabemos por quanto.
VALORES_VENCIDO_SEM_VALOR = {"VENCIDA", "VENCIDO"}

MESES_PT = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}
# Aceita espaço em volta da barra ("JUL / 27", visto na BANT) além do formato
# compacto ("out/2033").
RE_MES_ANO_PT = re.compile(r"^([a-zç]{3})[a-zç]*\s*[/\-]\s*(\d{2,4})$", re.IGNORECASE)
RE_DATA_BR = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$")
RE_MES_ANO_NUM = re.compile(r"^(\d{1,2})/(\d{2})$")

# Data-estimada-de-vencimento nunca é histórica de verdade (é sempre uma
# projeção futura de manutenção) — datas reais anteriores a isso indicam erro
# de formatação/digitação na origem (ex.: célula de duração lida como data
# do calendário de 1900 do Excel). Mesmo princípio já usado pro TMOT.
ANO_MINIMO_DATA_VENCIMENTO = 2000


def classificar_disponibilidade(valor):
    """Retorna (tipo, valor_numerico, texto_original). tipo em
    {"Hora","Pouso","Calendário",None,"Desconhecido"}. Para Calendário,
    valor_numerico é sempre em dias (mês aproximado como 30 dias)."""
    if valor is None:
        return None, None, None
    if hasattr(valor, "total_seconds"):
        return "Hora", round(valor.total_seconds() / 3600, 1), None
    if isinstance(valor, (int, float)):
        return "Pouso", valor, None
    if isinstance(valor, str):
        texto = valor.strip()
        if not texto:
            return None, None, None
        if texto.upper() in VALORES_ON_CONDITION:
            return "Condição", None, "On Condition"
        if texto.upper() in VALORES_NAO_INSTALADO:
            return "Não instalado", None, texto
        if texto.upper() in VALORES_VENCIDO_SEM_VALOR:
            return "Vencido (sem valor)", None, texto
        texto_sem_anotacao = RE_ANOTACAO_FINAL.sub("", texto)
        if RE_HORA_TEXTO.match(texto_sem_anotacao):
            partes = texto_sem_anotacao.replace(".", "").split(":")
            sinal = -1 if partes[0].startswith("-") else 1
            h = abs(int(partes[0]))
            m = int(partes[1])
            s = int(partes[2]) if len(partes) > 2 else 0
            return "Hora", sinal * round(h + m / 60 + s / 3600, 2), None
        m = RE_MES_DIA.match(texto)
        if m:
            sinal = -1 if m.group(1) == "-" else 1
            dias = sinal * (int(m.group(2)) * 30 + int(m.group(3)))
            return "Calendário", dias, texto
        m = RE_MES.match(texto)
        if m:
            return "Calendário", round(float(m.group(1).replace(",", ".")) * 30), texto
        m = RE_DIA.match(texto)
        if m:
            return "Calendário", round(float(m.group(1).replace(",", "."))), texto
        m = RE_ANO.match(texto)
        if m:
            return "Calendário", round(float(m.group(1).replace(",", ".")) * 365), texto
        m = RE_POUSO.match(texto)
        if m:
            return "Pouso", float(m.group(1).replace(",", ".")), None
        # Fonte leu como texto (ex.: CSV/ODS) mas é só um número puro sem
        # sufixo — mesma regra do int/float acima, só que em string.
        if RE_NUMERO_PURO.match(texto):
            return "Pouso", float(texto.replace(",", ".")), None
    return "Desconhecido", None, str(valor)


def vencido_de(tipo, valor_numerico):
    """Calcula o campo "vencido" (bool ou None) a partir do tipo e do valor.
    A maioria dos tipos usa valor_numerico < 0; "Vencido (sem valor)" (ex.:
    BANT escreveu "VENCIDA" sem informar o valor) já é sabidamente vencido
    mesmo sem número. Tipos sem vencimento aplicável (Condição, Não
    instalado) ficam None — não é nem vencido nem "ok"."""
    if tipo == "Vencido (sem valor)":
        return True
    if valor_numerico is not None:
        return valor_numerico < 0
    return None


def parse_data_vencimento(valor, dia_padrao=1):
    """Aceita datetime/date real, "DD/MM/AAAA" ou "mmm/aaaa" (abreviação
    portuguesa do mês, ex.: "out/2033", "mar/2028"). Retorna date ou None —
    não inventa data quando não reconhece."""
    if valor is None:
        return None
    if hasattr(valor, "date"):
        d = valor.date()
        return d if d.year >= ANO_MINIMO_DATA_VENCIMENTO else None
    if hasattr(valor, "year") and hasattr(valor, "month"):
        return valor if valor.year >= ANO_MINIMO_DATA_VENCIMENTO else None
    if isinstance(valor, str):
        texto = valor.strip()
        m = RE_DATA_BR.match(texto)
        if m:
            d, mth, y = m.groups()
            y = int(y)
            if y < 100:
                y += 2000
            try:
                return date(y, int(mth), int(d))
            except ValueError:
                return None
        m = RE_MES_ANO_PT.match(texto)
        if m:
            abrev, y = m.groups()
            mes = MESES_PT.get(abrev.lower())
            if mes:
                y = int(y)
                if y < 100:
                    y += 2000
                try:
                    return date(y, mes, dia_padrao)
                except ValueError:
                    return None
        m = RE_MES_ANO_NUM.match(texto)
        if m:
            mes, y = m.groups()
            try:
                return date(int(y) + 2000, int(mes), dia_padrao)
            except ValueError:
                return None
    return None


def normalizar_matricula(valor):
    """"FAB2723", "FAB 2723", "2723" -> "2723"."""
    if valor is None:
        return None
    texto = str(valor).upper().replace("FAB", "").strip()
    return texto or None
