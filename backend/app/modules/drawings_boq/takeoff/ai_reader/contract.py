from __future__ import annotations
from app.modules.drawings_boq.takeoff.ai_reader import prompts as P
from app.modules.drawings_boq.takeoff.prep import page_role as PRL
from app.modules.drawings_boq.takeoff.extract import sheet_identity as SI
from app.modules.drawings_boq.takeoff.extract import identity_words as IW

PURPOSE = "SHEET_CLASSIFICATION"
PROMPT_NAME = "sheet.v2"
PROMPT_VERSION = P.load(PROMPT_NAME)["version"]
SCHEMA_VERSION = "2"

DISCIPLINES = tuple(dict.fromkeys(code for code, _rx, _s in IW.DISCIPLINE_WORDS))
ROLES = PRL.ROLES
FLOORS = tuple(code for code, _rx in SI.LEVEL)
CONFIDENCE = ("high", "medium", "low")
CODE_KEYS = (("discipline", DISCIPLINES), ("role", ROLES))
LIST_KEYS = (("floors", FLOORS),)
TEXT_KEYS = ("scale_text", "sheet_no", "title", "firm")
KEYS = tuple(k for k, _ in CODE_KEYS) + tuple(k for k, _ in LIST_KEYS) + TEXT_KEYS
RULE_KEY = {"floors": "floor"}
STRIPS, WHOLE_PAGE = "STRIPS", "PAGE"
QUOTE_REGION = {"discipline": WHOLE_PAGE, "role": WHOLE_PAGE, "floors": WHOLE_PAGE, "scale_text": WHOLE_PAGE, "sheet_no": STRIPS, "title": STRIPS, "firm": STRIPS}
MAX_TEXT = 80
MAX_QUOTE = 200

def prompt() -> str:
  lists = "\n".join(f'- "{key}": {"every one of" if key == "floors" else "one of"} {", ".join(options)}, or null' for key, options in (*CODE_KEYS, *LIST_KEYS))
  return P.render(PROMPT_NAME, lists=lists)

def _pair(parsed: dict, key: str) -> tuple:
  raw = parsed.get(key)
  if isinstance(raw, dict):
    return raw.get("value"), raw.get("quote")
  return raw, (parsed.get("quotes") or {}).get(key)

def _empty(value) -> bool:
  return value is None or (isinstance(value, (str, list)) and not value) or (isinstance(value, str) and not value.strip())

def _floors(value) -> tuple:
  items = value if isinstance(value, list) else [value]
  codes = [str(v).strip().upper().replace(" ", "_") for v in items if not _empty(v)]
  kept = list(dict.fromkeys(c for c in codes if c in FLOORS))
  return (kept or None), (["FLOORS_OUT_OF_LIST"] if len(kept) != len(set(codes)) else [])

def validate(parsed) -> tuple[dict | None, list[str]]:
  """Turns a raw answer into a clean one, with each field's quote beside it, and lists what was wrong; a field with a problem is left empty, never the whole answer."""
  if not isinstance(parsed, dict):
    return None, ["NOT_AN_OBJECT"]
  problems: list[str] = []
  out: dict = {}
  quotes: dict = {}
  for key, options in CODE_KEYS:
    value, quote = _pair(parsed, key)
    text = None if _empty(value) else str(value).strip().upper().replace(" ", "_")
    if text is not None and text not in options:
      problems.append(f"{key.upper()}_OUT_OF_LIST")
      text = None
    out[key], quotes[key] = text, quote
    
  for key, _options in LIST_KEYS:
    value, quote = _pair(parsed, key)
    out[key], found = _floors(value) if not _empty(value) else (None, [])
    problems.extend(found)
    quotes[key] = quote
  for key in TEXT_KEYS:
    value, quote = _pair(parsed, key)
    out[key], quotes[key] = (None if _empty(value) else str(value).strip()[:MAX_TEXT]), quote
  for key in KEYS:
    quote = None if _empty(quotes.get(key)) else str(quotes[key]).strip()[:MAX_QUOTE]
    if out[key] is not None and quote is None:
      out[key] = None
      problems.append(f"{key.upper()}_NO_QUOTE")
    quotes[key] = quote if out[key] is not None else None
    
  out["quotes"] = {k: q for k, q in quotes.items() if q}
  conf = str(parsed.get("confidence") or "").strip().lower()
  out["confidence"] = conf if conf in CONFIDENCE else "low"
  if conf not in CONFIDENCE:
    problems.append("CONFIDENCE_MISSING")
  return out, problems
