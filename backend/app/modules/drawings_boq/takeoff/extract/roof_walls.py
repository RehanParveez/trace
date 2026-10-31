from __future__ import annotations
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.extract import finish_rules as FR
from app.modules.drawings_boq.takeoff.prep.facts import FLOOR_ORDER
from app.modules.drawings_boq.takeoff.model import levels as LV

PARAPET, MUMTY, UNCLASSED = "PARAPET", "MUMTY", "UNCLASSED"
PARAPET_RULE = "stage.parapet_height_mm"
SIDE_MIN_SHARE = 0.6
STEP_MM = 800.0
CLEAR_MM = 150.0

def _live(w) -> bool:
  f = w.facts or {}
  return (w.category == "WALL" and w.status != "INVALID" and f.get("enclosure") != "TANK" and not f.get("foundation_item") and float(f.get("length_cc_m") or 0.0) > 0.0
    and len((w.geometry or {}).get("points") or []) >= 2)

def _half_pt(w, f: float) -> float:
  t = float((w.facts or {}).get("thickness_used_mm") or (w.params or {}).get("thickness_mm") or (w.facts or {}).get("thickness_mm") or 114.3)
  return t / 2.0 / f

def _line(w) -> LineString:
  pts = w.geometry["points"]
  return LineString([tuple(pts[0][:2]), tuple(pts[-1][:2])])

def outline(walls: list, f: float):
  parts = [_line(w).buffer(_half_pt(w, f), cap_style=3) for w in walls]
  if not parts:
    return None
  reach = C.OUTLINE_CLOSE_MM / f
  joined = unary_union(parts).buffer(reach).buffer(-reach)
  rings = [Polygon(g.exterior) for g in (joined.geoms if hasattr(joined, "geoms") else [joined]) if not g.is_empty]
  shape = unary_union(rings) if rings else None
  return shape if shape is not None and shape.area > 0.0 else None

def _samples(w, f: float) -> list:
  ln = _line(w)
  length = ln.length
  if length <= 0.0:
    return []
  n = max(3, int(length * f / STEP_MM))
  (x0, y0), (x1, y1) = ln.coords[0], ln.coords[-1]
  ux, uy = (x1 - x0) / length, (y1 - y0) / length
  return [((x0 + (x1 - x0) * (i + 0.5) / n, y0 + (y1 - y0) * (i + 0.5) / n), -uy, ux) for i in range(n)]

def _room_shapes(rooms: list) -> list:
  out = []
  for r in rooms:
    if r.category != "ROOM" or r.status == "INVALID":
      continue
    g = r.geometry or {}
    pts = g.get("outer") or g.get("points") or []
    if len(pts) >= 3:
      p = Polygon([tuple(q[:2]) for q in pts])
      if p.is_valid and p.area > 0.0:
        out.append(p)
  return out

def classify(walls: list, rooms: list, f: float) -> dict:
  live = [w for w in walls if _live(w)]
  shape = outline(live, f)
  room_shapes = _room_shapes(rooms)
  out: dict = {}
  for w in live:
    samples = _samples(w, f)
    if not samples:
      continue
    reach = _half_pt(w, f) + CLEAR_MM / f
    outer_side = inner_side = in_room = 0
    
    for (x, y), nx, ny in samples:
      a, b = Point(x + nx * reach, y + ny * reach), Point(x - nx * reach, y - ny * reach)
      ia, ib = shape is not None and shape.contains(a), shape is not None and shape.contains(b)
      if shape is not None and (ia != ib):
        outer_side += 1
      elif ia and ib:
        inner_side += 1
      if any(p.contains(a) or p.contains(b) for p in room_shapes):
        in_room += 1
    n = len(samples)
    
    if shape is not None and outer_side / n >= SIDE_MIN_SHARE:
      out[w.key] = PARAPET
    elif in_room / n >= SIDE_MIN_SHARE or (inner_side / n >= SIDE_MIN_SHARE and room_shapes and in_room > 0):
      out[w.key] = MUMTY
    else:
      out[w.key] = UNCLASSED
  return out

