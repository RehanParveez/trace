from __future__ import annotations
import io
from decimal import Decimal as D

ZERO = D(0)
CENT = D("0.01")
CLASS_RANK = {"ERROR": 0, "CONFLICT": 1, "METHOD": 2, "CHECK": 3, "MISSING": 3, "EXTRA": 3, "UNVERIFIABLE": 4, "ROUNDING": 5, "NAMING": 6, "INFO": 7}
STATUSES = ("OPEN", "ACCEPTED", "REJECTED", "SIGNED")
COUNTED_STATUSES = ("OPEN", "ACCEPTED")
BASES = ("EXPECTATION", "ESTIMATE", "BBS_ROWS")
SHEET_NAME_MAX = 31
BAD_SHEET_CHARS = '[]:*?/\\'
ROW_ID_TOL = 0.05

def d(value) -> D | None:
  if value is None or value == "":
    return None
  return value if isinstance(value, D) else D(str(value))

def q2(value: D | None) -> D | None:
  return None if value is None else value.quantize(CENT)

def num(value) -> float | None:
  v = d(value)
  return None if v is None else float(v)

def sort_key(f: dict) -> tuple:
  ref = f.get("bbs_ref") or {}
  return (CLASS_RANK.get(f.get("finding_class"), 9), f.get("code") or "", ref.get("sheet") if ref.get("sheet") is not None else 999, ref.get("page") or 0,
    ref.get("member") or "", ref.get("sr") or 0, str(f.get("id") or ""))

def sort_findings(findings: list) -> list:
  out = sorted(findings, key=sort_key)
  return [{**f, "no": i} for i, f in enumerate(out, start=1)]

def counted(f: dict) -> bool:
  return f.get("status") in COUNTED_STATUSES and f.get("effect_basis") in BASES and d(f.get("diff_kg")) is not None

def where(ref: dict | None) -> str:
  ref = ref or {}
  parts = []
  if ref.get("sheet_name"):
    parts.append(str(ref["sheet_name"]))
  if ref.get("page"):
    parts.append(f"p.{ref['page']}")
  if ref.get("member"):
    parts.append(str(ref["member"]))
  if ref.get("sr"):
    parts.append(f"Sr {ref['sr']}")
  return " · ".join(parts) or "—"

def drawing_text(ref: dict | None) -> str:
  if not ref:
    return ""
  parts = []
  if ref.get("sheet_no"):
    parts.append(str(ref["sheet_no"]))
  if ref.get("page"):
    parts.append(f"p.{ref['page']}")
  if ref.get("what"):
    parts.append(str(ref["what"]))
  return " · ".join(parts)

