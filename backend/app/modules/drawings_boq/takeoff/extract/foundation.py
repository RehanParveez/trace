from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import config as C
from app.engine.measure import proposed as QP
from app.modules.drawings_boq.takeoff.prep import footing_sections as FSEC

EXCAVATION_AREA = "EXCAVATION_AREA"
TRENCH = "TRENCH"
PCC_STRIP = "PCC_STRIP"
TERMITE_STRIP = "TERMITE_STRIP"
TERMITE_FLOOR = "TERMITE_UNDER_FLOOR"
PCC_PAD = "PCC_PAD"
BRICK_STEP = "BRICK_STEP"
MEMBRANE = "MEMBRANE"
RCC_STRIP = "RCC_STRIP"
EARTH_FILL = "EARTH_FILL"
ROOF_TREATMENT = "ROOF_TREATMENT"
FLOOR_PCC = "FLOOR_PCC"
FLOOR_BALLAST = "FLOOR_BALLAST"
FLOOR_SAND_FILL = "FLOOR_SAND_FILL"
MEMBRANE_COAT = "MEMBRANE_COAT"
MEMBRANE_POLYTHENE = "MEMBRANE_POLYTHENE"
FLOOR_LAYER_ITEMS = (FLOOR_PCC, FLOOR_BALLAST, FLOOR_SAND_FILL)
ITEMS = (EXCAVATION_AREA, TRENCH, PCC_STRIP, TERMITE_STRIP, TERMITE_FLOOR, PCC_PAD, BRICK_STEP, MEMBRANE, RCC_STRIP, EARTH_FILL, ROOF_TREATMENT,
  *FLOOR_LAYER_ITEMS, MEMBRANE_COAT, MEMBRANE_POLYTHENE)

WORK_ITEM = {EXCAVATION_AREA: "EXC-FOUND", TRENCH: "EXC-FOUND", EARTH_FILL: "EXC-FILL", ROOF_TREATMENT: "FIN-ROOF-TREAT", PCC_STRIP: "CON-PCC", PCC_PAD: "CON-PCC", TERMITE_STRIP: "PRO-TERMITE", TERMITE_FLOOR: "PRO-TERMITE",
  BRICK_STEP: "MAS-BRICK", MEMBRANE: "FIN-WATERPROOF-DPC", RCC_STRIP: "CON-RCC", FLOOR_PCC: "CON-PCC", FLOOR_BALLAST: "FLR-BALLAST", FLOOR_SAND_FILL: "FLR-SAND-FILL",
  MEMBRANE_COAT: "FIN-WATERPROOF-DPC", MEMBRANE_POLYTHENE: "FIN-POLYTHENE"}
MODE = {EXCAVATION_AREA: "COUNT_X_VOLUME", EARTH_FILL: "COUNT_X_VOLUME", ROOF_TREATMENT: "COUNT_X_AREA", TRENCH: "COUNT_X_VOLUME", PCC_STRIP: "COUNT_X_VOLUME", PCC_PAD: "COUNT_X_VOLUME",
  TERMITE_STRIP: "COUNT_X_AREA", TERMITE_FLOOR: "COUNT_X_AREA", BRICK_STEP: "COUNT_X_VOLUME", MEMBRANE: "COUNT_X_AREA", RCC_STRIP: "COUNT_X_VOLUME",
  FLOOR_PCC: "COUNT_X_VOLUME", FLOOR_BALLAST: "COUNT_X_VOLUME", FLOOR_SAND_FILL: "COUNT_X_VOLUME", MEMBRANE_COAT: "COUNT_X_AREA", MEMBRANE_POLYTHENE: "COUNT_X_AREA"}

def strip_class(thickness_mm: float) -> str:
  return "THIN" if thickness_mm < C.FOUNDATION_THIN_WALL_MAX_MM else "THICK"

def is_foundation(cand) -> bool:
  return bool((getattr(cand, "facts", None) or {}).get("foundation_item"))

