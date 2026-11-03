from __future__ import annotations
from app.engine.measure import readings as QS
from app.engine.measure import proposed as PR
from app.modules.drawings_boq.takeoff.model import levels as LV
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.extract import spec_facts as SF

BASEMENT = "BASEMENT"
STOREYS_ABOVE_GROUND = ("GROUND", "MEZZANINE", "FIRST", "SECOND", "THIRD", "FOURTH")
HEIGHT_CODES = ("HEIGHT_FROM_SECTION", "HEIGHT_FROM_NOTE", "HEIGHT_FROM_QS")

def floor_finish_by_room() -> bool:
  return bool(QS.flag("floor_finish_by_room"))

def wall_plaster_mm() -> float:
  return float(QS.param("wall_plaster_face_mm") or 0.0) if QS.flag("wall_plaster_drawn") else 0.0

def _ft_in(mm: float) -> str:
  inches = round(mm / 25.4)
  return f"{inches // 12}'-{inches % 12}\""

BEAM_BASES = ("ABOVE_PLINTH_BEAM", "BETWEEN_BEAMS")

def less_beams(heights: dict, lowest_level: bool, ft_in) -> dict:
  basis = QS.choice("wall_height_basis")
  entry = (heights or {}).get("WALL")
  if basis not in BEAM_BASES or not entry or entry.get("basis") not in ("SECTION", "QS"):
    return heights
  sizes = PR.sizes()
  cuts: list = []
  
  if lowest_level:
    cuts.append(("plinth beam", float(sizes["plinth_beam_depth_mm"]["mm"])))
  if basis == "BETWEEN_BEAMS":
    web = float(sizes["beam_depth_mm"]["mm"])
    if QS.param("beam_depth_includes_slab"):
      web = max(web - float(QS.convention("slab_thickness_mm") or 0.0), 0.0)
    cuts.append(("roof beam web", web))
  total = sum(mm for _, mm in cuts)
  
  if total <= 0.0 or float(entry["mm"]) <= total:
    return heights
  mm = float(entry["mm"]) - total
  text = f"{entry['text']}, less the " + " and the ".join(f"{name} {ft_in(v)}" for name, v in cuts) + f" ({basis.lower().replace('_', ' ')}), {ft_in(mm)}"
  return {**heights, "WALL": {**entry, "mm": mm, "text": text, "less_beams": [{"name": n, "mm": v} for n, v in cuts]}}

SLAB_TOP_TO_SOFFIT = "SLAB_TOP_TO_SOFFIT"
BELOW_THE_SLAB_LAYERS = ("sand filling",)

def build_up_above_slab_mm(spec: dict | None, level_hint: str | None) -> float | None:
  head = SF.floor_set(spec, level_hint)
  if not head:
    return None
  total = sum(float(lay["value_mm"]) for name, lay in (head.get("layers") or {}).items() if name not in BELOW_THE_SLAB_LAYERS and lay.get("value_mm"))
  return total or None

def slab_top_to_soffit(heights: dict, floors: dict | None, level_hint: str | None, spec: dict | None, ft_in) -> dict:
  if QS.choice("wall_height_basis") != SLAB_TOP_TO_SOFFIT:
    return heights
  clear = ((floors or {}).get(level_hint or "") or {}).get("clear_mm")
  up = build_up_above_slab_mm(spec, level_hint)
  if not clear or not up:
    return heights
  mm = float(clear) + up
  old = (heights or {}).get("WALL") or {}
  text = f"clear storey height {ft_in(float(clear))} plus the floor build-up {ft_in(up)} above the slab, slab top to soffit {ft_in(mm)}"
  return {**heights, "WALL": {**old, "mm": mm, "text": text, "basis": "SECTION", "slab_top_to_soffit": {"clear_mm": float(clear), "build_up_mm": round(up, 1)}}}

ROAD_TO_PARAPET_TOP = "ROAD_TO_PARAPET_TOP"
ABOVE_GROUND_FLOORS = ("GROUND", "MEZZANINE", "FIRST", "SECOND", "THIRD", "FOURTH")

def outer_face_height_mm(floors: dict | None, level_hint: str | None, spec: dict | None) -> float | None:
  if QS.choice("plaster.external_height_basis") != ROAD_TO_PARAPET_TOP or str(level_hint or "").upper() not in ABOVE_GROUND_FLOORS:
    return None
  levels = sorted((float(v["level_mm"]), fl) for fl, v in (floors or {}).items() if fl in ABOVE_GROUND_FLOORS and v.get("level_mm") is not None)
  names = [fl for _lv, fl in levels]
  if str(level_hint).upper() not in names:
    return None
  
  i = names.index(str(level_hint).upper())
  below = 0.0 if i == 0 else levels[i][0]
  if i + 1 < len(levels):
    above = levels[i + 1][0]
  else:
    top = (((spec or {}).get("roof_levels") or {}).get("parapet") or {}).get("top_mm")
    if not top:
      return None
    above = float(top)
  return above - below if above > below else None

