from __future__ import annotations
from dataclasses import replace
from app.engine.measure.units import Unit, mm3_to_m3, q4, q6, to_decimal
from decimal import Decimal
from uuid import uuid5
from app.engine.measure.geometry import bbox_volume_mm3, extrusion_volume_mm3
from app.engine.measure.models import CalculationContext, CalculationResult, LedgerEntry, MappingInput, ModelElement, Rejected, Solid, AllocationResult
from app.engine.measure.formulas import get_formula
from app.engine.measure.allocate import allocate as _allocate
from app.engine.measure.conventions import get_convention
from app.engine.measure.intersect import find_overlaps
from app.engine.measure.spatial import build_spatial_index
from app.engine.measure.finishes import REINFORCEMENT_FORMULA_UNITS, apply_openings, measure_finishes, merge_openings, schedule_lines_ledger
from app.engine.measure.rebar import REBAR_FORMULA_UNITS, measure_rebar, self_check_rebar
from app.engine.measure.steel import (STEEL, STEEL_BBOX_FACTOR, STEEL_FORMULA_UNITS, STEEL_REJECTED_CODE, STEEL_SOLID_PROFILE_FACTOR,
  STEEL_UNCERTAIN_FACTOR, UNCERTAIN_BASES, is_pile, is_steel_role, measure_steel, solid_profile_suspected, split_steel,
  steel_check, steel_duplicate_ids, steel_length_mm, steel_member_length_mm, steel_recoverable, steel_stats)
from app.engine.measure.stages import split_stages
from app.engine.measure.layers import layer_check, layer_excluded_by_solid, split_layers
from app.engine.measure.derived import derived_check, measure_derived
from app.engine.measure.confidence import MISMATCH, VERIFIED, band, box_factor, stands_on_its_own
from app.engine.measure.spec import derive_spec, describe_spec, missing_spec_warnings, spec_grade, spec_key
from app.engine.measure.takeoff import TAKEOFF_FORMULA_UNITS, apply_replacements, measure_takeoff, takeoff_check

ENGINE_VERSION = "2026.10.10"

VOLUME_ROLES = frozenset({
  "COLUMN", "COLUMN_STRUCTURAL", "COLUMN_PRECAST",
  "BEAM", "BEAM_STRUCTURAL", "BEAM_EDGE", "BEAM_TRANSFER", "BEAM_PRECAST",
  "EDGE_BEAM", "GIRDER", "GIRDER_SEGMENT", "DIAPHRAGM",
  "LINTEL", "SILL", "KERB",
  "SLAB", "SLAB_STRUCTURAL", "SLAB_FOUNDATION", "SLAB_ROOF", "SLAB_GROUND",
  "SLAB_LANDING", "SLAB_PRECAST", "SLAB_POST_TENSIONED",
  "WALL", "WALL_EXTERNAL", "WALL_INTERNAL", "WALL_PARTITION",
  "WALL_LOAD_BEARING", "WALL_FOUNDATION", "WALL_RETAINING",
  "WALL_PARAPET", "WALL_SHEAR", "WALL_CORE",
  "FOUNDATION", "FOOTING", "FOOTING_ISOLATED", "FOOTING_STRIP",
  "FOOTING_COMBINED", "RAFT", "RAFT_FOUNDATION",
  "PILE", "PILE_FOUNDATION", "PILE_CAP", "GROUND_BEAM",
  "STAIR", "STAIR_FLIGHT", "LANDING",
  "RAMP", "RAMP_SLAB",
})
COUNT_ROLES = frozenset({"DOOR", "WINDOW"})
FORMULA_UNITS = {"SOLID_NET_VOLUME": Unit.M3.value, "OPENING_COUNT": Unit.NOS.value, **REINFORCEMENT_FORMULA_UNITS, **REBAR_FORMULA_UNITS, **STEEL_FORMULA_UNITS, **TAKEOFF_FORMULA_UNITS}
LOW_CONFIDENCE_FACTOR = Decimal("0.6")
QTO_ONLY_FACTOR = Decimal("0.9")
AABB_CONFIDENCE_FACTOR = Decimal("0.8")
QTO_MISMATCH_TOLERANCE = 0.02

