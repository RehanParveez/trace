from __future__ import annotations
from app.modules.drawings_boq.lab.aliases import KEY_LABEL

DEFAULT_TOLERANCE_PCT = 5.0
MAX_TOLERANCE_PCT = 100.0

FAMILY_TOLERANCE_PCT = {
  "EXCAVATION": 10.0, "TERMITE": 5.0, "MEMBRANE": 5.0, "BRICK_FOUNDATION": 10.0, "PCC": 10.0, "RCC_FOOTINGS": 5.0, "RCC_PLINTH_BEAM": 5.0,
  "RCC_COLUMNS": 5.0, "RCC_WALLS": 5.0, "RCC_LINTELS": 10.0, "RCC_ROOF_BEAMS": 5.0, "RCC_STAIR": 10.0, "RCC_SLABS": 5.0,
  "CEILING_PLASTER": 5.0, "WALL_PLASTER": 10.0, "BRICK_WALLS": 5.0, "STEEL": 10.0, "DOOR_FRAMES": 5.0, "DOORS": 5.0, "WINDOWS": 5.0,
  "KACHA": 5.0, "FILLING": 10.0, "ROOF_TREATMENT": 10.0, "FORMWORK": 15.0, "TANKS": 10.0,
}

def clamp(value) -> float | None:
  """A tolerance as a percentage between 0 and 100, or None when it is not a number."""
  if value is None or isinstance(value, bool):
    return None
  try:
    v = float(value)
  except (TypeError, ValueError):
    return None
  if v != v:
    return None
  return round(max(0.0, min(v, MAX_TOLERANCE_PCT)), 2)

def default_for(key: str) -> float:
  return FAMILY_TOLERANCE_PCT.get(key, DEFAULT_TOLERANCE_PCT)

def resolve(key: str, stored: dict | None = None, all_families: float | None = None) -> tuple:
  """(percentage, where it came from): the family's own value, else one value for every family, else the starting value."""
  own = clamp((stored or {}).get(key))
  if own is not None:
    return own, "family"
  every = clamp(all_families)
  if every is not None:
    return every, "all"
  return default_for(key), "default"

def clean(raw) -> dict:
  """The tolerances of a request: only known families, only numbers; anything else is dropped."""
  out: dict = {}
  if not isinstance(raw, dict):
    return out
  for k, v in raw.items():
    c = clamp(v)
    if k in KEY_LABEL and c is not None:
      out[k] = c
  return out
