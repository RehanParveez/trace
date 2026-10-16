from __future__ import annotations
from dataclasses import dataclass, field, replace
from decimal import Decimal
from uuid import UUID, uuid5
from app.engine.measure import frame as FR
from shapely.geometry import LineString, MultiPolygon, Polygon, box
from app.engine.measure.models import SpatialIndex, Deduction, Prism, Solid
import math
from collections import Counter, defaultdict
from shapely.ops import unary_union
from app.engine.measure.allocate import allocate
from app.engine.measure import stages as S
from app.engine.measure.derived import FRAME_STEP_MM, resolve_params
from app.engine.measure.units import mm3_to_m3, q6
from app.engine.measure.spatial import broad_phase
from app.engine.measure.conventions import get_convention
from app.engine.measure.intersect import find_overlaps
from app.engine.measure.takeoff import SOURCE_KIND

ROLE_OF = {"COLUMN": "COLUMN", "NECK": "COLUMN", "FOOTING": "FOOTING", "BEAM": "BEAM", "PLINTH_BEAM": "BEAM", "BAND": "BEAM", "WALL": "WALL", "RCC_WALL": "WALL_SHEAR",
  "SLAB": "SLAB", "LINTEL": "LINTEL"}
FOLLOWS_WALLS = ("BEAM", "PLINTH_BEAM")
BEAM_PARAM = "beam_depth_includes_slab"
BAND_PARAM = "tie_band_replaces_lintel"
BAND_RULE = "lintel.tie_band_replaces"
UNIT = "m3"
MIN_PIECE_MM = 5.0
DUPLICATE_FRACTION = 0.5
MAX_PARTS = 20000

CODE_OVER = "SPACE_OVER_DEDUCTED"
CODE_UNPLACED = "SPACE_VIEW_NOT_PLACED"
CODE_NO_HEIGHT = "SPACE_NO_HEIGHT"
CODE_SAME = "SPACE_SAME_ROLE_OVERLAP"
CODE_SPLIT_DEFAULT = "STAGE_DATUM_DEFAULTED"
CODE_SPLIT_SPREAD = "STAGE_SPREAD_BY_HEIGHT"
SPACE_CODES = (CODE_OVER, CODE_UNPLACED, CODE_NO_HEIGHT, CODE_SAME, CODE_SPLIT_DEFAULT)

@dataclass(frozen=True)
class Part:
  """One piece of a member that has a plan and a height: the unit allocation works on."""
  sid: UUID
  measurement_id: UUID
  index: int
  role: str
  category: str
  poly: object
  z0: float
  z1: float
  strip: bool
  placed: bool
  virtual: bool = False

@dataclass(frozen=True)
class SpaceResult:
  ledger: list = field(default_factory=list)
  replaced: list = field(default_factory=list)
  added: list = field(default_factory=list)
  deductions: list = field(default_factory=list)
  stats: dict = field(default_factory=dict)

def _mm3_to_m3(v: float) -> Decimal:
  return mm3_to_m3(Decimal(repr(float(v))))

def solid_id_of(ctx, measurement_id) -> UUID:
  return uuid5(ctx.run_id, f"solid|takeoff:{measurement_id}")

def _counted_rows(ledger) -> dict:
  """{measurement id: the one PDF row it produced} for the rows that count, in m3."""
  out: dict = {}
  for r in ledger or ():
    if getattr(r, "source_kind", None) != SOURCE_KIND or r.quantity <= 0 or r.unit != UNIT:
      continue
    mid = ((r.trace or {}).get("inputs") or {}).get("measurement_id")
    if mid and mid not in out:
      out[str(mid)] = r
  return out

def _frame_of(takeoff):
  frames = FR.frames_of(takeoff)
  group_of_view = {a.view: a.group for a in tuple(getattr(takeoff, "alignments", ()) or ())}
  return frames, group_of_view

