from __future__ import annotations
from decimal import Decimal
from app.engine.measure.units import Unit, q4, q6
import re
from app.engine.measure.material import wall_material_class
import math
from app.engine.measure.models import ModelElement, LedgerEntry, Solid

STEEL = "STEEL"
STEEL_DENSITY_KG_M3 = Decimal("7850")
STEEL_SECTION_CODE = "STL-STRUCT"
STEEL_PILE_CODE = "STL-PILE"
FORMULA_STEEL_WEIGHT = "STEEL_WEIGHT_FROM_VOLUME"
FORMULA_PILE_LENGTH = "STEEL_PILE_LENGTH"
STEEL_FORMULA_UNITS = {FORMULA_STEEL_WEIGHT: Unit.KG.value, FORMULA_PILE_LENGTH: Unit.M.value}
STEEL_MAPPING_CONFIDENCE = Decimal("0.9")
STEEL_BBOX_FACTOR = Decimal("0.85")
STEEL_UNCERTAIN_FACTOR = Decimal("0.8")
STEEL_SOLID_PROFILE_FACTOR = Decimal("0.7")
SOLID_PROFILE_MIN_DIM_MM = 60
HEAVY_SECTION_KG_PER_M = Decimal("800")
STEEL_REJECTED_CODE = "STEEL_NO_QUANTITY"

STEEL_ROLE_PREFIXES = ("COLUMN", "BEAM", "EDGE_BEAM", "GIRDER", "PILE", "MEMBER", "PLATE", "LINTEL")

_STEEL_TEXT = re.compile(r"\bsteel\b|\b(UB|UC|PFC|RHS|SHS|CHS|IPE|HEA|HEB)\s?\d{2,4}", re.I)
_METAL_TEXT = re.compile(r"\b(metal|iron)\b", re.I)
UNCERTAIN_BASES = ("METAL_TEXT", "NAME_ONLY")

def _role(role: str | None) -> str:
  return (role or "").strip().upper()

def is_pile(role: str | None) -> bool:
  r = _role(role)
  return r.startswith("PILE") and not r.startswith("PILE_CAP")

def is_steel_role(role: str | None) -> bool:
  r = _role(role)
  return r.startswith(STEEL_ROLE_PREFIXES) and not r.startswith("PILE_CAP")

def is_plate(role: str | None) -> bool:
  r = _role(role)
  return r.startswith("PLATE") or r.endswith("_PLATE")

def element_material_class(role: str | None, raw_material_text: str | None, material_family: str | None) -> str | None:
  if (material_family or "").strip().upper() == STEEL and is_steel_role(role):
    return STEEL
  return wall_material_class(role, raw_material_text)

def steel_material_basis(role: str | None, raw_material_text: str | None, material_family: str | None) -> str | None:
  if element_material_class(role, raw_material_text, material_family) != STEEL:
    return None
  text = raw_material_text or ""
  if _STEEL_TEXT.search(text):
    return "STEEL_TEXT"
  if _METAL_TEXT.search(text):
    return "METAL_TEXT"
  return "NAME_ONLY"

def _f(value) -> float | None:
  try:
    number = float(value)
  except (TypeError, ValueError):
    return None
  return number if math.isfinite(number) else None

def _positive_finite(value) -> bool:
  try:
    d = Decimal(value)
    return d.is_finite() and d > 0
  except Exception:
    return False

def _bbox_sides(el: ModelElement) -> list[float]:
  lo, hi = el.bbox_min_mm, el.bbox_max_mm
  if not (lo and hi):
    return []
  sides = []
  for l, h in zip(lo, hi):
    fl, fh = _f(l), _f(h)
    if fl is not None and fh is not None:
      sides.append(abs(fh - fl))
  return sorted(sides, reverse=True)

def steel_length_mm(el: ModelElement) -> float | None:
  depth = _f((el.placement or {}).get("depth_mm"))
  if depth and depth > 0:
    return depth
  sides = _bbox_sides(el)
  if sides and sides[0] > 0:
    return sides[0]
  return None

def steel_member_length_mm(el: ModelElement) -> float | None:
  depth = _f((el.placement or {}).get("depth_mm"))
  if depth and depth > 0:
    return depth
  sides = _bbox_sides(el)
  if not sides or sides[0] <= 0:
    return None
  if len(sides) >= 3 and sides[2] > 0 and sides[1] > 2 * sides[2]:
    return math.hypot(sides[0], sides[1])
  return sides[0]

