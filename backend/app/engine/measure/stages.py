from __future__ import annotations
import math
from dataclasses import dataclass, field, replace
from app.engine.measure.models import CalculationContext, LedgerEntry, ModelElement, Solid
from app.engine.measure.spatial import prism_and_polygon
from collections import Counter
from decimal import Decimal
from app.engine.measure.units import q6

BELOW_PLINTH = "BELOW_PLINTH"
PLINTH_TO_LINTEL = "PLINTH_TO_LINTEL"
LINTEL_TO_SLAB = "LINTEL_TO_SLAB"
TOP = "TOP"
PARAPET = "PARAPET"
MUMTY = "MUMTY"

STAGE_LABELS = {
  BELOW_PLINTH: "below plinth",
  PLINTH_TO_LINTEL: "plinth to lintel",
  LINTEL_TO_SLAB: "lintel to slab",
  TOP: "above roof slab",
  PARAPET: "roof parapet",
  MUMTY: "mumty and above",
}

def upper_floor(k: int) -> str:
  return f"UPPER_FLOOR_{k}"

def stage_label(stage: str | None) -> str | None:
  if not stage:
    return None
  if stage.startswith("UPPER_FLOOR_"):
    return f"upper floor {stage.rsplit('_', 1)[1]}"
  return STAGE_LABELS.get(stage, stage.replace("_", " ").lower())

DEFAULTS = {
  "dpc_below_ffl_mm": 0.0,
  "lintel_height_mm": 2134.0,
  "min_storey_mm": 2400.0,
  "slab_cluster_mm": 300.0,
  "floor_slab_min_area_frac": 0.5,
  "stage_snap_mm": 5.0,
  "parapet_height_mm": 914.4,
}
OVERRIDE_RANGE = (-100000.0, 300000.0)
MIN_PARAPET_MM = 100.0
FFL_BIN_MM = 5.0
HEAD_CLEARANCE_MM = 100.0
OPENING_ROLES = ("DOOR", "WINDOW")
NEG, POS = -math.inf, math.inf

CODE_DATUM_DEFAULTED = "DATUM_DEFAULTED"
CODE_NOT_SPLIT = "STAGE_NOT_SPLIT"
CODE_UNRESOLVED = "STAGE_UNRESOLVED"
CODE_APPORTIONED = "STAGE_DEDUCTION_APPORTIONED"

@dataclass(frozen=True)
class Datum:
  name: str
  z_mm: float
  source: str   
  note: str = ""

@dataclass(frozen=True)
class Band:
  stage: str
  lo: float
  hi: float
  defaulted: bool
  soft: bool = False

@dataclass(frozen=True)
class StageSetup:
  datums: tuple = ()
  bands: tuple = ()
  reason: str | None = None

  @property
  def resolved(self) -> bool:
    return bool(self.bands)

def _p(ctx: CalculationContext, key: str) -> float:
  value = (ctx.convention_params or {}).get(key)
  try:
    return float(value) if value is not None else DEFAULTS[key]
  except (TypeError, ValueError):
    return DEFAULTS[key]

def _given(ctx: CalculationContext, key: str) -> bool:
  return (ctx.convention_params or {}).get(key) is not None

def typed_overrides(ctx: CalculationContext) -> dict:
  out: dict = {}
  for name, value in (getattr(ctx, "datum_overrides", None) or {}).items():
    if isinstance(value, bool):
      continue
    try:
      z = float(value)
    except (TypeError, ValueError):
      continue
  
    if z == z and OVERRIDE_RANGE[0] <= z <= OVERRIDE_RANGE[1]:
      out[str(name).upper()] = z
  return out

def _typed(name: str, z: float, what: str) -> Datum:
  return Datum(name, z, "typed", f"{what}; the level you typed")

def element_z(el: ModelElement):
  
  pl = el.placement or {}
  lo, hi = pl.get("z_min_mm"), pl.get("z_max_mm")
  try:
    if lo is not None and hi is not None and float(hi) > float(lo):
      return float(lo), float(hi)
  except (TypeError, ValueError):
    pass
  if el.bbox_min_mm and el.bbox_max_mm:
    try:
      lo, hi = float(el.bbox_min_mm[2]), float(el.bbox_max_mm[2])
    except (TypeError, ValueError, IndexError):
      return None
    if hi > lo:
      return lo, hi
    try:
      height = float(getattr(el, "height_mm", None) or 0)
    except (TypeError, ValueError):
      height = 0.0
    if height > 0 and (el.role or "").upper() in OPENING_ROLES:
      return lo, lo + height
  return None

