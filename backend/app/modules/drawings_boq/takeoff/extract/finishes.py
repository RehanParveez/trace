from __future__ import annotations
import math
import re
from shapely.geometry import LineString, Point
from app.modules.drawings_boq.takeoff.orientation import axes as AX
from app.modules.drawings_boq.takeoff.extract import foundation as FD
from app.modules.drawings_boq.takeoff.extract import config as C

KACHA_FLOOR = "KACHA_FLOOR"
CEILING_PLASTER = "CEILING_PLASTER"
PLASTER_INSIDE = "PLASTER_INSIDE"
PLASTER_OUTSIDE = "PLASTER_OUTSIDE"
DOOR_FRAME = "DOOR_FRAME"
DOOR_AREA = "DOOR_AREA"
WINDOW_AREA = "WINDOW_AREA"
FLOOR_FINISH = "FLOOR_FINISH"
CEILING_PAINT = "CEILING_PAINT"
SKIRTING = "SKIRTING"
DADO = "DADO"
PAINT_INSIDE = "PAINT_INSIDE"
PAINT_OUTSIDE = "PAINT_OUTSIDE"
ITEMS = (KACHA_FLOOR, CEILING_PLASTER, PLASTER_INSIDE, PLASTER_OUTSIDE, DOOR_FRAME, DOOR_AREA, WINDOW_AREA, FLOOR_FINISH, CEILING_PAINT, SKIRTING, DADO, PAINT_INSIDE, PAINT_OUTSIDE)
OPENING_MIN_M2 = 0.5            

WORK_ITEM = {KACHA_FLOOR: "FLR-KACHA-BED", CEILING_PLASTER: "FIN-PLASTER", PLASTER_INSIDE: "FIN-PLASTER", PLASTER_OUTSIDE: "FIN-PLASTER", DOOR_FRAME: "JOI-DOOR-FRAME", DOOR_AREA: "JOI-DOOR-AREA", WINDOW_AREA: "JOI-WIN-AREA", FLOOR_FINISH: "FIN-FLOOR", CEILING_PAINT: "FIN-CEIL-PAINT", SKIRTING: "FIN-SKIRT", DADO: "FIN-DADO",
  PAINT_INSIDE: "FIN-PAINT", PAINT_OUTSIDE: "FIN-PAINT-EXT"}
SIDE = {PLASTER_INSIDE: "in", PLASTER_OUTSIDE: "out", PAINT_INSIDE: "in", PAINT_OUTSIDE: "out"}

def _make(cls, ctx: dict, finish, key_parts: tuple, item: str, label: str, tag: str, points: list, params: dict, missing: list, notes: list, facts: dict,
  base: float, count: int = 1, mode: str = "COUNT_X_AREA"):
  facts = {**facts, "foundation_item": item}
  cand = cls(key=FD._key_of(("FIN", *key_parts)), category="WALL", kind="COUNT", quantity_mode=mode, label=label, tag=tag, geometry={"points": points},
    params={**params, "dims_basis": "SPECIFIED"}, missing=missing, work_item=WORK_ITEM[item], status="VALID", confidence=0.0, facts=facts, notes=notes,
    source="VECTOR_SNAP", count=count)
  return finish(cand, ctx, base)

def room_total(rooms: list) -> tuple:
  """(total area in m2, rooms used, points) of the rooms of a floor, leaving out rooms with an error and rooms drawn inside another room."""
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
  return total, used, pts

def _area_item(item: str, rooms: list, ctx: dict, level_hint: str | None, spec, cls, finish, text: str, tag: str, note: str):
  total, used, pts = room_total(rooms)
  if used == 0:
    return None
  facts = {"derived_from": "ROOMS", "room_count": used, "area_m2": round(total, 3)}
  label = f"{text} · {total:.2f} m²" + (f" · {spec[0]}" if spec else "")
  return _make(cls, ctx, finish, (item, level_hint or ""), item, label, tag, [FD._centre(pts)], {"length_mm": round(total * 1000.0, 1), "width_mm": 1000.0}, [],
    [C.note(note)] + ([C.note("NO_WORK_ITEM")] if WORK_ITEM[item] is None else []), facts, 0.75)