class InvariantViolation(Exception):
  def __init__(self, failures: list[str]):
    super().__init__("; ".join(failures[:5]))
    self.failures = failures

def _issue(code: str, severity: str, message: str) -> dict:
  return {"code": code, "severity": severity, "message": message}

def _solid_id(ctx: CalculationContext, element_id, component: str = "BODY"):
  return uuid5(ctx.run_id, f"solid|{element_id}|{component}")

def validate_input(ctx: CalculationContext, elements: list[ModelElement]):
  accepted: list[ModelElement] = []
  rejected: list[Rejected] = []
  for el in sorted(elements, key=lambda e: str(e.id)):
    if el.normalization_status == "INVALID" and not steel_recoverable(el):
      if el.material_class == STEEL and is_steel_role(el.role):
        rejected.append(Rejected(el.id, el.ifc_type, STEEL_REJECTED_CODE,
          "Steel element has no model volume or length; not weighed."))
      else:
        rejected.append(Rejected(el.id, el.ifc_type, "INVALID_ELEMENT",
          "Element failed ingestion validation; not measured."))
    else:
      accepted.append(el)
  return accepted, rejected

def _volume_solid(ctx: CalculationContext, el: ModelElement) -> Solid:
  issues: list[dict] = []
  status = "OK"
  factor = Decimal("1")
  volume_mm3: float | None = None
  kind = el.geometry_kind or "UNSUPPORTED"
  qto_mm3 = float(el.volume_mm3) if el.volume_mm3 is not None and el.volume_mm3 > 0 else None

  if kind in ("EXTRUDED_PROFILE", "AXIS_SWEPT"):
    volume_mm3 = extrusion_volume_mm3(el.profile, el.placement)
    if volume_mm3 is None:
      if qto_mm3 is not None:
        volume_mm3 = qto_mm3
        factor = LOW_CONFIDENCE_FACTOR
        issues.append(_issue("QTO_FALLBACK", "warning",
          "Profile or extrusion depth missing; volume taken from the model's Qto value."))
      else:
        issues.append(_issue("GEOMETRY_INCOMPLETE", "warning",
          "Profile or extrusion depth missing; no gross volume measured."))
      status = "REVIEW_REQUIRED"
    elif qto_mm3 is not None:
      if abs(volume_mm3 - qto_mm3) / qto_mm3 > QTO_MISMATCH_TOLERANCE:
        is_wall = el.role.startswith("WALL")
        issues.append(_issue("QTO_GEOMETRY_MISMATCH", "info" if is_wall else "warning",
          "Geometry volume differs from the model's Qto volume by more than 2%."))
        if not is_wall:
          status = "REVIEW_REQUIRED"
  elif kind in ("BOX_ONLY", "QTO_ONLY"):
    volume_mm3 = qto_mm3
    from_bbox = False
    if volume_mm3 is None and kind == "BOX_ONLY":
      volume_mm3 = bbox_volume_mm3(el.bbox_min_mm, el.bbox_max_mm)
      from_bbox = volume_mm3 is not None
    status = "REVIEW_REQUIRED"
    if volume_mm3 is None:
      issues.append(_issue("UNSUPPORTED_GEOMETRY", "warning", "No usable volume for this element."))
    elif kind == "QTO_ONLY":
      factor = QTO_ONLY_FACTOR
      issues.append(_issue("LOW_CONFIDENCE_GEOMETRY", "warning", f"Volume taken from {kind}; treat as approximate."))
    else:
      factor = box_factor(el.volume_check, from_bbox)
      if stands_on_its_own(el.volume_check, from_bbox):
        status = "OK"
        issues.append(_issue(
          "BOX_VOLUME_VERIFIED" if el.volume_check == VERIFIED else "BOX_VOLUME_FROM_MESH", "info",
          "Volume agrees with the closed 3D mesh. The shape is a bounding box, so overlaps and openings are approximate."
          if el.volume_check == VERIFIED else
          "Volume taken from the closed 3D mesh. The shape is a bounding box, so overlaps and openings are approximate."))
      elif from_bbox:
        issues.append(_issue("LOW_CONFIDENCE_GEOMETRY", "warning",
          "No model volume and no closed mesh; the volume is the bounding box, which overstates a slanted or notched member."))
      elif el.volume_check == MISMATCH:
        issues.append(_issue("LOW_CONFIDENCE_GEOMETRY", "warning",
          "The model's volume and the 3D mesh volume differ by more than 2%; treat as approximate."))
      else:
        issues.append(_issue("LOW_CONFIDENCE_GEOMETRY", "warning", f"Volume taken from {kind}; treat as approximate."))
  else:
    issues.append(_issue("UNSUPPORTED_GEOMETRY", "warning", "Geometry kind not measurable in this engine version."))
    status = "REVIEW_REQUIRED"

  gross = mm3_to_m3(volume_mm3) if volume_mm3 is not None else None
  if gross is not None and gross <= 0:
    gross = None
    issues.append(_issue("ZERO_GROSS_VOLUME", "warning", "Gross volume rounds to zero."))
    status = "REVIEW_REQUIRED"

  spec = derive_spec(el) if ctx.spec_mode else None
  return Solid(
    id=_solid_id(ctx, el.id), element_id=el.id, ifc_type=el.ifc_type, role=el.role,
    level_id=el.level_id, geometry_kind=kind,
    classification_confidence=el.classification_confidence, confidence_factor=factor,
    gross_volume_m3=gross, status=status, issues=tuple(issues), material_class=el.material_class,
    material_grade=spec_grade(spec), spec=spec, volume_check=el.volume_check if kind == "BOX_ONLY" else None,
    generic_material=bool(getattr(el, "generic_material", False)),
  )

