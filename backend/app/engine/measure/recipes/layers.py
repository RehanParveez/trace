from __future__ import annotations
from app.engine.measure import recipes as RCP

NAME = "layers"
BASES = ("ROOF_TREATMENT", "MEMBRANE", "MAS-DPC")

def measure(spec: dict, item, bases: dict) -> dict | None:
  return RCP.from_bases(NAME, spec, item, bases)