def item_of(cand) -> str | None:
  item = (getattr(cand, "facts", None) or {}).get("foundation_item")
  return item if item in ITEMS else None

def _inch_label(mm: float) -> str:
  return f"{mm / 25.4:g}"

def _centre(points: list) -> list:
  if not points:
    return [0.0, 0.0]
  return [round(sum(p[0] for p in points) / len(points), 4), round(sum(p[1] for p in points) / len(points), 4)]

def _make(cls, ctx: dict, finish, key_parts: tuple, item: str, label: str, tag: str, points: list, params: dict, missing: list, notes: list, facts: dict,
  base: float, count: int = 1):
  facts = {**facts, "foundation_item": item}
  cand = cls(key=_key_of(key_parts), category="WALL", kind="COUNT", quantity_mode=MODE[item], label=label, tag=tag, geometry={"points": points},
    params={**params, "dims_basis": "SPECIFIED"}, missing=missing, work_item=WORK_ITEM[item], status="VALID", confidence=0.0, facts=facts, notes=notes,
    source="VECTOR_SNAP", count=count)
  return finish(cand, ctx, base)

def _key_of(parts: tuple) -> str:
  import hashlib
  return hashlib.sha1("|".join(str(p) for p in ("FND", *parts)).encode()).hexdigest()[:24]

def wall_groups(walls: list) -> dict:
  """The walls the footing strips run under, by thickness: brick and concrete walls of the floor, tank walls and walls with an error left out."""
  groups: dict = {}
  for w in walls:
    f = w.facts or {}
    if w.category != "WALL" or f.get("enclosure") == "TANK" or w.status == "INVALID":
      continue
    t = float(f.get("thickness_used_mm") or 0.0)
    if t <= 0.0 or not float(f.get("length_cc_m") or 0.0):
      continue
    groups.setdefault(round(t, 1), []).append(w)
  return groups

def _section_facts(sec: dict) -> dict:
  return {"footing_section": {"caption": sec.get("caption"), "calibration": sec.get("calibration"), "scale_mm_per_pt": sec.get("scale_mm_per_pt"),
    "pcc": sec.get("pcc"), "footing": sec.get("footing"), "steps": sec.get("steps"), "total_depth_mm": sec.get("total_depth_mm"), "steel": sec.get("steel") or []}}

