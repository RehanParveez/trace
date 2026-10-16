from __future__ import annotations
from decimal import Decimal
from dataclasses import dataclass, field
from app.engine.measure.models import CalculationContext, LedgerEntry, Solid
from uuid import uuid5
from app.engine.measure.takeoff import SOURCE_KIND as PDF_SOURCE
from app.engine.measure.derived import DERIVED, FACTOR_ASSUMED, FACTOR_CONFIRMED, counted_measurement_ids, resolve_params
from app.engine.measure.units import q4, q6
from app.engine.measure import frame as FR

FORMULA = "SOLID_FORMWORK_AREA"
RECIPE_CODE = "STRUCT_FORMWORK"
RECIPE_TYPES = ("IfcColumn", "IfcBeam", "IfcSlab", "IfcFooting")
FOOTING_PARAM, SLAB_EDGE_PARAM, SHARED_PARAM = "footing_formwork", "slab_edge_formwork", "formwork_shared_faces"
FORMWORK_PARAMS = (FOOTING_PARAM, SLAB_EDGE_PARAM, SHARED_PARAM)
PARAMS_USED = {"FOOTING": (FOOTING_PARAM,), "SLAB": (SLAB_EDGE_PARAM,), "COLUMN": (), "LINTEL": (), "BEAM": (), "STAIR": (), "RCC_WALL": ()}
CATEGORIES = tuple(PARAMS_USED)
IFC_OF = {"COLUMN": "IfcColumn", "FOOTING": "IfcFooting", "SLAB": "IfcSlab", "LINTEL": "IfcBeam", "BEAM": "IfcBeam", "STAIR": "IfcStair", "RCC_WALL": "IfcWall"}
ROLE_OF = {"RCC_WALL": "WALL"}
MM2_PER_M2 = Decimal("1000000")
MM_PER_M = Decimal("1000")
MAX_MARKS = 5000

CODE_ASSUMED = "FORMWORK_ASSUMED"
CODE_FRAME_ASSUMED = "FORMWORK_FRAME_ASSUMED"
FORMWORK_CODES = (CODE_ASSUMED, CODE_FRAME_ASSUMED)
SHARING = ("COLUMN",)
SHARED_BY = ("SLAB",)

@dataclass(frozen=True)
class FormworkResult:
  solids: list = field(default_factory=list)
  ledger: list = field(default_factory=list)
  stats: dict = field(default_factory=dict)

def _m2(mm2: Decimal) -> Decimal:
  return q6(mm2 / MM2_PER_M2)

def stair_faces(width: Decimal, stair: dict) -> list:
  """The shuttered faces of one flight of steps: the sloped soffit of the waist slab, the risers, and the two sides (the waist slab's edge plus the triangle of
  steps above it). The treads are the top of the concrete and are not shuttered."""
  riser, tread, waist = Decimal(str(stair["riser_mm"])), Decimal(str(stair["tread_mm"])), Decimal(str(stair["waist_mm"]))
  steps = Decimal(str(stair["steps"]))
  slope = steps * (riser * riser + tread * tread).sqrt()
  return [("soffit", slope * width), ("risers", steps * riser * width), ("sides", 2 * (slope * waist + steps * riser * tread / 2))]

def faces_for(category: str, length: Decimal, width: Decimal, depth: Decimal, edges: bool, stair: dict | None = None) -> list:
  """The shuttered faces of one member, as (name, area in mm2). A column carries all four vertical faces over its height; a footing its four sides over its
  depth; a slab its soffit and, when edge forms are wanted, the four edges over its thickness; a lintel or a beam its soffit and both sides (the top is open);
  a flight of steps its soffit, risers and sides."""
  perimeter = 2 * (length + width)
  
  if category == "COLUMN":
    return [("vertical_faces", perimeter * depth)]
  if category == "FOOTING":
    return [("sides", perimeter * depth)]
  if category == "SLAB":
    out = [("soffit", length * width)]
    if edges:
      out.append(("edges", perimeter * depth))
    return out
  if category in ("LINTEL", "BEAM"):
    return [("soffit", length * width), ("sides", 2 * length * depth)]
  if category == "STAIR" and stair:
    return stair_faces(width, stair)
  return []

def _frames_of(takeoff) -> dict:
  """One frame per group of views (a drawing): {group: Frame}. Views of different drawings are never placed in one frame."""
  return FR.frames_of(takeoff)

