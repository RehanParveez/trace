from __future__ import annotations
from decimal import Decimal
from dataclasses import dataclass, field
from app.engine.measure.takeoff import SOURCE_KIND as PDF_SOURCE
import math
from uuid import uuid5
from app.engine.measure import proposed as QP
from app.engine.measure import stages as S
from app.engine.measure.models import Solid, CalculationContext, LedgerEntry
from app.engine.measure.derived import CODE_ASSUMED, DERIVED, FACTOR_ASSUMED, WALL_BED_ROLES, WALL_MIN_BURIED_MM, resolve_params
from app.engine.measure.dpc import _on_dpc
from app.engine.measure.spatial import prism_and_polygon
from app.engine.measure.units import q4, q6

PARAM = "wall_foundation_works"
MEMBRANE_PARAM = "wall_membrane"
RECIPE = "WALL_FOUNDATION_WORKS"
FORMULA_VOLUME = "WALL_FOUNDATION_VOLUME"
FORMULA_AREA = "WALL_FOUNDATION_AREA"
CODE_BRICK, CODE_TERMITE, CODE_MEMBRANE = "MAS-BRICK", "PRO-TERMITE", "FIN-WATERPROOF-DPC"
BRICK_STEP, TERMITE_TRENCH, MEMBRANE = "BRICK_STEP", "TERMITE_TRENCH", "MEMBRANE"
ITEM_CODES = {BRICK_STEP: CODE_BRICK, TERMITE_TRENCH: CODE_TERMITE, MEMBRANE: CODE_MEMBRANE}
STEPS_PROPOSED = "WALL_WORKS_STEPS_PROPOSED"
THIN_WALL_MAX_MM = 150.0
MM3_PER_M3 = Decimal("1000000000")
MM2_PER_M2 = Decimal("1000000")
CODES = (STEPS_PROPOSED,)

@dataclass(frozen=True)
class WallWorksResult:
  solids: list = field(default_factory=list)
  ledger: list = field(default_factory=list)
  stats: dict = field(default_factory=dict)

def strip_class(thickness_mm: float) -> str:
  return "THIN" if thickness_mm < THIN_WALL_MAX_MM else "THICK"

def _short_side(poly) -> float:
  try:
    rect = poly.minimum_rotated_rectangle
    pts = list(rect.exterior.coords)
    sides = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(2)]
    return min(sides)
  except (AttributeError, IndexError, ValueError):
    return 0.0

def wall_run(el, poly) -> tuple[float, float]:
  t = float(el.thickness_mm) if getattr(el, "thickness_mm", None) else _short_side(poly)
  if t <= 0 or poly.area <= 0:
    return 0.0, 0.0
  return poly.area / t, t

def steps_of(cls: str, thickness_mm: float) -> list:
  heights = QP.BRICK_STEP_HEIGHTS_MM[cls]
  n = len(heights)
  offset = QP.BRICK_STEP_OFFSET_MM
  return [{"step_no": i, "height_mm": h, "width_mm": round(thickness_mm + (n - i) * offset, 1)} for i, h in enumerate(heights, start=1)]

def _m3(mm3: float) -> Decimal:
  return q6(Decimal(repr(float(mm3))) / MM3_PER_M3)

def _m2(mm2: float) -> Decimal:
  return q6(Decimal(repr(float(mm2))) / MM2_PER_M2)

def _taken(ledger: list, extra_ledger) -> tuple[set, bool]:
  codes = {r.work_item_code for r in ledger if r.source_kind == "MODEL" and r.quantity > 0}
  pdf = [r for r in (extra_ledger or ()) if getattr(r, "source_kind", None) == PDF_SOURCE and r.quantity > 0]
  codes |= {r.work_item_code for r in pdf}
  steps = any(str(((r.trace or {}).get("inputs") or {}).get("tag") or "").upper().startswith("BRICK-STEP") for r in pdf)
  return codes, steps

