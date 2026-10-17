from __future__ import annotations
from decimal import Decimal
from dataclasses import dataclass, field
from app.engine.measure.units import q6, q4
from app.engine.measure.models import Solid, LedgerEntry, CalculationContext
from app.engine.measure.derived import CODE_ASSUMED, DERIVED, FACTOR_ASSUMED, FACTOR_CONFIRMED, WALL_BED_ROLES, resolve_params
import math
from uuid import uuid5
from app.engine.measure import pdf_space as PS
from app.engine.measure import stages as S
from app.engine.measure.spatial import prism_and_polygon
from app.engine.measure.takeoff import SOURCE_KIND as PDF_SOURCE

DPC_FORMULA = "DPC_AREA"
DPC_CODE = "MAS-DPC"
RECIPE_CODE = "DPC_LAYER"
PARAMS_USED = ("dpc_thickness_mm", "dpc_door_deduction")
LEVEL_TOL_MM = 10.0
MM2_PER_M2 = Decimal("1000000")

CODE_LEVEL_ASSUMED = "DPC_LEVEL_ASSUMED"
CODE_DOOR_NOT_TAKEN = "DPC_DOOR_NOT_DEDUCTED"
DPC_CODES = (CODE_LEVEL_ASSUMED, CODE_DOOR_NOT_TAKEN)

@dataclass(frozen=True)
class DpcResult:
  solids: list = field(default_factory=list)
  ledger: list = field(default_factory=list)
  stats: dict = field(default_factory=dict)

def _m2(mm2: float) -> Decimal:
  return q6(Decimal(repr(float(mm2))) / MM2_PER_M2)

def _on_dpc(z0: float, z1: float, level: float) -> bool:
  return z0 <= level + LEVEL_TOL_MM and z1 > level + LEVEL_TOL_MM

def _row(ctx, solid: Solid, element_id, level_id, code: str, quantity: Decimal, params: dict, level: S.Datum, base: Decimal, steps: list,
  source: dict, extra_warnings: tuple = ()) -> LedgerEntry:
  assumed = [n for n in PARAMS_USED if params[n]["source"] == "default"]
  warnings = list(extra_warnings)
  if assumed:
    warnings.append(CODE_ASSUMED)
  if level.source == "default":
    warnings.append(CODE_LEVEL_ASSUMED)
  factor = FACTOR_ASSUMED if (assumed or level.source == "default") else FACTOR_CONFIRMED
  confidence = max(Decimal("0"), min(Decimal("1"), q4(base * factor)))
  spec = {"kind": DERIVED, "recipe": RECIPE_CODE, "item": "DPC", "dpc_z_mm": round(level.z_mm, 1),
    "params": {n: params[n]["value"] for n in PARAMS_USED}, "basis": {**{n: params[n]["source"] for n in PARAMS_USED}, "dpc_level": level.source}}
  
  return LedgerEntry(
    solid_id=solid.id, element_id=element_id, level_id=level_id, work_item_code=code, quantity=quantity, unit="m2", material_grade=None,
    confidence=confidence, formula_code=DPC_FORMULA,
    trace={"formula_code": DPC_FORMULA, "engine_version": ctx.engine_version, "convention": ctx.convention_code,
      "rule_set": {"code": ctx.rule_set_code, "version": ctx.rule_set_version},
      "inputs": {"recipe": RECIPE_CODE, "spec": spec, "dpc": {"z_mm": round(level.z_mm, 1), "source": level.source, "note": level.note}, **source},
      "steps": steps, "net": {"m2": str(quantity)}, "rounding": "half_up,6dp"},
    warnings=tuple(dict.fromkeys(warnings)), source_kind=DERIVED, spec=spec, spec_key="derived")