def strip_candidates(walls: list, ctx: dict, level_hint: str | None, spec, cls, finish, sections: list | None = None) -> list:
  out: list = []
  for t, ws in sorted(wall_groups(walls).items(), reverse=True):
    length_m = sum(float((w.facts or {}).get("length_cc_m") or 0.0) for w in ws)
    rcc_m = sum(float((w.facts or {}).get("length_cc_m") or 0.0) for w in ws if (w.facts or {}).get("construction") == "RCC")
    pts = [p for w in ws for p in ((w.geometry or {}).get("points") or [])]
    cls_name = strip_class(t)
    base_facts = {"derived_from": "WALLS", "strip_class": cls_name, "wall_thickness_mm": t, "wall_count": len(ws), "length_m": round(length_m, 3),
      "rcc_length_m": round(rcc_m, 3), "wall_keys": [w.key for w in ws]}
    where = f" · {spec[0]}" if spec else ""
    
    label_t = f"{_inch_label(t)} in walls · {length_m:.2f} m{where}"
    centre = [_centre(pts)]
    params = {"length_mm": round(length_m * 1000.0, 1)}
    walls_note = C.note("FOUNDATION_FROM_WALLS")
    sec = FSEC.for_wall(sections, t)
    if sec and sec.get("pcc") and sec.get("total_depth_mm"):
      base_facts.update(_section_facts(sec))
      
      sec_note = C.note("FOUNDATION_FROM_SECTION", caption=sec.get("caption"), total_depth_mm=sec["total_depth_mm"])
      bed_w, bed_t = float(sec["pcc"]["width_mm"]), float(sec["pcc"]["depth_mm"])
      out.append(_make(cls, ctx, finish, (TRENCH, round(t), level_hint or ""), TRENCH, f"Trench under {label_t}", f"TRENCH-{_inch_label(t)}IN", centre,
        {**params, "width_mm": round(bed_w + 2.0 * C.TRENCH_SIDE_ALLOWANCE_MM, 1), "depth_mm": float(sec["total_depth_mm"])}, [],
        [walls_note, sec_note, C.note("TRENCH_WORKING_SPACE_ASSUMED")], dict(base_facts), 0.72))
      out.append(_make(cls, ctx, finish, (PCC_STRIP, round(t), level_hint or ""), PCC_STRIP, f"Concrete bed under {label_t}", f"PCC-STRIP-{_inch_label(t)}IN", centre,
        {**params, "width_mm": bed_w, "depth_mm": bed_t}, [], [walls_note, sec_note], dict(base_facts), 0.78))
      out.append(_make(cls, ctx, finish, (TERMITE_STRIP, round(t), level_hint or ""), TERMITE_STRIP, f"Termite treatment under {label_t}", f"TERMITE-STRIP-{_inch_label(t)}IN",
        centre, {**params, "width_mm": bed_w}, [], [walls_note, sec_note, C.note("TERMITE_BOTTOM_ONLY")], dict(base_facts), 0.72))
      continue
  
    width_note = C.note("FOUNDATION_WIDTH_TYPED")
    out.append(_make(cls, ctx, finish, (TRENCH, round(t), level_hint or ""), TRENCH, f"Trench under {label_t}", f"TRENCH-{_inch_label(t)}IN", centre, dict(params),
      ["strip_width_mm", "depth_mm"], [walls_note, width_note, C.note("TRENCH_WORKING_SPACE_ASSUMED"), C.note("TRENCH_DEPTH_QS_SHEET", **QP.trench_extra())], dict(base_facts), 0.65))
    out.append(_make(cls, ctx, finish, (PCC_STRIP, round(t), level_hint or ""), PCC_STRIP, f"Concrete bed under {label_t}", f"PCC-STRIP-{_inch_label(t)}IN", centre,
       dict(params), ["strip_width_mm", "depth_mm"], [walls_note, width_note], dict(base_facts), 0.7))
    out.append(_make(cls, ctx, finish, (TERMITE_STRIP, round(t), level_hint or ""), TERMITE_STRIP, f"Termite treatment under {label_t}", f"TERMITE-STRIP-{_inch_label(t)}IN",
      centre, dict(params), ["strip_width_mm"], [walls_note, width_note, C.note("TERMITE_BOTTOM_ONLY")], dict(base_facts), 0.65))
  return out

def under_floor_candidate(rooms: list, ctx: dict, level_hint: str | None, spec, cls, finish):
  """The termite treatment under the floor of the lowest storey: the total of its room areas."""
  total = 0.0
  used = 0
  
  for r in rooms:
    f = r.facts or {}
    if r.category != "ROOM" or r.status == "INVALID" or any(n.get("code") == "ROOM_INSIDE_ROOM" for n in r.notes or []):
      continue
    a = float(f.get("area_m2") or 0.0)
    if a > 0.0:
      total += a
      used += 1
  if used == 0:
    return None
  pts = [p for r in rooms for p in ((r.geometry or {}).get("outer") or (r.geometry or {}).get("points") or [])]
  facts = {"derived_from": "ROOMS", "room_count": used, "area_m2": round(total, 3)}
  label = f"Termite treatment under the floor · {total:.2f} m²" + (f" · {spec[0]}" if spec else "")
  return _make(cls, ctx, finish, (TERMITE_FLOOR, level_hint or ""), TERMITE_FLOOR, label, "TERMITE-UNDER-FLOOR", [_centre(pts)],
    {"length_mm": round(total * 1000.0, 1), "width_mm": 1000.0}, [], [C.note("UNDER_FLOOR_FROM_ROOMS")], facts, 0.75)