def _plan_area(el: ModelElement) -> float:
  found = prism_and_polygon(el)
  if found is not None:
    return float(found[1].area)
  if el.bbox_min_mm and el.bbox_max_mm:
    try:
      return max(0.0, (float(el.bbox_max_mm[0]) - float(el.bbox_min_mm[0])) * (float(el.bbox_max_mm[1]) - float(el.bbox_min_mm[1])))
    except (TypeError, ValueError, IndexError):
      return 0.0
  return 0.0

def _ffl(ctx: CalculationContext, doors: list) -> float | None:
  if not doors:
    return None
  bases = sorted(round(z0 / FFL_BIN_MM) * FFL_BIN_MM for z0, _ in doors)
  lowest = bases[0]
  ground = [b for b in bases if b < lowest + _p(ctx, "min_storey_mm")]
  counts = Counter(ground)
  top = max(counts.values())
  return min(b for b, n in counts.items() if n == top)

def _slab_clusters(ctx: CalculationContext, elements: list, ffl: float) -> list:
  tol, storey = _p(ctx, "slab_cluster_mm"), _p(ctx, "min_storey_mm")
  slabs = []
  for el in elements:
    role = (el.role or "").upper()
    if not role.startswith("SLAB") or role in ("SLAB_FOUNDATION", "SLAB_GROUND"):
      continue
    z = element_z(el)
    if z is None or z[1] < ffl + storey:
      continue
    slabs.append((z[1], _plan_area(el)))
  slabs.sort()
  clusters: list = []
  for top, area in slabs:
    if clusters and top - clusters[-1]["first"] <= tol:
      clusters[-1]["top"] = max(clusters[-1]["top"], top)
      clusters[-1]["area"] += area
    else:
      clusters.append({"first": top, "top": top, "area": area})
  return clusters

def _floor_slab_tops(ctx: CalculationContext, elements: list, ffl: float) -> list:
  storey = _p(ctx, "min_storey_mm")
  clusters = _slab_clusters(ctx, elements, ffl)
  if not clusters:
    return []
  biggest = max(c["area"] for c in clusters)
  keep = [c["top"] for c in clusters if c["area"] >= _p(ctx, "floor_slab_min_area_frac") * biggest]
  tops: list = []
  for t in sorted(keep):
    if tops and t - tops[-1] < storey:
      continue
    tops.append(t)
  return tops

def _mumty_top(ctx: CalculationContext, elements: list, ffl: float, roof: float) -> float | None:
  """The top of a small slab standing a storey above the roof slab: the roof of a stair room (mumty). It is not a floor, so it is not a slab datum; it is
  shown beside the datums so the stage above the parapet can be read as the mumty."""
  storey = _p(ctx, "min_storey_mm")
  small = [c["top"] for c in _slab_clusters(ctx, elements, ffl) if c["top"] >= roof + storey]
  return max(small) if small else None

def build_setup(ctx: CalculationContext, ffl: Datum, dpc: Datum, lintel: Datum, slabs: list, extra: tuple = ()) -> StageSetup:
  """The bands of work from the datums found on the model or the drawing, after the levels typed by the person have been put in. Shared by the model and the PDF.
  Below the roof slab: below plinth, plinth to lintel, lintel to slab, one band for every upper floor. Above it: the parapet (a set height, taken as a default
  unless the convention gives it or the person types its top) and above that the mumty, a soft band. With no parapet height the whole of it is one band."""
  zs = [s.z_mm for s in slabs]
  if not zs:
    return StageSetup(reason="NO_FLOOR_SLAB_FOUND")
  if not dpc.z_mm < lintel.z_mm < zs[0] or any(b <= a for a, b in zip(zs, zs[1:])):
    return StageSetup(reason="DATUMS_OUT_OF_ORDER")
  datums = [ffl, dpc, lintel, *slabs]
  bands = [
    Band(BELOW_PLINTH, NEG, dpc.z_mm, dpc.source == "default"),
    Band(PLINTH_TO_LINTEL, dpc.z_mm, lintel.z_mm, dpc.source == "default" or lintel.source == "default"),
    Band(LINTEL_TO_SLAB, lintel.z_mm, zs[0], lintel.source == "default"),
  ]
  for i in range(1, len(zs)):
    bands.append(Band(upper_floor(i), zs[i - 1], zs[i], False))
  roof = zs[-1]
  typed = typed_overrides(ctx).get("PARAPET_TOP")
  height = _p(ctx, "parapet_height_mm")
  if typed is not None and typed >= roof + MIN_PARAPET_MM:
    top = Datum("PARAPET_TOP", typed, "typed", "top of the parapet; the level you typed")
  elif height >= MIN_PARAPET_MM:
    given = _given(ctx, "parapet_height_mm")
    top = Datum("PARAPET_TOP", roof + height, "param" if given else "default",
      "roof slab top plus the parapet height" if given else "no parapet level in the model; roof slab top plus an assumed parapet height")
  else:
    top = None
  if top is None:
    bands.append(Band(TOP, roof, POS, False))
  else:
    datums.append(top)
    bands.append(Band(PARAPET, roof, top.z_mm, top.source == "default"))
    bands.append(Band(MUMTY, top.z_mm, POS, top.source == "default", soft=True))
  datums.extend(extra)
  return StageSetup(datums=tuple(datums), bands=tuple(bands))

