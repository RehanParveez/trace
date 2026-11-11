from __future__ import annotations
from dataclasses import dataclass
from app.modules.drawings_boq.pricing.billing import profiles

@dataclass(frozen=True)
class Spec:
  name: str
  value: str | None
  basis: str            
  question: str | None = None

def resolve(name: str, floor: str | None, decisions: dict | None) -> Spec:
  given = (decisions or {}).get(name)
  if isinstance(given, dict):
    value = given.get(floor) if floor is not None and floor in given else given.get("default")
  else:
    value = given
  if value not in (None, ""):
    return Spec(name, str(value), ((decisions or {}).get("basis") or {}).get(name, "ANSWER"))
  default = profiles.spec_defaults().get(name)
  return Spec(name, default, "ASSUMED", profiles.spec_question(name))
