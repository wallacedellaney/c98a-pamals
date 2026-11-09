"""Publica o controle de reparáveis (estoque SILOMS) nas abas "Reparáveis – *" da planilha Devoluções.
Uso: python3 publicar_reparaveis_devolucoes.py <Reparaveis_TSAU_historico.xlsx> <relatorio-siloms-stock.xlsx> <entradas.csv> <saidas.csv>
O xlsx vem de montar_aba_reparaveis_estoque.py. Ver 00_Instrucoes/estoque_reparaveis_siloms.md."""
import sys, re, datetime as dt
from pathlib import Path
import pandas as pd, openpyxl
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from shared import drive_sync as ds
SID = "1czUWXVjQt7fPz7GJgdPp3rsxPn_5Uck44voBsJIiRWI"
ABAS = {"Saldos": 891093601, "Histórico": 891093602, "Evidências": 891093603, "Mov": 891093604}
NOME = {"Saldos": "Reparáveis – Saldos", "Histórico": "Reparáveis – Histórico", "Evidências": "Reparáveis – Evidências", "Mov": "Reparáveis – Mov. SILOMS"}
RMA_ID = 995048888
k = lambda v: re.sub(r"[^A-Z0-9]", "", str(v or "").upper())
EPOCH = dt.datetime(1899, 12, 30)
def serial(t):
    try: return (dt.datetime.strptime(str(t).strip(), "%d/%m/%Y") - EPOCH).days
    except Exception: return t
def txt(v):  # protege PN, SN, documentos de virar número/data
    if v is None: return ""
    if isinstance(v, (int, float)): return v
    t = str(v)
    return "'" + t if (re.search(r"\d", t) and not t.startswith("=")) else t
def ler(xlsx):
    wb = openpyxl.load_workbook(xlsx)
    rows = list(wb["Reparáveis"].iter_rows(values_only=True))
    resumo, i = [], 4
    while i < len(rows) and rows[i][0] not in (None, ""):
        resumo.append(rows[i]); i += 1
    hist, pn = {}, None
    for r in rows[i:]:
        if r[3] == "Tinha em 10/02/2025:": pn = r[0]; hist[pn] = []; continue
        if pn and r[0] not in (None, "", "Data") and not str(r[0]).startswith("Desde"):
            hist[pn].append(r[:7])
        elif pn and r[1] == "Sem OS nem devolução registradas; só movimento no SILOMS":
            pass
    mov = list(wb["Movimentos reparáveis"].iter_rows(values_only=True))
    return resumo, hist, mov
