from __future__ import annotations
import argparse
import json
import os
import sys
import tempfile
import time
import yaml

MOVE_PCT = 0.05
EXTENT_ITEMS = ("termite", "pcc_floor", "fill", "ceiling")
EXTENT_MODES = ("FLOOR_AREA", "GROSS", "STRIPS", "ROOMS")
EXTENT_TEXT = {"FLOOR_AREA": "over the floors inside the walls (the usual way)", "GROSS": "over the floors plus the plan area of the walls between them",
  "STRIPS": "as strips along the walls, with the strip widths of the rules", "ROOMS": "over the rooms of the types the rule lists (finish.pcc_under, finish.ceiling_includes)"}
ITEM_TEXT = {"termite": "Termite proofing", "pcc_floor": "PCC under the floor", "fill": "Earth filling under the floor", "ceiling": "Ceiling plaster"}

def _groups() -> list:
  out = []
  for item in EXTENT_ITEMS:
    out.append({"id": f"extent.{item}", "question": f"{ITEM_TEXT[item]}: over what extent", "key": "finish.extent", "scope": {"item": item},
      "methods": [{"label": EXTENT_TEXT[m], "value": m} for m in EXTENT_MODES]})
  out.append({"id": "wall_height", "question": "Height of a brick wall", "key": "wall_height_basis", "scope": {},
    "methods": [{"label": "floor to floor, as printed on the sections", "value": "FLOOR_TO_FLOOR"}, {"label": "clear storey height, floor to the soffit of the slab above", "value": "CLEAR"},
      {"label": "floor to floor less the plinth beam, on the lowest storey", "value": "ABOVE_PLINTH_BEAM"}, {"label": "also less the web of the roof beam below the slab, on every storey", "value": "BETWEEN_BEAMS"}]})
  out.append({"id": "beam_depth", "question": "Depth of a beam", "key": "beam_depth_includes_slab", "scope": {},
    "methods": [{"label": "the printed depth includes the slab (the web is taken below the slab)", "value": 1.0}, {"label": "the printed depth is the web, below the slab", "value": 0.0}]})
  out.append({"id": "brick_lintels", "question": "Brick at a lintel", "key": "brick_net_of_lintels", "scope": {},
    "methods": [{"label": "net of the lintels over the openings", "value": 1.0}, {"label": "gross, the lintels not taken out", "value": 0.0}]})
  out.append({"id": "tie_band", "question": "A tie band at lintel level", "key": "tie_band_replaces_lintel", "scope": {},
    "methods": [{"label": "the lintels stay, a tie band is not counted instead", "value": 0.0}, {"label": "the tie band replaces the lintels", "value": 1.0}]})
  out.append({"id": "opening_rules", "question": "Which openings come off each item", "key": "opening_rules_basis", "scope": {},
    "methods": [{"label": "one rule for every item, as a QS sheet has it (0.5 m2 and over)", "value": "SHEET"}, {"label": "a rule for each item (IS 1200, assumed)", "value": "IS1200"}]})
  for item, text in (("brick", "brickwork"), ("plaster", "plaster"), ("paint", "paint")):
    out.append({"id": f"deduct.{item}", "question": f"Openings off the {text}", "key": f"deduct_opening_{item}", "scope": {},
      "methods": [{"label": "openings taken off", "value": 1.0}, {"label": "openings not taken off", "value": 0.0}]})
  out.append({"id": "dado_bath", "question": "Tile band in a bath", "key": "finish.dado_height_mm", "scope": {"room_type": "BATH"},
    "methods": [{"label": "7 ft (2134 mm)", "value": 2134.0}, {"label": "to the ceiling", "value": "CEILING"}]})
  out.append({"id": "wall_faces", "question": "Wall faces for plaster and paint", "key": "finish.wall_faces", "scope": {},
    "methods": [{"label": "from the outline of the rooms", "value": "OUTLINE"}, {"label": "from the wall graph", "value": "GRAPH"}]})
  out.append({"id": "stair_external", "question": "A stair outside the building", "key": "finish.stair_external", "scope": {},
    "methods": [{"label": "billed as its own line", "value": "BILL_SEPARATE"}, {"label": "counted with the stairs", "value": "WITH_STAIR"}, {"label": "left out", "value": "EXCLUDE"}]})
  return out

GROUPS = _groups()

def _same(a, b) -> bool:
  try:
    return float(a) == float(b)
  except (TypeError, ValueError):
    return str(a).strip().upper() == str(b).strip().upper()