def set_outer_face_heights(walls: list, floors: dict | None, level_hint: str | None, spec: dict | None) -> int:
  h = outer_face_height_mm(floors, level_hint, spec)
  if not h:
    return 0
  n = 0
  for w in walls:
    sides = (w.facts or {}).get("face_sides")
    if sides and float(sides.get("out") or 0.0) > 0.0:
      w.facts = {**w.facts, "outer_face_height_mm": round(h, 1)}
      n += 1
  return n

def column_run(floors: dict | None, ft_in) -> dict | None:
  parts = [(fl, LV.height(floors, LV.FLOOR_TO_FLOOR, fl)) for fl in STOREYS_ABOVE_GROUND if fl in (floors or {})]
  parts = [(fl, float(v), src) for fl, (v, src) in parts if v]
  if not parts:
    return None
  neck = PR.sizes()["neck_height_mm"]
  total = float(neck["mm"]) + sum(v for _fl, v, _s in parts)
  text = f"column from the top of the footing to the top of the {parts[-1][0].lower()} slab, {ft_in(total)}: neck {ft_in(float(neck['mm']))} and " + ", ".join(f"{fl.lower()} {ft_in(v)}" for fl, v, _s in parts)
  return {"mm": total, "text": text, "basis": "LEVELS", "ladder": {"what": LV.FLOOR_TO_FLOOR, "floor": parts[-1][0], "kind": LV.PLAN_NOTES, "basis": "neck_height_mm", "entry": {fl: round(v, 1) for fl, v, _s in parts}}}

def floor_heights(heights: dict, floors: dict | None, level_hint: str | None, ft_in, clear_only) -> dict:
  if not QS.flag("wall_height_floor_to_floor"):
    return clear_only(heights, floors, level_hint)
  if not level_hint or str(level_hint).upper() == "FOUNDATION":
    run = column_run(floors, ft_in)
    return {**clear_only(heights, floors, level_hint), **({"COLUMN": run} if run and "COLUMN" not in heights else {})}
  f2f, src = LV.height(floors, LV.FLOOR_TO_FLOOR, level_hint)
  fh = (floors or {}).get(level_hint or "") or {}
  
  if f2f:
    how = "worked out from the room notes of the plans (ceiling height and level above the road)" if fh.get("basis") == "PLAN_NOTES" else "printed on the building section"
    entry = {"mm": float(f2f), "text": f"floor-to-floor height {ft_in(float(f2f))} {how}", "basis": "SECTION", **({"source": "PLAN_NOTES"} if fh.get("basis") == "PLAN_NOTES" else {}), "ladder": src}
  elif str(level_hint or "").upper() == BASEMENT:
    mm = float(QS.convention("basement_floor_to_floor_mm"))
    entry = {"mm": mm, "text": f"basement floor-to-floor height {ft_in(mm)}, " + QS.whose(["basement_floor_to_floor_mm"], "as the QS gave it (S5)", "as your company's convention has it"), "basis": "QS",
      "origin": QS.CO.origin_of("basement_floor_to_floor_mm"), "ladder": LV.rule_source(LV.FLOOR_TO_FLOOR, level_hint, "basement_floor_to_floor_mm")}
  else:
    return clear_only(heights, floors, level_hint)
  out = dict(heights)
  for cat in ("WALL", "COLUMN"):
    out.setdefault(cat, entry)
  return out

def mark_clear(cands: list, floors: dict | None, level_hint: str | None) -> int:
  clear = ((floors or {}).get(level_hint or "") or {}).get("clear_mm")
  if not clear or not QS.flag("wall_height_floor_to_floor"):
    return 0
  n = 0
  for c in cands:
    if c.category != "WALL" or any(x.get("code") == "HEIGHT_FROM_NOTE" for x in c.notes or []):
      continue
    if any(x.get("code") in ("HEIGHT_FROM_SECTION", "HEIGHT_FROM_QS") for x in c.notes or []):
      c.facts = {**(c.facts or {}), "clear_height_mm": float(clear)}
      n += 1
  return n

def stamp(cand, *ids: str) -> None:
  """Put the answer numbers on the facts of a candidate, so its provenance shows whose value it used."""
  f = cand.facts if cand.facts is not None else {}
  f["qs"] = sorted(set(f.get("qs") or []) | set(ids))
  cand.facts = f