def dpc_datum(ctx: CalculationContext, elements: list) -> Datum | None:
  typed = typed_overrides(ctx)
  if "DPC" in typed:
    return _typed("DPC", typed["DPC"], "damp-proof course level")
  if "FFL" in typed:
    ffl = typed["FFL"]
  else:
    doors = []
    
    for el in elements:
      if (el.role or "").upper() == "DOOR":
        z = element_z(el)
        if z is not None:
          doors.append(z)
    ffl = _ffl(ctx, doors)
  if ffl is None:
    return None
  given = _given(ctx, "dpc_below_ffl_mm")
  return Datum("DPC", ffl - _p(ctx, "dpc_below_ffl_mm"), "param" if given else "default",
    "floor level less the DPC drop" if given else "no DPC level in the model; taken at floor level")

def derive_datums(ctx: CalculationContext, elements: list) -> StageSetup:
  typed = typed_overrides(ctx)
  doors, heads = [], []
  for el in elements:
    if (el.role or "").upper() in OPENING_ROLES:
      z = element_z(el)
      if z is not None:
        heads.append(z)
        if el.role.upper() == "DOOR":
          doors.append(z)
  found_ffl = _ffl(ctx, doors)
  if "FFL" in typed:
    ffl = _typed("FFL", typed["FFL"], "finished level of the lowest storey")
  elif found_ffl is not None:
    ffl = Datum("FFL", found_ffl, "model", "most common door threshold on the lowest storey")
  else:
    return StageSetup(reason="NO_DOORS_FOR_FLOOR_LEVEL")
  tops = _floor_slab_tops(ctx, elements, ffl.z_mm)
  slabs = []
  
  for i, z in enumerate(tops):
    name = f"SLAB_{i + 1}"
    slabs.append(_typed(name, typed[name], "top of the floor slab") if name in typed else Datum(name, z, "model", "top of the floor slab"))
  if not slabs and "SLAB_1" in typed:
    slabs = [_typed("SLAB_1", typed["SLAB_1"], "top of the floor slab")]
  if not slabs:
    return StageSetup(reason="NO_FLOOR_SLAB_FOUND")

  dpc_given = _given(ctx, "dpc_below_ffl_mm")
  if "DPC" in typed:
    dpc = _typed("DPC", typed["DPC"], "damp-proof course level")
  else:
    dpc = Datum("DPC", ffl.z_mm - _p(ctx, "dpc_below_ffl_mm"), "param" if dpc_given else "default",
      "floor level less the DPC drop" if dpc_given else "no DPC level in the model; taken at floor level")
  first = slabs[0].z_mm
  below = [hi for lo, hi in heads if lo < first and dpc.z_mm < hi < first - HEAD_CLEARANCE_MM]
  if "LINTEL" in typed:
    lintel = _typed("LINTEL", typed["LINTEL"], "lintel level")
  elif below:
    lintel = Datum("LINTEL", max(below), "model", "highest door or window head below the first slab")
  else:
    lintel = Datum("LINTEL", ffl.z_mm + _p(ctx, "lintel_height_mm"), "param" if _given(ctx, "lintel_height_mm") else "default",
      "no opening heads below the first slab; floor level plus the lintel height")
  extra = []
  mumty = _mumty_top(ctx, elements, ffl.z_mm, slabs[-1].z_mm)
  if mumty is not None:
    extra.append(Datum("MUMTY_SLAB", mumty, "model", "top of a small slab a storey above the roof: taken as the roof of the stair room (mumty)"))
  return build_setup(ctx, ffl, dpc, lintel, slabs, tuple(extra))

