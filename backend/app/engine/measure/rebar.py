from __future__ import annotations
from decimal import Decimal
from app.engine.measure.models import BarSizeSpec, ShapeSpec, RebarRowInput, BarMark, RebarInputs, RebarResult
import math
from uuid import uuid5
from app.engine.measure.units import q4, q6
from app.engine.measure.models import LedgerEntry, Solid

ZERO, ONE = Decimal("0"), Decimal("1")

class RebarError(ValueError):
  """A bar mark that cannot be measured (missing dimension, no bend or hook rule, non-positive cut length). The mark is
  skipped with a warning instead of failing the run."""
  
REBAR_WORK_ITEM = "STL-REBAR"
FORMULA_BBS = "REBAR_BBS_WEIGHT"
FORMULA_ESTIMATE = "REBAR_RULE_ESTIMATE"
REBAR_FORMULA_UNITS = {FORMULA_BBS: "kg", FORMULA_ESTIMATE: "kg"}
KG_M_DIVISOR = Decimal("162.2")        
DEFAULT_ESTIMATE_DIA_MM = Decimal("12")
DEFAULT_ESTIMATE_CONFIDENCE = Decimal("0.5")
DEFAULT_TOLERANCE_PCT = Decimal("2.0")
SCHEDULE_CONFIDENCE_FLOOR = Decimal("0.6")
REVIEW_CODES = frozenset({"DECLARED_WEIGHT_MISMATCH", "LAP_LENGTH_UNKNOWN", "MATCHED_ELEMENT_NOT_MEASURED"})
_FAMILIES = (("COLUMN", "COLUMN"), ("BEAM", "BEAM"), ("LINTEL", "BEAM"), ("EDGE_BEAM", "BEAM"), ("GIRDER", "BEAM"),
  ("GROUND_BEAM", "BEAM"), ("DIAPHRAGM", "BEAM"), ("SLAB", "SLAB"), ("RAFT", "FOOTING"), ("FOOTING", "FOOTING"),
  ("FOUNDATION", "FOOTING"), ("PILE", "PILE"), ("WALL", "WALL"), ("STAIR", "STAIR"), ("RAMP", "STAIR"))

def role_family(role: str | None) -> str | None:
  r = (role or "").upper()
  for prefix, family in _FAMILIES:
    if r.startswith(prefix):
      return family
  return None

def _norm(text) -> str:
  return "".join(ch for ch in str(text or "").upper() if ch.isalnum() or ch == "#")

def lookup_size(sizes, designation, dia_mm: Decimal, grade) -> BarSizeSpec | None:
  d, g = _norm(designation), _norm(grade)
  def ok_grade(s, exact):
    return _norm(s.grade) == g if exact else _norm(s.grade) in ("ALL", "")
  for exact in (True, False):
    if d:
      hit = [s for s in sizes if _norm(s.designation) == d and ok_grade(s, exact) and abs(s.dia_mm - dia_mm) <= Decimal("1")]
      if hit:
        return sorted(hit, key=lambda s: (s.standard, s.designation))[0]
  for exact in (True, False):
    hit = [s for s in sizes if abs(s.dia_mm - dia_mm) <= Decimal("0.6") and ok_grade(s, exact)]
    if hit:
      return sorted(hit, key=lambda s: (abs(s.dia_mm - dia_mm), s.standard, s.designation))[0]
  return None

def unit_weight(sizes, designation, dia_mm: Decimal, grade) -> tuple[Decimal, list]:
  size = lookup_size(sizes, designation, dia_mm, grade)
  if size is not None:
    return size.kg_per_m, []
  return (dia_mm * dia_mm / KG_M_DIVISOR).quantize(Decimal("0.0001")), ["UNIT_WEIGHT_COMPUTED"]

def pick_rule(rules, family, role, bar_role: str, allow_all: bool = True):
  scopes = [s for s in (str(role or "").upper(), family) if s]
  if allow_all:
    scopes.append("ALL")
  for scope in scopes:
    for r in rules:
      if r.element_scope.upper() == scope and r.bar_role.upper() == bar_role.upper():
        return r
  return None

