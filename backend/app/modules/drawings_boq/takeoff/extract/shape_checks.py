from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import crosschecks as CK
import statistics
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.extract.hosts import ROLE_OF

def _geometry(c) -> dict:
  return getattr(c, "geometry", None) or {}

def _params(c) -> dict:
  return getattr(c, "params", None) or {}

def _walls(cands: list) -> list:
  out = []
  for c in cands:
    f = c.facts or {}
    pts = _geometry(c).get("points") or []
    if c.category == "WALL" and CK._live(c) and not c.tag and len(pts) >= 2 and float(f.get("length_cc_m") or 0.0) > 0.0 and float(f.get("thickness_used_mm") or 0.0) > 0.0:
      out.append(c)
  return out

def _wall_scale(walls: list) -> float | None:
  vals = []
  
  for w in walls:
    p0, p1 = w.geometry["points"][0], w.geometry["points"][1]
    d = ((p1[0] - p0[0]) ** 2 + (p1[1] - p0[1]) ** 2) ** 0.5
    if d > 0:
      vals.append(float(w.facts["length_cc_m"]) * 1000.0 / d)
  return statistics.median(vals) if vals else None

def _bands(walls: list, mm_per_pt: float, slack_mm: float) -> list:
  out = []
  for w in walls:
    pts = [tuple(p) for p in w.geometry["points"][:2]]
    half = (float(w.facts["thickness_used_mm"]) / 2.0 + slack_mm) / mm_per_pt
    out.append(LineString(pts).buffer(half, cap_style=3))
  return out

def _polygon(room) -> Polygon | None:
  g = _geometry(room)
  try:
    poly = Polygon(g["outer"]) if g.get("outer") else None
  except Exception:
    return None
  return poly if poly is not None and poly.is_valid and not poly.is_empty else None

def _by_floor(read: list):
  for sh in read:
    sf = CK._sheet_floor(sh)
    groups: dict = {}
    for c in sh["candidates"]:
      fl = CK._floor(c, sf)
      if fl:
        groups.setdefault(fl, []).append(c)
    for fl in sorted(groups, key=lambda k: (CK._rank(k), k)):
      yield sh, fl, groups[fl]

def _wall_rooms(cands: list) -> list:
  return [c for c in cands if c.category == "ROOM" and CK._live(c) and (c.facts or {}).get("outline_from") == "WALLS" and not CK.OUTDOOR.search(str((c.facts or {}).get("name") or ""))
    and _polygon(c) is not None]

def _room_scale(rooms: list) -> float | None:
  vals = []
  for r in rooms:
    poly, per = _polygon(r), float((r.facts or {}).get("perimeter_m") or 0.0)
    if poly is not None and per > 0 and poly.exterior.length > 0:
      vals.append(per * 1000.0 / poly.exterior.length)
  return statistics.median(vals) if vals else None

def _name(room) -> str:
  return str((room.facts or {}).get("name") or "a room without a name")

def walls_close_rooms(read: list) -> list:
  out: list = []
  for sh, fl, cands in _by_floor(read):
    rooms, walls = _wall_rooms(cands), _walls(cands)
    if not rooms:
      continue
    if not walls:
      out.append(CK._check("FLOOR_HAS_NO_WALLS", CK.INFO, fl, f"{len(rooms)} rooms were outlined from walls on the {fl.title()} floor (page {sh['page_no']}) but no wall of the floor is stored to set them against.", [sh["page_no"]], rooms=len(rooms)))
      continue
    scale = _room_scale(rooms) or _wall_scale(walls)
    if not scale:
      continue
    band = unary_union(_bands(walls, scale, C.CHECK_WALL_SLACK_MM))
    cover = []
    
    for r in rooms:
      ring = _polygon(r).exterior
      cover.append((_name(r), ring.intersection(band).length / ring.length if ring.length else 0.0))
    open_ = sorted((c for c in cover if c[1] < C.CHECK_WALL_CLOSED), key=lambda c: c[1])
    if open_:
      shown = "; ".join(f"{n} {v * 100:.0f}%" for n, v in open_[:5]) + (f"; and {len(open_) - 5} more" if len(open_) > 5 else "")
      out.append(CK._check("WALLS_OPEN_ROUND_ROOMS", CK.WARN, fl, f"On the {fl.title()} floor (page {sh['page_no']}) {len(open_)} of {len(rooms)} rooms have no wall along part of their outline: {shown}. A wall is missing, "
        f"or the outline is not a room.", [sh["page_no"]], rooms=len(rooms), open=len(open_), worst=round(open_[0][1], 3)))
    else:
      out.append(CK._check("WALLS_CLOSE_ROUND_ROOMS", CK.PASS, fl, f"Walls run along the whole outline of all {len(rooms)} rooms of the {fl.title()} floor (page {sh['page_no']}).", [sh["page_no"]], rooms=len(rooms), least=round(min(c[1] for c in cover), 3)))
  return out

