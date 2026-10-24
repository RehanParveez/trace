from __future__ import annotations
from app.modules.drawings_boq.takeoff.prep.facts import FLOOR_ORDER

def level_key(sheet) -> str | None:
  """The floor a plan sheet shows (BASEMENT, GROUND, ...); None for a sheet that shows several drawings."""
  title = ((getattr(sheet, "prep_meta", None) or {}).get("title")) or {}
  return None if title.get("composite") else title.get("level_hint")

def _view_floor(cand) -> str | None:
  """The floor a stair was read for on a sheet that shows several plans."""
  return (((cand.facts or {}).get("view") or {}).get("level_hint")) if getattr(cand, "facts", None) else None

def _way(cand) -> str | None:
  return ((cand.facts or {}).get("direction") if getattr(cand, "facts", None) else None)

def _width(cand) -> float | None:
  w = (cand.facts or {}).get("stair_width_mm") if getattr(cand, "facts", None) else None
  return float(w) if isinstance(w, (int, float)) else None

def _unlike(a, b) -> float:
  wa, wb = _width(a), _width(b)
  return 0.0 if wa is None or wb is None else abs(wa - wb)

def _match(candidates, sheets: dict) -> tuple:
  up: dict = {}
  down: dict = {}
  
  for c in candidates:
    if c.category != "STAIR" or c.decision == "REJECTED" or c.sheet_id not in sheets:
      continue
    key = level_key(sheets[c.sheet_id])
    if key not in FLOOR_ORDER:
      continue
    way = _way(c)
    if way == "UP":
      up.setdefault(key, []).append(c)
    elif way == "DOWN":
      down.setdefault(key, []).append(c)
  also: dict = {}
  hidden: set = set()
  taken: set = set()
  owners_of: dict = {}
  
  for key in FLOOR_ORDER:
    flights = down.get(key) or []
    if not flights:
      continue
    below = [k for k in FLOOR_ORDER[:FLOOR_ORDER.index(key)] if up.get(k)]
    if not below:
      continue
  
    pool = [c for c in up[below[-1]] if c.id not in taken]
    pool.sort(key=lambda c: (c.decision != "ACCEPTED", sheets[c.sheet_id].page_no, str(c.id)))
    for d in sorted(flights, key=lambda c: (c.decision != "ACCEPTED", str(c.id))):
      need = max(1, int(d.count or 1))
      if len(pool) < need:
        continue
      pool.sort(key=lambda c: _unlike(c, d))
      owners, pool = pool[:need], pool[need:]
      for o in owners:
        taken.add(o.id)
        also.setdefault(o.id, []).append(sheets[d.sheet_id].page_no)
        owners_of.setdefault(d.id, []).append(sheets[o.sheet_id].page_no)
      hidden.add(d.id)
  return also, hidden, {k: sorted(set(v)) for k, v in owners_of.items()}, up, down

def twins(candidates, sheets: dict) -> tuple:
  """(UP flight id -> sheets of the DN flights that are the same stair, ids of the DN flights that are listed with their UP flight)."""
  also, hidden, _owners, _up, _down = _match(candidates, sheets)
  return also, hidden

def pairs(candidates, sheets: dict) -> tuple:
  """(UP flight id -> sheets of its DN twins, ids of the DN flights listed with their UP flight, DN flight id -> sheets of the UP flights it is the same stair as)."""
  also, hidden, owners, _up, _down = _match(candidates, sheets)
  return also, hidden, owners

def alone(candidates, sheets: dict) -> list:
  also, hidden, owners, up, down = _match(candidates, sheets)
  out = []
  have_up = {k for k, v in up.items() if v}
  have_down = {k for k, v in down.items() if v}
  for key, flights in down.items():
    below = [k for k in FLOOR_ORDER[:FLOOR_ORDER.index(key)] if k in have_up]
    if below:
      out.extend(d.id for d in flights if d.id not in owners)
  for key, flights in up.items():
    above = [k for k in FLOOR_ORDER[FLOOR_ORDER.index(key) + 1:] if k in have_down]
    if above:
      out.extend(u.id for u in flights if u.id not in also)
  return out
