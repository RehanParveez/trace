from __future__ import annotations
import argparse
import collections
import os
import sys

TOGGLES = {
  "deduct_opening_plaster": ("FIN-PLASTER", "FIN-PLASTER-EXT", "FIN-PLASTER-MORTAR"),
  "deduct_opening_paint": ("FIN-PAINT", "FIN-PAINT-EXT"),
  "deduct_opening_brick": ("MAS-BRICK",),
  "derived_scaffold": ("SCF-EXTERNAL",),
  "derived_props": ("FRM-PROPS",),
}
PLASTER_ITEMS = ("PLASTER_INSIDE", "PLASTER_OUTSIDE")
AREA_TOL_M2 = 0.01

def _totals(ledger: list) -> dict:
  out: dict = collections.defaultdict(float)
  for r in ledger:
    out[(r.get("work_item_code"), r.get("unit"))] += float(r.get("quantity") or 0.0)
  return out

def _run(case: dict, files: dict, rows: list, profile, rule_set, catalog) -> tuple:
  from app.engine.measure import rulebook as RB
  from app.modules.drawings_boq.takeoff.proof import score as S
  keep: dict = {}
  with RB.using_case(rows):
    S.run_case(case, files, profile, rule_set, catalog, both=False, keep=keep)
  return keep["ledger"], keep["accs"]

def _deducted_m2(accs: list) -> float:
  total = 0.0
  for acc in accs:
    for c in acc.candidates:
      f = c.facts or {}
      if c.decision == "ACCEPTED" and f.get("foundation_item") in PLASTER_ITEMS and f.get("before_deductions_m2") is not None:
        total += float(f["before_deductions_m2"]) - float(f["after_deductions_m2"])
  return total

def prove(case_name: str, key: str, cases_dir: str | None = None) -> dict:
  from app.modules.drawings_boq.takeoff.proof import case_io as CIO, offline_run as OR
  profile, rule_set = OR.seed_profile()
  catalog = OR.work_item_catalog()
  
  case = CIO.load_case(os.path.join(CIO.HERE, case_name))
  files, missing = CIO.find_files(case, CIO.cases_dir(cases_dir))
  if missing:
    return {"case": case_name, "key": key, "ok": False, "why": f"the PDFs are missing: {', '.join(missing)}"}
  rows, _problems, _file = CIO.load_company_rules(case)
  off = {"id": f"toggle:{key}", "key": key, "scope": {}, "value": 0.0, "unit": None, "cls": "JUDGEMENT", "origin": "COMPANY", "version": 1, "note": "turned off to prove it moves only its own lines"}
  base_ledger, base_accs = _run(case, files, rows, profile, rule_set, catalog)
  flip_ledger, _flip_accs = _run(case, files, [*rows, off], profile, rule_set, catalog)
  a, b = _totals(base_ledger), _totals(flip_ledger)
  
  allowed = set(TOGGLES[key])
  moved = {f"{k[0]} ({k[1]})": [round(a.get(k, 0.0), 6), round(b.get(k, 0.0), 6)] for k in sorted(set(a) | set(b), key=str) if abs(a.get(k, 0.0) - b.get(k, 0.0)) > 1e-6 * max(1.0, abs(a.get(k, 0.0)))}
  stray = [k for k in moved if k.split(" ")[0] not in allowed]
  out = {"case": case_name, "key": key, "moved": moved, "stray": stray, "ok": bool(moved) and not stray, "rows": [len(base_ledger), len(flip_ledger)]}
  
  if not moved:
    out["why"] = "nothing moved: the switch changed no line, so it proves nothing"
  if key == "deduct_opening_plaster" and moved:
    wall = sum(b.get((c, "m2"), 0.0) - a.get((c, "m2"), 0.0) for c in ("FIN-PLASTER", "FIN-PLASTER-EXT"))
    took = _deducted_m2(base_accs)
    out["plaster_delta_m2"], out["openings_taken_off_m2"] = round(wall, 4), round(took, 4)
    if abs(wall - took) > AREA_TOL_M2:
      out["ok"] = False
      out["why"] = f"the plaster moved by {wall:.3f} m2 but the openings taken off in the first run are {took:.3f} m2"
  return out

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
  ap.add_argument("case")
  ap.add_argument("keys", nargs="*", default=["deduct_opening_plaster"])
  ap.add_argument("--cases-dir")
  args = ap.parse_args(argv)
  bad = 0
  
  for key in args.keys:
    r = prove(args.case, key, args.cases_dir)
    print(f"{'ok  ' if r['ok'] else 'FAIL'}  {r['case']} {key}")
    for k, (x, y) in (r.get("moved") or {}).items():
      print(f"      {k}: {x} -> {y}")
    for k in ("plaster_delta_m2", "openings_taken_off_m2", "why"):
      if k in r:
        print(f"      {k}: {r[k]}")
    if r.get("stray"):
      print(f"      MOVED ALSO: {', '.join(r['stray'])}")
    bad += 0 if r["ok"] else 1
  return 1 if bad else 0

if __name__ == "__main__":
  sys.exit(main())
