from __future__ import annotations
import os
import re
from app.modules.drawings_boq.takeoff.prep.facts import FLOOR_ORDER, floor_heights
from app.modules.drawings_boq.takeoff.prep.storeys import storey_heights
from app.modules.drawings_boq.takeoff.model.types import Source, Level, Decision, PERSON, SECTION, PLAN_NOTES, LEVEL_MARKS, ASSUMED, TRUST
from dataclasses import dataclass

ENV_SWITCH = "TRACE_LEVELS"
ENTRY, MODEL = "entry", "model"
DISAGREE_MM = 50.0
PRINTED_MARK, SUM_OF_STOREYS, AT_DATUM, TYPED, TYPICAL = "PRINTED_MARK", "SUM_OF_STOREYS", "AT_DATUM", "TYPED", "TYPICAL"
LEVEL, CLEAR, F2F = "level_mm", "clear_mm", "floor_to_floor_mm"
KIND_OF_BASIS = {"SECTION": SECTION, "PLAN_NOTES": PLAN_NOTES, "LEVEL_MARKS": LEVEL_MARKS}
PRINTED_KINDS = (SECTION, PLAN_NOTES, LEVEL_MARKS)
FFL, SLAB = "FFL", "SLAB_"

def mode() -> str:
  return ENTRY if os.environ.get(ENV_SWITCH, "").strip().lower() == ENTRY else MODEL

def _num(v) -> float | None:
  try:
    f = float(v)
  except (TypeError, ValueError):
    return None
  return f if f == f and f > 0 else None

def _signed(v) -> float | None:
  try:
    f = float(v)
  except (TypeError, ValueError):
    return None
  return f if f == f else None

NORM = {LEVEL: _signed, CLEAR: _num, F2F: _num}

def kind_of(entry: dict) -> str:
  return KIND_OF_BASIS.get(str((entry or {}).get("basis") or ""), ASSUMED)

def candidates(project_facts: dict) -> dict:
  pf = project_facts or {}
  ladder = floor_heights(pf.get("schedule_floor_keys") or [], pf.get("ladder") or {}, pf.get("slab_mm"))
  storeys = storey_heights(pf.get("floor_keys") or [], pf.get("storeys"))
  out: dict = {}
  for source in (ladder, storeys):
    for key, entry in source.items():
      out.setdefault(key, []).append((kind_of(entry), entry))
  for rows in out.values():
    rows.sort(key=lambda r: TRUST.index(r[0]))
  return out

def candidates_of_heights(heights: dict | None) -> dict:
  return {k: [(kind_of(e), e)] for k, e in (heights or {}).items() if isinstance(e, dict)}

def merged_heights(cands: dict) -> dict:
  return {k: dict(rows[0][1]) for k, rows in cands.items() if rows}

def _pick(rows: list, how: str) -> dict:
  picked: dict = {"used": {}}
  if how == ENTRY:
    entry = rows[0][1]
    for f in (LEVEL, CLEAR, F2F):
      picked[f] = NORM[f](entry.get(f))
      if picked[f] is not None:
        picked["used"][f] = 0
    picked["basis"] = entry.get("basis")
    return picked
  for f in (LEVEL, CLEAR, F2F):
    picked[f] = None
    for i, (_, e) in enumerate(rows):
      v = NORM[f](e.get(f))
      if v is not None:
        picked[f], picked["used"][f] = v, i
        break
  contributing = [picked["used"][f] for f in (CLEAR, F2F) if f in picked["used"]] or [picked["used"].get(LEVEL, 0)]
  picked["basis"] = rows[max(contributing)][1].get("basis")
  return picked

def _sources(rows: list, picked: dict, level_how: str, level) -> tuple:
  out = []
  for f in (LEVEL, CLEAR, F2F):
    for i, (kind, e) in enumerate(rows):
      v = NORM[f](e.get(f))
      if v is None:
        continue
      basis = str(e.get("basis") or "")
      what = TYPICAL if (f != LEVEL and basis == "TYPICAL") else PRINTED_MARK
      used = picked["used"].get(f) == i and (f != LEVEL or level_how == PRINTED_MARK)
      out.append(Source(kind, f, round(v, 1), what, basis, used))
  if level_how in (SUM_OF_STOREYS, AT_DATUM) and level is not None:
    out.append(Source(ASSUMED, LEVEL, round(level, 1), level_how, "", True))
  return tuple(out)

