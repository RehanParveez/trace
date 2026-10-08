from __future__ import annotations
from app.modules.drawings_boq.models import BOQItem, BOQVersion, BOQItemRateSource
from decimal import Decimal
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from app.modules.drawings_boq.words import rupees_in_words
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from reportlab.lib.pagesizes import landscape

_SECTION_TITLES = {
  "MATERIAL": "A. Materials",
  "LABOUR": "B. Labour",
  "CUSTOM": "C. Additional Works",
}

def _group_items(items: list[BOQItem]) -> dict[str, list[BOQItem]]:
  groups: dict[str, list[BOQItem]] = {"MATERIAL": [], "LABOUR": [], "CUSTOM": []}
  for item in items:
    groups[item.item_type.value].append(item)
  return groups

def _section_total(items: list[BOQItem]) -> Decimal:
  return sum(
    (item.quantity * item.unit_rate for item in items if item.unit_rate is not None),
    Decimal("0"),
  )

def build_boq_pdf(
  boq_version: BOQVersion,
  items: list[BOQItem],
  company_name: str,
) -> bytes:
  buffer = BytesIO()
  doc = SimpleDocTemplate(
    buffer, pagesize=A4,
    topMargin=18 * mm, bottomMargin=18 * mm,
    leftMargin=16 * mm, rightMargin=16 * mm,
  )
  styles = getSampleStyleSheet()
  meta = boq_version.export_meta or {}
  company = meta.get("company_name") or company_name

  story = [
    Paragraph(company, ParagraphStyle("Co", parent=styles["Heading1"], fontSize=16)),
    Paragraph("BILL OF QUANTITIES", styles["Heading2"]),
  ]

  if any(item.status.value == "DRAFT" for item in items):
    story.append(Paragraph(
      "DRAFT — contains unapproved line items, figures may change.",
      ParagraphStyle("Warn", parent=styles["Normal"], textColor=colors.red),
    ))

  missing_rate_count = sum(1 for i in items if i.unit_rate is None)
  ai_rate_count = sum(1 for i in items if i.rate_source == BOQItemRateSource.AI_SUGGESTED)
  if missing_rate_count:
    story.append(Paragraph(
      f"{missing_rate_count} item(s) have no rate yet — grand total is understated until priced.",
      ParagraphStyle("Warn2", parent=styles["Normal"], textColor=colors.red),
    ))
  if ai_rate_count:
    story.append(Paragraph(
      f"{ai_rate_count} item(s) use an AI-suggested rate — verify before final issue.",
      ParagraphStyle("Warn3", parent=styles["Normal"], textColor=colors.HexColor("#b45309")),
    ))

  project_rows = [
    ["Client", meta.get("client_name", "-"), "Project Title", meta.get("project_title", "-")],
    ["Location", meta.get("location", "-"), "Plot Size", meta.get("plot_size", "-")],
    ["Covered Area (Sft)", str(boq_version.covered_area_sqft or "-"), "Storeys", meta.get("storeys", "-")],
    ["Date", boq_version.created_at.strftime("%d %B %Y"), "", ""],
  ]
  project_table = Table(project_rows, colWidths=[35 * mm, 55 * mm, 35 * mm, 55 * mm])
  project_table.setStyle(TableStyle([
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
    ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
  ]))
  story += [Spacer(1, 6), project_table, Spacer(1, 10)]

  groups = _group_items(items)
  grand_total = Decimal("0")

  for key in ("MATERIAL", "LABOUR", "CUSTOM"):
    section_items = groups[key]
    if not section_items:
      continue
    story.append(Paragraph(_SECTION_TITLES[key], styles["Heading3"]))
    rows = [["#", "Description", "Unit", "Qty", "Rate (Rs)", "Amount (Rs)"]]
    for idx, item in enumerate(section_items, start=1):
      amount = item.quantity * item.unit_rate if item.unit_rate is not None else None
      rate_flag = " [RATE MISSING]" if item.unit_rate is None else (
        " [AI est. — verify]" if item.rate_source == BOQItemRateSource.AI_SUGGESTED else ""
      )
      label = item.material_name + (" (unapproved)" if item.status.value == "DRAFT" else "") + rate_flag
      rows.append([
        str(idx), label, item.unit, f"{item.quantity:,.2f}",
        f"{item.unit_rate:,.2f}" if item.unit_rate is not None else "—",
        f"{amount:,.2f}" if amount is not None else "—",
      ])
    section_total = _section_total(section_items)
    grand_total += section_total
    rows.append(["", "", "", "", "Sub-total", f"{section_total:,.2f}"])

    table = Table(rows, colWidths=[8 * mm, 65 * mm, 15 * mm, 22 * mm, 25 * mm, 30 * mm])
    table.setStyle(TableStyle([
      ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
      ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
      ("FONTSIZE", (0, 0), (-1, -1), 8),
      ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
      ("GRID", (0, 0), (-1, -2), 0.25, colors.HexColor("#cbd5e1")),
      ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
    ]))
    story += [table, Spacer(1, 8)]

  cost_per_sqft = (
    grand_total / boq_version.covered_area_sqft
    if boq_version.covered_area_sqft and boq_version.covered_area_sqft > 0
    else None
  )

  story.append(Paragraph(f"<b>GRAND TOTAL: Rs {grand_total:,.2f}</b>", styles["Heading2"]))
  story.append(Paragraph(f"In words: {rupees_in_words(grand_total)}", styles["Normal"]))
  if cost_per_sqft is not None:
    story.append(Paragraph(f"Cost per Sft: Rs {cost_per_sqft:,.2f}", styles["Normal"]))

  story.append(Spacer(1, 20))
  sign_table = Table(
    [["Prepared By", meta.get("prepared_by", "____________________"),
      "Checked By", meta.get("checked_by", "____________________")]],
    colWidths=[25 * mm, 60 * mm, 25 * mm, 60 * mm],
  )
  sign_table.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9)]))
  story.append(sign_table)

  doc.build(story)
  return buffer.getvalue()

