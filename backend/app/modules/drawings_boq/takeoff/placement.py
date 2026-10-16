from __future__ import annotations
from decimal import Decimal
from app.modules.drawings_boq.takeoff import z_range as Z

PLAN_BASIS = "MARK_CENTRE_SIZE"
PLACED = ("COLUMN", "FOOTING", "BEAM", "SLAB", "LINTEL")
ROW_KEYS = ("elevation_base_mm", "elevation_top_mm", "bbox_min_x_mm", "bbox_min_y_mm", "bbox_min_z_mm", "bbox_max_x_mm", "bbox_max_y_mm", "bbox_max_z_mm", "placement")

def _num(v):
  try:
    f = float(v)
  except (TypeError, ValueError):
    return None
  return f if f == f else None

def _d(v) -> Decimal:
  return Decimal(str(round(float(v), 3)))

def z_inputs(cand) -> tuple:
  """(kind, own height, own depth) of an item for the height range, or (None, None, None) for an item that has none."""
  kind = Z.member_kind(cand.category, cand.facts)
  if kind is None:
    return None, None, None
  p = cand.params or {}
  if kind in ("COLUMN", "NECK"):
    return kind, _num(p.get("depth_mm")), None
  if kind == "WALL":
    return kind, _num(p.get("height_mm")), None
  return kind, None, _num(p.get("depth_mm"))

def head_of(cand) -> tuple:
  """(how high the opening head stands above the floor, whether that was printed) for a lintel or a tie band; (None, ASSUMED) for any other item or when the
  reading found no head. A door's own height from the schedule is printed; the level taken for a window is not."""
  facts = getattr(cand, "facts", None) or {}
  return _num(facts.get("head_mm")), (Z.PRINTED if facts.get("head_basis") == "DOOR_HEIGHT" else Z.ASSUMED)

def z_of(cand, floors: dict, floor_key: str | None, footing: Z.FootingLevel | None) -> Z.ZRange | None:
  kind, height, depth = z_inputs(cand)
  if kind is None:
    return None
  head, grade = head_of(cand) if kind in ("LINTEL", "BAND") else (None, Z.ASSUMED)
  return Z.z_range(kind, (floors or {}).get(floor_key) if floor_key else None, height_mm=height, depth_mm=depth, footing=footing, head_mm=head, head_grade=grade)

def box_of(placed: dict | None, length_mm, width_mm) -> dict | None:
  """The plan rectangle of a mark placed in the frame: its size laid round its centre, with the sides along the sheet axes. None when the mark is not
  placed or has no size."""
  length, width = _num(length_mm), _num(width_mm)
  if not placed or not length or not width or length <= 0 or width <= 0:
    return None

  x, y = float(placed["position_mm"][0]), float(placed["position_mm"][1])
  x0, y0, x1, y1 = round(x - length / 2.0, 3), round(y - width / 2.0, 3), round(x + length / 2.0, 3), round(y + width / 2.0, 3)
  return {"x0": x0, "y0": y0, "x1": x1, "y1": y1, "plan_mm": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]}

def fields(cand, sizes: dict, placed: dict | None, zr: Z.ZRange | None, floor_key: str | None) -> dict:
  """The columns of a register row that say where the item is, and the note kept with the row's properties. Only what is known is written: no position, no
  box; no height range, no elevations. The result is the same for the same inputs, so writing it again changes nothing."""
  out: dict = {}
  meta: dict = {}
  
  box = box_of(placed, sizes.get("length_mm"), sizes.get("width_mm")) if cand.category in PLACED else None
  if zr is not None:
    meta["z"] = {**zr.as_dict(), "floor": floor_key}
    if zr.base_mm is not None:
      out["elevation_base_mm"] = _d(zr.base_mm)
    if zr.top_mm is not None:
      out["elevation_top_mm"] = _d(zr.top_mm)
      
  if box is not None:
    out.update({"bbox_min_x_mm": _d(box["x0"]), "bbox_min_y_mm": _d(box["y0"]), "bbox_max_x_mm": _d(box["x1"]), "bbox_max_y_mm": _d(box["y1"])})
  if zr is not None and zr.base_mm is not None and box is not None:
    out["bbox_min_z_mm"] = _d(zr.base_mm)
  if zr is not None and zr.top_mm is not None and box is not None:
    out["bbox_max_z_mm"] = _d(zr.top_mm)
    
  if box is not None or (zr is not None and zr.known):
    placement: dict = {"datum": zr.datum if zr is not None else Z.GROUND_LEVEL}
    if box is not None:
      placement.update({"plan_mm": box["plan_mm"], "plan_basis": PLAN_BASIS,
        "frame": {"view": placed["view"], "grade": placed["grade"], "method": placed["method"], "position_mm": list(placed["position_mm"])}})
    if zr is not None and zr.base_mm is not None and zr.top_mm is not None:
      placement.update({"z_min_mm": zr.base_mm, "z_max_mm": zr.top_mm, "z": meta["z"]})
    out["placement"] = placement
  return {"row": out, "meta": meta}