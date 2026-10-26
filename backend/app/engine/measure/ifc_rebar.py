from __future__ import annotations
from decimal import Decimal
from dataclasses import dataclass, field
from app.engine.measure.steel import STEEL_DENSITY_KG_M3, STEEL_MAPPING_CONFIDENCE, STEEL_UNCERTAIN_FACTOR
from app.engine.measure.models import LedgerEntry, Rejected, Solid
from uuid import uuid5
from app.engine.measure.rebar import REBAR_WORK_ITEM, role_family
from app.engine.measure.units import q4, q6

ZERO, ONE = Decimal("0"), Decimal("1")
PI = Decimal("3.14159265358979323846")
MM3_PER_M3 = Decimal("1000000000")

FORMULA_IFC_BAR = "IFC_BAR_WEIGHT"
IFC_BAR_FORMULA_UNITS = {FORMULA_IFC_BAR: "kg"}
NO_DIAMETER, NO_LENGTH = "IFC_BAR_NO_DIAMETER", "IFC_BAR_NO_LENGTH"
DERIVED_SOURCES = ("CrossSectionArea", "SweptDisk", "Directrix")

@dataclass(frozen=True)
class IfcBarResult:
  solids: list = field(default_factory=list)
  ledger: list = field(default_factory=list)
  rejected: list = field(default_factory=list)
  hosts: frozenset = frozenset()
  stats: dict = field(default_factory=dict)

def _dec(value) -> Decimal | None:
  try:
    number = Decimal(repr(float(value)))
  except Exception:
    return None
  return number if number > ZERO else None

def bar_weight_kg(dia_mm: Decimal, length_mm: Decimal) -> Decimal:
  return q6(PI * dia_mm * dia_mm / 4 * length_mm / MM3_PER_M3 * STEEL_DENSITY_KG_M3)

