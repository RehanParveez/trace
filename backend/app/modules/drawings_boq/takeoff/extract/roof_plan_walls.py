from __future__ import annotations
from app.engine.measure import rule_registry as RR

RULE = "PARAPET_FROM_ROOF_PLAN"
PARAPET = "PARAPET"

def enabled() -> bool:
  return RR.on(RULE)

def is_parapet(cand) -> bool:
  return enabled() and cand.category == "WALL" and (cand.facts or {}).get("roof_wall") == PARAPET