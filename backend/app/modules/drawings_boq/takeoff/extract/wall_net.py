from __future__ import annotations
from app.engine.measure import proposed
from app.engine.measure import readings as QS
from app.modules.drawings_boq.takeoff.extract import config as C

def lintel_sizes(lintels: list) -> dict:
  out: dict = {}
  for c in lintels or []:
    p, f = c.params or {}, c.facts or {}
    tag = f.get("opening_tag")
    if tag and p.get("length_mm") and p.get("width_mm") and p.get("depth_mm"):
      width = float((f.get("table_section_mm") or [p["width_mm"]])[0])
      out[str(tag)] = (float(p["length_mm"]), width, float(p["depth_mm"]))
  return out

def _thickness(wall) -> float:
  return float((wall.facts or {}).get("thickness_used_mm") or (wall.params or {}).get("thickness_mm") or 0.0)

def _brick_wall(wall) -> bool:
  f = wall.facts or {}
  return wall.category == "WALL" and f.get("construction") != "RCC" and not f.get("enclosure") and not f.get("foundation_item") and bool((wall.params or {}).get("openings"))

def less_lines(wall, sizes: dict) -> list:
  t = _thickness(wall)
  if not t:
    return []
  out = []
  
  for o in (wall.params or {}).get("openings") or []:
    s = sizes.get(str(o.get("label")))
    if not s:
      continue
  
    length, width, depth = s
    nos = int(o.get("nos") or 1)
    v = round(length * min(width, t) * depth / 1e9 * nos, 6)
    if v > 0:
      out.append({"op": "LESS", "value": v, "label": f"Lintel over {o['label']} x{nos}: {length:.0f} x {min(width, t):.0f} x {depth:.0f} mm"[:120]})
  return out

def attach(walls: list, lintels: list) -> int:
  if not QS.param("brick_net_of_lintels"):
    return 0
  sizes = lintel_sizes(lintels)
  n = 0
  
  for w in walls:
    if not _brick_wall(w):
      continue
  
    lines = less_lines(w, sizes)
    if not lines:
      continue
  
    w.params = {**(w.params or {}), "adjustments": [*((w.params or {}).get("adjustments") or []), *lines]}
    total = round(sum(x["value"] for x in lines), 4)
    w.facts = {**(w.facts or {}), "lintel_deduction": {"m3": total, "lintels": len(lines), "qs": "IS 1200 and usual practice (assumed)"}}
    w.notes.append(C.note("BRICK_NET_OF_LINTELS", m3=total, count=len(lines)))
    n += 1
  return n

def gross_net(wall) -> dict | None:
  p, f = wall.params or {}, wall.facts or {}
  length, h, t = float(f.get("length_cc_m") or 0.0), float(p.get("height_mm") or 0.0), _thickness(wall)
  if not (length and h and t) or f.get("construction") == "RCC" or f.get("enclosure") or f.get("foundation_item"):
    return None

  gross = length * h / 1000.0 * t / 1000.0
  opening = float((f.get("openings") or {}).get("area_m2") or 0.0) * t / 1000.0
  lintel = sum(float(a["value"]) for a in (p.get("adjustments") or []) if a.get("op") == "LESS")
  return {"gross_m3": round(gross, 3), "openings_m3": round(opening, 3), "lintels_m3": round(lintel, 3), "net_m3": round(max(gross - opening - lintel, 0.0), 3)}
