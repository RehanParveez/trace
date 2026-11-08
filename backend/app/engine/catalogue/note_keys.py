from __future__ import annotations
import functools
import os
import yaml

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "note_keys.yaml")
SHAPES = ("MM", "LAP", "GRADE", "PSI")
FIELDS = ("key", "shape", "unit", "range", "scopes", "fills", "about")

class NoteKeyError(Exception):
  pass

@functools.lru_cache(maxsize=1)
def _raw() -> dict:
  with open(PATH, encoding="utf-8") as fh:
    data = yaml.safe_load(fh)
  if not isinstance(data, dict) or not isinstance(data.get("keys"), list):
    raise NoteKeyError("note_keys.yaml must hold a list of keys")
  return data

def problems(data: dict | None = None) -> list:
  from app.modules.drawings_boq.takeoff.prep import printed_params as PP
  data = data or _raw()
  known = {*PP.COVER_PARAM_OF.values(), PP.PCC_PARAM, PP.FILL_PARAM, PP.PLASTER_PARAM, PP.DPC_PARAM, PP.LAP_PARAM}
  out, seen = [], set()
  
  for e in data["keys"]:
    name = e.get("key", "?")
    out += [f"{name}: no {f}" for f in FIELDS if f not in e]
    out += [f"{name}: repeated"] if name in seen else []
    seen.add(name)
    out += [f"{name}: shape {e.get('shape')} is not one of {', '.join(SHAPES)}"] if e.get("shape") not in SHAPES else []
    low_high = e.get("range") or [0, 0]
    out += [f"{name}: the range is empty"] if len(low_high) != 2 or low_high[0] >= low_high[1] else []
    out += [f"{name}: {p} is set by no printed-parameter reader" for p in e.get("fills") or [] if p not in known]
    
  from app.modules.drawings_boq.takeoff.prep import facts as F
  out += [f"{e['key']}: the range {e['range']} differs from the plausible range {list(F.PLAUSIBLE_MM[e['key']])} the rule reader uses" for e in data["keys"] if e.get("key") in F.PLAUSIBLE_MM and list(F.PLAUSIBLE_MM[e["key"]]) != list(e.get("range") or [])]
  out += [f"unit {u} has no factor" for u in ("mm", "in", "ft") if u not in data.get("units_mm", {})]
  return out

def keys() -> tuple:
  bad = problems()
  if bad:
    raise NoteKeyError("; ".join(bad[:5]))
  return tuple(_raw()["keys"])

def get(key: str) -> dict | None:
  return next((e for e in keys() if e["key"] == key), None)

def tolerance_mm() -> float:
  return float(_raw()["agree_tolerance_mm"])

def to_mm(value, unit) -> float | None:
  factor = _raw()["units_mm"].get(str(unit or "").strip().lower())
  try:
    return None if factor is None else round(float(value) * float(factor), 2)
  except (TypeError, ValueError):
    return None
