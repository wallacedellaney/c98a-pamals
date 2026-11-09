"""Aba "Reparáveis" a partir do Relatório de estoque calculado do SILOMS (pedido do fiscal, 09/11/2026).
Uso: python3 montar_aba_reparaveis_estoque.py <estoque_calculado.xlsx> <relatorio-siloms-stock.xlsx> <saida.xlsx> [entradas.csv|.xls] [saidas.csv|.xls]
Movimentos: relatório do SILOMS "Movimento entrada TSAU" (colunas Dt. Movto, Tp, ..., Razão, St, PN, CodEmp...).
St é o status do movimento (R realizado, A aberto, C cancelado, E estornado); só R entra na conta. Razão I = retorno de OS externa (LEP = OS externa).
Saídas: relatório "movimentosEstoque" (todos os projetos, Ctrl EQP); o script filtra Prj U8 e saídas com origem PAMALS/TSAU. Em 09/11 ele começava em 10/02/2026.
Ver 00_Instrucoes/estoque_reparaveis_siloms.md."""
import sys, re, datetime as dt
from pathlib import Path
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from shared import drive_sync as ds
DEV = "1czUWXVjQt7fPz7GJgdPp3rsxPn_5Uck44voBsJIiRWI"
BASE = Path(__file__).resolve().parents[2] / "02_Dados_Tratados" / "base_reparaveis_tratada.xlsx"
k = lambda v: re.sub(r"[^A-Z0-9]", "", str(v or "").upper())
def s(v):
    if v is None or (not isinstance(v, str) and pd.isna(v)): return ""
    if isinstance(v, float) and v.is_integer(): return str(int(v))
    if isinstance(v, (pd.Timestamp, dt.datetime)): return v.strftime("%d/%m/%Y")
    return str(v).strip()
def data(v):  # células da planilha Devoluções: serial (data real) ou texto dd/mm/aa(aa); m/d só quando o 2º campo > 12
    if isinstance(v, (int, float)) and v: return dt.datetime(1899, 12, 30) + dt.timedelta(days=v)
    t = str(v or "").strip(); p = t.split("/")
    if len(p) == 3 and p[0].isdigit() and p[1].isdigit():
        d, m, a = int(p[0]), int(p[1]), int(p[2]) if p[2].isdigit() else 0
        if m > 12: d, m = m, d
        try: return dt.datetime(a + 2000 if a < 100 else a, m, d)
        except ValueError: return None
    return None
def ler_mov(p):
    if not p: return None
    if p.lower().endswith(".xls"):
        import xlrd
        b = xlrd.open_workbook(p); sh = b.sheet_by_index(0)
        rows = [[(xlrd.xldate.xldate_as_datetime(c.value, b.datemode).strftime("%d/%m/%Y") if c.ctype == xlrd.XL_CELL_DATE else c.value) for c in sh.row(r)] for r in range(sh.nrows)]
        m = pd.DataFrame(rows[1:], columns=rows[0]).astype(str)
    else:
        m = pd.read_csv(p, dtype=str).fillna("")
    m["k"] = m.PN.map(k); m["c"] = m.CodEmp.str.upper().str.strip()
    m["dt"] = pd.to_datetime(m["Dt. Movto"], format="%d/%m/%Y", errors="coerce")
    m["q"] = m["Qt. Material"].str.replace(".", "", regex=False).str.replace(",", ".").astype(float)
    return m
