from __future__ import annotations
from app.engine.measure import grades as GR

KEY = "grade_stamp"
LABELS = {"COLUMN": "Columns", "BEAM": "Beams", "LINTEL": "Lintels", "FOOTING": "Footings", "SLAB": "Slabs", "CHAJJA": "Chajjas", "BALCONY_SLAB": "Balcony slabs", "STAIR": "Stairs",
  "RCC_WALL": "RCC walls", "TANK": "Tanks", "PARAPET": "Parapets"}
CANDIDATE_MEMBERS = ("COLUMN", "BEAM", "LINTEL", "FOOTING", "SLAB", "STAIR", "RCC_WALL", "TANK")

def is_concrete_code(code: str | None) -> bool:
  c = str(code or "").upper()
  return c.startswith("CON-") and not c.startswith("CON-PCC")

def member_of(cand) -> str | None:
  return GR.category_of_candidate(getattr(cand, "category", None), getattr(cand, "facts", None))

def stamp_for(cand, concrete_rules: list) -> dict | None:
  member = member_of(cand)
  if member is None:
    return None
  rule = GR.resolve(concrete_rules or [], member)["rule"]
  if rule is None:
    return None
  return {"grade": rule["mix"], "class": rule.get("class"), "mix": rule["mix"], "scope": rule.get("scope"), "pages": list(rule.get("pages") or []), "member": member}

def stamped(cand) -> dict | None:
  return ((getattr(cand, "facts", None) or {}).get(KEY)) or None

def classify(cand, material_grade: str | None) -> str:
  if not material_grade:
    return "NONE"
  s = stamped(cand)
  return "STAMPED" if s and s.get("grade") == material_grade else "TYPED"
