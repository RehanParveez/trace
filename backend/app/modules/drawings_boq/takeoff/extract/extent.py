from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import finish_rules as FR
from app.engine.measure import rule_formulas as RF
from app.modules.drawings_boq.takeoff.extract import room_types as RT
from app.modules.drawings_boq.takeoff.extract import config as C

OUTER, INNER, THIN = "outer", "inner", "thin"

def mode_of(item: str, level_hint: str | None) -> tuple:
  scope = {"item": item, **({"level": level_hint} if level_hint else {})}
  rv = FR.rule(FR.EXTENT, **scope)
  value = str(rv.value).upper() if rv.value is not None else FR.FLOOR_AREA
  return (value if value in FR.EXTENT_MODES else FR.FLOOR_AREA), rv

def needs_outer(level_hint: str | None) -> bool:
  return any(mode_of(item, level_hint)[0] == FR.STRIPS for item in FR.EXTENT_ITEMS)

def base_rooms(rooms: list, include: set | None = None) -> list:
  out: list = []
  for r in rooms:
    f = r.facts or {}
    
    if r.category != "ROOM" or r.status == "INVALID" or any(n.get("code") == "ROOM_INSIDE_ROOM" for n in r.notes or []) or not RT.floored(r):
      continue
    if include is not None and RT.of_room(r) not in include:
      continue
    if float(f.get("area_m2") or 0.0) > 0.0:
      out.append(r)
  return out

def _room_sum(rooms: list) -> tuple:
  total = sum(float((r.facts or {}).get("area_m2") or 0.0) for r in rooms)
  pts = [p for r in rooms for p in ((r.geometry or {}).get("outer") or (r.geometry or {}).get("points") or [])]
  return total, len(rooms), pts

def wall_class(w, outer: dict | None) -> str:
  if (outer or {}).get(w.key):
    return OUTER
  thickness = float((w.facts or {}).get("thickness_mm") or 0.0)
  return THIN if 0.0 < thickness < C.FOUNDATION_THIN_WALL_MAX_MM else INNER

def strips(walls: list, outer: dict | None, widths: dict) -> dict:
  by: dict = {}
  for w in walls:
    if w.category != "WALL":
      continue
    length_m = float((w.facts or {}).get("length_cc_m") or 0.0)
    if length_m <= 0.0:
      continue
    cls = wall_class(w, outer)
    
    got = RF.evaluate({"formula": "strip", "params": {"width_mm": float(widths[cls]), "depth_mm": 1000.0, "length_basis": "CENTRE"}}, {"centre_mm": length_m * 1000.0})
    slot = by.setdefault(cls, {"length_m": 0.0, "area_m2": 0.0})
    slot["length_m"] += length_m
    slot["area_m2"] += got["volume_m3"]
  return {"area_m2": sum(v["area_m2"] for v in by.values()), "by_class": {k: {"length_m": round(v["length_m"], 3), "area_m2": round(v["area_m2"], 3)} for k, v in sorted(by.items())}}

def strip_width(item: str, walls: list, outer: dict | None, level_hint: str | None) -> dict | None:
  rv = FR.rule(FR.STRIP_WIDTHS, item=item)
  widths = rv.value if isinstance(rv.value, dict) and set(rv.value) >= {OUTER, INNER, THIN} else None
  if widths is None:
    return None

  got = strips([w for w in walls if w.category == "WALL"], outer, widths)
  length = sum(v["length_m"] for v in got["by_class"].values())
  if length <= 0.0:
    return None
  return {"width_mm": round(got["area_m2"] / length * 1000.0, 3), "by_class": got["by_class"], "rule": FR.evidence(FR.STRIP_WIDTHS, rv, item=item), "widths_mm": {k: widths[k] for k in (OUTER, INNER, THIN)}}

def area(item: str, rooms: list, walls: list | None, outer: dict | None, level_hint: str | None, include: set | None, include_rule: str | None) -> dict:
  mode, rv = mode_of(item, level_hint)
  evidence = {} if FR.is_default(rv) else {"extent_rule": FR.evidence(FR.EXTENT, rv, item=item)}
  if mode == FR.ROOMS and include_rule:
    listed, lrv = FR.room_types_in(include_rule, level_hint)
    include = listed
    
  rows = base_rooms(rooms, include)
  total, used, pts = _room_sum(rows)
  facts = {"extent_mode": mode, **evidence}
  note = None
  
  if mode == FR.GROSS:
    foot = sum(float((w.facts or {}).get("length_cc_m") or 0.0) * float((w.facts or {}).get("thickness_mm") or 0.0) / 1000.0 for w in walls or [] if w.category == "WALL")
    if foot > 0.0 and used:
      total, note = total + foot, "EXTENT_GROSS"
      facts.update({"rooms_m2": round(total - foot, 3), "walls_m2": round(foot, 3)})
    else:
      facts["extent_mode"], note = FR.FLOOR_AREA, "EXTENT_RULE_NOT_FOLLOWED"
      facts["extent_problem"] = "no wall with a length and a thickness on this floor" if used else "no room"
      
  elif mode == FR.STRIPS:
    wrv = FR.rule(FR.STRIP_WIDTHS, item=item)
    widths = wrv.value if isinstance(wrv.value, dict) else None
    if widths and set(widths) >= {OUTER, INNER, THIN} and walls:
      got = strips(walls, outer, widths)
      if got["area_m2"] > 0.0:
        total, note = got["area_m2"], "EXTENT_STRIPS"
        facts.update({"strip_widths_mm": {k: widths[k] for k in (OUTER, INNER, THIN)}, "strips": got["by_class"], "widths_rule": FR.evidence(FR.STRIP_WIDTHS, wrv, item=item)})
        pts = [p for w in walls if w.category == "WALL" for p in ((w.geometry or {}).get("points") or [])]
        used = sum(1 for w in walls if w.category == "WALL")
        
    if note is None:
      facts["extent_mode"], note = FR.FLOOR_AREA, "EXTENT_RULE_NOT_FOLLOWED"
      facts["extent_problem"] = "no strip widths in finish.strip_widths_mm for this item" if not widths else "no wall with a length on this floor"
      rows = base_rooms(rooms, include)
      total, used, pts = _room_sum(rows)
  return {"mode": facts["extent_mode"], "area_m2": total, "rooms": used, "points": pts, "facts": facts, "note": note}