def bar_role_for(shape: ShapeSpec | None) -> str:
  return "STIRRUP" if shape is not None and shape.is_link else "MAIN"

def _stock_mm(rule) -> Decimal | None:
  if rule is None:
    return None
  if rule.stock_length_mm:
    return Decimal(rule.stock_length_mm)
  metres = (rule.splice_constraints or {}).get("stock_length_m")
  return Decimal(str(metres)) * 1000 if metres else None

def cut_from_shape(shape: ShapeSpec, params: dict, dia: Decimal, rule) -> tuple[Decimal, list]:
  missing = [p for p in shape.segments if p not in (params or {})]
  if missing:
    raise RebarError(f"shape {shape.code} needs dimension(s) {', '.join(missing)}")
  total = sum((Decimal(str(params[p])) for p in shape.segments), ZERO)
  steps = [{"op": "segments", "mm": str(total)}]
  if shape.bend_angles:
    table = ((rule.bend_rules if rule else {}) or {}).get("deduction_d_multiple") or {}
    if not table:
      raise RebarError(f"no bend deduction rule for shape {shape.code}")
    ded = ZERO
    
    for angle in shape.bend_angles:
      key = min(table, key=lambda k: abs(int(k) - int(angle)))
      if abs(int(key) - int(angle)) > 10:
        raise RebarError(f"no bend deduction for a {angle} degree bend")
      ded += Decimal(str(table[key])) * dia
    total -= ded
    steps.append({"op": "bend_deduction", "mm": str(-ded), "bends": len(shape.bend_angles)})
    
  if shape.hook_ends:
    hook_key = "stirrup_hook_d_multiple" if shape.is_link else "standard_hook_d_multiple"
    mult = ((rule.hook_rules if rule else {}) or {}).get(hook_key)
    if mult is None:
      raise RebarError(f"no {hook_key} rule for shape {shape.code}")
    add = Decimal(str(mult)) * dia * shape.hook_ends
    total += add
    steps.append({"op": "hook_allowance", "mm": str(add), "ends": shape.hook_ends})
    
  if total <= 0:
    raise RebarError("cut length is not positive")
  return total, steps

def split_laps(cut_mm: Decimal, dia: Decimal, rule) -> tuple[Decimal | None, int, int, Decimal | None, Decimal, list]:
  stock = _stock_mm(rule)
  if stock is None or cut_mm <= stock:
    return stock, 1, 0, None, cut_mm, []
  warnings: list = []
  basis = (rule.lap_basis or "").lower() if rule else ""
  coeff = Decimal(str(rule.lap_coefficient)) if rule and rule.lap_coefficient is not None else None
  
  if basis == "diameter_multiple" and coeff is not None:
    lap = coeff * dia
  elif basis == "fixed_mm" and coeff is not None:
    lap = coeff
  else:
    lap = ZERO
    warnings.append("LAP_LENGTH_UNKNOWN")
  if rule is not None and rule.min_lap_mm:
    lap = max(lap, Decimal(rule.min_lap_mm))
  if stock <= lap:
    raise RebarError("stock length is not longer than the lap length")
  pieces = int(math.ceil((cut_mm - lap) / (stock - lap)))
  coupled = bool(rule is not None and rule.use_couplers)
  lap_count = pieces - 1
  per_bar = cut_mm if coupled else cut_mm + lap_count * lap
  return stock, pieces, lap_count, (ZERO if coupled else lap), per_bar, warnings

