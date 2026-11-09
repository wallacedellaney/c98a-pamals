"""Aba "Reparáveis" a partir do Relatório de estoque calculado do SILOMS (pedido do fiscal, 09/11/2026).
Uso: python3 montar_aba_reparaveis_estoque.py <estoque_calculado.xlsx> <relatorio-siloms-stock.xlsx> <saida.xlsx>
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
def main(calc, hoje, saida):
    df = pd.read_excel(calc, sheet_name="levantamentoOficio")
    df.columns = ["OM", "SETOR", "PN", "CFF", "MAT", "PROJ", "ATUAL", "SAI", "ENT", "SALDO0"]
    f = df[(df.OM == "304 - PAMALS") & (df.SETOR == "U0 - TSAU")].copy(); f["k"] = f.PN.map(k)
    st = pd.read_excel(hoje, header=3); st = st[(st.Unidade == "PAMA LS") & (st.Setor == "TSAU")].copy(); st["k"] = st.PN.map(k)
    b = pd.read_excel(BASE); b["k"] = b.pn.map(k)
    svc = ds._obter_servico_sheets()
    raw = svc.spreadsheets().values().get(spreadsheetId=DEV, range="DEVOLUÇÃO!A3:W400", valueRenderOption="UNFORMATTED_VALUE").execute().get("values", [])
    dev = [r + [""] * (23 - len(r)) for r in raw]
    rep = set(b.k) | {k(r[1]) for r in dev if str(r[4]).strip().upper() in ("R", "T")}
    mov = f[((f.SAI > 0) | (f.ENT > 0)) & f.k.isin(rep)].sort_values("PN")
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
                      "Estoque no relatório calculado", "Conferência (inicial+entradas−saídas)", "Estoque hoje (SILOMS)", "Diferença hoje x calculado", "OS de reparo", "Lançamentos na planilha Devoluções"], B, cinza)
    blocos = []
    for _, r in mov.iterrows():
        kk = r.k; os_ = b[b.k == kk].sort_values("data_inicio"); dv = [x for x in dev if k(x[1]) == kk]
        nome = next((s(x) for x in b[b.k == kk].nomenclatura if s(x)), "") or next((s(x[2]) for x in dv if x[2]), "") or next((s(x) for x in st[st.k == kk].Nomenclatura), "")
        hj = float(st[st.k == kk].Quantidade.sum()); n = ws.max_row + 1
        lin([s(r.PN), nome, s(r.CFF), s(r.MAT), int(r.SALDO0), int(r.ENT), int(r.SAI), int(r.ATUAL), f"=E{n}+F{n}-G{n}", hj, f"=J{n}-H{n}", len(os_), len(dv)])
        ev = []
        for _, o in os_.iterrows():
            ev.append((o.data_inicio, [s(o.data_inicio), "OS de reparo aberta", f"OS {s(o.os)}", f"SN {s(o.sn)}", s(o.unidade_solicitante), " / ".join(x for x in [s(o.condicao), s(o.situacao)] if x), f"Onde está: {s(o.onde_se_encontra)}" if s(o.onde_se_encontra) else ""]))
            if s(o.data_entrega): ev.append((o.data_entrega, [s(o.data_entrega), "Reparável entregue pela VEE ONE", f"OS {s(o.os)}", f"SN {s(o.sn)}", s(o.unidade_solicitante), "", f"Recibo {s(o.recibo)}" if s(o.recibo) else ""]))
        for x in dv:
            de = data(x[10]); ev.append((de, [de.strftime("%d/%m/%Y") if de else s(x[10]), f"Enviado à base (Devoluções nº {s(x[0])})", f"Pedido/EMG {s(x[7])}", f"Qtd {s(x[6])}", f"{s(x[12])} ANV {s(x[11])}", s(x[8]), ""]))
            if x[19] or x[16] or x[17]:
                dd = data(x[19]); ev.append((dd or de, [dd.strftime("%d/%m/%Y") if dd else (s(x[19]) or "(sem data)"), "Devolução VEE ONE", f"PN devolvido {s(x[15])}" if s(x[15]) else "", s(x[16]), "", s(x[22]), f"RC {s(x[17])}" if s(x[17]) else ""]))
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
    wb.save(saida); print(f"{len(blocos)} reparáveis com movimentação -> {saida}")
if __name__ == "__main__":
    main(*sys.argv[1:4])