def steel_recoverable(el: ModelElement) -> bool:
  if el.material_class != STEEL or not is_steel_role(el.role):
    return False
  if is_pile(el.role):
    return (steel_length_mm(el) or 0) > 0
  return _positive_finite(el.volume_mm3)

def solid_profile_suspected(el: ModelElement) -> bool:
  if is_pile(el.role) or is_plate(el.role) or el.geometry_kind != "EXTRUDED_PROFILE":
    return False
  p = el.profile or {}
  kind = p.get("kind")
  if kind == "RECT":
    x, y = _f(p.get("x_dim")), _f(p.get("y_dim"))
    return x is not None and y is not None and min(x, y) >= SOLID_PROFILE_MIN_DIM_MM
  if kind == "CIRCLE":
    r = _f(p.get("radius"))
    return r is not None and 2 * r >= SOLID_PROFILE_MIN_DIM_MM
  return False

def steel_duplicate_ids(elements: list[ModelElement]) -> set:
  seen: dict = {}
  dups: set = set()
  for el in sorted((e for e in elements if e.material_class == STEEL and is_steel_role(e.role)), key=lambda e: str(e.id)):
    coords = [_f(v) for v in (*(el.bbox_min_mm or ()), *(el.bbox_max_mm or ()))]
    if len(coords) != 6 or any(c is None for c in coords):
      continue
    volume = round(float(el.volume_mm3) / 1000) if _positive_finite(el.volume_mm3) else None
    key = (el.ifc_type, _role(el.role), tuple(round(c) for c in coords), volume)
    if key in seen:
      dups.add(el.id)
    else:
      seen[key] = el.id
  return dups

def split_steel(solids: list[Solid], elements: list[ModelElement]):
  steel_elements = {s.element_id for s in solids if s.material_class == STEEL}
  return ([s for s in solids if s.material_class != STEEL],
    [e for e in elements if e.id not in steel_elements])

def measure_steel(ctx, solids: list[Solid]) -> list[LedgerEntry]:
  ledger: list[LedgerEntry] = []
  for s in sorted((x for x in solids if x.material_class == STEEL), key=lambda x: (x.role, str(x.level_id), str(x.element_id))):
    confidence = q4(max(Decimal("0"), min(Decimal("1"), min(STEEL_MAPPING_CONFIDENCE, s.classification_confidence) * s.confidence_factor)))
    warnings = [i["code"] for i in s.issues if i.get("severity") == "warning"]
    base_trace = {"engine_version": ctx.engine_version, "convention": ctx.convention_code,
      "rule_set": {"code": ctx.rule_set_code, "version": ctx.rule_set_version}, "rounding": "half_up,6dp"}

    if is_pile(s.role):
      if s.gross_length_m is None or s.gross_length_m <= 0:
        continue
      length = q6(s.gross_length_m)
      ledger.append(LedgerEntry(
        solid_id=s.id, element_id=s.element_id, level_id=s.level_id, work_item_code=STEEL_PILE_CODE,
        quantity=length, unit=Unit.M.value, material_grade=None, confidence=confidence, formula_code=FORMULA_PILE_LENGTH,
        trace={**base_trace, "formula_code": FORMULA_PILE_LENGTH,
          "inputs": {"geometry_kind": s.geometry_kind, "piles": 1,
            "note": "Billed by driven length. The model draws a pipe pile as a solid cylinder, so no weight is taken from its volume."},
          "steps": [{"op": "pile_length", "m": str(length)}], "net": {"m": str(length), "nos": "1"}},
        warnings=tuple(dict.fromkeys([*warnings, "PILE_WEIGHT_NOT_COMPUTED"]))))
      continue

    if s.gross_volume_m3 is None or s.gross_volume_m3 <= 0:
      continue
    volume = q6(s.gross_volume_m3)
    kg = q6(volume * STEEL_DENSITY_KG_M3)
    steps = [{"op": "model_volume", "m3": str(volume)}, {"op": "density", "kg_per_m3": str(STEEL_DENSITY_KG_M3)},
      {"op": "weight", "kg": str(kg)}]
    inputs = {"geometry_kind": s.geometry_kind, "gross_m3": str(volume), "density_kg_m3": str(STEEL_DENSITY_KG_M3)}
    
    if s.gross_length_m and s.gross_length_m > 0:
      inputs["length_m"] = str(q6(s.gross_length_m))
      if not is_plate(s.role):
        per_metre = kg / s.gross_length_m
        steps.append({"op": "kg_per_metre", "kg_m": str(q4(per_metre))})
        if per_metre > HEAVY_SECTION_KG_PER_M:
          warnings.append("STEEL_SOLID_SECTION_SUSPECTED")
          
    ledger.append(LedgerEntry(
      solid_id=s.id, element_id=s.element_id, level_id=s.level_id, work_item_code=STEEL_SECTION_CODE,
      quantity=kg, unit=Unit.KG.value, material_grade=None, confidence=confidence, formula_code=FORMULA_STEEL_WEIGHT,
      trace={**base_trace, "formula_code": FORMULA_STEEL_WEIGHT, "inputs": inputs, "steps": steps, "net": {"kg": str(kg)}},
      warnings=tuple(dict.fromkeys(warnings))))
  return ledger

