from __future__ import annotations
from collections import defaultdict
from dataclasses import replace
from decimal import Decimal
from app.engine.measure import rulebook as RB
from app.engine.measure import stages as S
from app.engine.measure.derived import NGL_PARAM, NGL_RANGE
from app.engine.measure.pdf_space import _stage_pieces
from app.engine.measure.takeoff import SOURCE_KIND
from app.engine.measure.units import q6

TAGS = ("PLASTER-INSIDE", "PLASTER-OUTSIDE", "PAINT-INSIDE", "PAINT-OUTSIDE")
OUTSIDE_TAGS = ("PLASTER-OUTSIDE", "PAINT-OUTSIDE")
WALL = "WALL"
GROUND = "GROUND"
CODE_BY_HEIGHT = "FINISH_STAGE_BY_HEIGHT"
CODE_DEFAULTED = "STAGE_DATUM_DEFAULTED"
CODE_BELOW_GRADE = "FINISH_BELOW_GRADE"
CODE_PLINTH_FOR_NGL = "NGL_ASSUMED_PLINTH"
BELOW_GRADE_RULE = "finish.external_below_grade"
EXCLUDE, INCLUDE = "EXCLUDE", "INCLUDE"
BELOW_GRADE_MODES = (EXCLUDE, INCLUDE)
FROM_PARAM, FROM_PLINTH = "param", "plinth"

def _homes(takeoff) -> dict:
  out: dict = {}
  for m in getattr(takeoff, "space", ()) or ():
    if m.level_id is not None and m.floor and m.level_id not in out:
      out[m.level_id] = (m.group, m.floor)
  return out

def _wall_span(takeoff, group: str, floor: str):
  zs = [(float(m.z0_mm), float(m.z1_mm)) for m in getattr(takeoff, "space", ()) or ()
    if m.group == group and m.floor == floor and m.category == WALL and m.z0_mm is not None and m.z1_mm is not None and float(m.z1_mm) > float(m.z0_mm)]
  return (min(z[0] for z in zs), max(z[1] for z in zs)) if zs else None

def natural_ground(ctx, takeoff, group: str):
  """(z of the natural ground in the group's datum, where it comes from): the level typed as ngl_below_ffl_mm below the ground floor, else the plinth, which is the ground floor
  level less the DPC drop. None when the group has no ground floor."""
  ground = next((f for f in getattr(takeoff, "floors", ()) or () if f.group == group and f.key == GROUND), None)
  if ground is None or ground.level_mm is None:
    return None
  raw = (getattr(ctx, "derived_params", None) or {}).get(NGL_PARAM)
  raw = (ctx.convention_params or {}).get(NGL_PARAM) if raw is None else raw
  try:
    typed = float(raw) if raw is not None else None
  except (TypeError, ValueError):
    typed = None
  if typed is not None and NGL_RANGE[0] <= typed <= NGL_RANGE[1]:
    return float(ground.level_mm) - typed, FROM_PARAM
  return float(ground.level_mm) - S._p(ctx, "dpc_below_ffl_mm"), FROM_PLINTH

def _above_ground(row, span: tuple, ngl: tuple):
  z0, z1 = span
  if ngl[0] <= z0:
    return row, span
  keep = max(0.0, z1 - max(z0, ngl[0])) / (z1 - z0)
  kept = q6(row.quantity * Decimal(repr(keep)))
  if kept <= 0:
    return None, span

  trace = dict(row.trace)
  ins = dict(trace.get("inputs") or {})
  ins["below_grade"] = {"of_m2": str(row.quantity), "ngl_z_mm": round(ngl[0], 1), "ngl_from": ngl[1], "z_from_mm": round(z0, 1), "z_to_mm": round(z1, 1), "removed_m2": str(row.quantity - kept), "share_above": round(keep, 6)}
  trace["inputs"] = ins
  trace["steps"] = [*list(trace.get("steps") or []), {"op": "below_grade_cut", "ngl_z_mm": round(ngl[0], 1), "m2": str(kept), "removed_m2": str(row.quantity - kept)}]
  trace["net"] = {"m2": str(kept)}
  warnings = [*row.warnings, CODE_BELOW_GRADE, *([CODE_PLINTH_FOR_NGL] if ngl[1] == FROM_PLINTH else [])]
  return replace(row, quantity=kept, trace=trace, warnings=tuple(dict.fromkeys(warnings))), (max(z0, ngl[0]), z1)

