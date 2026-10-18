from __future__ import annotations
from app.modules.drawings_boq.lab.aliases import KEY_LABEL, SOFTWARE_UNIT
from app.modules.drawings_boq.lab.compare import software_totals

PASS, WARN, INFO = "PASS", "WARN", "INFO"

CONCRETE = ("RCC_FOOTINGS", "RCC_PLINTH_BEAM", "RCC_COLUMNS", "RCC_WALLS", "RCC_LINTELS", "RCC_ROOF_BEAMS", "RCC_STAIR", "RCC_SLABS")
BELOW_GROUND = ("RCC_FOOTINGS", "PCC", "BRICK_FOUNDATION")

BANDS_NOTE = "The usual range for a low-rise house. It is a rule of thumb, not a standard: a figure outside it is a reason to look, not proof of a mistake."

BANDS = {
  "STEEL_PER_CONCRETE": ("Steel per cubic metre of concrete", "kg/m3", 60.0, 180.0,
    "Steel and concrete do not fit together. Either steel is missing or assumed too low, or too much is counted."),
  "FORMWORK_PER_CONCRETE": ("Form work per cubic metre of concrete", "m2/m3", 5.0, 15.0,
    "Form work and concrete do not fit together. Check the members that have concrete but no form work, or form work counted on a member twice."),
  "IMPLIED_SLAB_THICKNESS": ("Slab concrete over ceiling plaster (average slab thickness)", "m", 0.09, 0.30,
    "The slab concrete does not fit the ceiling area. Check the slab thickness and whether every slab has a ceiling."),
  "PLASTER_PER_BRICK": ("Wall plaster per cubic metre of brick work", "m2/m3", 3.0, 12.0,
    "Plaster and brick work do not fit together. Check wall faces counted twice, or walls with no plaster."),
  "EXCAVATION_OVER_FOUNDATION": ("Excavation over what is placed below ground", "ratio", 1.0, 8.0,
    "Excavation should be at least the volume placed in it (footings, lean concrete, foundation brick work)."),
}

PRESENCE = {
  "STEEL_FOR_CONCRETE": (CONCRETE, ("STEEL",), "concrete", "Concrete is counted but no reinforcement steel is."),
  "FORMWORK_FOR_CONCRETE": (CONCRETE, ("FORMWORK",), "concrete", "Concrete is counted but no form work is."),
  "PLASTER_FOR_BRICK": (("BRICK_WALLS",), ("WALL_PLASTER",), "brick work above the plinth", "Brick walls are counted but no wall plaster is."),
  "CEILING_FOR_SLABS": (("RCC_SLABS",), ("CEILING_PLASTER",), "slabs", "Slabs are counted but no ceiling plaster is."),
  "EXCAVATION_FOR_FOUNDATION": (BELOW_GROUND, ("EXCAVATION",), "footings, lean concrete or foundation brick work", "Work is counted below ground but no excavation is."),
}

def _q(totals: dict, keys: tuple) -> float:
  return sum(float(totals.get(k, {}).get("quantity") or 0.0) for k in keys)

def _inputs(totals: dict, keys: tuple) -> list:
  return [{"key": k, "label": KEY_LABEL.get(k, k), "quantity": round(float(totals[k]["quantity"]), 3), "unit": SOFTWARE_UNIT.get(k, totals[k].get("unit") or "")} for k in keys if k in totals]

def _check(code: str, status: str, label: str, message: str, inputs: list, value=None, unit: str = "", low=None, high=None) -> dict:
  return {"code": code, "status": status, "label": label, "message": message, "value": None if value is None else round(value, 3), "unit": unit,
    "low": low, "high": high, "inputs": inputs}

def _ratio(totals: dict, code: str, top: float, bottom: float, top_keys: tuple, bottom_keys: tuple) -> dict:
  label, unit, low, high, out_text = BANDS[code]
  inputs = _inputs(totals, tuple(dict.fromkeys(top_keys + bottom_keys)))
  if top <= 0 or bottom <= 0:
    return _check(code, INFO, label, "Not judged: one of the two quantities is not counted.", inputs, unit=unit, low=low, high=high)
  v = top / bottom
  if v < low or v > high:
    side = "below" if v < low else "above"
    return _check(code, WARN, label, f"{v:.3g} {unit} is {side} the usual {low:g} to {high:g}. {out_text}", inputs, v, unit, low, high)
  return _check(code, PASS, label, f"{v:.3g} {unit} is inside the usual {low:g} to {high:g}.", inputs, v, unit, low, high)

def run(rows: list) -> dict:
  totals, unclassified = software_totals(rows)
  concrete, steel, form = _q(totals, CONCRETE), _q(totals, ("STEEL",)), _q(totals, ("FORMWORK",))
  checks: list = []

  for code, (premise, needed, premise_text, message) in PRESENCE.items():
    if _q(totals, premise) <= 0:
      continue
    ins = _inputs(totals, premise + needed)
    label = ", ".join(KEY_LABEL.get(k, k) for k in needed)
    if _q(totals, needed) <= 0:
      checks.append(_check(code, WARN, label, message, ins))
    else:
      checks.append(_check(code, PASS, label, f"{label} is counted along with the {premise_text}.", ins))

  checks.append(_ratio(totals, "STEEL_PER_CONCRETE", steel, concrete, ("STEEL",), CONCRETE))
  checks.append(_ratio(totals, "FORMWORK_PER_CONCRETE", form, concrete, ("FORMWORK",), CONCRETE))
  checks.append(_ratio(totals, "IMPLIED_SLAB_THICKNESS", _q(totals, ("RCC_SLABS",)), _q(totals, ("CEILING_PLASTER",)), ("RCC_SLABS",), ("CEILING_PLASTER",)))
  checks.append(_ratio(totals, "PLASTER_PER_BRICK", _q(totals, ("WALL_PLASTER",)), _q(totals, ("BRICK_WALLS",)), ("WALL_PLASTER",), ("BRICK_WALLS",)))
  checks.append(_ratio(totals, "EXCAVATION_OVER_FOUNDATION", _q(totals, ("EXCAVATION",)), _q(totals, BELOW_GROUND), ("EXCAVATION",), BELOW_GROUND))
  order = {WARN: 0, INFO: 1, PASS: 2}
  checks.sort(key=lambda c: (order[c["status"]], c["code"]))
  figures = [{"key": k, "label": KEY_LABEL.get(k, k), "quantity": round(v["quantity"], 3), "unit": SOFTWARE_UNIT.get(k, v.get("unit") or ""), "rows": v["rows"]}
    for k, v in sorted(totals.items(), key=lambda kv: KEY_LABEL.get(kv[0], kv[0]))]
  return {"checks": checks, "warnings": sum(1 for c in checks if c["status"] == WARN), "passed": sum(1 for c in checks if c["status"] == PASS),
    "info": sum(1 for c in checks if c["status"] == INFO), "figures": figures, "ungrouped_rows": sum(u["rows"] for u in unclassified), "note": BANDS_NOTE}
