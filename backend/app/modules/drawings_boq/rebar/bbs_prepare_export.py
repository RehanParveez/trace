from __future__ import annotations
import io
from app.modules.drawings_boq.rebar import bbs_report as BR

DASH = "—"
ROW_KEYS = ("sr", "description", "dia", "spacing_in", "members", "each", "total", "cut_ft", "total_ft", "unit_kg_ft", "kg")
EXTRA = (("Shape", "shape", 14), ("Parts (ft)", "parts", 22), ("Member", "member", 12), ("Source drawing", "source", 38), ("Basis", "basis", 10))
WIDTHS = (6, 22, 7, 8, 9, 8, 10, 9, 14, 10, 11)

def _cell(v):
  if isinstance(v, list):
    return " + ".join(f"{x:g}" for x in v)
  return v

def _fmt(v) -> str:
  if v is None:
    return DASH
  if isinstance(v, list):
    return " + ".join(f"{x:g}" for x in v)
  if isinstance(v, float):
    return f"{v:,.2f}" if abs(v) >= 1 or v == 0 else f"{v:.3f}"
  return str(v)

def _head(prepared: dict, generated: str) -> list:
  p = prepared.get("project") or {}
  return [f"Bar bending schedule prepared by Trace: {p.get('name') or 'project'}", f"Layout {prepared['layout']} · {generated}",
    "Source drawings: " + (", ".join(prepared["sources"][:6]) + (f" and {len(prepared['sources']) - 6} more" if len(prepared["sources"]) > 6 else "") if prepared["sources"] else "none read")]