_STATUS_FILL = {"ADDED": "DCFCE7", "REMOVED": "FEE2E2", "CHANGED": "FEF9C3"}

def build_revision_comparison_xlsx(snapshot: dict, base: dict, diff: dict, meta: dict, company: str) -> bytes:
  wb = Workbook()
  head_fill, head_font, bold = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid"), Font(color="FFFFFF", bold=True), Font(bold=True)
  ws = wb.active
  ws.title = "Summary"
  ws.append([company, "REVISION COMPARISON"])
  ws["A1"].font = Font(bold=True, size=14)
  ws.append(["Base (older)", _stamp(base)])
  ws.append(["New", _stamp(snapshot)])
  ws.append([])
  summary = diff["summary"]
  for label, key in (("Lines added", "ADDED"), ("Lines removed", "REMOVED"), ("Lines changed", "CHANGED"), ("Lines unchanged", "UNCHANGED")):
    ws.append([label, summary[key]])
    
  ws.append([])
  ws.append(["Total (base)", float(summary["total_a"])])
  ws.append(["Total (new)", float(summary["total_b"])])
  ws.append(["Difference", float(summary["total_delta"])])
  ws.cell(row=ws.max_row, column=1).font = bold
  if summary.get("total_delta_pct") is not None:
    ws.append(["Difference %", float(summary["total_delta_pct"])])
  if summary["unpriced_a"] or summary["unpriced_b"]:
    ws.append([f"Unpriced lines: {summary['unpriced_a']} in the base, {summary['unpriced_b']} in the new snapshot - totals understate them."])
  ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 22, 110

  ch = wb.create_sheet("Changes")
  ch.append(["Status", "Work item", "Description", "Unit (base)", "Unit (new)", "Qty base", "Qty new", "Qty change",
    "Qty change %", "Rate base", "Rate new", "Rate change", "Amount base", "Amount new", "Amount change"])
  
  for c in ch[1]:
    c.fill, c.font = head_fill, head_font
  order = {"ADDED": 0, "REMOVED": 1, "CHANGED": 2}
  for l in sorted((l for l in diff["lines"] if l["status"] != "UNCHANGED"),
      key=lambda l: (order[l["status"]], l["work_item_code"] or "~", l["material_name"] or "")):
    ch.append([l["status"], l["work_item_code"], l["material_name"], l["unit_a"], l["unit_b"], _num(l["quantity_a"]),
      _num(l["quantity_b"]), _num(l["quantity_delta"]), _num(l["quantity_delta_pct"]), _num(l["rate_a"]), _num(l["rate_b"]),
      _num(l["rate_delta"]), _num(l["amount_a"]), _num(l["amount_b"]), _num(l["amount_delta"])])
    fill = _STATUS_FILL.get(l["status"])
    
    if fill:
      ch.cell(row=ch.max_row, column=1).fill = PatternFill(start_color=fill, end_color=fill, fill_type="solid")
  for col, width in zip("ABCDEFGHIJKLMNO", (11, 16, 44, 10, 10, 14, 14, 14, 12, 12, 12, 12, 16, 16, 16)):
    ch.column_dimensions[col].width = width
  ch.freeze_panes = "A2"
  buffer = BytesIO()
  wb.save(buffer)
  return buffer.getvalue()

