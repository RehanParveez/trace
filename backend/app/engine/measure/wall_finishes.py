from __future__ import annotations
from decimal import Decimal
from dataclasses import dataclass, field
from app.engine.measure import stages as S
from app.engine.measure.models import Solid, CalculationContext, LedgerEntry
from app.engine.measure.spatial import prism_and_polygon
from uuid import uuid5
from shapely.ops import unary_union
from app.engine.measure.stages import Datum
from app.engine.measure.derived import DERIVED, FACTOR_ASSUMED, resolve_params
from app.engine.measure.takeoff import SOURCE_KIND as PDF_SOURCE
from app.engine.measure.units import q4, q6
from app.engine.measure.wall_foundation import wall_run

PARAM = "wall_finishes_from_walls"
RECIPE = "WALL_FINISHES_FROM_WALLS"
FORMULA = "WALL_FINISH_AREA"
SIDES_ASSUMED = "WALL_FINISH_SIDES_ASSUMED"
NO_OPENINGS = "WALL_FINISH_NO_OPENINGS"
CODES = (SIDES_ASSUMED, NO_OPENINGS)
FINISH_ROLES = frozenset({"WALL", "WALL_EXTERNAL", "WALL_INTERNAL", "WALL_PARTITION", "WALL_LOAD_BEARING"})
OUTER_ROLES = frozenset({"WALL_EXTERNAL"})
INNER_ROLES = frozenset({"WALL_INTERNAL", "WALL_PARTITION"})
OUTLINE_TOLERANCE_MM = 5.0
OUTER_SHARE = 0.5
ITEMS = (("PLASTER_INSIDE", "FIN-PLASTER", "in"), ("PAINT_INSIDE", "FIN-PAINT", "in"), ("PLASTER_OUTSIDE", "FIN-PLASTER-EXT", "out"), ("PAINT_OUTSIDE", "FIN-PAINT-EXT", "out"))
MM2_PER_M2 = Decimal("1000000")

@dataclass(frozen=True)
class WallFinishResult:
  solids: list = field(default_factory=list)
  ledger: list = field(default_factory=list)
  stats: dict = field(default_factory=dict)

def _m2(mm2: float) -> Decimal:
  return q6(Decimal(repr(max(0.0, float(mm2)))) / MM2_PER_M2)

def _taken(ledger: list, extra_ledger) -> set:
  codes = {r.work_item_code for r in ledger if r.source_kind == "MODEL" and r.quantity > 0}
  codes |= {r.work_item_code for r in (extra_ledger or ()) if getattr(r, "source_kind", None) in ("MODEL", PDF_SOURCE) and r.quantity > 0}
  return codes

def _has_rooms(ctx) -> bool:
  for s in (ctx.spaces or ()):
    if not s.is_external and s.net_floor_area_mm2 and Decimal(str(s.net_floor_area_mm2)) > 0:
      return True
  return False

def _outline(polys: list):
  try:
    union = unary_union([p for p in polys if p is not None and not p.is_empty])
    geoms = list(getattr(union, "geoms", [union]))
    rings = [g.exterior for g in geoms if getattr(g, "exterior", None) is not None]
    return unary_union(rings) if rings else None
  except (ValueError, AttributeError):
    return None

def faces_of(role: str, poly, length: float, outline) -> tuple[int, int, bool]:
  role = (role or "").upper()
  if role in OUTER_ROLES:
    return 1, 1, False
  if role in INNER_ROLES:
    return 2, 0, False
  if outline is None or length <= 0:
    return 2, 0, True
  on_outline = poly.boundary.intersection(outline.buffer(OUTLINE_TOLERANCE_MM)).length
  return (1, 1, True) if on_outline >= OUTER_SHARE * length else (2, 0, True)

def _span(z: tuple | None, lo: float, hi: float) -> float:
  if z is None:
    return 0.0
  return max(0.0, min(z[1], hi) - max(z[0], lo))

def _openings(elements: list) -> list:
  out = []
  for el in elements:
    if (el.role or "").upper() not in ("DOOR", "WINDOW"):
      continue
    found = prism_and_polygon(el)
    z = S.element_z(el)
    if found is not None and z is not None:
      out.append((el, found[1], z))
  return out