def resolve(cands: dict, floor_keys: list | None, how: str | None = None, person: dict | None = None) -> list:
  how = how or mode()
  person = person or {}
  p_levels, p_tops = person.get("levels") or {}, person.get("tops") or {}
  keys = [k for k in FLOOR_ORDER if k in set(floor_keys or ()) | set(cands)]
  rows_of = {k: cands.get(k) or [(ASSUMED, {})] for k in keys}
  pk = {k: _pick(rows_of[k], how) for k in keys}
  levels: dict = {}

  def unplaced(key):
    p = pk[key]
    levels[key] = Level(key, None, p[CLEAR], p[F2F], _sources(rows_of[key], p, "", None), str(p["basis"] or ""), "")

  def place(key, level, level_how):
    p = pk[key]
    f2f = p[F2F]
    src = list(_sources(rows_of[key], p, level_how, level))
    if key in p_tops:
      f2f = round(float(p_tops[key]) - level, 1)
      if f2f > 0:
        src.insert(0, Source(PERSON, F2F, f2f, TYPED, "", True))
      else:
        f2f = p[F2F]
    if level_how == TYPED:
      src.insert(0, Source(PERSON, LEVEL, round(level, 1), TYPED, "", True))
    levels[key] = Level(key, round(float(level), 1), p[CLEAR], f2f, tuple(src), str(p["basis"] or ""), level_how)

  def printed(key, datum_zero, below=None):
    if key in p_levels:
      return float(p_levels[key]), TYPED
    if below in p_tops:
      return float(p_tops[below]), TYPED
    own = pk[key][LEVEL]
    return (own, PRINTED_MARK) if own is not None and datum_zero else (None, None)

  if "GROUND" not in keys:
    for k in keys:
      unplaced(k)
    return [levels[k] for k in keys]
  g_level, g_how = printed("GROUND", True, "BASEMENT" if "BASEMENT" in keys else None)
  datum_zero = g_level is not None
  place("GROUND", g_level if g_level is not None else 0.0, g_how or AT_DATUM)
  prev, broken = "GROUND", False
  for key in [k for k in keys if FLOOR_ORDER.index(k) > FLOOR_ORDER.index("GROUND")]:
    if broken:
      unplaced(key)
      continue
  
    lvl, lhow = printed(key, datum_zero, prev)
    if lvl is not None:
      place(key, lvl, lhow)
    elif levels[prev].f2f_mm is not None:
      place(key, levels[prev].level_mm + levels[prev].f2f_mm, SUM_OF_STOREYS)
    else:
      broken = True
      unplaced(key)
      continue
    prev = key
    
  if "BASEMENT" in keys:
    lvl, lhow = printed("BASEMENT", datum_zero)
    f2f = pk["BASEMENT"][F2F]
    if lvl is not None:
      place("BASEMENT", lvl, lhow)
    elif f2f is not None:
      place("BASEMENT", levels["GROUND"].level_mm - f2f, SUM_OF_STOREYS)
    else:
      unplaced("BASEMENT")
  return [levels[k] for k in keys]

def placed(levels) -> list:
  return [l for l in levels if l.level_mm is not None]

def lowest(levels) -> Level | None:
  rows = placed(levels)
  return min(rows, key=lambda l: l.level_mm) if rows else None

def person_of(levels, typed: dict | None) -> dict:
  rows = placed(levels)
  out: dict = {"levels": {}, "tops": {}}
  for name, z in (typed or {}).items():
    try:
      z = float(z)
    except (TypeError, ValueError):
      continue
    n = str(name).upper()
    m = re.match(r"^SLAB_(\d+)$", n)
    if n == FFL and rows:
      out["levels"][rows[0].key] = z
    elif m and 1 <= int(m.group(1)) <= len(rows):
      out["tops"][rows[int(m.group(1)) - 1].key] = z
  return out

def _options(values: list) -> tuple:
  options: list = []
  for kind, v in values:
    for o in options:
      if abs(o["value"] - v) <= DISAGREE_MM:
        o["sources"].append(kind)
        break
    else:
      options.append({"value": round(v, 1), "sources": [kind]})
  return tuple(options)