def build_xlsx(prepared: dict, comparison: dict | None, generated: str) -> bytes:
  from openpyxl import Workbook
  from openpyxl.styles import Alignment, Font, PatternFill
  from openpyxl.utils import get_column_letter
  head_fill, head_font, bold = PatternFill("solid", fgColor="1F3A5F"), Font(bold=True, color="FFFFFF"), Font(bold=True)
  wrap = Alignment(wrap_text=True, vertical="top")
  
  kg_fmt = "#,##0.00"
  wb = Workbook()
  ws = wb.active
  ws.title = "Summary"
  lines = _head(prepared, generated)
  ws.append([lines[0]])
  ws["A1"].font = Font(bold=True, size=13)
  for t in lines[1:]:
    ws.append([t])
  ws.append([])
  ws.append(["Sheet", "Rows", "kg", "State"])
  
  for c in ws[ws.max_row]:
    c.font, c.fill = head_font, head_fill
  titles = BR.sheet_titles([s["title"] for s in prepared["sheets"]])
  for s in prepared["sheets"]:
    ws.append([s["title"], s["totals"]["rows"], s["totals"]["kg"], s["state"]])
    ws.cell(ws.max_row, 3).number_format = kg_fmt
  ws.append(["All sheets", prepared["totals"]["rows"], prepared["totals"]["kg"]])
  ws.cell(ws.max_row, 3).number_format = kg_fmt
  for c in ws[ws.max_row]:
    c.font = bold
  ws.append([])
  ws.append(["Bar size", "kg"])
  
  for c in ws[ws.max_row]:
    c.font, c.fill = head_font, head_fill
  for dia, kg in prepared["totals"]["by_dia_kg"].items():
    ws.append([f"#{dia}", kg])
    ws.cell(ws.max_row, 2).number_format = kg_fmt
  ws.append([])
  
  ws.append(["Inputs that rest on an answer or an assumption", f"{len(prepared['answers'])} (listed on the Inputs tab)"])
  ws.append(["Members with no row (bars cannot be worked out)", len(prepared["unverifiable"])])
  
  for n in prepared["notes"]:
    ws.append([n])
  for i, w in enumerate((46, 14, 14, 24), start=1):
    ws.column_dimensions[get_column_letter(i)].width = w
  for s, title in zip(prepared["sheets"], titles):
    sh = wb.create_sheet(title)
    sh.append([c["title"] for c in prepared["columns"]] + [e[0] for e in EXTRA])
    for cell in sh[1]:
      cell.font, cell.fill, cell.alignment = head_font, head_fill, Alignment(wrap_text=True, vertical="center")
    for i, w in enumerate(list(WIDTHS) + [e[2] for e in EXTRA], start=1):
      sh.column_dimensions[get_column_letter(i)].width = w
    last_member = None
    for r in s["rows"]:
      sh.append([_cell(r.get(k)) for k in ROW_KEYS] + [_cell(r.get(k)) for _t, k, _w in EXTRA])
      sh.cell(sh.max_row, len(ROW_KEYS)).number_format = kg_fmt
      sh.cell(sh.max_row, len(ROW_KEYS) + 4).alignment = wrap
      last_member = r["member"]
    if s["rows"]:
      first, last = 2, sh.max_row
      kg_col = get_column_letter(len(ROW_KEYS))
      sh.cell(last + 2, 2, "Total of the sheet (kg)").font = bold
      sh.cell(last + 2, len(ROW_KEYS), f"=SUM({kg_col}{first}:{kg_col}{last})").number_format = kg_fmt
      row = last + 3
      for dia, v in s["totals"]["by_dia"].items():
        sh.cell(row, 2, f"Dia #{dia} (kg)")
        sh.cell(row, len(ROW_KEYS), v["kg"]).number_format = kg_fmt
        row += 1
      if s["totals"]["rows_with_members_unknown"]:
        sh.cell(row, 2, f"{s['totals']['rows_with_members_unknown']} row(s) show one member: the member count is not known")
        row += 1
        
    for u in s["unverifiable"]:
      sh.append([])
      sh.append([None, f"No row for {u['member']}: {u['reason']}"])
      sh.cell(sh.max_row, 2).alignment = wrap
    sh.freeze_panes = "A2"
  ins = wb.create_sheet("Inputs")
  ins.append(["Member", "Class", "Floor", "Input", "Value", "Basis", "Source"])
  
  for c in ins[1]:
    c.font, c.fill = head_font, head_fill
  for a in prepared["answers"]:
    ins.append([a["member"], a["class"], a["floor"], a["input"], str(a["value"]), a["basis"], a["source"]])
  ins.append([])
  ins.append(["Method conventions used (stock length, rounding, hooks, zones)"])
  ins.cell(ins.max_row, 1).font = bold
  
  for a in prepared["conventions"]:
    ins.append([None, None, None, a["input"], str(a["value"]), a["basis"], a["source"]])
  for i, w in enumerate((14, 10, 10, 22, 14, 10, 60), start=1):
    ins.column_dimensions[get_column_letter(i)].width = w
  if comparison is not None:
    cs = wb.create_sheet("Comparison")
    cs.append(["Supplied sheet", "Page", "Member", "Sr", "Description", "Supplied each", "Supplied cut", "Supplied kg", "Trace each", "Trace cut", "Trace kg", "Trace − supplied kg", "Class", "Checks", "Rule"])
    for c in cs[1]:
      c.font, c.fill = head_font, head_fill
    for r in comparison["rows"]:
      cs.append([r["sheet_name"], r["page"], r["member"], r["sr"], r["description"], r["bbs"]["each"], r["bbs"]["cut_ft"], r["bbs"]["kg"], r["trace"]["each"], r["trace"]["cut_ft"], r["trace"]["kg"],
        r["diff_kg"], r["class"], ", ".join(r["codes"]), r["rule"]])
      for col in (8, 11, 12):
        cs.cell(cs.max_row, col).number_format = kg_fmt
    t = comparison["totals"]
    
    cs.append([])
    cs.append(["Supplied schedule total (kg)", None, None, None, None, None, None, t["supplied_kg"]])
    cs.append(["Supplied kg on the rows compared", None, None, None, None, None, None, t["supplied_kg_compared"], None, None, t["trace_kg_for_those_rows"]])
    cs.append(["Trace prepared schedule total (kg)", None, None, None, None, None, None, t["trace_prepared_kg"]])
    for col, w in enumerate((26, 6, 16, 5, 24, 11, 11, 12, 10, 10, 12, 14, 12, 28, 50), start=1):
      cs.column_dimensions[get_column_letter(col)].width = w
    cs.freeze_panes = "A2"
  out = io.BytesIO()
  wb.save(out)
  return out.getvalue()

