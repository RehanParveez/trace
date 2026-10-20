from __future__ import annotations
from app.engine.measure.models import CalculationContext, LedgerEntry, ModelElement, Solid
from app.engine.measure.takeoff import SOURCE_KIND as PDF_SOURCE
from shapely.affinity import translate
from shapely.geometry import box
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import uuid5
from app.engine.measure.units import mm3_to_m3, q4, q6
from shapely.ops import unary_union
from app.engine.measure.stages import _ffl, element_z
from app.engine.measure.spatial import prism_and_polygon
from app.engine.measure import frame as FR
from app.engine.measure import readings as QS
from app.engine.measure import fill_balance as FB

DERIVED = "DERIVED"
FORMWORK_FORMULA = "SOLID_FORMWORK_AREA"
STEEL_FORMULA = "PDF_MEMBER_STEEL_WEIGHT"
EXEMPT_FORMULAS = (FORMWORK_FORMULA, STEEL_FORMULA)
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
  "footing_formwork": (0.0, 0.0, 1.0),
  "slab_edge_formwork": (1.0, 0.0, 1.0),
  "formwork_shared_faces": (1.0, 0.0, 1.0),
  "tank_base_formwork": (0.0, 0.0, 1.0),
  "steel_cover_mm": (38.1, 10.0, 100.0),
  "ring_hook_dia": (20.0, 0.0, 40.0),
  "bar_lap_dia": (40.0, 0.0, 80.0),
  "bar_anchor_dia": (0.0, 0.0, 80.0),
  "steel_wastage_pct": (0.0, 0.0, 15.0),
  "steel_cover_slab_mm": (38.1, 10.0, 100.0),
  "steel_cover_beam_mm": (38.1, 10.0, 100.0),
  "steel_cover_column_mm": (38.1, 10.0, 100.0),
  "steel_cover_footing_mm": (38.1, 10.0, 100.0),
  "steel_cover_wall_mm": (38.1, 10.0, 100.0),
  "fill_layer_mm": (152.4, 50.0, 600.0),
  "earth_swell_pct": (0.0, 0.0, 50.0),
  "fill_compaction_pct": (0.0, 0.0, 40.0),
  "fill_from_excavation": (0.0, 0.0, 1.0),
  "floor_works_from_spaces": (0.0, 0.0, 1.0),
  "beam_depth_includes_slab": (1.0, 0.0, 1.0),
  "tie_band_replaces_lintel": (0.0, 0.0, 1.0),
  "dpc_thickness_mm": (38.1, 0.0, 300.0),
  "dpc_door_deduction": (1.0, 0.0, 1.0),
  "stair_formwork_soffit_only": (0.0, 0.0, 1.0),
  "beam_lintel_qs_rate": (0.0, 0.0, 1.0),
  "formwork_shared_walls": (1.0, 0.0, 1.0),
  "formwork_shared_beams": (1.0, 0.0, 1.0),
  "rcc_wall_reveals": (0.0, 0.0, 1.0),
}
NGL_PARAM = "ngl_below_ffl_mm"
NGL_RANGE = (-2000.0, 3000.0)
FOOTING_LEVEL_PARAM = "footing_bottom_below_ngl_mm"
ASKED_PARAMS = {FOOTING_LEVEL_PARAM: (1.0, 10000.0)}
FRAME_STEP_MM = 1.0e7
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
CODE_MARK = "DERIVED_MARK_POSITION"
CODE_ELEMENT = "DERIVED_ELEMENT_OVERRIDE"
DERIVED_CODES = (CODE_ASSUMED, CODE_NGL_ASSUMED, CODE_BOX, CODE_MARK, CODE_ELEMENT)
ELEMENT_PARAMS = ("working_space_mm", "pcc_projection_mm", "pcc_thickness_mm", "ballast_thickness_mm", "ballast_clearance_mm")
AREA_FORMULAS = (SHORING, "DPC_AREA", "FLOOR_WORKS_AREA")
MAX_LISTED = 400
BALANCE_TOLERANCE_M3 = Decimal("0.00001")