def _poly_of(member, part, shift) -> Polygon | None:
  x, y = shift
  if member.shape == "BOX":
    cx, cy = float(part[0]) + x, float(part[1]) + y
    length, width = float(member.length_mm), float(member.width_mm)
    if length <= 0 or width <= 0:
      return None
    return box(cx - length / 2.0, cy - width / 2.0, cx + length / 2.0, cy + width / 2.0)
  if member.shape == "STRIP":
    x1, y1, x2, y2 = (float(v) for v in part)
    width = float(member.width_mm)
    if width <= 0 or math.hypot(x2 - x1, y2 - y1) <= 0:
      return None
    return LineString([(x1 + x, y1 + y), (x2 + x, y2 + y)]).buffer(width / 2.0, cap_style=2)
  return None

def _place(takeoff, member, frames, group_of_view, view_no) -> tuple:
  """(a function taking a sheet point to its place, placed). A placed view goes through its frame, one coordinate system per drawing; a view the frame did
  not place keeps its sheet coordinates, kept away from every other view so it meets only its own members."""
  group = group_of_view.get(member.frame)
  frame = frames.get(group) if group is not None else None
  if frame is not None:
    probe = FR.frame_xy(frame, member.frame, 0.0, 0.0)
    if probe is not None:
      step = sorted(frames).index(group) * FRAME_STEP_MM

      def go(px, py):
        p = FR.frame_xy(frame, member.frame, px, py)
        return (p[0] + step, p[1])
      return go, True
  step = (len(frames) + view_no[(member.group, member.frame)]) * FRAME_STEP_MM
  return (lambda px, py: (px + step, py)), False

def _build_parts(ctx, members, rows) -> tuple:
  """The parts of every counted member that has a plan and a height, and what was left out."""
  takeoff = ctx.takeoff
  frames, group_of_view = _frame_of(takeoff)
  views = sorted({(m.group, m.frame) for m in members})
  view_no = {v: i for i, v in enumerate(views)}
  parts: list = []
  left: Counter = Counter()
  
  for m in sorted(members, key=lambda b: str(b.measurement_id)):
    if str(m.measurement_id) not in rows:
      left["NOT_COUNTED"] += 1
      continue
    role = ROLE_OF.get(m.category)
    if role is None or m.shape not in ("BOX", "STRIP") or not m.parts:
      continue
    if m.z0_mm is None or m.z1_mm is None or float(m.z1_mm) <= float(m.z0_mm):
      left["NO_HEIGHT"] += 1
      continue
  
    go, placed = _place(takeoff, m, frames, group_of_view, view_no)
    for i, part in enumerate(m.parts):
      if m.shape == "BOX":
        cx, cy = go(float(part[0]), float(part[1]))
        poly = _poly_of(m, (cx, cy), (0.0, 0.0))
      else:
        a, b = go(float(part[0]), float(part[1])), go(float(part[2]), float(part[3]))
        poly = _poly_of(m, (a[0], a[1], b[0], b[1]), (0.0, 0.0))
      if poly is None or poly.is_empty or poly.area <= 0:
        left["NO_SIZE"] += 1
        continue
      parts.append(Part(uuid5(ctx.run_id, f"solid|space|{m.measurement_id}|{i}"), m.measurement_id, i, role, m.category, poly, float(m.z0_mm), float(m.z1_mm),
        m.shape == "STRIP", placed))
  return parts, left

def _virtual_slabs(ctx, members, parts, rows, slab_by_level) -> list:
  """Where a beam's depth is the overall depth, the slab is laid over the beams of its floor as one piece (their footprints, from the slab's underside to its
  top), so the allocation gives the slab what lies inside its thickness and the beam keeps its web. One piece per drawing and floor."""
  out: list = []
  beams: dict = defaultdict(list)
  by_id = {str(m.measurement_id): m for m in members}
  
  for p in parts:
    m = by_id[str(p.measurement_id)]
    if p.category == "BEAM":
      beams[(m.group, m.level_id)].append(p)
  for key in sorted(beams, key=lambda k: (k[0], str(k[1]))):
    slab = slab_by_level.get(key)
    if slab is None:
      continue
    union = unary_union([p.poly for p in beams[key]])
    pieces = list(union.geoms) if isinstance(union, MultiPolygon) else [union]
    for n, poly in enumerate(pieces):
      if poly.is_empty or poly.area <= 0:
        continue
      out.append(Part(uuid5(ctx.run_id, f"solid|space|slab|{slab.measurement_id}|{key[0]}|{key[1]}|{n}"), slab.measurement_id, -1 - n, "SLAB", "SLAB", poly,
        float(slab.z0_mm), float(slab.z1_mm), False, True, virtual=True))
  return out