def compute_mark(row: RebarRowInput, shape: ShapeSpec | None, sizes, rules, family: str | None) -> dict:
  bar_role = bar_role_for(shape)
  rule = pick_rule(rules, family, row.role, bar_role)
  steps: list = []
  
  if row.cut_len_mm is not None and row.cut_len_mm > 0:
    cut = Decimal(row.cut_len_mm)
    steps.append({"op": "declared_cut_length", "mm": str(cut)})
  elif shape is not None:
    cut, steps = cut_from_shape(shape, row.shape_params or {}, row.dia_mm, rule)
  else:
    raise RebarError("no cut length and no known shape")
  stock, pieces, laps, lap_len, per_bar, warnings = split_laps(cut, row.dia_mm, rule)
  if laps:
    steps.append({"op": "laps", "pieces": pieces, "lap_count": laps, "lap_mm": str(lap_len), "stock_mm": str(stock)})
    
  uw, uw_warn = unit_weight(sizes, row.designation, row.dia_mm, row.grade)
  total_len_m = q6(Decimal(row.count) * per_bar / 1000)
  total_kg = q6(total_len_m * uw)
  steps.append({"op": "weight", "kg_per_m": str(uw), "m": str(total_len_m), "kg": str(total_kg)})
  warnings = [*warnings, *uw_warn]
  
  if row.declared_total_kg and row.declared_total_kg > 0:
    tol = Decimal(rule.weight_tolerance_pct) if rule is not None and rule.weight_tolerance_pct is not None else DEFAULT_TOLERANCE_PCT
    off = abs(total_kg - row.declared_total_kg) / row.declared_total_kg * 100
    
    if off > tol:
      warnings.append("DECLARED_WEIGHT_MISMATCH")
      steps.append({"op": "declared_weight", "kg": str(row.declared_total_kg), "diff_pct": str(q4(off))})
  return {"cut_len_mm": q4(cut).quantize(Decimal("0.001")), "stock_len_mm": stock, "pieces": pieces, "lap_count": laps * row.count,
    "lap_len_mm": lap_len, "total_len_m": total_len_m, "unit_weight_kg_m": uw, "total_kg": total_kg, "warnings": warnings,
    "steps": steps, "bar_role": bar_role}

def _review(warnings, confidence: Decimal) -> str:
  return "REVIEW_REQUIRED" if (set(warnings) & REVIEW_CODES or confidence < SCHEDULE_CONFIDENCE_FLOOR) else "OK"

def _unique_mark(used: dict, solid_id, mark: str) -> str:
  names = used.setdefault(solid_id, set())
  mark = (mark or "M")[:50]
  candidate, n = mark, 1
  while candidate in names:
    n += 1
    candidate = f"{mark[:45]}-{n}"
  names.add(candidate)
  return candidate

def _ledger_for_solid(ctx, solid: Solid, marks: list[BarMark], formula: str, source_kind: str, label: str) -> LedgerEntry:
  kg = q6(sum((m.total_kg for m in marks), ZERO))
  grades = {m.grade for m in marks}
  warnings = [w for m in marks for w in m.warnings]
  
  if len(grades) > 1:
    warnings.append("MIXED_GRADES")
  if source_kind == "ESTIMATE":
    warnings.append("STEEL_ESTIMATED")
    
  return LedgerEntry(
    solid_id=solid.id, element_id=solid.element_id, level_id=solid.level_id, work_item_code=REBAR_WORK_ITEM,
    quantity=kg, unit="kg", material_grade=next(iter(grades)) if len(grades) == 1 else None,
    confidence=min(m.confidence for m in marks), formula_code=formula,
    trace={"formula_code": formula, "engine_version": ctx.engine_version, "convention": ctx.convention_code,
      "rule_set": {"code": ctx.rule_set_code, "version": ctx.rule_set_version}, "label": label,
      "inputs": {"marks": len(marks), "provenance": sorted({m.provenance for m in marks})},
      "steps": [{"op": "bar_mark", "mark": m.mark, "dia_mm": str(m.dia_mm), "count": m.count, "kg": str(m.total_kg)} for m in marks],
      "net": {"kg": str(kg)}, "rounding": "half_up,6dp"},
    warnings=tuple(dict.fromkeys(warnings)), source_kind=source_kind)

