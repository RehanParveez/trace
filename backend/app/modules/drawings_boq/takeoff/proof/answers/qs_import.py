from __future__ import annotations
import argparse
import hashlib
import os
import re
import sys
import warnings
import yaml
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.run import known_facts as KF

HERE = os.path.dirname(os.path.abspath(__file__))
VOCAB_PATH = os.path.join(HERE, "columns.yaml")

MEASURED, SUBTOTAL, GROUP, NO_QUANTITY = "MEASURED", "SUBTOTAL", "GROUP", "NO_QUANTITY"
DETAIL, SUMMARY, BILL_ITEM = "DETAIL", "SUMMARY", "BILL_ITEM"
DIMENSIONS = ("count", "length", "width", "thick")
ROLE_ORDER = ("serial", "description", "unit", "count", "length", "width", "thick", "quantity", "remarks")
FLOOR_FILLER = {"FLOOR", "FLOORS", "LEVEL", "THE", "OF", "FF"}
TOTAL_TOLERANCE = 1e-6

def vocabulary(path: str = VOCAB_PATH) -> dict:
  with open(path, encoding="utf-8") as fh:
    return yaml.safe_load(fh)

def header_text(value) -> str:
  t = str(value if value is not None else "").lower().replace("\n", " ").replace("'", "")
  t = re.sub(r"\([^)]*\)", " ", t)
  t = re.sub(r"[.#/:~_]", " ", t)
  return re.sub(r"\s+", " ", t).strip()

def unit_in_header(value) -> str | None:
  m = re.search(r"\(([^)]*)\)", str(value or ""))
  return m.group(1).strip() if m else None

def number(value) -> float | None:
  if isinstance(value, bool) or value is None:
    return None
  if isinstance(value, (int, float)):
    return float(value)
  return None

def text(value) -> str:
  return re.sub(r"\s+", " ", str(value).replace("\n", " ")).strip() if value is not None and not isinstance(value, (int, float)) else ""

def floor_words(vocab: dict) -> dict:
  words = {k: v for k, v in KF.FLOOR_WORDS.items() if len(k) > 1 and k != "TYPICAL"}
  words.update(vocab.get("floor_extra") or {})
  return words

def clean_floor_text(raw: str) -> str:
  t = str(raw or "").upper()
  t = re.sub(r"\b([A-Z])\.\s?([A-Z])\b\.?", r"\1\2", t)
  t = re.sub(r"([A-Z]+)\.\s*F\b", r"\1F", t)
  return t

def floor_of_group(raw: str, vocab: dict) -> str | None:
  words = floor_words(vocab)
  tokens = [t for t in re.findall(r"[A-Z]+", clean_floor_text(raw)) if t not in FLOOR_FILLER]
  if not tokens or any(t not in words for t in tokens):
    return None
  return words[tokens[0]]

def floor_at_start(raw: str, vocab: dict) -> str | None:
  words = floor_words(vocab)
  tokens = re.findall(r"[A-Z]+", clean_floor_text(raw))
  return words.get(tokens[0]) if tokens else None

def floor_in_brackets(raw: str, vocab: dict) -> str | None:
  for inner in re.findall(r"\(([^)]*)\)", str(raw or "")):
    got = floor_of_group(inner, vocab)
    if got:
      return got
  return None

def floor_of_sheet_name(name: str, vocab: dict) -> str | None:
  m = re.search(r"[_\s]([A-Za-z]\.?[A-Za-z])\.?\s*$", str(name or ""))
  if not m:
    return None
  return floor_words(vocab).get(clean_floor_text(m.group(1)).replace(".", ""))

def unit_of(raw, vocab: dict) -> str | None:
  t = header_text(raw)
  if not t:
    return None
  for canon, spellings in (vocab.get("units") or {}).items():
    if t in spellings:
      return canon
  return t

def roles_of(row: list, vocab: dict) -> dict:
  found: dict = {}
  for col, v in enumerate(row):
    if v is None or isinstance(v, (int, float)):
      continue
    h = header_text(v)
    for role in ROLE_ORDER:
      if h in (vocab["roles"].get(role) or []) and role not in found.values():
        found[col] = role
        break
  return found

def floor_columns(row: list, taken: set, vocab: dict) -> dict:
  out: dict = {}
  others = set(vocab.get("others_words") or [])
  for col, v in enumerate(row):
    if col in taken or v is None or isinstance(v, (int, float)):
      continue
    h = header_text(v)
    if h in others:
      out[col] = None
      continue
    f = floor_of_group(str(v), vocab)
    if f:
      out[col] = f
  return out