def kacha_candidate(rooms: list, ctx: dict, level_hint: str | None, spec, cls, finish):
  """The concrete or kacha bed under the floor of this storey: the total of its room areas."""
  return _area_item(KACHA_FLOOR, rooms, ctx, level_hint, spec, cls, finish, "Kacha bed under the floor", "KACHA-FLOOR", "KACHA_FROM_ROOMS")

def ceiling_candidate(rooms: list, ctx: dict, level_hint: str | None, spec, cls, finish):
  """The plaster on the ceiling of this storey: the total of its room areas."""
  return _area_item(CEILING_PLASTER, rooms, ctx, level_hint, spec, cls, finish, "Ceiling plaster", "CEILING-PLASTER", "CEILING_FROM_ROOMS")

NOT_FINISHED = ("LIFT", "LAWN", "COURTYARD")
WET_ROOM = re.compile(r"^(?:BATH ?ROOM|BATH|TOILET|LAVATORY|W\.C|W/C|WC)(?![A-Z])")
DADO_HEIGHT_MM = 2134.0         
DOOR_ON_BOUNDARY_MM = 300.0
DOOR_WIDTH_ASSUMED_MM = 900.0     
DOOR_REACH = 1.5                
PAINT_ITEMS = ((PAINT_INSIDE, "in", "Paint on the inside faces of the walls", "PAINT-INSIDE"), (PAINT_OUTSIDE, "out", "Paint on the outside faces of the outer walls", "PAINT-OUTSIDE"))

def usable_rooms(rooms: list) -> list:
  """The rooms of a floor that count: not in error and not drawn inside another room, with an area."""
  out = []
  for r in rooms:
    f = r.facts or {}
    if r.category != "ROOM" or r.status == "INVALID" or any(n.get("code") == "ROOM_INSIDE_ROOM" for n in r.notes or []):
      continue
    if float(f.get("area_m2") or 0.0) > 0.0:
      out.append(r)
  return out

def _names(room) -> list:
  """The names of a room: a room read from the plan carries its name as `name`; a room with several labels inside carries them as `names`."""
  f = room.facts or {}
  out = [str(n).upper() for n in (f.get("names") or [])]
  if f.get("name"):
    out.append(str(f["name"]).upper())
  return out

def is_wet(room) -> bool:
  """A bath, toilet or W.C: it has a tile dado and no skirting."""
  return any(WET_ROOM.match(n) for n in _names(room))

def is_finished(room) -> bool:
  """A room whose floor is finished: not a lift shaft, a lawn or a courtyard."""
  return not any(w in NOT_FINISHED for n in _names(room) for w in re.split(r"[^A-Z]+", n))

def _room_points(rooms: list) -> list:
  pts = []
  for r in rooms:
    pts.extend((r.geometry or {}).get("outer") or (r.geometry or {}).get("points") or [])
  return pts

def floor_candidate(rooms: list, ctx: dict, level_hint: str | None, spec, cls, finish):
  """The floor finish of this storey: the total of its room areas, leaving out lift shafts, lawns and courtyards."""
  used = [r for r in usable_rooms(rooms) if is_finished(r)]
  if not used:
    return None
  total = sum(float(r.facts["area_m2"]) for r in used)
  wet = [r for r in used if is_wet(r)]
  wet_m2 = sum(float(r.facts["area_m2"]) for r in wet)
  facts = {"derived_from": "ROOMS", "room_count": len(used), "area_m2": round(total, 3), "wet_room_count": len(wet), "wet_room_area_m2": round(wet_m2, 3)}
  label = f"Floor finish · {total:.2f} m²" + (f" · {spec[0]}" if spec else "")
  return _make(cls, ctx, finish, (FLOOR_FINISH, level_hint or ""), FLOOR_FINISH, label, "FLOOR-FINISH", [FD._centre(_room_points(used))],
    {"length_mm": round(total * 1000.0, 1), "width_mm": 1000.0}, [], [C.note("FLOOR_FROM_ROOMS")], facts, 0.7)

def ceiling_paint_candidate(rooms: list, ctx: dict, level_hint: str | None, spec, cls, finish):
  """The paint on the ceiling of this storey: the same area as the ceiling plaster."""
  return _area_item(CEILING_PAINT, rooms, ctx, level_hint, spec, cls, finish, "Ceiling paint", "CEILING-PAINT", "CEILING_PAINT_FROM_ROOMS")