def measure_rebar(ctx, profile, solids: list, ledger: list, inputs: RebarInputs | None) -> RebarResult:
  inputs = inputs or RebarInputs()
  rules = tuple(getattr(profile, "reinforcement_rules", ()) or ())
  shapes = {s.code.upper(): s for s in inputs.shapes}
  by_element = {s.element_id: s for s in solids if s.element_id is not None and s.component_type == "BODY"}
  by_id = {s.id: s for s in solids}
  new_solids: list = []
  marks: list = []
  skipped: dict = {}
  used: dict = {}
  per_solid: dict = {}
  covered_elements: set = set()
  covered_families: set = set()
  stats = {"schedule_rows": len(inputs.rows), "schedule_marks": 0, "matched": 0, "unmatched": 0, "estimated_marks": 0,
    "estimate_suppressed": 0}

  for row in sorted(inputs.rows, key=lambda r: (str(r.import_id), r.row_no)):
    family = role_family(row.role)
    shape = shapes.get((row.shape_code or "").upper())
    try:
      calc = compute_mark(row, shape, inputs.sizes, rules, family)
    except RebarError as exc:
      key = f"row skipped: {exc}"
      skipped[key] = skipped.get(key, 0) + 1
      continue
    warnings = list(calc["warnings"])
    host = by_element.get(row.matched_element_id) if row.matched_element_id else None
    if row.matched_element_id and host is None:
      warnings.append("MATCHED_ELEMENT_NOT_MEASURED")
      
    if host is None:
      host = Solid(id=uuid5(ctx.run_id, f"solid|rebar-row:{row.id}"), element_id=None, ifc_type="BBS", role="REBAR_SCHEDULE",
        level_id=row.level_id, geometry_kind="QTO_ONLY", classification_confidence=ONE, confidence_factor=ONE,
        component_type="REBAR", gross_length_m=calc["total_len_m"])
      new_solids.append(host)
      stats["unmatched"] += 1
    else:
      covered_elements.add(host.element_id)
      stats["matched"] += 1
    if family:
      covered_families.add(family)
    confidence = max(ZERO, min(ONE, Decimal(row.confidence)))
    
    mark = BarMark(
      solid_id=host.id, element_id=host.element_id, level_id=host.level_id or row.level_id,
      mark=_unique_mark(used, host.id, row.mark), role=(row.role or "UNKNOWN").upper(),
      shape_code=(row.shape_code or "DECLARED").upper(), shape_params=dict(row.shape_params or {}),
      designation=row.designation, dia_mm=row.dia_mm, grade=row.grade, count=row.count, spacing_mm=row.spacing_mm,
      cut_len_mm=calc["cut_len_mm"], stock_len_mm=calc["stock_len_mm"], pieces=calc["pieces"], lap_count=calc["lap_count"],
      lap_len_mm=calc["lap_len_mm"], total_len_m=calc["total_len_m"], unit_weight_kg_m=calc["unit_weight_kg_m"],
      total_kg=calc["total_kg"], provenance="SCHEDULE_IMPORT", confidence=confidence,
      review_status=_review(warnings, confidence), schedule_row_id=row.id,
      trace={"steps": calc["steps"], "row_no": row.row_no, "member_mark": row.member_mark},
      warnings=tuple(dict.fromkeys(warnings)))
    marks.append(mark)
    per_solid.setdefault(host.id, (host, []))[1].append(mark)
    stats["schedule_marks"] += 1

  out_ledger = [
    _ledger_for_solid(ctx, host, ms, FORMULA_BBS, "SCHEDULE_IMPORT", f"BBS {host.role}")
    for host, ms in (per_solid[k] for k in sorted(per_solid, key=str))]

  for e in sorted(ledger, key=lambda r: (str(r.solid_id), r.work_item_code)):
    if e.formula_code != "SOLID_NET_VOLUME":
      continue
    solid = by_id.get(e.solid_id)
    family = role_family(solid.role) if solid is not None else None
    rule = pick_rule(rules, family, solid.role if solid else None, "ESTIMATE", allow_all=False) if family else None
    if rule is None:
      continue
  
    if solid.element_id in covered_elements or family in covered_families:
      stats["estimate_suppressed"] += 1
      continue
    extra = rule.extra_config or {}
    try:
      intensity = Decimal(str(extra.get("kg_per_m3") or 0))
      dia = Decimal(str(extra.get("assumed_dia_mm") or DEFAULT_ESTIMATE_DIA_MM))
      conf = Decimal(str(extra.get("confidence") or DEFAULT_ESTIMATE_CONFIDENCE))
    except Exception:
      intensity, dia, conf = ZERO, DEFAULT_ESTIMATE_DIA_MM, DEFAULT_ESTIMATE_CONFIDENCE
    if intensity <= 0:
      skipped["estimate rule has no kg_per_m3"] = skipped.get("estimate rule has no kg_per_m3", 0) + 1
      continue
    uw, uw_warn = unit_weight(inputs.sizes, None, dia, None)
    kg = q6(e.quantity * intensity)
    total_len_m = q6(kg / uw)
    
    mark = BarMark(
      solid_id=solid.id, element_id=solid.element_id, level_id=solid.level_id, mark=_unique_mark(used, solid.id, f"EST-{family}"),
      role=family, shape_code="ESTIMATE", shape_params={}, designation=None, dia_mm=dia, grade=None, count=1, spacing_mm=None,
      cut_len_mm=(total_len_m * 1000).quantize(Decimal("0.001")), stock_len_mm=None, pieces=1, lap_count=0, lap_len_mm=None,
      total_len_m=total_len_m, unit_weight_kg_m=uw, total_kg=kg, provenance="RULE_ESTIMATE", confidence=max(ZERO, min(ONE, conf)),
      review_status="REVIEW_REQUIRED", schedule_row_id=None,
      trace={"steps": [{"op": "net_volume", "m3": str(e.quantity)}, {"op": "intensity", "kg_per_m3": str(intensity)},
        {"op": "weight", "assumed_dia_mm": str(dia), "kg": str(kg)}]},
      warnings=tuple(dict.fromkeys(["STEEL_ESTIMATED", *uw_warn])))
    marks.append(mark)
    
    out_ledger.append(_ledger_for_solid(ctx, solid, [mark], FORMULA_ESTIMATE, "ESTIMATE", f"Estimate {family}"))
    stats["estimated_marks"] += 1

  out_ledger.sort(key=lambda r: (r.work_item_code, str(r.level_id), str(r.solid_id)))
  total = q6(sum((m.total_kg for m in marks), ZERO))
  stats.update({"total_kg": str(total), "covered_families": sorted(covered_families),
    "tier2_kg": str(q6(sum((m.total_kg for m in marks if m.provenance != "RULE_ESTIMATE"), ZERO))),
    "tier3_kg": str(q6(sum((m.total_kg for m in marks if m.provenance == "RULE_ESTIMATE"), ZERO)))})
  return RebarResult(solids=new_solids, ledger=out_ledger, marks=marks, skipped=dict(sorted(skipped.items())), stats=stats)