FACTOR_ASSUMED = Decimal("0.75")
FACTOR_CONFIRMED = Decimal("0.9")
FACTOR_BOX = Decimal("0.9")
FACTOR_MARK = Decimal("0.85")
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
  
    value = _number(((getattr(ctx, "drawing_params", None) or {}).get("params") or {}).get(name), low, high)
    if value is not None:
      out[name] = {"value": value, "source": "drawing"}
      continue
    given_qs = QS.param(name)
    value = _number(given_qs, low, high) if given_qs is not None else None
    if value is not None:
      out[name] = {"value": value, "source": QS.SOURCE}
      continue
    out[name] = {"value": default, "source": "default"}
  return out

def element_overrides(ctx: CalculationContext) -> dict:
  out: dict = {}
  
  for eid, values in (getattr(ctx, "element_overrides", None) or {}).items():
    clean = {}
    for name in ELEMENT_PARAMS:
      value = _number((values or {}).get(name), PARAMS[name][1], PARAMS[name][2])
      if value is not None:
        clean[name] = value
    if clean:
      out[str(eid)] = clean
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
  claim: dict | None = None
  ws: float = 0.0
  params: dict | None = None

def _retune(f: _Foundation, over: dict, params: dict) -> None:
  """Put the values typed for one element in place of the project's: its trench, bed and level are worked out again from its own footprint."""
  mine = {**params, **{n: {"value": v, "source": "element"} for n, v in over.items()}}
  ws = mine["working_space_mm"]["value"]
  if f.bed == "BALLAST":
    proj, thick = mine["ballast_clearance_mm"]["value"], mine["ballast_thickness_mm"]["value"]
    
  else:
    proj, thick = mine["pcc_projection_mm"]["value"], mine["pcc_thickness_mm"]["value"]
  f.exc_poly, f.pcc_poly = _grow(f.poly, proj + ws), _grow(f.poly, proj)
  f.exc_bottom, f.bed_proj, f.bed_t, f.ws, f.params = f.bottom - thick, float(proj), float(thick), float(ws), mine
class _Buried:
  poly: object
  z0: float
  z1: float

def _levels(foundations: list, buried: list, ngl: float) -> list:
  low = min([f.exc_bottom for f in foundations] + [b.z0 for b in buried])
  raw = {round(ngl, 1)}
  for f in foundations:
    raw.update({round(f.exc_bottom, 1), round(f.bottom, 1)})
  for b in buried:
    for z in (b.z0, b.z1):
      if low <= z < ngl:
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
  if f.claim is not None:
    warnings.append(CODE_MARK)
  if any(params[n]["source"] == "element" for n in used):
    warnings.append(CODE_ELEMENT)
  base = f.solid.classification_confidence * f.solid.confidence_factor
  factor = FACTOR_ASSUMED if (assumed or (needs_ngl and ngl["source"] == "default")) else FACTOR_CONFIRMED
  
  if not f.exact:
    factor *= FACTOR_BOX
  if f.claim is not None:
    factor *= FACTOR_MARK
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
      "inputs": {"source_element_id": str(el.id), "recipe": RECIPE_CODE, "spec": spec, "ngl": ngl,
        **({"pdf_source": f.claim} if f.claim is not None else {}), **detail},
      "steps": steps, "net": {unit: str(quantity)}, "rounding": "half_up,6dp",
    },
    warnings=tuple(dict.fromkeys(warnings)), source_kind=DERIVED, spec=spec, spec_key="derived",
  )
  return solid, entry

def resolve_asked(ctx: CalculationContext) -> dict:
  given = getattr(ctx, "derived_params", None) or {}
  convention = ctx.convention_params or {}
  out = {}
  for name, (low, high) in ASKED_PARAMS.items():
    value = _number(given.get(name), low, high)
    if value is not None:
      out[name] = {"value": value, "source": "user"}
      continue
    value = _number(convention.get(name), low, high)
    if value is not None:
      out[name] = {"value": value, "source": "convention"}
  return out

def counted_measurement_ids(extra_ledger) -> set:
  out = set()
  for r in extra_ledger or ():
    if getattr(r, "source_kind", None) != PDF_SOURCE or r.quantity <= 0:
      continue
    mid = ((r.trace or {}).get("inputs") or {}).get("measurement_id")
    if mid:
      out.add(str(mid))
  return out

def _count_up(d: dict, key: str, n: int = 1):
  d[key] = d.get(key, 0) + n

