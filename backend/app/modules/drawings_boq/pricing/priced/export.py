from __future__ import annotations
import io
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from app.modules.drawings_boq.pricing.billing import group as G
from app.modules.drawings_boq.pricing.priced import price as PR

HEAD = Font(bold=True, color="FFFFFF")
FILL = PatternFill("solid", fgColor="2F4F6F")
HEADERS = ("Item", "Description", "Unit", "Quantity", "Rate", "Amount", "Spec", "Floor", "Not priced because")
MARK_HEADERS = ("State", "Measured amount", "Assumed amount", "Range low %", "Range high %", "Open review rows")
MARK_KEYS = ("label", "measured_amount", "assumed_amount", "low_pct", "high_pct", "open_rows")

def _f(x):
  return None if x is None else float(x)

def _header(ws, headers):
  ws.append(list(headers))
  for c in ws[1]:
    c.font, c.fill, c.alignment = HEAD, FILL, Alignment(horizontal="center", vertical="center", wrap_text=True)
  ws.freeze_panes = "A2"

def build_xlsx(project: str, profile_id: str, lines: list, totals: dict, materials=None, ratios: list | None = None, generated: str = "", marks: list | None = None) -> bytes:
  wb = Workbook()
  ws = wb.active
  ws.title = "BOQ"
  _header(ws, HEADERS + (MARK_HEADERS if marks else ()))
  
  for n, l in enumerate(lines):
    qty = G.convert(l.qty, l.unit, l.rate_unit) if l.rate_unit and l.amount is not None else l.qty
    unit = l.rate_unit if l.amount is not None else l.unit
    per_unit = None if l.rate is None or not l.basis else l.rate / l.basis
    extra = [marks[n][k] for k in MARK_KEYS] if marks else []
    ws.append([l.code, l.description, unit, _f(qty), _f(per_unit), _f(l.amount), " ".join(str(v) for v in l.spec[:2]) if l.spec else None, l.floor, l.unpriced_why, *extra])
  last = ws.max_row
  ws.append(["TOTAL", None, None, None, None, f"=SUM(F2:F{last})" if last >= 2 else 0])
  
  for c in ws[ws.max_row]:
    c.font = Font(bold=True)
  for col, w in zip("ABCDEFGHIJKLMNO", (14, 46, 8, 14, 12, 16, 22, 12, 52, 26, 16, 16, 12, 12, 12)):
    ws.column_dimensions[col].width = w
  for row in ws.iter_rows(min_row=2, min_col=4, max_col=6):
    for c in row:
      c.number_format = "#,##0.00"
      
  s = wb.create_sheet("Summary")
  s.append(["Project", project]); s.append(["Billing profile", profile_id]); s.append(["Generated", generated]); s.append([])
  s.append(["Priced lines", totals["priced"]]); s.append(["Lines not priced", totals["unpriced"]])
  s.append(["Measured", _f(totals["measured"])]); s.append(["Assumed", _f(totals["assumed"])]); s.append(["Total (priced lines only)", _f(totals["grand"])])
  
  if totals.get("range"):
    r = totals["range"]
    s.append(["Range of the lines that have one", f"{_f(r['low']):,.2f} to {_f(r['high']):,.2f} against {_f(r['of_amount']):,.2f}"])
  s.append([]); s.append(["Section", "Amount"])
  for k, v in totals["by_section"].items():
    s.append([k, _f(v)])
  s.append([]); s.append(["Floor", "Amount"])
  for k, v in totals["by_floor"].items():
    s.append([k, _f(v)])
  s.column_dimensions["A"].width = 34; s.column_dimensions["B"].width = 40
  m = wb.create_sheet("Materials")
  _header(m, ("Item", "Material", "Quantity", "How it was worked out"))
  
  if materials is not None:
    for code, mat, qty, how in materials.rows:
      m.append([code, mat, _f(qty), how])
    m.append([])
    m.append(["Total by material"])
    for mat, qty in sorted(materials.totals.items()):
      m.append([None, mat, _f(qty)])
    for code, why in materials.missing:
      m.append([code, "not counted", None, why])
      
  for col, w in zip("ABCD", (14, 16, 14, 90)):
    m.column_dimensions[col].width = w
  r = wb.create_sheet("Ratios")
  _header(r, ("Ratio", "Value", "Unit", "Inputs", "Not made because"))
  for x in ratios or []:
    r.append([x["ratio"], _f(x["value"]), x["unit"], ", ".join(f"{k} = {v}" for k, v in x["inputs"].items()), x["why"]])
  for col, w in zip("ABCDE", (14, 14, 16, 48, 40)):
    r.column_dimensions[col].width = w
  buf = io.BytesIO()
  wb.save(buf)
  return buf.getvalue()