def find_header(rows: list, start: int, vocab: dict) -> tuple | None:
  for i in range(start, len(rows)):
    roles = roles_of(rows[i], vocab)
    if "description" not in roles.values():
      continue
    floors = floor_columns(rows[i], set(roles), vocab)
    if ("quantity" in roles.values() or len(floors) >= 2) and len(roles) + len(floors) >= 3:
      return i, roles, floors
  return None

def item_marker(row: list, vocab: dict) -> str | None:
  markers = vocab.get("item_markers") or []
  for col, v in enumerate(row):
    if v is None or isinstance(v, (int, float)):
      continue
    raw = str(v)
    head, sep, tail = raw.partition(":")
    if sep and header_text(head) in markers:
      value = text(tail)
      if value:
        return value
      for nxt in row[col + 1:]:
        if nxt not in (None, "") and not isinstance(nxt, (int, float)):
          return text(nxt)
  return None

def layout_of(roles: dict, floors: dict) -> str:
  if floors and "quantity" not in roles.values():
    return "FLOOR_COLUMNS"
  return "MEASUREMENT" if any(r in DIMENSIONS for r in roles.values()) else "BILL"

def read_sheet(name: str, grid: list, vocab: dict, block_floor: dict | None = None) -> dict:
  blocks = {re.sub(r"\s+", " ", str(k).upper()).strip(): v for k, v in (block_floor or {}).items()}
  out = {"sheet": name, "header_row": None, "layout": None, "title": None, "rows": [], "with_quantity": 0, "problems": []}
  first = find_header(grid, 0, vocab)
  if first is None:
    out["layout"] = "NONE"
    return out
  
  head_i, roles, floors = first
  out["header_row"] = head_i + 1
  out["layout"] = layout_of(roles, floors)
  col_of = {role: col for col, role in roles.items()}
  qty_unit = unit_in_header(grid[head_i][col_of["quantity"]]) if "quantity" in col_of else None
  item = None
  for i in range(head_i):
    item = item_marker(grid[i], vocab) or item
    if out["title"] is None:
      first_text = next((text(v) for v in grid[i] if text(v)), "")
      if first_text and not item_marker(grid[i], vocab):
        out["title"] = first_text
        
  sheet_floor = floor_of_sheet_name(name, vocab)
  item_floor = floor_in_brackets(item, vocab) if item else None
  floor_ctx = None
  groups: list = []
  fresh = True
  last_desc = ""
  last_unit = None
  base = {"sheet": name}

  def add_group(label: str):
    nonlocal groups, floor_ctx, fresh
    f = floor_of_group(label, vocab) or blocks.get(re.sub(r"\s+", " ", label.upper()).strip())
    if f:
      floor_ctx = f
    else:
      groups = (groups + [label]) if (fresh or not groups) else (groups[:-1] + [label])
      groups = groups[-2:]
    fresh = True

  def put(kind: str, r: int, **kw):
    rec = {**base, "row": r + 1, "kind": kind, "item": item, "groups": list(groups), **kw}
    out["rows"].append(rec)
    return rec

  for r in range(head_i + 1, len(grid)):
    row = grid[r]
    again = find_header(grid[r:r + 1], 0, vocab)
    if again is not None and again[1] == roles:
      continue
    marker = item_marker(row, vocab)
    if marker:
      item, item_floor, groups, fresh, floor_ctx = marker, floor_in_brackets(marker, vocab), [], True, None
      continue

    def cell(role: str):
      return row[col_of[role]] if role in col_of and col_of[role] < len(row) else None
    desc, serial = text(cell("description")), cell("serial")
    unit_raw = text(cell("unit"))
    dims = {d: number(cell(d)) for d in DIMENSIONS if d in col_of}
    has_dims = any(v is not None for v in dims.values())
    qty = number(cell("quantity"))
    remark = number(cell("remarks"))
    serial_text = text(serial)
    serial_is_number = number(serial) is not None

    if floors:
      cells = {col: number(row[col]) for col in floors if col < len(row) and number(row[col]) is not None}
      if cells:
        out["with_quantity"] += 1
        unit = unit_of(unit_raw, vocab) or last_unit
        if desc:
          last_desc = desc
        for col, q in cells.items():
          put(MEASURED, r, description=desc or last_desc, unit=unit, floor=floors[col], quantity=q, dims={}, serial=serial_text or None)
        continue
      
    elif qty is not None:
      out["with_quantity"] += 1
      label = desc or serial_text
      if not desc and not serial_is_number and not serial_text and not unit_raw and not has_dims:
        put(SUBTOTAL, r, description="", unit=None, floor=None, quantity=qty, dims={})
        continue
      if re.search(r"\btotal\b", label.lower()) and not has_dims and not unit_raw:
        put(SUBTOTAL, r, description=label, unit=None, floor=None, quantity=qty, dims={})
        continue
      if (desc or serial_text and not serial_is_number) and not unit_raw and not has_dims and qty == 0:
        add_group(label)
        put(GROUP, r, description=label, unit=None, floor=floor_ctx, quantity=0.0, dims={})
        continue
      
      unit = unit_of(unit_raw, vocab) or (unit_of(qty_unit, vocab) if qty_unit else None) or last_unit
      if desc:
        last_desc = desc
      if unit_raw:
        last_unit = unit
      d = desc or last_desc
      floor = floor_at_start(d, vocab) if desc and floor_at_start(d, vocab) and len(desc) > 4 and floor_of_group(desc, vocab) is None else None
      fl = floor or floor_ctx or item_floor or sheet_floor
      put(MEASURED, r, description=d, unit=unit, floor=fl, quantity=qty, dims={k: v for k, v in dims.items() if v is not None}, serial=serial_text or None, remarks=text(cell("remarks")) or None, block_total=remark, inherited_description=not desc)
      fresh = False
      continue
    
    if remark is not None and not desc and not serial_text and not unit_raw and not has_dims:
      out["with_quantity"] += 1
      put(SUBTOTAL, r, description="", unit=None, floor=None, quantity=remark, dims={}, in_remarks=True)
      continue
    label = desc or (serial_text if not serial_is_number else "")
    if label and not unit_raw and not has_dims:
      add_group(label)
      put(GROUP, r, description=label, unit=None, floor=floor_ctx, quantity=None, dims={})
      continue
    if desc and unit_raw and qty is None:
      put(NO_QUANTITY, r, description=desc, unit=unit_of(unit_raw, vocab), floor=floor_ctx or item_floor or sheet_floor, quantity=None, dims={})
  return out