def claim_foundations(ctx: CalculationContext, members, counted: set, bottom_below, ngl_z: float, working_space: float, projection: float,
  thickness: float) -> tuple:
  """PDF footing marks that were counted in this run, as foundations that can be dug and bedded like model footings. The footprint is the
  size of the footing centred on the mark, so the mark position stands in for the drawn outline. A mark cannot be placed without the level
  of the footing bottom below natural ground, which the drawing does not carry, so it waits for that figure."""
  views = sorted({m.frame for m in members})
  placed_frames = FR.frames_of(getattr(ctx, "takeoff", None))
  group_of = {a.view: a.group for a in tuple(getattr(getattr(ctx, "takeoff", None), "alignments", ()) or ())}
  group_no = {g: i for i, g in enumerate(sorted(placed_frames))}
  frame_no = {f: i + len(group_no) for i, f in enumerate(views)}
  used = waiting = 0
  ignored: dict = {}
  waiting_list: list = []
  found: list = []
  
  for m in sorted(members, key=lambda b: str(b.measurement_id)):
    n = len(m.points_mm)
    if str(m.measurement_id) not in counted:
      _count_up(ignored, "NOT_COUNTED", n)
      continue
    length, width, depth = float(m.length_mm), float(m.width_mm), float(m.depth_mm)
    if not (length > 0 and width > 0 and depth > 0):
      _count_up(ignored, "NO_SIZE", n)
      continue
    if bottom_below is None:
      waiting += n
      waiting_list.append({"measurement_id": str(m.measurement_id), "candidate_id": str(m.candidate_id), "tag": m.tag, "marks": n,
        "page_no": m.page_no})
      continue

    for i, (x, y) in enumerate(m.points_mm):
      if i >= len(m.element_ids):
        _count_up(ignored, "NOT_REGISTERED")
        continue
      eid = m.element_ids[i]
      if eid is None:
        _count_up(ignored, "NOT_REGISTERED")
        continue
      group = group_of.get(m.frame)
      spot = FR.frame_xy(placed_frames[group], m.frame, float(x), float(y)) if group in placed_frames else None
      cx, cy, xoff = (spot[0], spot[1], group_no[group] * FRAME_STEP_MM) if spot is not None else (float(x), float(y), frame_no[m.frame] * FRAME_STEP_MM)
      poly = translate(box(cx - length / 2, cy - width / 2, cx + length / 2, cy + width / 2), xoff=xoff)
      z0 = ngl_z - float(bottom_below)
      z1 = z0 + depth
      
      el = ModelElement(
        id=eid, ifc_type="IfcFooting", role="FOOTING", level_id=m.level_id, geometry_kind="EXTRUDED_PROFILE", profile=None,
        placement={"plan_mm": [list(c) for c in list(poly.exterior.coords)[:-1]], "z_min_mm": z0, "z_max_mm": z1},
        volume_mm3=Decimal(repr(poly.area * depth)), bbox_min_mm=None, bbox_max_mm=None,
        classification_confidence=m.confidence, normalization_status="VALID", ifc_global_id=None)
      solid = Solid(
        id=uuid5(ctx.run_id, f"solid|claim|{eid}"), element_id=eid, ifc_type="IfcFooting", role="FOOTING", level_id=m.level_id,
        geometry_kind="EXTRUDED_PROFILE", classification_confidence=m.confidence, confidence_factor=Decimal("1"))
      claim = {
        "measurement_id": str(m.measurement_id), "candidate_id": str(m.candidate_id), "sheet_id": str(m.sheet_id), "page_no": m.page_no,
        "tag": m.tag, "instance": i + 1, "instances": n, "position_basis": "FRAME" if spot is not None else m.position_basis, "position_mm": [round(float(x), 1), round(float(y), 1)],
        "size_mm": [round(length, 1), round(width, 1), round(depth, 1)], "bottom_below_ngl_mm": round(float(bottom_below), 1), "view": m.frame,
      }
      if spot is not None:
        claim["frame_position_mm"] = [round(spot[0], 1), round(spot[1], 1)]
        claim["frame_grade"] = placed_frames[group].alignments[m.frame].grade

      prism, _ = prism_and_polygon(el) or (None, None)
      if prism is None:
        _count_up(ignored, "NO_FOOTPRINT")
        continue
      found.append(_Foundation(
        element=el, solid=solid, poly=poly, exact=True, bottom=float(prism.z0), top=float(prism.z1), claim=claim,
        exc_poly=_grow(poly, projection + working_space), pcc_poly=_grow(poly, projection), exc_bottom=float(prism.z0) - thickness,
        bed="PCC", bed_proj=float(projection), bed_t=float(thickness)))
      used += 1
  stats = {"used": used, "waiting": waiting, "ignored": dict(sorted(ignored.items())), "waiting_list": waiting_list,
    "footing_bottom_below_ngl_mm": float(bottom_below) if bottom_below is not None else None}
  return found, stats

