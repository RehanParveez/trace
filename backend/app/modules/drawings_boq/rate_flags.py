from __future__ import annotations

NO_RATE = "NO_RATE"
RATE_ZERO = "RATE_ZERO"
AI_SUGGESTED_RATE = "AI_SUGGESTED_RATE"
UNIT_CONVERTED = "UNIT_CONVERTED"
LIBRARY_TEXT = "LIBRARY_TEXT"
LIBRARY_DEFAULT = "LIBRARY_DEFAULT"
SPEC_NOT_SETTLED = "SPEC_NOT_SETTLED"
NO_ESCALATION = "NO_ESCALATION"

FLAGS = (
  (NO_RATE, "No rate found: the line adds nothing to the bill until it is priced"),
  (RATE_ZERO, "The rate is zero, so the line costs nothing in the bill"),
  (AI_SUGGESTED_RATE, "The rate was suggested by the assistant and nobody has confirmed it"),
  (SPEC_NOT_SETTLED, "The rate book publishes several rates by specification and the drawing did not settle which; the base rate was taken"),
  (UNIT_CONVERTED, "The rate is published in another unit and was converted"),
  (LIBRARY_TEXT, "Priced from the material library by matching the wording of the line, not by its work item"),
  (LIBRARY_DEFAULT, "Priced from the library default, not from a published rate book"),
  (NO_ESCALATION, "A published rate with no escalation in force, so it is the rate of the book's own date"),
)
CODES = tuple(code for code, _ in FLAGS)
BLOCKS = {NO_RATE: "ISSUE", RATE_ZERO: "ISSUE", AI_SUGGESTED_RATE: "APPROVAL"}

def blocks_of(code: str) -> str | None:
  return BLOCKS.get(code)

def _f(v) -> float:
  try:
    return float(v)
  except (TypeError, ValueError):
    return 0.0

def _source(v) -> str | None:
  if v is None:
    return None
  return str(getattr(v, "value", v))

def flags_of(row: dict) -> list:
  quantity, rate = _f(row.get("quantity")), row.get("unit_rate")
  if rate is None:
    return [NO_RATE] if quantity != 0 else []
  out: list = []

  source = _source(row.get("rate_source"))
  trace = row.get("rate_resolution") if isinstance(row.get("rate_resolution"), dict) else {}
  if _f(rate) == 0 and quantity != 0:
    out.append(RATE_ZERO)
  if source == "AI_SUGGESTED":
    out.append(AI_SUGGESTED_RATE)
  if source == "RATE_BOOK" and trace.get("spec_unresolved"):
    out.append(SPEC_NOT_SETTLED)
  if trace.get("unit_converted") is True:
    out.append(UNIT_CONVERTED)
  if source == "LIBRARY":
    out.append(LIBRARY_TEXT if trace.get("matched_on") == "text" else LIBRARY_DEFAULT)
  if source == "RATE_BOOK" and trace and not trace.get("escalation_id"):
    out.append(NO_ESCALATION)
  return out
