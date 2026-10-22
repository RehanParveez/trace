from __future__ import annotations
from decimal import Decimal
from app.engine.measure.member_steel import clean_steel
from dataclasses import dataclass, field
from app.engine.measure.rebar import ESTIMATE_BANDS, REBAR_WORK_ITEM
from math import sqrt
from app.engine.measure.takeoff import range_trace
from app.engine.measure.units import q6, q4
from uuid import uuid5
from app.engine.measure.derived import DERIVED, FACTOR_ASSUMED
from app.engine.measure.models import LedgerEntry, Solid
from app.engine.measure import grades as GR

FORMULA = "PDF_MEMBER_STEEL_WEIGHT"
RECIPE = "PDF_MEMBER_STEEL_ESTIMATE"
CODE_ESTIMATED = "STEEL_ESTIMATED"
SWITCH, SLAB_RULE, WASTAGE = "steel_estimate_from_volume", "slab_steel_kg_per_m2", "steel_wastage_pct"
FAMILY = {"LINTEL": "BEAM", "BEAM": "BEAM", "COLUMN": "COLUMN", "FOOTING": "FOOTING", "SLAB": "SLAB", "CHAJJA": "SLAB", "BALCONY_SLAB": "SLAB"}
SLAB_CATEGORIES = ("SLAB", "CHAJJA", "BALCONY_SLAB")
NOT_ESTIMATED = ("RCC_WALL", "STAIR", "TANK", "PARAPET")
RULE_PCT = 10.0
MM3_PER_M3 = Decimal("1000000000")
MM2_PER_M2 = Decimal("1000000")

@dataclass(frozen=True)
class EstimateResult:
  solids: list = field(default_factory=list)
  ledger: list = field(default_factory=list)
  stats: dict = field(default_factory=dict)

def unbarred(members) -> tuple:
  return tuple(m for m in members if (m.category in FAMILY or m.category in NOT_ESTIMATED) and not clean_steel(m.steel))

def _pct(low: Decimal, likely: Decimal, high: Decimal) -> tuple:
  return (float((low / likely - 1) * 100), float((high / likely - 1) * 100)) if likely > 0 else (0.0, 0.0)

def _range(ctx, m, low_pct: float, high_pct: float, basis_name: str) -> dict:
  drivers = [{"name": basis_name, "basis": "ASSUMED", "low_pct": round(low_pct, 2), "high_pct": round(high_pct, 2)}]
  own = range_trace(ctx.takeoff, m.measurement_id)
  low, high = low_pct, high_pct
  
  if own and own.get("bounded") and own.get("low_pct") is not None and own.get("high_pct") is not None:
    low = -sqrt(low_pct ** 2 + float(own["low_pct"]) ** 2)
    high = sqrt(high_pct ** 2 + float(own["high_pct"]) ** 2)
    drivers += [dict(d) for d in (own.get("drivers") or [])]
  return {"grade": "ASSUMED", "bounded": True, "low_pct": round(low, 2), "high_pct": round(high, 2), "leaves_out": False, "drivers": drivers, "by": "ENGINE"}

def figure(category: str, length_mm, width_mm, depth_mm, rule: Decimal, wastage: Decimal) -> dict | None:
  family = FAMILY.get(category)
  length, width, depth = Decimal(str(length_mm or 0)), Decimal(str(width_mm or 0)), Decimal(str(depth_mm or 0))
  
  if family is None or length <= 0 or width <= 0 or depth <= 0:
    return None
  volume = length * width * depth / MM3_PER_M3
  area = length * width / MM2_PER_M2
  low_i, likely_i, high_i = ESTIMATE_BANDS[family]
  if category in SLAB_CATEGORIES and rule > 0:
    basis, unit, quantity = "QS_RULE", "kg/m2", area
    rate, rate_low, rate_high = rule, rule * Decimal("0.9"), rule * Decimal("1.1")
    low_pct, high_pct = -RULE_PCT, RULE_PCT
    driver = "slab steel by the quantity surveyor's rule (kg per m2)"
  else:
    basis, unit, quantity = "USUAL_KG_PER_M3", "kg/m3", volume
    rate, rate_low, rate_high = likely_i, low_i, high_i
    low_pct, high_pct = _pct(low_i, likely_i, high_i)
    driver = f"no bars printed: the usual kg per m3 of {family.lower()} concrete"
    
  bare = quantity * rate
  kg = q6(bare * (1 + wastage / 100))
  return {"family": family, "basis": basis, "unit": unit, "quantity": quantity, "rate": rate, "rate_low": rate_low, "rate_high": rate_high, "bare_kg": bare, "kg": kg,
    "kg_low": q6(kg * (1 + Decimal(str(low_pct)) / 100)), "kg_high": q6(kg * (1 + Decimal(str(high_pct)) / 100)), "low_pct": low_pct, "high_pct": high_pct,
    "driver": driver, "volume": volume, "area": area}