def excavation_candidate(dims, outline_facts: dict, ctx: dict, level_hint: str | None, spec, cls, finish, centre: list):
  """The dig over the whole basement: the outline of the basement slab (covered area widened by its projections) x a depth that is typed."""
  if not dims or len(dims) != 2:
    return None
  length, width = float(dims[0]), float(dims[1])
  area = length * width / 1e6
  
  facts = {"derived_from": "AREA_TABLE", "outline_dims_mm": [round(length, 1), round(width, 1)], "area_m2": round(area, 3), **outline_facts}
  label = f"Excavation over the basement · {area:.2f} m²" + (f" · {spec[0]}" if spec else "")
  return _make(cls, ctx, finish, (EXCAVATION_AREA, level_hint or ""), EXCAVATION_AREA, label, "EXCAVATION-BASEMENT", [centre],
    {"length_mm": round(length, 1), "width_mm": round(width, 1)}, ["depth_mm"],
    [C.note("EXCAVATION_AREA_FROM_OUTLINE"), C.note("EXCAVATION_OVERLAPS_FOOTING_PITS"), C.note("EXCAVATION_DEPTH_QS_SHEET", **QP.excavation_extra())], facts, 0.8)

def pad_candidates(footings: list, ctx: dict, cls, finish) -> list:
  """The concrete bed under each footing mark: as many beds as marks, each as large as the footing."""
  out: list = []
  
  for fc in footings:
    p = fc.params or {}
    length, width = p.get("length_mm"), p.get("width_mm")
    if fc.category != "FOOTING" or fc.status == "INVALID" or not length or not width:
      continue
    pts = (fc.geometry or {}).get("points") or []
    if not pts:
      continue
    facts = {"derived_from": "FOOTINGS", "footing_key": fc.key, "footing_tag": fc.tag, "marks": len(pts), "size_mm": [float(length), float(width)]}
    if (fc.facts or {}).get("view"):
      facts["view"] = fc.facts["view"]
    out.append(_make(cls, ctx, finish, (PCC_PAD, fc.key), PCC_PAD, f"Concrete bed under footing {fc.tag} · {len(pts)} nos", f"PCC-PAD-{fc.tag}", [list(pt) for pt in pts],
      {"length_mm": float(length), "width_mm": float(width)}, ["depth_mm"], [C.note("PCC_PAD_FROM_FOOTINGS")], facts, 0.75, count=len(pts)))
  return out

