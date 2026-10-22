from __future__ import annotations
from decimal import Decimal, InvalidOperation
import re
from dataclasses import dataclass, field
from app.engine.measure.derived import resolve_params, DERIVED, FACTOR_ASSUMED
from uuid import uuid5
from app.engine.measure.models import CalculationContext, LedgerEntry, Solid
from app.engine.measure.takeoff import SOURCE_KIND as PDF_SOURCE
from app.engine.measure.units import q6, q4

SWITCH, DEPTH, CEMENT = "soil_stabilisation", "soil_stab_depth_mm", "soil_stab_cement_pct"
CODE = "EXC-SOIL-STAB"
FILL_CODE = "EXC-FILL"
FORMULA = "SOIL_STABILISATION_VOLUME"
RECIPE = "SOIL_STABILISATION_UNDER_FLOOR"
ASSUMED = "SOIL_STAB_AREA_ASSUMED"
MM_PER_M = Decimal("1000")
_DIMS = re.compile(r"^\s*(?P<l>[\d.]+)\s*x\s*(?P<w>[\d.]+)\s*x\s*(?P<d>[\d.]+)\s*$")

@dataclass(frozen=True)
class SoilStabResult:
  solids: list = field(default_factory=list)
  ledger: list = field(default_factory=list)
  stats: dict = field(default_factory=dict)

def fill_area_m2(row) -> Decimal | None:
  for st in (row.trace or {}).get("steps") or []:
    if isinstance(st, dict) and st.get("op") == "multiply" and "length_mm" in str(st.get("by")) and "depth_mm" in str(st.get("by")):
      m = _DIMS.match(str(st.get("value") or ""))
      if not m:
        return None
      try:
        return q6(Decimal(m.group("l")) * Decimal(m.group("w")) / Decimal("1000000"))
      except (InvalidOperation, ValueError):
        return None
  return None

def measure_soil_stabilisation(ctx: CalculationContext, ledger: list, extra_ledger=()) -> SoilStabResult:
  params = resolve_params(ctx)
  on = params[SWITCH]["value"] >= 0.5
  depth = Decimal(repr(float(params[DEPTH]["value"])))
  cement = float(params[CEMENT]["value"])
  stats: dict = {"enabled": on, "ran": False, "switch_source": params[SWITCH]["source"], "depth_mm": str(depth) if depth > 0 else None, "depth_source": params[DEPTH]["source"],
    "cement_pct": cement if cement > 0 else None, "cement_source": params[CEMENT]["source"]}
  
  if not on:
    stats["reason"] = "SWITCHED_OFF"
    return SoilStabResult(stats=stats)
  rows_all = list(ledger) + list(extra_ledger or ())
  if any(r.work_item_code == CODE and r.quantity > 0 and getattr(r, "source_kind", None) in ("MODEL", PDF_SOURCE) for r in rows_all):
    stats["reason"] = "ALREADY_MEASURED"
    return SoilStabResult(stats=stats)
  if depth <= 0:
    stats["reason"] = "DEPTH_NOT_GIVEN"
    return SoilStabResult(stats=stats)
  fills = sorted((r for r in rows_all if r.work_item_code == FILL_CODE and r.unit == "m3" and r.quantity > 0 and getattr(r, "source_kind", None) == PDF_SOURCE),
    key=lambda r: (str(r.level_id), str(r.solid_id), str(r.quantity)))
  if not fills:
    stats["reason"] = "NO_FILLING"
    return SoilStabResult(stats=stats)
  solids: list = []
  rows: list = []
  
  skipped = 0
  area_total = Decimal("0")
  for n, src in enumerate(fills):
    area = fill_area_m2(src)
    if area is None or area <= 0:
      skipped += 1
      continue
    quantity = q6(area * depth / MM_PER_M)
    if quantity <= 0:
      continue
  
    spec = {"kind": DERIVED, "recipe": RECIPE, "item": "SOIL_STABILISATION", "params": {DEPTH: float(depth), **({CEMENT: cement} if cement > 0 else {})},
      "basis": {DEPTH: params[DEPTH]["source"], "stabilised_area": "default", **({CEMENT: params[CEMENT]["source"]} if cement > 0 else {})}}
    solid = Solid(id=uuid5(ctx.run_id, f"solid|soilstab|{src.solid_id}|{n}"), element_id=src.element_id, ifc_type="IfcEarthworksFill", role="SOIL_STABILISATION", level_id=src.level_id,
      geometry_kind="QTO_ONLY", classification_confidence=Decimal("1"), confidence_factor=FACTOR_ASSUMED, component_type="DERIVED_SOIL_STAB", gross_volume_m3=quantity, status="REVIEW_REQUIRED")
    steps = [{"op": "fill_area", "m2": str(area), "note": "the floor area of the earth-filling row this layer sits under"}, {"op": "layer_depth", "mm": str(depth), "source": params[DEPTH]["source"]},
      {"op": "net_volume", "m3": str(quantity)}]
    
    rows.append(LedgerEntry(solid_id=solid.id, element_id=src.element_id, level_id=src.level_id, work_item_code=CODE, quantity=quantity, unit="m3", material_grade=None,
      confidence=q4(min(Decimal(src.confidence), Decimal("1")) * FACTOR_ASSUMED), formula_code=FORMULA,
      trace={"formula_code": FORMULA, "engine_version": ctx.engine_version, "convention": ctx.convention_code, "rule_set": {"code": ctx.rule_set_code, "version": ctx.rule_set_version},
        "inputs": {"recipe": RECIPE, "spec": spec, "fill_area_m2": str(area), "depth_mm": str(depth), "cement_pct": cement if cement > 0 else None, "source_work_item": FILL_CODE},
        "steps": steps, "net": {"m3": str(quantity)}, "rounding": "half_up,6dp"},
      warnings=(ASSUMED,), source_kind=DERIVED, spec=spec, spec_key="derived"))
    
    solids.append(solid)
    area_total += area
  stats.update({"ran": bool(rows), "rows": len(rows), "fill_rows": len(fills), "skipped_no_area": skipped, "area_m2": str(q6(area_total)),
    "volume_m3": str(q6(sum((r.quantity for r in rows), Decimal("0"))))})
  if not rows:
    stats["reason"] = "NOTHING_TO_MEASURE"
  return SoilStabResult(solids=solids, ledger=rows, stats=stats)

def soil_stabilisation_check(solids: list, ledger: list) -> list:
  ids = {s.id for s in solids}
  out: list = []
  
  for r in ledger:
    if r.formula_code != FORMULA:
      continue
    if r.solid_id not in ids:
      out.append(f"{r.work_item_code}: soil stabilisation row has no solid")
    if r.unit != "m3" or r.quantity <= 0:
      out.append(f"{r.work_item_code}: soil stabilisation quantity {r.quantity} {r.unit}")
    if r.source_kind != DERIVED:
      out.append(f"{r.work_item_code}: soil stabilisation row is not a derived row")
    if ASSUMED not in (r.warnings or ()):
      out.append(f"{r.work_item_code}: soil stabilisation row is not flagged as assumed")
    inputs = (r.trace or {}).get("inputs") or {}
    try:
      expect = q6(Decimal(inputs["fill_area_m2"]) * Decimal(inputs["depth_mm"]) / MM_PER_M)
    except Exception:
      out.append(f"{r.work_item_code}: soil stabilisation row has no area and depth in its trace")
      continue
    if abs(expect - r.quantity) > Decimal("0.000004"):
      out.append(f"{r.work_item_code}: soil stabilisation != area x depth")
  return out