def wall_length_vs_perimeter(read: list) -> list:
  out: list = []
  for sh, fl, cands in _by_floor(read):
    rooms, walls = _wall_rooms(cands), _walls(cands)
    indoor = [c for c in cands if c.category == "ROOM" and CK._live(c) and not CK.OUTDOOR.search(str((c.facts or {}).get("name") or ""))]
    if not rooms or not walls or len(rooms) < C.CHECK_WALL_ROOMS_SHARE * len(indoor):
      continue
  
    sides = round(sum(float((r.facts or {}).get("perimeter_m") or 0.0) for r in rooms), 2)
    length = round(sum(float(w.facts["length_cc_m"]) for w in walls), 2)
    ratio = round(sides / length, 3)
    head = f"The sides of the {len(rooms)} rooms of the {fl.title()} floor (page {sh['page_no']}) add up to {sides:g} m against {length:g} m of wall"
    if ratio > C.CHECK_WALL_PERIM_MAX:
      out.append(CK._check("WALL_SHORT_FOR_ROOMS", CK.WARN, fl, head + ". Every wall can bound at most two rooms, so wall is missing or a room is outlined where there is none.", [sh["page_no"]], sides_m=sides, wall_m=length, ratio=ratio))
    elif ratio < C.CHECK_WALL_PERIM_MIN:
      out.append(CK._check("WALL_LONGER_THAN_ROOMS", CK.INFO, fl, head + ". More wall is stored than the rooms enclose: a boundary wall, a wall outside the plan, or a room that was not outlined.", [sh["page_no"]], sides_m=sides, wall_m=length, ratio=ratio))
    else:
      out.append(CK._check("WALL_FITS_ROOMS", CK.PASS, fl, head + ", which is what walls shared by two rooms and walls with the outside on one side leave.", [sh["page_no"]], sides_m=sides, wall_m=length, ratio=ratio))
  return out

def openings_in_walls(read: list) -> list:
  out: list = []
  for sh, fl, cands in _by_floor(read):
    walls = _walls(cands)
    if not any((w.facts or {}).get("openings") for w in walls):
      continue
    sized = sum(int(c.count or 1) for c in cands if c.category in ("DOOR", "WINDOW") and CK._live(c) and (c.facts or {}).get("size_schedule_mm") and ROLE_OF.get((c.facts or {}).get("opening_kind") or c.category))
    held = sum(int(w.facts["openings"].get("count") or 0) for w in walls if w.facts.get("openings"))
    
    too_wide = []
    for w in walls:
      ops = _params(w).get("openings") or []
      width = sum(float(o["width_mm"]) * int(o["nos"]) for o in ops)
      if ops and width > C.CHECK_OPENINGS_FILL * float(w.facts["length_cc_m"]) * 1000.0:
        too_wide.append((float(w.facts["length_cc_m"]), width / 1000.0, sum(int(o["nos"]) for o in ops)))
        
    if too_wide:
      shown = "; ".join(f"{n} openings, {wd:.2f} m wide, in a wall {ln:.2f} m long" for ln, wd, n in too_wide[:4])
      out.append(CK._check("OPENINGS_WIDER_THAN_WALL", CK.WARN, fl, f"On the {fl.title()} floor (page {sh['page_no']}): {shown}. An opening was given to a wall it does not belong to, or the wall is cut short.", [sh["page_no"]], walls=len(too_wide)))
    if sized:
      lost = sized - held
      if lost > 0 and lost / sized > C.CHECK_OPENINGS_LOST_SHARE:
        out.append(CK._check("OPENINGS_IN_NO_WALL", CK.WARN, fl, f"{lost} of the {sized} doors and windows of the {fl.title()} floor (page {sh['page_no']}) sit in no wall: {held} were found in a wall. "
          "Each is a mark with no wall near it, so its wall is not stored or its position is off.", [sh["page_no"]], sized=sized, held=held))
      elif not too_wide:
        out.append(CK._check("OPENINGS_IN_WALLS", CK.PASS, fl, f"{f'All {sized}' if lost <= 0 else f'All but {lost} of the {sized}'} sized doors and windows of the {fl.title()} floor (page {sh['page_no']}) sit in a wall, and no wall holds more opening than it is long.", [sh["page_no"]], sized=sized, held=held))
  return out

