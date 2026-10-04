from __future__ import annotations
from decimal import Decimal
from app.engine.measure.models import Solid, Deduction, CalculationContext, AllocationResult, LedgerEntry
from dataclasses import dataclass, field, replace
from shapely.geometry import Point, Polygon
from app.engine.measure.units import q4, q6
from uuid import uuid5

MM2_PER_M2 = Decimal("1000000")
MM_PER_M = Decimal("1000")
ZERO, ONE = Decimal("0"), Decimal("1")
RULE_DEFAULT_CONFIDENCE = Decimal("0.7")
GEOMETRY_CONFIDENCE = {"EXTRUDED_PROFILE": ONE, "QTO_ONLY": Decimal("0.9")}
SURFACE_ORDER = {"FLOOR": 0, "SKIRTING": 1, "WALL": 2, "DADO": 3, "CEILING": 4}
FINISH_FORMULAS = {
  "FLOOR": ("FINISH_FLOOR_AREA", "m2"),
  "CEILING": ("FINISH_CEILING_AREA", "m2"),
  "WALL": ("FINISH_WALL_AREA_NET", "m2"),
  "DADO": ("FINISH_DADO_AREA_NET", "m2"),
  "SKIRTING": ("FINISH_SKIRTING_LENGTH_NET", "m"),
}

SCHEDULE_UNITS = ("m3", "m2", "m", "kg", "nos")
PHASE6_FORMULA_UNITS = {
  **{code: unit for code, unit in FINISH_FORMULAS.values()},
  **{f"SCHEDULE_LINE_{u.upper()}": u for u in SCHEDULE_UNITS},
}

@dataclass(frozen=True)
class OpeningsResult:
  deductions: list = field(default_factory=list)
  solid_warnings: dict = field(default_factory=dict)
  checked: frozenset = frozenset()
  stats: dict = field(default_factory=dict)

@dataclass(frozen=True)
class FinishResult:
  solids: list
  ledger: list
  skipped: dict

@dataclass(frozen=True)
class _Finish:
  surface: str
  work_item_code: str
  height_mm: Decimal | None
  deduct_openings: bool
  source: str
  confidence: Decimal
  review: str

@dataclass
class _Calc:
  gross: Decimal
  net: Decimal
  unit: str
  formula: str
  steps: list
  warnings: list
  inputs: dict

def _void(host: Solid, o, quantity: Decimal, rule: str, explanation: str, extra: dict) -> Deduction:
  return Deduction(
    from_solid_id=host.id, to_solid_id=None, deduction_type="VOID_DEDUCTION", quantity=quantity, unit="m3",
    rule_code=rule, explanation=explanation,
    geometry={"opening_element_id": str(o.element_id), "role": o.role, **extra},
  )

DEDUCTIBLE_KINDS = ("EXTRUDED_PROFILE", "AXIS_SWEPT")

def apply_openings(ctx: CalculationContext, profile, solids: list[Solid], openings) -> OpeningsResult:
  walls = {s.element_id: s for s in solids if s.role.startswith("WALL") and s.gross_volume_m3 is not None}
  deductions: list = []
  warnings: dict = {}
  stats = {"hosted": 0, "deducted": 0, "ignored": 0, "size_missing": 0, "unhosted": 0, "qto_walls_skipped": 0}
  for o in sorted(openings, key=lambda o: str(o.element_id)):
    host = walls.get(o.host_element_id)
    if host is None:
      stats["unhosted"] += 1
      continue
    stats["hosted"] += 1
    
    if host.geometry_kind not in DEDUCTIBLE_KINDS:
      stats["qto_walls_skipped"] += 1
      continue
  
    w, h, t = o.width_mm, o.height_mm, o.host_thickness_mm
    if not w or not h or not t or w <= 0 or h <= 0 or t <= 0:
      stats["size_missing"] += 1
      warnings.setdefault(host.id, set()).add("OPENING_SIZE_MISSING")
      deductions.append(_void(host, o, ZERO, "OPENING_SIZE_MISSING",
        f"{o.role.title()} has no usable width, height or host thickness; not deducted.", {}))
      continue
  
    area_m2 = (w * h) / MM2_PER_M2
    behavior, fraction = profile.opening_behavior(o.role, area_m2)
    if behavior == "IGNORE":
      stats["ignored"] += 1
      deductions.append(_void(host, o, ZERO, "OPENING_IGNORED",
        f"{o.role.title()} {int(w)}x{int(h)} mm is below the deduction threshold; not deducted.",
        {"behavior": behavior, "area_m2": str(q6(area_m2))}))
      continue
  
    stats["deducted"] += 1
    volume = q6(area_m2 * (t / MM_PER_M) * fraction)
    deductions.append(_void(host, o, volume, "OPENING_PARTIAL" if behavior == "PARTIAL" else "OPENING_DEDUCT",
      f"{o.role.title()} {int(w)}x{int(h)} mm x {int(t)} mm wall, {behavior.lower()} deduction.",
      {"behavior": behavior, "fraction": str(fraction), "area_m2": str(q6(area_m2)),
       "width_mm": str(w), "height_mm": str(h), "thickness_mm": str(t)}))
  relations_exist = stats["hosted"] > 0 or not openings
  checked = frozenset(s.id for s in walls.values() if s.geometry_kind in DEDUCTIBLE_KINDS) if relations_exist else frozenset()
  return OpeningsResult(deductions=deductions, checked=checked, stats=stats,
    solid_warnings={k: tuple(sorted(v)) for k, v in warnings.items()})

