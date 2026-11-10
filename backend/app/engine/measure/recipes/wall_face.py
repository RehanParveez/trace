from __future__ import annotations
from app.engine.measure import recipes as RCP

NAME = "wall_face"
BASES = ("WALL_PLASTER", "WALL_PLASTER_EXT", "FIN-PAINT", "FIN-PAINT-EXT", "BRICK_WALLS")

def measure(spec: dict, item, bases: dict) -> dict | None:
  return RCP.from_bases(NAME, spec, item, bases)
