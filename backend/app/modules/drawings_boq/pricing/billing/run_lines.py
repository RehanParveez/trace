from __future__ import annotations
from collections import defaultdict
from app.modules.drawings_boq.lab.aliases import SOFTWARE_UNIT, bill_quantity, software_key
from app.engine.catalogue import loader as CAT
from app.modules.drawings_boq.takeoff.completeness import facts as F

WALL_FORMULA = "PDF_TAKEOFF_LENGTH_X_HEIGHT_X_THICKNESS"
WALL_FAMILY_OF_CODE = {"MAS-BRICK": "BRICK_WALLS", "CON-RCC": "RCC_WALLS"}

def family_of(row: dict) -> str | None:
  trace = row.get("trace") or {}
  inputs = trace.get("inputs") or {}
  
  src = inputs.get("formwork_source") or inputs.get("steel_source") or {}
  family = software_key(row.get("formula_code") or "", inputs.get("tag") or src.get("tag"), trace.get("label"))
  if family is None and row.get("formula_code") == WALL_FORMULA:
    family = WALL_FAMILY_OF_CODE.get(row.get("work_item_code"))
  return family

def convert(value: float, from_unit: str, to_unit: str) -> float | None:
  _q, si_to, one_to = bill_quantity("", to_unit, 1.0)
  _q, si_from, one_from = bill_quantity("", from_unit, 1.0)
  if si_to != si_from or si_to == "?" or not one_to or not one_from:
    return None
  return value * one_from / one_to     

def floor_name(level_name: str | None) -> str | None:
  name = str(level_name or "").strip().upper()
  return name if name in F.FLOOR_ORDER or name == "FOUNDATION" else None

def units_of_family() -> dict:
  out: dict = defaultdict(set)
  for item in CAT.items():
    own = {y.qty for y in item.yields if y.unit == item.unit}
    for b in item.billing.PRIVATE_QS:
      if b.qty in own:
        out[b.line].add(item.unit)
  return out

def lines_from_rows(rows: list, floor_of: dict, units: dict | None = None) -> dict:
  units = units if units is not None else units_of_family()
  si: dict = defaultdict(float)
  row_unit: dict = {}
  left_out = 0
  
  for r in rows:
    family = family_of(r)
    if family is None:
      left_out += 1
      continue
    
    floor = floor_of.get(str(r.get("level_id"))) if r.get("level_id") else None
    unit = SOFTWARE_UNIT.get(family) or r.get("unit") or ""
    si[(family, floor, unit)] += float(r.get("quantity") or 0)
    row_unit[(family, floor, unit)] = unit
    
  lines, no_unit = [], []
  for (family, floor, unit), value in sorted(si.items(), key=lambda kv: (kv[0][0], str(kv[0][1]), kv[0][2])):
    wanted = sorted(units.get(family) or ())
    done = False
    for target in wanted:
      v = convert(value, unit, target)
      if v is not None:
        lines.append({"family": family, "floor": floor, "value": round(v, 6), "unit": target})
        done = True
    if not done:
      no_unit.append({"family": family, "floor": floor, "why": f"measured in {unit}; the items that bill {family} take {', '.join(wanted) or 'no unit of their own yield'}"})
  return {"lines": lines, "no_family": left_out, "no_unit": no_unit}
