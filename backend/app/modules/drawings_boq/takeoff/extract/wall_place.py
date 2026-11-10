from __future__ import annotations
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union
from app.engine.measure import rule_registry as RR
from app.modules.drawings_boq.takeoff.extract import config as C

RULE = "BOUNDARY_FROM_PLAN"
BOUNDARY = "BOUNDARY"
GROUND = "GROUND"

def enabled() -> bool:
  return RR.on(RULE)

def is_boundary(cand) -> bool:
  return enabled() and cand.category == "WALL" and (cand.facts or {}).get("place") == BOUNDARY

def _live(w) -> bool:
  f = w.facts or {}
  return (w.category == "WALL" and w.status != "INVALID" and f.get("enclosure") != "TANK" and not f.get("foundation_item") and float(f.get("length_cc_m") or 0.0) > 0.0
    and len((w.geometry or {}).get("points") or []) >= 2)

def _thickness_mm(w) -> float:
  f = w.facts or {}
  return float(f.get("thickness_used_mm") or (w.params or {}).get("thickness_mm") or f.get("thickness_mm") or 0.0)

def _line(w) -> LineString:
  pts = w.geometry["points"]
  return LineString([tuple(pts[0][:2]), tuple(pts[-1][:2])])

def house_outline(walls: list, mm_per_pt: float):
  parts = [_line(w).buffer(_thickness_mm(w) / 2.0 / mm_per_pt, cap_style=3) for w in walls if _live(w) and _thickness_mm(w) >= C.HOUSE_WALL_MIN_MM and not (w.facts or {}).get("light_pen")]
  if not parts:
    return None
  reach = C.OUTLINE_CLOSE_MM / mm_per_pt
  joined = unary_union(parts).buffer(reach).buffer(-reach)
  rings = [Polygon(g.exterior) for g in (joined.geoms if hasattr(joined, "geoms") else [joined]) if not g.is_empty]
  shape = unary_union(rings) if rings else None
  return shape if shape is not None and shape.area > 0.0 else None

def apply(walls: list, mm_per_pt: float, level_hint: str | None) -> dict:
  out = {"ran": False, "boundary_runs": 0, "boundary_m": 0.0}
  if str(level_hint or "").upper() != GROUND or not mm_per_pt:
    return out
  shape = house_outline(walls, mm_per_pt)
  if shape is None:
    return out
  out["ran"] = True
  clear = C.BOUNDARY_CLEAR_MM / mm_per_pt
  for w in walls:
    if not _live(w) or (w.facts or {}).get("construction") == "RCC" or (w.facts or {}).get("place"):
      continue
    ln = _line(w)
    if ln.length * mm_per_pt < C.BOUNDARY_MIN_RUN_MM or ln.distance(shape) < clear:
      continue
    w.facts = {**(w.facts or {}), "place": BOUNDARY}
    out["boundary_runs"] += 1
    out["boundary_m"] = round(out["boundary_m"] + ln.length * mm_per_pt / 1000.0, 2)
  return out
