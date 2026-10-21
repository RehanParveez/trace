from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from app.engine.measure.rebar import REBAR_WORK_ITEM
from app.engine.measure.models import Solid, CalculationContext, LedgerEntry
from uuid import uuid5
from app.engine.measure.units import q6, q4
from app.engine.measure.derived import BINDING_WIRE_FORMULA, CHAIRS_FORMULA, DERIVED, FACTOR_ASSUMED, resolve_params

SWITCH_WIRE, PARAM_WIRE_PCT = "steel_binding_wire", "steel_binding_wire_pct"
SWITCH_CHAIRS, PARAM_CHAIRS = "steel_chairs", "steel_chairs_kg_per_m2"
WIRE_CODE, CHAIRS_CODE = "STL-BINDING-WIRE", "STL-CHAIRS"
RECIPE = "STEEL_ALLOWANCE"
ASSUMED = "STEEL_ALLOWANCE_ASSUMED"
SLAB_CATEGORIES = ("SLAB", "CHAJJA", "BALCONY_SLAB")
MM2_PER_M2 = Decimal("1000000")
TOLERANCE = Decimal("0.000004")
KINDS = ("WIRE", "CHAIRS")
CODE_OF = {"WIRE": WIRE_CODE, "CHAIRS": CHAIRS_CODE}
FORMULA_OF = {"WIRE": BINDING_WIRE_FORMULA, "CHAIRS": CHAIRS_FORMULA}
FORMULAS = (BINDING_WIRE_FORMULA, CHAIRS_FORMULA)

@dataclass(frozen=True)
class AllowanceResult:
  solids: list = field(default_factory=list)
  ledger: list = field(default_factory=list)
  stats: dict = field(default_factory=dict)

def _rows(ledger: list, extra_ledger) -> list:
  rows = [r for r in list(ledger) + list(extra_ledger or ()) if r.work_item_code == REBAR_WORK_ITEM and r.unit == "kg" and r.quantity > 0]
  return sorted(rows, key=lambda r: (str(r.level_id), str(r.solid_id)))

def _slab_area_m2(row) -> Decimal | None:
  src = (((row.trace or {}).get("inputs") or {}).get("steel_source") or {})
  if src.get("category") not in SLAB_CATEGORIES:
    return None
  try:
    length, width = Decimal(str(src["size_mm"][0])), Decimal(str(src["size_mm"][1]))
  except Exception:
    return None
  return q6(length * width / MM2_PER_M2) if length > 0 and width > 0 else None

def _has_member(row) -> bool:
  return bool((((row.trace or {}).get("inputs") or {}).get("steel_source") or {}).get("category"))

def _is_slab_row(row) -> bool:
  src = (((row.trace or {}).get("inputs") or {}).get("steel_source") or {})
  return src.get("category") in SLAB_CATEGORIES