def _steel_flags(el: ModelElement, duplicate: bool):
  issues: list[dict] = []
  factor = Decimal("1")
  if el.material_basis in UNCERTAIN_BASES:
    issues.append(_issue("STEEL_MATERIAL_UNCERTAIN", "warning",
      "The material only says metal or iron, or steel was inferred from the element name; confirm it is structural steel."))
    factor *= STEEL_UNCERTAIN_FACTOR
    
  if duplicate:
    issues.append(_issue("STEEL_DUPLICATE_SUSPECTED", "warning",
      "Another steel member has the same type, position and size; this one may be a duplicate in the model."))
  if solid_profile_suspected(el):
    issues.append(_issue("STEEL_SOLID_SECTION_SUSPECTED", "warning",
      "The member is drawn as a plain solid rectangle or circle of section size; it may be a hollow or rolled section."))
    factor *= STEEL_SOLID_PROFILE_FACTOR
  return issues, factor

def _steel_solid(ctx: CalculationContext, el: ModelElement, duplicate: bool = False) -> Solid:
  solid = _steel_solid_base(ctx, el, duplicate)
  flags, factor = _steel_flags(el, duplicate)
  if not flags:
    return solid
  return replace(solid, confidence_factor=solid.confidence_factor * factor, issues=(*solid.issues, *flags),
    status="REVIEW_REQUIRED" if solid.status == "OK" else solid.status)