def rcc_heights(cands: list, level_hint: str | None) -> int:
  if str(level_hint or "").upper() != BASEMENT:
    return 0
  mm = float(QS.convention("basement_wall_height_mm"))
  n = 0
  
  for c in cands:
    f = c.facts or {}
    if c.category != "WALL" or f.get("construction") != "RCC":
      continue
    if any(x.get("code") == "HEIGHT_FROM_NOTE" for x in c.notes or []):
      continue
  
    c.params = {**(c.params or {}), "height_mm": mm, "dims_basis": "SPECIFIED"}
    c.missing = [m for m in (c.missing or []) if m != "height_mm"]
    c.notes = [x for x in (c.notes or []) if x.get("code") not in HEIGHT_CODES]
    c.notes.append(C.note("HEIGHT_FROM_QS", origin=QS.CO.origin_of("basement_wall_height_mm"), ladder=LV.rule_source("WALL_HEIGHT", level_hint, "basement_wall_height_mm"),
      text=f"basement concrete wall {_ft_in(mm)} high for the estimate, " + QS.whose(["basement_wall_height_mm"], "as the QS gave it (S1, S5)", "as your company's convention has it")))
    stamp(c, "S1", "S5")
    n += 1
  return n

def counted_completion(completion: list) -> list:
  if not QS.flag("rcc_ring_closed"):
    return []
  for c in completion or []:
    stamp(c, "S8")
  return list(completion or [])

CFT_MM3 = 304.8 ** 3

def _piece(c, role: str, assumed: list) -> None:
  p = c.params or {}
  if p.get("length_mm") and p.get("width_mm") and p.get("depth_mm"):
    c.facts = {**(c.facts or {}), "foundation_piece": {"role": role, "cft": round(p["length_mm"] * p["width_mm"] * p["depth_mm"] / CFT_MM3, 4), "assumed": assumed}}

def apply(cands: list, level_hint: str | None) -> dict:
  stats = {"footing_depths": 0, "stairs": 0, "tanks": 0, "boundary": 0, "neck_heights": 0}
  depth = float(QS.convention("footing_depth_mm"))
  
  for c in cands:
    f = c.facts or {}
    if c.category == "FOOTING" and "depth_mm" in (c.missing or []):
      c.params = {**(c.params or {}), "depth_mm": depth}
      c.params.setdefault("dims_basis", "SPECIFIED")
      c.missing = [m for m in c.missing if m != "depth_mm"]
      c.notes.append(C.note("FOOTING_DEPTH_QS", depth_mm=depth))
      
      stamp(c, "X4")
      stats["footing_depths"] += 1
    elif c.category == "COLUMN" and f.get("neck_of") and "height_mm" in (c.missing or []):
      size = PR.sizes()["neck_height_mm"]
      c.params = {**(c.params or {}), "depth_mm": size["mm"], "dims_basis": "SPECIFIED"}
      c.missing = [m for m in c.missing if m != "height_mm"]
      c.facts = {**f, "neck_assumed": {"mm": size["mm"], "text": size["text"], "evidence": size["evidence"]}}
      nh = C.note("NECK_HEIGHT_ASSUMED", height_mm=size["mm"], ladder=LV.rule_source("FOOTING_TOP", None, "neck_height_mm"))
      whose = (f"as your company's convention has it ({size['evidence'].rstrip('.').lower()})" if size.get("origin") == QS.CO.COMPANY and QS.company_differs("neck_height_mm")
        else f"as the QS's workbook has it ({size['evidence'].rstrip('.')})")
      nh["message"] = (f"The neck column runs from the top of the footing to the lowest floor. That height is not printed on the sheet. {size['text']} is used, {whose}. Type another height to override it.")
      c.notes.append(nh)
      stats["neck_heights"] += 1
      
    elif c.category == "STAIR" and any(x.get("code") == "STAIR_WAIST_ASSUMED" for x in c.notes or []):
      stamp(c, "X8", "S12")
      stats["stairs"] += 1
    elif c.category == "SITE" and f.get("site_kind") in ("OHWT", "UGWT", "SEPTIC"):
      if not (f.get("tank_slabs_mm") or {}).get("bottom_mm"):
        c.notes.append(C.note("TANK_SLABS_QS",top_mm=QS.convention("tank_top_slab_mm"), bottom_mm=QS.convention("tank_bottom_slab_mm")))
        stamp(c, "S11")
      stats["tanks"] += 1
    elif c.category == "SITE" and f.get("site_kind") == "BOUNDARY_WALL":
      c.notes.append(C.note("SITE_WALL_QS_ESTIMATE", thickness_mm=QS.convention("boundary_wall_thickness_mm")))
      stamp(c, "S7", "X11")
      stats["boundary"] += 1
  for c in cands:
    codes = {n.get("code") for n in c.notes or []}
    if c.category == "FOOTING":
      _piece(c, "FOOTING", [x for x, k in (("depth", "FOOTING_DEPTH_QS"), ("size pairing", "FOOTING_SIZE_ORDER_ASSUMED"), ("size pairing", "FOOTING_SIZE_PAIRED"),
        ("size by elimination", "FOOTING_SIZE_BY_ELIMINATION")) if k in codes])
    elif c.category == "COLUMN" and (c.facts or {}).get("neck_of"):
      _piece(c, "NECK", ["height"] if "NECK_HEIGHT_ASSUMED" in codes else [])
  return stats