def brick_step_candidates(walls: list, ctx: dict, level_hint: str | None, spec, cls, finish, sections: list | None = None) -> list:
  out: list = []
  for t, ws in sorted(wall_groups(walls).items(), reverse=True):
    brick = [w for w in ws if (w.facts or {}).get("construction") != "RCC"]
    length_m = sum(float((w.facts or {}).get("length_cc_m") or 0.0) for w in brick)
    if length_m <= 0.0:
      continue
  
    pts = [p for w in brick for p in ((w.geometry or {}).get("points") or [])]
    cls_name = strip_class(t)
    sec = FSEC.for_wall(sections, t)
    where = f" · {spec[0]}" if spec else ""
    centre = [_centre(pts)]
    if sec and sec.get("steps"):
      n = len(sec["steps"])
      
      for i, st in enumerate(sec["steps"], start=1):
        facts = {"derived_from": "WALLS", "strip_class": cls_name, "wall_thickness_mm": t, "wall_count": len(brick), "length_m": round(length_m, 3),
          "step_no": i, "steps_in_class": n, "wall_keys": [w.key for w in brick], **_section_facts(sec)}
        label = f"Brick foundation step {i} of {n} under {_inch_label(t)} in walls · {length_m:.2f} m{where}"
        out.append(_make(cls, ctx, finish, (BRICK_STEP, round(t), i, level_hint or ""), BRICK_STEP, label, f"BRICK-STEP-{_inch_label(t)}IN-{i}", centre,
          {"length_mm": round(length_m * 1000.0, 1), "width_mm": float(st["width_mm"]), "depth_mm": float(st["height_mm"])}, [],
          [C.note("FOUNDATION_FROM_WALLS"), C.note("BRICK_STEPS_FROM_SECTION", steps=n, caption=sec.get("caption")), C.note("BRICK_STEPS_BRICK_ONLY")], facts, 0.74))
      foot = sec.get("footing")
      
      if foot:
        facts = {"derived_from": "WALLS", "strip_class": cls_name, "wall_thickness_mm": t, "wall_count": len(brick), "length_m": round(length_m, 3),
          "wall_keys": [w.key for w in brick], **_section_facts(sec)}
        notes = [C.note("FOUNDATION_FROM_WALLS"), C.note("RCC_STRIP_FROM_SECTION", caption=sec.get("caption")), C.note("BRICK_STEPS_BRICK_ONLY")]
        notes.append(C.note("RCC_STRIP_STEEL_PRINTED", bars=sec["steel"]) if sec.get("steel") else C.note("RCC_STRIP_STEEL_NOT_READ"))
        out.append(_make(cls, ctx, finish, (RCC_STRIP, round(t), level_hint or ""), RCC_STRIP, f"Reinforced concrete strip footing under {_inch_label(t)} in walls · {length_m:.2f} m{where}",
          f"RCC-STRIP-{_inch_label(t)}IN", centre, {"length_mm": round(length_m * 1000.0, 1), "width_mm": float(foot["width_mm"]), "depth_mm": float(foot["depth_mm"])}, [],
          notes, facts, 0.74))
      continue
  
    steps = C.BRICK_STEPS_THIN if cls_name == "THIN" else C.BRICK_STEPS_THICK
    for i in range(1, steps + 1):
      facts = {"derived_from": "WALLS", "strip_class": cls_name, "wall_thickness_mm": t, "wall_count": len(brick), "length_m": round(length_m, 3),
        "step_no": i, "steps_in_class": steps, "wall_keys": [w.key for w in brick]}
      label = f"Brick foundation step {i} of {steps} under {_inch_label(t)} in walls · {length_m:.2f} m{where}"
      out.append(_make(cls, ctx, finish, (BRICK_STEP, round(t), i, level_hint or ""), BRICK_STEP, label, f"BRICK-STEP-{_inch_label(t)}IN-{i}", centre,
        {"length_mm": round(length_m * 1000.0, 1)}, ["step_height_mm", "step_offset_mm"],
        [C.note("FOUNDATION_FROM_WALLS"), C.note("BRICK_STEPS_ASSUMED"), C.note("BRICK_STEPS_QS_SHEET", **QP.brick_step_extra(cls_name, i)), C.note("BRICK_STEPS_BRICK_ONLY")], facts, 0.6))
  return out

def membrane_candidate(walls: list, ctx: dict, level_hint: str | None, spec, cls, finish, mm_per_pt: float | None = None):
  """The membrane: on a basement, up the outside of every outer wall for the full wall height (the QS, S1); otherwise along the top of the plinth."""
  if str(level_hint or "").upper() == "BASEMENT" and mm_per_pt:
    cand = _outside_membrane(walls, ctx, level_hint, spec, cls, finish, mm_per_pt)
    if cand is not None:
      return cand
  return _plinth_membrane(walls, ctx, level_hint, spec, cls, finish)

def _outside_extent(walls: list, mm_per_pt: float):
  """(length in m, outer wall count, points, height in mm) of the outside face of the outer walls of a basement, or None."""
  from app.modules.drawings_boq.takeoff.extract import finishes as FN
  from app.engine.measure import readings as QS
  faces = FN.plaster_faces(walls, mm_per_pt)
  outer = [r for r in faces if r["out"]]
  length_m = sum(float(r["l"]) for r in outer)
  if length_m <= 0.0:
     return None
  height = float(QS.convention("basement_wall_height_mm"))
  pts = [p for w in FN.plaster_walls(walls) for p in w.geometry["points"]]
  return length_m, len(outer), pts, height