def measure_derived(ctx: CalculationContext, profile, elements: list, solids: list, ledger: list, extra_ledger=()) -> DerivedResult:
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
  model_codes |= {r.work_item_code for r in (extra_ledger or ()) if getattr(r, "source_kind", None) == PDF_SOURCE and r.quantity > 0}
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
      bed=bed, bed_proj=float(proj), bed_t=float(thick), ws=float(ws), params=params))
  stats["skipped"] = dict(sorted(skipped.items()))
  stats["wall_foundations"] = sum(1 for f in foundations if f.bed == "BALLAST" or f.element.role in WALL_BED_ROLES)
  
  members = tuple(getattr(ctx.takeoff, "members", ()) or ())
  if members:
    asked = resolve_asked(ctx)
    if foundations:
      claim_f, claims = [], {"used": 0, "waiting": 0, "ignored": {"MODEL_HAS_FOUNDATIONS": sum(len(m.points_mm) for m in members)}, "waiting_list": [],
        "footing_bottom_below_ngl_mm": None}
    else:
      if not elements and ngl["source"] == "default":
        ngl = {"z_mm": 0.0, "source": "claim", "note": "footing levels from the PDF are measured down from natural ground level"}
        stats["ngl"] = dict(ngl)
      level = asked.get(FOOTING_LEVEL_PARAM)
      claim_f, claims = claim_foundations(ctx, members, counted_measurement_ids(extra_ledger), level["value"] if level else None, float(ngl["z_mm"]), ws, pp, pt)
      claims["footing_bottom_below_ngl_source"] = level["source"] if level else None
    foundations += claim_f
    buried += [_Buried(f.poly, f.bottom, f.top) for f in claim_f]
    stats["claims"] = claims
  for f in foundations:
    if f.params is None:
      f.ws, f.params = float(ws), params
  typed_over = element_overrides(ctx)
  applied = 0
  
  for f in foundations:
    over = typed_over.get(str(f.element.id))
    if over:
      _retune(f, over, params)
      applied += 1
      
  stats["foundations"] = len(foundations)
  stats["element_overrides"] = {"given": len(typed_over), "applied": applied,
    "unmatched": sorted(set(typed_over) - {str(f.element.id) for f in foundations})}
  stats["foundation_list"] = [
    {"element_id": str(f.element.id), "label": (f.claim or {}).get("tag") or f.element.role, "role": f.element.role, "bed": f.bed,
      "mark": bool(f.claim), "page_no": (f.claim or {}).get("page_no"),
      "params": {n: dict(f.params[n]) for n in (_BALLAST_PARAMS if f.bed == "BALLAST" else ("pcc_projection_mm", "pcc_thickness_mm")) + ("working_space_mm",)}}
    for f in sorted(foundations, key=lambda x: str(x.element.id))[:MAX_LISTED]]
  
  if not foundations:
    stats["reason"] = "NEEDS_FOOTING_LEVEL" if (stats.get("claims") or {}).get("waiting") else "NO_FOUNDATIONS"
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
  ngl_z = float(ngl["z_mm"])
  levels = _levels(foundations, buried, ngl_z)
  structure_m3 = outside_m3 = Decimal("0")
  negative_rows: set = set()
  for za, zb in zip(levels, levels[1:]):
    h = zb - za
    
    if h <= EPS:
      continue
    reaching = [f for f in foundations if _covers(f, za, zb)]
    solid_polys = [b.poly for b in buried if b.z0 <= za + EPS and b.z1 >= zb - EPS]
    covering = solid_polys + [f.pcc_poly for f in foundations if _pcc_covers(f, za, zb)]
    union = unary_union(covering) if covering else None
    whole = unary_union([x.exc_poly for x in reaching]) if shoring_on and reaching else None
    
    if solid_polys:
      structure = unary_union(solid_polys)
      dug = unary_union([x.exc_poly for x in reaching]) if reaching else None
      structure_m3 += _vol_m3(structure.area, h)
      outside_m3 += _vol_m3(structure.difference(dug).area if dug is not None else structure.area, h)
    for f, owned in _owned(reaching, lambda x: x.exc_poly):
      inside = owned.intersection(union).area if union is not None else 0.0
      key = f.element.id
      if whole is not None:
        exposed = owned.boundary.intersection(whole.boundary.buffer(0.5)).length
        shr[key] = shr.get(key, 0.0) + exposed * h
      if inside > owned.area + 1.0:
        negative_rows.add(key)
        
      exc[key] = exc.get(key, Decimal("0")) + _vol_m3(owned.area, h)
      back[key] = back.get(key, Decimal("0")) + _vol_m3(max(0.0, owned.area - inside), h)
      bur[key] = bur.get(key, Decimal("0")) + _vol_m3(min(inside, owned.area), h)
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
        {"op": "plan_offset", "mm": round(f.bed_proj + f.ws, 1), "working_space_mm": f.ws,
          ("ballast_clearance_mm" if f.bed == "BALLAST" else "pcc_projection_mm"): f.bed_proj},
        {"op": "depth", "from_mm": round(ngl_z, 1), "to_mm": round(f.exc_bottom, 1),
          ("ballast_thickness_mm" if f.bed == "BALLAST" else "pcc_thickness_mm"): f.bed_t},
        {"op": "share_of_overlapping_trench", "note": "trench area shared with a neighbouring foundation is counted once"},
        {"op": "net_volume", "m3": str(q)},
      ]
      
      s, e = _row(ctx, f, EXCAVATION, codes[EXCAVATION], q, f.params, ngl, {**common, "excavation_bottom_mm": round(f.exc_bottom, 1)}, steps, [])
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
      s, e = _row(ctx, f, bed_kind, codes[bed_kind], q, f.params, ngl, common, steps, [])
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
      s, e = _row(ctx, f, BACKFILL, codes[BACKFILL], q, f.params, ngl,
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
      s, e = _row(ctx, f, SHORING, codes[SHORING], area, f.params, ngl, common, steps, [], unit="m2")
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
    "mark_positions": sum(1 for f in foundations if f.claim is not None),
    "balance": balance_of({EXCAVATION: sum(exc.values(), Decimal("0")), BACKFILL: sum(back.values(), Decimal("0")), "buried": sum(bur.values(), Decimal("0"))},
      structure_m3, outside_m3, len(negative_rows), FB.fill_of(extra_ledger, params)),
  })
  return DerivedResult(solids=out_solids, ledger=out_ledger, stats=stats)