def _steel_solid_base(ctx: CalculationContext, el: ModelElement, duplicate: bool = False) -> Solid:
  kind = el.geometry_kind or "UNSUPPORTED"
  if el.volume_mm3 is not None and not Decimal(el.volume_mm3).is_finite():
    el = replace(el, volume_mm3=None)
  length_mm = steel_length_mm(el) if is_pile(el.role) else steel_member_length_mm(el)
  length_m = q6(to_decimal(length_mm) / 1000) if length_mm else None
  note = _issue("STEEL_MEASURED_BY_WEIGHT", "info",
    "Steel element measured as structural steel, not concrete." if el.normalization_status != "INVALID" else
    "The reader flagged this steel element as non-concrete; it is measured as structural steel instead.")
  
  if is_pile(el.role):
    issues = [note]
    
    if length_m is None:
      issues.append(_issue("UNSUPPORTED_GEOMETRY", "warning", "No usable pile length."))
    return Solid(
      id=_solid_id(ctx, el.id), element_id=el.id, ifc_type=el.ifc_type, role=el.role, level_id=el.level_id,
      geometry_kind=kind if kind in ("EXTRUDED_PROFILE", "AXIS_SWEPT", "BOX_ONLY", "QTO_ONLY") else "UNSUPPORTED",
      classification_confidence=el.classification_confidence,
      confidence_factor=Decimal("1") if kind in ("EXTRUDED_PROFILE", "AXIS_SWEPT") else STEEL_BBOX_FACTOR,
      gross_length_m=length_m, status="OK" if length_m is not None else "REVIEW_REQUIRED", issues=tuple(issues),
      material_class=STEEL)
    
  solid = _volume_solid(ctx, el)
  issues = [i for i in solid.issues if i["code"] not in ("LOW_CONFIDENCE_GEOMETRY", "BOX_VOLUME_VERIFIED", "BOX_VOLUME_FROM_MESH")]
  issues.append(note)
  
  if kind == "BOX_ONLY":
    if not (el.volume_mm3 is not None and el.volume_mm3 > 0):
      issues.append(_issue("STEEL_NO_RELIABLE_VOLUME", "warning",
        "Only a bounding box is available for this steel member; it was not weighed."))
      return replace(solid, gross_volume_m3=None, status="REVIEW_REQUIRED", issues=tuple(issues), material_class=STEEL)
    return replace(solid, confidence_factor=STEEL_BBOX_FACTOR, status="OK", issues=tuple(issues),
      gross_length_m=length_m, material_class=STEEL)
  return replace(solid, issues=tuple(issues), gross_length_m=length_m, material_class=STEEL)

def build_solids(ctx: CalculationContext, elements: list[ModelElement]):
  solids: list[Solid] = []
  skipped: dict[str, int] = {}
  duplicates = steel_duplicate_ids(elements)
  
  for el in elements:
    if el.material_class == STEEL and is_steel_role(el.role):
      solids.append(_steel_solid(ctx, el, el.id in duplicates))
    elif el.role in COUNT_ROLES:
      solids.append(Solid(
        id=_solid_id(ctx, el.id), element_id=el.id, ifc_type=el.ifc_type, role=el.role,
        level_id=el.level_id, geometry_kind=el.geometry_kind or "UNSUPPORTED",
        classification_confidence=el.classification_confidence, confidence_factor=Decimal("1"),
        count=1,
      ))
    elif el.role in VOLUME_ROLES:
      solids.append(_volume_solid(ctx, el))
    else:
      skipped[el.role] = skipped.get(el.role, 0) + 1
  solids.sort(key=lambda s: (s.role, str(s.level_id), str(s.element_id)))
  return solids, dict(sorted(skipped.items()))

STRUCTURAL_CONCRETE_TYPES = ("IfcSlab", "IfcColumn", "IfcBeam", "IfcFooting")

def _structural_concrete_code(by_ifc: dict) -> str | None:
  for ifc_type in STRUCTURAL_CONCRETE_TYPES:
    m = by_ifc.get(ifc_type)
    if m is not None and m.work_item_code:
      return m.work_item_code
  return None