def classify(sheet: dict, has_detail: bool) -> str:
  if sheet["layout"] == "MEASUREMENT":
    return DETAIL
  return SUMMARY if has_detail else BILL_ITEM

def lost_rows(sheet: dict) -> int:
  read = sum(1 for r in sheet["rows"] if r["kind"] in (MEASURED, SUBTOTAL) or (r["kind"] == GROUP and r["quantity"] == 0.0))
  if sheet["layout"] == "FLOOR_COLUMNS":
    read = len({r["row"] for r in sheet["rows"] if r["kind"] in (MEASURED,)}) + sum(1 for r in sheet["rows"] if r["kind"] == SUBTOTAL)
  return sheet["with_quantity"] - read

def load_grids(path: str) -> list:
  import openpyxl
  with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    data = openpyxl.load_workbook(path, data_only=True)
    forms = openpyxl.load_workbook(path, data_only=False)
  out = []
  for ws in data.worksheets:
    grid = [[c for c in row] for row in ws.iter_rows(values_only=True)]
    uncached = 0
    fw = forms[ws.title]
    for r_i, row in enumerate(fw.iter_rows(values_only=True)):
      for c_i, v in enumerate(row):
        if isinstance(v, str) and v.startswith("=") and (r_i >= len(grid) or c_i >= len(grid[r_i]) or grid[r_i][c_i] is None):
          uncached += 1
    out.append((ws.title, grid, uncached))
  return out

def sha256_of(path: str) -> str:
  with open(path, "rb") as fh:
    return hashlib.sha256(fh.read()).hexdigest()

def read_workbook(path: str, block_floor: dict | None = None, vocab: dict | None = None) -> dict:
  vocab = vocab or vocabulary()
  sheets = []
  for name, grid, uncached in load_grids(path):
    s = read_sheet(name, grid, vocab, block_floor)
    if uncached:
      s["problems"].append(f"{uncached} formula cell(s) have no stored value; open the workbook in Excel and save it")
    sheets.append(s)
  has_detail = any(s["layout"] == "MEASUREMENT" and s["rows"] for s in sheets)
  rows: list = []
  for s in sheets:
    s["role"] = classify(s, has_detail) if s["layout"] not in (None, "NONE") else None
    for r in s["rows"]:
      r["role"] = s["role"]
      rows.append(r)
  return {"workbook": os.path.basename(path), "sha256": sha256_of(path), "sheets": sheets, "rows": rows, "has_detail": has_detail}