def door_assignment(rooms: list, doors: list, mm_per_pt: float) -> dict:
  """{id(room): (width of doors in m, number of doors, how many of them have an assumed width)}. A door opens into at most two rooms: the two whose outlines are nearest its centre, each within
  one and a half times the width of the door (or 300 mm if that is more). The centre of a door symbol is not on the wall line (the swing is part of it)."""
  lines = []
  for r in rooms:
    ring = (r.geometry or {}).get("outer") or []
    if len(ring) >= 3:
      lines.append((r, LineString([tuple(p) for p in ring] + [tuple(ring[0])])))
  out = {id(r): [0.0, 0, 0] for r in rooms}
  if lines and doors and mm_per_pt > 0.0:
    for d in doors:
      f = d.facts or {}
      size = f.get("size_schedule_mm") or f.get("size_drawn_mm")
      if d.category != "DOOR" or d.status == "INVALID":
        continue
      known = bool(size) and len(size) == 2 and float(size[0]) > 0.0
      width = float(size[0]) if known else DOOR_WIDTH_ASSUMED_MM
      tol = max(DOOR_ON_BOUNDARY_MM, DOOR_REACH * width) / mm_per_pt
      for p in (d.geometry or {}).get("points") or []:
        pt = Point(float(p[0]), float(p[1]))
        near = sorted(((ln.distance(pt), i) for i, (_, ln) in enumerate(lines)), key=lambda t: t[0])
        for dist, i in near[:2]:
          if dist <= tol:
            out[id(lines[i][0])][0] += width / 1000.0
            out[id(lines[i][0])][1] += 1
            out[id(lines[i][0])][2] += 0 if known else 1
  return {k: (v[0], v[1], v[2]) for k, v in out.items()}

def _lengths(rooms: list, assigned: dict) -> list:
  out = []
  for r in rooms:
    per = float((r.facts or {}).get("perimeter_m") or 0.0)
    door_m, n, assumed = assigned.get(id(r), (0.0, 0, 0))
    out.append({"room": r, "name": (_names(r) or ["ROOM"])[0], "perimeter_m": per, "doors_m": door_m, "doors": n, "assumed": assumed, "length_m": max(0.0, per - door_m)})
  return out

def _assumed_note(facts: dict) -> list:
  n = int(facts.get("doors_assumed_width") or 0)
  return [C.note("DOOR_WIDTH_ASSUMED", count=n)] if n else []

def _length_facts(rows: list) -> dict:
  return {"derived_from": "ROOMS", "room_count": len(rows), "perimeter_m": round(sum(x["perimeter_m"] for x in rows), 3),
    "doors_deducted_m": round(sum(x["doors_m"] for x in rows), 3), "door_count": sum(x["doors"] for x in rows),
    "doors_assumed_width": sum(x["assumed"] for x in rows), "length_m": round(sum(x["length_m"] for x in rows), 3),
    "rooms": [{"name": x["name"], "perimeter_m": round(x["perimeter_m"], 3), "doors_m": round(x["doors_m"], 3), "length_m": round(x["length_m"], 3)} for x in rows]}

def skirting_candidate(rooms: list, doors: list, mm_per_pt: float, ctx: dict, level_hint: str | None, spec, cls, finish):
  """The skirting of this storey: round every dry room, less the doors on its outline. Baths and toilets have a dado instead."""
  every = usable_rooms(rooms)
  used = [r for r in every if is_finished(r) and not is_wet(r)]
  rows = _lengths(used, door_assignment(every, doors, mm_per_pt))
  total = sum(x["length_m"] for x in rows)
  if total <= 0.0:
    return None
  facts = _length_facts(rows)
  label = f"Skirting · {total:.2f} m" + (f" · {spec[0]}" if spec else "")
  return _make(cls, ctx, finish, (SKIRTING, level_hint or ""), SKIRTING, label, "SKIRTING", [FD._centre(_room_points(used))], {"length_mm": round(total * 1000.0, 1)}, [],
    [C.note("SKIRTING_FROM_ROOMS"), C.note("SKIRTING_DOORS_BY_POSITION")] + _assumed_note(facts), facts, 0.6, mode="COUNT_X_LENGTH")