def measure(ctx: CalculationContext, solids: list[Solid], alloc):
  by_ifc = {m.ifc_type: m for m in ctx.mappings}
  concrete_code = _structural_concrete_code(by_ifc)
  deds_by_solid: dict = {}
  for d in getattr(alloc, "deductions", ()) or ():
    deds_by_solid.setdefault(d.from_solid_id, []).append(d)

  ledger: list[LedgerEntry] = []
  unmapped: dict[str, int] = {}

  for s in solids:
    if s.material_class == STEEL:
      continue
    mapping = by_ifc.get(s.ifc_type)
    redirect = None
    if (mapping is not None and mapping.work_item_code and concrete_code and s.material_class == "CONCRETE"
        
        and s.role.startswith("WALL") and mapping.work_item_code != concrete_code):
      redirect = {"from": mapping.work_item_code, "to": concrete_code, "reason": "WALL_MATERIAL_CONCRETE"}
      mapping = MappingInput(mapping.ifc_type, concrete_code, mapping.confidence_base)
    if mapping is None or not mapping.work_item_code:
      unmapped[s.ifc_type] = unmapped.get(s.ifc_type, 0) + 1
      continue
    
    warnings = [i["code"] for i in s.issues if i.get("severity") == "warning"]
    warnings.extend(missing_spec_warnings(s.spec, bool(concrete_code) and mapping.work_item_code == concrete_code))
    if s.generic_material:
      warnings.append("MATERIAL_GENERIC")
    warnings.extend(getattr(alloc, "solid_warnings", {}).get(s.id, ()))
    if s.id in getattr(alloc, "approximate_solids", ()):
      warnings.append("ALLOCATION_APPROXIMATE")
    if s.id in getattr(alloc, "unallocated_solids", ()):
      warnings.append("NOT_ALLOCATED")
    elif s.gross_volume_m3 is not None and not getattr(alloc, "applied", False):
      warnings.append("NOT_ALLOCATED") 

    if s.count is not None:
      formula, unit, quantity = "OPENING_COUNT", Unit.NOS.value, Decimal(s.count)
      inputs = {"count": s.count}
      steps = [{"op": "count", "nos": str(s.count)}]
      net = {"nos": str(quantity)}
    elif s.gross_volume_m3 is not None:
      gross = q6(s.gross_volume_m3)
      solid_deds = deds_by_solid.get(s.id, [])
      total_ded = q6(sum((d.quantity for d in solid_deds), Decimal("0")))
      quantity = q6(gross - total_ded)
      zero_flagged = False
      if quantity <= 0 and total_ded > 0:
        warnings.append("DUPLICATE_SOLID" if "SAME_ROLE_OVERLAP" in warnings else "ZERO_NET_QUANTITY")
        zero_flagged = True
      if quantity < 0:
        quantity = Decimal("0")
        
      formula, unit = "SOLID_NET_VOLUME", Unit.M3.value
      inputs = {"geometry_kind": s.geometry_kind, "gross_m3": str(gross), "confidence_factor": str(s.confidence_factor)}
      if s.volume_check:
        inputs["volume_check"] = s.volume_check
      if s.material_class:
        inputs["material_class"] = s.material_class
      if redirect:
        inputs["work_item_redirect"] = redirect
      if s.spec:
        inputs["spec"] = s.spec
      steps = [
        {"op": "gross_volume", "m3": str(gross)},
      ]
      for d in solid_deds:
        steps.append({
          "op": "deduction",
          "type": d.deduction_type,
          "m3": str(d.quantity),
          "rule": getattr(d, "rule_code", None),
          "note": getattr(d, "explanation", None),
          "to_solid_id": str(d.to_solid_id) if d.to_solid_id else None,
        })
      steps.append({"op": "net_volume", "m3": str(quantity)})
      net = {"m3": str(quantity)}

      if s.role.startswith("WALL") and s.id not in getattr(alloc, "openings_checked", ()) \
        and not any(d.deduction_type == "VOID_DEDUCTION" for d in solid_deds):
        warnings.append("OPENINGS_NOT_DEDUCTED")
    else:
      continue

    if quantity <= 0 and not (s.count is None and zero_flagged):
      continue

    confidence = q4(min(mapping.confidence_base, s.classification_confidence) * s.confidence_factor)
    confidence = max(Decimal("0"), min(Decimal("1"), confidence))

    ledger.append(LedgerEntry(
      solid_id=s.id,
      element_id=s.element_id,
      level_id=s.level_id,
      work_item_code=mapping.work_item_code,
      quantity=quantity,
      unit=unit,
      material_grade=s.material_grade,
      confidence=confidence,
      formula_code=formula,
      trace={
        "formula_code": formula,
        "engine_version": ctx.engine_version,
        "convention": ctx.convention_code,
        "rule_set": {"code": ctx.rule_set_code, "version": ctx.rule_set_version},
        "inputs": inputs,
        "steps": steps,
        "net": net,
        "rounding": "half_up,6dp",
      },
      warnings=tuple(dict.fromkeys(warnings)),
      spec=s.spec,
      spec_key=spec_key(s.spec),
    ))

  ledger.extend(measure_steel(ctx, solids))
  ledger.sort(key=lambda r: (r.work_item_code, str(r.level_id), str(r.element_id)))
  return ledger, dict(sorted(unmapped.items()))

