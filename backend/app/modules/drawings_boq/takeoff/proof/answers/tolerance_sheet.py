from __future__ import annotations
import argparse
import datetime
import os
import sys
from app.modules.drawings_boq.takeoff.proof.answers import answers as AN
from app.engine.catalogue import tolerances as TOL
from app.engine.catalogue import loader as CL
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.proof.bench import rates as RT
from app.modules.drawings_boq.takeoff.proof.bench import sets as ST

HERE = os.path.dirname(os.path.abspath(__file__))
SUGGEST = os.path.join(HERE, "tolerance_suggest.yaml")
SHEET, META, KIND = "Tolerances", "_meta", "tolerances"
HEAD = ["Item", "Name", "Section", "Unit", "Tolerance now %", "Suggested %", "Tolerance % (his)", "Share of cost % (top 20 only)", "Note"]
FIXED = len(HEAD) - 3
SUGGESTED, DEFAULT = ("s", "suggested"), "default"

class SheetError(Exception):
  pass

def suggestions() -> dict:
  return AN.read_yaml(SUGGEST) or {}

def suggestion_problems(doc: dict | None = None) -> list:
  doc = suggestions() if doc is None else doc
  out = []
  classes = doc.get("classes") or {}
  for k, v in classes.items():
    if not TOL._pct_ok(v):
      out.append(f"tolerance_suggest.yaml: class {k} must be a number above 0 and at most {TOL.MAX_PCT:g}")
  sections = doc.get("sections") or {}
  for sec in sorted({i.section for i in CL.items()} - set(sections)):
    out.append(f"tolerance_suggest.yaml: section {sec!r} has no class")
  for sec, cls in sections.items():
    if cls not in classes:
      out.append(f"tolerance_suggest.yaml: section {sec!r} names class {cls!r}, which is not one of {', '.join(classes)}")
  return out

def suggested_for(section: str, doc: dict) -> float:
  return float(doc["classes"][doc["sections"][section]])

def case_names() -> list:
  doc = ST.load()
  return [n for n, m in sorted(doc["sets"].items()) if not m.get("audit") and os.path.isfile(os.path.join(CIO.HERE, n, AN.FILE))]

def quantities(names: list) -> dict:
  out: dict = {}
  for name in names:
    for it in (AN.load(os.path.join(CIO.HERE, name)) or {}).get("items") or []:
      slot = out.setdefault(it["element"], {}).setdefault(name, {"quantity": 0.0, "unit": it.get("unit")})
      slot["quantity"] += float(it["quantity"])
  return out

def export(out_dir: str, names: list | None = None) -> dict:
  from openpyxl import Workbook
  from openpyxl.styles import Alignment, Font
  names = names or case_names()
  bad = suggestion_problems()
  if bad:
    raise SheetError("; ".join(bad[:3]))
  if not names:
    raise SheetError("no set has an answers.yaml; map a workbook first (qs_map map <case>)")

  sug = suggestions()
  qty = quantities(names)
  rows = [i for i in CL.items() if i.id in qty]
  wb = Workbook()
  ws = wb.active
  ws.title = SHEET
  ws.append(HEAD[:FIXED] + [f"Quantity in {n}" for n in names] + HEAD[FIXED:])
  for c in ws[1]:
    c.font = Font(bold=True)
  wrap = Alignment(wrap_text=True, vertical="top")
  
  for it in rows:
    now, _basis = TOL.pct_for(it.id)
    got = qty[it.id]
    ws.append([it.id, it.name, it.section, it.unit, now, suggested_for(it.section, sug)] + [f"{got[n]['quantity']:,.2f} {got[n]['unit']}" if n in got else None for n in names] + [None, None, None])
    for c in ws[ws.max_row]:
      c.alignment = wrap
  for col, width in zip("ABCDEF", (9, 48, 34, 7, 10, 10)):
    ws.column_dimensions[col].width = width
  ws.freeze_panes = "C2"
  hint = wb.create_sheet("Read me", 0)
  
  for line in (f"Tolerance per catalogue item for the sets {', '.join(names)} ({len(rows)} items with a quantity in at least one of them).",
    "Tolerance % (his): how far, in percent, Trace's quantity may be from the workbook's and still count as right. Leave it empty to keep the default (10%).",
    "Type s (or suggested) to take the Suggested % of that row; type default to put an item back on the default; or type your own figure above 0 and at most 100.",
    "Share of cost %: only for the 20 items that carry most of the money in a typical 10-marla house. Leave every other row empty; at most 20 rows.",
    "Trace's own results never set a figure here. Nothing is recorded until the sheet is imported with your name.",
    "Then run: python -m app.modules.drawings_boq.takeoff.proof.answers.tolerance_sheet import <this file> --by \"<your name>\" --house \"<the house the shares are for>\" [--write]"):
    hint.append([line])
    
  hint.column_dimensions["A"].width = 150
  meta = wb.create_sheet(META)
  meta.sheet_state = "hidden"
  for k, v in (("kind", KIND), ("sets", ",".join(names)), ("items", len(rows))):
    meta.append([k, v])
  os.makedirs(out_dir, exist_ok=True)
  path = os.path.join(out_dir, "tolerances.xlsx")
  wb.save(path)
  return {"path": path, "items": len(rows), "sets": names}