def measure_ifc_bars(ctx, elements: list, tolerance: float) -> IfcBarResult:
  bars = [e for e in elements if e.role == "REBAR"]
  read = [e for e in bars if getattr(e, "rebar", None)]
  by_gid = {e.ifc_global_id: e for e in elements if e.ifc_global_id}
  tol = Decimal(repr(float(tolerance)))

  solids: list = []
  ledger: list = []
  rejected: list = []
  hosts: set = set()
  total_kg = total_len = ZERO
  by_dia: dict = {}
  by_family: dict = {}
  flags = {"no_host": 0, "length_from_geometry": 0, "diameter_derived": 0, "area_mismatch": 0, "file_weight_mismatch": 0}
  file_bars = 0
  file_kg = same_bars_kg = ZERO

  for el in sorted(read, key=lambda e: str(e.id)):
    rb = el.rebar
    dia, length = _dec(rb.get("dia_mm")), _dec(rb.get("length_mm"))
    if dia is None:
      rejected.append(Rejected(el.id, el.ifc_type, NO_DIAMETER, "The bar gives no diameter (NominalDiameter, a property set value or a cross-section area); not weighed."))
      continue
    if length is None:
      rejected.append(Rejected(el.id, el.ifc_type, NO_LENGTH, "The bar gives no length (BarLength, a property or quantity value, or a centre line that can be measured); not weighed."))
      continue

    dia, length = q6(dia), q6(length)
    kg = bar_weight_kg(dia, length)
    area = q6(PI * dia * dia / 4)
    length_m = q6(length / 1000)
    dia_source, length_source = rb.get("dia_source"), rb.get("length_source")
    derived = dia_source in DERIVED_SOURCES or length_source in DERIVED_SOURCES
    factor = STEEL_UNCERTAIN_FACTOR if derived else ONE
    confidence = q4(max(ZERO, min(ONE, min(STEEL_MAPPING_CONFIDENCE, el.classification_confidence) * factor)))

    host = by_gid.get(rb.get("host_global_id")) if rb.get("host_global_id") else None
    family = role_family(host.role) if host is not None else None
    level_id = el.level_id or (host.level_id if host is not None else None)
    if host is not None:
      hosts.add(host.id)
    else:
      flags["no_host"] += 1

    warnings: list = []
    if length_source == "Directrix":
      warnings.append("IFC_BAR_LENGTH_FROM_GEOMETRY")
      flags["length_from_geometry"] += 1
    if dia_source in ("CrossSectionArea", "SweptDisk"):
      warnings.append("IFC_BAR_DIAMETER_DERIVED")
      flags["diameter_derived"] += 1
    if host is None:
      warnings.append("IFC_BAR_NO_HOST")
    given_area = _dec(rb.get("area_mm2"))
    if given_area is not None and dia_source == "NominalDiameter" and abs(given_area - area) / area > tol:
      warnings.append("IFC_BAR_AREA_MISMATCH")
      flags["area_mismatch"] += 1
    given_kg = _dec(rb.get("file_kg"))
    if given_kg is not None:
      file_bars += 1
      file_kg += given_kg
      same_bars_kg += kg
      if abs(given_kg - kg) / given_kg > tol:
        warnings.append("IFC_BAR_FILE_WEIGHT_MISMATCH")
        flags["file_weight_mismatch"] += 1

    solid = Solid(
      id=uuid5(ctx.run_id, f"solid|ifc-bar|{el.id}"), element_id=el.id, ifc_type=el.ifc_type, role="REBAR", level_id=level_id,
      geometry_kind=el.geometry_kind or "QTO_ONLY", classification_confidence=el.classification_confidence, confidence_factor=factor,
      component_type="REBAR", material_grade=rb.get("grade"), gross_length_m=length_m, count=1)
    inputs = {
      "dia_mm": str(q6(dia)), "dia_source": dia_source, "length_mm": str(q6(length)), "length_source": length_source,
      "density_kg_m3": str(STEEL_DENSITY_KG_M3), "grade": rb.get("grade"),
      "host": {"element_id": str(host.id), "global_id": host.ifc_global_id, "name": host.name or rb.get("host_name"), "role": host.role,
        "family": family} if host is not None else None,
      "file_kg": str(q6(given_kg)) if given_kg is not None else None, "file_kg_source": rb.get("file_kg_source") if given_kg is not None else None,
    }
    if length_source != "Directrix":
      inputs["geometry_kind"] = "QTO_ONLY"
    if rb.get("parts"):
      inputs["parts"] = rb["parts"]
    steps = [
      {"op": "bar_diameter", "mm": str(q6(dia))}, {"op": "bar_length", "mm": str(q6(length))}, {"op": "section_area", "mm2": str(area)},
      {"op": "density", "kg_per_m3": str(STEEL_DENSITY_KG_M3)}, {"op": "weight", "kg": str(kg)},
      {"op": "bar_mark", "mark": el.name or str(el.id)[:8], "dia_mm": str(q6(dia)), "kg": str(kg), "length_m": str(length_m)},
    ]
    solids.append(solid)
    ledger.append(LedgerEntry(
      solid_id=solid.id, element_id=el.id, level_id=level_id, work_item_code=REBAR_WORK_ITEM, quantity=kg, unit="kg",
      material_grade=rb.get("grade"), confidence=confidence, formula_code=FORMULA_IFC_BAR,
      trace={"engine_version": ctx.engine_version, "convention": ctx.convention_code, "rule_set": {"code": ctx.rule_set_code, "version": ctx.rule_set_version},
        "rounding": "half_up,6dp", "formula_code": FORMULA_IFC_BAR, "inputs": inputs, "steps": steps, "net": {"kg": str(kg)}},
      warnings=tuple(dict.fromkeys(warnings))))
    total_kg += kg
    total_len += length_m
    key = f"{dia.normalize():f}"
    slot = by_dia.setdefault(key, {"bars": 0, "kg": ZERO, "length_m": ZERO})
    slot["bars"] += 1; slot["kg"] += kg; slot["length_m"] += length_m
    fam = family or "NO_HOST"
    by_family[fam] = by_family.get(fam, ZERO) + kg

  stats = {
    "bars": len(bars), "bars_without_data": len(bars) - len(read), "measured": len(ledger),
    "no_diameter": sum(1 for r in rejected if r.code == NO_DIAMETER), "no_length": sum(1 for r in rejected if r.code == NO_LENGTH),
    "kg": str(q6(total_kg)), "tonnes": str(q4(total_kg / 1000)), "length_m": str(q6(total_len)), "hosts": len(hosts),
    "by_dia": {k: {"bars": v["bars"], "kg": str(q6(v["kg"])), "length_m": str(q6(v["length_m"]))} for k, v in sorted(by_dia.items(), key=lambda kv: Decimal(kv[0]))},
    "by_family_kg": {k: str(q6(v)) for k, v in sorted(by_family.items())},
    **flags,
    "file_weight": {
      "bars": file_bars, "file_kg": str(q6(file_kg)), "computed_kg": str(q6(same_bars_kg)),
      "difference_pct": str(q4((same_bars_kg - file_kg) / file_kg * 100)) if file_kg > ZERO else None,
    },
  }
  return IfcBarResult(solids=solids, ledger=ledger, rejected=rejected, hosts=frozenset(hosts), stats=stats)

def ifc_bar_check(solids: list, ledger: list) -> list[str]:
  by_id = {s.id: s for s in solids}
  failures: list[str] = []

  for r in ledger:
    if r.formula_code != FORMULA_IFC_BAR:
      continue
    s = by_id.get(r.solid_id)
    if s is None:
      failures.append(f"IFC bar row has no solid ({r.solid_id})")
      continue
    inputs = (r.trace or {}).get("inputs") or {}
    try:
      expected = bar_weight_kg(Decimal(inputs["dia_mm"]), Decimal(inputs["length_mm"]))
    except Exception:
      failures.append(f"IFC bar row {r.solid_id} has no diameter and length in its trace")
      continue
    if r.unit != "kg" or r.work_item_code != REBAR_WORK_ITEM:
      failures.append(f"IFC bar row {r.solid_id} is not steel in kg")
    elif abs(r.quantity - expected) > Decimal("0.000004"):
      failures.append(f"IFC bar weight {r.quantity} != {expected} from its diameter and length on solid {r.solid_id}")
  return failures