def _row(ctx, el, solid_of_el: Solid, item: str, code: str, area: Decimal, steps: list, detail: dict, level, sides_assumed: bool, no_openings: bool) -> tuple:
  warnings = ([SIDES_ASSUMED] if sides_assumed else []) + ([NO_OPENINGS] if no_openings else [])
  spec = {"kind": DERIVED, "recipe": RECIPE, "item": item, "params": {}, "basis": {"sides": "geometry" if sides_assumed else "role", "dpc_level": level.source}}
  base = solid_of_el.classification_confidence * solid_of_el.confidence_factor
  confidence = max(Decimal("0"), min(Decimal("1"), q4(base * FACTOR_ASSUMED)))
  
  solid = Solid(id=uuid5(ctx.run_id, f"solid|wallfin|{el.id}|{item}"), element_id=el.id, ifc_type=el.ifc_type, role=el.role, level_id=el.level_id, geometry_kind="QTO_ONLY",
    classification_confidence=solid_of_el.classification_confidence, confidence_factor=solid_of_el.confidence_factor * FACTOR_ASSUMED, component_type=f"DERIVED_{item}",
    gross_area_m2=area, status="REVIEW_REQUIRED" if warnings else "OK")
  
  row = LedgerEntry(solid_id=solid.id, element_id=el.id, level_id=el.level_id, work_item_code=code, quantity=area, unit="m2", material_grade=None, confidence=confidence,
    formula_code=FORMULA,
    trace={"formula_code": FORMULA, "engine_version": ctx.engine_version, "convention": ctx.convention_code,
      "rule_set": {"code": ctx.rule_set_code, "version": ctx.rule_set_version},
      "inputs": {"recipe": RECIPE, "spec": spec, "source_element_id": str(el.id), "start_mm": round(level.z_mm, 1), **detail},
      "steps": steps, "net": {"m2": str(area)}, "rounding": "half_up,6dp"},
    warnings=tuple(warnings), source_kind=DERIVED, spec=spec, spec_key="derived")
  return solid, row

