from __future__ import annotations
from decimal import Decimal
from app.engine.measure.models import CalculationContext, LedgerEntry, Solid
from uuid import uuid5
from app.engine.measure.derived import DERIVED, resolve_params
from app.engine.measure.takeoff import SOURCE_KIND as PDF_SOURCE
from app.engine.measure.units import q4, q6

FORMULA = "FLOOR_WORKS_AREA"
PARAM = "floor_works_from_spaces"
ITEMS = (("FLR-KACHA-BED", "KACHA_BED"), ("PRO-TERMITE", "TERMITE_UNDER_FLOOR"))
FOUNDATION_ROLES = ("FOOTING", "FOOTING_ISOLATED", "FOOTING_STRIP", "FOOTING_COMBINED", "PILE_CAP", "PILE", "SLAB_FOUNDATION", "GROUND_BEAM", "WALL_FOUNDATION")
ASSUMED = "FLOOR_WORKS_LEVEL_ASSUMED"
FROM_ROOMS = "FLOOR_WORKS_FROM_ROOMS"
MM2_PER_M2 = Decimal("1000000")
BASE = Decimal("0.75")

def _median(values: list) -> float:
  v = sorted(values)
  n = len(v)
  return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2.0

def lowest_level(spaces: list, elements) -> tuple:
  """(level id, how): how is 'ONLY_LEVEL' (the rooms are on one level), 'LOWEST_MEMBERS' or None when it cannot be told."""
  levels = sorted({s.level_id for s in spaces if s.level_id is not None}, key=str)
  if not levels:
    return None, None
  if len(levels) == 1:
    return levels[0], "ONLY_LEVEL"

  low: dict = {}
  for lv in levels:
    zs = [float(e.bbox_min_mm[2]) for e in elements or () if e.level_id == lv and e.bbox_min_mm and (e.role or "").upper() not in FOUNDATION_ROLES]
    if zs:
      low[lv] = _median(zs)
  if len(low) < len(levels):
    return None, None
  ordered = sorted(low.items(), key=lambda kv: (kv[1], str(kv[0])))
  if len(ordered) > 1 and ordered[1][1] - ordered[0][1] < 1.0:
    return None, None
  return ordered[0][0], "LOWEST_MEMBERS"

def _taken(ledger: list, extra_ledger) -> set:
  codes = {r.work_item_code for r in ledger if r.source_kind == "MODEL" and r.quantity > 0}
  codes |= {r.work_item_code for r in (extra_ledger or ()) if getattr(r, "source_kind", None) == PDF_SOURCE and r.quantity > 0}
  return codes

def measure_floor_works(ctx: CalculationContext, elements: list, ledger: list, extra_ledger=()) -> tuple:
  params = resolve_params(ctx)
  on = params[PARAM]["value"] >= 0.5
  stats: dict = {"enabled": on, "ran": False, "param_source": params[PARAM]["source"]}
  if not on:
    stats["reason"] = "SWITCHED_OFF"
    return [], [], stats
  rooms = [s for s in (ctx.spaces or ()) if not s.is_external and s.net_floor_area_mm2 and Decimal(str(s.net_floor_area_mm2)) > 0]
  if not rooms:
    stats["reason"] = "NO_ROOMS"
    return [], [], stats
  level, how = lowest_level(rooms, elements)
  if how is None:
    stats["reason"] = "LOWEST_LEVEL_UNKNOWN"
    return [], [], stats

  rooms = sorted((s for s in rooms if s.level_id == level), key=lambda s: str(s.id))
  total = sum((Decimal(str(s.net_floor_area_mm2)) for s in rooms), Decimal("0")) / MM2_PER_M2
  quantity = q6(total)
  taken = _taken(ledger, extra_ledger)
  assumed = how != "ONLY_LEVEL"
  stats.update({"level_id": str(level), "level_how": how, "rooms": len(rooms), "area_m2": str(quantity), "skipped": {}})
  solids, rows = [], []
  for code, item in ITEMS:
    if code in taken:
      stats["skipped"][code] = "ALREADY_MEASURED"
      continue
  
    solid = Solid(id=uuid5(ctx.run_id, f"solid|floor_works|{level}|{code}"), element_id=None, ifc_type="IfcSpace", role="SPACE_FLOOR_WORKS", level_id=level,
      geometry_kind="QTO_ONLY", classification_confidence=Decimal("1"), confidence_factor=Decimal("1"), component_type=f"DERIVED_{item}", gross_area_m2=quantity,
      status="REVIEW_REQUIRED")
    warnings = [FROM_ROOMS] + ([ASSUMED] if assumed else [])
    confidence = q4(BASE * (Decimal("0.9") if assumed else Decimal("1")))
    spec = {"kind": DERIVED, "recipe": "FLOOR_WORKS_FROM_ROOMS", "item": item, "params": {PARAM: 1.0}, "basis": {PARAM: params[PARAM]["source"], "level": how}}
    steps = [{"op": "net_floor_area", "rooms": len(rooms), "m2": str(quantity)}, {"op": "net_area", "m2": str(quantity)}]
    rows.append(LedgerEntry(solid_id=solid.id, element_id=None, level_id=level, work_item_code=code, quantity=quantity, unit="m2", material_grade=None,
      confidence=confidence, formula_code=FORMULA,
      
      trace={"formula_code": FORMULA, "engine_version": ctx.engine_version, "convention": ctx.convention_code, "rule_set": {"code": ctx.rule_set_code, "version": ctx.rule_set_version},
        "inputs": {"recipe": "FLOOR_WORKS_FROM_ROOMS", "spec": spec, "space_ids": [str(s.id) for s in rooms], "level_how": how},
        "steps": steps, "net": {"m2": str(quantity)}, "rounding": "half_up,6dp"},
      warnings=tuple(warnings), source_kind=DERIVED, spec=spec, spec_key="derived"))
    solids.append(solid)
  stats["ran"] = bool(rows)
  stats["rows"] = len(rows)
  if not rows:
    stats["reason"] = "ALL_ITEMS_ALREADY_MEASURED"
  return solids, rows, stats

def floor_works_check(solids: list, ledger: list) -> list:
  ids = {s.id for s in solids}
  out = []
  for r in ledger:
    if r.formula_code != FORMULA:
      continue
    if r.solid_id not in ids:
      out.append(f"{r.work_item_code}: row has no solid")
    if r.unit != "m2" or r.quantity <= 0:
      out.append(f"{r.work_item_code}: quantity {r.quantity} {r.unit}")
    if r.source_kind != DERIVED:
      out.append(f"{r.work_item_code}: source {r.source_kind}")
  return out
