from __future__ import annotations
from app.engine.measure.models import CalculationContext, LedgerEntry, Solid
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import uuid5
from app.engine.measure.units import mm3_to_m3, q4, q6
from shapely.ops import unary_union
from app.engine.measure.stages import _ffl, element_z
from app.engine.measure.spatial import prism_and_polygon

DERIVED = "DERIVED"
RECIPE_CODE = "FOOTING_PREP"
EXCAVATION, PCC, BACKFILL = "EXCAVATION_VOLUME", "FOOTING_PCC_VOLUME", "BACKFILL_VOLUME"
BALLAST, SHORING = "BRICK_BALLAST_VOLUME", "SHORING_AREA"
DEFAULT_CODES = {EXCAVATION: "EXC-FOUND", PCC: "CON-PCC", BACKFILL: "EXC-BACKFILL", BALLAST: "MAS-BALLAST", SHORING: "EXC-SHORING"}
ITEM_NAMES = {EXCAVATION: "EXCAVATION", PCC: "PCC", BACKFILL: "BACKFILL", BALLAST: "BALLAST", SHORING: "SHORING"}
FOUNDATION_ROLES = frozenset({"FOOTING", "FOOTING_ISOLATED", "FOOTING_STRIP", "FOOTING_COMBINED", "RAFT", "RAFT_FOUNDATION", "SLAB_FOUNDATION"})
WALL_BED_ROLES = frozenset({"WALL", "WALL_EXTERNAL", "WALL_INTERNAL", "WALL_PARTITION", "WALL_LOAD_BEARING", "WALL_FOUNDATION"})
WALL_MIN_BURIED_MM = 300.0
NOT_BURIED_ROLES = frozenset({"DOOR", "WINDOW"})

PARAMS = {
  "working_space_mm": (150.0, 0.0, 3000.0),
  "pcc_projection_mm": (100.0, 0.0, 1000.0),
  "pcc_thickness_mm": (100.0, 0.0, 600.0),
  "ballast_thickness_mm": (304.8, 0.0, 1500.0),
  "ballast_clearance_mm": (152.4, 0.0, 1000.0),
  "wall_bed": (0.0, 0.0, 1.0),
  "shoring": (0.0, 0.0, 1.0),
}
NGL_PARAM = "ngl_below_ffl_mm"
NGL_RANGE = (-2000.0, 3000.0)
_BALLAST_PARAMS = ("ballast_clearance_mm", "ballast_thickness_mm")
PARAM_USED_BY = {
  EXCAVATION: ("working_space_mm", "pcc_projection_mm", "pcc_thickness_mm"),
  PCC: ("pcc_projection_mm", "pcc_thickness_mm"),
  BACKFILL: ("working_space_mm", "pcc_projection_mm", "pcc_thickness_mm"),
  BALLAST: _BALLAST_PARAMS,
  SHORING: ("working_space_mm", "shoring", *_BALLAST_PARAMS),
}

def _used(kind: str, bed: str) -> tuple:
  if bed == "BALLAST" and kind in (EXCAVATION, BACKFILL):
    return ("working_space_mm", *_BALLAST_PARAMS)
  return PARAM_USED_BY[kind]

CODE_ASSUMED = "DERIVED_ASSUMED"
CODE_NGL_ASSUMED = "DERIVED_NGL_ASSUMED"
CODE_BOX = "DERIVED_BOX_FOOTPRINT"
DERIVED_CODES = (CODE_ASSUMED, CODE_NGL_ASSUMED, CODE_BOX)

FACTOR_ASSUMED = Decimal("0.75")
FACTOR_CONFIRMED = Decimal("0.9")
FACTOR_BOX = Decimal("0.9")
MAX_FOUNDATIONS = 2000
EPS = 1e-6

@dataclass(frozen=True)
class DerivedResult:
  solids: list = field(default_factory=list)
  ledger: list = field(default_factory=list)
  stats: dict = field(default_factory=dict)

def _number(value, low: float, high: float):
  try:
    x = float(value)
  except (TypeError, ValueError):
    return None
  return x if low <= x <= high and x == x else None

def resolve_params(ctx: CalculationContext) -> dict:
  given = getattr(ctx, "derived_params", None) or {}
  convention = ctx.convention_params or {}
  out = {}
  for name, (default, low, high) in PARAMS.items():
    value = _number(given.get(name), low, high)
    if value is not None:
      out[name] = {"value": value, "source": "user"}
      continue
    value = _number(convention.get(name), low, high)
    if value is not None:
      out[name] = {"value": value, "source": "convention"}
      continue
    out[name] = {"value": default, "source": "default"}
  return out

