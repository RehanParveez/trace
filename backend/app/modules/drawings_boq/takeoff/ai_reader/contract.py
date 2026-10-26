from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import sheet_identity as SI
from app.modules.drawings_boq.takeoff.extract import identity_words as IW

PURPOSE = "SHEET_CLASSIFICATION"
PROMPT_VERSION = "1"
SCHEMA_VERSION = "1"

DISCIPLINES = tuple(dict.fromkeys(code for code, _rx, _s in IW.DISCIPLINE_WORDS))
SHEET_TYPES = tuple(dict.fromkeys(code for code, _rx in IW.SHEET_TYPE_WORDS))
FLOORS = tuple(code for code, _rx in SI.LEVEL)
CONFIDENCE = ("high", "medium", "low")
CODE_KEYS = (("discipline", DISCIPLINES), ("sheet_type", SHEET_TYPES), ("floor", FLOORS))
TEXT_KEYS = ("title", "sheet_no")
KEYS = tuple(k for k, _ in CODE_KEYS) + TEXT_KEYS
MAX_TEXT = 80

def prompt() -> str:
  lists = "\n".join(f'- "{key}": one of {", ".join(options)}, or null' for key, options in CODE_KEYS)
  return (
    "You are shown the title-block areas of one construction drawing sheet: the bottom strip and the right-hand strip, "
    "placed side by side in one picture. Read only what is printed there. Do not guess, and do not use anything you cannot "
    "see in the picture. If a field is not printed, answer null for it.\n\n"
    "Answer with strict JSON only, no markdown, in this exact shape:\n"
    '{"discipline": ..., "sheet_type": ..., "floor": ..., "title": ..., "sheet_no": ..., "confidence": "high" | "medium" | "low"}\n\n'
    f"{lists}\n"
    '- "title": the drawing title as printed, or null\n'
    '- "sheet_no": the sheet or drawing number as printed, or null\n'
    "A plan of points (electrical, plumbing) is POINTS_PLAN; any other plan is PLAN. Use floor only when the title names a storey or level."
  )

def validate(parsed) -> tuple[dict | None, list[str]]:
  if not isinstance(parsed, dict):
    return None, ["NOT_AN_OBJECT"]
  problems: list[str] = []
  out: dict = {}
  for key, options in CODE_KEYS:
    value = parsed.get(key)
    if value in (None, ""):
      out[key] = None
      continue

    text = str(value).strip().upper().replace(" ", "_")
    if text in options:
      out[key] = text
    else:
      out[key] = None
      problems.append(f"{key.upper()}_OUT_OF_LIST")

  for key in TEXT_KEYS:
    value = parsed.get(key)
    out[key] = str(value).strip()[:MAX_TEXT] if value not in (None, "") else None
  conf = str(parsed.get("confidence") or "").strip().lower()
  out["confidence"] = conf if conf in CONFIDENCE else "low"
  if conf not in CONFIDENCE:
    problems.append("CONFIDENCE_MISSING")
  return out, problems
