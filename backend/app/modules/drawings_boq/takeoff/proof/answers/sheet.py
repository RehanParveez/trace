from __future__ import annotations
import datetime
import os
from app.modules.drawings_boq.takeoff.proof.answers import qs_map as QM
from app.engine.catalogue import loader as CL
from app.modules.drawings_boq.takeoff.proof.answers import answers as AN
from app.modules.drawings_boq.takeoff.proof.answers import qs_import as QI

SHEET, ITEMS_SHEET, META = "Mappings", "Items", "_meta"
CANDIDATES = 5
REJECTED = "answers_rejected.yaml"
ACCEPT, USE_BELOW, NOT_ITEM = "accept proposed", "use item below", "not an item"
DECISIONS = (ACCEPT, USE_BELOW, NOT_ITEM)
HEAD = ["Key", "Workbook line", "Sheets", "Rows", "Quantity", "Proposed item", "Proposed by", "Decision", "Right item (when 'use item below')", "Floor (only if the line is for one floor)", "Note"]

class SheetError(Exception):
  pass

def review_path(case_name: str) -> str:
  return QM.case_paths(case_name, None)["review"]

def candidates_of(m: dict, index: QM.Index) -> list:
  ids = []
  for c in m.get("candidates") or []:
    cid = str(c).split(" ", 1)[0]
    if cid in index.by_id and cid not in ids:
      ids.append(cid)
      
  proposed = m.get("element")
  if proposed in index.by_id:
    ids = [proposed] + [i for i in ids if i != proposed]
  unit = next(iter((m.get("quantity") or {}).keys()), None)
  if len(ids) < CANDIDATES:
    for cid in index.choices_for(m.get("qs_line") or "", None if unit == "?" else unit):
      if cid not in ids:
        ids.append(cid)
      if len(ids) >= CANDIDATES:
        break
  return ids[:CANDIDATES]

def export(case_name: str, out_dir: str) -> dict:
  from openpyxl import Workbook
  from openpyxl.styles import Alignment, Font
  from openpyxl.worksheet.datavalidation import DataValidation
  review = AN.read_yaml(review_path(case_name))
  
  if not review:
    raise SheetError(f"there is no answers_review.yaml for {case_name}; run: python -m app.modules.drawings_boq.takeoff.proof.answers.qs_map map {case_name}")
  index = QM.Index(QI.vocabulary())
  wb = Workbook()
  ws = wb.active
  ws.title = SHEET
  ws.append(HEAD)
  for c in ws[1]:
    c.font = Font(bold=True)
  for col, width in zip("ABCDEFGHIJK", (24, 52, 22, 7, 20, 44, 12, 18, 40, 16, 30)):
    ws.column_dimensions[col].width = width
  ws.freeze_panes = "C2"
  wrap = Alignment(wrap_text=True, vertical="top")
  decide = DataValidation(type="list", formula1='"' + ",".join(DECISIONS) + '"', allow_blank=True)
  ws.add_data_validation(decide)
  mappings = review.get("mappings") or []
  
  for m in mappings:
    cands = candidates_of(m, index)
    proposed = m.get("element")
    named = f"{proposed} {index.by_id[proposed].name}" if proposed in index.by_id else "(nothing proposed)"
    qty = ", ".join(f"{q:g} {u}" for u, q in (m.get("quantity") or {}).items())
    ws.append([m["key"], m.get("qs_line"), ", ".join(str(s) for s in m.get("sheets") or []), m.get("rows"), qty, named, m.get("mapped_by") or "-", None, None, None, None])
    r = ws.max_row
    for c in ws[r]:
      c.alignment = wrap
    pick = DataValidation(type="list", formula1='"' + ",".join(cands) + '"', allow_blank=True, showErrorMessage=False)
    ws.add_data_validation(pick)
    pick.add(f"I{r}")
    ws.cell(row=r, column=11, value=None)
  decide.add(f"H2:H{max(2, ws.max_row)}")
  hint = wb.create_sheet("Read me", 0)
  
  for line in (f"Mappings of the workbook {review.get('workbook')} for QS {review.get('qs')} ({len(mappings)} lines to confirm).",
    "Trace proposes an item for each line; nothing is confirmed until a person sets a Decision. The AI never confirms.",
    "Decision 'accept proposed': the proposed item is right. 'use item below': pick the right item in column I (the first five are Trace's candidates; any item id of the Items sheet may be typed).",
    "'not an item': the line is not a catalogue item (a total, a heading, a rate). Put the reason in Note.",
    "Floor is only for a line that belongs to one floor (GROUND, FIRST ...); leave it empty otherwise.",
    "Leave a line with no Decision if you cannot tell; it stays unconfirmed and out of the bench.",
    "Then run: python -m app.modules.drawings_boq.takeoff.proof.answers.qs_map import " + case_name + " <this file> --by \"<name of the QS or the person who confirmed>\" [--write]"):
    hint.append([line])
  hint.column_dimensions["A"].width = 150
  items = wb.create_sheet(ITEMS_SHEET)
  items.append(["Item", "Name", "Unit"])
  
  for it in index.items:
    items.append([it.id, it.name, it.unit])
  items.column_dimensions["B"].width = 70
  meta = wb.create_sheet(META)
  meta.sheet_state = "hidden"
  for k, v in (("case", case_name), ("qs", review.get("qs")), ("workbook", review.get("workbook")), ("lines", len(mappings))):
    meta.append([k, v])
  os.makedirs(out_dir, exist_ok=True)
  path = os.path.join(out_dir, f"mappings_{case_name}.xlsx")
  wb.save(path)
  return {"path": path, "lines": len(mappings), "qs": review.get("qs")}

