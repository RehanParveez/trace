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

def solve(candidates, sheets: dict):
  from app.modules.drawings_boq.takeoff import stair_pairs as SP
  return SP.solve(candidates, sheets)

def sightings(candidates, sheets: dict) -> dict:
  return {k: v["twin_of_page"] for k, v in solve(candidates, sheets).info.items()}

def _match(candidates, sheets: dict) -> tuple:
  s = solve(candidates, sheets)
  return s.also, s.hidden, s.owners, s.up, s.down

def twins(candidates, sheets: dict) -> tuple:
  also, hidden, _owners, _up, _down = _match(candidates, sheets)
  return also, hidden

def pairs(candidates, sheets: dict) -> tuple:
  also, hidden, owners, _up, _down = _match(candidates, sheets)
  return also, hidden, owners

def alone(candidates, sheets: dict) -> list:
  return solve(candidates, sheets).lone
