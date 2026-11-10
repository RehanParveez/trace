from __future__ import annotations
from app.engine.measure import rule_registry as RR

RULE = "PARAPET_FROM_ROOF_PLAN"
PARAPET = "PARAPET"
LIGHT_RULE = "PARAPET_LIGHT_PEN_ON_ROOF"
ROOF = "ROOF"

def enabled() -> bool:
  return RR.on(RULE)

def is_parapet(cand) -> bool:
  return enabled() and cand.category == "WALL" and (cand.facts or {}).get("roof_wall") == PARAPET
def light_pen_on(level_hint: str | None) -> bool:
  return str(level_hint or "").upper() == ROOF and RR.on(LIGHT_RULE)