def read(path: str) -> dict:
  from openpyxl import load_workbook
  wb = load_workbook(path, data_only=True)
  if SHEET not in wb.sheetnames or META not in wb.sheetnames:
    raise SheetError("this is not a mapping sheet made by `qs_map export` (no Mappings or _meta sheet)")
  meta = {str(r[0]): r[1] for r in wb[META].iter_rows(values_only=True) if r[0] is not None}
  rows = []
  for r in wb[SHEET].iter_rows(min_row=2, values_only=True):
    if r[0] is None:
      continue
    rows.append({"key": str(r[0]), "decision": str(r[7] or "").strip().lower(), "item": str(r[8] or "").strip().upper(), "floor": str(r[9] or "").strip().upper(), "note": str(r[10] or "").strip()})
  return {"meta": meta, "rows": rows}

def apply(case_name: str, path: str, by: str, write: bool, today: str | None = None) -> dict:
  if not by or not by.strip():
    raise SheetError("--by must name the person who confirmed; a confirmation with no name is not one")
  today = today or datetime.date.today().isoformat()
  book = read(path)
  if book["meta"].get("case") != case_name:
    raise SheetError(f"this sheet is for case {book['meta'].get('case')!r}, not {case_name!r}")
  review = AN.read_yaml(review_path(case_name))
  
  if not review:
    raise SheetError(f"there is no answers_review.yaml for {case_name}")
  if book["meta"].get("qs") != review.get("qs"):
    raise SheetError(f"the sheet is for QS {book['meta'].get('qs')!r}, the review file for {review.get('qs')!r}")
  by_key = {m["key"]: m for m in review.get("mappings") or []}
  known = {i.id for i in CL.items()}
  confirmed = rejected = skipped_rows = left = 0
  
  refused, rejects = [], []
  for r in book["rows"]:
    m = by_key.get(r["key"])
    if m is None:
      refused.append(f"{r['key']}: not in the review file any more; export a new sheet")
      continue
    if r["decision"] == "":
      left += 1
      continue
    if r["decision"] not in DECISIONS:
      refused.append(f"{r['key']}: decision {r['decision']!r} is not one of {', '.join(DECISIONS)}")
      continue
    
    proposed = m.get("proposed", m.get("element"))
    if r["decision"] == NOT_ITEM:
      if not r["note"]:
        refused.append(f"{r['key']}: 'not an item' needs a note saying why")
        continue
      m.update({"confirmed": True, "skip": True, "note": r["note"], "confirmed_by": by.strip(), "confirmed_date": today})
      if proposed in known:
        m["rejected"] = True
        rejected += 1
        rejects.append({"key": r["key"], "qs_line": m.get("qs_line"), "proposed": proposed, "mapped_by": m.get("mapped_by"), "right": "not an item"})
      skipped_rows += 1
      confirmed += 1
      continue
    
    if r["decision"] == ACCEPT:
      if proposed not in known:
        refused.append(f"{r['key']}: nothing was proposed, so there is nothing to accept")
        continue
      element = proposed
    else:
      element = r["item"]
      if element not in known:
        refused.append(f"{r['key']}: {element or 'no item'!r} is not a catalogue item")
        continue
    m.update({"confirmed": True, "element": element, "proposed": proposed, "confirmed_by": by.strip(), "confirmed_date": today})
    m.pop("skip", None)
    if r["floor"]:
      m["floor"] = r["floor"]
    if proposed in known and element != proposed:
      m["rejected"] = True
      rejected += 1
      rejects.append({"key": r["key"], "qs_line": m.get("qs_line"), "proposed": proposed, "mapped_by": m.get("mapped_by"), "right": element})
    confirmed += 1
    
  res = {"qs": review.get("qs"), "confirmed": confirmed, "rejected": rejected, "not_items": skipped_rows, "left": left, "refused": refused, "rejects": rejects, "folded": None}
  if write and confirmed:
    AN.write_yaml(review_path(case_name), review)
    log_path = os.path.join(QM.case_paths(case_name, None)["folder"], REJECTED)
    log = AN.read_yaml(log_path) or {"rejected": []}
    seen = {x["key"] for x in log["rejected"]}
    log["rejected"] += [dict(x, by=by.strip(), date=today) for x in rejects if x["key"] not in seen]
    AN.write_yaml(log_path, log)
    res["folded"] = QM.run_fold(case_name, None)
  return res

