from __future__ import annotations
from math import sqrt

PICTURE_PCT = 3.0
MEASURED_PCT = 3.0
ASSUMED_PCT = 10.0

EXACT = ("PRINTED", "VERIFIED", "CONFIRMED")
NOT_QUANTITY = ("name", "mark", "position", "material", "host wall", "tank drawings", "levels")    

def _beam_alternatives(cand) -> tuple | None:
  from app.engine.measure import readings as QS
  f, p = cand.facts or {}, cand.params or {}
  try:
    used = float(p.get("depth_mm"))
  except (TypeError, ValueError):
    return None
  depths = [float(o["depth_mm"]) for o in f.get("section_options") or [] if o.get("depth_mm")]
  if not f.get("section_assumed") or len(depths) < 2 or used <= 0:
    return None
  
  cut = float(QS.convention("slab_thickness_mm") or 0.0) if f.get("depth_basis") == "WEB_BELOW_SLAB" else 0.0
  eff = [d - cut for d in [used, *depths]]
  if eff[0] <= 0 or min(eff) < 0:
    return None
  return (round((min(eff) - eff[0]) / eff[0] * 100.0, 2), round((max(eff) - eff[0]) / eff[0] * 100.0, 2))

def _alternatives(cand, name: str) -> tuple | None:
  if name == "depth" and cand.category == "BEAM":
    return _beam_alternatives(cand)
  if name != "thickness" or cand.category != "SLAB":
    return None
  used = ((cand.params or {}).get("depth_mm"))
  try:
    used = float(used)
  except (TypeError, ValueError):
    return None
  note = next((n for n in (cand.notes or []) if n.get("code") == "SLAB_THICKNESS_DISAGREES"), None)
  if not note or used <= 0:
    return None

  values = [used]
  for key in ("plan_mm", "sections_mm"):
    if note.get(key):
      values.append(float(note[key]))
  values += [float(o["mm"]) for o in (note.get("others") or []) if o.get("mm")]
  if len(values) < 2:
    return None
  return (round((min(values) - used) / used * 100.0, 2), round((max(values) - used) / used * 100.0, 2))

def range_for(cand, inputs: list) -> dict:
  lows: list = []
  highs: list = []
  drivers: list = []
  bounded, leaves_out = True, False
  for i in inputs:
    basis, name = i["basis"], i["name"]
    if name in NOT_QUANTITY:
      continue
    if basis == "NOT_READ":
      leaves_out = True
      continue
  
    if basis == "MISSING":
      bounded = False
      drivers.append({"name": name, "basis": basis, "low_pct": None, "high_pct": None})
      continue
    if basis in EXACT:
      continue
  
    alt = _alternatives(cand, name) if basis == "ASSUMED" else None
    if alt is not None:
      lo, hi = alt
    else:
      band = PICTURE_PCT if basis == "PICTURE" else MEASURED_PCT if basis == "MEASURED" else ASSUMED_PCT
      lo, hi = -band, band
    lows.append(lo)
    highs.append(hi)
    drivers.append({"name": name, "basis": basis, "low_pct": lo, "high_pct": hi})
  if not bounded:
    return {"bounded": False, "low_pct": None, "high_pct": None, "leaves_out": leaves_out, "drivers": drivers}
  return {"bounded": True, "low_pct": round(-sqrt(sum(x * x for x in lows)), 2) if lows else 0.0, "high_pct": round(sqrt(sum(x * x for x in highs)), 2) if highs else 0.0,
    "leaves_out": leaves_out, "drivers": drivers}

def apply(quantity, rng: dict) -> dict:
  """The low, likely and high figure of a quantity. low and high are None when the item has no range."""
  q = float(quantity or 0)
  if not rng or not rng.get("bounded"):
    return {"low": None, "likely": q, "high": None}
  return {"low": round(q * (1 + rng["low_pct"] / 100.0), 4), "likely": q, "high": round(q * (1 + rng["high_pct"] / 100.0), 4)}

def totals(rows: list) -> list:
  out: dict = {}
  for r in rows:
    props = (r.get("properties") if isinstance(r, dict) else getattr(r, "properties", None)) or {}
    ev = (props.get("_pdf") or {}).get("evidence") or {}
    rng = ev.get("range")
    
    unit = (r.get("unit") if isinstance(r, dict) else getattr(r, "unit", None)) or ""
    q = r.get("quantity") if isinstance(r, dict) else getattr(r, "quantity", 0)
    slot = out.setdefault(unit, {"unit": unit, "likely": 0.0, "down": 0.0, "up": 0.0, "rows": 0, "unbounded": 0, "leaves_out": 0})
    slot["rows"] += 1
    slot["likely"] += float(q or 0)
    if not rng or not rng.get("bounded"):
      slot["unbounded"] += 1
      continue
  
    v = apply(q, rng)
    slot["down"] += (v["likely"] - v["low"]) ** 2
    slot["up"] += (v["high"] - v["likely"]) ** 2
    if rng.get("leaves_out"):
      slot["leaves_out"] += 1
  res = []
  for s in sorted(out.values(), key=lambda x: x["unit"]):
    res.append({"unit": s["unit"], "likely": round(s["likely"], 4), "low": round(s["likely"] - sqrt(s["down"]), 4), "high": round(s["likely"] + sqrt(s["up"]), 4),
      "rows": s["rows"], "unbounded": s["unbounded"], "leaves_out": s["leaves_out"]})
  return res

def source_mix(rows: list) -> dict:
  out: dict = {}
  
  for r in rows:
    props = (r.get("properties") if isinstance(r, dict) else getattr(r, "properties", None)) or {}
    ev = (props.get("_pdf") or {}).get("evidence") or {}
    grade = ev.get("grade")
    if grade not in ("PRINTED", "MEASURED", "ASSUMED", "MISSING"):
      continue
  
    unit = (r.get("unit") if isinstance(r, dict) else getattr(r, "unit", None)) or ""
    q = r.get("quantity") if isinstance(r, dict) else getattr(r, "quantity", 0)
    slot = out.setdefault(unit, {"PRINTED": 0.0, "MEASURED": 0.0, "ASSUMED": 0.0, "MISSING": 0.0})
    slot[grade] += abs(float(q or 0))
  for unit, slot in out.items():
    total = sum(slot.values())
    out[unit] = {g: round(v / total, 4) if total else 0.0 for g, v in slot.items()}
  return out