def merge_openings(alloc: AllocationResult, res: OpeningsResult) -> AllocationResult:
  warn = {k: set(v) for k, v in alloc.solid_warnings.items()}
  for k, v in res.solid_warnings.items():
    warn.setdefault(k, set()).update(v)
  deds = sorted([*alloc.deductions, *res.deductions],
    key=lambda d: (str(d.from_solid_id), str(d.to_solid_id), d.deduction_type, d.geometry.get("opening_element_id", "")))
  return replace(alloc, deductions=deds, openings_checked=res.checked,
    solid_warnings={k: tuple(sorted(v)) for k, v in warn.items()}, stats={**alloc.stats, "openings": res.stats})

def resolve_finishes(space, rules) -> list[_Finish]:
  explicit: dict = {}
  for f in space.finishes:
    explicit.setdefault(f.surface, []).append(f)
  out = [_Finish(f.surface, f.work_item_code, f.height_mm, True, f.source, f.confidence, f.review_status)
    for rows in explicit.values() for f in rows]
  chosen: dict = {}
  for r in rules:
    if r.surface in explicit or r.space_category not in (space.category, "ALL"):
      continue
    key = (r.surface, r.work_item_code)
    cur = chosen.get(key)
    if cur is None or (cur.space_category == "ALL" and r.space_category != "ALL"):
      chosen[key] = r
  for r in chosen.values():
    if not r.exclude:
      out.append(_Finish(r.surface, r.work_item_code, r.height_mm, r.deduct_openings, "RULE_DEFAULT",
        RULE_DEFAULT_CONFIDENCE, "OK"))
  out.sort(key=lambda f: (SURFACE_ORDER.get(f.surface, 9), f.work_item_code))
  return out

def _assign_openings(space, by_id: dict, by_host: dict):
  polygon = None
  if space.footprint and len(space.footprint) >= 3:
    polygon = Polygon(space.footprint)
    if not polygon.is_valid:
      polygon = polygon.buffer(0)
  assigned: dict = {}
  approximate = False
  for eid in space.boundary_element_ids:
    cands = []
    if eid in by_id:
      cands.append((by_id[eid], True))
    cands.extend((o, False) for o in by_host.get(eid, ()))
    for o, direct in cands:
      if o.element_id in assigned:
        continue
      if o.level_id and space.level_id and o.level_id != space.level_id:
        continue
      if not direct:
        if polygon is not None and o.centre_mm is not None:
          if polygon.distance(Point(o.centre_mm)) > float(o.host_thickness_mm or 230) + 100.0:
            continue
        else:
          approximate = True
      assigned[o.element_id] = o
      
  if not space.boundary_element_ids and polygon is not None:
    for o in by_id.values():
      if o.element_id in assigned or o.centre_mm is None:
        continue
      if o.level_id and space.level_id and o.level_id != space.level_id:
        continue
      if polygon.distance(Point(o.centre_mm)) <= float(o.host_thickness_mm or 230) + 100.0:
        assigned[o.element_id] = o
        approximate = True
  return sorted(assigned.values(), key=lambda o: str(o.element_id)), approximate

def _perimeter_mm(space) -> Decimal | None:
  if space.perimeter_mm and space.perimeter_mm > 0:
    return space.perimeter_mm
  pts = space.footprint
  if pts and len(pts) >= 3:
    total = sum(((pts[i][0] - pts[(i + 1) % len(pts)][0]) ** 2 + (pts[i][1] - pts[(i + 1) % len(pts)][1]) ** 2) ** 0.5
      for i in range(len(pts)))
    return Decimal(str(round(total, 3)))
  return None

