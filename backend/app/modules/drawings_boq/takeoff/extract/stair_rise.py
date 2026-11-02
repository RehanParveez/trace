from __future__ import annotations
import copy
import math
from app.modules.drawings_boq.takeoff.model import levels as LV
from app.modules.drawings_boq.takeoff.prep import stairs as STR
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.extract import note_scope as NS
from app.modules.drawings_boq.takeoff.extract import room_types as RT

ABOVE_GROUND = ("BASEMENT", "GROUND", "MEZZANINE", "FIRST", "SECOND", "THIRD", "FOURTH")

def _drawn(rows: list) -> list:
  out = []
  for r in rows:
    for c in r.get("candidates") or []:
      f = c.facts or {}
      if c.category == "STAIR" and "size" in (c.missing or []) and f.get("treads_drawn") and f.get("tread_drawn_mm") and f.get("stair_width_mm") and f.get("floor_hint") in ABOVE_GROUND and c.status != "INVALID":
        out.append((r, c))
  return out

def _steps(c) -> int:
  return int(c.facts["treads_drawn"]) + 1

def _paired(flights: list) -> dict:
  floors = sorted({c.facts["floor_hint"] for _r, c in flights}, key=ABOVE_GROUND.index)
  
  out: dict = {}
  for fl in floors:
    up = [(r, c) for r, c in flights if c.facts["floor_hint"] == fl and c.facts.get("direction") == "UP"]
    if not up:
      continue
    above = [x for x in floors if ABOVE_GROUND.index(x) > ABOVE_GROUND.index(fl)]
    down = [(r, c) for x in above[:1] for r, c in flights if c.facts["floor_hint"] == x and c.facts.get("direction") == "DOWN"]
    out[fl] = (up, down)
  return out

def _hall(row: dict) -> tuple:
  best = (0.0, None)
  for r in row.get("candidates") or []:
    if r.category == "ROOM" and r.status != "INVALID" and RT.of_room(r) == RT.STAIR:
      area, ring = float((r.facts or {}).get("area_m2") or 0.0), (r.geometry or {}).get("outer") or []
      if area > best[0] and ring:
        xs, ys = [p[0] for p in ring], [p[1] for p in ring]
        best = (area, [[round((min(xs) + max(xs)) / 2.0, 3), round((min(ys) + max(ys)) / 2.0, 3)]])
  return best

def apply(rows: list, heights: dict | None, waist_mm: float | None = None) -> dict:
  waist = float(waist_mm or C.STAIR_WAIST_DEFAULT_MM)
  flights = _drawn(rows)
  tally = {"flights": len(flights), "sized": 0, "held": 0, "landings": 0, "landing_m2": 0.0, "stairs": []}
  for floor, (up, down) in _paired(flights).items():
    f2f, src = LV.height(heights, LV.FLOOR_TO_FLOOR, floor)
    if not f2f:
      tally["held"] += len(up) + len(down)
      tally["stairs"].append({"floor": floor, "held": "NO_STOREY_HEIGHT"})
      continue
    if len(up) != 1 or len(down) > 1:
      tally["held"] += len(up) + len(down)
      tally["stairs"].append({"floor": floor, "held": "SEVERAL_FLIGHTS", "up": len(up), "down": len(down)})
      continue
  
    (r, c), parts = up[0], [x for x in [*up, *down]]
    risers = sum(_steps(x) for _r, x in parts)
    riser = float(f2f) / risers
    f = c.facts
    spec = {"riser_mm": riser, "tread_mm": float(f["tread_drawn_mm"]), "width_mm": float(f["stair_width_mm"]), "steps": risers}
    box = STR.flight_box(spec, waist)
    if not box:
      tally["held"] += len(parts)
      continue
  
    needed = math.ceil(float(f2f) / C.STAIR_RISER_MAX_MM)
    c.params = {**(c.params or {}), **box, "dims_basis": "SPECIFIED"}
    c.missing = [m for m in c.missing if m != "size"]
    c.facts = {**f, "riser_mm": round(riser, 1), "tread_mm": f["tread_drawn_mm"], "steps": risers, "waist_mm": round(waist, 1), "waist_source": "ASSUMED", "equivalent_depth_mm": box["depth_mm"],
      "rise": {"storey_mm": round(float(f2f), 1), "floor": floor, "risers": risers, "flights": [_steps(x) for _r, x in parts], "pairs_with_pages": sorted({rr["page_no"] for rr, _x in parts})}}
    high = [C.note("STAIR_RISER_HIGH", riser_mm=round(riser, 1), limit_mm=C.STAIR_RISER_MAX_MM, risers_needed=needed, risers_read=risers)] if riser > C.STAIR_RISER_MAX_MM else []
    c.notes = [*[n for n in c.notes if n.get("code") not in ("STAIR_FOUND_NO_DETAILS", "STAIR_LANDINGS_NOT_INCLUDED")], C.note("STAIR_RISE_FROM_LEVELS", floor=floor, storey_mm=round(float(f2f), 1), risers=risers, riser_mm=round(riser, 1)), C.note("STAIR_WAIST_ASSUMED"), *high]
    c.label = f"Stair · {risers} risers · {riser:.0f}/{spec['tread_mm']:.0f} mm · {spec['width_mm']:.0f} mm wide"
    c.status = NS.status_of(c.notes)
    tally["sized"] += 1
    area, centre = _hall(r)
    area = max(0.0, area - box["length_mm"] * box["width_mm"] / 1.0e6)
    
    if area > 0.0 and centre:
      landing = copy.deepcopy(c)
      width = float(c.facts["stair_width_mm"])
      landing.key = c.key + "L"
      landing.geometry = {**(c.geometry or {}), "points": centre}
      landing.params = {"length_mm": round(area * 1.0e6 / width, 1), "width_mm": round(width, 1), "depth_mm": round(waist, 1), "dims_basis": "SPECIFIED"}
      landing.facts = {**landing.facts, "stair_part": "LANDING", "direction": None, "landing_area_m2": round(area, 3), "flight_area_m2": None, "flight_box": None, "treads_drawn": 0}
      landing.notes = [C.note("STAIR_LANDING_FROM_HALL", area_m2=round(area, 2), floor=floor), C.note("STAIR_WAIST_ASSUMED")]
      landing.label = f"Stair landing · {area:.2f} m² of the stair hall less the flight"
      landing.status = NS.status_of(landing.notes)
      r["candidates"].append(landing)
      
      tally["landings"] += 1
      tally["landing_m2"] = round(tally["landing_m2"] + area, 3)
    tally["stairs"].append({"floor": floor, "storey_mm": round(float(f2f), 1), "risers": risers, "riser_mm": round(riser, 1), "risers_needed": needed, "landing_m2": round(area, 3)})
  return tally
