from __future__ import annotations
from app.modules.drawings_boq.takeoff.prep.facts import FLOOR_ORDER

def level_key(sheet) -> str | None:
  """The floor a plan sheet shows (BASEMENT, GROUND, ...); None for a sheet that shows several drawings."""
  title = ((getattr(sheet, "prep_meta", None) or {}).get("title")) or {}
  return None if title.get("composite") else title.get("level_hint")

def _way(cand) -> str | None:
  return ((cand.facts or {}).get("direction") if getattr(cand, "facts", None) else None)

def twins(candidates, sheets: dict) -> tuple:
  """(also, hidden): also[owner id] = [page numbers of the sheets the same stair is drawn on], hidden = ids of the DN candidates that are the same stair as an UP
  candidate. candidates carry category, decision, sheet_id, count and facts["direction"] ("UP" or "DOWN")."""
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
      owners, pool = pool[:need], pool[need:]
      for o in owners:
        taken.add(o.id)
        also.setdefault(o.id, []).append(sheets[d.sheet_id].page_no)
      hidden.add(d.id)
  return also, hidden