def main(xlsx, hoje, ent, sai):
    resumo, hist, mov = ler(xlsx)
    st = pd.read_excel(hoje, header=3); st = st[(st.Unidade == "PAMA LS") & (st.Setor == "TSAU")].copy(); st["k"] = st.PN.map(k)
    ms = pd.concat([pd.read_csv(ent, dtype=str), pd.read_csv(sai, dtype=str)]).fillna(""); ms = ms[ms.Prj == "U8"]; ms["k"] = ms.PN.map(k)
    # ---------- Histórico (formato longo) ----------
    H = [["PN", "CFF", "Data", "Evento", "Documento", "SN / Qtd", "Origem / Destino / Base", "Situação / Status", "Observação", "Fonte"]]
    primeira = {}
    for r in resumo:
        pn, cff = r[0], r[2]; primeira[pn] = len(H) + 1
        H.append([txt(pn), txt(cff), serial("10/02/2025"), "Saldo inicial no TSAU (relatório calculado)", "", r[4], "PAMALS/TSAU", "Sim" if r[17] == "Sim" else "Assumido 0 (fora do calculado)", "", "SILOMS"])
        for e in hist.get(pn, []):
            ev = str(e[1] or "")
            fonte = "SILOMS" if ev.startswith("SILOMS") else ("Controle de reparáveis (OS)" if ev.startswith(("OS de reparo", "Reparável entregue")) else "Planilha DEVOLUÇÃO")
            H.append([txt(pn), txt(cff), serial(e[0]), ev.replace("SILOMS: ", ""), txt(e[2]), txt(e[3]), txt(e[4]), txt(e[5]), txt(e[6]), fonte])
        H.append([txt(pn), txt(cff), serial("09/11/2026"), "Saldo SILOMS hoje (relatorio-siloms-stock)", "", r[9], "PAMALS/TSAU", "", "", "SILOMS"])
    # ---------- Saldos ----------
    ordem = sorted(resumo, key=lambda r: (r[4] + r[13] - r[18] == r[9], r[0]))
    S = [["PN", "Nomenclatura", "CFF", "Cód. material", "Saldo em 10/02/2025", "Entradas no TSAU (SILOMS)", "Saídas do TSAU (SILOMS)", "Saldo recalculado",
          "Saldo SILOMS em 09/11/2026", "Diferença", "Situação", "Justificativa da diferença (preencher)", "Entradas de OS externa (LEP)", "Entradas de compra (C)",
          "Outras entradas", "OS de reparo (total)", "Lançamentos na DEVOLUÇÃO", "Saldo inicial no relatório calculado?", "Saldo do relatório calculado (02/09/2026)", "Histórico"]]
    for n, r in enumerate(ordem, start=2):
        S.append([txt(r[0]), r[1], txt(r[2]), txt(r[3]), r[4], r[13], r[18], f"=E{n}+F{n}-G{n}", r[9], f"=I{n}-H{n}",
                  f'=IF(J{n}=0;"Fecha";IF(L{n}<>"";"Justificada";"A explicar"))', "", r[14], r[15], r[16], r[11], r[12],
                  "Sim" if r[17] == "Sim" else "Não", r[7] if r[17] == "Sim" else "", f'=HYPERLINK("#gid={ABAS["Histórico"]}&range=A{primeira[r[0]]}";"ver")'])
    # ---------- Evidências (itens que não fecham) ----------
    E = [["PN", "Nomenclatura", "CFF", "Saldo recalculado", "Saldo SILOMS hoje", "Diferença", "Possível causa (automática)", "Conferência / justificativa (preencher)", "Histórico"]]
    chaves = set(st.k)
    for r in ordem:
        rec = r[4] + r[13] - r[18]
        if rec == r[9]: continue
        kk = k(r[0]); causas = []
        if r[17] != "Sim": causas.append("Fora do relatório calculado: saldo inicial assumido 0")
        parecidos = sorted({p for p in st[st.k.str.startswith(kk[:max(5, len(kk) - 2)])].PN if k(p) != kk})
        if parecidos: causas.append("PN parecido no estoque de hoje: " + ", ".join(parecidos[:4]))
        tipos = st[st.k == kk]["Tipo de saldo"].unique().tolist()
        if "Reparável" in tipos: causas.append("Estoque de hoje tem saldo do tipo Reparável")
        nr = ms[(ms.k == kk) & (ms.St != "R")]
        if len(nr): causas.append(f"{len(nr)} movimento(s) não realizado(s) (status {', '.join(sorted(set(nr.St)))})")
        sub = ms[(ms.k == kk) & (ms.St == "R") & (((ms["Setor Origem"].str.startswith("TSAU")) & (ms["Setor Origem"] != "TSAU")) | ((ms["Setor Destino"].str.startswith("TSAU")) & (ms["Setor Destino"] != "TSAU")))]
        if len(sub): causas.append("Movimento com subsetor do TSAU (ex.: TSAU2)")
        E.append([txt(r[0]), r[1], txt(r[2]), rec, r[9], r[9] - rec, "; ".join(causas) or "Conferir no SILOMS", "", f'=HYPERLINK("#gid={ABAS["Histórico"]}&range=A{primeira[r[0]]}";"ver")'])
    # ---------- Mov. SILOMS ----------
    cab = list(mov[0]); idx = {c: i for i, c in enumerate(cab)}
    M = [["PN", "CFF", "Nomenclatura", "Data movimento", "Data contábil", "Tipo", "Razão", "Status", "Nº movimento", "OM origem", "Setor origem", "OM destino", "Setor destino",
          "Documento", "Qtd. material", "Efeito no TSAU", "SN / Lote", "Emergência", "Requisição", "Observação", "Gerado por"]]
    for r in mov[1:]:
        g = lambda c: r[idx[c]] if r[idx[c]] is not None else ""
        q = float(str(g("Qt. Material")).replace(".", "").replace(",", ".") or 0)
        ef = q if (g("Tp") == "E" and g("Setor Destino") == "TSAU" and g("St") == "R") else (-q if (g("Tp") == "S" and g("Setor Origem") == "TSAU" and g("OM Origem") == "PAMALS" and g("St") == "R") else 0)
        M.append([txt(g("PN")), txt(g("CodEmp")), g("Nomenclatura"), serial(g("Dt. Movto")), serial(g("Dt. Contábil")) if g("Dt. Contábil") else "", g("Tp"), g("Razão"), g("St"), txt(g("Movimento")),
                  g("OM Origem"), g("Setor Origem"), g("OM Destino"), g("Setor Destino"), txt(g("Documento")), q, ef, txt(g("Detalhe (SN, Lote ou Volume)")), txt(g("Emergência")), txt(g("Requisição")), txt(g("Observação")), g("Gerado Por")])
    publicar({"Saldos": S, "Histórico": H, "Evidências": E, "Mov": M})
    print(f"Saldos {len(S)-1} | Histórico {len(H)-1} | Evidências {len(E)-1} | Mov {len(M)-1}")