def summarize(rows: list, sheets: list, findings: list) -> dict:
  bbs_total = sum((d(r.get("total_kg")) or ZERO for r in rows), ZERO)
  by_sheet_rows: dict = {}
  
  for r in rows:
    by_sheet_rows[r["sheet"]] = by_sheet_rows.get(r["sheet"], ZERO) + (d(r.get("total_kg")) or ZERO)
  effect = ZERO
  effect_by_class: dict = {}
  effect_by_basis: dict = {}
  effect_by_sheet: dict = {}
  excluded = {"REJECTED": ZERO, "SIGNED": ZERO}
  for f in findings:
    amount = d(f.get("diff_kg"))
    if amount is None or f.get("effect_basis") not in BASES:
      continue
    if f.get("status") in excluded:
      excluded[f["status"]] += amount
      continue
    effect += amount
    
    effect_by_class[f["finding_class"]] = effect_by_class.get(f["finding_class"], ZERO) + amount
    effect_by_basis[f["effect_basis"]] = effect_by_basis.get(f["effect_basis"], ZERO) + amount
    sheet = (f.get("bbs_ref") or {}).get("sheet")
    effect_by_sheet[sheet] = effect_by_sheet.get(sheet, ZERO) + amount
    
  by_class: dict = {}
  by_status = {s: 0 for s in STATUSES}
  by_code: dict = {}
  per_sheet_count: dict = {}
  per_sheet_open: dict = {}
  
  for f in findings:
    by_class[f["finding_class"]] = by_class.get(f["finding_class"], 0) + 1
    by_status[f["status"]] = by_status.get(f["status"], 0) + 1
    by_code[f["code"]] = by_code.get(f["code"], 0) + 1
    sheet = (f.get("bbs_ref") or {}).get("sheet")
    per_sheet_count[sheet] = per_sheet_count.get(sheet, 0) + 1
    if f["status"] == "OPEN":
      per_sheet_open[sheet] = per_sheet_open.get(sheet, 0) + 1
      
  sheet_out = []
  for s in sorted(sheets, key=lambda s: s["idx"]):
    computed = by_sheet_rows.get(s["idx"], ZERO)
    printed = d(s.get("printed_total_kg"))
    eff = effect_by_sheet.get(s["idx"], ZERO)
    sheet_out.append({"idx": s["idx"], "name": s["name"], "first_page": s["first_page"], "last_page": s["last_page"], "row_count": sum(1 for r in rows if r["sheet"] == s["idx"]),
      "printed_total_kg": q2(printed), "computed_kg": q2(computed), "printed_diff_kg": None if printed is None else q2(computed - printed),
      "effect_kg": q2(eff), "expected_kg": q2(computed + eff), "findings": per_sheet_count.get(s["idx"], 0), "open_findings": per_sheet_open.get(s["idx"], 0)})
    
  loose = effect_by_sheet.get(None, ZERO)
  expected = bbs_total + effect
  return {"bbs_total_kg": q2(bbs_total), "expected_total_kg": q2(expected), "diff_kg": q2(effect), "diff_pct": None if bbs_total == 0 else (effect / bbs_total * 100).quantize(CENT),
    "printed_total_kg": q2(sum((d(s.get("printed_total_kg")) or ZERO for s in sheets), ZERO)),
    "effect_by_class": {k: q2(v) for k, v in sorted(effect_by_class.items(), key=lambda t: CLASS_RANK.get(t[0], 9))},
    "effect_by_basis": {k: q2(v) for k, v in effect_by_basis.items()},
    "excluded_kg": {k: q2(v) for k, v in excluded.items()},
    "counts_by_class": dict(sorted(by_class.items(), key=lambda t: CLASS_RANK.get(t[0], 9))), "counts_by_status": by_status,
    "counts_by_code": dict(sorted(by_code.items())), "finding_count": len(findings), "sheets": sheet_out,
    "unassigned": {"findings": per_sheet_count.get(None, 0), "effect_kg": q2(loose)}}

def questions(findings: list) -> list:
  out = []
  for f in findings:
    text = (f.get("question") or "").strip()
    if not text or f.get("status") != "OPEN":
      continue
    n = len(out) + 1
    ref = f.get("bbs_ref") or {}
    out.append({"no": n, "finding_id": f["id"], "finding_no": f["no"], "code": f["code"], "finding_class": f["finding_class"], "where": where(ref), "member": ref.get("member"),
      "question": text, "text": f"Q{n}. [{where(ref)}] {text}"})
  return out

def questions_text(items: list) -> str:
  return "\n".join(i["text"] for i in items)

def findings_by_row(rows: list, findings: list) -> dict:
  by_no = {r["row_no"]: r for r in rows}
  by_pos: dict = {}
  
  for r in rows:
    by_pos.setdefault((r["sheet"], r["page"], r.get("sr")), []).append(r)
  out: dict = {}
  for f in findings:
    ref = f.get("bbs_ref") or {}
    named = [i + 1 for i in (x.get("index") for x in (ref.get("rows") or [])) if isinstance(i, int)]
    if not named and ref.get("sheet") is not None and ref.get("page") is not None and ref.get("y") is not None:
      for r in by_pos.get((ref["sheet"], ref["page"], ref.get("sr")), []):
        if r.get("y") is not None and abs(float(r["y"]) - float(ref["y"])) <= ROW_ID_TOL:
          named.append(r["row_no"])
    for no in named:
      if no in by_no:
        out.setdefault(no, []).append(f)
  return out

def row_verdict(hits: list) -> dict:
  if not hits:
    return {"class": None, "rule": None, "status": None, "more": 0}
  top = sorted(hits, key=sort_key)[0]
  return {"class": top["finding_class"], "rule": top["rule"], "status": top["status"], "more": len(hits) - 1}

def _cell(text) -> str:
  return str("" if text is None else text).replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip()

def _kg(value) -> str:
  v = d(value)
  return "—" if v is None else f"{v:,.2f}"

def _signed(value) -> str:
  v = d(value)
  if v is None:
    return "—"
  return f"{'+' if v > 0 else ''}{v:,.2f}"