def _row(ctx, el, solid_of_el: Solid, item: str, quantity: Decimal, unit: str, formula: str, params: dict, level, steps: list, detail: dict, used: tuple) -> tuple:
  assumed = [n for n in used if params[n]["source"] == "default"]
  warnings = [STEPS_PROPOSED] + ([CODE_ASSUMED] if assumed else [])
  base = solid_of_el.classification_confidence * solid_of_el.confidence_factor
  confidence = max(Decimal("0"), min(Decimal("1"), q4(base * FACTOR_ASSUMED)))
  
  spec = {"kind": DERIVED, "recipe": RECIPE, "item": item, "strip_class": detail["strip_class"],
    "params": {n: params[n]["value"] for n in used}, "basis": {**{n: params[n]["source"] for n in used}, "steps": "workbook"}}
  solid = Solid(id=uuid5(ctx.run_id, f"solid|wallfnd|{el.id}|{item}"), element_id=el.id, ifc_type=el.ifc_type, role=el.role, level_id=el.level_id,
    geometry_kind="QTO_ONLY", classification_confidence=solid_of_el.classification_confidence, confidence_factor=solid_of_el.confidence_factor * FACTOR_ASSUMED,
    component_type=f"DERIVED_{item}", gross_volume_m3=quantity if unit == "m3" else None, gross_area_m2=quantity if unit == "m2" else None, status="REVIEW_REQUIRED")
  row = LedgerEntry(solid_id=solid.id, element_id=el.id, level_id=el.level_id, work_item_code=ITEM_CODES[item], quantity=quantity, unit=unit, material_grade=None,
    confidence=confidence, formula_code=formula,
    trace={"formula_code": formula, "engine_version": ctx.engine_version, "convention": ctx.convention_code,
      "rule_set": {"code": ctx.rule_set_code, "version": ctx.rule_set_version},
      
      "inputs": {"recipe": RECIPE, "spec": spec, "source_element_id": str(el.id), "dpc": {"z_mm": round(level.z_mm, 1), "source": level.source}, **detail},
      "steps": steps, "net": {unit: str(quantity)}, "rounding": "half_up,6dp"},
    warnings=tuple(dict.fromkeys(warnings)), source_kind=DERIVED, spec=spec, spec_key="derived")
  return solid, row