def build_boq_xlsx(
  boq_version: BOQVersion,
  items: list[BOQItem],
  company_name: str,
) -> bytes:

  meta = boq_version.export_meta or {}
  company = meta.get("company_name") or company_name

  wb = Workbook()
  ws = wb.active
  ws.title = "Bill of Quantities"

  header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
  header_font = Font(color="FFFFFF", bold=True)
  bold = Font(bold=True)

  ws.append([company])
  ws["A1"].font = Font(bold=True, size=14)
  ws.append(["BILL OF QUANTITIES"])
  ws.append([])
  ws.append(["Client", meta.get("client_name", "-"), "Project Title", meta.get("project_title", "-")])
  ws.append(["Location", meta.get("location", "-"), "Plot Size", meta.get("plot_size", "-")])
  ws.append(["Covered Area (Sft)", str(boq_version.covered_area_sqft or "-"), "Storeys", meta.get("storeys", "-")])

  missing_rate_count = sum(1 for i in items if i.unit_rate is None)
  ai_rate_count = sum(1 for i in items if i.rate_source == BOQItemRateSource.AI_SUGGESTED)
  if missing_rate_count:
    ws.append([f"{missing_rate_count} item(s) have no rate — total understated"])
  if ai_rate_count:
    ws.append([f"{ai_rate_count} item(s) use an AI-suggested rate — verify"])
  ws.append([])

  groups = _group_items(items)
  grand_total = Decimal("0")

  for key in ("MATERIAL", "LABOUR", "CUSTOM"):
    section_items = groups[key]
    if not section_items:
      continue
    ws.append([_SECTION_TITLES[key]])
    ws.cell(row=ws.max_row, column=1).font = bold
    header_row = ws.max_row + 1
    ws.append(["#", "Description", "Unit", "Qty", "Rate (Rs)", "Amount (Rs)"])
    for cell in ws[header_row]:
      cell.fill = header_fill
      cell.font = header_font
    for idx, item in enumerate(section_items, start=1):
      amount = item.quantity * item.unit_rate if item.unit_rate is not None else None
      rate_flag = " [RATE MISSING]" if item.unit_rate is None else (
        " [AI est. — verify]" if item.rate_source == BOQItemRateSource.AI_SUGGESTED else ""
      )
      label = item.material_name + (" (unapproved)" if item.status.value == "DRAFT" else "") + rate_flag
      ws.append([
        idx, label, item.unit, float(item.quantity),
        float(item.unit_rate) if item.unit_rate is not None else None,
        float(amount) if amount is not None else None,
      ])
    section_total = _section_total(section_items)
    grand_total += section_total
    ws.append(["", "", "", "", "Sub-total", float(section_total)])
    ws.cell(row=ws.max_row, column=5).font = bold
    ws.cell(row=ws.max_row, column=6).font = bold
    ws.append([])

  cost_per_sqft = (
    grand_total / boq_version.covered_area_sqft
    if boq_version.covered_area_sqft and boq_version.covered_area_sqft > 0
    else None
  )

  ws.append(["GRAND TOTAL", float(grand_total)])
  ws.cell(row=ws.max_row, column=1).font = bold
  ws.append(["In words", rupees_in_words(grand_total)])
  if cost_per_sqft is not None:
    ws.append(["Cost per Sft", float(cost_per_sqft)])
  ws.append([])
  ws.append(["Prepared By", meta.get("prepared_by", ""), "Checked By", meta.get("checked_by", "")])

  for col, width in zip("ABCDEF", (20, 40, 12, 14, 14, 16)):
    ws.column_dimensions[col].width = width

  buffer = BytesIO()
  wb.save(buffer)
  return buffer.getvalue()