def shared_faces(inputs: tuple, takeoff, enabled: bool) -> tuple:
  """The side faces of each column instance that a slab of its floor covers, found in the building frame. Returns ({(measurement id, instance): [faces]},
  stats). The slab is taken to run over the top of the column to its own thickness (a column is measured to the top of the slab it carries), and its
  outline is the covered area's length x width centred where the slab was found. Columns and slabs that are not placed in the frame are left alone and
  counted, so their gross shuttering stands."""
  stats: dict = {"enabled": enabled, "placed_columns": 0, "unplaced_columns": 0, "removed_m2": "0", "members_with_removal": 0, "uncertain_members": 0}
  frames = _frames_of(takeoff)
  if not enabled or not frames:
    stats["enabled"] = bool(enabled) and bool(frames)
    return {}, stats
  group_of = {a.view: a.group for a in tuple(getattr(takeoff, "alignments", ()) or ())}
  def place(view, x, y):
    f = frames.get(group_of.get(view))
    return FR.frame_xy(f, view, x, y) if f is not None else None

  slabs = []
  for m in inputs:
    if m.category in SHARED_BY and m.frame and m.points_mm:
      p = place(m.frame, float(m.points_mm[0][0]), float(m.points_mm[0][1]))
      if p is not None:
        slabs.append((m, p))
  out: dict = {}
  removed = Decimal("0")
  for m in inputs:
    if m.category not in SHARING:
      continue
    if not (m.frame and m.points_mm):
      stats["unplaced_columns"] += m.count
      continue
    height, length, width = float(m.depth_mm), float(m.length_mm), float(m.width_mm)
    for i, pt in enumerate(m.points_mm[:m.count]):
      p = place(m.frame, float(pt[0]), float(pt[1]))
      if p is None:
        stats["unplaced_columns"] += 1
        continue
      stats["placed_columns"] += 1
      col = FR.box_around(p[0], p[1], length, width, 0.0, height)
      
      near = []
      for s, (sx, sy) in slabs:
        if s.level_id is not None and m.level_id is not None and s.level_id != m.level_id:
          continue
        if group_of.get(s.frame) != group_of.get(m.frame):
          continue
        t = min(float(s.depth_mm), height)
        near.append((f"slab {s.tag or ''}".strip(), FR.box_around(sx, sy, float(s.length_mm), float(s.width_mm), height - t, height), s))
      faces = FR.shared_side_faces(col, [(label, box) for label, box, _ in near])
      if not faces:
        continue
      uncertain = False
      for label, _, s in near:
        if any(f["by"] == label for f in faces) and (s.level_id is None) != (m.level_id is None):
          uncertain = True
        if any(f["by"] == label for f in faces) and s.frame != m.frame:
          f = frames[group_of[m.frame]]
          a, b = f.alignments.get(m.frame), f.alignments.get(s.frame)
          if any(x is None or x.grade != FR.CONFIRMED for x in (a, b)):
            uncertain = True
            
      out[(str(m.measurement_id), i)] = {"faces": faces, "uncertain": uncertain}
      stats["members_with_removal"] += 1
      stats["uncertain_members"] += 1 if uncertain else 0
      removed += sum((Decimal(str(f["area_mm2"])) for f in faces), Decimal("0")) / MM2_PER_M2
  stats["removed_m2"] = str(q6(removed))
  stats["alignments"] = {k: {"method": a.method, "grade": a.grade, "dx_mm": a.dx_mm, "dy_mm": a.dy_mm}
    for f in frames.values() for k, a in sorted(f.alignments.items())}
  return out, stats

def _recipe_code(profile) -> str | None:
  if profile is None:
    return None
  for ifc in RECIPE_TYPES:
    for recipe in profile.recipes_for(ifc):
      if recipe.code == RECIPE_CODE:
        for c in recipe.components:
          if c.formula_code == FORMULA and c.work_item_code:
            return c.work_item_code
  return None

