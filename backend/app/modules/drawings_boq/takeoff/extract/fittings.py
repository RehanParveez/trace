from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import finish_rules as FR
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.extract import finishes as FN

SILL, STOPPER = "WINDOW_SILL", "WET_DOOR_STOPPER"
ITEMS = (SILL, STOPPER)
WORK_ITEM: dict = {}
SILL_MIN_MM = 300.0

def window_width_mm(win) -> float | None:
  f = win.facts or {}
  size = f.get("size_schedule_mm") or f.get("size_drawn_mm")
  if size and len(size) == 2 and float(size[0]) > 0.0:
    return float(size[0])
  return None

def sill_candidate(windows: list, ctx: dict, level_hint: str | None, spec, cls, finish):
  code, rule = FR.sill_item()
  if code == FR.NONE:
    return None
  depth, depth_rule = FR.sill_depth()
  rows, points, unsized, low, unknown = [], [], 0, 0, 0
  
  for w in windows:
    if w.category != "WINDOW" or w.status == "INVALID":
      continue
    f = w.facts or {}
    width = window_width_mm(w)
    sill = f.get("sill_mm")
    if width is None:
      unsized += int(w.count or 1)
      continue
    if sill is None:
      unknown += int(w.count or 1)
      continue
    if float(sill) < SILL_MIN_MM:
      low += int(w.count or 1)
      continue
  
    rows.append({"tag": w.tag, "width_mm": width, "count": int(w.count or 1), "sill_mm": float(sill)})
    points.extend([float(q[0]), float(q[1])] for q in (w.geometry or {}).get("points") or [])
  if not rows:
    return None
  length_m = sum(r["width_mm"] * r["count"] for r in rows) / 1000.0
  area = length_m * depth / 1000.0
  facts = {"derived_from": "WINDOW_ROWS", "rows": rows, "length_m": round(length_m, 3), "depth_mm": depth, "area_m2": round(area, 3), "no_sill_door_windows": low, "unsized_windows": unsized,
    "sill_not_printed": unknown, "sill_min_mm": SILL_MIN_MM, "item_rule": FR.evidence(FR.SILL_ITEM, rule), "depth_rule": FR.evidence(FR.SILL_DEPTH, depth_rule)}
  notes = [C.note("FITTING_SILL_FROM_WINDOWS", windows=sum(r["count"] for r in rows), length_m=round(length_m, 2), depth_mm=depth)]
  
  if unsized or unknown:
    notes.append(C.note("FITTING_SILL_WINDOWS_LEFT_OUT", unsized=unsized, sill_not_printed=unknown))
  label = f"Window sills · {length_m:.2f} m long × {depth:g} mm · {area:.2f} m²" + (f" · {spec[0]}" if spec else "")
  return FN._make(cls, ctx, finish, (SILL, level_hint or ""), SILL, label, "SILL", [[sum(q[0] for q in points) / max(1, len(points)), sum(q[1] for q in points) / max(1, len(points))]] if points else [], {"length_mm": round(area * 1000.0, 1), "width_mm": 1000.0}, [], notes, facts, 0.5, work_item=code)

def stopper_candidate(rooms: list, doors: list, mm_per_pt: float, ctx: dict, level_hint: str | None, spec, cls, finish):
  code, rule = FR.stopper_item()
  if code == FR.NONE:
    return None
  every = FN.usable_rooms(rooms)
  used = [r for r in every if FN.is_finished(r) and FN.is_wet(r)]
  
  if not used:
    return None
  assigned = FN.door_assignment(every, doors, mm_per_pt)
  rows = [{"room": (FN._names(r) or ["ROOM"])[0], "doors": assigned.get(id(r), (0.0, 0, 0))[1], "width_m": round(assigned.get(id(r), (0.0, 0, 0))[0], 3), "assumed": assigned.get(id(r), (0.0, 0, 0))[2]} for r in used]
  total = sum(r["width_m"] for r in rows)
  if total <= 0.0:
    return None

  facts = {"derived_from": "DOORS_OF_WET_ROOMS", "rows": rows, "length_m": round(total, 3), "item_rule": FR.evidence(FR.STOPPER_ITEM, rule), "assumed_widths": sum(r["assumed"] for r in rows)}
  notes = [C.note("FITTING_STOPPER_FROM_DOORS", rooms=len(used), length_m=round(total, 2))]
  label = f"Water stopper at wet-room doors · {total:.2f} m" + (f" · {spec[0]}" if spec else "")
  return FN._make(cls, ctx, finish, (STOPPER, level_hint or ""), STOPPER, label, "STOPPER", [FN.FD._centre(FN._room_points(used))], {"length_mm": round(total * 1000.0, 1)}, [], notes, facts, 0.5,
    mode="COUNT_X_LENGTH", work_item=code)