def main(calc, hoje, saida, movs=None, saidas=None):
    df = pd.read_excel(calc, sheet_name="levantamentoOficio")
    df.columns = ["OM", "SETOR", "PN", "CFF", "MAT", "PROJ", "ATUAL", "SAI", "ENT", "SALDO0"]
    f = df[(df.OM == "304 - PAMALS") & (df.SETOR == "U0 - TSAU")].copy(); f["k"] = f.PN.map(k)
    st = pd.read_excel(hoje, header=3); st = st[(st.Unidade == "PAMA LS") & (st.Setor == "TSAU")].copy(); st["k"] = st.PN.map(k)
    b = pd.read_excel(BASE); b["k"] = b.pn.map(k)
    svc = ds._obter_servico_sheets()
    raw = svc.spreadsheets().values().get(spreadsheetId=DEV, range="DEVOLUÇÃO!A3:W400", valueRenderOption="UNFORMATTED_VALUE").execute().get("values", [])
    dev = [r + [""] * (23 - len(r)) for r in raw]
    rep = set(b.k) | {k(r[1]) for r in dev if str(r[4]).strip().upper() in ("R", "T")}
    m = ler_mov(movs)
    m2 = ler_mov(saidas)
    if m2 is not None:
        m = m2 if m is None else pd.concat([m, m2], ignore_index=True)
    if m is not None:
        m = m[m.Prj.str.strip() == "U8"].drop_duplicates(subset=["Movimento", "Tp", "PN"])
        mR = m[(m.St == "R") & (m.Tp == "E") & (m["Setor Destino"] == "TSAU")]
        mS = m[(m.St == "R") & (m.Tp == "S") & (m["Setor Origem"] == "TSAU") & (m["OM Origem"] == "PAMALS")]
        rep |= set(mR[mR["Razão"] == "I"].k) | set(mS.k)
        com_mov = set(mR.k) | set(mS.k)
    else:
        mR, mS, com_mov = None, None, set()
    base = f[f.k.isin(rep)][["k", "PN", "CFF", "MAT", "SALDO0", "ENT", "SAI", "ATUAL"]]
    extra = [] if mR is None else [dict(k=kk, PN=g.PN.iloc[0], CFF=g.CodEmp.iloc[0], MAT="", SALDO0=0, ENT=0, SAI=0, ATUAL=0) for kk, g in mR[mR.k.isin(rep - set(f.k))].groupby("k")]
    tudo = pd.concat([base, pd.DataFrame(extra)], ignore_index=True) if extra else base
    mov = tudo[(tudo.SAI > 0) | (tudo.ENT > 0) | tudo.k.isin(com_mov)].sort_values("PN")
    wb = Workbook(); ws = wb.active; ws.title = "Reparáveis"
    B = Font(name="Arial", bold=True); A = Font(name="Arial"); cinza = PatternFill("solid", fgColor="D5E8F0")
    def lin(vals, fonte=A, fill=None):
        ws.append(vals); r = ws.max_row
        for c in ws[r]:
            c.font = fonte
            if fill: c.fill = fill
        return r
    lin(["REPARÁVEIS – PAMALS / TSAU (projeto U8) – itens com movimentação desde 10/02/2025"], B)
    lin(["Fontes: SILOMS Relatório de estoque calculado (levantamentoOficio); estoque do dia (relatorio-siloms-stock); controle de reparáveis (OS); planilha Devoluções (CAT R/T)."])
    lin([]); h = lin(["PN", "Nomenclatura", "CFF", "Cód. material", "Tinha em 10/02/2025", "Entradas desde 10/02/2025", "Saídas desde 10/02/2025",
                      "Estoque no relatório calculado", "Conferência (inicial+entradas−saídas)", "Estoque hoje (SILOMS)", "Diferença hoje x calculado", "OS de reparo", "Lançamentos na planilha Devoluções",
                      "Entradas no TSAU (movimentos, St=R)", "…de OS externa (Razão I, LEP)", "…de compra (C)", "…outras", "Na base do calculado?", "Saídas do TSAU (movimentos, St=R, desde 10/02/2026)"], B, cinza)
    blocos = []
    for _, r in mov.iterrows():
        kk = r.k; os_ = b[b.k == kk].sort_values("data_inicio"); dv = [x for x in dev if k(x[1]) == kk]
        nome = next((s(x) for x in b[b.k == kk].nomenclatura if s(x)), "") or next((s(x[2]) for x in dv if x[2]), "") or next((s(x) for x in st[st.k == kk].Nomenclatura), "") or (next((s(x) for x in m[m.k == kk].Nomenclatura), "") if m is not None else "")
        hj = float(st[st.k == kk].Quantidade.sum()); n = ws.max_row + 1
        mv = mR[mR.k == kk] if mR is not None else pd.DataFrame(columns=["q", "Razão"])
        qi = float(mv[mv["Razão"] == "I"].q.sum()); qc = float(mv[mv["Razão"] == "C"].q.sum()); qt = float(mv.q.sum())
        nab = "Sim" if kk in set(f.k) else "Não (sem saldo em 10/02/2025)"
        qs = float(mS[mS.k == kk].q.sum()) if mS is not None else 0.0
        lin([s(r.PN), nome, s(r.CFF), s(r.MAT), int(r.SALDO0), int(r.ENT), int(r.SAI), int(r.ATUAL), f"=E{n}+F{n}-G{n}", hj, f"=J{n}-H{n}", len(os_), len(dv), qt, qi, qc, qt - qi - qc, nab, qs])
        ev = []
        for _, o in os_.iterrows():
            ev.append((o.data_inicio, [s(o.data_inicio), "OS de reparo aberta", f"OS {s(o.os)}", f"SN {s(o.sn)}", s(o.unidade_solicitante), " / ".join(x for x in [s(o.condicao), s(o.situacao)] if x), f"Onde está: {s(o.onde_se_encontra)}" if s(o.onde_se_encontra) else ""]))
            if s(o.data_entrega): ev.append((o.data_entrega, [s(o.data_entrega), "Reparável entregue pela VEE ONE", f"OS {s(o.os)}", f"SN {s(o.sn)}", s(o.unidade_solicitante), "", f"Recibo {s(o.recibo)}" if s(o.recibo) else ""]))
        for x in dv:
            de = data(x[10]); ev.append((de, [de.strftime("%d/%m/%Y") if de else s(x[10]), f"Enviado à base (Devoluções nº {s(x[0])})", f"Pedido/EMG {s(x[7])}", f"Qtd {s(x[6])}", f"{s(x[12])} ANV {s(x[11])}", s(x[8]), ""]))
            if x[19] or x[16] or x[17]:
                dd = data(x[19]); ev.append((dd or de, [dd.strftime("%d/%m/%Y") if dd else (s(x[19]) or "(sem data)"), "Devolução VEE ONE", f"PN devolvido {s(x[15])}" if s(x[15]) else "", s(x[16]), "", s(x[22]), f"RC {s(x[17])}" if s(x[17]) else ""]))
        if mR is not None:
            for _, x in m[(m.k == kk)].iterrows():
                stt = {"R": "", "A": " (aberto)", "C": " (cancelado)", "E": " (estornado)"}.get(x.St, f" (St {x.St})")
                if x.St != "R": continue
                if x.Tp == "E" and x["Setor Destino"] == "TSAU":
                    evt = "SILOMS: entrada no TSAU – retorno de OS externa (LEP)" if x["Razão"] == "I" else f"SILOMS: entrada no TSAU, razão {x['Razão']}"
                    lug = f"De {x['OM Origem']}/{x['Setor Origem']}"
                elif x.Tp == "S" and x["Setor Origem"] == "TSAU" and x["OM Origem"] == "PAMALS":
                    evt = f"SILOMS: saída do TSAU, razão {x['Razão']}"; lug = f"Para {x['OM Destino']}/{x['Setor Destino']}"
                else:
                    continue
                ref = " ".join(t for t in [f"EMG {x['Emergência']}" if x["Emergência"].strip() else "", f"Req {x['Requisição']}" if x["Requisição"].strip() else ""] if t)
                ev.append((x["dt"], [x["Dt. Movto"], evt, f"Doc {x.Documento}".strip() if x.Documento.strip() else f"Mov {x.Movimento}",
                                  f"Qtd {x['Qt. Material']} {x['Detalhe (SN, Lote ou Volume)']}".strip(), lug, (x["Observação"] or "")[:120], ref]))
        ev.sort(key=lambda e: e[0] if isinstance(e[0], (dt.datetime, pd.Timestamp)) and not pd.isna(e[0]) else dt.datetime(2100, 1, 1))
        blocos.append((r, nome, hj, [e[1] for e in ev]))
    lin([]); lin([]); lin(["HISTÓRICO POR ITEM (do mais antigo para o mais recente)"], B)
    for r, nome, hj, ev in blocos:
        lin([]); lin([s(r.PN), nome, f"CFF {s(r.CFF)}", "Tinha em 10/02/2025:", int(r.SALDO0), "Hoje (SILOMS):", hj], B, cinza)
        lin(["Data", "Evento", "Documento", "SN / Qtd", "Base / ANV", "Situação / Status", "Observação"], B)
        for e in ev: lin(e)
        if not ev: lin(["", "Sem OS nem devolução registradas; só movimento no SILOMS"])
        lin(["Desde 10/02/2025", "Movimento no SILOMS (TSAU)", f"Entradas: {int(r.ENT)}", f"Saídas: {int(r.SAI)}", f"Calculado: {int(r.ATUAL)}"])
    for col, w in zip("ABCDEFGHIJKLM", [16, 38, 22, 22, 18, 30, 26, 14, 14, 12, 12, 10, 12]): ws.column_dimensions[col].width = w
    if m is not None:
        w2 = wb.create_sheet("Movimentos reparáveis")
        cols = [c for c in m.columns if c not in ("k", "c", "dt", "q")]
        w2.append(cols)
        for c in w2[1]: c.font = B; c.fill = cinza
        for _, x in m[m.k.isin(set(mov.k))].sort_values(["PN", "dt"]).iterrows(): w2.append([x[c] for c in cols])
    wb.save(saida); print(f"{len(blocos)} reparáveis com movimentação -> {saida}")
if __name__ == "__main__":
    main(*sys.argv[1:6])