def _calculate(space, f: _Finish, openings: list, profile):
  formula, unit = FINISH_FORMULAS[f.surface]
  steps: list = []
  warnings: list = []
  inputs: dict = {"surface": f.surface}
  if f.surface in ("FLOOR", "CEILING"):
    area = space.net_floor_area_mm2 or space.gross_floor_area_mm2
    if not area or area <= 0:
      return "space has no floor area"
    gross = area / MM2_PER_M2
    net = gross
    steps.append({"op": "gross_area", "m2": str(q6(gross))})
    return _Calc(gross, net, unit, formula, steps, warnings, inputs)

  perimeter = _perimeter_mm(space)
  if perimeter is None:
    return "space has no perimeter"
  inputs["perimeter_mm"] = str(perimeter)

  if f.surface == "SKIRTING":
    gross = perimeter / MM_PER_M
    net = gross
    steps.append({"op": "gross_length", "m": str(q6(gross))})
    if f.deduct_openings:
      for o in openings:
        if o.role != "DOOR":
          continue
        if not o.width_mm:
          warnings.append("OPENING_SIZE_MISSING")
          continue
        cut = o.width_mm / MM_PER_M
        net -= cut
        steps.append({"op": "deduction", "type": "VOID_DEDUCTION", "m": str(q6(cut)), "note": f"Door {int(o.width_mm)} mm"})
    return _Calc(gross, net, unit, formula, steps, warnings, inputs)

  height = f.height_mm or (space.height_mm if f.surface == "WALL" else None)
  if not height or height <= 0:
    return "no finish height"
  inputs["height_mm"] = str(height)
  gross = perimeter * height / MM2_PER_M2
  net = gross
  steps.append({"op": "gross_area", "m2": str(q6(gross))})
  if f.deduct_openings:
    for o in openings:
      if not o.width_mm or not o.height_mm:
        warnings.append("OPENING_SIZE_MISSING")
        continue
      if f.surface == "WALL":
        area = o.width_mm * o.height_mm / MM2_PER_M2
        behavior, fraction = profile.opening_behavior(o.role, area)
        cut = ZERO if behavior == "IGNORE" else area * fraction
      else:
        if o.role != "DOOR":
          continue
        cut = o.width_mm * min(o.height_mm, height) / MM2_PER_M2
      if cut > 0:
        net -= cut
        steps.append({"op": "deduction", "type": "VOID_DEDUCTION", "m2": str(q6(cut)),
          "note": f"{o.role.title()} {int(o.width_mm)}x{int(o.height_mm)} mm"})
  return _Calc(gross, net, unit, formula, steps, warnings, inputs)

def measure_finishes(ctx: CalculationContext, profile, spaces, openings) -> FinishResult:
  by_id = {o.element_id: o for o in openings}
  by_host: dict = {}
  for o in openings:
    if o.host_element_id:
      by_host.setdefault(o.host_element_id, []).append(o)
  solids: list = []
  ledger: list = []
  skipped: dict = {}
  
  for space in sorted(spaces, key=lambda s: str(s.id)):
    finishes = resolve_finishes(space, profile.finish_rules)
    if not finishes:
      continue
    assigned, approximate = _assign_openings(space, by_id, by_host)
    for f in finishes:
      calc = _calculate(space, f, assigned, profile)
      if isinstance(calc, str):
        skipped[calc] = skipped.get(calc, 0) + 1
        continue
      quantity = q6(max(ZERO, calc.net))
      if quantity <= 0:
        skipped["zero quantity"] = skipped.get("zero quantity", 0) + 1
        continue
    
      warnings = list(calc.warnings)
      if approximate and f.deduct_openings and f.surface in ("WALL", "DADO", "SKIRTING"):
        warnings.append("OPENING_ASSIGNMENT_APPROXIMATE")
      if f.review == "REVIEW_REQUIRED":
        warnings.append("FINISH_NEEDS_REVIEW")
        
      factor = GEOMETRY_CONFIDENCE.get(space.geometry_kind, Decimal("0.8"))
      confidence = max(ZERO, min(ONE, q4(f.confidence * factor)))
      solid_id = uuid5(ctx.run_id, f"solid|space:{space.id}|{f.surface}|{f.work_item_code}")
      solids.append(Solid(
        id=solid_id, element_id=None, ifc_type="IfcSpace", role="SPACE_FINISH", level_id=space.level_id,
        geometry_kind=space.geometry_kind, classification_confidence=ONE, confidence_factor=factor,
        component_type=f"FINISH_{f.surface}",
        gross_area_m2=q6(calc.gross) if calc.unit == "m2" else None,
        gross_length_m=q6(calc.gross) if calc.unit == "m" else None,
        status="REVIEW_REQUIRED" if warnings else "OK",
      ))
      
      label = f"{space.number or '-'} {space.name or space.category}".strip()
      ledger.append(LedgerEntry(
        solid_id=solid_id, element_id=None, level_id=space.level_id, work_item_code=f.work_item_code,
        quantity=quantity, unit=calc.unit, material_grade=None, confidence=confidence, formula_code=calc.formula,
        trace={
          "formula_code": calc.formula, "engine_version": ctx.engine_version, "convention": ctx.convention_code,
          "rule_set": {"code": ctx.rule_set_code, "version": ctx.rule_set_version},
          "inputs": {**calc.inputs, "space_id": str(space.id), "finish_source": f.source},
          "steps": calc.steps + [{"op": "net", calc.unit: str(quantity)}], "net": {calc.unit: str(quantity)},
          "label": label, "rounding": "half_up,6dp",
        },
        warnings=tuple(dict.fromkeys(warnings)),
        source_kind=f.source if f.source in ("SCHEDULE_IMPORT", "MANUAL") else "MODEL",
      ))
  ledger.sort(key=lambda r: (r.work_item_code, str(r.level_id), str(r.solid_id)))
  return FinishResult(solids=solids, ledger=ledger, skipped=dict(sorted(skipped.items())))

