from __future__ import annotations
from app.engine.measure.takeoff import SOURCE_KIND as PDF_SOURCE
from decimal import Decimal
from dataclasses import dataclass, field
from app.engine.measure.models import CalculationContext, Solid, LedgerEntry
from app.engine.measure.units import q6, q4
from uuid import uuid5
from app.engine.measure.derived import DERIVED, FACTOR_ASSUMED, resolve_params

PARAM_ON, PARAM_COBA, PARAM_MEMBRANE, PARAM_SCREED = "roof_deck_assembly", "roof_coba_thickness_mm", "roof_membrane", "roof_screed"
SOURCE_CODE = "FIN-ROOF-TREAT"
AREA_FORMULA, VOLUME_FORMULA = "ROOF_DECK_AREA", "ROOF_DECK_VOLUME"
FORMULAS = (AREA_FORMULA, VOLUME_FORMULA)
RECIPE = "ROOF_DECK_FROM_TREATMENT"
ASSUMED = "ROOF_DECK_LAYERS_ASSUMED"
MM_PER_M = Decimal("1000")

LAYERS = {
  "MEMBRANE": ("FIN-ROOF-MEMBRANE", "m2", AREA_FORMULA, PARAM_MEMBRANE),
  "COBA": ("FIN-ROOF-COBA", "m3", VOLUME_FORMULA, None),
  "SCREED": ("FIN-ROOF-SCREED", "m2", AREA_FORMULA, PARAM_SCREED),
}
ORDER = ("MEMBRANE", "COBA", "SCREED")
SOURCE_KINDS = ("MODEL", PDF_SOURCE, DERIVED)

@dataclass(frozen=True)
class RoofDeckResult:
  solids: list = field(default_factory=list)
  ledger: list = field(default_factory=list)
  stats: dict = field(default_factory=dict)

def _taken(ledger: list, extra_ledger) -> set:
  codes = {r.work_item_code for r in ledger if r.source_kind == "MODEL" and r.quantity > 0}
  codes |= {r.work_item_code for r in (extra_ledger or ()) if getattr(r, "source_kind", None) in ("MODEL", PDF_SOURCE) and r.quantity > 0}
  return codes

def _sources(ledger: list, extra_ledger) -> list:
  rows = [r for r in list(ledger) + list(extra_ledger or ()) if r.work_item_code == SOURCE_CODE and r.unit == "m2" and r.quantity > 0 and getattr(r, "source_kind", "MODEL") in SOURCE_KINDS]
  return sorted(rows, key=lambda r: (str(r.level_id), str(r.solid_id), str(r.quantity)))

def layers_wanted(params: dict) -> dict:
  out: dict = {}
  for name in ORDER:
    switch = LAYERS[name][3]
    if switch is not None and params[switch]["value"] < 0.5:
      continue
    if name == "COBA":
      thick = Decimal(repr(float(params[PARAM_COBA]["value"])))
      if thick <= 0:
        continue
      out[name] = thick
    else:
      out[name] = None
  return out

