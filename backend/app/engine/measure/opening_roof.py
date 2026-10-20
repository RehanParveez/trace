from __future__ import annotations
from decimal import Decimal
from app.engine.measure.takeoff import SOURCE_KIND as PDF_SOURCE
from dataclasses import dataclass, field
from app.engine.measure.units import q6, q4
from app.engine.measure.models import Solid, LedgerEntry, CalculationContext
from uuid import uuid5
from app.engine.measure.spatial import prism_and_polygon
from app.engine.measure import stages as S
from app.engine.measure.derived import DERIVED, FACTOR_ASSUMED, resolve_params

OPENING_PARAM, ROOF_PARAM = "opening_area_from_model", "roof_treatment_from_slabs"
OPENING_FORMULA, ROOF_FORMULA = "OPENING_AREA", "ROOF_TREATMENT_AREA"
OPENING_RECIPE, ROOF_RECIPE = "OPENING_AREA_FROM_MODEL", "ROOF_TREATMENT_FROM_SLABS"
SIZE_FROM_BOX, ROOF_FROM_PLAN = "OPENING_SIZE_FROM_BOX", "ROOF_AREA_FROM_PLAN"
CODES = (SIZE_FROM_BOX, ROOF_FROM_PLAN)
OPENING_ITEMS = {"DOOR": ("DOOR_AREA", "JOI-DOOR-AREA"), "WINDOW": ("WINDOW_AREA", "JOI-WIN-AREA")}
ROOF_ITEM, ROOF_CODE = "ROOF_TREATMENT", "FIN-ROOF-TREAT"
ROOF_ROLES = frozenset({"SLAB_ROOF"})
MM2_PER_M2 = Decimal("1000000")
FORMULAS = (OPENING_FORMULA, ROOF_FORMULA)

@dataclass(frozen=True)
class AreaWorksResult:
  solids: list = field(default_factory=list)
  ledger: list = field(default_factory=list)
  stats: dict = field(default_factory=dict)

def _m2(mm2: float) -> Decimal:
  return q6(Decimal(repr(max(0.0, float(mm2)))) / MM2_PER_M2)

def _taken(ledger: list, extra_ledger) -> set:
  codes = {r.work_item_code for r in ledger if r.source_kind == "MODEL" and r.quantity > 0}
  codes |= {r.work_item_code for r in (extra_ledger or ()) if getattr(r, "source_kind", None) in ("MODEL", PDF_SOURCE) and r.quantity > 0}
  return codes

def opening_size(poly, z) -> tuple | None:
  if poly is None or z is None:
    return None
  try:
    rect = poly.minimum_rotated_rectangle
    xs = list(rect.exterior.coords)
    a = ((xs[1][0] - xs[0][0]) ** 2 + (xs[1][1] - xs[0][1]) ** 2) ** 0.5
    b = ((xs[2][0] - xs[1][0]) ** 2 + (xs[2][1] - xs[1][1]) ** 2) ** 0.5
  except (AttributeError, IndexError, ValueError):
    return None
  width, height = max(a, b), float(z[1]) - float(z[0])
  return (width, height) if width > 0 and height > 0 else None

def _row(ctx, el, solid_of_el, recipe: str, formula: str, item: str, code: str, area: Decimal, steps: list, detail: dict, basis: dict, warning: str) -> tuple:
  spec = {"kind": DERIVED, "recipe": recipe, "item": item, "params": {}, "basis": basis}
  base = solid_of_el.classification_confidence * solid_of_el.confidence_factor if solid_of_el is not None else Decimal("0.9")
  confidence = max(Decimal("0"), min(Decimal("1"), q4(base * FACTOR_ASSUMED)))
  
  solid = Solid(id=uuid5(ctx.run_id, f"solid|areaworks|{el.id}|{item}"), element_id=el.id, ifc_type=el.ifc_type, role=el.role, level_id=el.level_id, geometry_kind="QTO_ONLY",
    classification_confidence=solid_of_el.classification_confidence if solid_of_el is not None else Decimal("0.9"),
    confidence_factor=(solid_of_el.confidence_factor if solid_of_el is not None else Decimal("1")) * FACTOR_ASSUMED, component_type=f"DERIVED_{item}",
    gross_area_m2=area, status="REVIEW_REQUIRED")
  
  row = LedgerEntry(solid_id=solid.id, element_id=el.id, level_id=el.level_id, work_item_code=code, quantity=area, unit="m2", material_grade=None, confidence=confidence,
    formula_code=formula,
    trace={"formula_code": formula, "engine_version": ctx.engine_version, "convention": ctx.convention_code,
      "rule_set": {"code": ctx.rule_set_code, "version": ctx.rule_set_version},
      "inputs": {"recipe": recipe, "spec": spec, "source_element_id": str(el.id), **detail}, "steps": steps, "net": {"m2": str(area)}, "rounding": "half_up,6dp"},
    warnings=(warning,), source_kind=DERIVED, spec=spec, spec_key="derived")
  return solid, row