def stage_of(setup: StageSetup, z: float) -> Band:
  for band in setup.bands:
    if band.lo <= z < band.hi:
      return band
  return setup.bands[-1]

def _crossings(setup: StageSetup, z0: float, z1: float, snap: float) -> list:
  return [b.lo for b in setup.bands if b.lo != NEG and not b.soft and z0 + snap < b.lo < z1 - snap]

def datum_payload(setup: StageSetup) -> dict:
  if not setup.resolved:
    return {"resolved": False, "reason": setup.reason}
  return {"resolved": True, "datums": [{"name": d.name, "z_mm": round(d.z_mm, 1), "source": d.source, "note": d.note} for d in setup.datums],
    "bands": [{"stage": b.stage, "from_mm": None if b.lo == NEG else round(b.lo, 1), "to_mm": None if b.hi == POS else round(b.hi, 1),
      "defaulted": b.defaulted, "soft": b.soft} for b in setup.bands]}

def unused_overrides(ctx: CalculationContext, setups) -> list:
  typed = typed_overrides(ctx)
  names = {d.name for s in setups if s.resolved for d in s.datums if d.source == "typed"}
  return sorted(n for n in typed if n not in names)

def _d(x: float) -> Decimal:
  return Decimal(repr(float(x)))

def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
  return max(0.0, min(a1, b1) - max(a0, b0))

def _share(d, pieces: list, z0: float, z1: float):
  
  geo = d.geometry or {}
  weights = None
  if geo.get("bands"):
    weights = [sum(m * _overlap(za, zb, p0, p1) / (zb - za) for za, zb, m in geo["bands"] if zb > za) for p0, p1 in pieces]
  elif geo.get("z_min_mm") is not None and geo.get("z_max_mm") is not None and geo["z_max_mm"] > geo["z_min_mm"]:
    weights = [_overlap(geo["z_min_mm"], geo["z_max_mm"], p0, p1) for p0, p1 in pieces]
  total = sum(weights) if weights else 0.0
  if total > 0:
    return [w / total for w in weights], False
  height = z1 - z0
  return [(p1 - p0) / height for p0, p1 in pieces], True

@dataclass(frozen=True)
class StageResult:
  ledger: list                                   
  replaced: list = field(default_factory=list)   
  added: list = field(default_factory=list)    
  stats: dict = field(default_factory=dict)

def _tag(row: LedgerEntry, band: Band | None, extra: tuple = ()) -> LedgerEntry:
  warnings = list(row.warnings)
  if band is not None and band.defaulted:
    warnings.append(CODE_DATUM_DEFAULTED)
  warnings.extend(extra)
  trace = dict(row.trace)
  inputs = dict(trace.get("inputs") or {})
  if band is not None:
    inputs["work_stage"] = band.stage
  trace["inputs"] = inputs
  return replace(row, work_stage=band.stage if band else None, warnings=tuple(dict.fromkeys(warnings)), trace=trace)

def _pieces_of(row: LedgerEntry, solid: Solid, host_deds: list, cuts: list, z0: float, z1: float):
  points = [z0, *cuts, z1]
  spans = list(zip(points, points[1:]))
  height = z1 - z0
  gross = solid.gross_volume_m3
  shares = []
  apportioned = False
  for d in host_deds:
    s, fallback = _share(d, spans, z0, z1)
    shares.append(s)
    apportioned = apportioned or fallback
    
  raw = []
  base = q6(q6(gross) - q6(sum((d.quantity for d in host_deds), Decimal("0"))))
  scale = row.quantity / base if base > 0 and row.quantity != base else Decimal("1")
  for i, (p0, p1) in enumerate(spans):
    piece_gross = (gross * scale) * _d(p1 - p0) / _d(height)
    piece_deds = [d.quantity * scale * _d(shares[k][i]) for k, d in enumerate(host_deds)]
    raw.append((piece_gross, piece_deds))
    
  nets = [max(Decimal("0"), q6(g - sum(ds, Decimal("0")))) for g, ds in raw]
  biggest = max(range(len(nets)), key=lambda i: (nets[i], -i))
  nets[biggest] = q6(nets[biggest] + (row.quantity - sum(nets, Decimal("0"))))
  return spans, raw, nets, apportioned