def cut_finishes(ctx, ledger: list, setups: dict) -> tuple:
  takeoff = getattr(ctx, "takeoff", None)
  stats: dict = {"rows_split": 0, "rows_tagged": 0, "rows_by_stage": {}}
  replaced: list = []
  added: list = []
  
  if takeoff is None or not setups:
    return list(ledger), replaced, added, stats
  homes = _homes(takeoff)
  out: list = []
  per_stage: dict = defaultdict(int)
  mode = str(RB.pick(BELOW_GRADE_RULE, EXCLUDE)).upper()
  ground: dict = {}
  for row in ledger:
    inputs = (row.trace or {}).get("inputs") or {}
    home = homes.get(row.level_id)
    setup = setups.get(home[0]) if home else None
    span = _wall_span(takeoff, *home) if home else None
    if getattr(row, "source_kind", None) != SOURCE_KIND or inputs.get("tag") not in TAGS or row.work_stage or span is None:
      out.append(row)
      continue
    whole = row
    
    if mode == EXCLUDE and inputs.get("tag") in OUTSIDE_TAGS:
      if home[0] not in ground:
        ground[home[0]] = natural_ground(ctx, takeoff, home[0])
      if ground[home[0]] is not None:
        row, span = _above_ground(row, span, ground[home[0]])
    if row is None or row is not whole:
      stats["rows_below_grade"] = stats.get("rows_below_grade", 0) + 1
      stats["removed_m2"] = str(Decimal(stats.get("removed_m2", "0")) + whole.quantity - (row.quantity if row is not None else Decimal("0")))
      replaced.append((whole.solid_id, whole.work_item_code))
      
    if row is None:
      continue
    if setup is None or not setup.resolved:
      out.append(row)
      if row is not whole:
        added.append(row)
      continue
    pieces = _stage_pieces(setup, span[0], span[1], 1.0, [])
    total = sum(pieces.values())
    if total <= 0:
      out.append(row)
      if row is not whole:
        added.append(row)
      continue
    order = [b.stage for b in setup.bands]
    stages = sorted(pieces, key=order.index)
    qty = {s: q6(row.quantity * Decimal(repr(pieces[s] / total))) for s in stages}
    biggest = max(stages, key=lambda s: (qty[s], -order.index(s)))
    qty[biggest] = q6(qty[biggest] + (row.quantity - sum(qty.values(), Decimal("0"))))
    
    made = []
    for s in stages:
      if qty[s] <= 0:
        continue
      band = next(b for b in setup.bands if b.stage == s)
      warnings = list(row.warnings)
      if band.defaulted:
        warnings.append(CODE_DEFAULTED)
      if len(stages) > 1:
        warnings.append(CODE_BY_HEIGHT)
      trace = dict(row.trace)
      ins = dict(trace.get("inputs") or {})
      ins["work_stage"] = s
      ins["stage_split"] = {"of_m2": str(row.quantity), "z_from_mm": round(span[0], 1), "z_to_mm": round(span[1], 1), "share": round(pieces[s] / total, 6)}
      trace["inputs"] = ins
      trace["steps"] = [*list(trace.get("steps") or []), {"op": "stage_area", "stage": s, "m2": str(qty[s]), "from_mm": round(max(span[0], band.lo), 1), "to_mm": round(min(span[1], band.hi), 1)}]
      trace["net"] = {"m2": str(qty[s])}
      made.append(replace(row, quantity=qty[s], work_stage=s, trace=trace, warnings=tuple(dict.fromkeys(warnings))))
      per_stage[s] += 1
    if not made:
      out.append(row)
      if row is not whole:
        added.append(row)
      continue
    out.extend(made)
    added.extend(made)
    if row is whole:
      replaced.append((whole.solid_id, whole.work_item_code))
    stats["rows_split" if len(made) > 1 else "rows_tagged"] += 1
  stats["rows_by_stage"] = dict(sorted(per_stage.items()))
  out.sort(key=lambda r: (r.work_item_code, str(r.level_id), str(r.solid_id), r.work_stage or ""))
  return out, replaced, added, stats