def measure_opening_area(ctx: CalculationContext, elements: list, solids: list, ledger: list, extra_ledger=()) -> AreaWorksResult:
  params = resolve_params(ctx)
  on = params[OPENING_PARAM]["value"] >= 0.5
  stats: dict = {"enabled": on, "ran": False, "param_source": params[OPENING_PARAM]["source"]}
  
  if not on:
    stats["reason"] = "SWITCHED_OFF"
    return AreaWorksResult(stats=stats)
  taken = _taken(ledger, extra_ledger)
  wanted = {role: v for role, v in OPENING_ITEMS.items() if v[1] not in taken}
  stats["skipped"] = {v[1]: "ALREADY_MEASURED" for v in OPENING_ITEMS.values() if v[1] in taken}
  if not wanted:
    stats["reason"] = "ALL_ITEMS_ALREADY_MEASURED"
    return AreaWorksResult(stats=stats)
  solid_of = {s.element_id: s for s in solids if s.element_id is not None and s.component_type == "BODY"}
  out_solids, out_rows = [], []
  totals = {role: Decimal("0") for role in wanted}
  counts = {role: 0 for role in wanted}
  
  no_size = 0
  for el in sorted(elements, key=lambda e: str(e.id)):
    role = (el.role or "").upper()
    if role not in wanted:
      continue
    found = prism_and_polygon(el)
    size = opening_size(found[1] if found is not None else None, S.element_z(el))
    if size is None:
      no_size += 1
      continue
    width, height = size
    area = _m2(width * height)
    if area <= 0:
      no_size += 1
      continue
  
    item, code = wanted[role]
    steps = [{"op": "opening_size", "width_mm": round(width, 1), "height_mm": round(height, 1), "note": "long side of the footprint box times the height"},
      {"op": "net_area", "m2": str(area)}]
    s_, r_ = _row(ctx, el, solid_of.get(el.id), OPENING_RECIPE, OPENING_FORMULA, item, code, area, steps, {"width_mm": round(width, 1), "height_mm": round(height, 1)},
      {"size": "geometry"}, SIZE_FROM_BOX)
    out_solids.append(s_)
    out_rows.append(r_)
    totals[role] += area
    counts[role] += 1
    
  out_rows.sort(key=lambda r: (r.work_item_code, str(r.level_id), str(r.element_id)))
  stats.update({"ran": bool(out_rows), "rows": len(out_rows), "no_size": no_size,
    "doors": counts.get("DOOR", 0), "windows": counts.get("WINDOW", 0),
    "door_area_m2": str(q6(totals.get("DOOR", Decimal("0")))), "window_area_m2": str(q6(totals.get("WINDOW", Decimal("0"))))})
  if not out_rows:
    stats["reason"] = "NO_OPENINGS"
  return AreaWorksResult(solids=out_solids, ledger=out_rows, stats=stats)

def measure_roof_treatment(ctx: CalculationContext, elements: list, solids: list, ledger: list, extra_ledger=()) -> AreaWorksResult:
  params = resolve_params(ctx)
  on = params[ROOF_PARAM]["value"] >= 0.5
  stats: dict = {"enabled": on, "ran": False, "param_source": params[ROOF_PARAM]["source"]}
  if not on:
    stats["reason"] = "SWITCHED_OFF"
    return AreaWorksResult(stats=stats)
  if ROOF_CODE in _taken(ledger, extra_ledger):
    stats["reason"] = "ALREADY_MEASURED"
    stats["skipped"] = {ROOF_CODE: "ALREADY_MEASURED"}
    return AreaWorksResult(stats=stats)

  solid_of = {s.element_id: s for s in solids if s.element_id is not None and s.component_type == "BODY"}
  measured = {r.element_id for r in ledger if r.source_kind == "MODEL" and r.quantity > 0}
  out_solids, out_rows = [], []
  total = Decimal("0")
  no_plan = roof_slabs = 0
  
  for el in sorted(elements, key=lambda e: str(e.id)):
    if (el.role or "").upper() not in ROOF_ROLES or el.id not in measured:
      continue
    roof_slabs += 1
    found = prism_and_polygon(el)
    if found is None or found[1] is None or found[1].area <= 0:
      no_plan += 1
      continue
    area = _m2(found[1].area)
    if area <= 0:
      no_plan += 1
      continue
  
    steps = [{"op": "plan_area", "m2": str(area), "note": "flat roof assumed; slope, upstand and holes in the slab are not taken"}, {"op": "net_area", "m2": str(area)}]
    s_, r_ = _row(ctx, el, solid_of.get(el.id), ROOF_RECIPE, ROOF_FORMULA, ROOF_ITEM, ROOF_CODE, area, steps, {"plan_area_m2": str(area)}, {"area": "plan"}, ROOF_FROM_PLAN)
    out_solids.append(s_)
    out_rows.append(r_)
    total += area
    
  out_rows.sort(key=lambda r: (r.work_item_code, str(r.level_id), str(r.element_id)))
  stats.update({"ran": bool(out_rows), "rows": len(out_rows), "roof_slabs": roof_slabs, "no_plan": no_plan, "area_m2": str(q6(total))})
  if not roof_slabs:
    stats["reason"] = "NO_ROOF_SLAB"
  elif not out_rows:
    stats["reason"] = "NOTHING_TO_MEASURE"
  return AreaWorksResult(solids=out_solids, ledger=out_rows, stats=stats)

def opening_roof_check(solids: list, ledger: list) -> list:
  ids = {s.id for s in solids}
  out = []
  
  for r in ledger:
    if r.formula_code not in FORMULAS:
      continue
    if r.solid_id not in ids:
      out.append(f"{r.work_item_code}: area row has no solid")
    if r.unit != "m2" or r.quantity <= 0:
      out.append(f"{r.work_item_code}: area quantity {r.quantity} {r.unit}")
    if r.source_kind != DERIVED:
      out.append(f"{r.work_item_code}: area row is not a derived row")
    if r.element_id is None:
      out.append(f"{r.work_item_code}: area row has no element")
  return out