def _model_walls(ctx, elements: list, solids: list, ledger: list, code: str, params: dict, stats: dict) -> tuple:
  if not any((el.role or "").upper() in WALL_BED_ROLES for el in elements):
    return [], []
  level = S.dpc_datum(ctx, elements)
  if level is None:
    stats["model"] = {"reason": "NO_DPC_LEVEL"}
    return [], []
  solid_of = {s.element_id: s for s in solids if s.element_id is not None and s.component_type == "BODY"}
  measured = {r.element_id for r in ledger if r.source_kind == "MODEL" and r.quantity > 0}
  doors = []
  
  for el in elements:
    if (el.role or "").upper() != "DOOR":
      continue
    z, found = S.element_z(el), prism_and_polygon(el)
    if z is not None and z[0] <= level.z_mm + LEVEL_TOL_MM and z[1] > level.z_mm:
      doors.append((el, found[1] if found is not None else None))
  deduct = params["dpc_door_deduction"]["value"] >= 0.5
  out_solids, out_rows = [], []
  walls = taken = no_footprint = door_no_plan = 0
  gross_total = net_total = Decimal("0")
  for el in sorted(elements, key=lambda e: str(e.id)):
    if (el.role or "").upper() not in WALL_BED_ROLES or el.id not in measured or el.material_class == "CONCRETE":
      continue
  
    solid = solid_of.get(el.id)
    found = prism_and_polygon(el)
    if solid is None or found is None:
      no_footprint += 1
      continue
    prism, poly = found
    if not _on_dpc(prism.z0, prism.z1, level.z_mm):
      continue
  
    walls += 1
    gross = poly.area
    cut = 0.0
    cuts = []
    missing = False
    if deduct:
      for door, door_poly in doors:
        if door_poly is None:
          missing = True
          continue
      
        a = poly.intersection(door_poly).area
        if a > 0:
          cut += a
          cuts.append({"door_element_id": str(door.id), "m2": str(_m2(a))})
    if missing:
      door_no_plan += 1
    net = max(0.0, gross - min(cut, gross))
    quantity = _m2(net)
    if quantity <= 0:
      continue
  
    steps = [{"op": "wall_plan_area", "m2": str(_m2(gross)), "at_mm": round(level.z_mm, 1)}]
    steps += [{"op": "less_door", **c} for c in cuts]
    steps.append({"op": "net_area", "m2": str(quantity)})
    s = Solid(id=uuid5(ctx.run_id, f"solid|dpc|{el.id}"), element_id=el.id, ifc_type=el.ifc_type, role=el.role, level_id=el.level_id, geometry_kind="QTO_ONLY",
      classification_confidence=solid.classification_confidence, confidence_factor=solid.confidence_factor, component_type="DERIVED_DPC",
      gross_area_m2=quantity, status="OK")
    out_solids.append(s)
    out_rows.append(_row(ctx, s, el.id, el.level_id, code, quantity, params, level, solid.classification_confidence * solid.confidence_factor, steps,
      {"source_element_id": str(el.id)}, (CODE_DOOR_NOT_TAKEN,) if (missing and deduct) else ()))
    
    taken += len(cuts)
    gross_total += _m2(gross)
    net_total += quantity
  stats["model"] = {"walls": walls, "doors_taken_out": taken, "no_footprint": no_footprint, "doors_without_plan": door_no_plan,
    "gross_m2": str(q6(gross_total)), "net_m2": str(q6(net_total)), "level": {"z_mm": round(level.z_mm, 1), "source": level.source}}
  return out_solids, out_rows

def _runs_length(parts) -> float:
  return sum(math.hypot(float(p[2]) - float(p[0]), float(p[3]) - float(p[1])) for p in parts)

