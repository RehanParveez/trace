from __future__ import annotations
from shapely.geometry import Polygon
from app.engine.measure.takeoff import FormworkInput
from decimal import Decimal
from shapely.strtree import STRtree
from shapely.geometry import box as sbox
from app.engine.measure import frame as FR
from app.engine.measure.units import q6

ROLE_CATEGORY = {
  "COLUMN": "COLUMN", "COLUMN_STRUCTURAL": "COLUMN",
  "BEAM": "BEAM", "BEAM_STRUCTURAL": "BEAM", "BEAM_EDGE": "BEAM", "BEAM_TRANSFER": "BEAM", "EDGE_BEAM": "BEAM", "GIRDER": "BEAM", "GIRDER_SEGMENT": "BEAM", "GROUND_BEAM": "BEAM",
  "LINTEL": "LINTEL",
  "SLAB": "SLAB", "SLAB_STRUCTURAL": "SLAB", "SLAB_ROOF": "SLAB", "SLAB_LANDING": "SLAB", "SLAB_POST_TENSIONED": "SLAB",
  "FOOTING": "FOOTING", "FOOTING_ISOLATED": "FOOTING", "FOOTING_STRIP": "FOOTING", "FOOTING_COMBINED": "FOOTING", "PILE_CAP": "FOOTING",
  "WALL_RETAINING": "RCC_WALL", "WALL_SHEAR": "RCC_WALL", "WALL_CORE": "RCC_WALL",
}
CONCRETE_WALL_ROLES = ("WALL", "WALL_EXTERNAL", "WALL_INTERNAL", "WALL_LOAD_BEARING")
NOT_SHUTTERED = {"SLAB_FOUNDATION": "RAFT_NOT_SHUTTERED", "SLAB_GROUND": "SLAB_ON_GROUND", "SLAB_PRECAST": "PRECAST", "BEAM_PRECAST": "PRECAST", "COLUMN_PRECAST": "PRECAST",
  "PILE": "PILE", "STAIR": "STAIR_NO_DETAIL", "STAIR_FLIGHT": "STAIR_NO_DETAIL"}
BOX_TOL = 0.03
BEAM_SLAB_ROLES = (None, "ROOF")
BEAM_SLAB_MAX_SHARE = 0.35
NEAR_MM = 5.0

def category_of(el) -> str | None:
  role = (el.role or "").upper()
  if role in ROLE_CATEGORY:
    return ROLE_CATEGORY[role]
  if role in CONCRETE_WALL_ROLES and str(el.material_class or "").upper() == "CONCRETE":
    return "RCC_WALL"
  return None

def _plan(el):
  pl = el.placement or {}
  pts = pl.get("plan_mm") or pl.get("outline_mm") or []
  holes = [] if pl.get("plan_mm") else (pl.get("outline_holes_mm") or [])
  try:
    poly = Polygon([(float(x), float(y)) for x, y in pts], [[(float(x), float(y)) for x, y in h] for h in holes if len(h) >= 3]) if len(pts) >= 3 else None
  except (TypeError, ValueError):
    poly = None
  return poly if poly is not None and poly.is_valid and poly.area > 0 else None

def _extent(el):
  lo, hi = el.bbox_min_mm, el.bbox_max_mm
  if not lo or not hi:
    return None
  return float(lo[0]), float(lo[1]), float(lo[2]), float(hi[0]), float(hi[1]), float(hi[2])

def _is_box(el, poly, ext) -> bool:
  """The footprint is its own bounding rectangle (within 3 per cent of the area)."""
  if poly is None:
    return True
  w, d = ext[3] - ext[0], ext[4] - ext[1]
  return w > 0 and d > 0 and abs(poly.area - w * d) <= BOX_TOL * w * d

