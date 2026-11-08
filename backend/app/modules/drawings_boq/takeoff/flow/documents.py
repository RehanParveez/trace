from __future__ import annotations
from app.modules.drawings_boq.takeoff.flow import marks as MK
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Table, TableStyle
from reportlab.lib.units import mm
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import landscape, A4

LIMITS = MK.LIMITS
HEAD = colors.HexColor("#1e293b")
GRID = colors.HexColor("#cbd5e1")
WARN = colors.HexColor("#b45309")

def money(v) -> str:
  return "-" if v is None else f"{float(v):,.2f}"

def qty(v) -> str:
  return "-" if v is None else f"{float(v):,.3f}"

def span(low, high) -> str:
  return "-" if low is None or high is None else f"{money(low)} to {money(high)}"

def pct_span(row: dict) -> str:
  lo, hi = row.get("low_pct"), row.get("high_pct")
  return "-" if lo is None or hi is None else f"{lo:+.1f}% / {hi:+.1f}%"

def styles() -> dict:
  base = getSampleStyleSheet()
  return {"h1": ParagraphStyle("h1", parent=base["Heading1"], fontSize=16), "h2": ParagraphStyle("h2", parent=base["Heading2"], fontSize=12), "body": ParagraphStyle("body", parent=base["Normal"], fontSize=9),
    "cell": ParagraphStyle("cell", parent=base["Normal"], fontSize=7, leading=8.5), "warn": ParagraphStyle("warn", parent=base["Normal"], fontSize=9, textColor=WARN), "small": ParagraphStyle("small", parent=base["Normal"], fontSize=7.5, textColor=colors.grey)}

