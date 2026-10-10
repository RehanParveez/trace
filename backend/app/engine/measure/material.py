from __future__ import annotations
import re

_MASONRY = re.compile(r"\b(bricks?|brickwork|blocks?|blockwork|masonry|cmu|aac|rubble|ashlar)\b", re.I)
_CONCRETE = re.compile(
  r"\b(concrete|rcc|pcc|in[\s_-]?situ|cast[\s_-]?in[\s_-]?(?:situ|place))\b|\bm\s?(?:15|20|25|30|35|40|45|50)\b", re.I)
_CONCRETE_WALL_ROLES = frozenset({"WALL_RETAINING", "WALL_SHEAR", "WALL_CORE"})

def wall_material_class(role: str | None, material_text: str | None) -> str | None:
  r = (role or "").upper()
  if not r.startswith("WALL"):
    return None
  text = material_text or ""
  if _MASONRY.search(text):
    return "MASONRY"
  if _CONCRETE.search(text):
    return "CONCRETE"
  if r in _CONCRETE_WALL_ROLES:
    return "CONCRETE"
  return None