def _sizes(cat: str, el, poly, ext) -> tuple:
  w, d, h = ext[3] - ext[0], ext[4] - ext[1], ext[5] - ext[2]
  
  if poly is not None and not _is_box(el, poly, ext):
    if cat == "SLAB":
      width = min(w, d)
      return poly.area / width, width, h, True
    rect = poly.minimum_rotated_rectangle
    xs = list(rect.exterior.coords)
    a = ((xs[1][0] - xs[0][0]) ** 2 + (xs[1][1] - xs[0][1]) ** 2) ** 0.5
    b = ((xs[2][0] - xs[1][0]) ** 2 + (xs[2][1] - xs[1][1]) ** 2) ** 0.5
    return max(a, b), min(a, b), h, True
  if cat in ("BEAM", "LINTEL", "RCC_WALL"):
    return max(w, d), min(w, d), h, False
  return w, d, h, False

def model_inputs(elements, measured_ids: set) -> tuple:
  """(inputs, items, stats): the FormworkInput of each shuttered member of the model, {id: (element, Box or None, category)}, and what was left out and why."""
  inputs: list = []
  items: dict = {}
  stats: dict = {"members": 0, "not_box": 0, "skipped": {}}
  skipped = stats["skipped"]

  def skip(key):
    skipped[key] = skipped.get(key, 0) + 1

  for el in sorted(elements or (), key=lambda e: str(e.id)):
    if (el.role or "").upper() in NOT_SHUTTERED:
      skip(NOT_SHUTTERED[el.role.upper()])
      continue
    cat = category_of(el)
    if cat is None:
      continue
    if el.id not in measured_ids:
      skip("NOT_MEASURED_IN_MODEL")
      continue
    ext = _extent(el)
    if ext is None:
      skip("NO_SIZE")
      continue
  
    poly = _plan(el)
    length, width, depth, assumed = _sizes(cat, el, poly, ext)
    if min(length, width, depth) <= 0:
      skip("NO_SIZE")
      continue
  
    round_mm = None
    if cat == "COLUMN" and isinstance(el.profile, dict) and el.profile.get("kind") == "CIRCLE":
      try:
        radius = float(el.profile.get("radius"))
      except (TypeError, ValueError):
        radius = 0.0
      if radius > 0:
        round_mm = Decimal(str(round(2 * radius, 3)))
        length = width = float(round_mm)
        stats["round"] = stats.get("round", 0) + 1
    box = sbox_of(ext) if _is_box(el, poly, ext) else None
    stats["not_box"] += 0 if box is not None else 1
    role = "PLINTH" if (el.role or "").upper() == "GROUND_BEAM" else None
    inputs.append(FormworkInput(measurement_id=el.id, candidate_id=el.id, sheet_id=None, page_no=None, category=cat, tag=el.ifc_global_id, level_id=el.level_id,
      element_ids=(el.id,), count=1, length_mm=Decimal(str(round(length, 3))), width_mm=Decimal(str(round(width, 3))), depth_mm=Decimal(str(round(depth, 3))),
      confidence=Decimal(str(el.classification_confidence)) * (Decimal("0.9") if assumed else Decimal("1")), role=role, round_mm=round_mm))
    items[str(el.id)] = (el, box, cat)
    stats["members"] += 1
  return tuple(inputs), items, stats

def sbox_of(ext) -> FR.Box:
  return FR.Box(ext[0], ext[1], ext[3], ext[4], ext[2], ext[5])

def _pick(tree, target: FR.Box) -> list:
  """The indexes of the boxes whose plan rectangle reaches the target (within a few mm)."""
  g = sbox(target.x0 - NEAR_MM, target.y0 - NEAR_MM, target.x1 + NEAR_MM, target.y1 + NEAR_MM)
  return [int(i) for i in tree.query(g)]

def _label(kind: str, el) -> str:
  return f"{kind} {el.ifc_global_id or ''}".strip()