def summary_md(doc: dict, run: dict | None, summary: dict, findings: list, items: list) -> str:
  lines = [f"# Bar schedule audit: {doc.get('file_name') or 'schedule'} (version {doc.get('version')})", ""]
  if run:
    lines += [f"Audit level {run.get('level')} run on {str(run.get('created_at') or '')[:10]}. Every effect is Trace minus schedule, in kg; a schedule that bills too much shows negative.", ""]
  pct = "—" if summary["diff_pct"] is None else f"{_signed(summary['diff_pct'])} %"
  lines += ["## Totals", "", "| | kg |", "|---|---:|", f"| Schedule total | {_kg(summary['bbs_total_kg'])} |", f"| Expected total | {_kg(summary['expected_total_kg'])} |",
    f"| Difference | {_signed(summary['diff_kg'])} ({pct}) |", "",
    "The expected total is the schedule total plus the weight effect of the findings that are still open or accepted and that state the basis of their figure. "
    "Rejected and signed findings leave the billed figure standing.", ""]
  basis = summary["effect_by_basis"]
  
  if basis:
    lines += ["| Basis of the effect | kg |", "|---|---:|"] + [f"| {k.title().replace('_', ' ')} | {_signed(v)} |" for k, v in basis.items()] + [""]
    if "ESTIMATE" in basis:
      lines += ["The estimate part rests on an input that was assumed or derived, not read from the drawing.", ""]
  lines += ["## Findings by class", "", "| Class | Findings | Effect kg |", "|---|---:|---:|"]
  for klass, n in summary["counts_by_class"].items():
    lines.append(f"| {klass} | {n} | {_signed(summary['effect_by_class'].get(klass))} |")
  st = summary["counts_by_status"]
  lines += ["", f"Open {st.get('OPEN', 0)} · accepted {st.get('ACCEPTED', 0)} · rejected {st.get('REJECTED', 0)} · signed {st.get('SIGNED', 0)}", "",
    "## Sheets", "", "| Sheet | Printed total kg | Recomputed kg | Expected kg | Findings |", "|---|---:|---:|---:|---:|"]
  for s in summary["sheets"]:
    lines.append(f"| {_cell(s['name'])} | {_kg(s['printed_total_kg'])} | {_kg(s['computed_kg'])} | {_kg(s['expected_kg'])} | {s['findings']} |")
  lines += ["", "## Findings", "", "| No | Class | Check | Where | Schedule | Trace | kg | Status |", "|---:|---|---|---|---|---|---:|---|"]
  for f in findings:
    lines.append(f"| F{f['no']} | {f['finding_class']} | {f['code']} | {_cell(where(f.get('bbs_ref')))} | {_cell(f.get('bbs_value'))} | {_cell(f.get('trace_value'))} | {_signed(f.get('diff_kg'))} | {f['status']} |")
  lines += ["", "## Questions", ""]
  if items:
    lines += [f"{i['no']}. [{i['where']}] {i['question']} (F{i['finding_no']})" for i in items]
  else:
    lines.append("No question is open.")
  return "\n".join(lines) + "\n"

BBS_COLUMNS = [("Page", "page", 6), ("Member", "member", 14), ("Sr", "sr", 5), ("Description", "description", 22), ("Dia (#)", "dia", 7), ("C/C (in)", "spacing_in", 8),
  ("Members", "members", 9), ("Each", "each", 8), ("Total bars", "total", 10), ("Cut (ft)", "cut_ft", 9), ("Total length (ft)", "total_ft", 12), ("Unit kg/ft", "unit_kg_ft", 10),
  ("BBS kg", "total_kg", 12)]
TRACE_COLUMNS = [("Trace each", 11), ("Trace cut (ft)", 12), ("Trace kg", 12), ("Trace − schedule kg", 14), ("Class", 13), ("Rule", 46), ("Status", 11)]
FINDING_COLUMNS = [("No", 6), ("Class", 13), ("Check", 22), ("Sheet", 22), ("Page", 6), ("Member", 12), ("Sr", 5), ("Description", 20), ("Rule", 50), ("Schedule", 26), ("Trace", 26),
  ("Effect kg", 11), ("Effect %", 9), ("Basis", 13), ("Confidence", 10), ("Status", 11), ("Reason", 34), ("Drawing", 34), ("Question", 60)]
QUESTION_COLUMNS = [("No", 5), ("Finding", 8), ("Class", 13), ("Where", 40), ("Question", 90), ("Answer", 40)]

def sheet_titles(names: list) -> list:
  taken = {"summary", "findings", "questions"}
  out = []
  
  for raw in names:
    base = "".join("-" if c in BAD_SHEET_CHARS else c for c in (raw or "Sheet")).strip("' ")[:SHEET_NAME_MAX] or "Sheet"
    name, n = base, 1
    while name.lower() in taken:
      n += 1
      suffix = f" ({n})"
      name = base[:SHEET_NAME_MAX - len(suffix)] + suffix
    taken.add(name.lower())
    out.append(name)
  return out