def dado_candidate(rooms: list, doors: list, mm_per_pt: float, ctx: dict, level_hint: str | None, spec, cls, finish):
  """The tile dado of this storey: round every bath and toilet, less the doors on its outline, times the dado height. Windows are not taken out."""
  every = usable_rooms(rooms)
  used = [r for r in every if is_wet(r)]
  rows = _lengths(used, door_assignment(every, doors, mm_per_pt))
  length = sum(x["length_m"] for x in rows)
  if length <= 0.0:
    return None
  area = length * DADO_HEIGHT_MM / 1000.0
  facts = {**_length_facts(rows), "dado_height_mm": DADO_HEIGHT_MM, "area_m2": round(area, 3)}
  label = f"Dado in baths and toilets · {area:.2f} m² · {DADO_HEIGHT_MM / 1000.0:.3f} m high" + (f" · {spec[0]}" if spec else "")
  return _make(cls, ctx, finish, (DADO, level_hint or ""), DADO, label, "DADO", [FD._centre(_room_points(used))], {"length_mm": round(area * 1000.0, 1), "width_mm": 1000.0}, [],
    [C.note("DADO_FROM_ROOMS"), C.note("DADO_HEIGHT_DEFAULT"), C.note("DADO_WINDOWS_NOT_DEDUCTED")] + _assumed_note(facts), facts, 0.55)

def paint_candidates(walls: list, mm_per_pt: float, ctx: dict, level_hint: str | None, spec, cls, finish, dado_m2: float = 0.0) -> list:
  faces = plaster_faces(walls, mm_per_pt)
  if not faces:
    return []
  pts = [p for w in plaster_walls(walls) for p in w.geometry["points"]]
  centre = [FD._centre(pts)]
  outer = sum(1 for r in faces if r["out"])
  out = []
  for item, side, text, tag in PAINT_ITEMS:
    if sum(r[side] for r in faces) == 0:
      continue
    
    face_len = sum(r[side] * r["l"] for r in faces)
    open_m2 = sum(r[side] * r["o"] for r in faces)
    less = dado_m2 if side == "in" else 0.0
    area = plaster_area(faces, side)
    
    if area is not None:
      area = max(0.0, area - less)
    facts = {"derived_from": "WALLS", "plaster_side": side, "wall_count": len(faces), "outer_wall_count": outer, "face_length_m": round(face_len, 3),
      "opening_m2": round(open_m2, 3), "less_dado_m2": round(less, 3), "faces": faces}
    if area is not None:
      facts["area_m2"] = round(area, 3)
    notes = [C.note("PAINT_FROM_PLASTER"), C.note("PLASTER_OUTER_BY_OUTLINE")]
    if area is None:
      notes.append(C.note("PLASTER_HEIGHT_FROM_WALLS"))
    if area is not None and area <= 0.0:
      continue
    
    label = f"{text} · {face_len:.2f} m of face" + (f" · {spec[0]}" if spec else "")
    params = {"length_mm": round(area * 1000.0, 1), "width_mm": 1000.0} if area is not None else {}
    out.append(_make(cls, ctx, finish, (item, level_hint or ""), item, label, tag, centre, params, [] if params else ["height_mm"], notes, facts, 0.55))
  return out

def _opening_m2(params: dict) -> float:
  total = 0.0
  for o in (params or {}).get("openings") or []:
    if isinstance(o, dict):
      each = float(o.get("width_mm") or 0.0) * float(o.get("height_mm") or 0.0) / 1e6
      if each >= OPENING_MIN_M2:
        total += float(o.get("nos") or 0) * each
  return total

def plaster_walls(walls: list) -> list:
  """The walls whose faces are plastered: every wall of the floor except tank walls and walls with an error."""
  out = []
  for w in walls:
    f = w.facts or {}
    if w.category != "WALL" or f.get("enclosure") == "TANK" or w.status == "INVALID":
      continue
    if float(f.get("length_cc_m") or 0.0) <= 0.0 or len((w.geometry or {}).get("points") or []) < 2:
      continue
    out.append(w)
  return out

def _turned(p, turn: float) -> tuple:
  return (p[0], p[1]) if not turn else AX.turn(p[0], p[1], -turn)