def balance_of(totals: dict, structure_m3: Decimal, outside_m3: Decimal, negative_rows: int, fill: dict | None = None) -> dict:
  exc, back, buried = totals[EXCAVATION], totals[BACKFILL], totals["buried"]
  gap = q6(exc - back - buried)
  
  return {
    "excavation_m3": str(q6(exc)), "backfill_m3": str(q6(back)), "buried_m3": str(q6(buried)), "carted_m3": str(q6(max(Decimal("0"), exc - back))),
    "gap_m3": str(gap), "closes": abs(gap) <= BALANCE_TOLERANCE_M3 and back <= exc + BALANCE_TOLERANCE_M3,
    "structure_below_ground_m3": str(q6(structure_m3)), "structure_outside_trench_m3": str(q6(outside_m3)), "negative_backfill_rows": negative_rows,
    **FB.balance_fill(exc, back, fill),
  }

def derived_check(solids: list, ledger: list) -> list:
  failures: list = []
  by_id = {s.id for s in solids}
  for r in ledger:
    if r.source_kind != DERIVED or r.formula_code in EXEMPT_FORMULAS:
      continue
    if r.solid_id not in by_id:
      failures.append(f"derived row references unknown solid {r.solid_id}")
    want_unit = "m2" if r.formula_code in AREA_FORMULAS else "m3"
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