def _expected_unit(formula_code: str) -> str | None:
  spec = get_formula(formula_code)
  if spec is not None:
    return spec.output_unit
  return FORMULA_UNITS.get(formula_code)

def self_check(solids: list[Solid], ledger: list[LedgerEntry], alloc: AllocationResult | None = None) -> None:
  alloc = alloc or AllocationResult.empty()
  failures: list[str] = []
  by_id = {s.id: s for s in solids}

  ded_total: dict = {}
  for d in alloc.deductions:
    if d.from_solid_id not in by_id or (d.to_solid_id is not None and d.to_solid_id not in by_id):
      failures.append("deduction references unknown solid")
      continue
    if d.quantity < 0:
      failures.append(f"negative deduction on solid {d.from_solid_id}")
    if d.deduction_type == "OVERLAP_ALLOCATION" and d.to_solid_id is None:
      failures.append(f"overlap deduction without owner on solid {d.from_solid_id}")
    ded_total[d.from_solid_id] = ded_total.get(d.from_solid_id, Decimal("0")) + d.quantity

  seen: set = set()
  net_by_solid: dict = {}
  layer_excluded = layer_excluded_by_solid(ledger)
  for row in ledger:
    solid = by_id.get(row.solid_id)
    if solid is None:
      failures.append(f"ledger row references unknown solid {row.solid_id}")
      continue
    if row.quantity < 0:
      failures.append(f"negative quantity on solid {row.solid_id}")
    if _expected_unit(row.formula_code) != row.unit:
      failures.append(f"unit {row.unit} does not match formula {row.formula_code}")
    key = (row.solid_id, row.work_item_code, row.work_stage)
    if key in seen:
      failures.append(f"duplicate ledger row for {key}")
    seen.add(key)
    if not row.trace or "formula_code" not in row.trace:
      failures.append(f"missing trace on solid {row.solid_id}")
    if row.work_stage is not None and row.source_kind != "MODEL":
      failures.append(f"work stage {row.work_stage} on a row not measured from the model ({row.solid_id})")

    layered = bool((((row.trace or {}).get("inputs") or {}).get("layer_split")))
    if row.formula_code == "SOLID_NET_VOLUME" and not layered and row.spec_key != spec_key(solid.spec):
      failures.append(f"specification key differs from its solid on solid {row.solid_id}")
      
    if row.formula_code == "SOLID_NET_VOLUME" and solid.gross_volume_m3 is not None:
      net_by_solid[row.solid_id] = net_by_solid.get(row.solid_id, Decimal("0")) + row.quantity

  for solid_id, total in net_by_solid.items():
    expected = q6(max(Decimal("0"), by_id[solid_id].gross_volume_m3 - ded_total.get(solid_id, Decimal("0"))
      - layer_excluded.get(solid_id, Decimal("0"))))
    if total != expected:
      failures.append(f"net volume != gross - deductions on solid {solid_id}")

  failures.extend(takeoff_check(solids, ledger))
  failures.extend(steel_check(solids, ledger))
  failures.extend(layer_check(ledger))
  failures.extend(derived_check(solids, ledger))
  failures.extend(f"NON_CONSERVING_ALLOCATION: {m}" for m in alloc.conservation_failures)
  if failures:
    raise InvariantViolation(failures)

def spatial_index(ctx: CalculationContext, convention, solids: list[Solid], elements: list[ModelElement]):
  return build_spatial_index(ctx, convention, solids, elements)

def find_relations(ctx: CalculationContext, index):
  return find_overlaps(ctx, index)