def estimate_steel(ctx, params: dict, members, counted: set) -> EstimateResult:
  stats: dict = {"enabled": False}
  if float(params[SWITCH]["value"]) < 0.5:
    return EstimateResult(stats=stats)
  stats = {"enabled": True, "members": 0, "kg": "0", "kg_low": "0", "kg_high": "0", "by_family": {}, "skipped": {}, "slab_rule_kg_per_m2": None}
  rule = Decimal(str(params[SLAB_RULE]["value"]))
  wastage = Decimal(str(params[WASTAGE]["value"]))
  rule_source = params[SLAB_RULE]["source"]
  stats["slab_rule_kg_per_m2"] = str(rule) if rule > 0 else None
  skipped: dict = stats["skipped"]
  rows: list = []
  solids: list = []
  fam: dict = {}
  
  for m in sorted(unbarred(members), key=lambda b: str(b.measurement_id)):
    if str(m.measurement_id) not in counted:
      skipped["NOT_COUNTED"] = skipped.get("NOT_COUNTED", 0) + m.count
      continue
    if m.category in NOT_ESTIMATED or m.category not in FAMILY:
      skipped["NO_USUAL_FIGURE"] = skipped.get("NO_USUAL_FIGURE", 0) + m.count
      continue
    fg = figure(m.category, m.length_mm, m.width_mm, m.depth_mm, rule, wastage)
    if fg is None:
      skipped["NO_SIZE"] = skipped.get("NO_SIZE", 0) + m.count
      continue
  
    family, basis, unit, volume, area = fg["family"], fg["basis"], fg["unit"], fg["volume"], fg["area"]
    kg, kg_low, kg_high = fg["kg"], fg["kg_low"], fg["kg_high"]
    rg = _range(ctx, m, fg["low_pct"], fg["high_pct"], fg["driver"])
    grade = GR.steel_grade_of(ctx, m.category)
    confidence = max(Decimal("0"), min(Decimal("1"), q4(m.confidence * FACTOR_ASSUMED)))
    used = (SWITCH, WASTAGE) + ((SLAB_RULE,) if basis == "QS_RULE" else ())
    spec = {"kind": DERIVED, "recipe": RECIPE, "item": "STEEL", "category": m.category, "params": {n: params[n]["value"] for n in used}, "basis": {n: params[n]["source"] for n in used}}
    
    for i in range(m.count):
      eid = m.element_ids[i] if i < len(m.element_ids) else None
      solid_id = uuid5(ctx.run_id, f"solid|steel-est|{m.measurement_id}|{i}")
      solids.append(Solid(id=solid_id, element_id=eid, ifc_type={"LINTEL": "IfcBeam", "BEAM": "IfcBeam", "COLUMN": "IfcColumn", "FOOTING": "IfcFooting"}.get(m.category, "IfcSlab"),
        role=m.category, level_id=m.level_id, geometry_kind="QTO_ONLY", classification_confidence=m.confidence, confidence_factor=FACTOR_ASSUMED,
        component_type="DERIVED_STEEL", gross_length_m=q6(m.length_mm / Decimal("1000")), status="REVIEW_REQUIRED"))
      est = {"basis": basis, "unit": unit, "quantity": str(q6(fg["quantity"])), "kg_per_unit": str(fg["rate"]), "kg_per_unit_low": str(fg["rate_low"]), "kg_per_unit_high": str(fg["rate_high"]),
        "family": family, "rule_source": rule_source if basis == "QS_RULE" else "band"}
      source = {"measurement_id": str(m.measurement_id), "candidate_id": str(m.candidate_id), "sheet_id": str(m.sheet_id), "page_no": m.page_no, "category": m.category,
        "tag": m.tag, "instance": i + 1, "instances": m.count, "size_mm": [float(m.length_mm), float(m.width_mm), float(m.depth_mm)], "estimate": est,
        "wastage_pct": str(wastage), "concrete_m3": str(q6(volume)), "bare_kg": str(q6(fg["bare_kg"])),
        **({"steel_grade": grade["label"], "steel_grade_note": {"scope": grade["scope"], "pages": grade["pages"]}} if grade["label"] else {}),
        **({"steel_grade_clash": grade["clash"]} if grade["clash"] else {})}
      
      rows.append(LedgerEntry(solid_id=solid_id, element_id=eid, level_id=m.level_id, work_item_code=REBAR_WORK_ITEM, quantity=kg, unit="kg", material_grade=grade["label"],
        confidence=confidence, formula_code=FORMULA,
        trace={"formula_code": FORMULA, "engine_version": ctx.engine_version, "convention": ctx.convention_code, "rule_set": {"code": ctx.rule_set_code, "version": ctx.rule_set_version},
          "inputs": {"recipe": RECIPE, "spec": spec, "steel_source": source},
          "steps": [{"op": "estimate_basis", **est}, {"op": "weight", "bare_kg": str(q6(fg["bare_kg"])), "wastage_pct": str(wastage), "kg": str(kg), "kg_low": str(kg_low), "kg_high": str(kg_high)}],
          "net": {"kg": str(kg), "kg_low": str(kg_low), "kg_high": str(kg_high)}, "rounding": "half_up,6dp", "range": rg},
        warnings=(CODE_ESTIMATED,), source_kind=DERIVED, spec=spec, spec_key="derived"))
      slot = fam.setdefault(m.category, {"members": 0, "kg": Decimal("0"), "kg_low": Decimal("0"), "kg_high": Decimal("0"), "m3": Decimal("0"), "m2": Decimal("0")})
      slot["members"] += 1
      slot["kg"] += kg
      slot["kg_low"] += kg_low
      slot["kg_high"] += kg_high
      slot["m3"] += volume
      slot["m2"] += area
      
  rows.sort(key=lambda r: (str(r.level_id), r.trace["inputs"]["steel_source"]["category"], str(r.solid_id)))
  total = sum((r.quantity for r in rows), Decimal("0"))
  stats.update({"members": len(rows), "kg": str(q6(total)), "kg_low": str(q6(sum((v["kg_low"] for v in fam.values()), Decimal("0")))),
    "kg_high": str(q6(sum((v["kg_high"] for v in fam.values()), Decimal("0")))),
    "by_family": {k: {"members": v["members"], "kg": str(q6(v["kg"])), "kg_low": str(q6(v["kg_low"])), "kg_high": str(q6(v["kg_high"])), "concrete_m3": str(q6(v["m3"])), "area_m2": str(q6(v["m2"]))} for k, v in sorted(fam.items())},
    "skipped": dict(sorted(skipped.items())), "slab_rule_source": rule_source})
  return EstimateResult(solids=solids, ledger=rows, stats=stats)

def estimate_check(solids: list, ledger: list) -> list:
  failures: list = []
  by_id = {s.id for s in solids}
  
  for r in ledger:
    if r.source_kind != DERIVED or r.formula_code != FORMULA or ((r.trace or {}).get("inputs") or {}).get("recipe") != RECIPE:
      continue
    if r.solid_id not in by_id:
      failures.append(f"steel estimate row references unknown solid {r.solid_id}")
    src = (((r.trace or {}).get("inputs") or {}).get("steel_source") or {})
    est = src.get("estimate") or {}
    
    try:
      expect = q6(Decimal(est["quantity"]) * Decimal(est["kg_per_unit"]) * (1 + Decimal(src["wastage_pct"]) / 100))
    except Exception:
      failures.append(f"steel estimate row {r.solid_id} has no basis in its trace")
      continue
    if abs(expect - r.quantity) > Decimal("0.001"):
      failures.append(f"steel estimate != quantity x rate on solid {r.solid_id}")
    if CODE_ESTIMATED not in (r.warnings or ()):
      failures.append(f"steel estimate row {r.solid_id} is not flagged as an estimate")
  return failures
