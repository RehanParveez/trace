from __future__ import annotations
from decimal import Decimal
from app.engine.measure import rulebook as RB

DIVISOR_KEY = "steel.unit_weight_divisor"
DIVISOR = Decimal("162.2")
FAMILIES = ("SLAB", "BEAM", "COLUMN", "FOOTING", "WALL", "STAIR", "TANK", "PARAPET")
WHICH = ("low", "likely", "high")

def band_key(family: str, which: str) -> str:
  return f"steel.band.{family}.{which}"

def code_bands() -> dict:
  from app.engine.measure.rebar import ESTIMATE_BANDS
  return {f: ESTIMATE_BANDS[f] for f in FAMILIES if f in ESTIMATE_BANDS}

def divisor() -> Decimal:
  return Decimal(str(RB.pick(DIVISOR_KEY, float(DIVISOR))))

def band(family: str | None) -> tuple | None:
  base = code_bands().get(family or "")
  if base is None:
    return None
  return tuple(Decimal(str(RB.pick(band_key(family, w), float(v)))) for w, v in zip(WHICH, base))

def seed_expect() -> dict:
  out = {DIVISOR_KEY: float(DIVISOR)}
  for family, values in code_bands().items():
    for w, v in zip(WHICH, values):
      out[band_key(family, w)] = float(v)
  return out