def steel_check(solids: list[Solid], ledger: list[LedgerEntry]) -> list[str]:
 
  by_id = {s.id: s for s in solids}
  failures: list[str] = []
  for r in ledger:
    if r.work_item_code not in (STEEL_SECTION_CODE, STEEL_PILE_CODE):
      continue
    s = by_id.get(r.solid_id)
    if s is None or s.material_class != STEEL:
      failures.append(f"steel row {r.work_item_code} on a solid that is not steel ({r.solid_id})")
      continue
  
    if r.work_item_code == STEEL_SECTION_CODE:
      expected = q6(q6(s.gross_volume_m3 or Decimal("0")) * STEEL_DENSITY_KG_M3)
      ok = r.formula_code == FORMULA_STEEL_WEIGHT and r.unit == Unit.KG.value
    else:
      expected = q6(s.gross_length_m or Decimal("0"))
      ok = r.formula_code == FORMULA_PILE_LENGTH and r.unit == Unit.M.value
    if not ok:
      failures.append(f"steel row {r.work_item_code} has the wrong formula or unit on solid {r.solid_id}")
    elif r.quantity != expected:
      failures.append(f"steel quantity {r.quantity} != {expected} on solid {r.solid_id}")
  return failures

def steel_stats(solids: list[Solid], ledger: list[LedgerEntry], rejected=()) -> dict:
  steel_solids = [s for s in solids if s.material_class == STEEL]
  rejected_steel = sum(1 for r in rejected if getattr(r, "code", None) == STEEL_REJECTED_CODE)
  rows = [r for r in ledger if r.work_item_code in (STEEL_SECTION_CODE, STEEL_PILE_CODE)]
  by_solid = {s.id: s for s in steel_solids}
  sections = [r for r in rows if r.work_item_code == STEEL_SECTION_CODE]
  piles = [r for r in rows if r.work_item_code == STEEL_PILE_CODE]
  by_role: dict = {}

  for r in sections:
    role = by_solid[r.solid_id].role if r.solid_id in by_solid else "UNKNOWN"
    entry = by_role.setdefault(role, {"count": 0, "kg": Decimal("0")})
    entry["count"] += 1
    entry["kg"] += r.quantity
  total_kg = q6(sum((r.quantity for r in sections), Decimal("0")))

  def flagged(code: str) -> int:
    return sum(1 for r in rows if code in r.warnings)

  return {
    "elements": len(steel_solids) + rejected_steel,
    "measured": len(rows),
    "not_measured": len(steel_solids) - len(rows) + rejected_steel,
    "sections_kg": str(total_kg),
    "sections_tonnes": str(q4(total_kg / 1000)),
    "by_role": {k: {"count": v["count"], "kg": str(q6(v["kg"]))} for k, v in sorted(by_role.items())},
    "piles": len(piles),
    "pile_length_m": str(q6(sum((r.quantity for r in piles), Decimal("0")))),
    "suspected_solid_sections": flagged("STEEL_SOLID_SECTION_SUSPECTED"),
    "duplicates_suspected": flagged("STEEL_DUPLICATE_SUSPECTED"),
    "uncertain_material": flagged("STEEL_MATERIAL_UNCERTAIN"),
    "density_kg_m3": str(STEEL_DENSITY_KG_M3),
  }