def measure_wall_finishes(ctx: CalculationContext, profile, elements: list, solids: list, ledger: list, extra_ledger=()) -> WallFinishResult:
  params = resolve_params(ctx)
  
  on = params[PARAM]["value"] >= 0.5
  stats: dict = {"enabled": on, "ran": False, "param_source": params[PARAM]["source"]}
  if not on:
    stats["reason"] = "SWITCHED_OFF"
    return WallFinishResult(stats=stats)
  if profile is None:
    stats["reason"] = "NO_PROFILE"
    return WallFinishResult(stats=stats)
  if _has_rooms(ctx):
    stats["reason"] = "HAS_ROOMS"
    return WallFinishResult(stats=stats)

  taken = _taken(ledger, extra_ledger)
  items = [(item, code, side) for item, code, side in ITEMS if code not in taken]
  stats["skipped"] = {code: "ALREADY_MEASURED" for _, code, _ in ITEMS if code in taken}
  if not items:
    stats["reason"] = "ALL_ITEMS_ALREADY_MEASURED"
    return WallFinishResult(stats=stats)

  solid_of = {s.element_id: s for s in solids if s.element_id is not None and s.component_type == "BODY"}
  measured = {r.element_id for r in ledger if r.source_kind == "MODEL" and r.quantity > 0}
  level = S.dpc_datum(ctx, elements)
  
  walls: list = []
  for el in sorted(elements, key=lambda e: str(e.id)):
    if (el.role or "").upper() not in FINISH_ROLES or el.id not in measured or el.id not in solid_of:
      continue
    found = prism_and_polygon(el)
    if found is not None:
      walls.append((el, found[0], found[1]))
  if not walls:
    stats["reason"] = "NO_WALLS"
    return WallFinishResult(stats=stats)

  openings = _openings(elements)
  outline = _outline([p for _, _, p in walls])
  owner: dict = {}
  
  for oi, (op, op_poly, _) in enumerate(openings):
    best, best_area = None, 0.0
    for el, _, poly in walls:
      a = poly.intersection(op_poly).area
      if a > best_area:
        best, best_area = el.id, a
    if best is not None:
      owner[oi] = best
      
  out_solids, out_rows = [], []
  totals = {"in": 0.0, "out": 0.0}
  cut_total = 0.0
  sides_assumed_walls = no_height = 0
  for el, prism, poly in walls:
    start = level.z_mm if level is not None else prism.z0
    bottom = max(prism.z0, start)
    height = prism.z1 - bottom
    length, thickness = wall_run(el, poly)
    if height <= 0 or length <= 0:
      no_height += 1
      continue
  
    inside, outside, assumed = faces_of(el.role, poly, length, outline)
    cuts = []
    for oi, (op, op_poly, z) in enumerate(openings):
      if owner.get(oi) != el.id:
        continue
      width = poly.intersection(op_poly).area / thickness
      h = _span(z, bottom, prism.z1)
      if width > 0 and h > 0:
        cuts.append({"opening_element_id": str(op.id), "role": (op.role or "").upper(), "width_mm": round(width, 1), "height_mm": round(h, 1), "mm2": width * h})
        
    cut = sum(c["mm2"] for c in cuts)
    face = length * height
    sides_assumed_walls += 1 if assumed else 0
    shown = [{k: v for k, v in c.items() if k != "mm2"} for c in cuts]
    for item, code, side in items:
      faces = inside if side == "in" else outside
      if faces <= 0:
        continue
      gross = face * faces
      net = gross - cut * faces
      area = _m2(net)
      if area <= 0:
        continue
    
      steps = [{"op": "wall_face_area", "m2": str(_m2(gross)), "faces": faces, "length_mm": round(length, 1), "height_mm": round(height, 1)}]
      steps += [{"op": "less_opening", **c, "faces": faces} for c in shown]
      steps.append({"op": "net_area", "m2": str(area)})
      lvl = level if level is not None else Datum("DPC", prism.z0, "default", "no floor level in the model; taken at the foot of the wall")
      detail = {"faces": faces, "wall_length_mm": round(length, 1), "wall_thickness_mm": round(thickness, 1), "height_mm": round(height, 1)}
      if item.startswith("PLASTER"):
        pname = "plaster_inside_mm" if side == "in" else "plaster_outside_mm"
        detail["plaster_thickness_mm"] = params[pname]["value"]
        detail["plaster_thickness_source"] = params[pname]["source"]
      s_, r_ = _row(ctx, el, solid_of[el.id], item, code, area, steps, detail, lvl, assumed, not openings)
      out_solids.append(s_)
      out_rows.append(r_)
      if item.startswith("PLASTER"):
        totals[side] += float(area)
        cut_total += cut * faces / 1_000_000.0
        
  out_rows.sort(key=lambda r: (r.work_item_code, str(r.level_id), str(r.element_id)))
  stats.update({"ran": bool(out_rows), "rows": len(out_rows), "walls": len(walls) - no_height, "openings": len(openings), "openings_given_to_a_wall": len(owner),
    "plaster_thickness_mm": {"inside": params["plaster_inside_mm"]["value"], "outside": params["plaster_outside_mm"]["value"],
      "inside_source": params["plaster_inside_mm"]["source"], "outside_source": params["plaster_outside_mm"]["source"]},
    "plaster_inside_m2": str(q6(Decimal(repr(totals["in"])))), "plaster_outside_m2": str(q6(Decimal(repr(totals["out"])))),
    "openings_deducted_m2": str(q6(Decimal(repr(cut_total)))), "sides_from_geometry": sides_assumed_walls, "no_height": no_height,
    "dpc_level": {"z_mm": round(level.z_mm, 1), "source": level.source} if level is not None else None})
  if not out_rows:
    stats["reason"] = "NOTHING_TO_MEASURE"
  return WallFinishResult(solids=out_solids, ledger=out_rows, stats=stats)

def wall_finishes_check(solids: list, ledger: list) -> list:
  ids = {s.id for s in solids}
  out = []
  
  for r in ledger:
    if r.formula_code != FORMULA:
      continue
    if r.solid_id not in ids:
      out.append(f"{r.work_item_code}: wall finish row has no solid")
    if r.unit != "m2" or r.quantity <= 0:
      out.append(f"{r.work_item_code}: wall finish quantity {r.quantity} {r.unit}")
    if r.source_kind != DERIVED:
      out.append(f"{r.work_item_code}: wall finish row is not a derived row")
  return out