def _m(v) -> str:
  return f"{Decimal(v):,.2f}" if v is not None else "-"

def _q(v) -> str:
  return f"{Decimal(v):,.4f}" if v is not None else "-"

def _stamp(s: dict) -> str:
  return (f"Snapshot v{s['version_no']} ({s['purpose']}) | hash {s['content_hash'][:12]} | engine "
    f"{s.get('engine_version') or '-'} | rules {s.get('rule_set_code') or '-'} v{s.get('rule_set_version') or '-'} "
    f"| convention {s.get('convention_code') or '-'}")

def _groups(rows: list[dict]) -> dict[str, list[dict]]:
  groups: dict[str, list[dict]] = {"MATERIAL": [], "LABOUR": [], "CUSTOM": []}
  for r in rows:
    groups.setdefault(r["item_type"], []).append(r)
  return groups

def _flag(r: dict) -> str:
  if r["unit_rate"] is None:
    return " [RATE MISSING]"
  return " [AI est. - verify]" if r.get("rate_source") == "AI_SUGGESTED" else ""

_GRID = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
  ("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
  ("VALIGN", (0, 0), (-1, -1), "TOP")]

def _styles():
  base = getSampleStyleSheet()
  return base, ParagraphStyle("Cell", parent=base["Normal"], fontSize=8, leading=10), \
    ParagraphStyle("Small", parent=base["Normal"], fontSize=7, textColor=colors.HexColor("#475569"))