def self_check_rebar(marks: list, ledger: list) -> list[str]:
  failures: list[str] = []
  kg_by_solid: dict = {}
  
  for m in marks:
    kg_by_solid[m.solid_id] = kg_by_solid.get(m.solid_id, ZERO) + m.total_kg
    if m.provenance == "RULE_ESTIMATE" and m.review_status != "REVIEW_REQUIRED":
      failures.append(f"estimate mark {m.mark} is not flagged for review")
    if m.total_kg < 0 or m.total_len_m < 0:
      failures.append(f"negative quantity on mark {m.mark}")
      
  for e in ledger:
    if e.formula_code in REBAR_FORMULA_UNITS:
      if q6(kg_by_solid.get(e.solid_id, ZERO)) != e.quantity:
        failures.append(f"ledger kg != sum of bar marks on solid {e.solid_id}")
  return failures

def rebar_payload(inputs: RebarInputs | None) -> dict:
  if inputs is None:
    return {}

  return {
    "rows": [[str(r.id), r.mark, r.role, r.shape_code, sorted((r.shape_params or {}).items()), r.designation, str(r.dia_mm),
      r.grade, r.count, str(r.spacing_mm), str(r.cut_len_mm), str(r.declared_total_kg), str(r.level_id),
      str(r.matched_element_id), str(r.confidence)] for r in sorted(inputs.rows, key=lambda r: str(r.id))],
    "shapes": [[s.code, list(s.segments), list(s.bend_angles), s.hook_ends, s.is_link] for s in sorted(inputs.shapes, key=lambda s: s.code)],
    "sizes": [[s.standard, s.designation, s.grade, str(s.dia_mm), str(s.kg_per_m)] for s in sorted(inputs.sizes, key=lambda s: (s.standard, s.designation, s.grade))],
  }