def _number(cell, label: str, item: str) -> float:
  try:
    v = float(str(cell).strip().rstrip("%"))
  except ValueError:
    raise SheetError(f"{item}: {label} {cell!r} is not a number")
  if not TOL._pct_ok(v):
    raise SheetError(f"{item}: {label} {v:g} must be above 0 and at most {TOL.MAX_PCT:g}")
  return v

def read(path: str) -> dict:
  from openpyxl import load_workbook
  wb = load_workbook(path, data_only=True)
  if SHEET not in wb.sheetnames or META not in wb.sheetnames:
    raise SheetError("this is not a tolerance sheet made by `tolerance_sheet export`")
  meta = {str(r[0]): r[1] for r in wb[META].iter_rows(values_only=True) if r[0] is not None}
  if meta.get("kind") != KIND:
    raise SheetError("this is not a tolerance sheet made by `tolerance_sheet export`")

  head = [c.value for c in next(wb[SHEET].iter_rows(min_row=1, max_row=1))]
  col = {name: n for n, name in enumerate(head)}
  rows = []
  for r in wb[SHEET].iter_rows(min_row=2, values_only=True):
    if r[0] is None:
      continue
    rows.append({"item": str(r[0]).strip().upper(), "section": r[col["Section"]], "suggested": r[col["Suggested %"]], "tolerance": r[col["Tolerance % (his)"]], "share": r[col["Share of cost % (top 20 only)"]]})
  return {"meta": meta, "rows": rows}

def apply(path: str, by: str, house: str | None, write: bool, today: str | None = None) -> dict:
  if not by or not by.strip():
    raise SheetError("--by must name the QS who gave the figures; a figure with no name is not confirmed")
  today = today or datetime.date.today().isoformat()
  book = read(path)
  known = {i.id for i in CL.items()}
  have = TOL._load()
  per = dict(have.get("per_item") or {})
  if per and have.get("confirmed_by") and have["confirmed_by"] != by.strip():
    raise SheetError(f"tolerances.yaml holds figures confirmed by {have['confirmed_by']!r}; one QS owns the file, so {by.strip()!r} cannot add to it")

  set_n = dropped = 0
  shares: dict = {}
  for r in book["rows"]:
    if r["item"] not in known:
      raise SheetError(f"{r['item']} is not a catalogue item")
    cell = r["tolerance"]
    if cell not in (None, ""):
      word = str(cell).strip().lower()
      if word == DEFAULT:
        if per.pop(r["item"], None) is not None:
          dropped += 1
      else:
        per[r["item"]] = float(r["suggested"]) if word in SUGGESTED else _number(cell, "tolerance", r["item"])
        set_n += 1
    if r["share"] not in (None, ""):
      shares[r["item"]] = _number(r["share"], "share of cost", r["item"])
      
  if len(shares) > RT.TOP:
    raise SheetError(f"{len(shares)} shares given; the sheet takes the top {RT.TOP} items only")
  if shares and not (house or "").strip():
    raise SheetError("--house must say which house the shares are for (for example '10-marla house')")
  doc = {"default_pct": have["default_pct"], "confirmed_by": by.strip() if per else None, "confirmed_date": today if per else None, "per_item": dict(sorted(per.items()))}
  bad = TOL.problems(doc)
  if bad:
    raise SheetError("; ".join(bad[:3]))

  res = {"set": set_n, "dropped": dropped, "per_item": len(per), "shares": len(shares), "written": False}
  if write and (set_n or dropped):
    AN.write_yaml(TOL.PATH, doc)
    TOL.reload()
    res["written"] = True
  if write and shares:
    AN.write_yaml(RT.SHARES, {"house": house.strip(), "confirmed_by": by.strip(), "confirmed_date": today, "shares": dict(sorted(shares.items()))})
    res["written"] = True
  return res

def cmd_export(a) -> int:
  try:
    r = export(a.out, a.cases)
  except SheetError as exc:
    print(f"refused: {exc}")
    return 1
  print(f"{r['items']} item(s) from {', '.join(r['sets'])} -> {r['path']}")
  return 0

def cmd_import(a) -> int:
  try:
    r = apply(a.workbook, a.by, a.house, a.write)
  except SheetError as exc:
    print(f"refused: {exc}")
    return 1
  print(f"tolerances: {r['set']} set, {r['dropped']} put back on the default, {r['per_item']} item(s) now carry a figure; money shares: {r['shares']}")
  print("written to tolerances.yaml and money_shares.yaml" if r["written"] else "nothing written; add --write to record them with the QS's name and the date")
  return 0

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Tolerance sheet for the QS (one row per catalogue item with a quantity in a mapped workbook) and the import of his figures into tolerances.yaml and money_shares.yaml.")
  sub = ap.add_subparsers(dest="cmd", required=True)
  ex = sub.add_parser("export")
  ex.add_argument("--out", default="mapping_out")
  ex.add_argument("--cases", nargs="*", help="case names (default: every set with an answers.yaml)")
  im = sub.add_parser("import")
  im.add_argument("workbook")
  im.add_argument("--by", required=True)
  im.add_argument("--house")
  im.add_argument("--write", action="store_true")
  a = ap.parse_args(argv)
  return {"export": cmd_export, "import": cmd_import}[a.cmd](a)

if __name__ == "__main__":
  sys.exit(main())
