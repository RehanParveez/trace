from __future__ import annotations
from collections import defaultdict
from app.engine.catalogue import roads as RD
from app.engine.measure import line_sources as LS
from app.engine.measure import recipes as RCP
from app.engine.measure import rulebook as RB
from app.modules.drawings_boq.lab.aliases import SOFTWARE_UNIT
from app.modules.drawings_boq.pricing.billing import run_lines as RL
from app.modules.drawings_boq.takeoff.completeness import facts as F
from app.modules.drawings_boq.takeoff.run import offline_accept as OA
from app.modules.drawings_boq.takeoff.run import offline_run as OR

PROJECT = "project"

def lines_of_rows(rows: list, floor_of: dict, units: dict | None = None) -> dict:
  units = units if units is not None else RL.units_of_family()
  skipped = RD.not_billed()
  si: dict = defaultdict(float)
  ins: dict = defaultdict(list)
  for r in rows:
    family = RL.family_of(r) or r.get("work_item_code")
    if not family:
      continue
  
    floor = floor_of.get(str(r.get("level_id"))) if r.get("level_id") else None
    unit = SOFTWARE_UNIT.get(family) or r.get("unit") or ""
    key = (family, floor if floor in F.FLOOR_ORDER else None, unit)
    si[key] += float(r.get("quantity") or 0)
    ins[key].append(LS.from_spec(r.get("spec")))
    
  out, not_billed, unmapped = [], {}, {}
  for (family, floor, unit), value in sorted(si.items(), key=lambda kv: (kv[0][0], str(kv[0][1]), kv[0][2])):
    wanted = sorted(units.get(family) or ())
    if not wanted:
      bucket = not_billed if family in skipped else unmapped
      bucket[family] = bucket.get(family, 0) + 1
      continue
    for target in wanted:
      v = RL.convert(value, unit, target)
      if v is not None:
        out.append({"family": family, "floor": floor, "value": round(v, 6), "unit": target, "inputs": LS.merge(ins[(family, floor, unit)])})
        
  return {"lines": out, "not_billed": not_billed, "unmapped": unmapped}

def lines_of_reads(reads: list, name: str = PROJECT, ready_only: bool = False, rules: list | None = None, derived_params: dict | None = None) -> dict:
  profile, rule_set = OR.seed_profile()
  with RB.using_case(rules or []):
    acc = OA.accept_case(name, reads, profile, ready_only=ready_only)
    res = OR.run_engine(OA.build_inputs(acc), profile, rule_set, acc.printed_all, case=name, derived_params=derived_params)
  rows = [{**{k: v for k, v in r.items() if k != "_entry"}, "quantity": float(r["quantity"])} for r in res.rows]
  profile, rule_set = OR.seed_profile()
  
  acc = OA.accept_case(name, reads, profile, ready_only=ready_only)
  res = OR.run_engine(OA.build_inputs(acc), profile, rule_set, acc.printed_all, case=name, derived_params=derived_params)
  rows = [{**{k: v for k, v in r.items() if k != "_entry"}, "quantity": float(r["quantity"])} for r in res.rows]
  out = lines_of_rows(rows, {str(k): v for k, v in acc.floor_of.items()})
  made = RCP.run(out["lines"])
  base: dict = {}
  for ln in out["lines"]:
    base.setdefault(ln["family"], []).append(ln.get("inputs") or [])
  base = {k: LS.merge(v) for k, v in base.items()}
  made = [{**m, "inputs": LS.recipe_inputs(m, base)} for m in made]
  out = {**out, "lines": out["lines"] + made, "recipes": len(made), "rules": len(rules or [])}
  return {**out, "rows": len(rows), "errors": [e if isinstance(e, dict) else {"message": str(e)} for e in res.errors]}
