from __future__ import annotations
import functools
import importlib
import os
import yaml
from app.engine.catalogue import loader as CAT

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "catalogue", "recipe_specs.yaml")
NAMES = ("floor_area", "wall_face", "openings_area", "layers", "site", "counts")
FAMILY = "RECIPE"

@functools.lru_cache(maxsize=1)
def _doc() -> dict:
  with open(PATH, encoding="utf-8") as fh:
    return yaml.safe_load(fh) or {}

def specs() -> dict:
  return {s["item"]: s for s in _doc().get("specs") or []}

def blocked() -> dict:
  return dict(_doc().get("blocked") or {})

def module(name: str):
  return importlib.import_module(f"app.engine.measure.recipes.{name}")

def family_units() -> dict:
  out: dict = {}
  for item in CAT.items():
    own = {y.qty for y in item.yields if y.unit == item.unit}
    for b in item.billing.PRIVATE_QS:
      if b.qty in own:
        out.setdefault(b.line, set()).add(item.unit)
  return out

def bases_of(lines: list) -> dict:
  out: dict = {}
  for ln in lines:
    if not ln.get("family") or ln.get("value") is None or ln.get("item"):
      continue
    by_unit = out.setdefault(ln["family"], {})
    by_unit[ln.get("unit")] = by_unit.get(ln.get("unit"), 0.0) + float(ln["value"])
  return out

def from_bases(recipe: str, spec: dict, item, bases: dict) -> dict | None:
  total, used = 0.0, []
  for fam in spec["base"]:
    got = (bases.get(fam) or {}).get(item.unit)
    if got:
      total += got
      used.append(fam)

  if not used:
    return None
  return {"family": f"{FAMILY}/{recipe}", "item": item.id, "floor": None, "value": round(total, 6), "unit": item.unit, "recipe": recipe, "ask": spec.get("ask", True), "from": used, "note": spec.get("note") or ""}

def run(lines: list, only: set | None = None) -> list:
  bases, table, out = bases_of(lines), specs(), []
  for item in CAT.items():
    spec = table.get(item.id)
    if spec is None or (only is not None and item.id not in only):
      continue
    line = module(spec["recipe"]).measure(spec, item, bases)
    if line is not None:
      out.append(line)
  return out

def problems() -> list:
  out, units = [], family_units()
  for iid, s in specs().items():
    item = CAT.get(iid)
    if item is None:
      out.append(f"recipe_specs.yaml: {iid} is not an item")
      continue

    if s.get("recipe") not in NAMES:
      out.append(f"recipe_specs.yaml: {iid} names recipe {s.get('recipe')!r}, which has no module")
      continue
    if item.recipe != s["recipe"] or item.billing.PRIVATE_QS:
      out.append(f"recipe_specs.yaml: {iid} is not an item whose road is recipe {s['recipe']}")
    allowed = module(s["recipe"]).BASES

    for fam in s.get("base") or []:
      if fam not in allowed:
        out.append(f"recipe_specs.yaml: {iid} takes base {fam}, which is not a base of recipe {s['recipe']}")
      elif item.unit not in units.get(fam, ()):
        out.append(f"recipe_specs.yaml: {iid} is in {item.unit} and base {fam} is in {', '.join(sorted(units.get(fam, ()))) or 'no unit'}")
    if not s.get("base"):
      out.append(f"recipe_specs.yaml: {iid} names no base")
  waiting = {i.recipe for i in CAT.items() if i.recipe}
  out += [f"recipe_specs.yaml: no reason is given for recipe {r}, which has items without a spec" for r in sorted(waiting - set(blocked()))]
  return out
