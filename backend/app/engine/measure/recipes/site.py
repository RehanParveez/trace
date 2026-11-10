from __future__ import annotations
from app.engine.measure import recipes as RCP

NAME = "site"
BASES = ("FIN-PAVING", "FIN-PORCH-TILE", "BRICK_BOUNDARY")

def measure(spec: dict, item, bases: dict) -> dict | None:
  return RCP.from_bases(NAME, spec, item, bases)