def _outside_membrane(walls: list, ctx: dict, level_hint: str | None, spec, cls, finish, mm_per_pt: float):
  extent = _outside_extent(walls, mm_per_pt)
  if extent is None:
    return None
  length_m, outer_n, pts, height = extent
  facts = {"derived_from": "WALLS", "membrane_kind": "OUTSIDE_FACE", "outer_wall_count": outer_n, "length_m": round(length_m, 3), "height_mm": height, "qs": ["S1", "S5", "S8"]}
  label = f"Membrane on the outside of the basement walls · {length_m:.2f} m × {height / 304.8:g} ft" + (f" · {spec[0]}" if spec else "")
  return _make(cls, ctx, finish, (MEMBRANE, level_hint or ""), MEMBRANE, label, "MEMBRANE", [_centre(pts)], {"length_mm": round(length_m * 1000.0, 1), "width_mm": height}, [],
    [C.note("MEMBRANE_OUTSIDE_QS")], facts, 0.8)

def membrane_layer_candidates(walls: list, ctx: dict, level_hint: str | None, spec, cls, finish, mm_per_pt: float | None, layers: list | None) -> list:
  if str(level_hint or "").upper() != "BASEMENT" or not mm_per_pt or not layers:
    return []
  extent = _outside_extent(walls, mm_per_pt)
  if extent is None:
    return []
  length_m, outer_n, pts, height = extent
  out: list = []
  
  for lay in layers:
    n = lay.get("layers")
    item = {"waterproofing coat": MEMBRANE_COAT, "polythene sheet": MEMBRANE_POLYTHENE}.get(lay.get("material"))
    if item is None or not n:
      continue
    unit = "coat" if lay.get("unit") == "coat" else "layer"
    facts = {"derived_from": "WALLS", "membrane_kind": "OUTSIDE_FACE", "outer_wall_count": outer_n, "length_m": round(length_m, 3), "height_mm": height, "material": lay["material"],
      "layers": int(n), "layer_unit": unit, "spec_pages": lay.get("pages") or [], "qs": ["S1", "S5", "S8"]}
    label = f"{lay['material'].capitalize()} · {n} {unit}{'s' if n != 1 else ''} · outside of the basement walls · {length_m:.2f} m × {height / 304.8:g} ft" + (f" · {spec[0]}" if spec else "")
    out.append(_make(cls, ctx, finish, (item, level_hint or ""), item, label, item.replace("_", "-"), [_centre(pts)], {"length_mm": round(length_m * 1000.0, 1), "width_mm": height}, [],
      [C.note("MEMBRANE_OUTSIDE_QS"), (C.note("MEMBRANE_LAYER_UNDER_HEADING", material=lay["material"], layers=int(n), unit=unit, heading=lay["heading"], pages=lay.get("pages") or [])
        if lay.get("heading") else C.note("MEMBRANE_LAYER_FROM_SPEC", material=lay["material"], layers=int(n), unit=unit, pages=lay.get("pages") or []))], facts, 0.7))
  return out