def measure_roof_deck(ctx: CalculationContext, ledger: list, extra_ledger=()) -> RoofDeckResult:
  params = resolve_params(ctx)
  on = params[PARAM_ON]["value"] >= 0.5
  stats: dict = {"enabled": on, "ran": False, "param_source": params[PARAM_ON]["source"]}
  if not on:
    stats["reason"] = "SWITCHED_OFF"
    return RoofDeckResult(stats=stats)

  wanted = layers_wanted(params)
  taken = _taken(ledger, extra_ledger)
  skipped = {LAYERS[n][0]: "ALREADY_MEASURED" for n in wanted if LAYERS[n][0] in taken}
  wanted = {n: t for n, t in wanted.items() if LAYERS[n][0] not in taken}
  stats["skipped"] = skipped
  if not wanted:
    stats["reason"] = "ALL_LAYERS_ALREADY_MEASURED" if skipped else "NO_LAYER_WANTED"
    return RoofDeckResult(stats=stats)
  sources = _sources(ledger, extra_ledger)
  
  if not sources:
    stats["reason"] = "NO_ROOF_TREATMENT"
    return RoofDeckResult(stats=stats)
  thick_source = params[PARAM_COBA]["source"]
  solids, rows = [], []
  totals = {n: Decimal("0") for n in wanted}
  seen: dict = {}
  for src in sources:
    n = seen.get(src.solid_id, 0)
    seen[src.solid_id] = n + 1
    area = q6(Decimal(src.quantity))
    for name in ORDER:
      if name not in wanted:
        continue
    
      code, unit, formula, _ = LAYERS[name]
      thickness = wanted[name]
      if thickness is not None:
        quantity = q6(area * thickness / MM_PER_M)
        steps = [{"op": "roof_area", "m2": str(area), "note": "the roof treatment row this layer sits on"},
          {"op": "layer_thickness", "mm": str(thickness), "note": "average thickness, gives the fall"}, {"op": "net_volume", "m3": str(quantity)}]
        net = {"m3": str(quantity)}
      else:
        quantity = area
        steps = [{"op": "roof_area", "m2": str(area), "note": "the roof treatment row this layer sits on"}, {"op": "net_area", "m2": str(quantity)}]
        net = {"m2": str(quantity)}
        
      if quantity <= 0:
        continue
      basis = {"area": "roof_treatment"}
      if thickness is not None:
        basis[PARAM_COBA] = thick_source
        
      spec = {"kind": DERIVED, "recipe": RECIPE, "item": name, "params": ({PARAM_COBA: float(thickness)} if thickness is not None else {}), "basis": basis}
      solid = Solid(id=uuid5(ctx.run_id, f"solid|roofdeck|{src.solid_id}|{n}|{name}"), element_id=src.element_id, ifc_type="IfcSlab", role="ROOF_DECK", level_id=src.level_id,
        geometry_kind="QTO_ONLY", classification_confidence=Decimal("1"), confidence_factor=FACTOR_ASSUMED, component_type=f"DERIVED_ROOF_{name}",
        gross_area_m2=area if unit == "m2" else None, gross_volume_m3=quantity if unit == "m3" else None, status="REVIEW_REQUIRED")
      rows.append(LedgerEntry(solid_id=solid.id, element_id=src.element_id, level_id=src.level_id, work_item_code=code, quantity=quantity, unit=unit, material_grade=None,
        confidence=q4(Decimal("0.9") * FACTOR_ASSUMED), formula_code=formula,
        trace={"formula_code": formula, "engine_version": ctx.engine_version, "convention": ctx.convention_code,
          "rule_set": {"code": ctx.rule_set_code, "version": ctx.rule_set_version},
          "inputs": {"recipe": RECIPE, "spec": spec, "layer": name, "roof_area_m2": str(area), "source_work_item": SOURCE_CODE, "source_kind": getattr(src, "source_kind", None),
            **({"thickness_mm": str(thickness)} if thickness is not None else {})},
          "steps": steps, "net": net, "rounding": "half_up,6dp"},
        
        warnings=(ASSUMED,), source_kind=DERIVED, spec=spec, spec_key="derived"))
      solids.append(solid)
      totals[name] += quantity
      
  rows_sorted = sorted(zip(rows, solids), key=lambda p: (ORDER.index(p[0].trace["inputs"]["layer"]), str(p[0].level_id), str(p[0].solid_id)))
  rows = [r for r, _ in rows_sorted]
  solids = [s for _, s in rows_sorted]
  stats.update({"ran": bool(rows), "rows": len(rows), "roofs": len(sources), "layers": [n for n in ORDER if n in wanted],
    "roof_area_m2": str(q6(sum((Decimal(s.quantity) for s in sources), Decimal("0")))),
    "membrane_m2": str(q6(totals.get("MEMBRANE", Decimal("0")))), "coba_m3": str(q6(totals.get("COBA", Decimal("0")))), "screed_m2": str(q6(totals.get("SCREED", Decimal("0")))),
    "coba_thickness_mm": str(wanted["COBA"]) if "COBA" in wanted else None, "coba_thickness_source": thick_source if "COBA" in wanted else None})
  if not rows:
    stats["reason"] = "NOTHING_TO_MEASURE"
  return RoofDeckResult(solids=solids, ledger=rows, stats=stats)

def roof_deck_check(solids: list, ledger: list) -> list:
  ids = {s.id for s in solids}
  unit_of = {v[0]: v[1] for v in LAYERS.values()}
  out = []
  
  for r in ledger:
    if r.formula_code not in FORMULAS:
      continue
  
    if r.solid_id not in ids:
      out.append(f"{r.work_item_code}: roof layer row has no solid")
    if r.unit != unit_of.get(r.work_item_code) or r.quantity <= 0:
      out.append(f"{r.work_item_code}: roof layer quantity {r.quantity} {r.unit}")
    if r.source_kind != DERIVED:
      out.append(f"{r.work_item_code}: roof layer row is not a derived row")
    if ASSUMED not in (r.warnings or ()):
      out.append(f"{r.work_item_code}: roof layer row is not flagged as assumed")
  return out