def _slab_for_levels(members, rows) -> dict:
  """The slab each floor of each drawing is measured as: the counted one with the most concrete. Panels of different thickness are not told apart."""
  best: dict = {}
  for m in members:
    if m.category != "SLAB" or m.z0_mm is None or m.z1_mm is None or float(m.z1_mm) <= float(m.z0_mm):
      continue
    row = rows.get(str(m.measurement_id))
    if row is None:
      continue
    key = (m.group, m.level_id)
    if key not in best or row.quantity > rows[str(best[key].measurement_id)].quantity:
      best[key] = m
  return best

def _solid_of(p: Part, ctx) -> Solid:
  gross = _mm3_to_m3(p.poly.area * (p.z1 - p.z0))
  return Solid(id=p.sid, element_id=p.sid, ifc_type="PdfMember", role=p.role, level_id=None, geometry_kind="EXTRUDED_PROFILE",
    classification_confidence=Decimal("1"), confidence_factor=Decimal("1"), gross_volume_m3=gross)

def _index_of(parts: list, ctx) -> tuple:
  prisms: dict = {}
  polys: dict = {}
  
  strips: set = set()
  for p in parts:
    hull = p.poly.convex_hull
    plan = tuple((float(x), float(y)) for x, y in (hull.exterior.coords[:-1] if hull.geom_type == "Polygon" else ()))
    prisms[p.sid] = Prism(plan=plan, z0=p.z0, z1=p.z1, exact=True)
    polys[p.sid] = p.poly
    if p.strip:
      strips.add(p.sid)
  ids = sorted(prisms, key=str)
  min_z = float((ctx.convention_params or {}).get("min_z_overlap_mm", 0.1))
  index = SpatialIndex(prisms=prisms, polys=polys, candidates=broad_phase(ids, prisms, polys, min_z), unallocated=frozenset())
  return index, strips

def _band_slices(d) -> list:
  return [(float(za), float(zb), float(m)) for za, zb, m in ((d.geometry or {}).get("bands") or []) if zb > za]

def _slice_in(slices: list, lo: float, hi: float) -> float:
  total = 0.0
  for za, zb, m in slices:
    ov = min(zb, hi) - max(za, lo)
    if ov > 0:
      total += m * ov / (zb - za)
  return total

def pdf_datums(ctx, floors: list, lintel_z: float | None = None) -> S.StageSetup:
  """The stage bands of one drawing from the floors its register gave: floor level of the ground floor, the DPC a set drop below it, the lintel level, and
  the top of every floor's slab above it. A drawing with no ground floor, or no slab top, cannot be cut."""
  ground = next((f for f in floors if f.key == "GROUND"), None)
  if ground is None:
    return S.StageSetup(reason="NO_GROUND_FLOOR")
  tops = sorted(f.top_mm for f in floors if f.top_mm is not None and f.level_mm >= ground.level_mm)
  if not tops:
    return S.StageSetup(reason="NO_SLAB_LEVEL")
  ffl = float(ground.level_mm)
  given = (ctx.convention_params or {}).get("dpc_below_ffl_mm") is not None
  dpc = S.Datum("DPC", ffl - S._p(ctx, "dpc_below_ffl_mm"), "param" if given else "default",
    "floor level less the DPC drop" if given else "no DPC level on the drawing; taken at floor level")
  
  if lintel_z is not None:
    lintel = S.Datum("LINTEL", lintel_z, "drawing", "opening heads of the ground floor")
  else:
    lintel = S.Datum("LINTEL", ffl + S._p(ctx, "lintel_height_mm"), "param" if (ctx.convention_params or {}).get("lintel_height_mm") is not None else "default",
      "no opening heights on the drawing; floor level plus the lintel height")
    
  if not dpc.z_mm < lintel.z_mm < tops[0]:
    return S.StageSetup(reason="DATUMS_OUT_OF_ORDER")
  datums = [S.Datum("FFL", ffl, "drawing", "finished level of the ground floor"), dpc, lintel]
  datums += [S.Datum(f"SLAB_{i + 1}", z, "drawing", "top of the floor slab") for i, z in enumerate(tops)]
  bands = [S.Band(S.BELOW_PLINTH, S.NEG, dpc.z_mm, dpc.source == "default"),
    S.Band(S.PLINTH_TO_LINTEL, dpc.z_mm, lintel.z_mm, dpc.source == "default" or lintel.source == "default"),
    S.Band(S.LINTEL_TO_SLAB, lintel.z_mm, tops[0], lintel.source == "default")]
  for i in range(1, len(tops)):
    bands.append(S.Band(S.upper_floor(i), tops[i - 1], tops[i], False))
  bands.append(S.Band(S.TOP, tops[-1], S.POS, False))
  return S.StageSetup(datums=tuple(datums), bands=tuple(bands))

