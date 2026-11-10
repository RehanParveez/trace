from __future__ import annotations
import argparse
import os
import sys
import yaml
from app.engine.catalogue import model as M
from app.engine.measure import recipes as RCP
from app.engine.catalogue import loader as CAT

NOT_BILLED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lines_not_billed.yaml")
FAMILY, RECIPE, DERIVED, ASK_ONLY, NONE = "FAMILY", "RECIPE", "DERIVED", "ASK_ONLY", "NONE"
ROADS = (FAMILY, RECIPE, DERIVED, ASK_ONLY, NONE)
STATUS_OF = {FAMILY: M.MEASURED_BY_FAMILY, RECIPE: M.BY_RECIPE, DERIVED: M.DERIVED_ROAD, ASK_ONLY: M.ASK_ONLY}
QUESTIONABLE = ("DECISION", "CONVENTION", "RATE_BOOK")

def not_billed(path: str = NOT_BILLED) -> dict:
  with open(path, encoding="utf-8") as fh:
    rows = yaml.safe_load(fh) or []
  return {str(r["line"]): str(r["reason"]) for r in rows if isinstance(r, dict) and r.get("line") and r.get("reason")}

def road_of(item) -> str:
  if item.derived:
    return DERIVED
  if item.billing.PRIVATE_QS:
    return FAMILY
  if item.recipe:
    return RECIPE
  if item.status_v1 == M.ASK_ONLY:
    return ASK_ONLY
  return NONE

def without_fallback(item) -> list:
  return [i.name for i in item.inputs if not set(i.sources) & set(QUESTIONABLE)]

def table(items=None) -> list:
  return [{"id": i.id, "name": i.name, "section": i.section, "unit": i.unit, "road": road_of(i), "status": i.status_v1, "recipe": i.recipe or None, "families": [b.line for b in i.billing.PRIVATE_QS],
    "no_fallback": without_fallback(i) if road_of(i) == RECIPE else [], "measured_by_recipe": i.id in RCP.specs()} for i in (items if items is not None else CAT.items())]

def problems(items=None) -> tuple:
  bad, warn = [], []
  every = list(items if items is not None else CAT.items())
  for row in table(every):
    if row["road"] == NONE:
      bad.append(f"{row['id']}: no road; it has no billing family, no recipe, no derived rule and is not ask-only")
    elif STATUS_OF[row["road"]] != row["status"]:
      bad.append(f"{row['id']}: status_v1 is {row['status']} but its road is {row['road']} ({STATUS_OF[row['road']]})")
  billed = {b.line for i in every for b in i.billing.PRIVATE_QS}
  
  for line, reason in not_billed().items():
    if line in billed:
      bad.append(f"{line}: recorded as not billed and also billed by an item")
  unknown = sorted({i.recipe for i in every if i.recipe and i.recipe not in M.RECIPES})
  bad += [f"recipe {r} is not one of {', '.join(M.RECIPES)}" for r in unknown]
  bad += RCP.problems()
  have = RCP.specs()
  waiting: dict = {}
  for i in every:
    if i.recipe and i.id not in have:
      waiting[i.recipe] = waiting.get(i.recipe, 0) + 1
  if waiting:
    total = sum(1 for i in every if i.recipe)
    warn.append(f"{sum(waiting.values())} of {total} recipe items have no spec yet ({', '.join(f'{r} {n}' for r, n in sorted(waiting.items()))}); recipe_specs.yaml says why for each recipe")
  return bad, warn

def counts(rows: list) -> dict:
  out = {r: 0 for r in ROADS}
  for row in rows:
    out[row["road"]] += 1
  return out

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Every catalogue item with the road its number comes by: FAMILY (an engine line feeds it), RECIPE (a named recipe will), DERIVED (a rule from other items), ASK_ONLY (only a question answers it), NONE.")
  ap.add_argument("--recipes", action="store_true", help="group the RECIPE items by recipe")
  ap.add_argument("--road", choices=ROADS, help="only the items with this road")
  args = ap.parse_args(argv)
  rows = table()
  
  if args.recipes:
    groups: dict = {}
    for r in rows:
      if r["road"] == RECIPE:
        groups.setdefault(r["recipe"], []).append(r)
    why = RCP.blocked()
    
    for name in sorted(groups):
      rs = groups[name]
      print(f"{name:15} {len(rs):3} items, {sum(1 for r in rs if r['measured_by_recipe']):3} measured  {' '.join(r['id'] + ('*' if r['measured_by_recipe'] else '') for r in rs)}")
      print(f"{'':15} not measured: {why.get(name, '-')}")
  else:
    for r in rows:
      if args.road and r["road"] != args.road:
        continue
      print(f"{r['id']:6} {r['road']:9} {r['recipe'] or '-':15} {'measured' if r['measured_by_recipe'] else '-':9} {','.join(r['families']) or '-':28} {r['name'][:50]}")
  c = counts(rows)
  print("roads: " + ", ".join(f"{k} {v}" for k, v in c.items()))
  bad, warn = problems()
  for line in bad + warn:
    print(f"{'FAIL' if line in bad else 'warn'}  {line}")
  return 1 if bad else 0

if __name__ == "__main__":
  sys.exit(main())