def allocate(ctx: CalculationContext, convention, solids: list[Solid], index, overlaps):
  return _allocate(ctx, convention, solids, index, overlaps)

def wall_material_stats(solids: list[Solid], ledger: list[LedgerEntry]) -> dict:
  walls = [s for s in solids if s.role.startswith("WALL")]
  return {
    "walls": len(walls),
    "concrete": sum(1 for s in walls if s.material_class == "CONCRETE"),
    "masonry": sum(1 for s in walls if s.material_class == "MASONRY"),
    "material_unknown": sum(1 for s in walls if not s.material_class),
    "billed_as_concrete": sum(1 for r in ledger if (r.trace.get("inputs") or {}).get("work_item_redirect")),
  }

def spec_stats(ctx: CalculationContext, ledger: list[LedgerEntry]) -> dict:
  if not ctx.spec_mode:
    return {"enabled": False}
  rows = [r for r in ledger if r.spec]
  def count(code):
    return sum(1 for r in rows if code in r.warnings)
  return {
    "enabled": True, "rows_with_spec": len(rows),
    "masonry_rows": sum(1 for r in rows if r.spec.get("kind") == "MASONRY"),
    "concrete_rows": sum(1 for r in rows if r.spec.get("kind") == "CONCRETE"),
    "mix_missing": count("SPEC_MIX_MISSING"), "mortar_missing": count("SPEC_MORTAR_MISSING"),
    "thickness_missing": count("SPEC_THICKNESS_MISSING"),
    "distinct_spec_keys": len({(r.work_item_code, r.material_grade, r.spec_key) for r in rows}),
  }
  
def stage_stats(ctx: CalculationContext) -> dict:
  return {"enabled": bool(ctx.stage_mode)}

def layer_stats(ctx: CalculationContext) -> dict:
  return {"enabled": bool(ctx.layer_mode and ctx.spec_mode)}

def derived_stats(ctx: CalculationContext) -> dict:
  return {"enabled": bool(ctx.derived_mode)}

def material_stats(solids: list, ledger: list) -> dict:
  generic = {r.solid_id for r in ledger if "MATERIAL_GENERIC" in r.warnings}
  return {"generic_elements": len(generic)}

def coverage_stats(elements: list, rejected: list, skipped: dict, unmapped: dict, ledger: list) -> dict:
  ids = {e.id for e in elements}
  measured = len({r.element_id for r in ledger if r.element_id in ids and getattr(r, "source_kind", "MODEL") == "MODEL"})
  not_roled = sum(skipped.values())
  not_mapped = sum(unmapped.values())
  other = max(0, len(ids) - measured - len(rejected) - not_roled - not_mapped)
  
  return {
    "elements": len(ids), "measured": measured, "rejected": len(rejected),
    "skipped_by_role": not_roled, "unmapped": not_mapped, "other_unmeasured": other,
  }

def confidence_stats(ledger: list) -> dict:
  zero = Decimal("0")
  bands = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
  volume = {"HIGH": zero, "MEDIUM": zero, "LOW": zero}
  by_geometry: dict = {}
  
  for r in ledger:
    b = band(r.confidence)
    bands[b] += 1
    inputs = (r.trace or {}).get("inputs") or {}
    if r.unit == Unit.M3.value and r.source_kind == "MODEL":
      volume[b] += r.quantity
      label = inputs.get("geometry_kind") or "UNKNOWN"
      if inputs.get("volume_check"):
        label = f"{label}:{inputs['volume_check']}"
      row = by_geometry.setdefault(label, {"rows": 0, "m3": zero})
      row["rows"] += 1
      row["m3"] += r.quantity
      
  return {
    "rows": len(ledger), "bands": bands,
    "volume_m3": {k: str(q6(v)) for k, v in volume.items()},
    "by_geometry": {k: {"rows": v["rows"], "m3": str(q6(v["m3"]))} for k, v in sorted(by_geometry.items())},
  }