def build_xlsx(doc: dict, run: dict | None, rows: list, sheets: list, findings: list, row_expect: dict, summary: dict, items: list) -> bytes:
  from openpyxl import Workbook
  from openpyxl.styles import Alignment, Font, PatternFill
  from openpyxl.utils import get_column_letter
  head_fill = PatternFill("solid", fgColor="1F3A5F")
  trace_fill = PatternFill("solid", fgColor="7A5C00")
  head_font = Font(bold=True, color="FFFFFF")
  bold = Font(bold=True)
  wrap = Alignment(wrap_text=True, vertical="top")
  kg_fmt = "#,##0.00"
  hits = findings_by_row(rows, findings)
  wb = Workbook()
  ws = wb.active
  ws.title = "Summary"
  
  ws.append([f"Bar schedule audit: {doc.get('file_name') or 'schedule'} (version {doc.get('version')})"])
  ws["A1"].font = Font(bold=True, size=13)
  ws.append([f"Audit level {run.get('level')} · {str(run.get('created_at') or '')[:10]}" if run else "No audit has been run"])
  ws.append(["Every effect is Trace minus schedule, in kg. Expected total = schedule total + the effect of open and accepted findings that state their basis."])
  ws.append([])
  
  for label, value in (("Schedule total (kg)", summary["bbs_total_kg"]), ("Expected total (kg)", summary["expected_total_kg"]), ("Difference (kg)", summary["diff_kg"]),
      ("Difference (%)", summary["diff_pct"]), ("Printed totals added (kg)", summary["printed_total_kg"])):
    ws.append([label, num(value)])
    ws.cell(ws.max_row, 1).font = bold
    ws.cell(ws.max_row, 2).number_format = kg_fmt
  ws.append([])
  ws.append(["Class", "Findings", "Effect kg"])
  
  for c in ws[ws.max_row]:
    c.font, c.fill = head_font, head_fill
  for klass, n in summary["counts_by_class"].items():
    ws.append([klass, n, num(summary["effect_by_class"].get(klass))])
    ws.cell(ws.max_row, 3).number_format = kg_fmt
    
  st = summary["counts_by_status"]
  ws.append([])
  ws.append(["Open", st.get("OPEN", 0), "Accepted", st.get("ACCEPTED", 0), "Rejected", st.get("REJECTED", 0), "Signed", st.get("SIGNED", 0)])
  ws.append([])
  ws.append(["Sheet", "Printed total kg", "Recomputed kg", "Effect kg", "Expected kg", "Findings", "Open"])
  
  for c in ws[ws.max_row]:
    c.font, c.fill = head_font, head_fill
  for s in summary["sheets"]:
    ws.append([s["name"], num(s["printed_total_kg"]), num(s["computed_kg"]), num(s["effect_kg"]), num(s["expected_kg"]), s["findings"], s["open_findings"]])
    for col in (2, 3, 4, 5):
      ws.cell(ws.max_row, col).number_format = kg_fmt
  if summary["unassigned"]["findings"]:
    ws.append(["Not on one sheet", None, None, num(summary["unassigned"]["effect_kg"]), None, summary["unassigned"]["findings"]])
    ws.cell(ws.max_row, 4).number_format = kg_fmt
  for i, w in enumerate((34, 18, 16, 14, 16, 10, 8, 10), start=1):
    ws.column_dimensions[get_column_letter(i)].width = w
  names = sheet_titles([s["name"] for s in sorted(sheets, key=lambda s: s["idx"])])
  sums_of = {s["idx"]: x for s, x in zip(sorted(sheets, key=lambda s: s["idx"]), summary["sheets"])}
  for s, title in zip(sorted(sheets, key=lambda s: s["idx"]), names):
    sh = wb.create_sheet(title)
    head = [c[0] for c in BBS_COLUMNS] + [c[0] for c in TRACE_COLUMNS]
    sh.append(head)
    for i, cell in enumerate(sh[1], start=1):
      cell.font, cell.alignment = head_font, Alignment(wrap_text=True, vertical="center")
      cell.fill = head_fill if i <= len(BBS_COLUMNS) else trace_fill
    for i, w in enumerate([c[2] for c in BBS_COLUMNS] + [c[1] for c in TRACE_COLUMNS], start=1):
      sh.column_dimensions[get_column_letter(i)].width = w
    first = 2
    for r in (r for r in rows if r["sheet"] == s["idx"]):
      ex = row_expect.get(str(r["row_no"] - 1)) or {}
      verdict = row_verdict(hits.get(r["row_no"], []))
      bbs_kg, trace_kg = d(r.get("total_kg")), d(ex.get("kg"))
      rule = verdict["rule"] or ""
      if verdict["more"]:
        rule = f"{rule} (+{verdict['more']} more)"
      sh.append([r["page"], r.get("member"), r.get("sr"), r.get("description")] + [num(r.get(key)) for _l, key, _w in BBS_COLUMNS[4:]] +
        [num(ex.get("each")), num(ex.get("cut")), num(trace_kg), None if bbs_kg is None or trace_kg is None else num(trace_kg - bbs_kg), verdict["class"], rule, verdict["status"]])
      row_no = sh.max_row
      for col in (len(BBS_COLUMNS), len(BBS_COLUMNS) + 3, len(BBS_COLUMNS) + 4):
        sh.cell(row_no, col).number_format = kg_fmt
      sh.cell(row_no, len(BBS_COLUMNS) + 6).alignment = wrap
    last = sh.max_row
    
    kg_col, tk_col, df_col = get_column_letter(len(BBS_COLUMNS)), get_column_letter(len(BBS_COLUMNS) + 3), get_column_letter(len(BBS_COLUMNS) + 4)
    foot = last + 2
    sh.cell(foot, 4, "Totals of the rows (Trace columns: rows compared only)").font = bold
    sh.cell(foot, len(BBS_COLUMNS), f"=SUM({kg_col}{first}:{kg_col}{max(last, first)})")
    sh.cell(foot, len(BBS_COLUMNS) + 3, f"=SUM({tk_col}{first}:{tk_col}{max(last, first)})")
    sh.cell(foot, len(BBS_COLUMNS) + 4, f"=SUM({df_col}{first}:{df_col}{max(last, first)})")
    sh.cell(foot + 1, 4, "Printed total of the sheet").font = bold
    sh.cell(foot + 1, len(BBS_COLUMNS), num(s.get("printed_total_kg")))
    sh.cell(foot + 2, 4, "Effect of the findings on this sheet (kg)").font = bold
    sh.cell(foot + 2, len(BBS_COLUMNS), num(sums_of[s["idx"]]["effect_kg"]))
    sh.cell(foot + 3, 4, "Expected total of the sheet").font = bold
    sh.cell(foot + 3, len(BBS_COLUMNS), f"={kg_col}{foot}+{kg_col}{foot + 2}")
    for rr in range(foot, foot + 4):
      for cc in (len(BBS_COLUMNS), len(BBS_COLUMNS) + 3, len(BBS_COLUMNS) + 4):
        sh.cell(rr, cc).number_format = kg_fmt
    sh.freeze_panes = "E2"
    
  fs = wb.create_sheet("Findings")
  fs.append([c[0] for c in FINDING_COLUMNS])
  for cell in fs[1]:
    cell.font, cell.fill = head_font, head_fill
  for i, w in enumerate([c[1] for c in FINDING_COLUMNS], start=1):
    fs.column_dimensions[get_column_letter(i)].width = w
  for f in findings:
    ref = f.get("bbs_ref") or {}
    fs.append([f["no"], f["finding_class"], f["code"], ref.get("sheet_name"), ref.get("page"), ref.get("member"), ref.get("sr"), ref.get("description"), f.get("rule"),
      f.get("bbs_value"), f.get("trace_value"), num(f.get("diff_kg")), num(f.get("diff_pct")), f.get("effect_basis"), num(f.get("confidence")), f["status"], f.get("reason"),
      drawing_text(f.get("drawing_ref")), f.get("question")])
    fs.cell(fs.max_row, 12).number_format = kg_fmt
    for col in (9, 10, 11, 17, 18, 19):
      fs.cell(fs.max_row, col).alignment = wrap
      
  fs.freeze_panes = "A2"
  qs = wb.create_sheet("Questions")
  qs.append([c[0] for c in QUESTION_COLUMNS])
  for cell in qs[1]:
    cell.font, cell.fill = head_font, head_fill
  for i, w in enumerate([c[1] for c in QUESTION_COLUMNS], start=1):
    qs.column_dimensions[get_column_letter(i)].width = w
  for i in items:
    qs.append([i["no"], f"F{i['finding_no']}", i["finding_class"], i["where"], i["question"], None])
    for col in (4, 5):
      qs.cell(qs.max_row, col).alignment = wrap
  qs.freeze_panes = "A2"
  out = io.BytesIO()
  wb.save(out)
  return out.getvalue()