def schedule_lines_ledger(ctx: CalculationContext, lines) -> FinishResult:
  solids: list = []
  ledger: list = []
  for ln in sorted(lines, key=lambda l: (str(l.import_id), l.row_no)):
    if ln.unit not in SCHEDULE_UNITS:
      continue
    quantity = q6(ln.quantity)
    if quantity <= 0:
      continue
    solid_id = uuid5(ctx.run_id, f"solid|schedule:{ln.id}")
    solids.append(Solid(
      id=solid_id, element_id=None, ifc_type="ScheduleRow", role="SCHEDULE_LINE", level_id=ln.level_id,
      geometry_kind="QTO_ONLY", classification_confidence=ONE, confidence_factor=ONE, component_type="SCHEDULE",
      gross_volume_m3=quantity if ln.unit == "m3" else None,
      gross_area_m2=quantity if ln.unit == "m2" else None,
      gross_length_m=quantity if ln.unit == "m" else None,
      count=int(quantity.to_integral_value()) if ln.unit == "nos" else None,
    ))
    formula = f"SCHEDULE_LINE_{ln.unit.upper()}"
    ledger.append(LedgerEntry(
      solid_id=solid_id, element_id=None, level_id=ln.level_id, work_item_code=ln.work_item_code,
      quantity=quantity, unit=ln.unit, material_grade=None, confidence=max(ZERO, min(ONE, q4(ln.confidence))),
      formula_code=formula,
      
      trace={
        "formula_code": formula, "engine_version": ctx.engine_version, "convention": ctx.convention_code,
        "rule_set": {"code": ctx.rule_set_code, "version": ctx.rule_set_version},
        "inputs": {"schedule_import_id": str(ln.import_id), "row_no": ln.row_no, "mark": ln.mark,
          "kind": ln.schedule_kind, "raw_text": (ln.raw_text or "")[:300]},
        "steps": [{"op": "schedule_quantity", ln.unit: str(quantity)}], "net": {ln.unit: str(quantity)},
        "label": f"Schedule {ln.schedule_kind} row {ln.row_no} {ln.mark or ''}".strip(), "rounding": "half_up,6dp",
      },
      
      warnings=(), source_kind="SCHEDULE_IMPORT",
    ))
  ledger.sort(key=lambda r: (r.work_item_code, str(r.solid_id)))
  return FinishResult(solids=solids, ledger=ledger, skipped={})

def phase6_payload(spaces, openings, lines) -> dict:
  return {
    "spaces": [[str(s.id), str(s.level_id), s.category, s.is_external, str(s.net_floor_area_mm2),
      str(s.gross_floor_area_mm2), str(s.perimeter_mm), str(s.height_mm), s.footprint,
      sorted(str(b) for b in s.boundary_element_ids),
      sorted([f.surface, f.work_item_code, str(f.height_mm), f.source, str(f.confidence), f.review_status]
        for f in s.finishes)] for s in sorted(spaces, key=lambda s: str(s.id))],
    "openings": [[str(o.element_id), o.role, str(o.host_element_id), str(o.host_thickness_mm), str(o.width_mm),
      str(o.height_mm), str(o.level_id), o.centre_mm] for o in sorted(openings, key=lambda o: str(o.element_id))],
    "schedule": [[str(l.id), l.work_item_code, l.unit, str(l.quantity), str(l.confidence), str(l.level_id)]
      for l in sorted(lines, key=lambda l: str(l.id))],
  }