def _pdf_walls(ctx, extra_ledger: list, code: str, params: dict, stats: dict) -> tuple:
  takeoff = getattr(ctx, "takeoff", None)
  members = tuple(getattr(takeoff, "space", ()) or ())
  walls = [m for m in members if m.category == "WALL" and m.shape == "STRIP" and m.parts]
  if not walls:
    return [], []

  rows = PS._counted_rows(extra_ledger)
  floors_by_group: dict = {}
  for f in getattr(takeoff, "floors", ()) or ():
    floors_by_group.setdefault(f.group, []).append(f)
  levels = {g: PS.dpc_datum(ctx, floors_by_group.get(g, [])) for g in sorted({m.group for m in walls})}
  by_id = {str(m.id): m for m in getattr(takeoff, "measurements", ()) or ()}
  deduct = params["dpc_door_deduction"]["value"] >= 0.5
  out_solids, out_rows = [], []
  used = no_level = no_height = 0
  doors_taken = 0
  net_total = Decimal("0")
  
  for m in sorted(walls, key=lambda w: str(w.measurement_id)):
    mid = str(m.measurement_id)
    level = levels.get(m.group)
    if mid not in rows:
      continue
    if level is None:
      no_level += 1
      continue
    if m.z0_mm is None or m.z1_mm is None or float(m.z1_mm) <= float(m.z0_mm):
      no_height += 1
      continue
  
    if not _on_dpc(float(m.z0_mm), float(m.z1_mm), level.z_mm):
      continue
    meas = by_id.get(mid)
    mp = (meas.params if meas is not None else None) or {}
    try:
      repeat = max(1, int(mp.get("repeat") or 1))
    except (TypeError, ValueError):
      repeat = 1
    thickness = float(m.width_mm)
    gross = _runs_length(m.parts) * thickness * repeat
    
    cuts = []
    if deduct:
      for o in mp.get("openings") or []:
        if str(o.get("role") or "").upper() != "DOOR":
          continue
        try:
          width, nos = float(o.get("width_mm")), int(o.get("nos", 1))
        except (TypeError, ValueError):
          continue
        if width > 0 and nos > 0:
          cuts.append({"label": o.get("label") or f"door {int(width)} mm x {nos}", "m2": str(_m2(width * thickness * nos * repeat))})
    cut = sum((Decimal(c["m2"]) for c in cuts), Decimal("0"))
    quantity = max(Decimal("0"), q6(_m2(gross) - cut))
    if quantity <= 0:
      continue
  
    solid = Solid(id=uuid5(ctx.run_id, f"solid|dpc|{mid}"), element_id=None, ifc_type="PdfMeasurement", role="WALL", level_id=m.level_id, geometry_kind="QTO_ONLY",
      classification_confidence=Decimal("1"), confidence_factor=Decimal("1"), component_type="DERIVED_DPC", gross_area_m2=quantity, status="OK")
    steps = [{"op": "wall_plan_area", "m2": str(_m2(gross)), "at_mm": round(level.z_mm, 1), "thickness_mm": thickness, **({"repeat": repeat} if repeat > 1 else {})}]
    steps += [{"op": "less_door", **c} for c in cuts]
    steps.append({"op": "net_area", "m2": str(quantity)})
    out_solids.append(solid)
    out_rows.append(_row(ctx, solid, None, m.level_id, code, quantity, params, level, Decimal("0.95"), steps,
      {"measurement_id": mid, "candidate_id": str(m.candidate_id), "sheet_id": str(m.sheet_id), "page_no": m.page_no, "tag": m.tag}))
    used += 1
    
    doors_taken += len(cuts)
    net_total += quantity
  stats["pdf"] = {"walls": used, "doors_taken_out": doors_taken, "no_level": no_level, "no_height": no_height, "net_m2": str(q6(net_total)),
    "levels": {g: ({"z_mm": round(d.z_mm, 1), "source": d.source} if d is not None else None) for g, d in levels.items()}}
  return out_solids, out_rows

def measure_dpc(ctx: CalculationContext, profile, elements: list, solids: list, ledger: list, extra_ledger=()) -> DpcResult:
  stats: dict = {"enabled": True, "ran": False, "vertical": "NOT_TAKEN"}
  if profile is None:
    stats["reason"] = "NO_PROFILE"
    return DpcResult(stats=stats)
  taken = {r.work_item_code for r in ledger if r.source_kind == "MODEL" and r.quantity > 0}
  taken |= {r.work_item_code for r in (extra_ledger or ()) if getattr(r, "source_kind", None) == PDF_SOURCE and r.quantity > 0}
  if DPC_CODE in taken:
    stats["reason"] = "ALL_ITEMS_IN_MODEL"
    return DpcResult(stats=stats)
  params = resolve_params(ctx)
  
  stats["params"] = {n: dict(params[n]) for n in PARAMS_USED}
  model_solids, model_rows = _model_walls(ctx, elements, solids, ledger, DPC_CODE, params, stats)
  pdf_solids, pdf_rows = _pdf_walls(ctx, extra_ledger, DPC_CODE, params, stats) if not model_rows else ([], [])
  rows = [*model_rows, *pdf_rows]
  
  rows.sort(key=lambda r: (str(r.level_id), str(r.element_id), str(r.solid_id)))
  total = sum((r.quantity for r in rows), Decimal("0"))
  stats.update({"ran": bool(rows), "rows": len(rows), "area_m2": str(q6(total))})
  if not rows:
    no_level = (stats.get("model") or {}).get("reason") == "NO_DPC_LEVEL" or bool((stats.get("pdf") or {}).get("no_level"))
    stats["reason"] = "NO_DPC_LEVEL" if no_level else "NO_WALL_ON_DPC"
  return DpcResult(solids=[*model_solids, *pdf_solids], ledger=rows, stats=stats)