def build_contract_boq_pdf(snapshot: dict, rows: list[dict], meta: dict, company: str) -> bytes:
  buffer = BytesIO()
  doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm, leftMargin=16 * mm, rightMargin=16 * mm)
  styles, cell, small = _styles()
  totals = snapshot["totals"]
  story = [Paragraph(company, ParagraphStyle("Co", parent=styles["Heading1"], fontSize=16)),
    Paragraph("BILL OF QUANTITIES", styles["Heading2"]), Paragraph(_stamp(snapshot), small)]
  if totals.get("unpriced_item_count"):
    story.append(Paragraph(f"{totals['unpriced_item_count']} item(s) have no rate yet - grand total is understated.",
      ParagraphStyle("Warn", parent=styles["Normal"], textColor=colors.red)))
  info = Table([
    ["Client", meta.get("client_name", "-"), "Project Title", meta.get("project_title", "-")],
    ["Location", meta.get("location", "-"), "Plot Size", meta.get("plot_size", "-")],
    ["Covered Area (Sft)", str(meta.get("covered_area_sqft") or "-"), "Storeys", meta.get("storeys", "-")],
    ["Date", snapshot["created_at"].strftime("%d %B %Y"), "", ""]], colWidths=[35 * mm, 55 * mm, 35 * mm, 55 * mm])
  info.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
    ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold")]))
  
  story += [Spacer(1, 6), info, Spacer(1, 10)]
  for key, rows_k in _groups(rows).items():
    if not rows_k:
      continue
    story.append(Paragraph(_SECTION_TITLES[key], styles["Heading3"]))
    data = [["#", "Description", "Unit", "Qty", "Rate (Rs)", "Amount (Rs)"]]
    for n, r in enumerate(rows_k, 1):
      data.append([str(n), Paragraph(r["material_name"] + _flag(r), cell), r["unit"], _q(r["quantity"]),
        _m(r["unit_rate"]), _m(r["amount"])])
    sub = sum((r["amount"] for r in rows_k if r["amount"] is not None), Decimal("0"))
    data.append(["", "", "", "", "Sub-total", _m(sub)])
    t = Table(data, colWidths=[8 * mm, 65 * mm, 15 * mm, 22 * mm, 25 * mm, 30 * mm], repeatRows=1)
    t.setStyle(TableStyle(_GRID + [("ALIGN", (3, 0), (-1, -1), "RIGHT"), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")]))
    story += [t, Spacer(1, 8)]
    
  grand = Decimal(totals["grand"])
  story.append(Paragraph(f"<b>GRAND TOTAL: Rs {grand:,.2f}</b>", styles["Heading2"]))
  story.append(Paragraph(f"In words: {rupees_in_words(grand)}", styles["Normal"]))
  area = meta.get("covered_area_sqft")
  
  if area and Decimal(area) > 0:
    story.append(Paragraph(f"Cost per Sft: Rs {grand / Decimal(area):,.2f}", styles["Normal"]))
  story.append(Spacer(1, 20))
  sign = Table([["Prepared By", meta.get("prepared_by", "____________________"), "Checked By",
    meta.get("checked_by", "____________________")]], colWidths=[25 * mm, 60 * mm, 25 * mm, 60 * mm])
  
  sign.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9)]))
  story.append(sign)
  doc.build(story)
  return buffer.getvalue()

def build_contract_boq_xlsx(snapshot: dict, rows: list[dict], meta: dict, company: str) -> bytes:
  wb = Workbook()
  ws = wb.active
  ws.title = "Bill of Quantities"
  head_fill, head_font, bold = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid"), Font(color="FFFFFF", bold=True), Font(bold=True)
  ws.append([company])
  ws["A1"].font = Font(bold=True, size=14)
  ws.append(["BILL OF QUANTITIES"])
  ws.append([_stamp(snapshot)])
  ws.append([])
  ws.append(["Client", meta.get("client_name", "-"), "Project Title", meta.get("project_title", "-")])
  ws.append(["Location", meta.get("location", "-"), "Plot Size", meta.get("plot_size", "-")])
  ws.append(["Covered Area (Sft)", str(meta.get("covered_area_sqft") or "-"), "Storeys", meta.get("storeys", "-")])
  if snapshot["totals"].get("unpriced_item_count"):
    ws.append([f"{snapshot['totals']['unpriced_item_count']} item(s) have no rate - total understated"])
  ws.append([])
  for key, rows_k in _groups(rows).items():
    if not rows_k:
      continue
    ws.append([_SECTION_TITLES[key]])
    ws.cell(row=ws.max_row, column=1).font = bold
    ws.append(["#", "Description", "Unit", "Qty", "Rate (Rs)", "Amount (Rs)", "Base rate (Rs)", "Escalation (x)"])
    for c in ws[ws.max_row]:
      c.fill, c.font = head_fill, head_font
    for n, r in enumerate(rows_k, 1):
      ws.append([n, r["material_name"] + _flag(r), r["unit"], float(r["quantity"]),
        float(r["unit_rate"]) if r["unit_rate"] is not None else None,
        float(r["amount"]) if r["amount"] is not None else None,
        float(r["base_rate"]) if r.get("base_rate") is not None else None,
        float(r["escalation_factor"]) if r.get("escalation_factor") is not None else None])
    sub = sum((r["amount"] for r in rows_k if r["amount"] is not None), Decimal("0"))
    ws.append(["", "", "", "", "Sub-total", float(sub)])
    ws.cell(row=ws.max_row, column=5).font = ws.cell(row=ws.max_row, column=6).font = bold
    ws.append([])
    
  grand = Decimal(snapshot["totals"]["grand"])
  ws.append(["GRAND TOTAL", float(grand)])
  ws.cell(row=ws.max_row, column=1).font = bold
  ws.append(["In words", rupees_in_words(grand)])
  area = meta.get("covered_area_sqft")
  if area and Decimal(area) > 0:
    ws.append(["Cost per Sft", float(grand / Decimal(area))])
  for col, width in zip("ABCDEFGH", (22, 50, 12, 14, 14, 16, 16, 14)):
    ws.column_dimensions[col].width = width
  buffer = BytesIO()
  wb.save(buffer)
  return buffer.getvalue()

