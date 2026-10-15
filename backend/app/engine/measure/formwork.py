from __future__ import annotations
from decimal import Decimal
from dataclasses import dataclass, field
from app.engine.measure.models import CalculationContext, LedgerEntry, Solid
from uuid import uuid5
from app.engine.measure.takeoff import SOURCE_KIND as PDF_SOURCE
from app.engine.measure.derived import DERIVED, FACTOR_ASSUMED, FACTOR_CONFIRMED, counted_measurement_ids, resolve_params
from app.engine.measure.units import q4, q6

FORMULA = "SOLID_FORMWORK_AREA"
RECIPE_CODE = "STRUCT_FORMWORK"
RECIPE_TYPES = ("IfcColumn", "IfcBeam", "IfcSlab", "IfcFooting")
FOOTING_PARAM, SLAB_EDGE_PARAM = "footing_formwork", "slab_edge_formwork"
FORMWORK_PARAMS = (FOOTING_PARAM, SLAB_EDGE_PARAM)
PARAMS_USED = {"FOOTING": (FOOTING_PARAM,), "SLAB": (SLAB_EDGE_PARAM,), "COLUMN": (), "LINTEL": (), "BEAM": (), "STAIR": (), "RCC_WALL": ()}
CATEGORIES = tuple(PARAMS_USED)
IFC_OF = {"COLUMN": "IfcColumn", "FOOTING": "IfcFooting", "SLAB": "IfcSlab", "LINTEL": "IfcBeam", "BEAM": "IfcBeam", "STAIR": "IfcStair", "RCC_WALL": "IfcWall"}
ROLE_OF = {"RCC_WALL": "WALL"}
MM2_PER_M2 = Decimal("1000000")
MM_PER_M = Decimal("1000")
MAX_MARKS = 5000

CODE_ASSUMED = "FORMWORK_ASSUMED"
FORMWORK_CODES = (CODE_ASSUMED,)

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
  measured = {str(((r.trace or {}).get("inputs") or {}).get("measurement_id")): r for r in (extra_ledger or ())
    if getattr(r, "source_kind", None) == PDF_SOURCE and r.quantity > 0 and r.unit == "m3"}
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
      row = measured.get(str(m.measurement_id))
      if row is None:
        skipped["NOT_COUNTED"] = skipped.get("NOT_COUNTED", 0) + m.count
        continue
      faces = [("both_faces", 2 * row.quantity / (width / MM_PER_M) * MM2_PER_M2)]
    else:
      faces = faces_for(cat, length, width, depth, edges, m.stair)
    used = PARAMS_USED[cat]
    assumed = [n for n in used if params[n]["source"] == "default"]
    
    factor = FACTOR_ASSUMED if assumed else FACTOR_CONFIRMED
    confidence = max(Decimal("0"), min(Decimal("1"), q4(m.confidence * factor)))
    warnings = [CODE_ASSUMED] if assumed else []
    spec = {"kind": DERIVED, "recipe": RECIPE_CODE, "item": "FORMWORK", "category": cat,
      "params": {n: params[n]["value"] for n in used}, "basis": {n: params[n]["source"] for n in used}}
    face_steps = [{"op": "face", "name": name, "m2": str(_m2(area))} for name, area in faces]
    quantity = q6(sum((_m2(area) for _, area in faces), Decimal("0")))
    for i in range(m.count):
      eid = m.element_ids[i] if i < len(m.element_ids) else None
      solid_id = uuid5(ctx.run_id, f"solid|formwork|{m.measurement_id}|{i}")
      solids.append(Solid(
        id=solid_id, element_id=eid, ifc_type=IFC_OF[cat], role=ROLE_OF.get(cat, cat), level_id=m.level_id, geometry_kind="QTO_ONLY",
        classification_confidence=m.confidence, confidence_factor=factor, component_type="DERIVED_FORMWORK",
        gross_area_m2=quantity, status="REVIEW_REQUIRED" if warnings else "OK"))
      source = {"measurement_id": str(m.measurement_id), "candidate_id": str(m.candidate_id), "sheet_id": str(m.sheet_id),
        "page_no": m.page_no, "category": cat, "tag": m.tag, "instance": i + 1, "instances": m.count,
        "size_mm": [float(length), float(width), float(depth)], **({"stair": m.stair} if m.stair else {}), "faces": [{"name": n, "m2": str(_m2(a))} for n, a in faces]}
      
      rows.append(LedgerEntry(
        solid_id=solid_id, element_id=eid, level_id=m.level_id, work_item_code=code, quantity=quantity, unit="m2", material_grade=None,
        confidence=confidence, formula_code=FORMULA,
        
        trace={
          "formula_code": FORMULA, "engine_version": ctx.engine_version, "convention": ctx.convention_code,
          "rule_set": {"code": ctx.rule_set_code, "version": ctx.rule_set_version},
          "inputs": {"recipe": RECIPE_CODE, "spec": spec, "formwork_source": source},
          "steps": [*face_steps, {"op": "net_area", "m2": str(quantity)}], "net": {"m2": str(quantity)}, "rounding": "half_up,6dp"},
        warnings=tuple(warnings), source_kind=DERIVED, spec=spec, spec_key="derived"))
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
    "contact_not_deducted": bool(rows),
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