def measure_steel_allowances(ctx: CalculationContext, ledger: list, extra_ledger=()) -> AllowanceResult:
  params = resolve_params(ctx)
  wire_on = params[SWITCH_WIRE]["value"] >= 0.5
  chairs_on = params[SWITCH_CHAIRS]["value"] >= 0.5
  stats: dict = {"enabled": wire_on or chairs_on, "ran": False, "wire_on": wire_on, "chairs_on": chairs_on, "param_source": params[SWITCH_WIRE]["source"]}
  if not (wire_on or chairs_on):
    stats["reason"] = "SWITCHED_OFF"
    return AllowanceResult(stats=stats)
  rows = _rows(ledger, extra_ledger)
  
  if not rows:
    stats["reason"] = "NO_REINFORCEMENT"
    return AllowanceResult(stats=stats)
  wire_pct = Decimal(repr(float(params[PARAM_WIRE_PCT]["value"])))
  chairs_rate = Decimal(repr(float(params[PARAM_CHAIRS]["value"])))
  wire_source, chairs_source = params[PARAM_WIRE_PCT]["source"], params[PARAM_CHAIRS]["source"]
  levels: dict = {}
  slab_rows_without_size = 0
  rows_without_member = 0
  
  for r in rows:
    slot = levels.setdefault(r.level_id, {"kg": Decimal("0"), "rows": 0, "area": Decimal("0"), "slab_rows": 0})
    slot["kg"] += r.quantity
    slot["rows"] += 1
    area = _slab_area_m2(r)
    if area is not None:
      slot["area"] += area
      slot["slab_rows"] += 1
    elif _is_slab_row(r):
      slab_rows_without_size += 1
    elif not _has_member(r):
      rows_without_member += 1
      
  solids, out = [], []
  totals = {"WIRE": Decimal("0"), "CHAIRS": Decimal("0")}
  skipped: dict = {}
  
  if chairs_on and slab_rows_without_size:
    skipped["SLAB_WITHOUT_SIZE"] = slab_rows_without_size
  if chairs_on and rows_without_member:
    skipped["ROW_WITHOUT_MEMBER"] = rows_without_member
    
  for level in sorted(levels, key=str):
    slot = levels[level]
    for kind in KINDS:
      if kind == "WIRE" and not wire_on:
        continue
      if kind == "CHAIRS" and not chairs_on:
        continue
      if kind == "WIRE":
        quantity = q6(slot["kg"] * wire_pct / 100)
        steps = [{"op": "reinforcement_kg", "kg": str(q6(slot["kg"])), "rows": slot["rows"], "note": "the reinforcement rows of this storey, as they stand in the bill"},
          {"op": "allowance_pct", "pct": str(wire_pct), "note": "binding wire as a share of the weight of the bars"}, {"op": "weight", "kg": str(quantity)}]
        inputs = {"recipe": RECIPE, "kind": kind, "reinforcement_kg": str(q6(slot["kg"])), "reinforcement_rows": slot["rows"], "pct": str(wire_pct)}
        used = {PARAM_WIRE_PCT: params[PARAM_WIRE_PCT]["value"]}
        basis = {PARAM_WIRE_PCT: wire_source}
        
      else:
        if slot["area"] <= 0:
          continue
        quantity = q6(slot["area"] * chairs_rate)
        steps = [{"op": "slab_area", "m2": str(q6(slot["area"])), "slabs": slot["slab_rows"], "note": "plan area of the slab steel rows of this storey"},
          {"op": "allowance_rate", "kg_per_m2": str(chairs_rate), "note": "chairs and spacers that hold the top steel up"}, {"op": "weight", "kg": str(quantity)}]
        inputs = {"recipe": RECIPE, "kind": kind, "slab_area_m2": str(q6(slot["area"])), "slab_rows": slot["slab_rows"], "kg_per_m2": str(chairs_rate)}
        used = {PARAM_CHAIRS: params[PARAM_CHAIRS]["value"]}
        basis = {PARAM_CHAIRS: chairs_source}
        
      if quantity <= 0:
        continue
      spec = {"kind": DERIVED, "recipe": RECIPE, "item": kind, "params": used, "basis": basis}
      formula = FORMULA_OF[kind]
      solid = Solid(id=uuid5(ctx.run_id, f"solid|steel-allowance|{level}|{kind}"), element_id=None, ifc_type="IfcReinforcingElement", role="STEEL_ALLOWANCE", level_id=level,
        geometry_kind="QTO_ONLY", classification_confidence=Decimal("1"), confidence_factor=FACTOR_ASSUMED, component_type=f"DERIVED_STEEL_{kind}",
        status="REVIEW_REQUIRED")
      out.append(LedgerEntry(solid_id=solid.id, element_id=None, level_id=level, work_item_code=CODE_OF[kind], quantity=quantity, unit="kg", material_grade=None,
        confidence=q4(Decimal("0.9") * FACTOR_ASSUMED), formula_code=formula,
        trace={"formula_code": formula, "engine_version": ctx.engine_version, "convention": ctx.convention_code,
          "rule_set": {"code": ctx.rule_set_code, "version": ctx.rule_set_version}, "inputs": {**inputs, "spec": spec}, "steps": steps, "net": {"kg": str(quantity)},
          "rounding": "half_up,6dp"},
        warnings=(ASSUMED,), source_kind=DERIVED, spec=spec, spec_key="derived"))
      solids.append(solid)
      totals[kind] += quantity
      
  out.sort(key=lambda r: (r.work_item_code, str(r.level_id), str(r.solid_id)))
  reinforcement = sum((s["kg"] for s in levels.values()), Decimal("0"))
  stats.update({"ran": bool(out), "rows": len(out), "levels": len(levels), "reinforcement_kg": str(q6(reinforcement)),
    "wire_kg": str(q6(totals["WIRE"])), "wire_pct": str(wire_pct) if wire_on else None, "wire_source": wire_source if wire_on else None,
    "chairs_kg": str(q6(totals["CHAIRS"])), "chairs_kg_per_m2": str(chairs_rate) if chairs_on else None, "chairs_source": chairs_source if chairs_on else None,
    "slab_area_m2": str(q6(sum((s["area"] for s in levels.values()), Decimal("0")))),
    "kg": str(q6(totals["WIRE"] + totals["CHAIRS"])), "skipped": skipped,
    "share_of_reinforcement_pct": str(q4((totals["WIRE"] + totals["CHAIRS"]) / reinforcement * 100)) if reinforcement > 0 else "0"})
  
  if not out:
    stats["reason"] = "NOTHING_TO_ADD"
  return AllowanceResult(solids=solids, ledger=out, stats=stats)

def steel_allowances_check(solids: list, ledger: list) -> list:
  ids = {s.id for s in solids}
  out = []
  
  for r in ledger:
    if r.formula_code not in FORMULAS:
      continue
    if r.solid_id not in ids:
      out.append(f"{r.work_item_code}: steel allowance row has no solid")
    if r.unit != "kg" or r.quantity <= 0:
      out.append(f"{r.work_item_code}: steel allowance quantity {r.quantity} {r.unit}")
    if r.source_kind != DERIVED:
      out.append(f"{r.work_item_code}: steel allowance row is not a derived row")
    if ASSUMED not in (r.warnings or ()):
      out.append(f"{r.work_item_code}: steel allowance row is not flagged as assumed")
    inputs = (r.trace or {}).get("inputs") or {}
    
    try:
      if r.formula_code == BINDING_WIRE_FORMULA:
        expect = q6(Decimal(inputs["reinforcement_kg"]) * Decimal(inputs["pct"]) / 100)
      else:
        expect = q6(Decimal(inputs["slab_area_m2"]) * Decimal(inputs["kg_per_m2"]))
    except Exception:
      out.append(f"{r.work_item_code}: steel allowance row has no basis in its trace")
      continue
    if abs(expect - r.quantity) > TOLERANCE:
      out.append(f"{r.work_item_code}: steel allowance != basis x rate ({r.quantity} against {expect})")
  return out