def build_pdf(prepared: dict, comparison: dict | None, generated: str) -> bytes:
  from reportlab.lib import colors
  from reportlab.lib.pagesizes import A4, landscape
  from reportlab.lib.styles import getSampleStyleSheet
  from reportlab.lib.units import mm
  from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
  styles = getSampleStyleSheet()
  small = styles["BodyText"].clone("small")
  small.fontSize, small.leading = 7.5, 9
  buf = io.BytesIO()
  doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm, topMargin=10 * mm, bottomMargin=12 * mm, title="Bar bending schedule")
  navy = colors.HexColor("#1F3A5F")
  
  def table(data, widths, head=1):
    t = Table(data, colWidths=widths, repeatRows=head)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, head - 1), navy), ("TEXTCOLOR", (0, 0), (-1, head - 1), colors.white), ("FONTSIZE", (0, 0), (-1, -1), 7.5),
      ("GRID", (0, 0), (-1, -1), 0.25, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (2, 1), (-1, -1), "RIGHT")]))
    return t
  
  lines = _head(prepared, generated)
  story = [Paragraph(lines[0], styles["Title"]), Paragraph(lines[1], styles["Normal"]), Paragraph(lines[2], styles["Normal"]), Spacer(1, 4 * mm)]
  story.append(table([["Sheet", "Rows", "kg", "State"]] + [[s["title"], s["totals"]["rows"], _fmt(s["totals"]["kg"]), s["state"]] for s in prepared["sheets"]] +
    [["All sheets", prepared["totals"]["rows"], _fmt(prepared["totals"]["kg"]), ""]], [90 * mm, 20 * mm, 30 * mm, 50 * mm]))
  story += [Spacer(1, 3 * mm)] + [Paragraph(n, small) for n in prepared["notes"]]
  if prepared["answers"]:
    story += [Spacer(1, 3 * mm), Paragraph(f"{len(prepared['answers'])} input(s) rest on an answer or an assumption; they are listed after the sheets.", small)]
  widths = [9 * mm, 34 * mm, 10 * mm, 11 * mm, 13 * mm, 11 * mm, 14 * mm, 14 * mm, 20 * mm, 14 * mm, 18 * mm, 18 * mm, 40 * mm, 31 * mm]
  head = [c["title"] for c in prepared["columns"]] + ["Member", "Shape"]
  for s in prepared["sheets"]:
    story.append(PageBreak())
    story.append(Paragraph(s["title"], styles["Heading2"]))
    
    if s["rows"]:
      data = [head] + [[_fmt(r.get(k)) for k in ROW_KEYS] + [r["member"], r["shape"]] for r in s["rows"]]
      data.append(["", "Total of the sheet", "", "", "", "", "", "", "", "", _fmt(s["totals"]["kg"]), "", ""])
      story.append(table(data, widths[:len(head)]))
      story.append(Paragraph("Per bar size: " + "; ".join(f"#{d} {_fmt(v['kg'])} kg" for d, v in s["totals"]["by_dia"].items()), small))
    for u in s["unverifiable"]:
      story.append(Paragraph(f"No row for {u['member']}: {u['reason']}", small))
  if prepared["answers"]:
    story.append(PageBreak())
    story.append(Paragraph("Inputs that rest on an answer or an assumption", styles["Heading2"]))
    story.append(table([["Member", "Floor", "Input", "Value", "Basis", "Source"]] + [[a["member"], a["floor"] or DASH, a["input"], str(a["value"]), a["basis"], a["source"]] for a in prepared["answers"]],
      [28 * mm, 20 * mm, 36 * mm, 24 * mm, 22 * mm, 140 * mm]))
    
  if comparison is not None:
    story.append(PageBreak())
    story.append(Paragraph("Comparison with the supplied schedule", styles["Heading2"]))
    story.append(table([["Supplied sheet", "Rows compared", "Supplied kg", "Trace kg", "Difference kg", "Rows with a finding"]] +
      [[s["name"], s["rows_compared"], _fmt(s["bbs_kg"]), _fmt(s["trace_kg"]), _fmt(s["diff_kg"]), s["differences"]] for s in comparison["sheets"]], [80 * mm, 28 * mm, 30 * mm, 30 * mm, 30 * mm, 36 * mm]))
    story.append(Paragraph(comparison["note"], small))
  doc.build(story)
  return buf.getvalue()