def blocks_of(sheet_rows: list) -> list:
  out: list = []
  cur: list = []
  totals: list = []
  for r in sheet_rows:
    if r["kind"] == MEASURED:
      if totals:
        out.append((cur, totals))
        cur, totals = [], []
      cur.append(r)
      if r.get("block_total") is not None:
        totals.append({"row": r["row"], "quantity": r["block_total"]})
    elif r["kind"] == SUBTOTAL:
      totals.append({"row": r["row"], "quantity": r["quantity"]})
  if cur:
    out.append((cur, totals))
  return out

def totals_check(imp: dict) -> list:
  out: list = []
  for s in imp["sheets"]:
    if s["role"] != DETAIL:
      continue
    for rows, totals in blocks_of(s["rows"]):
      if not totals or not rows:
        continue
      got = sum(r["quantity"] for r in rows)
      if any(abs(got - t["quantity"]) <= TOTAL_TOLERANCE * max(1.0, abs(t["quantity"])) for t in totals):
        continue
      t = next((x for x in totals if x["quantity"]), totals[0])
      out.append({"sheet": s["sheet"], "rows": f"{rows[0]['row']}-{rows[-1]['row']}", "total_row": t["row"], "summed": got, "workbook": t["quantity"], "difference": got - t["quantity"]})
  return out

def summary_lines(imp: dict) -> list:
  return [r for r in imp["rows"] if r["role"] == SUMMARY and r["kind"] == MEASURED]

def counts(imp: dict) -> dict:
  out = {"sheets": len(imp["sheets"]), "rows": len(imp["rows"]), "measured": 0, "subtotal": 0, "group": 0, "no_quantity": 0, "with_quantity": sum(s["with_quantity"] for s in imp["sheets"]), "lost": sum(lost_rows(s) for s in imp["sheets"])}
  for r in imp["rows"]:
    out[{MEASURED: "measured", SUBTOTAL: "subtotal", GROUP: "group", NO_QUANTITY: "no_quantity"}[r["kind"]]] += 1
  return out

def case_workbook(case_name: str, cases_dir: str | None = None) -> tuple:
  folder = os.path.join(CIO.HERE, case_name)
  case = CIO.load_case(folder)
  wb = case.get("workbook") or {}
  files = CIO.cases_dir(cases_dir)
  path = os.path.join(files, wb.get("path") or "")
  return case, path, case.get("block_floor") or {}

def lines_of(imp: dict) -> list:
  out = [f"{imp['workbook']}: {len(imp['sheets'])} sheets, {'measurement sheets with summary sheets' if imp['has_detail'] else 'bill sheets'}"]
  for s in imp["sheets"]:
    n = sum(1 for r in s["rows"] if r["kind"] == MEASURED)
    out.append(f"  {s['sheet']!r}: {s['layout'] or 'NONE'} {s['role'] or '-'}, header row {s['header_row'] or '-'}, {n} measured rows, {s['with_quantity']} rows with a quantity, {lost_rows(s)} lost" + (f"; {'; '.join(s['problems'])}" if s["problems"] else ""))
  c = counts(imp)
  out.append(f"  rows with a quantity {c['with_quantity']}; read as measured {c['measured']}, sub-total {c['subtotal']}, group with zero {sum(1 for r in imp['rows'] if r['kind'] == GROUP and r['quantity'] == 0.0)}; lost {c['lost']}; lines with no quantity {c['no_quantity']}")
  for d in totals_check(imp):
    out.append(f"  TOTAL DIFFERS {d['sheet']!r} rows {d['rows']}: summed {d['summed']:.4f}, workbook says {d['workbook']:.4f} (row {d['total_row']}), difference {d['difference']:.4f}")
  return out

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Read a QS workbook into one record per row and print what was read and every total that differs from the workbook's own.")
  ap.add_argument("case", nargs="?", help="a case name whose case.yaml names the workbook")
  ap.add_argument("--workbook", help="a workbook path, instead of a case")
  ap.add_argument("--cases-dir", default=None)
  args = ap.parse_args(argv)
  
  if args.workbook:
    imp = read_workbook(args.workbook)
  elif args.case:
    _case, path, block_floor = case_workbook(args.case, args.cases_dir)
    if not os.path.isfile(path):
      print(f"{args.case}: the workbook is not at {path}.", file=sys.stderr)
      return 2
    imp = read_workbook(path, block_floor)
  else:
    ap.error("give a case name or --workbook")
  for ln in lines_of(imp):
    print(ln)
  return 0 if counts(imp)["lost"] == 0 else 1

if __name__ == "__main__":
  sys.exit(main())