def table(rows: list, widths: list, right: tuple = (), font: float = 7.5) -> Table:
  t = Table(rows, colWidths=widths, repeatRows=1)
  style = [("BACKGROUND", (0, 0), (-1, 0), HEAD), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTSIZE", (0, 0), (-1, -1), font), ("GRID", (0, 0), (-1, -1), 0.25, GRID), ("VALIGN", (0, 0), (-1, -1), "TOP")]
  style += [("ALIGN", (c, 0), (c, -1), "RIGHT") for c in right]
  t.setStyle(TableStyle(style))
  return t

def build(story: list, size, margin: float = 14 * mm) -> bytes:
  buf = BytesIO()
  SimpleDocTemplate(buf, pagesize=size, topMargin=margin, bottomMargin=margin, leftMargin=margin, rightMargin=margin).build(story)
  return buf.getvalue()

def head_block(s: dict, title: str, meta: list, warnings: list) -> list:
  out = [Paragraph(title, s["h1"])] + [Paragraph(line, s["body"]) for line in meta]
  return out + [Paragraph(w, s["warn"]) for w in warnings] + [Spacer(1, 6)]

def totals_rows(totals: dict) -> list:
  rows = [["Total (priced lines)", money(totals.get("grand"))], ["Measured", money(totals.get("measured"))], ["Assumed", money(totals.get("assumed"))]]
  rg = totals.get("range")
  if rg:
    rows.append(["Range of the lines that have one", f"{span(rg['low'], rg['high'])} against {money(rg['of_amount'])}"])
  rows.append(["Lines priced / not priced", f"{totals.get('priced', 0)} / {totals.get('unpriced', 0)}"])
  return rows

def priced_pdf(title: str, meta: list, warnings: list, lines: list, totals: dict, footer: str) -> bytes:
  s = styles()
  story = head_block(s, title, meta, warnings)
  with_conf = any(ln.get("confidence") for ln in lines)
  rows = [["Item", "Description", "Floor", "Unit", "Qty", "Rate", "Amount", "State", "Range", "Open"] + (["Conf."] if with_conf else [])]

  for ln in lines:
    why = f"<br/><font color='#b45309'>{ln['unpriced_why']}</font>" if ln.get("unpriced_why") else ""
    rows.append([Paragraph(ln["code"], s["cell"]), Paragraph(f"{ln.get('description') or ''}{why}", s["cell"]), ln.get("floor") or "", ln["unit"], qty(ln.get("qty")), money(ln.get("rate")), money(ln.get("amount")), Paragraph(ln["label"], s["cell"]), pct_span(ln), ln["open_rows"] or ""] + ([ln.get("confidence") or ""] if with_conf else []))

  story.append(table(rows, [28 * mm, 64 * mm, 18 * mm, 12 * mm, 22 * mm, 20 * mm, 26 * mm, 30 * mm, 28 * mm, 12 * mm] + ([14 * mm] if with_conf else []), right=(4, 5, 6)))
  
  story += [Spacer(1, 8), Paragraph("Totals", s["h2"]), table(totals_rows(totals), [90 * mm, 110 * mm], right=(1,))]
  if totals.get("by_section"):
    story += [Spacer(1, 6), table([["Section", "Amount"]] + [[k, money(v)] for k, v in totals["by_section"].items()], [90 * mm, 50 * mm], right=(1,))]
  if totals.get("by_floor"):
    story += [Spacer(1, 6), table([["Floor", "Amount"]] + [[k, money(v)] for k, v in totals["by_floor"].items()], [90 * mm, 50 * mm], right=(1,))]
  story += [Spacer(1, 8), Paragraph(footer, s["small"])]
  return build(story, landscape(A4), 10 * mm)

def client_pdf(title: str, meta: list, warnings: list, totals: dict, coverage: list, open_rows: list, assumed: list, unpriced: list, footer: str) -> bytes:
  s = styles()
  story = head_block(s, title, meta, warnings)
  story += [Paragraph("1. Totals", s["h2"]), table(totals_rows(totals), [70 * mm, 110 * mm], right=(1,))]
  story += [Spacer(1, 8), Paragraph("2. Coverage by section", s["h2"])]
  story.append(table([["Section", "Measured", "Assumed", "Asked", "Not read", "With a quantity"]] + [[Paragraph(c["section"], s["cell"]), c["MEASURED"], c["ASSUMED"], c["ASKED"], c["NOT_READ"], f"{c['with_quantity_pct']:.1f}%"] for c in coverage], [68 * mm, 20 * mm, 20 * mm, 20 * mm, 20 * mm, 32 * mm], right=(1, 2, 3, 4, 5)))
  story += [Spacer(1, 8), Paragraph(f"3. Open questions ({len(open_rows)})", s["h2"])]
  
  if open_rows:
    shown = open_rows[:LIMITS["open_rows_in_report"]]
    story.append(table([["What", "Sheet", "Changes", "Effect (Rs)"]] + [[Paragraph(f"{r['item']}: {r['prompt']}", s["cell"]), r.get("page") or "", f"{len(r.get('touches') or [])} item(s)", money(r.get("effect_rs"))] for r in shown], [100 * mm, 14 * mm, 22 * mm, 34 * mm], right=(3,)))
    if len(open_rows) > len(shown):
      story.append(Paragraph(f"{len(open_rows) - len(shown)} more are in the review list of the project.", s["small"]))
  else:
    story.append(Paragraph("No review row is open.", s["body"]))
  story += [Spacer(1, 8), Paragraph(f"4. Assumptions and their sources ({len(assumed)})", s["h2"])]
  if assumed:
    rows = [["Input", "Figure used", "Range", "Source", "Items"]]
    for a in assumed[:LIMITS["assumptions_in_report"]]:
      rg = a.get("range")
      rows.append([a["input"].replace("_", " "), f"{a.get('value')} {a.get('unit') or ''}".strip(), "-" if not rg else f"{rg[0]} to {rg[1]}", Paragraph(str(a.get("source") or ""), s["cell"]), len(a["items"])])
    story.append(table(rows, [40 * mm, 28 * mm, 28 * mm, 70 * mm, 14 * mm], right=(4,)))
  else:
    story.append(Paragraph("No quantity rests on an assumed input.", s["body"]))
    
  story += [Spacer(1, 8), Paragraph(f"5. Lines with no rate ({len(unpriced)})", s["h2"])]
  if unpriced:
    shown = unpriced[:LIMITS["unpriced_in_report"]]
    story.append(table([["Item", "Description", "Why"]] + [[u["code"], Paragraph(u.get("description") or "", s["cell"]), Paragraph(u.get("unpriced_why") or "", s["cell"])] for u in shown], [20 * mm, 70 * mm, 90 * mm]))
  else:
    story.append(Paragraph("Every line has a rate.", s["body"]))
  story += [Spacer(1, 8), Paragraph(footer, s["small"])]
  return build(story, A4)