def parapet_height() -> tuple:
  rv = FR.rule(PARAPET_RULE)
  try:
    mm = float(rv.value)
  except (TypeError, ValueError):
    mm = 0.0
  return (mm if mm > 0.0 else None), FR.evidence(PARAPET_RULE, rv)

def top_storey(floor_heights: dict | None, level_hint: str | None, storey_height) -> tuple:
  for k in reversed([k for k in FLOOR_ORDER if k in (floor_heights or {}) and k != "BASEMENT"]):
    if k == str(level_hint or "").upper() or k == "ROOF":
      continue
    entry = storey_height(k)
    if entry and entry.get("mm"):
      return k, entry
  return None, None

def _label(w, name: str, height_mm: float) -> str:
  f = w.facts or {}
  t = float(f.get("thickness_used_mm") or (w.params or {}).get("thickness_mm") or 0.0)
  return f"{name} {t:g} mm · {float(f.get('length_cc_m') or 0.0):.2f} m · {height_mm / 304.8:.1f} ft high"

def apply(walls: list, rooms: list, f: float, floor_heights: dict | None, level_hint: str | None, storey_height, notes_fn, height_notes, status_fn) -> dict:
  tally = {PARAPET: {"walls": 0, "metres": 0.0}, MUMTY: {"walls": 0, "metres": 0.0}, UNCLASSED: {"walls": 0, "metres": 0.0}, "mumty_floor": None, "mumty_mm": None, "parapet_mm": None}
  todo = [w for w in walls if _live(w) and not (w.params or {}).get("height_mm")]
  if not todo:
    return tally
  kinds = classify(todo, rooms, f)
  para_mm, para_ev = parapet_height()
  
  floor, entry = top_storey(floor_heights, level_hint, storey_height)
  tally["mumty_floor"], tally["mumty_mm"], tally["parapet_mm"] = floor, (float(entry["mm"]) if entry else None), para_mm
  para_entry = {"mm": para_mm, "text": f"parapet height {para_mm / 304.8:.1f} ft from the rule {PARAPET_RULE}", "basis": "RULE", "origin": para_ev.get("origin"), "ladder": LV.rule_source("PARAPET_HEIGHT", level_hint, PARAPET_RULE)} if para_mm else None
  for w in todo:
    kind = kinds.get(w.key)
    if kind is None:
      continue
  
    length = float((w.facts or {}).get("length_cc_m") or 0.0)
    tally[kind]["walls"] += 1
    tally[kind]["metres"] = round(tally[kind]["metres"] + length, 3)
    w.facts = {**(w.facts or {}), "roof_wall": kind}
    
    if kind == UNCLASSED:
      w.notes.append(notes_fn("ROOF_WALL_UNCLASSED"))
    elif kind == PARAPET and para_mm:
      w.params["height_mm"], w.params["dims_basis"] = para_mm, "SPECIFIED"
      w.facts["height_rule"] = para_ev
      w.notes.extend([notes_fn("ROOF_WALL_PARAPET", height_mm=para_mm), *height_notes(para_entry)])
      w.label = _label(w, "Parapet wall", para_mm)
    elif kind == MUMTY and entry and entry.get("mm"):
      w.params["height_mm"], w.params["dims_basis"] = float(entry["mm"]), "SPECIFIED"
      w.facts["height_floor"] = floor
      w.notes.extend([notes_fn("ROOF_WALL_MUMTY", height_mm=float(entry["mm"]), floor=floor), *height_notes(entry)])
      w.label = _label(w, "Mumty wall", float(entry["mm"]))
    else:
      w.notes.append(notes_fn("ROOF_WALL_UNCLASSED"))
      continue
  
    w.missing = [m for m in w.missing if m != "height_mm"]
    w.status = status_fn(w.notes)
  return tally