def run(ctx: CalculationContext, elements: list[ModelElement], profile=None) -> CalculationResult:
  accepted, rejected = validate_input(ctx, elements)
  solids, skipped = build_solids(ctx, accepted)
  convention = get_convention(ctx.convention_code)
  if convention is None:
    alloc = AllocationResult.empty()
  else:
    concrete_solids, concrete_elements = split_steel(solids, accepted)
    index = spatial_index(ctx, convention, concrete_solids, concrete_elements)
    alloc = allocate(ctx, convention, concrete_solids, index, find_relations(ctx, index))
  if profile is not None:
    alloc = merge_openings(alloc, apply_openings(ctx, profile, solids, ctx.openings))
    
  ledger, unmapped = measure(ctx, solids, alloc)
  extra_solids, extra_ledger = [], []
  finish_skipped: dict = {}
  rebar_res = None
  if profile is not None:
    for res in (measure_finishes(ctx, profile, ctx.spaces, ctx.openings), schedule_lines_ledger(ctx, ctx.schedule_lines)):
      extra_solids += res.solids
      extra_ledger += res.ledger
      for k, v in res.skipped.items():
        finish_skipped[k] = finish_skipped.get(k, 0) + v
        
    rebar_res = measure_rebar(ctx, profile, solids, ledger, ctx.rebar)
    extra_solids += rebar_res.solids
    extra_ledger += rebar_res.ledger
    
  takeoff_res = None
  stage_info: dict = stage_stats(ctx)
  layer_info: dict = layer_stats(ctx)
  derived_info: dict = derived_stats(ctx)
  if ctx.takeoff is not None:
    takeoff_res = measure_takeoff(ctx, profile, ctx.takeoff, ledger + extra_ledger)
    ledger = apply_replacements(ledger, takeoff_res.dropped_keys)
    extra_ledger = apply_replacements(extra_ledger, takeoff_res.dropped_keys)
    live = {e.solid_id for e in ledger + extra_ledger}
    gone = {sid for sid, _ in takeoff_res.dropped_keys if sid not in live}
    extra_solids = [s for s in extra_solids if s.id not in gone]
    extra_solids += takeoff_res.solids
    extra_ledger += takeoff_res.ledger

  if ctx.layer_mode and ctx.spec_mode:
    layered = split_layers(ctx, accepted, solids, ledger)
    ledger = layered.ledger
    layer_info = layered.stats
  if ctx.stage_mode:
    staged = split_stages(ctx, accepted, solids, alloc, ledger)
    ledger = staged.ledger
    stage_info = staged.stats
  if ctx.derived_mode and profile is not None:
    derived_res = measure_derived(ctx, profile, accepted, solids, ledger)
    extra_solids += derived_res.solids
    extra_ledger += derived_res.ledger
    derived_info = derived_res.stats
  if rebar_res is not None:
    rebar_failures = self_check_rebar(rebar_res.marks, rebar_res.ledger)
    if rebar_failures:
      raise InvariantViolation(rebar_failures)

  stats = {
    **alloc.stats,
    **(rebar_res.stats if rebar_res else {}),
    "rebar_skipped": rebar_res.skipped if rebar_res else {},
    "pdf_takeoff": takeoff_res.stats if takeoff_res else {},
    "skipped_by_role": skipped,
    "wall_material": wall_material_stats(solids, ledger),
    "spec": spec_stats(ctx, ledger),
    "stages": stage_info,
    "layers": layer_info,
    "derived": derived_info,
    "material": material_stats(solids, ledger),
    "coverage": coverage_stats(elements, rejected, skipped, unmapped, ledger),
    "confidence": confidence_stats(ledger + extra_ledger),
    "steel": steel_stats(solids, ledger, rejected),
    "unmapped_by_type": unmapped,
    "rejected": [{"element_id": str(r.element_id), "ifc_type": r.ifc_type, "code": r.code, "message": r.message} for r in rejected],
  }
  return CalculationResult(solids=solids + extra_solids, ledger=ledger + extra_ledger, rejected=rejected,
    skipped_by_role=skipped, unmapped_by_type=unmapped, deductions=alloc.deductions,
    bar_marks=rebar_res.marks if rebar_res else [], stats=stats)