def cor(h): h = h.lstrip("#"); return {"red": int(h[0:2], 16) / 255, "green": int(h[2:4], 16) / 255, "blue": int(h[4:6], 16) / 255}
def publicar(dados):
    svc = ds._obter_servico_sheets(); sh = svc.spreadsheets()
    meta = sh.get(spreadsheetId=SID, fields="sheets(properties(sheetId,title),conditionalFormats)").execute()
    ncf = {s["properties"]["sheetId"]: len(s.get("conditionalFormats", [])) for s in meta["sheets"]}
    larg = {"Saldos": [130, 260, 70, 110, 90, 90, 90, 90, 100, 80, 95, 260, 95, 90, 80, 80, 95, 110, 120, 70],
            "Histórico": [130, 70, 85, 300, 150, 170, 150, 160, 380, 150],
            "Evidências": [130, 260, 70, 95, 95, 80, 420, 300, 70],
            "Mov": [130, 70, 220, 90, 90, 45, 50, 50, 105, 70, 70, 70, 70, 130, 70, 75, 160, 110, 100, 320, 100]}
    datas = {"Histórico": [2], "Mov": [3, 4]}
    req = []
    for nome, linhas in dados.items():
        sid = ABAS[nome]; nl, nc = len(linhas), len(linhas[0])
        req += [{"clearBasicFilter": {"sheetId": sid}},
                {"updateSheetProperties": {"properties": {"sheetId": sid, "title": NOME[nome], "gridProperties": {"rowCount": nl + 50, "columnCount": nc, "frozenRowCount": 1, "frozenColumnCount": 1 if nome != "Mov" else 2},
                                           "tabColorStyle": {"rgbColor": cor("#2E7D32")}}, "fields": "title,gridProperties(rowCount,columnCount,frozenRowCount,frozenColumnCount),tabColorStyle"}},
                {"updateCells": {"range": {"sheetId": sid}, "fields": "userEnteredValue,userEnteredFormat"}}]
        req += [{"deleteConditionalFormatRule": {"sheetId": sid, "index": 0}} for _ in range(ncf.get(sid, 0))]
    sh.batchUpdate(spreadsheetId=SID, body={"requests": req}).execute()
    for nome, linhas in dados.items():
        sh.values().update(spreadsheetId=SID, range=f"'{NOME[nome]}'!A1", valueInputOption="USER_ENTERED", body={"values": linhas}).execute()
    req = []
    for nome, linhas in dados.items():
        sid = ABAS[nome]; nl, nc = len(linhas), len(linhas[0])
        req += [{"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": nl}, "cell": {"userEnteredFormat": {"textFormat": {"fontFamily": "Arial", "fontSize": 10}, "verticalAlignment": "MIDDLE"}}, "fields": "userEnteredFormat(textFormat,verticalAlignment)"}},
                {"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1}, "cell": {"userEnteredFormat": {"backgroundColor": cor("#1F3864"), "textFormat": {"bold": True, "foregroundColor": cor("#FFFFFF"), "fontFamily": "Arial", "fontSize": 10}, "wrapStrategy": "WRAP", "verticalAlignment": "MIDDLE", "horizontalAlignment": "CENTER"}}, "fields": "userEnteredFormat"}},
                {"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "ROWS", "startIndex": 0, "endIndex": 1}, "properties": {"pixelSize": 48}, "fields": "pixelSize"}},
                {"setBasicFilter": {"filter": {"range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": nl, "startColumnIndex": 0, "endColumnIndex": nc}}}}]
        for c, w in enumerate(larg[nome][:nc]):
            req.append({"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": c, "endIndex": c + 1}, "properties": {"pixelSize": w}, "fields": "pixelSize"}})
        for c in datas.get(nome, []):
            req.append({"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": nl, "startColumnIndex": c, "endColumnIndex": c + 1}, "cell": {"userEnteredFormat": {"numberFormat": {"type": "DATE", "pattern": "dd/mm/yyyy"}}}, "fields": "userEnteredFormat.numberFormat"}})
    def cf(sid, c0, c1, formula, fundo, negrito=False, nl=10000):
        return {"addConditionalFormatRule": {"index": 0, "rule": {"ranges": [{"sheetId": sid, "startRowIndex": 1, "endRowIndex": nl, "startColumnIndex": c0, "endColumnIndex": c1}],
                "booleanRule": {"condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": formula}]}, "format": {"backgroundColor": cor(fundo), "textFormat": {"bold": negrito}}}}}}
    S, H, M = ABAS["Saldos"], ABAS["Histórico"], ABAS["Mov"]
    req += [cf(S, 0, 20, '=$K2="A explicar"', "#FDE2E1"), cf(S, 0, 20, '=$K2="Justificada"', "#FFF4CE"), cf(S, 9, 11, '=$K2="Fecha"', "#E2F0D9"),
            cf(S, 11, 12, '=TRUE', "#FFF9E6"), cf(ABAS["Evidências"], 7, 8, '=TRUE', "#FFF9E6"),
            cf(H, 0, 10, '=LEFT($D2;5)="Saldo"', "#D5E8F0", True), cf(H, 0, 10, '=LEFT($D2;5)="saída"', "#FCE4D6"),
            cf(H, 0, 10, '=ISNUMBER(SEARCH("OS externa";$D2))', "#E2F0D9"), cf(H, 0, 10, '=LEFT($D2;2)="OS"', "#EDE7F6"),
            cf(M, 0, 21, '=$P2<0', "#FCE4D6"), cf(M, 0, 21, '=$P2>0', "#E2F0D9"), cf(M, 0, 21, '=$H2<>"R"', "#EEEEEE")]
    # aba RMA: cabeçalho, congelar e datas dd/mm/aaaa
    req += [{"updateSheetProperties": {"properties": {"sheetId": RMA_ID, "gridProperties": {"frozenRowCount": 1}}, "fields": "gridProperties.frozenRowCount"}},
            {"repeatCell": {"range": {"sheetId": RMA_ID, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 16}, "cell": {"userEnteredFormat": {"backgroundColor": cor("#1F3864"), "textFormat": {"bold": True, "foregroundColor": cor("#FFFFFF"), "fontFamily": "Arial", "fontSize": 10}, "wrapStrategy": "WRAP", "verticalAlignment": "MIDDLE", "horizontalAlignment": "CENTER"}}, "fields": "userEnteredFormat"}}]
    for c in (7, 15):
        req.append({"repeatCell": {"range": {"sheetId": RMA_ID, "startRowIndex": 1, "endRowIndex": 1000, "startColumnIndex": c, "endColumnIndex": c + 1}, "cell": {"userEnteredFormat": {"numberFormat": {"type": "DATE", "pattern": "dd/mm/yyyy"}}}, "fields": "userEnteredFormat.numberFormat"}})
    sh.batchUpdate(spreadsheetId=SID, body={"requests": req}).execute()
if __name__ == "__main__":
    main(*sys.argv[1:5])