def resolve_ngl(ctx: CalculationContext, elements: list) -> dict:
  given = _number((getattr(ctx, "derived_params", None) or {}).get(NGL_PARAM), *NGL_RANGE)
  if given is None:
    given = _number((ctx.convention_params or {}).get(NGL_PARAM), *NGL_RANGE)
  if given is None:
    return {"z_mm": 0.0, "source": "default", "note": "no ground level given; the model's zero level is taken as natural ground level"}
  doors = []
  for el in elements:
    if (el.role or "").upper() == "DOOR":
      z = element_z(el)
      if z is not None:
        doors.append(z)
  ffl = _ffl(ctx, doors)
  if ffl is None:
    return {"z_mm": 0.0, "source": "default", "note": "floor level could not be found from the doors, so the model's zero level is taken as natural ground level"}
  return {"z_mm": float(ffl) - given, "source": "user", "note": f"floor level {ffl:.0f} mm less {given:.0f} mm"}

def _d(x: float) -> Decimal:
  return Decimal(repr(float(x)))

def _vol_m3(area_mm2: float, height_mm: float) -> Decimal:
  return mm3_to_m3(_d(area_mm2) * _d(height_mm))

def _grow(poly, distance: float):
  if distance <= 0:
    return poly
  grown = poly.buffer(distance, join_style=2)
  return grown if not grown.is_empty else poly

@dataclass
class _Foundation:
  element: object
  solid: object
  poly: object
  exact: bool
  bottom: float
  top: float
  exc_poly: object = None
  pcc_poly: object = None
  exc_bottom: float = 0.0
  bed: str = "PCC"
  bed_proj: float = 0.0
  bed_t: float = 0.0

@dataclass
class _Buried:
  poly: object
  z0: float
  z1: float

def _levels(foundations: list, buried: list, ngl: float) -> list:
  low = min(f.exc_bottom for f in foundations)
  raw = {round(ngl, 1)}
  for f in foundations:
    raw.update({round(f.exc_bottom, 1), round(f.bottom, 1)})
  for b in buried:
    for z in (b.z0, b.z1):
      if low < z < ngl:
        raw.add(round(z, 1))
  return sorted(z for z in raw if low - EPS <= z <= ngl + EPS)

def _covers(f: _Foundation, za: float, zb: float) -> bool:
  return f.exc_bottom <= za + EPS

def _pcc_covers(f: _Foundation, za: float, zb: float) -> bool:
  return f.exc_bottom <= za + EPS and f.bottom >= zb - EPS

def _owned(items: list, poly_of, prefix=None):
  pieces = []
  for f in items:
    poly = poly_of(f)
    owned = poly if prefix is None else poly.difference(prefix)
    prefix = poly if prefix is None else prefix.union(poly)
    if not owned.is_empty and owned.area > EPS:
      pieces.append((f, owned))
  return pieces

def _row(ctx, f: _Foundation, kind: str, code: str, quantity: Decimal, params: dict, ngl: dict, detail: dict, steps: list,
  extra_warnings: list, unit: str = "m3"):
  used = _used(kind, f.bed)
  needs_ngl = kind not in (PCC, BALLAST)
  assumed = [n for n in used if params[n]["source"] == "default"]
  warnings = list(extra_warnings)
  
  if assumed:
    warnings.append(CODE_ASSUMED)
  if needs_ngl and ngl["source"] == "default":
    warnings.append(CODE_NGL_ASSUMED)
  if not f.exact:
    warnings.append(CODE_BOX)
  base = f.solid.classification_confidence * f.solid.confidence_factor
  factor = FACTOR_ASSUMED if (assumed or (needs_ngl and ngl["source"] == "default")) else FACTOR_CONFIRMED
  if not f.exact:
    factor *= FACTOR_BOX
  confidence = max(Decimal("0"), min(Decimal("1"), q4(base * factor)))
  el = f.element
  solid_id = uuid5(ctx.run_id, f"solid|derived|{el.id}|{kind}")
  spec = {
    "kind": DERIVED, "recipe": RECIPE_CODE, "item": ITEM_NAMES[kind],
    "params": {n: params[n]["value"] for n in used}, "basis": {n: params[n]["source"] for n in used},
  }
  if f.bed == "BALLAST":
    spec["bed"] = "BALLAST"
  
  if needs_ngl:
    spec["ngl_z_mm"] = round(ngl["z_mm"], 1)
    spec["basis"]["ngl"] = ngl["source"]
  solid = Solid(
    id=solid_id, element_id=el.id, ifc_type=el.ifc_type, role=el.role, level_id=el.level_id,
    geometry_kind="EXTRUDED_PROFILE" if f.exact else "BOX_ONLY", classification_confidence=f.solid.classification_confidence,
    confidence_factor=f.solid.confidence_factor * factor, component_type=f"DERIVED_{ITEM_NAMES[kind]}",
    gross_volume_m3=quantity, status="REVIEW_REQUIRED" if warnings else "OK",
  )
  
  entry = LedgerEntry(
    solid_id=solid_id, element_id=el.id, level_id=el.level_id, work_item_code=code, quantity=quantity, unit=unit,
    material_grade=None, confidence=confidence, formula_code=kind,
    trace={
      "formula_code": kind, "engine_version": ctx.engine_version, "convention": ctx.convention_code,
      "rule_set": {"code": ctx.rule_set_code, "version": ctx.rule_set_version},
      "inputs": {"source_element_id": str(el.id), "recipe": RECIPE_CODE, "spec": spec, "ngl": ngl, **detail},
      "steps": steps, "net": {unit: str(quantity)}, "rounding": "half_up,6dp",
    },
    warnings=tuple(dict.fromkeys(warnings)), source_kind=DERIVED, spec=spec, spec_key="derived",
  )
  return solid, entry