def rules_with(base_path: str | None, key: str, scope: dict, value) -> str:
  raw = {"origin": "QS_WORKBOOK", "rules": []}
  if base_path and os.path.isfile(base_path):
    with open(base_path, encoding="utf-8") as fh:
      raw = yaml.safe_load(fh) or raw
      
  rows = [r for r in (raw.get("rules") or []) if not (r.get("key") == key and dict(r.get("scope") or {}) == dict(scope))]
  row = {"key": key, "value": value, "cls": "JUDGEMENT", "note": "method menu variant"}
  if scope:
    row["scope"] = dict(scope)
  rows.append(row)
  raw["rules"] = rows
  fd, path = tempfile.mkstemp(suffix=".yaml", prefix="menu_rules_")
  with os.fdopen(fd, "w", encoding="utf-8") as fh:
    yaml.safe_dump(raw, fh, sort_keys=False, allow_unicode=True)
  return path

def line_figures(doc: dict) -> dict:
  return {l["key"]: {"unit": l.get("unit"), "trace": l.get("trace"), "qs": l.get("qs")} for l in doc.get("lines") or [] if l.get("trace") is not None}

def effective(key: str, scope: dict):
  from app.engine.measure import rulebook as RB
  try:
    return RB.resolve(key, scope or None, record=False).value
  except Exception:
    return None

def run_variants(case_name: str, only: list | None, cases_dir: str | None, log=print) -> dict:
  from app.engine.measure import rulebook as RB
  from app.modules.drawings_boq.takeoff.proof import case_io as CIO
  from app.modules.drawings_boq.takeoff.proof import offline_run as OR
  from app.modules.drawings_boq.takeoff.proof import score as SC
  folder = os.path.join(CIO.HERE, case_name)
  case = CIO.load_case(folder)
  files, probs = CIO.find_files(case, CIO.cases_dir(cases_dir))
  
  if probs:
    raise SystemExit(f"{case_name}: {' '.join(probs)}")
  profile, rule_set = OR.seed_profile()
  catalog = OR.work_item_catalog()
  base_path = os.path.join(folder, case["company_rules"]) if case.get("company_rules") else None
  def one(path: str | None) -> dict:
    rows, problems = RB.load_rules(path) if path else ([], [])
    if problems:
      return {"error": " ".join(problems)}
    with RB.using_case(rows):
      doc, _ = SC.run_case(case, files, profile, rule_set, catalog, both=False, rules=None, keep={})
    return line_figures(doc)

  t0 = time.monotonic()
  result = {"case": case_name, "baseline": one(base_path), "groups": []}
  log(f"{case_name}: current rules {time.monotonic() - t0:.0f} s")
  base_rows, _ = RB.load_rules(base_path) if base_path else ([], [])
  for g in GROUPS:
    if only and not any(g["id"].startswith(o) for o in only):
      continue
    with RB.using_case(base_rows):
      now = effective(g["key"], g["scope"])
    entry = {"id": g["id"], "question": g["question"], "key": g["key"], "scope": g["scope"], "current": now, "methods": []}
    for m in g["methods"]:
      if _same(m["value"], now):
        entry["methods"].append({"label": m["label"], "value": m["value"], "is_current": True, "lines": None})
        continue
    
      path = rules_with(base_path, g["key"], g["scope"], m["value"])
      try:
        lines = one(path)
      finally:
        os.unlink(path)
      entry["methods"].append({"label": m["label"], "value": m["value"], "is_current": False, "lines": lines})
      log(f"  {g['id']} = {m['value']}: {time.monotonic() - t0:.0f} s")
    result["groups"].append(entry)
  return result

UNMOVED = "no line moved: the same figures as the current rule (the same by construction, or the rule could not be followed on this drawing)"

def moved_lines(base: dict, lines: dict | None) -> set:
  out = set()
  for key, v in (lines or {}).items():
    b = base.get(key)
    if b is None or v["trace"] is None or abs(float(v["trace"]) - float(b["trace"])) > abs(float(b["trace"])) * MOVE_PCT / 100.0 + 1e-9:
      out.add(key)
  return out

def table_rows(result: dict) -> list:
  base = result["baseline"]
  
  rows = []
  for g in result["groups"]:
    moved = set()
    for m in g["methods"]:
      if m["lines"] is None or "error" in m["lines"]:
        continue
      for key, v in m["lines"].items():
        b = base.get(key)
        if b is None or v["trace"] is None:
          moved.add(key)
        elif abs(float(v["trace"]) - float(b["trace"])) > abs(float(b["trace"])) * MOVE_PCT / 100.0 + 1e-9:
          moved.add(key)
      for key in base:
        if key not in m["lines"]:
          moved.add(key)
          
    for key in sorted(moved):
      for m in g["methods"]:
        if m["lines"] is None:
          src = base.get(key)
        elif "error" in m["lines"]:
          rows.append((g["question"], m["label"], key, None, None, False, m["lines"]["error"]))
          continue
        else:
          src = m["lines"].get(key)
        note = UNMOVED if (m["lines"] is not None and not moved_lines(base, m["lines"]) and not set(base) - set(m["lines"])) else ""
        rows.append((g["question"], m["label"], key, (src or base.get(key) or {}).get("unit"), None if src is None else src["trace"], m["lines"] is None, note))
  return rows