def decisions_of(cands: dict, levels, person: dict | None = None) -> list:
  person = person or {}
  p_levels, p_tops = person.get("levels") or {}, person.get("tops") or {}
  by_key = {l.key: l for l in levels}
  out = []
  
  for key in [l.key for l in levels]:
    rows = cands.get(key) or []
    for f, ident, question in ((LEVEL, "level", f"Floor level of {key}"), (F2F, "f2f", f"Floor-to-floor height of {key}")):
      values = [(kind, NORM[f](e.get(f))) for kind, e in rows if kind in PRINTED_KINDS and NORM[f](e.get(f)) is not None]
      if len(values) < 2 or max(v for _, v in values) - min(v for _, v in values) <= DISAGREE_MM:
        continue
      options = _options(values)
      if len(options) < 2:
        continue
      lvl = by_key[key]
      chosen = None
      order = [l.key for l in levels]
      
      below = order[order.index(key) - 1] if order.index(key) > 0 else None
      if f == LEVEL and key in p_levels:
        chosen = round(float(p_levels[key]), 1)
      elif f == LEVEL and below in p_tops:
        chosen = round(float(p_tops[below]), 1)
      elif f == F2F and key in p_tops and lvl.level_mm is not None:
        chosen = round(float(p_tops[key]) - lvl.level_mm, 1)
      out.append(Decision(f"{ident}:{key}", question, options, chosen))
  return out

FLOOR_TO_FLOOR, FLOOR_TO_SOFFIT = "FLOOR_TO_FLOOR", "FLOOR_TO_SOFFIT"
HEIGHT_FIELD = {FLOOR_TO_FLOOR: F2F, FLOOR_TO_SOFFIT: CLEAR}
RULE, PLAN_NOTE = "RULE", "PLAN_NOTE"
HEIGHT_KINDS = {SECTION: "SECTION", PLAN_NOTES: "PLAN_NOTES", LEVEL_MARKS: "LEVEL_MARKS"}

def height(heights: dict | None, what: str, floor: str | None) -> tuple:
  entry = (heights or {}).get(floor or "") or {}
  field = HEIGHT_FIELD.get(what)
  v = NORM[field](entry.get(field)) if field else None
  source = {"what": what, "floor": floor, "kind": HEIGHT_KINDS.get(kind_of(entry), ASSUMED) if v is not None else "NONE", "basis": entry.get("basis"),
    "entry": {k: entry.get(k) for k in (LEVEL, CLEAR, F2F) if entry.get(k) is not None}}
  return (v, source) if v is not None else (None, source)

def rule_source(what: str, floor: str | None, key: str) -> dict:
  """The source of a height the rule book gives (a convention of the QS or of the company), named by its rule key."""
  return {"what": what, "floor": floor, "kind": RULE, "basis": key, "entry": {}}

def note_source(floor: str | None, heights: dict | None, mm: float) -> dict:
  """The source of a height written as a note on the plan, with the clear height the floor's entry prints when that differs from it by more than DISAGREE_MM (a STOREY_HEIGHT)."""
  clear, _ = height(heights, FLOOR_TO_SOFFIT, floor)
  out = {"what": FLOOR_TO_SOFFIT, "floor": floor, "kind": PLAN_NOTE, "basis": None, "entry": {}}
  if clear is not None and abs(clear - float(mm)) > DISAGREE_MM:
    out["disagrees"] = {"ladder_mm": round(clear, 1), "note_mm": round(float(mm), 1), "ladder_kind": HEIGHT_KINDS.get(kind_of((heights or {}).get(floor or "") or {}), ASSUMED)}
  return out

@dataclass(frozen=True)
class Ladder:
  levels: tuple = ()
  decisions: tuple = ()
  heights: dict = None

def build_all(project_facts: dict, typed: dict | None = None, how: str | None = None) -> Ladder:
  pf = project_facts or {}
  cands = candidates(pf)
  keys = pf.get("floor_keys") or []
  base = resolve(cands, keys, how)
  person = person_of(base, typed)
  levels = resolve(cands, keys, how, person) if (person["levels"] or person["tops"]) else base
  return Ladder(tuple(levels), tuple(decisions_of(cands, levels, person)), merged_heights(cands))

def build(project_facts: dict, typed: dict | None = None, how: str | None = None) -> list:
  return list(build_all(project_facts, typed, how).levels)

def from_heights(heights: dict | None, floor_keys: list | None, how: str | None = None) -> list:
  return resolve(candidates_of_heights(heights), floor_keys, how or ENTRY)

def rows_of(levels, decisions=()) -> list:
  by_floor: dict = {}
  for d in decisions:
    by_floor.setdefault(str(d.id).split(":", 1)[1], []).append(d.as_dict())
  return [{**l.as_dict(), "decisions": by_floor.get(l.key, [])} for l in levels]
