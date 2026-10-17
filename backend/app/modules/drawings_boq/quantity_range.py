from __future__ import annotations
from math import sqrt

GRADE_ORDER = ("PRINTED", "VERIFIED", "CONFIRMED", "PICTURE", "MEASURED", "ASSUMED", "MISSING", "NOT_READ")

def _f(v) -> float:
  try:
    return float(v)
  except (TypeError, ValueError):
    return 0.0

def row_range(trace: dict | None) -> dict | None:
  rg = (trace or {}).get("range")
  return rg if isinstance(rg, dict) else None

def combine(rows: list, factor=1, net=None) -> dict | None:
  if not any(rg for _, rg in rows):
    return None
  fac = _f(factor)
  likely = sum(_f(q) for q, _ in rows) * fac
  if net is not None:
    likely = _f(net)
  down = up = 0.0
  bounded = unbounded = leaves = 0
  mix: dict = {}
  weakest = None
  
  for q, rg in rows:
    if not rg:
      unbounded += 1
      continue
    grade = str(rg.get("grade") or "")
    mix[grade] = mix.get(grade, 0) + 1
    if grade in GRADE_ORDER and (weakest is None or GRADE_ORDER.index(grade) > GRADE_ORDER.index(weakest)):
      weakest = grade
    if rg.get("leaves_out"):
      leaves += 1
    if not rg.get("bounded") or rg.get("low_pct") is None or rg.get("high_pct") is None:
      unbounded += 1
      continue
    bounded += 1
    
    mag = abs(_f(q)) * fac
    down += (mag * abs(_f(rg["low_pct"])) / 100.0) ** 2
    up += (mag * _f(rg["high_pct"]) / 100.0) ** 2
  low = likely - sqrt(down)
  high = likely + sqrt(up)
  
  def pct(v: float) -> float | None:
    return round((v - likely) / likely * 100.0, 2) if likely else None
  return {
    "likely": round(likely, 4), "low": round(low, 4), "high": round(high, 4), "low_pct": pct(low), "high_pct": pct(high),
    "rows": len(rows), "bounded_rows": bounded, "unbounded_rows": unbounded, "leaves_out_rows": leaves,
    "complete": unbounded == 0 and leaves == 0, "weakest": weakest, "mix": mix,
  }

def range_totals(items: list) -> list:
  out: dict = {}
  for it in items:
    unit = it.get("unit") or ""
    rg = it.get("quantity_range")
    q = _f(it.get("quantity"))
    s = out.setdefault(unit, {"unit": unit, "likely": 0.0, "down": 0.0, "up": 0.0, "items": 0, "unbounded": 0, "leaves_out": 0})
    s["items"] += 1
    s["likely"] += q
    if not rg:
      s["unbounded"] += 1
      continue
  
    s["down"] += (_f(rg["likely"]) - _f(rg["low"])) ** 2
    s["up"] += (_f(rg["high"]) - _f(rg["likely"])) ** 2
    if rg.get("unbounded_rows"):
      s["unbounded"] += 1
    if rg.get("leaves_out_rows"):
      s["leaves_out"] += 1
  return [{"unit": s["unit"], "likely": round(s["likely"], 4), "low": round(s["likely"] - sqrt(s["down"]), 4), "high": round(s["likely"] + sqrt(s["up"]), 4),
    "items": s["items"], "unbounded": s["unbounded"], "leaves_out": s["leaves_out"]} for s in sorted(out.values(), key=lambda x: x["unit"])]