def write_xlsx(result: dict, path: str) -> int:
  import openpyxl
  from openpyxl.styles import Font
  wb = openpyxl.Workbook()
  ws = wb.active
  ws.title = "Menu"
  ws.append(["Question", "Method", "Line", "Unit", "Trace quantity", "Current rule", "Note"])
  
  for c in ws[1]:
    c.font = Font(bold=True)
  rows = table_rows(result)
  for q, m, line, unit, qty, cur, note in rows:
    ws.append([q, m, line, unit, None if qty is None else round(float(qty), 3), "yes" if cur else "", note])
  ws.freeze_panes = "A2"
  for col, w in zip("ABCDEFG", (44, 64, 28, 8, 16, 12, 40)):
    ws.column_dimensions[col].width = w
    
  rules = wb.create_sheet("Rules")
  rules.append(["Question", "Rule key", "Scope", "Value", "Method", "Value in the current rules"])
  for c in rules[1]:
    c.font = Font(bold=True)
  for g in result["groups"]:
    for m in g["methods"]:
      rules.append([g["question"], g["key"], json.dumps(g["scope"]), str(m["value"]), m["label"], str(g["current"])])
      
  base = wb.create_sheet("Current rules")
  base.append(["Line", "Unit", "Trace quantity"])
  for c in base[1]:
    c.font = Font(bold=True)
  for key, v in sorted(result["baseline"].items()):
    if isinstance(v, dict) and v.get("trace") is not None:
      base.append([key, v["unit"], round(float(v["trace"]), 3)])
  wb.save(path)
  return len(rows)

def check_text(result: dict) -> str:
  base = result["baseline"]
  out = [f"# Method menu check: {result['case']}\n", "For each line a question moves, the methods whose Trace quantity is within 5% of the QS's figure. Read as evidence of which method the workbook used, not as a rule to adopt.\n",
    "| Question | Line | QS | Methods within 5% of it | Current rule within 5% |", "|---|---|---|---|---|"]
  
  for g in result["groups"]:
    seen = set()
    for row in table_rows({"baseline": base, "groups": [g]}):
      seen.add(row[2])
    for key in sorted(seen):
      qs = (base.get(key) or {}).get("qs")
      if not qs:
        continue
    
      good, cur_ok = [], False
      for m in g["methods"]:
        src = base.get(key) if m["lines"] is None else (m["lines"].get(key) if "error" not in m["lines"] else None)
        if src is None or src.get("trace") is None:
          continue
        ok = abs(float(src["trace"]) - float(qs)) <= abs(float(qs)) * 0.05
        if ok:
          good.append(str(m["value"]) + (" (current)" if m["lines"] is None else ""))
        if ok and m["lines"] is None:
          cur_ok = True
      out.append(f"| {g['question']} | {key} | {float(qs):,.1f} | {'; '.join(good) or 'none'} | {'yes' if cur_ok else 'no'} |")
      
  return "\n".join(out) + "\n"

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Run a case under each standard method of the convention questions and write what Trace measures under each. The QS figure is not in the file.")
  ap.add_argument("case")
  ap.add_argument("--out", default="method_menu_out")
  ap.add_argument("--only", help="comma list of question ids (or their starts) to run, such as extent,wall_height")
  ap.add_argument("--cases-dir")
  ap.add_argument("--check", action="store_true", help="also write the check file that sets each method beside the QS figure of the case")
  ap.add_argument("--from-json", dest="from_json", help="write the files again from a method_menu_<case>.json of an earlier run, without running the case")
  ap.add_argument("--list", action="store_true", help="print the questions and methods and stop")
  a = ap.parse_args(argv)
  if a.list:
    for g in GROUPS:
      print(f"{g['id']}: {g['question']} ({g['key']} {g['scope'] or ''})")
      for m in g["methods"]:
        print(f"    {m['value']}: {m['label']}")
    return 0
  os.makedirs(a.out, exist_ok=True)
  
  if a.from_json:
    with open(a.from_json, encoding="utf-8") as fh:
      result = json.load(fh)
  else:
    result = run_variants(a.case, [s for s in (a.only or "").split(",") if s] or None, a.cases_dir)
  if not a.from_json:
    with open(os.path.join(a.out, f"method_menu_{a.case}.json"), "w", encoding="utf-8") as fh:
      json.dump(result, fh, indent=1, default=str)
  n = write_xlsx(result, os.path.join(a.out, f"method_menu_{a.case}.xlsx"))
  print(f"{a.case}: {len(result['groups'])} questions, {n} rows in method_menu_{a.case}.xlsx")
  if a.check:
    with open(os.path.join(a.out, f"method_menu_check_{a.case}.md"), "w", encoding="utf-8") as fh:
      fh.write(check_text(result))
  return 0

if __name__ == "__main__":
  sys.exit(main())