def measure_wall_foundation(ctx: CalculationContext, profile, elements: list, solids: list, ledger: list, extra_ledger=()) -> WallWorksResult:
  params = resolve_params(ctx)
  on = params[PARAM]["value"] >= 0.5
  stats: dict = {"enabled": on, "ran": False, "param_source": params[PARAM]["source"]}
  
  if not on:
    stats["reason"] = "SWITCHED_OFF"
    return WallWorksResult(stats=stats)
  if profile is None:
    stats["reason"] = "NO_PROFILE"
    return WallWorksResult(stats=stats)
  if not any((el.role or "").upper() in WALL_BED_ROLES for el in elements):
    stats["reason"] = "NO_WALLS"
    return WallWorksResult(stats=stats)
  level = S.dpc_datum(ctx, elements)
  if level is None:
    stats["reason"] = "NO_DPC_LEVEL"
    return WallWorksResult(stats=stats)

  taken, steps_in_pdf = _taken(ledger, extra_ledger)
  membrane_on = params[MEMBRANE_PARAM]["value"] >= 0.5
  wanted = {BRICK_STEP: not steps_in_pdf, TERMITE_TRENCH: CODE_TERMITE not in taken, MEMBRANE: membrane_on and CODE_MEMBRANE not in taken}
  stats["skipped"] = {item: why for item, why in (
    (BRICK_STEP, "PDF_HAS_STEPS" if steps_in_pdf else None),
    (TERMITE_TRENCH, "ALREADY_MEASURED" if CODE_TERMITE in taken else None),
    (MEMBRANE, "SWITCHED_OFF" if not membrane_on else ("ALREADY_MEASURED" if CODE_MEMBRANE in taken else None))) if why}
  if not any(wanted.values()):
    stats["reason"] = "ALL_ITEMS_ALREADY_MEASURED"
    return WallWorksResult(stats=stats)

  solid_of = {s.element_id: s for s in solids if s.element_id is not None and s.component_type == "BODY"}
  measured = {r.element_id for r in ledger if r.source_kind == "MODEL" and r.quantity > 0}
  projection = params["pcc_projection_mm"]["value"]
  out_solids, out_rows = [], []
  walls = already_down = no_footprint = 0
  length_total = 0.0
  totals = {BRICK_STEP: Decimal("0"), TERMITE_TRENCH: Decimal("0"), MEMBRANE: Decimal("0")}
  
  by_class: dict = {}
  for el in sorted(elements, key=lambda e: str(e.id)):
    role = (el.role or "").upper()
    if role not in WALL_BED_ROLES or el.id not in measured or el.material_class == "CONCRETE":
      continue
  
    solid = solid_of.get(el.id)
    found = prism_and_polygon(el)
    if solid is None or found is None:
      no_footprint += 1
      continue
  
    prism, poly = found
    if not _on_dpc(prism.z0, prism.z1, level.z_mm):
      continue
    if role == "WALL_FOUNDATION" or prism.z0 < level.z_mm - WALL_MIN_BURIED_MM:
      already_down += 1
      continue
    length, thickness = wall_run(el, poly)
    if length <= 0:
      no_footprint += 1
      continue
  
    cls = strip_class(thickness)
    steps = steps_of(cls, thickness)
    walls += 1
    length_total += length
    slot = by_class.setdefault(cls, {"walls": 0, "length_m": 0.0})
    slot["walls"] += 1
    slot["length_m"] += length / 1000.0
    detail = {"strip_class": cls, "wall_length_mm": round(length, 1), "wall_thickness_mm": round(thickness, 1), "steps_source": "QS workbook"}

    if wanted[BRICK_STEP]:
      parts = [{"op": "step", "step_no": s["step_no"], "height_mm": s["height_mm"], "width_mm": s["width_mm"],
        "m3": str(_m3(length * s["width_mm"] * s["height_mm"]))} for s in steps]
      qty = q6(sum((Decimal(p["m3"]) for p in parts), Decimal("0")))
      if qty > 0:
        s_, r_ = _row(ctx, el, solid, BRICK_STEP, qty, "m3", FORMULA_VOLUME, params, level, [*parts, {"op": "net_volume", "m3": str(qty)}],
          {**detail, "offset_mm": QP.BRICK_STEP_OFFSET_MM, "steps": steps}, ())
        out_solids.append(s_)
        out_rows.append(r_)
        totals[BRICK_STEP] += qty
        
    if wanted[TERMITE_TRENCH]:
      bed = steps[0]["width_mm"] + 2.0 * projection
      qty = _m2(length * bed)
      if qty > 0:
        s_, r_ = _row(ctx, el, solid, TERMITE_TRENCH, qty, "m2", FORMULA_AREA, params, level,
          [{"op": "trench_bottom", "length_mm": round(length, 1), "width_mm": round(bed, 1), "m2": str(qty)}, {"op": "net_area", "m2": str(qty)}],
          {**detail, "bed_width_mm": round(bed, 1)}, ("pcc_projection_mm",))
        out_solids.append(s_)
        out_rows.append(r_)
        totals[TERMITE_TRENCH] += qty
        
    if wanted[MEMBRANE]:
      qty = _m2(poly.area)
      if qty > 0:
        s_, r_ = _row(ctx, el, solid, MEMBRANE, qty, "m2", FORMULA_AREA, params, level,
          [{"op": "plinth_plan_area", "m2": str(qty)}, {"op": "net_area", "m2": str(qty)}], detail, ())
        out_solids.append(s_)
        out_rows.append(r_)
        totals[MEMBRANE] += qty

  out_rows.sort(key=lambda r: (r.work_item_code, str(r.level_id), str(r.element_id)))
  stats.update({"ran": bool(out_rows), "rows": len(out_rows), "walls": walls, "left_alone_going_below_dpc": already_down, "no_footprint": no_footprint,
    "length_m": str(q6(Decimal(repr(length_total / 1000.0)))), "brick_steps_m3": str(q6(totals[BRICK_STEP])), "termite_trench_m2": str(q6(totals[TERMITE_TRENCH])),
    "membrane_m2": str(q6(totals[MEMBRANE])), "classes": {k: {"walls": v["walls"], "length_m": round(v["length_m"], 3)} for k, v in sorted(by_class.items())},
    "level": {"z_mm": round(level.z_mm, 1), "source": level.source}, "step_offset_mm": QP.BRICK_STEP_OFFSET_MM,
    "step_heights_mm": {k: list(v) for k, v in QP.BRICK_STEP_HEIGHTS_MM.items()}, "pcc_projection_mm": projection})
  
  if not out_rows:
    stats["reason"] = "NO_WALL_ON_DPC" if walls == 0 else "NOTHING_TO_MEASURE"
  return WallWorksResult(solids=out_solids, ledger=out_rows, stats=stats)

def wall_works_check(solids: list, ledger: list) -> list:
  ids = {s.id for s in solids}
  out = []
  
  for r in ledger:
    if r.formula_code not in (FORMULA_VOLUME, FORMULA_AREA):
      continue
  
    if r.solid_id not in ids:
      out.append(f"{r.work_item_code}: wall works row has no solid")
    want = "m3" if r.formula_code == FORMULA_VOLUME else "m2"
    if r.unit != want or r.quantity <= 0:
      out.append(f"{r.work_item_code}: wall works quantity {r.quantity} {r.unit}")
    if r.source_kind != DERIVED:
      out.append(f"{r.work_item_code}: wall works row is not a derived row")
  return out