def removals(items: dict, shared_on: bool, walls_on: bool, beams_on: bool, sides_inside_slab: bool) -> tuple:
  """({(measurement id, 0): {"faces": [...], "uncertain": False}}, stats)."""
  stats = {"enabled": shared_on, "columns_with_removal": 0, "beams_matched": 0, "beams_adjusted": 0, "slabs_with_removal": 0, "removed_m2": "0", "removed_by": {}}
  if not shared_on:
    return {}, stats
  boxed = [(k, el, box, cat) for k, (el, box, cat) in sorted(items.items()) if box is not None]
  if not boxed:
    return {}, stats
  polys = [sbox(b.x0, b.y0, b.x1, b.y1) for _, _, b, _ in boxed]
  tree = STRtree(polys)
  out: dict = {}
  removed = 0.0
  by_kind: dict = {}

  def add(key, face, by, area, kind):
    nonlocal removed
    slot = out.setdefault((key, 0), {"faces": [], "uncertain": False})
    slot["faces"].append({"face": face, "by": by, "area_mm2": float(area)})
    removed += area
    by_kind[kind] = by_kind.get(kind, 0.0) + area

  for i, (key, el, box, cat) in enumerate(boxed):
    if cat != "COLUMN":
      continue
    near = []
    for j in _pick(tree, box):
      k2, el2, box2, cat2 = boxed[j]
      if j == i or not _z_overlaps(box, box2):
        continue
      if cat2 in ("SLAB",) or (cat2 in ("BEAM", "LINTEL") and beams_on) or (cat2 == "RCC_WALL" and walls_on):
        near.append((_label({"SLAB": "slab", "BEAM": "beam", "LINTEL": "beam", "RCC_WALL": "wall"}[cat2], el2), box2, cat2))
    kind_of = {label: cat2 for label, _, cat2 in near}
    faces = FR.shared_side_faces(box, [(label, b) for label, b, _ in near])
    if faces:
      stats["columns_with_removal"] += 1
      for f in faces:
        add(key, f["face"], f["by"], f["area_mm2"], {"SLAB": "slab", "BEAM": "beam", "LINTEL": "beam", "RCC_WALL": "wall"}.get(kind_of.get(f["by"]), "slab"))

  slabs = [(k, el, b) for k, el, b, c in boxed if c == "SLAB"]
  room = {k: (b.x1 - b.x0) * (b.y1 - b.y0) * BEAM_SLAB_MAX_SHARE for k, _, b in slabs}
  slab_polys = [sbox(b.x0, b.y0, b.x1, b.y1) for _, _, b in slabs]
  slab_tree = STRtree(slab_polys) if slabs else None
  for key, el, box, cat in boxed:
    if cat != "BEAM" or slab_tree is None:
      continue
    role = "PLINTH" if (el.role or "").upper() == "GROUND_BEAM" else None
    if role not in BEAM_SLAB_ROLES:
      continue
    centre = sbox((box.x0 + box.x1) / 2 - 1, (box.y0 + box.y1) / 2 - 1, (box.x0 + box.x1) / 2 + 1, (box.y0 + box.y1) / 2 + 1)
    host = None
    for idx in slab_tree.query(centre):
      k2, el2, b2 = slabs[int(idx)]
      if abs(b2.z1 - box.z1) <= NEAR_MM and b2.z0 < box.z1 and (host is None or (b2.x1 - b2.x0) * (b2.y1 - b2.y0) > (host[2].x1 - host[2].x0) * (host[2].y1 - host[2].y0)):
        host = (k2, el2, b2)
    if host is None:
      continue
  
    stats["beams_matched"] += 1
    k2, el2, b2 = host
    length, width = max(box.x1 - box.x0, box.y1 - box.y0), min(box.x1 - box.x0, box.y1 - box.y0)
    slab_t, beam_d = b2.z1 - b2.z0, box.z1 - box.z0
    if sides_inside_slab and beam_d > slab_t:
      add(key, "sides", _label("slab", el2), 2 * length * slab_t, "slab")
      stats["beams_adjusted"] += 1
    take = min(length * width, room[k2])
    if take > 0:
      room[k2] -= take
      add(k2, "soffit", _label("beam", el), take, "beam")

  stats["slabs_with_removal"] = sum(1 for k, _, _ in slabs if (k, 0) in out)
  stats["removed_m2"] = str(q6(Decimal(str(removed)) / Decimal("1000000")))
  stats["removed_by"] = {k: str(q6(Decimal(str(v)) / Decimal("1000000"))) for k, v in sorted(by_kind.items())}
  return out, stats

def _z_overlaps(a: FR.Box, b: FR.Box) -> bool:
  return min(a.z1, b.z1) - max(a.z0, b.z0) > FR.TOUCH_TOL_MM
