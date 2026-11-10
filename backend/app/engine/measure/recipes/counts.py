from __future__ import annotations
from app.engine.measure import recipes as RCP

NAME = "counts"
BASES = ("MET-OHWT-COVER", "MET-SEPTIC-COVER", "MET-UGT-COVER", "ELE-LIGHT", "ELE-FAN", "ELE-SWITCH", "ELE-SOCKET")

def measure(spec: dict, item, bases: dict) -> dict | None:
  return RCP.from_bases(NAME, spec, item, bases)
