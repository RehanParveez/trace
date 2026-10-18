from __future__ import annotations
from math import sqrt
from app.modules.drawings_boq import driver_marks as DM

TOP_DRIVERS = 12
TOP_ITEMS = 5
NOT_ITEMISED = "(not itemised)"

def _f(v) -> float:
  try:
    return float(v)
  except (TypeError, ValueError):
    return 0.0

def _drivers_of(rg: dict) -> list:
  drivers = [d for d in (rg.get("drivers") or []) if isinstance(d, dict)]
  if drivers:
    return drivers
  return [{"name": NOT_ITEMISED, "basis": str(rg.get("grade") or ""), "low_pct": rg.get("low_pct"), "high_pct": rg.get("high_pct")}]

def _top(per_item: dict, limit: int = TOP_ITEMS) -> list:
  ranked = sorted(per_item.values(), key=lambda x: (-x["swing"], x["name"] or ""))
  return [{"item_id": x["item_id"], "name": x["name"], "swing": round(x["swing"], 4)} for x in ranked[:limit]]

def _bump(per_item: dict, item: dict, amount: float) -> None:
  slot = per_item.setdefault(item["item_id"], {"item_id": item["item_id"], "name": item["name"], "swing": 0.0})
  slot["swing"] += amount

def build(items: list) -> dict:

  groups: dict = {}
  for item in items:
    g = groups.setdefault(item.get("unit") or "", {"unit": item.get("unit") or "", "likely": 0.0, "down": 0.0, "up": 0.0, "rows": 0, "bounded": 0,
      "unbounded": 0, "no_range": 0, "leaves_out": 0, "drivers": {}, "open": {}})
    fac = _f(item.get("factor") or 1)
    for row in item.get("rows") or []:
      qty, rg, mark = row[0], row[1], (row[2] if len(row) > 2 else None)
      q = abs(_f(qty)) * fac
      g["rows"] += 1
      g["likely"] += _f(qty) * fac
      if not rg:
        g["no_range"] += 1
        continue
    
      if rg.get("leaves_out"):
        g["leaves_out"] += 1
      if not rg.get("bounded") or rg.get("low_pct") is None or rg.get("high_pct") is None:
        g["unbounded"] += 1
        DM.bump(g, mark, item, q, open_q=q)
        names = {str(d.get("name")) for d in _drivers_of(rg) if d.get("low_pct") is None and d.get("high_pct") is None} or {NOT_ITEMISED}
        for name in names:
          o = g["open"].setdefault(name, {"name": name, "rows": 0, "items": set(), "quantity": 0.0, "per_item": {}})
          o["rows"] += 1
          o["items"].add(item["item_id"])
          o["quantity"] += q
          _bump(o["per_item"], item, q)
          DM.bump(o, mark, item, q, open_q=q)
        continue
    
      g["bounded"] += 1
      for d in _drivers_of(rg):
        lo, hi = d.get("low_pct"), d.get("high_pct")
        if lo is None or hi is None:
          continue
      
        down, up = q * abs(_f(lo)) / 100.0, q * _f(hi) / 100.0
        key = (str(d.get("name")), str(d.get("basis")))
        s = g["drivers"].setdefault(key, {"name": key[0], "basis": key[1], "rows": 0, "items": set(), "down2": 0.0, "up2": 0.0, "per_item": {}})
        s["rows"] += 1
        s["items"].add(item["item_id"])
        s["down2"] += down * down
        s["up2"] += up * up
        _bump(s["per_item"], item, down + up)
        DM.bump(s, mark, item, down + up)
        DM.bump(g, mark, item, down + up, down2=down * down, up2=up * up)
        g["down"] += down * down
        g["up"] += up * up

  units = []
  for unit in sorted(groups):
    g = groups[unit]
    likely, total_down, total_up = g["likely"], g["down"], g["up"]
    span2 = total_down + total_up
    drivers = []
    
    for s in sorted(g["drivers"].values(), key=lambda x: (-(x["down2"] + x["up2"]), x["name"])):
      mine = s["down2"] + s["up2"]
      after_down, after_up = sqrt(max(total_down - s["down2"], 0.0)), sqrt(max(total_up - s["up2"], 0.0))
      drivers.append({"name": s["name"], "basis": s["basis"], "rows": s["rows"], "items": len(s["items"]),
        "swing_down": round(sqrt(s["down2"]), 4), "swing_up": round(sqrt(s["up2"]), 4),
        "share_pct": round(mine / span2 * 100.0, 1) if span2 else 0.0,
        "low_after": round(likely - after_down, 4), "high_after": round(likely + after_up, 4),
        "top_items": _top(s["per_item"]), "marks": DM.top(s)})
      
    opens = []
    for o in sorted(g["open"].values(), key=lambda x: (-x["quantity"], x["name"])):
      opens.append({"name": o["name"], "rows": o["rows"], "items": len(o["items"]), "quantity": round(o["quantity"], 4),
        "share_of_quantity_pct": round(o["quantity"] / abs(likely) * 100.0, 1) if likely else None, "top_items": _top(o["per_item"]), "marks": DM.top(o)})
    units.append({"unit": unit, "likely": round(likely, 4), "low": round(likely - sqrt(total_down), 4), "high": round(likely + sqrt(total_up), 4),
      "rows": g["rows"], "bounded_rows": g["bounded"], "unbounded_rows": g["unbounded"], "no_range_rows": g["no_range"], "leaves_out_rows": g["leaves_out"],
      "drivers": drivers[:TOP_DRIVERS], "open_inputs": opens[:TOP_DRIVERS],
      "confirm_first": DM.confirm_first(g, likely, total_down, total_up), "open_marks": DM.open_marks(g, likely)})
  return {"units": units}