def measure_formwork(ctx: CalculationContext, profile, ledger: list, extra_ledger=()) -> FormworkResult:
  """Formwork area for the concrete members read from a PDF and counted in this run: columns, footings, slabs, lintels, beams, flights of steps and RCC walls (both faces over the net area the wall's own measurement worked out). One row per mark, so a row
  opens the mark it came from. Faces that touch other concrete (a slab over its beams, a column through a slab) are not taken off: the members of a PDF
  are not placed in one building frame yet, so that contact cannot be found, and the area is reported as the gross shuttering of each member."""
  stats: dict = {"enabled": True, "ran": False}
  inputs = tuple(getattr(ctx.takeoff, "formwork", ()) or ())
  if not inputs:
    stats["reason"] = "NO_MEMBERS"
    return FormworkResult(stats=stats)
  code = _recipe_code(profile)
  if code is None:
    stats["reason"] = "NO_RECIPE"
    return FormworkResult(stats=stats)
  model_codes = {r.work_item_code for r in ledger if r.source_kind == "MODEL" and r.quantity > 0}
  model_codes |= {r.work_item_code for r in (extra_ledger or ()) if getattr(r, "source_kind", None) == PDF_SOURCE and r.quantity > 0}
  if code in model_codes:
    stats["reason"] = "ALL_ITEMS_IN_MODEL"
    return FormworkResult(stats=stats)
  if sum(m.count for m in inputs) > MAX_MARKS:
    stats["reason"] = "TOO_MANY_MARKS"
    return FormworkResult(stats=stats)

  params = resolve_params(ctx)
  counted = counted_measurement_ids(extra_ledger)
  removals, frame_stats = shared_faces(tuple(m for m in inputs if str(m.measurement_id) in counted), ctx.takeoff, params[SHARED_PARAM]["value"] >= 0.5)
  measured: dict = {}
  for r in (extra_ledger or ()):
    if getattr(r, "source_kind", None) == PDF_SOURCE and r.quantity > 0 and r.unit == "m3":
      key = str(((r.trace or {}).get("inputs") or {}).get("measurement_id"))
      measured[key] = measured.get(key, Decimal("0")) + r.quantity   
  skipped: dict = {}
  by_category: dict = {}
  solids: list = []
  rows: list = []
  
  for m in sorted(inputs, key=lambda b: str(b.measurement_id)):
    cat = m.category
    if cat not in PARAMS_USED:
      skipped["CATEGORY_NOT_SHUTTERED"] = skipped.get("CATEGORY_NOT_SHUTTERED", 0) + m.count
      continue
    if str(m.measurement_id) not in counted:
      skipped["NOT_COUNTED"] = skipped.get("NOT_COUNTED", 0) + m.count
      continue
    if cat == "FOOTING" and params[FOOTING_PARAM]["value"] < 0.5:
      key = "FOOTING_NOT_SHUTTERED_DEFAULT" if params[FOOTING_PARAM]["source"] == "default" else "FOOTING_NOT_SHUTTERED"
      skipped[key] = skipped.get(key, 0) + m.count
      continue
    length, width, depth = m.length_mm, m.width_mm, m.depth_mm
    if not (length > 0 and width > 0 and depth > 0):
      skipped["NO_SIZE"] = skipped.get("NO_SIZE", 0) + m.count
      continue
    edges = params[SLAB_EDGE_PARAM]["value"] >= 0.5
    if cat == "STAIR" and not m.stair:
      skipped["STAIR_NO_DETAIL"] = skipped.get("STAIR_NO_DETAIL", 0) + m.count
      continue
  
    if cat == "RCC_WALL":
      volume = measured.get(str(m.measurement_id))
      if volume is None:
        skipped["NOT_COUNTED"] = skipped.get("NOT_COUNTED", 0) + m.count
        continue
      faces = [("both_faces", 2 * volume / (width / MM_PER_M) * MM2_PER_M2)]
    else:
      faces = faces_for(cat, length, width, depth, edges, m.stair)
    used = PARAMS_USED[cat]
    assumed = [n for n in used if params[n]["source"] == "default"]
    
    factor = FACTOR_ASSUMED if assumed else FACTOR_CONFIRMED
    confidence = max(Decimal("0"), min(Decimal("1"), q4(m.confidence * factor)))
    warnings = [CODE_ASSUMED] if assumed else []
    spec = {"kind": DERIVED, "recipe": RECIPE_CODE, "item": "FORMWORK", "category": cat,
      "params": {n: params[n]["value"] for n in used}, "basis": {n: params[n]["source"] for n in used}}
    for i in range(m.count):
      cut = removals.get((str(m.measurement_id), i))
      inst_faces = list(faces)
      inst_warnings = list(warnings)
      inst_factor, inst_spec = factor, spec
      
      if cut:
        inst_faces += [(f"shared {f['face']} face with {f['by']}", -Decimal(str(f["area_mm2"]))) for f in cut["faces"]]
        inst_spec = {**spec, "params": {**spec["params"], SHARED_PARAM: params[SHARED_PARAM]["value"]},
          "basis": {**spec["basis"], SHARED_PARAM: params[SHARED_PARAM]["source"]}}
        if cut["uncertain"]:
          inst_warnings.append(CODE_FRAME_ASSUMED)
          inst_factor = min(factor, FACTOR_ASSUMED)
      inst_confidence = max(Decimal("0"), min(Decimal("1"), q4(m.confidence * inst_factor)))
      face_steps = [{"op": "face", "name": name, "m2": str(_m2(area))} for name, area in inst_faces]
      quantity = max(Decimal("0"), q6(sum((_m2(area) for _, area in inst_faces), Decimal("0"))))
      eid = m.element_ids[i] if i < len(m.element_ids) else None
      solid_id = uuid5(ctx.run_id, f"solid|formwork|{m.measurement_id}|{i}")
      solids.append(Solid(
        id=solid_id, element_id=eid, ifc_type=IFC_OF[cat], role=ROLE_OF.get(cat, cat), level_id=m.level_id, geometry_kind="QTO_ONLY",
        classification_confidence=m.confidence, confidence_factor=inst_factor, component_type="DERIVED_FORMWORK",
        gross_area_m2=quantity, status="REVIEW_REQUIRED" if inst_warnings else "OK"))
      source = {"measurement_id": str(m.measurement_id), "candidate_id": str(m.candidate_id), "sheet_id": str(m.sheet_id),
        "page_no": m.page_no, "category": cat, "tag": m.tag, "instance": i + 1, "instances": m.count,
        "size_mm": [float(length), float(width), float(depth)], **({"stair": m.stair} if m.stair else {}),
        "faces": [{"name": n, "m2": str(_m2(a))} for n, a in inst_faces],
        **({"shared_faces": [{"face": f["face"], "by": f["by"], "m2": str(_m2(Decimal(str(f["area_mm2"]))))} for f in cut["faces"]],
          "frame": m.frame} if cut else {})}

      rows.append(LedgerEntry(
        solid_id=solid_id, element_id=eid, level_id=m.level_id, work_item_code=code, quantity=quantity, unit="m2", material_grade=None,
        confidence=inst_confidence, formula_code=FORMULA,

        trace={
          "formula_code": FORMULA, "engine_version": ctx.engine_version, "convention": ctx.convention_code,
          "rule_set": {"code": ctx.rule_set_code, "version": ctx.rule_set_version},
          "inputs": {"recipe": RECIPE_CODE, "spec": inst_spec, "formwork_source": source},
          "steps": [*face_steps, {"op": "net_area", "m2": str(quantity)}], "net": {"m2": str(quantity)}, "rounding": "half_up,6dp"},
        warnings=tuple(inst_warnings), source_kind=DERIVED, spec=inst_spec, spec_key="derived"))
      slot = by_category.setdefault(cat, {"marks": 0, "m2": Decimal("0")})
      slot["marks"] += 1
      slot["m2"] += quantity
      
  rows.sort(key=lambda r: (str(r.level_id), r.trace["inputs"]["formwork_source"]["category"], str(r.solid_id)))
  total = sum((r.quantity for r in rows), Decimal("0"))
  stats.update({
    "ran": bool(rows), "rows": len(rows), "area_m2": str(q6(total)), "code": code,
    "by_category": {k: {"marks": v["marks"], "m2": str(q6(v["m2"]))} for k, v in sorted(by_category.items())},
    "skipped": dict(sorted(skipped.items())),
    "params": {n: dict(params[n]) for n in FORMWORK_PARAMS},
    "assumed": sorted({n for r in rows for n, b in ((r.spec or {}).get("basis") or {}).items() if b == "default"}),
    "contact_not_deducted": bool(rows) and not frame_stats.get("members_with_removal"),
    "shared_faces": frame_stats,
  })
  if not rows:
    stats["reason"] = "NOTHING_TO_SHUTTER"
  return FormworkResult(solids=solids, ledger=rows, stats=stats)

def formwork_check(solids: list, ledger: list) -> list:
  failures: list = []
  
  by_id = {s.id for s in solids}
  for r in ledger:
    if r.source_kind != DERIVED or r.formula_code != FORMULA:
      continue
    if r.solid_id not in by_id:
      failures.append(f"formwork row references unknown solid {r.solid_id}")
    if r.unit != "m2":
      failures.append(f"formwork row {r.solid_id} is not in m2")
    if r.work_stage is not None:
      failures.append(f"formwork row {r.solid_id} carries a work stage")
    faces = (((r.trace or {}).get("inputs") or {}).get("formwork_source") or {}).get("faces") or []
    try:
      total = sum((Decimal(f["m2"]) for f in faces), Decimal("0"))
    except Exception:
      failures.append(f"formwork row {r.solid_id} has no faces in its trace")
      continue
    if abs(total - r.quantity) > Decimal("0.000002"):
      failures.append(f"formwork area != sum of its faces on solid {r.solid_id}")
  return failures