def rejected_of(case_name: str) -> list:
  log = AN.read_yaml(os.path.join(QM.case_paths(case_name, None)["folder"], REJECTED)) or {}
  return list(log.get("rejected") or [])

def cmd_export(args) -> int:
  try:
    res = export(args.case, args.out)
  except SheetError as exc:
    print(f"refused: {exc}")
    return 1
  print(f"{res['lines']} mapping(s) for QS {res['qs']} -> {res['path']}")
  return 0

def cmd_import(args) -> int:
  try:
    res = apply(args.case, args.workbook, args.by, args.write)
  except SheetError as exc:
    print(f"refused: {exc}")
    return 1
  print(f"QS {res['qs']}: {res['confirmed']} line(s) confirmed ({res['rejected']} where the proposal was changed, {res['not_items']} not catalogue items), {res['left']} left unconfirmed")
  for x in res["rejects"]:
    print(f"  rejected: {x['key']}: proposed {x['proposed']} by {x['mapped_by']}, right is {x['right']}")
  for x in res["refused"]:
    print(f"  not applied: {x}")
  if not args.write:
    print("nothing written; add --write to record the confirmations and fold them into qs_map.yaml")
  elif res["folded"]:
    f = res["folded"]
    print(f"folded into qs_map.yaml: {f['added']} mapping(s), the map for {f['qs']} now holds {f['size']}; run `qs_map map {args.case}` again to rebuild answers.yaml with them")
  return 1 if res["refused"] else 0

def cmd_rejected(args) -> int:
  rows = rejected_of(args.case)
  for x in rows:
    print(f"{x['key']}: proposed {x['proposed']} by {x['mapped_by']}, right is {x['right']} (confirmed by {x['by']})")
  print(f"{len(rows)} proposal(s) rejected for {args.case}")
  return 0