def _lintel_z(members, group) -> float | None:
  """The lintel level of a drawing: the lowest base of a lintel on its ground floor, when the lintels carry a height."""
  bases = [float(m.z0_mm) for m in members if m.group == group and m.category == "LINTEL" and m.z0_mm is not None and m.floor == "GROUND"]
  return min(bases) if bases else None

def _stage_pieces(setup, z0: float, z1: float, area: float, slices: list) -> dict:
  """{stage: net mm3} of one prism cut at the bands of the datums, less what the deductions took from each band."""
  out: dict = {}
  for band in setup.bands:
    lo, hi = max(z0, band.lo), min(z1, band.hi)
    if hi - lo < MIN_PIECE_MM:
      continue
    gross = area * (hi - lo)
    net = gross - _slice_in(slices, lo, hi)
    if net > 0:
      out[band.stage] = out.get(band.stage, 0.0) + net
  return out

def split_space(ctx, ledger: list, solids: list = ()) -> SpaceResult:
  """Allocation (when derived works are on) and stage cut (when work stages are on) of the counted PDF members. ledger is every ledger row of the run so far; the
  rows returned are the PDF rows with their net quantities and stages, to be put in place of the ones they replace."""
  takeoff = getattr(ctx, "takeoff", None)
  members = tuple(getattr(takeoff, "space", ()) or ())
  
  allocate_on, stage_on = bool(ctx.derived_mode), bool(ctx.stage_mode)
  stats: dict = {"enabled": True, "allocation": allocate_on, "stages": stage_on}
  if not members or not (allocate_on or stage_on):
    stats["reason"] = "NO_MEMBERS" if not members else "NOT_SWITCHED_ON"
    return SpaceResult(ledger=list(ledger), stats=stats)
  rows = _counted_rows(ledger)
  if not rows:
    stats["reason"] = "NOTHING_COUNTED"
    return SpaceResult(ledger=list(ledger), stats=stats)

  params = resolve_params(ctx)
  convention = get_convention(ctx.convention_code) or get_convention("FRAME_MONOLITHIC_A")
  by_mid = {str(m.measurement_id): m for m in members}
  parts, left = _build_parts(ctx, members, rows)
  stats["members"] = len(members)
  stats["parts"] = len(parts)
  if len(parts) > MAX_PARTS:
    stats["reason"] = "TOO_MANY_PARTS"
    return SpaceResult(ledger=list(ledger), stats=stats)

  deds: dict = defaultdict(list)       
  taken_by_part: dict = defaultdict(list)
  placed_groups = {by_mid[str(p.measurement_id)].group for p in parts if p.placed}
  unplaced = sorted({p.measurement_id for p in parts if not p.placed and by_mid[str(p.measurement_id)].group in placed_groups}, key=str)
  conservation: tuple = ()
  same_role: set = set()
  
  if allocate_on and len(parts) > 1:
    virtual = _virtual_slabs(ctx, members, parts, rows, _slab_for_levels(members, rows)) if params[BEAM_PARAM]["value"] >= 0.5 else []
    everything = parts + virtual
    solids_of = [_solid_of(p, ctx) for p in everything]
    index, strips = _index_of(everything, ctx)
    overlaps = find_overlaps(ctx, index)
    kept = []
    for o in overlaps:
      pa, pb = index.prisms[o.a], index.prisms[o.b]
      dz = min(pa.z1, pb.z1) - max(pa.z0, pb.z0)
      area = o.volume_mm3 / dz if dz > 0 else 0.0
      if o.a in strips and o.b in strips and area < DUPLICATE_FRACTION * min(index.polys[o.a].area, index.polys[o.b].area):
        continue
    
      kept.append(o)
    result = allocate(ctx, convention, solids_of, index, kept)
    conservation = tuple(result.conservation_failures)
    part_of = {p.sid: p for p in everything}
    for sid, codes in (result.solid_warnings or {}).items():
      if "SAME_ROLE_OVERLAP" in codes:
        same_role.add(str(part_of[sid].measurement_id))
        
    for d in result.deductions:
      loser, owner = part_of[d.from_solid_id], part_of[d.to_solid_id]
      key = (str(loser.measurement_id), str(owner.measurement_id), d.deduction_type)
      deds[key].append((d, loser.sid))
      taken_by_part[loser.sid].append(d)
    stats.update({"parts_allocated": len(everything), "overlaps": len(kept), "virtual_slabs": len(virtual)})
  stats["same_role_overlaps"] = len(same_role)
  stats["unplaced_members"] = len(unplaced)
  stats["left_out"] = dict(sorted(left.items()))

  per_loser: dict = defaultdict(list)
  for (loser, owner, dtype), items in sorted(deds.items()):
    mm3 = sum(float(d.quantity) * 1e9 for d, _ in items)
    per_loser[loser].append([owner, dtype, items[0][0].rule_code, mm3, items])
  replaced_lintels = 0
  if allocate_on and params[BAND_PARAM]["value"] >= 0.5:
    
    bands: dict = {}
    for m in members:
      row = rows.get(str(m.measurement_id))
      if m.category != "BAND" or row is None:
        continue
      key = (m.group, m.level_id)
      if key not in bands or row.quantity > rows[str(bands[key].measurement_id)].quantity:
        bands[key] = m
        
    for m in sorted(members, key=lambda b: str(b.measurement_id)):
      mid = str(m.measurement_id)
      owner = bands.get((m.group, m.level_id))
      if m.category == "LINTEL" and m.covered_by_band and mid in rows and owner is not None:
        by_mid[str(owner.measurement_id)] = owner
        per_loser[mid].append([str(owner.measurement_id), "OVERLAP_ALLOCATION", BAND_RULE, float(rows[mid].quantity) * 1e9, []])
        replaced_lintels += 1
  stats["lintels_replaced_by_band"] = replaced_lintels
  out_deductions: list = []
  net_of: dict = {}
  over: set = set()
  
  by_rule: Counter = Counter()
  for mid, entries in per_loser.items():
    row = rows[mid]
    gross = _mm3_to_m3(sum(e[3] for e in entries))
    scale = Decimal("1")
    limit = q6(Decimal(row.quantity))
    if q6(gross) > limit and gross > 0:
      scale = limit / gross
      over.add(mid)
    total = Decimal("0")
    for owner, dtype, rule, mm3, items in entries:
      q = q6(_mm3_to_m3(mm3) * scale)
      if q <= 0:
        continue
    
      total += q
      slices = [(za, zb, m) for d, _ in items for za, zb, m in _band_slices(d)]
      merged = [[round(za, 1), round(zb, 1), round(m, 1)] for za, zb, m in slices]
      out_deductions.append(Deduction(
        from_solid_id=solid_id_of(ctx, mid), to_solid_id=solid_id_of(ctx, owner), deduction_type=dtype, quantity=q, unit=UNIT, rule_code=rule,
        geometry={"method": "pdf_member_prisms", "owner_measurement_id": owner, "parts": len(items), "bands": merged},
        explanation=("The tie band at lintel level runs over the opening of this lintel, so the band is counted and the separate lintel is not." if rule == BAND_RULE else
          f"{ROLE_OF.get(by_mid[mid].category, by_mid[mid].category).lower()} volume shared with {ROLE_OF.get(by_mid[owner].category, by_mid[owner].category).lower()}; "
          f"owned by the latter under {convention.code}.")))
      
      by_rule[rule] += 1
    net_of[mid] = max(Decimal("0"), q6(limit - total))
  stats["deductions"] = len(out_deductions)
  stats["deducted_m3"] = str(q6(sum((d.quantity for d in out_deductions), Decimal("0"))))
  stats["by_rule"] = dict(sorted(by_rule.items()))
  if over:
    stats["over_deducted"] = len(over)
  if conservation:
    stats["conservation_failures"] = list(conservation)

  ded_of_row: dict = defaultdict(list)
  for d in out_deductions:
    ded_of_row[d.from_solid_id].append(d)
  setups: dict = {}
  if stage_on:
    floors_by_group: dict = defaultdict(list)
    for f in getattr(takeoff, "floors", ()) or ():
      floors_by_group[f.group].append(f)
    for group in sorted({m.group for m in members}):
      setups[group] = pdf_datums(ctx, floors_by_group.get(group, []), _lintel_z(members, group))
    stats["datums"] = {g: S.datum_payload(s) for g, s in sorted(setups.items())}

  parts_of: dict = defaultdict(list)
  for p in parts:
    parts_of[str(p.measurement_id)].append(p)
  out: list = []
  replaced: list = []
  added: list = []
  cut = tagged = 0
  per_stage: Counter = Counter()
  
  for row in ledger:
    mid = ((row.trace or {}).get("inputs") or {}).get("measurement_id") if getattr(row, "source_kind", None) == SOURCE_KIND else None
    m = by_mid.get(str(mid)) if mid else None
    if m is None or str(mid) not in rows or rows[str(mid)] is not row:
      out.append(row)
      continue
    mid = str(mid)
    net = net_of.get(mid, q6(row.quantity))
    changed = mid in net_of
    steps = list((row.trace or {}).get("steps") or [])
    
    if changed:
      steps.append({"op": "space_gross_volume", "m3": str(q6(row.quantity))})
      for d in ded_of_row.get(solid_id_of(ctx, mid), []):
        steps.append({"op": "deduction", "type": d.deduction_type, "m3": str(d.quantity), "rule": d.rule_code, "note": d.explanation,
          "to_solid_id": str(d.to_solid_id)})
      steps.append({"op": "net_volume", "m3": str(net)})
    warnings = list(row.warnings)
    if mid in over:
      warnings.append(CODE_OVER)
    if mid in same_role:
      warnings.append(CODE_SAME)
    if mid in {str(u) for u in unplaced}:
      warnings.append(CODE_UNPLACED)
    pieces: dict = {}
    setup = setups.get(m.group)
    height_known = m.z0_mm is not None and m.z1_mm is not None and float(m.z1_mm) > float(m.z0_mm)
    if stage_on and setup is not None and setup.resolved and height_known and net > 0:
      mine = parts_of.get(mid)
      
      if mine:
        for p in mine:
          slices = [s for d in taken_by_part.get(p.sid, []) for s in _band_slices(d)]
          for stage, mm3 in _stage_pieces(setup, p.z0, p.z1, p.poly.area, slices).items():
            pieces[stage] = pieces.get(stage, 0.0) + mm3
      else:
        pieces = {s: v for s, v in _stage_pieces(setup, float(m.z0_mm), float(m.z1_mm), 1.0, []).items()}
    if stage_on and not height_known:
      warnings.append(CODE_NO_HEIGHT)
    if pieces and sum(pieces.values()) > 0:
      total = sum(pieces.values())
      shares = {s: net * Decimal(repr(v / total)) for s, v in pieces.items()}
      qty = {s: q6(v) for s, v in shares.items()}
      biggest = max(sorted(qty), key=lambda s: qty[s])
      qty[biggest] = q6(qty[biggest] + (net - sum(qty.values(), Decimal("0"))))
      made = []
      for stage in sorted(qty, key=lambda s: [b.stage for b in setup.bands].index(s)):
        if qty[stage] <= 0:
          continue
      
        band = next(b for b in setup.bands if b.stage == stage)
        trace = dict(row.trace)
        inputs = dict(trace.get("inputs") or {})
        inputs["work_stage"] = stage
        inputs["stage_split"] = {"of_m3": str(net), "z_from_mm": round(float(m.z0_mm), 1), "z_to_mm": round(float(m.z1_mm), 1), "grade": m.z_grade}
        trace["inputs"] = inputs
        trace["steps"] = [*steps, {"op": "stage_volume", "stage": stage, "m3": str(qty[stage])}]
        trace["net"] = {UNIT: str(qty[stage])}
        
        w = list(warnings)
        if band.defaulted:
          w.append(CODE_SPLIT_DEFAULT)
        made.append(replace(row, quantity=qty[stage], work_stage=stage, trace=trace, warnings=tuple(dict.fromkeys(w))))
        per_stage[stage] += 1
      if made:
        cut += 1
        replaced.append((row.solid_id, row.work_item_code))
        added.extend(made)
        out.extend(made)
        continue
    
    if changed:
      if net <= 0:
        replaced.append((row.solid_id, row.work_item_code))
        continue
      trace = dict(row.trace)
      trace["steps"], trace["net"] = steps, {UNIT: str(net)}
      new = replace(row, quantity=net, trace=trace, warnings=tuple(dict.fromkeys(warnings)))
      replaced.append((row.solid_id, row.work_item_code))
      added.append(new)
      out.append(new)
      tagged += 1
      continue
  
    if tuple(dict.fromkeys(warnings)) != tuple(row.warnings):
      new = replace(row, warnings=tuple(dict.fromkeys(warnings)))
      replaced.append((row.solid_id, row.work_item_code))
      added.append(new)
      out.append(new)
      continue
    out.append(row)
  out.sort(key=lambda r: (r.work_item_code, str(r.level_id), str(r.solid_id), r.work_stage or ""))
  stats.update({"rows_cut": cut, "rows_netted": tagged, "rows_by_stage": dict(sorted(per_stage.items()))})
  return SpaceResult(ledger=out, replaced=replaced, added=added, deductions=out_deductions, stats=stats)