def split_stages(ctx: CalculationContext, elements: list, solids: list, alloc, ledger: list, setup: StageSetup | None = None) -> StageResult:
  setup = setup if setup is not None else derive_datums(ctx, elements)
  stats = {"enabled": True, **datum_payload(setup), "unused_overrides": unused_overrides(ctx, [setup])}
  if not setup.resolved:
    stats.update({"rows_split": 0, "rows_tagged": 0})
    return StageResult(ledger=list(ledger), stats=stats)

  snap = _p(ctx, "stage_snap_mm")
  by_element = {e.id: e for e in elements}
  by_solid = {s.id: s for s in solids}
  deds: dict = {}
  for d in getattr(alloc, "deductions", ()) or ():
    if d.quantity > 0:
      deds.setdefault(d.from_solid_id, []).append(d)

  out: list = []
  replaced: list = []
  added: list = []
  counts = Counter()
  per_stage: Counter = Counter()
  for row in ledger:
    solid = by_solid.get(row.solid_id)
    el = by_element.get(row.element_id)
    if row.source_kind != "MODEL" or solid is None or el is None or row.formula_code not in ("SOLID_NET_VOLUME", "OPENING_COUNT"):
      out.append(row)
      continue
    span = element_z(el)
    if span is None:
      tagged = _tag(row, None, (CODE_UNRESOLVED,))
      out.append(tagged)
      replaced.append((row.solid_id, row.work_item_code))
      added.append(tagged)
      counts["unresolved"] += 1
      continue
  
    z0, z1 = span
    cuts = _crossings(setup, z0, z1, snap)
    prism = prism_and_polygon(el) if row.formula_code == "SOLID_NET_VOLUME" else None
    cuttable = bool(cuts) and prism is not None and prism[0].exact and (el.placement or {}).get("vertical") is not False \
      and solid.gross_volume_m3 is not None
    if cuttable:
      z0, z1 = prism[0].z0, prism[0].z1
      cuts = _crossings(setup, z0, z1, snap)
    if not cuttable:
      band = stage_of(setup, (z0 + z1) / 2)
      tagged = _tag(row, band, (CODE_NOT_SPLIT,) if cuts else ())
      out.append(tagged)
      replaced.append((row.solid_id, row.work_item_code))
      added.append(tagged)
      counts["not_split" if cuts else "tagged"] += 1
      per_stage[band.stage] += 1
      continue

    spans, raw, nets, apportioned = _pieces_of(row, solid, deds.get(row.solid_id, []), cuts, z0, z1)
    host_deds = deds.get(row.solid_id, [])
    made = []
    for i, (p0, p1) in enumerate(spans):
      if nets[i] <= 0:
        continue
      band = stage_of(setup, (p0 + p1) / 2)
      piece_gross, piece_deds = raw[i]
      steps = [{"op": "stage_gross_volume", "stage": band.stage, "z_from_mm": round(p0, 1), "z_to_mm": round(p1, 1), "m3": str(q6(piece_gross))}]
      for d, amount in zip(host_deds, piece_deds):
        if amount > 0:
          steps.append({"op": "deduction", "type": d.deduction_type, "m3": str(q6(amount)), "rule": d.rule_code,
            "note": d.explanation, "to_solid_id": str(d.to_solid_id) if d.to_solid_id else None})
          
      steps.append({"op": "net_volume", "m3": str(nets[i])})
      trace = dict(row.trace)
      trace["steps"] = steps
      trace["net"] = {"m3": str(nets[i])}
      inputs = dict(trace.get("inputs") or {})
      inputs["stage_split"] = {"of_m3": str(row.quantity), "z_from_mm": round(z0, 1), "z_to_mm": round(z1, 1)}
      trace["inputs"] = inputs
      made.append(_tag(replace(row, quantity=nets[i], trace=trace), band, (CODE_APPORTIONED,) if apportioned else ()))
      per_stage[band.stage] += 1
    if made:
      replaced.append((row.solid_id, row.work_item_code))
      out.extend(made)
      added.extend(made)
      counts["split"] += 1
    else:
      out.append(row)
  stats.update({"rows_split": counts["split"], "rows_tagged": counts["tagged"], "rows_not_split": counts["not_split"],
    "rows_unresolved": counts["unresolved"], "rows_by_stage": dict(sorted(per_stage.items()))})
  out.sort(key=lambda r: (r.work_item_code, str(r.level_id), str(r.element_id), r.work_stage or ""))
  return StageResult(ledger=out, replaced=replaced, added=added, stats=stats)
