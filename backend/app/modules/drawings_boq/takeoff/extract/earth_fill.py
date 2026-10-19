from __future__ import annotations
import math
from app.modules.drawings_boq.takeoff.extract import foundation as FD
from app.modules.drawings_boq.takeoff.extract import config as C

FILL_ITEM = FD.EARTH_FILL
DEFAULT_LAYER_MM = 152.4

def layers_of(depth_mm: float, layer_mm: float | None) -> int:
  layer = float(layer_mm or DEFAULT_LAYER_MM)
  if depth_mm <= 0 or layer <= 0:
    return 0
  return int(math.ceil(round(depth_mm / layer, 6)))

def fill_candidate(rooms: list, ctx: dict, level_hint: str | None, spec, cls, finish):
  total, used, pts = 0.0, 0, []
  
  for r in rooms:
    f = r.facts or {}
    if r.category != "ROOM" or r.status == "INVALID" or any(n.get("code") == "ROOM_INSIDE_ROOM" for n in r.notes or []):
      continue
    a = float(f.get("area_m2") or 0.0)
    if a > 0.0:
      total += a
      used += 1
      
      pts.extend((r.geometry or {}).get("outer") or (r.geometry or {}).get("points") or [])
  if used == 0:
    return None
  facts = {"derived_from": "ROOMS", "room_count": used, "area_m2": round(total, 3)}
  label = f"Earth filling under the floor · {total:.2f} m²" + (f" · {spec[0]}" if spec else "")
  return FD._make(cls, ctx, finish, (FILL_ITEM, level_hint or ""), FILL_ITEM, label, "EARTH-FILL", [FD._centre(pts)],
    {"length_mm": round(total * 1000.0, 1), "width_mm": 1000.0}, ["depth_mm"], [C.note("FILL_FROM_ROOMS"), C.note("FILL_DEPTH_NOT_READ")], facts, 0.7)
