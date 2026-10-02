from __future__ import annotations
from .units import Unit, mm3_to_m3, q4, q6
from decimal import Decimal
from uuid import uuid5
from .geometry import bbox_volume_mm3, extrusion_volume_mm3
from .models import CalculationContext, CalculationResult, LedgerEntry, ModelElement, Rejected, Solid
from .formulas import get_formula

ENGINE_VERSION = "2026.10.1"

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
FORMULA_UNITS = {"SOLID_NET_VOLUME": Unit.M3.value, "OPENING_COUNT": Unit.NOS.value}
LOW_CONFIDENCE_FACTOR = Decimal("0.6")
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
    if el.normalization_status == "INVALID":
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
    if volume_mm3 is None and kind == "BOX_ONLY":
      volume_mm3 = bbox_volume_mm3(el.bbox_min_mm, el.bbox_max_mm)
    if volume_mm3 is None:
      issues.append(_issue("UNSUPPORTED_GEOMETRY", "warning", "No usable volume for this element."))
    else:
      factor = LOW_CONFIDENCE_FACTOR if kind == "BOX_ONLY" else QTO_ONLY_FACTOR
      issues.append(_issue("LOW_CONFIDENCE_GEOMETRY", "warning", f"Volume taken from {kind}; treat as approximate."))
    status = "REVIEW_REQUIRED"
  else:
    issues.append(_issue("UNSUPPORTED_GEOMETRY", "warning", "Geometry kind not measurable in this engine version."))
    status = "REVIEW_REQUIRED"

  gross = mm3_to_m3(volume_mm3) if volume_mm3 is not None else None
  if gross is not None and gross <= 0:
    gross = None
    issues.append(_issue("ZERO_GROSS_VOLUME", "warning", "Gross volume rounds to zero."))
    status = "REVIEW_REQUIRED"

  return Solid(
    id=_solid_id(ctx, el.id), element_id=el.id, ifc_type=el.ifc_type, role=el.role,
    level_id=el.level_id, geometry_kind=kind,
    classification_confidence=el.classification_confidence, confidence_factor=factor,
    gross_volume_m3=gross, status=status, issues=tuple(issues),
  )

def build_solids(ctx: CalculationContext, elements: list[ModelElement]):
  solids: list[Solid] = []
  skipped: dict[str, int] = {}
  for el in elements:
    if el.role in COUNT_ROLES:
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

def measure(ctx: CalculationContext, solids: list[Solid]):
  by_ifc = {m.ifc_type: m for m in ctx.mappings}
  ledger: list[LedgerEntry] = []
  unmapped: dict[str, int] = {}
  for s in solids:
    mapping = by_ifc.get(s.ifc_type)
    if mapping is None or not mapping.work_item_code:
      unmapped[s.ifc_type] = unmapped.get(s.ifc_type, 0) + 1
      continue

    warnings = [i["code"] for i in s.issues if i.get("severity") == "warning"]
    if s.count is not None:
      formula, unit, quantity = "OPENING_COUNT", Unit.NOS.value, Decimal(s.count)
      inputs = {"count": s.count}
      steps = [{"op": "count", "nos": str(s.count)}]
      net = {"nos": str(quantity)}
    elif s.gross_volume_m3 is not None:
      formula, unit, quantity = "SOLID_NET_VOLUME", Unit.M3.value, q6(s.gross_volume_m3)
      inputs = {"geometry_kind": s.geometry_kind}
      steps = [
        {"op": "gross_volume", "m3": str(s.gross_volume_m3)},
        {"op": "allocation", "status": "not_applied", "note": "overlap allocation arrives in Phase 4"},
      ]
      net = {"m3": str(quantity)}
      if s.role.startswith("WALL"):
        warnings.append("OPENINGS_NOT_DEDUCTED")
    else:
      continue
    if quantity <= 0:
      continue

    confidence = q4(min(mapping.confidence_base, s.classification_confidence) * s.confidence_factor)
    confidence = max(Decimal("0"), min(Decimal("1"), confidence))
    ledger.append(LedgerEntry(
      solid_id=s.id, element_id=s.element_id, level_id=s.level_id,
      work_item_code=mapping.work_item_code, quantity=quantity, unit=unit,
      material_grade=s.material_grade, confidence=confidence, formula_code=formula,
      trace={
        "formula_code": formula, "engine_version": ctx.engine_version,
        "convention": ctx.convention_code,
        "rule_set": {"code": ctx.rule_set_code, "version": ctx.rule_set_version},
        "inputs": inputs, "steps": steps, "net": net, "rounding": "half_up,6dp",
      },
      warnings=tuple(warnings),
    ))
  ledger.sort(key=lambda r: (r.work_item_code, str(r.level_id), str(r.element_id)))
  return ledger, dict(sorted(unmapped.items()))

def _expected_unit(formula_code: str) -> str | None:
  spec = get_formula(formula_code)
  if spec is not None:
    return spec.output_unit
  return FORMULA_UNITS.get(formula_code)

def self_check(solids: list[Solid], ledger: list[LedgerEntry]) -> None:
  failures: list[str] = []
  gross = {s.id: s for s in solids}
  seen: set = set()
  for row in ledger:
    solid = gross.get(row.solid_id)
    if solid is None:
      failures.append(f"ledger row references unknown solid {row.solid_id}")
      continue
    if row.quantity < 0:
      failures.append(f"negative quantity on solid {row.solid_id}")
    if _expected_unit(row.formula_code) != row.unit:
      failures.append(f"unit {row.unit} does not match formula {row.formula_code}")
    key = (row.solid_id, row.work_item_code)
    if key in seen:
      failures.append(f"duplicate ledger row for {key}")
    seen.add(key)
    if not row.trace or "formula_code" not in row.trace:
      failures.append(f"missing trace on solid {row.solid_id}")
      
    if row.formula_code == "SOLID_NET_VOLUME" and solid.gross_volume_m3 is not None \
        and row.quantity != q6(solid.gross_volume_m3):
      failures.append(f"net volume != gross volume on solid {row.solid_id}")
  if failures:
    raise InvariantViolation(failures)

def run(ctx: CalculationContext, elements: list[ModelElement]) -> CalculationResult:
  accepted, rejected = validate_input(ctx, elements)
  solids, skipped = build_solids(ctx, accepted)
  ledger, unmapped = measure(ctx, solids)
  self_check(solids, ledger)
  return CalculationResult(solids=solids, ledger=ledger, rejected=rejected,
    skipped_by_role=skipped, unmapped_by_type=unmapped)