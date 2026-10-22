from __future__ import annotations
from decimal import Decimal
from dataclasses import dataclass, field
from app.engine.measure.takeoff import SOURCE_KIND as PDF_SOURCE
from app.engine.measure.models import CalculationContext, Solid, LedgerEntry
from app.engine.measure.derived import DERIVED, FACTOR_CONFIRMED, resolve_params
from uuid import uuid5
from app.engine.measure.units import q6, q4

PARAM = "plaster_thickness_mm"
CODE = "FIN-PLASTER-MORTAR"
SOURCE_CODES = ("FIN-PLASTER", "FIN-PLASTER-EXT")
FORMULA = "PLASTER_MORTAR_VOLUME"
RECIPE = "PLASTER_MORTAR_FROM_AREA"
MM_PER_M = Decimal("1000")
SOURCE_KINDS = ("MODEL", PDF_SOURCE, DERIVED)

@dataclass(frozen=True)
class PlasterMortarResult:
  solids: list = field(default_factory=list)
  ledger: list = field(default_factory=list)
  stats: dict = field(default_factory=dict)

def _taken(ledger: list, extra_ledger) -> bool:
  return any(r.work_item_code == CODE and r.quantity > 0 and getattr(r, "source_kind", None) in ("MODEL", PDF_SOURCE) for r in list(ledger) + list(extra_ledger or ()))

def _sources(ledger: list, extra_ledger) -> list:
  rows = [r for r in list(ledger) + list(extra_ledger or ()) if r.work_item_code in SOURCE_CODES and r.unit == "m2" and r.quantity > 0 and getattr(r, "source_kind", "MODEL") in SOURCE_KINDS]
  return sorted(rows, key=lambda r: (r.work_item_code, str(r.level_id), str(r.solid_id), str(r.quantity)))

def measure_plaster_mortar(ctx: CalculationContext, ledger: list, extra_ledger=()) -> PlasterMortarResult:
  p = resolve_params(ctx)[PARAM]
  thickness = Decimal(repr(float(p["value"])))
  stats: dict = {"enabled": thickness > 0, "ran": False, "thickness_mm": str(thickness) if thickness > 0 else None, "thickness_source": p["source"]}
  
  if thickness <= 0:
    stats["reason"] = "NO_THICKNESS"
    return PlasterMortarResult(stats=stats)
  if _taken(ledger, extra_ledger):
    stats["reason"] = "ALREADY_MEASURED"
    return PlasterMortarResult(stats=stats)
  sources = _sources(ledger, extra_ledger)
  if not sources:
    stats["reason"] = "NO_PLASTER"
    return PlasterMortarResult(stats=stats)
  solids: list = []
  rows: list = []
  seen: dict = {}
  by_code: dict = {c: {"m2": Decimal("0"), "m3": Decimal("0")} for c in SOURCE_CODES}
  for src in sources:
    n = seen.get((src.work_item_code, src.solid_id), 0)
    seen[(src.work_item_code, src.solid_id)] = n + 1
    area = q6(Decimal(src.quantity))
    quantity = q6(area * thickness / MM_PER_M)
    if quantity <= 0:
      continue
  
    spec = {"kind": DERIVED, "recipe": RECIPE, "item": "PLASTER_MORTAR", "params": {PARAM: float(thickness)}, "basis": {PARAM: p["source"]}}
    solid = Solid(id=uuid5(ctx.run_id, f"solid|plastermortar|{src.work_item_code}|{src.solid_id}|{n}"), element_id=src.element_id, ifc_type="IfcCovering", role="PLASTER_MORTAR",
      level_id=src.level_id, geometry_kind="QTO_ONLY", classification_confidence=Decimal("1"), confidence_factor=FACTOR_CONFIRMED, component_type="DERIVED_PLASTER_MORTAR",
      gross_volume_m3=quantity, status="OK")
    steps = [{"op": "plaster_area", "m2": str(area), "note": f"the {src.work_item_code} row this mortar sits behind"},
      {"op": "plaster_thickness", "mm": str(thickness), "source": p["source"]}, {"op": "net_volume", "m3": str(quantity)}]
    rows.append(LedgerEntry(solid_id=solid.id, element_id=src.element_id, level_id=src.level_id, work_item_code=CODE, quantity=quantity, unit="m3", material_grade=None,
      confidence=q4(min(Decimal(src.confidence), Decimal("1")) * FACTOR_CONFIRMED), formula_code=FORMULA,
      trace={"formula_code": FORMULA, "engine_version": ctx.engine_version, "convention": ctx.convention_code,
        "rule_set": {"code": ctx.rule_set_code, "version": ctx.rule_set_version},
        "inputs": {"recipe": RECIPE, "spec": spec, "plaster_area_m2": str(area), "thickness_mm": str(thickness), "thickness_source": p["source"], "source_work_item": src.work_item_code,
          "source_kind": getattr(src, "source_kind", None)}, "steps": steps, "net": {"m3": str(quantity)}, "rounding": "half_up,6dp"},
      warnings=(), source_kind=DERIVED, spec=spec, spec_key="derived"))
    
    solids.append(solid)
    by_code[src.work_item_code]["m2"] += area
    by_code[src.work_item_code]["m3"] += quantity
  total = sum((v["m3"] for v in by_code.values()), Decimal("0"))
  stats.update({"ran": bool(rows), "rows": len(rows), "plaster_rows": len(sources), "mortar_m3": str(q6(total)),
    "by_item": {c: {"area_m2": str(q6(v["m2"])), "mortar_m3": str(q6(v["m3"]))} for c, v in by_code.items() if v["m2"] > 0}})
  if not rows:
    stats["reason"] = "NOTHING_TO_MEASURE"
  return PlasterMortarResult(solids=solids, ledger=rows, stats=stats)

def plaster_mortar_check(solids: list, ledger: list) -> list:
  ids = {s.id for s in solids}
  out: list = []
  
  for r in ledger:
    if r.formula_code != FORMULA:
      continue
    if r.solid_id not in ids:
      out.append(f"{r.work_item_code}: plaster mortar row has no solid")
    if r.unit != "m3" or r.quantity <= 0:
      out.append(f"{r.work_item_code}: plaster mortar quantity {r.quantity} {r.unit}")
    if r.source_kind != DERIVED:
      out.append(f"{r.work_item_code}: plaster mortar row is not a derived row")
    inputs = (r.trace or {}).get("inputs") or {}
    try:
      expect = q6(Decimal(inputs["plaster_area_m2"]) * Decimal(inputs["thickness_mm"]) / MM_PER_M)
    except Exception:
      out.append(f"{r.work_item_code}: plaster mortar row has no area and thickness in its trace")
      continue
    if abs(expect - r.quantity) > Decimal("0.000004"):
      out.append(f"{r.work_item_code}: plaster mortar != area x thickness")
  return out