def space_check(solids: list, ledger: list, deductions=()) -> list:
  """What allocation and the stage cut must keep true: a deduction points at two PDF solids of the run and is a positive amount of m3; a PDF row carries a work
  stage only when it is one of the pieces its measurement was cut into, and the pieces of a measurement sit in different stages."""
  by_id = {s.id for s in solids}
  failures: list = []
  
  for d in deductions or ():
    if d.from_solid_id not in by_id or d.to_solid_id not in by_id:
      failures.append(f"PDF deduction references an unknown solid {d.from_solid_id}")
    if d.unit != UNIT or d.quantity <= 0:
      failures.append(f"PDF deduction on solid {d.from_solid_id} is not a positive quantity in m3")
    if d.from_solid_id == d.to_solid_id:
      failures.append(f"PDF deduction from a solid to itself {d.from_solid_id}")
  seen: set = set()
  
  for r in ledger:
    if getattr(r, "source_kind", None) != SOURCE_KIND:
      continue
    key = (r.solid_id, r.work_item_code, r.work_stage)
    if key in seen:
      failures.append(f"two PDF rows for {key}")
    seen.add(key)
    if r.work_stage is not None and (r.trace or {}).get("inputs", {}).get("work_stage") != r.work_stage:
      failures.append(f"PDF row on solid {r.solid_id} has stage {r.work_stage} that its trace does not give")
  return failures