def _is_outer(w, box: tuple, mm_per_pt: float, turn: float = 0.0) -> bool:
  pts = w.geometry["points"]
  (a, b), (c, d) = _turned(pts[0], turn), _turned(pts[-1], turn)
  t = float((w.facts or {}).get("thickness_used_mm") or 228.6)
  tol = t * C.OUTER_WALL_TOL_FACTOR / mm_per_pt
  x0, y0, x1, y1 = box
  if abs(a - c) <= tol < abs(b - d):
    return abs(a - x0) <= tol or abs(a - x1) <= tol
  if abs(b - d) <= tol < abs(a - c):
    return abs(b - y0) <= tol or abs(b - y1) <= tol
  return False

def plan_angle(ws: list) -> float:
  items = []
  for w in ws:
    (a, b), (c, d) = w.geometry["points"][0], w.geometry["points"][-1]
    items.append((math.degrees(math.atan2(d - b, c - a)), float((w.facts or {}).get("length_cc_m") or 0.0)))
  return AX.axes(items)

def plaster_faces(walls: list, mm_per_pt: float) -> list:
  ws = plaster_walls(walls)
  if not ws:
    return []
  turn = plan_angle(ws)
  
  ends = [_turned(p, turn) for w in ws for p in (w.geometry["points"][0], w.geometry["points"][-1])]
  xs = [p[0] for p in ends]
  ys = [p[1] for p in ends]
  box = (min(xs), min(ys), max(xs), max(ys))
  
  out = []
  for w in ws:
    outer = _is_outer(w, box, mm_per_pt, turn)
    h = (w.facts or {}).get("clear_height_mm") or (w.params or {}).get("height_mm")
    out.append({"l": round(float(w.facts["length_cc_m"]), 3), "h": float(h) if h else None, "o": round(_opening_m2(w.params), 3), "in": 1 if outer else 2,
      "out": 1 if outer else 0})
  return out

def plaster_area(faces: list, side: str, typed_height_mm: float | None = None) -> float | None:
  """Net plastered area in m2 for the faces on one side, or None while a wall that needs a height has none."""
  total = 0.0
  for r in faces:
    n = int(r.get(side) or 0)
    if n <= 0:
      continue
    h = r.get("h") or typed_height_mm
    if not h:
      return None
    total += n * max(0.0, float(r["l"]) * float(h) / 1000.0 - float(r.get("o") or 0.0))
  return total

def plaster_candidates(walls: list, mm_per_pt: float, ctx: dict, level_hint: str | None, spec, cls, finish) -> list:
  """The wall plaster of a floor as two items: the inside faces (an outer wall once, an inside wall twice) and the outside faces of the outer walls."""
  faces = plaster_faces(walls, mm_per_pt)
  if not faces:
    return []

  pts = [p for w in plaster_walls(walls) for p in w.geometry["points"]]
  centre = [FD._centre(pts)]
  outer = sum(1 for r in faces if r["out"])
  out = []
  
  for item, side, text, tag in ((PLASTER_INSIDE, "in", "Plaster on the inside faces of the walls", "PLASTER-INSIDE"),
    (PLASTER_OUTSIDE, "out", "Plaster on the outside faces of the outer walls", "PLASTER-OUTSIDE")):
    count_faces = sum(r[side] for r in faces)
    if count_faces == 0:
      continue
  
    face_len = sum(r[side] * r["l"] for r in faces)
    open_m2 = sum(r[side] * r["o"] for r in faces)
    area = plaster_area(faces, side)
    facts = {"derived_from": "WALLS", "plaster_side": side, "wall_count": len(faces), "outer_wall_count": outer, "face_length_m": round(face_len, 3),
      "opening_m2": round(open_m2, 3), "faces": faces}
    if area is not None:
      facts["area_m2"] = round(area, 3)
    notes = [C.note("PLASTER_FROM_WALLS"), C.note("PLASTER_OUTER_BY_OUTLINE")]
    if item == PLASTER_OUTSIDE:
      notes.append(C.note("PLASTER_OUTSIDE_SEPARATE"))
    if area is None:
      notes.append(C.note("PLASTER_HEIGHT_FROM_WALLS"))
    if area is not None and area <= 0.0:
      continue
    label = f"{text} · {face_len:.2f} m of face" + (f" · {spec[0]}" if spec else "")
    params = {"length_mm": round(area * 1000.0, 1), "width_mm": 1000.0} if area is not None else {}
    missing = [] if params else ["height_mm"]
    out.append(_make(cls, ctx, finish, (item, level_hint or ""), item, label, tag, centre, params, missing, notes, facts, 0.6))
  return out