def build_procurement_xlsx(snapshot: dict, rows: list[dict], meta: dict, company: str) -> bytes:
  wb = Workbook()
  ws = wb.active
  ws.title = "Procurement"
  ws.append([company, "PROCUREMENT SCHEDULE"])
  ws["A1"].font = Font(bold=True, size=14)
  ws.append([_stamp(snapshot)])
  ws.append(["Gross quantities include waste and are for purchasing only; contract pricing uses the contract quantity."])
  ws.append([])
  ws.append(["#", "Work item", "Description", "Unit", "Net (calculated)", "Adjustments", "Contract qty",
    "Waste factor", "Gross (procure)", "Confidence", "Review"])
  for c in ws[ws.max_row]:
    c.fill, c.font = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid"), Font(color="FFFFFF", bold=True)
  for n, r in enumerate(rows, 1):
    ws.append([n, r["work_item_code"], r["material_name"], r["unit"],
      float(r["net_quantity"]) if r["net_quantity"] is not None else None, float(r["adjustment_total"]),
      float(r["quantity"]), float(r["waste_factor_applied"]) if r["waste_factor_applied"] is not None else None,
      float(r["gross_quantity"]) if r["gross_quantity"] is not None else None,
      float(r["confidence"]) if r["confidence"] is not None else None, r["review_status"]])
    
  for col, width in zip("ABCDEFGHIJK", (5, 16, 44, 8, 16, 14, 14, 12, 16, 12, 18)):
    ws.column_dimensions[col].width = width
  buffer = BytesIO()
  wb.save(buffer)
  return buffer.getvalue()

def _num(v):
  return float(v) if v is not None else None

def _dims(params: dict) -> str:
  return ", ".join(f"{k}={Decimal(str(v)):g}" for k, v in sorted((params or {}).items()))