def measure_derived(ctx: CalculationContext, profile, elements: list, solids: list, ledger: list) -> DerivedResult:
  stats: dict = {"enabled": True, "ran": False}
  components = {}
  if profile is not None:
    for recipe in profile.recipes_for("IfcFooting"):
      if recipe.code == RECIPE_CODE:
        for c in recipe.components:
          if c.formula_code in (EXCAVATION, PCC, BACKFILL) and c.work_item_code:
            components[c.formula_code] = c.work_item_code
            
  if not components:
    stats["reason"] = "NO_RECIPE"
    return DerivedResult(stats=stats)
  codes = {k: c for k, c in components.items() if k in (EXCAVATION, PCC)}
  if EXCAVATION in components:
    codes[BACKFILL] = components.get(BACKFILL, DEFAULT_CODES[BACKFILL])
  model_codes = {r.work_item_code for r in ledger if r.source_kind == "MODEL"}
  skipped_items = {}
  for kind in list(codes):
    if codes[kind] in model_codes:
      skipped_items[kind] = "MODEL_HAS_ITEM"
      del codes[kind]
  stats["skipped_items"] = skipped_items
  if not codes:
    stats["reason"] = "ALL_ITEMS_IN_MODEL"
    return DerivedResult(stats=stats)

  params = resolve_params(ctx)
  ngl = resolve_ngl(ctx, elements)
  ws, pp, pt = (params[n]["value"] for n in ("working_space_mm", "pcc_projection_mm", "pcc_thickness_mm"))
  bc, bt = params["ballast_clearance_mm"]["value"], params["ballast_thickness_mm"]["value"]
  stats["params"] = {n: dict(v) for n, v in params.items()}
  stats["ngl"] = dict(ngl)

  solid_of = {s.element_id: s for s in solids if s.element_id is not None and s.component_type == "BODY"}
  measured = {r.element_id for r in ledger if r.source_kind == "MODEL" and r.quantity > 0}
  skipped: dict = {}
  foundations: list = []
  buried: list = []
  for el in sorted(elements, key=lambda e: str(e.id)):
    role = (el.role or "").upper()
    solid = solid_of.get(el.id)
    if role in NOT_BURIED_ROLES or solid is None or el.material_class == "STEEL" or el.id not in measured:
      continue
  
    found = prism_and_polygon(el)
    if found is None:
      if role in FOUNDATION_ROLES:
        skipped["NO_FOOTPRINT"] = skipped.get("NO_FOOTPRINT", 0) + 1
      continue
    prism, poly = found
    if prism.z0 < ngl["z_mm"]:
      buried.append(_Buried(poly, prism.z0, prism.z1))
    is_wall = role in WALL_BED_ROLES
    if role not in FOUNDATION_ROLES and not is_wall:
      continue
    if is_wall:
      if prism.z0 > ngl["z_mm"] - WALL_MIN_BURIED_MM:
        continue
      bed = "PCC" if params["wall_bed"]["value"] >= 0.5 else "BALLAST"
      proj, thick = (pp, pt) if bed == "PCC" else (bc, bt)
    else:
      if prism.z0 >= ngl["z_mm"] - 1.0:
        skipped["ABOVE_GROUND"] = skipped.get("ABOVE_GROUND", 0) + 1
        continue
      bed, proj, thick = "PCC", pp, pt
  
    foundations.append(_Foundation(
      element=el, solid=solid, poly=poly, exact=bool(prism.exact), bottom=float(prism.z0), top=float(prism.z1),
      exc_poly=_grow(poly, proj + ws), pcc_poly=_grow(poly, proj), exc_bottom=float(prism.z0) - thick,
      bed=bed, bed_proj=float(proj), bed_t=float(thick)))
  stats["skipped"] = dict(sorted(skipped.items()))
  stats["wall_foundations"] = sum(1 for f in foundations if f.bed == "BALLAST" or f.element.role in WALL_BED_ROLES)
  
  stats["foundations"] = len(foundations)
  if not foundations:
    stats["reason"] = "NO_FOUNDATIONS"
    return DerivedResult(stats=stats)
  if len(foundations) > MAX_FOUNDATIONS:
    stats["reason"] = "TOO_MANY_FOUNDATIONS"
    return DerivedResult(stats=stats)
  if EXCAVATION in codes:
    if any(f.bed == "BALLAST" for f in foundations) and DEFAULT_CODES[BALLAST] not in model_codes:
      codes[BALLAST] = DEFAULT_CODES[BALLAST]
    if params["shoring"]["value"] >= 0.5 and DEFAULT_CODES[SHORING] not in model_codes:
      codes[SHORING] = DEFAULT_CODES[SHORING]
  shoring_on = SHORING in codes

  exc: dict = {}
  pcc: dict = {}
  back: dict = {}
  bur: dict = {}
  shr: dict = {}
  area_sum: dict = {}
  ngl_z = float(ngl["z_mm"])
  levels = _levels(foundations, buried, ngl_z)
  for za, zb in zip(levels, levels[1:]):
    h = zb - za
    
    if h <= EPS:
      continue
    reaching = [f for f in foundations if _covers(f, za, zb)]
    covering = [b.poly for b in buried if b.z0 <= za + EPS and b.z1 >= zb - EPS]
    covering += [f.pcc_poly for f in foundations if _pcc_covers(f, za, zb)]
    union = unary_union(covering) if covering else None
    whole = unary_union([x.exc_poly for x in reaching]) if shoring_on and reaching else None
    for f, owned in _owned(reaching, lambda x: x.exc_poly):
      inside = owned.intersection(union).area if union is not None else 0.0
      key = f.element.id
      if whole is not None:
        exposed = owned.boundary.intersection(whole.boundary.buffer(0.5)).length
        shr[key] = shr.get(key, 0.0) + exposed * h
        
      exc[key] = exc.get(key, Decimal("0")) + _vol_m3(owned.area, h)
      back[key] = back.get(key, Decimal("0")) + _vol_m3(max(0.0, owned.area - inside), h)
      bur[key] = bur.get(key, Decimal("0")) + _vol_m3(inside, h)
    covering_pcc = [f for f in foundations if _pcc_covers(f, za, zb)]
    for f, owned in _owned(covering_pcc, lambda x: x.pcc_poly):
      pcc[f.element.id] = pcc.get(f.element.id, Decimal("0")) + _vol_m3(owned.area, h)

  out_solids: list = []
  out_ledger: list = []
  totals = {EXCAVATION: Decimal("0"), PCC: Decimal("0"), BACKFILL: Decimal("0"), BALLAST: Decimal("0"), SHORING: Decimal("0"),
    "buried": Decimal("0")}
  for f in sorted(foundations, key=lambda x: str(x.element.id)):
    key = f.element.id
    footprint = q6(_d(f.poly.area) / Decimal("1000000"))
    common = {"footprint_m2": str(footprint), "foundation_bottom_mm": round(f.bottom, 1), "foundation_top_mm": round(f.top, 1)}
    if EXCAVATION in codes and exc.get(key, Decimal("0")) > 0:
      q = q6(exc[key])
      steps = [
        {"op": "footprint", "m2": str(footprint)},
        {"op": "plan_offset", "mm": round(f.bed_proj + ws, 1), "working_space_mm": ws,
          ("ballast_clearance_mm" if f.bed == "BALLAST" else "pcc_projection_mm"): f.bed_proj},
        {"op": "depth", "from_mm": round(ngl_z, 1), "to_mm": round(f.exc_bottom, 1),
          ("ballast_thickness_mm" if f.bed == "BALLAST" else "pcc_thickness_mm"): f.bed_t},
        {"op": "share_of_overlapping_trench", "note": "trench area shared with a neighbouring foundation is counted once"},
        {"op": "net_volume", "m3": str(q)},
      ]
      
      s, e = _row(ctx, f, EXCAVATION, codes[EXCAVATION], q, params, ngl, {**common, "excavation_bottom_mm": round(f.exc_bottom, 1)}, steps, [])
      out_solids.append(s)
      out_ledger.append(e)
      totals[EXCAVATION] += q
    bed_kind = BALLAST if f.bed == "BALLAST" else PCC
    if bed_kind in codes and pcc.get(key, Decimal("0")) > 0:
      q = q6(pcc[key])
      steps = [
        {"op": "footprint", "m2": str(footprint)},
        {"op": "plan_offset", "mm": f.bed_proj,
          ("ballast_clearance_mm" if f.bed == "BALLAST" else "pcc_projection_mm"): f.bed_proj},
        {"op": "thickness", "mm": f.bed_t},
        {"op": "net_volume", "m3": str(q)},
        
      ]
      s, e = _row(ctx, f, bed_kind, codes[bed_kind], q, params, ngl, common, steps, [])
      out_solids.append(s)
      out_ledger.append(e)
      totals[bed_kind] += q
    if BACKFILL in codes and back.get(key, Decimal("0")) > 0:
      q = q6(back[key])
      excavation_q = q6(exc.get(key, Decimal("0")))
      buried_q = q6(bur.get(key, Decimal("0")))
      steps = [
        {"op": "excavation_volume", "m3": str(excavation_q)},
        {"op": "less_buried_structure", "m3": str(buried_q),
         "note": "foundation, PCC bed and every measured element standing in this trench below natural ground level"},
        {"op": "net_volume", "m3": str(q)},
      ]
      s, e = _row(ctx, f, BACKFILL, codes[BACKFILL], q, params, ngl,
        {**common, "excavation_m3": str(excavation_q), "buried_m3": str(buried_q)}, steps, [])
      out_solids.append(s)
      out_ledger.append(e)
      totals[BACKFILL] += q
      totals["buried"] += buried_q
      
    if SHORING in codes and shr.get(key, 0.0) > 1.0:
      area = q6(_d(shr[key]) / Decimal("1000000"))
      steps = [
        {"op": "excavation_side_length_exposed_to_ground", "note": "sides of the trench not shared with a neighbouring trench"},
        {"op": "depth", "from_mm": round(ngl_z, 1), "to_mm": round(f.exc_bottom, 1)},
        {"op": "net_area", "m2": str(area)},
      ]
      s, e = _row(ctx, f, SHORING, codes[SHORING], area, params, ngl, common, steps, [], unit="m2")
      out_solids.append(s)
      out_ledger.append(e)
      totals[SHORING] += area
  out_ledger.sort(key=lambda r: (r.work_item_code, str(r.level_id), str(r.element_id)))
  
  stats.update({
    "ran": True, "rows": len(out_ledger),
    "excavation_m3": str(q6(totals[EXCAVATION])), "pcc_m3": str(q6(totals[PCC])),
    "ballast_m3": str(q6(totals[BALLAST])), "shoring_m2": str(q6(totals[SHORING])),
    "backfill_m3": str(q6(totals[BACKFILL])), "buried_m3": str(q6(totals["buried"])),
    "assumed": sorted({n for e in out_ledger for n, b in ((e.spec or {}).get("basis") or {}).items() if b == "default" and n != "ngl"}),
    "ngl_assumed": ngl["source"] == "default",
    "box_footprints": sum(1 for f in foundations if not f.exact),
  })
  return DerivedResult(solids=out_solids, ledger=out_ledger, stats=stats)

