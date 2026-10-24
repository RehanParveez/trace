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

def mix_of(cand) -> dict | None:
  """The mix printed for a line that is not a structural member: the mortar behind plaster, a plain concrete bed, a cement-sand bed. The reader puts it on the line as `spec_grade`
  only when the drawing prints exactly one for that work."""
  facts = getattr(cand, "facts", None) or {}
  printed = facts.get("spec_grade") or {}
  if not facts.get("foundation_item") or not printed.get("grade") or member_of(cand) is not None:
    return None
  return {"grade": str(printed["grade"])[:50], "mix": str(printed["grade"])[:50], "what": printed.get("what") or "mix", "pages": list(printed.get("pages") or []), "item": facts["foundation_item"]}

def mix_stamp(cand) -> dict | None:
  return mix_of(cand)

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