def _plinth_membrane(walls: list, ctx: dict, level_hint: str | None, spec, cls, finish):
  """The damp-proof membrane along the top of the plinth: the walls of the lowest floor laid end to end, times a width that is typed."""
  groups = wall_groups(walls)
  ws = [w for group in groups.values() for w in group]
  length_m = sum(float((w.facts or {}).get("length_cc_m") or 0.0) for w in ws)
  if length_m <= 0.0:
    return None
  rcc_m = sum(float((w.facts or {}).get("length_cc_m") or 0.0) for w in ws if (w.facts or {}).get("construction") == "RCC")
  pts = [p for w in ws for p in ((w.geometry or {}).get("points") or [])]
  facts = {"derived_from": "WALLS", "wall_count": len(ws), "length_m": round(length_m, 3), "rcc_length_m": round(rcc_m, 3), "wall_keys": [w.key for w in ws]}
  label = f"Damp-proof membrane under walls · {length_m:.2f} m" + (f" · {spec[0]}" if spec else "")
  return _make(cls, ctx, finish, (MEMBRANE, level_hint or ""), MEMBRANE, label, "MEMBRANE", [_centre(pts)], {"length_mm": round(length_m * 1000.0, 1)},
    ["membrane_width_mm"], [C.note("MEMBRANE_FROM_WALLS")], facts, 0.65)

STRIP_FIELDS = {"THICK": "pcc_strip_width_mm", "THIN": "pcc_strip_width_thin_mm"}
DEPTH_FIELDS = {EXCAVATION_AREA: ("excavation_depth_mm", "the depth of the excavation over the basement"),
  EARTH_FILL: ("fill_depth_mm", "the depth of the earth filling under the floor"),

  TRENCH: ("trench_depth_mm", "the depth of the trench below the dug floor"), PCC_STRIP: ("pcc_thickness_mm", "the thickness of the concrete bed"),
  PCC_PAD: ("pcc_thickness_mm", "the thickness of the concrete bed")}

def fill_foundation(item: str, missing: list, params: dict, typed: dict, facts: dict) -> tuple:
  """(params, problem) for a foundation item: the strip width, depth or thickness typed at accept."""
  out = dict(params or {})
  
  for need in missing or []:
    if need == "strip_width_mm":
      field = STRIP_FIELDS["THIN" if (facts or {}).get("strip_class") == "THIN" else "THICK"]
      value = typed.get(field)
      if value is None:
        thin = (facts or {}).get("strip_class") == "THIN"
        return out, ("CANDIDATE_NEEDS_DIMENSIONS", f"Give the width of the strip under {'thin walls (under 6 inches)' if thin else 'walls of 6 inches and thicker'} to measure this item.")
      width = float(value) + (2.0 * C.TRENCH_SIDE_ALLOWANCE_MM if item == TRENCH else 0.0)
      out["width_mm"] = round(width, 1)
    elif need == "step_height_mm":
      field = f"brick_step_{int((facts or {}).get('step_no') or 0)}_height_mm"
      value = typed.get(field)
      if value is None:
        return out, ("CANDIDATE_NEEDS_DIMENSIONS", f"Give the height of step {int((facts or {}).get('step_no') or 0)} of the brick foundation to measure this item.")
      out["depth_mm"] = float(value)
      
    elif need == "step_offset_mm":
      value = typed.get("brick_step_offset_mm")
      if value is None:
        return out, ("CANDIDATE_NEEDS_DIMENSIONS", "Give how much each step of the brick foundation is narrower than the one below it, both sides together, to measure this item.")
      f = facts or {}
      out["width_mm"] = round(float(f.get("wall_thickness_mm") or 0.0) + (int(f.get("steps_in_class") or 1) - int(f.get("step_no") or 1)) * float(value), 1)
    elif need == "membrane_width_mm":
      value = typed.get("membrane_width_mm")
      if value is None:
        return out, ("CANDIDATE_NEEDS_DIMENSIONS", "Give the width of the damp-proof membrane to measure this item.")
      out["width_mm"] = float(value)
    elif need == "depth_mm" and item in DEPTH_FIELDS:
      field, words = DEPTH_FIELDS[item]
      value = typed.get(field)
      if value is None:
          
        return out, ("CANDIDATE_NEEDS_DIMENSIONS", f"Give {words} to measure this item.")
      out["depth_mm"] = float(value)
    else:
      return out, ("CANDIDATE_NEEDS_DIMENSIONS", "No size was found for this item. Draw it by hand.")
  out["dims_basis"] = "SPECIFIED"
  return out, None
