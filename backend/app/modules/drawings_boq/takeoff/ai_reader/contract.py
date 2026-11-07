from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import sheet_identity as SI
from app.modules.drawings_boq.takeoff.extract import identity_words as IW
from app.modules.drawings_boq.takeoff.ai_reader import prompts as P

PURPOSE = "SHEET_CLASSIFICATION"
PROMPT_NAME = "sheet.v1"
PROMPT_VERSION = P.load(PROMPT_NAME)["version"]
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
  return P.render(PROMPT_NAME, lists=lists)

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