def derived_check(solids: list, ledger: list) -> list:
  failures: list = []
  by_id = {s.id for s in solids}
  for r in ledger:
    if r.source_kind != DERIVED:
      continue
    if r.solid_id not in by_id:
      failures.append(f"derived row references unknown solid {r.solid_id}")
    want_unit = "m2" if r.formula_code == SHORING else "m3"
    if r.unit != want_unit:
      failures.append(f"derived row {r.solid_id} is not in {want_unit}")
    if r.work_stage is not None:
      failures.append(f"derived row {r.solid_id} carries a work stage")
    inputs = (r.trace or {}).get("inputs") or {}
    
    if r.formula_code == BACKFILL:
      try:
        want = q6(Decimal(inputs["excavation_m3"]) - Decimal(inputs["buried_m3"]))
      except Exception:
        failures.append(f"backfill row {r.solid_id} has no excavation and buried volumes in its trace")
        continue
      if abs(want - r.quantity) > Decimal("0.000002"):
        failures.append(f"backfill != excavation - buried on solid {r.solid_id}")
      if Decimal(inputs["buried_m3"]) > Decimal(inputs["excavation_m3"]) + Decimal("0.000002"):
        failures.append(f"permanent work exceeds the excavation on solid {r.solid_id}; a datum or footprint is wrong")
  return failures
