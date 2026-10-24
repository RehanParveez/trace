from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import foundation as FD
from app.modules.drawings_boq.takeoff.extract import config as C

BOUNDARY_RETURNS = "BOUNDARY_RETURNS"
BOUNDARY_PLASTER = "BOUNDARY_PLASTER"
BOUNDARY_PAINT = "BOUNDARY_PAINT"
ITEMS = (BOUNDARY_RETURNS, BOUNDARY_PLASTER, BOUNDARY_PAINT)
WORK_ITEM = {BOUNDARY_RETURNS: "MAS-BRICK", BOUNDARY_PLASTER: "FIN-PLASTER-EXT", BOUNDARY_PAINT: "FIN-PAINT-EXT"}
MODE = {BOUNDARY_RETURNS: "COUNT_X_VOLUME", BOUNDARY_PLASTER: "COUNT_X_AREA", BOUNDARY_PAINT: "COUNT_X_AREA"}
TEXT = {BOUNDARY_RETURNS: ("Boundary wall · side and rear walls", "BOUNDARY-RETURNS"), BOUNDARY_PLASTER: ("Boundary wall · plaster on both faces", "BOUNDARY-PLASTER"),
  BOUNDARY_PAINT: ("Boundary wall · paint on both faces", "BOUNDARY-PAINT")}

SIDES = 2
FACES = 2

FIELDS = {
  "side_length_mm": ("boundary_side_mm", "length_mm", "the length of one side wall of the boundary (0 where there is none)"),
  "rear_length_mm": ("boundary_rear_mm", "length_mm", "the length of the rear wall of the boundary (0 where there is none)"),
  "height_mm": ("site_height_mm", "depth_mm", "the height of the boundary wall"),
  "thickness_mm": ("site_thickness_mm", "width_mm", "the thickness of the boundary wall"),
}
ZERO_OK = ("boundary_side_mm", "boundary_rear_mm")

def is_boundary(cand) -> bool:
  return (getattr(cand, "facts", None) or {}).get("foundation_item") in ITEMS

def field_of(need: str) -> tuple | None:
  return FIELDS.get(need)

def candidates(sites: list, ctx: dict, cls, finish) -> list:
  out: list = []

  for s in sites:
    f = s.facts or {}
    p = s.params or {}
    front = float(p.get("length_mm") or 0.0)
    if f.get("site_kind") != "BOUNDARY_WALL" or front <= 0.0:
      continue
    height = float(p["depth_mm"]) if p.get("depth_mm") else None
    faces = int(f.get("faces") or FACES)
    facts = {"derived_from": "SITE", "wall_key": s.key, "front_length_mm": round(front, 1), "height_mm": height, "faces": faces, "gate_deducted": bool(f.get("gate_deducted")),
      "gate_mm": f.get("gate_mm"), "wall_label": s.label, "front_printed": bool(f.get("pieces_mm")) and height is not None and f.get("height_pick") == "ONLY",
      "front_area_m2": round(faces * front * height / 1e6, 3) if height else None}

    for item in ITEMS:
      text, tag = TEXT[item]
      missing = ["side_length_mm", "rear_length_mm"] + (["thickness_mm"] if item == BOUNDARY_RETURNS else []) + ([] if height else ["height_mm"])
      notes = [C.note("BOUNDARY_RETURNS_TYPED")]
      notes.append(C.note("BOUNDARY_RETURNS_ASSUMED") if item == BOUNDARY_RETURNS else C.note("BOUNDARY_FACES_ASSUMED"))
      params: dict = {"dims_basis": "SPECIFIED"}
      if height:
        params["depth_mm"] = height
      label = text + (f" · {height / 304.8:g} ft high" if height else "")
      cand = cls(key=FD._key_of(("BOUNDARY", item, s.key)), category="WALL", kind="COUNT", quantity_mode=MODE[item], label=label, tag=tag, geometry=dict(s.geometry or {}),
        params=params, missing=missing, work_item=WORK_ITEM[item], status="VALID", confidence=0.0, facts={**facts, "foundation_item": item}, notes=notes, source="TAG_SCAN", count=1)
      out.append(finish(cand, ctx, 0.7 if facts["front_printed"] else 0.55))
  return out

def fill_boundary(item: str, missing: list, params: dict, typed: dict, facts: dict) -> tuple:
  out = dict(params or {})
  f = facts or {}
  got: dict = {}

  for need in missing or []:
    spec = FIELDS.get(need)
    if spec is None:
      return out, ("CANDIDATE_NEEDS_DIMENSIONS", "No size was found for this item. Draw it by hand.")
    value = typed.get(spec[0])
    if value is None:
      return out, ("CANDIDATE_NEEDS_DIMENSIONS", f"Give {spec[2]} to measure this item.")
    got[need] = float(value)
  height = got.get("height_mm") or (float(out["depth_mm"]) if out.get("depth_mm") else None)
  front = float(f.get("front_length_mm") or 0.0)
  
  if not height or front <= 0.0:
    return out, ("CANDIDATE_NEEDS_DIMENSIONS", "No size was found for this item. Draw it by hand.")
  returns = SIDES * got.get("side_length_mm", 0.0) + got.get("rear_length_mm", 0.0)
  if item == BOUNDARY_RETURNS:
    if returns <= 0.0:
      return out, ("CANDIDATE_NEEDS_DIMENSIONS", "The side and rear lengths are both 0, so there is no side or rear wall to measure. Reject this item.")
    out.update({"length_mm": round(returns, 1), "width_mm": got["thickness_mm"], "depth_mm": height})
  else:
    area = int(f.get("faces") or FACES) * (front + returns) * height / 1e6
    out.update({"length_mm": round(area * 1000.0, 1), "width_mm": 1000.0})
    out.pop("depth_mm", None)
  out["dims_basis"] = "SPECIFIED"
  return out, None