def _ring_m(walls: list) -> float | None:
  scale = _wall_scale(walls)
  if not scale:
    return None
  merged = unary_union(_bands(walls, scale, 0.0))
  parts = list(merged.geoms) if hasattr(merged, "geoms") else [merged]
  polys = [p for p in parts if isinstance(p, Polygon) and not p.is_empty]
  if not polys:
    return None
  return max(polys, key=lambda p: p.area).exterior.length * scale / 1000.0

def parapet_vs_ring(read: list) -> list:
  out: list = []
  floors: dict = {}
  
  for sh, fl, cands in _by_floor(read):
    floors.setdefault(fl, []).extend(_walls(cands))
  for sh in read:
    for c in sh["candidates"]:
      f = c.facts or {}
      if c.category != "SITE" or f.get("site_kind") != "PARAPET" or not CK._live(c) or not f.get("slab_level"):
        continue
      fl = f["slab_level"]
      ring = _ring_m(floors.get(fl, []))
      if ring is None:
        continue
      printed = float(_params(c).get("length_mm") or 0.0) / 1000.0
      pages = [sh["page_no"]]
      
      if printed <= 0:
        out.append(CK._check("PARAPET_LENGTH_FROM_RING", CK.INFO, fl, f"The plan prints a parapet but no length for it. The outer walls of the {fl.title()} floor close round {ring:.1f} m; type that, or the length it really runs, when you accept.", pages, ring_m=round(ring, 2)))
        continue
      ratio = printed / ring
      head = f"The parapet is {printed:.1f} m long (from the area table) and the outer walls of the {fl.title()} floor close round {ring:.1f} m"
      if abs(ratio - 1.0) > C.CHECK_PARAPET_RING_TOL:
        out.append(CK._check("PARAPET_DIFFERS_FROM_RING", CK.WARN, fl, head + ". A parapet that is set back, or round a projection, has another length; otherwise the outline or the walls are wrong.", pages, parapet_m=round(printed, 2), ring_m=round(ring, 2), ratio=round(ratio, 3)))
      else:
        out.append(CK._check("PARAPET_FITS_RING", CK.PASS, fl, head + ": the same building.", pages, parapet_m=round(printed, 2), ring_m=round(ring, 2), ratio=round(ratio, 3)))
  return out

def balcony_and_slab(read: list) -> list:
  slabs = CK._slabs(read)
  out: list = []
  for sh in read:
    sf = CK._sheet_floor(sh)
    for fl in sorted({CK._floor(c, sf) for c in sh["candidates"] if c.category == "ROOM"} - {None}, key=lambda k: (CK._rank(k), k)):
      rooms = [c for c in sh["candidates"] if c.category == "ROOM" and CK._live(c) and CK._floor(c, sf) == fl]
      balc = [c for c in rooms if "BALCON" in str((c.facts or {}).get("name") or "").upper()]
      slab = slabs.get(fl)
      if not balc or slab is None:
        continue
    
      indoor = sum(float((c.facts or {}).get("area_m2") or 0.0) for c in rooms if not CK.OUTDOOR.search(str((c.facts or {}).get("name") or "")))
      b = sum(float((c.facts or {}).get("area_m2") or 0.0) for c in balc)
      s = slab["area_m2"]
      without, with_ = indoor / s, (indoor + b) / s
      pages = [sh["page_no"], slab["page_no"]]
      nums = dict(rooms_m2=round(indoor, 2), balcony_m2=round(b, 2), slab_m2=s)
      lo, hi = C.CHECK_ROOMS_MIN_RATIO, C.CHECK_ROOMS_MAX_RATIO
      
      head = f"The balcony of the {fl.title()} floor is {b:g} m²; the rooms add up to {indoor:g} m² and the slab covers {s:g} m²"
      if without < lo <= with_ <= hi:
        out.append(CK._check("BALCONY_IN_SLAB", CK.WARN, fl, head + ". The rooms only fill the slab once the balcony is counted with them, so the covered area includes it. Do not accept a balcony slab as well: it would be counted twice.", pages, **nums))
      elif with_ > hi and lo <= without <= hi:
        out.append(CK._check("BALCONY_OUTSIDE_SLAB", CK.PASS, fl, head + ". The rooms fill the slab without the balcony, so the balcony is outside the covered area and a slab of its own is right.", pages, **nums))
  return out

def run(read: list) -> list:
  return [*walls_close_rooms(read), *wall_length_vs_perimeter(read), *openings_in_walls(read), *parapet_vs_ring(read), *balcony_and_slab(read)]