def build_bbs_xlsx(snapshot: dict, marks: list[dict], meta: dict, company: str, estimated_kg: Decimal) -> bytes:
  wb = Workbook()
  ws = wb.active
  ws.title = "Bar Bending Schedule"
  head_fill, white = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid"), Font(color="FFFFFF", bold=True)
  bold = Font(bold=True)
  ws.append([company, "BAR BENDING SCHEDULE"])
  ws["A1"].font = Font(bold=True, size=14)
  ws.append([_stamp(snapshot)])
  
  ws.append(["Scheduled steel only (bar schedule or model). Estimated steel is never part of a bar bending schedule."])
  if estimated_kg and estimated_kg > 0:
    ws.append([f"Not included: {Decimal(estimated_kg):,.3f} kg of steel estimated from concrete volume (review required)."])
    ws.cell(row=ws.max_row, column=1).font = Font(color="B45309", bold=True)
  ws.append([])
  ws.append(["#", "Level", "Member", "Member mark", "Bar mark", "Shape", "Dimensions (mm)", "Dia (mm)", "Size", "Grade",
    "No. of bars", "Spacing (mm)", "Cut length (mm)", "Stock (mm)", "Pieces", "Laps", "Lap (mm)", "Total length (m)",
    "kg/m", "Total (kg)", "Source", "Confidence", "Review", "Warnings"])
  
  for c in ws[ws.max_row]:
    c.fill, c.font = head_fill, white
  for n, m in enumerate(marks, 1):
    ws.append([n, m["level"], m["member"], (m.get("trace") or {}).get("member_mark"), m["mark"], m["shape_code"],
      _dims(m.get("shape_params")), _num(m["dia_mm"]), m.get("designation"), m.get("grade"), m["count"],
      _num(m.get("spacing_mm")), _num(m["cut_len_mm"]), _num(m.get("stock_len_mm")), m["pieces"], m["lap_count"],
      _num(m.get("lap_len_mm")), _num(m["total_len_m"]), _num(m["unit_weight_kg_m"]), _num(m["total_kg"]),
      m["provenance"], _num(m["confidence"]), m["review_status"], ", ".join(m.get("warnings") or [])])
    
  total = sum((Decimal(m["total_kg"]) for m in marks), Decimal("0"))
  ws.append([])
  ws.append(["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "TOTAL", float(total)])
  ws.cell(row=ws.max_row, column=19).font = ws.cell(row=ws.max_row, column=20).font = bold
  for col, width in zip("ABCDEFGHIJKLMNOPQRSTUVWX", (5, 14, 22, 12, 10, 14, 22, 9, 8, 10, 10, 11, 14, 11, 8, 7, 9, 14, 9, 12, 16, 11, 16, 30)):
    ws.column_dimensions[col].width = width
  ws.freeze_panes = "A7" if estimated_kg and estimated_kg > 0 else "A6"

  sm = wb.create_sheet("Summary by diameter")
  sm.append([company, "STEEL SUMMARY BY DIAMETER AND GRADE"])
  sm["A1"].font = Font(bold=True, size=14)
  sm.append([_stamp(snapshot)])
  sm.append([])
  
  sm.append(["Dia (mm)", "Size", "Grade", "Bar marks", "Total length (m)", "Total (kg)", "Total (tonnes)"])
  for c in sm[sm.max_row]:
    c.fill, c.font = head_fill, white
    
  groups: dict = {}
  for m in marks:
    key = (Decimal(m["dia_mm"]), m.get("designation") or "", m.get("grade") or "")
    g = groups.setdefault(key, [0, Decimal("0"), Decimal("0")])
    g[0] += 1
    g[1] += Decimal(m["total_len_m"])
    g[2] += Decimal(m["total_kg"])
    
  for (dia, desig, grade), (count, length, kg) in sorted(groups.items()):
    sm.append([float(dia), desig or None, grade or None, count, float(length), float(kg), float(kg / 1000)])
  sm.append(["TOTAL", None, None, len(marks), None, float(total), float(total / 1000)])
  for c in sm[sm.max_row]:
    c.font = bold
    
  for col, width in zip("ABCDEFG", (10, 8, 12, 11, 16, 14, 14)):
    sm.column_dimensions[col].width = width
    
  buffer = BytesIO()
  wb.save(buffer)
  return buffer.getvalue()

def _evidence_text(e: dict) -> str:
  return "; ".join(e["steps"]) + (f"  [{', '.join(e['warnings'])}]" if e["warnings"] else "")

def build_measurement_book_pdf(snapshot: dict, rows: list[dict], evidence: dict, meta: dict, company: str) -> bytes:
  buffer = BytesIO()
  doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=15 * mm, bottomMargin=15 * mm, leftMargin=12 * mm, rightMargin=12 * mm)
  styles, cell, small = _styles()
  story = [Paragraph(f"{company} - MEASUREMENT BOOK", styles["Heading2"]), Paragraph(_stamp(snapshot), small), Spacer(1, 6)]
  
  for r in rows:
    story.append(Paragraph(f"<b>{r['line_no']}. {r['material_name']}</b> - contract {_q(r['quantity'])} {r['unit']} "
      f"(calculated {_q(r['net_quantity'])}, adjustments {_q(r['adjustment_total'])})", styles["Normal"]))
    lines = evidence.get(str(r["source_item_id"]), [])
    if lines:
      data = [["Element", "Level", "Qty (canonical)", "Working"]]
      
      for e in lines:
        data.append([Paragraph(str(e["element"]), cell), e["level"], f"{Decimal(e['quantity']):,.6f} {e['unit']}",
         Paragraph(_evidence_text(e), cell)])
      t = Table(data, colWidths=[55 * mm, 30 * mm, 40 * mm, 140 * mm], repeatRows=1)
      t.setStyle(TableStyle(_GRID))
      story.append(t)
      
    else:
      story.append(Paragraph("Manual or imported line - no model measurement behind it.", small))
    story.append(Spacer(1, 6))
  doc.build(story)
  return buffer.getvalue()

def build_measurement_book_xlsx(snapshot: dict, rows: list[dict], evidence: dict, meta: dict, company: str) -> bytes:
  wb = Workbook()
  ws = wb.active
  ws.title = "Measurement Book"
  ws.append([f"{company} - MEASUREMENT BOOK"])
  ws["A1"].font = Font(bold=True, size=14)
  ws.append([_stamp(snapshot)])
  ws.append([])
  
  for r in rows:
    ws.append([f"{r['line_no']}. {r['material_name']}", "", f"Contract {r['quantity']} {r['unit']}",
      f"Calculated {r['net_quantity']}", f"Adjustments {r['adjustment_total']}"])
    for c in ws[ws.max_row]:
      c.font = Font(bold=True)
    ws.append(["Element", "Level", "Qty", "Unit", "Working"])
    for e in evidence.get(str(r["source_item_id"]), []):
      ws.append([e["element"], e["level"], float(e["quantity"]), e["unit"], _evidence_text(e)])
    ws.append([])
    
  for col, width in zip("ABCDE", (46, 18, 16, 10, 100)):
    ws.column_dimensions[col].width = width
  buffer = BytesIO()
  wb.save(buffer)
  return buffer.getvalue()

def build_audit_report_pdf(snapshot: dict, rows: list[dict], issues: list[dict], adjustments: list[dict],
  meta: dict, company: str) -> bytes:
  buffer = BytesIO()
  doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=16 * mm, bottomMargin=16 * mm, leftMargin=14 * mm, rightMargin=14 * mm)
  styles, cell, small = _styles()
  story = [Paragraph(f"{company} - BOQ AUDIT REPORT", styles["Heading2"]), Paragraph(_stamp(snapshot), small), Spacer(1, 8)]

  def table(title, header, data, widths):
    story.append(Paragraph(title, styles["Heading3"]))
    if not data:
      story.append(Paragraph("None.", small))
      return
    t = Table([header] + data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle(_GRID))
    story.extend([t, Spacer(1, 8)])

  totals = snapshot["totals"]
  table("Summary", ["Items", "Unpriced", "Grand total (Rs)"],
    [[str(totals["item_count"]), str(totals["unpriced_item_count"]), _m(totals["grand"])]], [40 * mm, 40 * mm, 60 * mm])
  table("Review issues", ["Code", "Severity", "Blocks", "Status", "Message / note"],
    [[i["code"], i["severity"], i["blocks"], i["status"], Paragraph(i["message"] + (f" <i>Note: {i['note']}</i>" if i["note"] else ""), cell)]
     
      for i in issues], [38 * mm, 18 * mm, 20 * mm, 18 * mm, 88 * mm])
  table("Manual overrides (adjustments)", ["Item", "Kind", "Value", "Reason", "State"],
    [[Paragraph(a["item"], cell), a["kind"], _q(a["value"]), Paragraph(a["reason"], cell),
      "revoked" if a["revoked"] else "active"] for a in adjustments], [48 * mm, 16 * mm, 24 * mm, 70 * mm, 22 * mm])
  table("Items needing review or with low confidence", ["Item", "Review", "Confidence", "Source"],
    [[Paragraph(r["material_name"], cell), r["review_status"], str(r["confidence"] or "-"), r["source_kind"]]
      for r in rows if r["review_status"] != "OK" or (r["confidence"] is not None and r["confidence"] < Decimal("0.6"))],
      [90 * mm, 30 * mm, 28 * mm, 30 * mm])
  
  doc.build(story)
  return buffer.getvalue()