def door_hosts(walls: list) -> dict:
  """For each door mark, how many of its doors were found in thin walls and how many in thicker walls."""
  hosts: dict = {}
  for w in plaster_walls(walls):
    t = float((w.facts or {}).get("thickness_used_mm") or 0.0)
    if t <= 0.0:
      continue
    key = "thin" if t < C.FOUNDATION_THIN_WALL_MAX_MM else "thick"
    for o in (w.params or {}).get("openings") or []:
      if isinstance(o, dict) and o.get("role") == "DOOR" and o.get("label"):
        h = hosts.setdefault(str(o["label"]).upper(), {"thin": 0, "thick": 0})
        h[key] += int(o.get("nos") or 1)
  return hosts

def door_frame_candidates(doors: list, walls: list, ctx: dict, level_hint: str | None, spec, cls, finish) -> list:
  """The frames of the doors of a floor: for every door mark, the two sides and the top of the door times the width of the frame. The width of the frame
  is the thickness of the wall the door stands in, so the doors of a mark are asked for the thin or the thick width by the walls they were found in."""
  hosts = door_hosts(walls)
  out = []
  
  for d in doors:
    f = d.facts or {}
    size = f.get("size_schedule_mm") or f.get("size_drawn_mm")
    if d.category != "DOOR" or d.status == "INVALID" or not d.tag or not size or len(size) != 2:
      continue
    width, height = float(size[0]), float(size[1])
    if width <= 0.0 or height <= 0.0:
      continue
    pts = [list(p) for p in ((d.geometry or {}).get("points") or [])]
    if not pts:
      continue
  
    h = hosts.get(str(d.tag).upper(), {"thin": 0, "thick": 0})
    found = h["thin"] + h["thick"]
    thin = found > 0 and h["thin"] / found >= C.DOOR_FRAME_THIN_SHARE
    facts = {"derived_from": "DOORS", "door_key": d.key, "door_tag": d.tag, "door_count": len(pts), "size_mm": [width, height],
      "frame_class": "THIN" if thin else "THICK", "hosts": h}
    if f.get("view"):
      facts["view"] = f["view"]
    where = f" · {spec[0]}" if spec else ""
    out.append(_make(cls, ctx, finish, (DOOR_FRAME, d.key), DOOR_FRAME, f"Door frames {d.tag} ×{len(pts)} · {width:g}×{height:g} mm{where}", f"FRAME-{d.tag}", pts,
      {"length_mm": round(2.0 * height + width, 1)}, ["frame_width_mm"], [C.note("DOOR_FRAME_FROM_DOORS"), C.note("DOOR_FRAME_WIDTH_BY_WALL")],
      facts, 0.7, count=len(pts)))
  return out

def fill_finish(item: str, missing: list, params: dict, typed: dict, facts: dict) -> tuple:
  """(params, problem) for a finish item: the frame width or the wall height typed at accept."""
  out = dict(params or {})
  facts = facts or {}
  
  for need in missing or []:
    if need == "frame_width_mm":
      thin = facts.get("frame_class") == "THIN"
      value = typed.get("door_frame_width_thin_mm" if thin else "door_frame_width_mm")
      if value is None:
        return out, ("CANDIDATE_NEEDS_DIMENSIONS", f"Give the width of the door frame in {'thin walls (under 6 inches)' if thin else 'walls of 6 inches and thicker'} to measure this item.")
      out["width_mm"] = float(value)
    elif need == "height_mm" and item in SIDE:
      value = typed.get("wall_height_mm")
      if value is None:
        return out, ("CANDIDATE_NEEDS_DIMENSIONS", "Give the wall height to measure this item.")
      area = plaster_area(facts.get("faces") or [], SIDE[item], float(value))
      if area is not None:
        area -= float(facts.get("less_dado_m2") or 0.0)
      if not area or area <= 0.0:
        return out, ("CANDIDATE_NEEDS_DIMENSIONS", "No plastered area was found for this item. Draw it by hand.")
      out["length_mm"], out["width_mm"] = round(area * 1000.0, 1), 1000.0
    else:
      return out, ("CANDIDATE_NEEDS_DIMENSIONS", "No size was found for this item. Draw it by hand.")
  out["dims_basis"] = "SPECIFIED"
  return out, None
