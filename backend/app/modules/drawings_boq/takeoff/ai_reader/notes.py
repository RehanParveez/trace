from __future__ import annotations
import re
import asyncio
from app.modules.drawings_boq.takeoff.ai_reader import prompts as P
from app.engine.catalogue import note_keys as NK
from app.modules.drawings_boq.takeoff.prep import printed_params as PP
from app.modules.drawings_boq.takeoff.ai_reader import compare as CMP
from app.modules.drawings_boq.takeoff.ai_reader import evidence as E
from app.modules.drawings_boq.takeoff.ai_reader import regions as R

TASK = "NOTE_FACT"
PURPOSE = "NOTE_FACT"
PROMPT_NAME = "note.v1"
PROMPT_VERSION = P.load(PROMPT_NAME)["version"]
SCHEMA_VERSION = "1"
SOURCE = "AI_READ"
CONFIDENCE = ("high", "medium", "low")
MAX_QUOTE = 240
MAX_SCOPE = 40
OK, INVALID, FAILED = "OK", "INVALID", "FAILED"
MAX_ERROR = 500

def prompt() -> str:
  lines = []
  for e in NK.keys():
    scopes = ", ".join(e["scopes"]) if e.get("scopes") else "any member or material, in a few words"
    lines.append(f'- {e["key"]}: {e["about"]}; unit {e["unit"]}; scope: {scopes}')
  return P.render(PROMPT_NAME, lists="\n".join(lines))

def _text(value, limit: int) -> str | None:
  text = re.sub(r"\s+", " ", str(value or "")).strip()
  return text[:limit] if text else None

def _fact(raw) -> tuple:
  if not isinstance(raw, dict):
    return None, ["FACT_NOT_AN_OBJECT"]
  entry = NK.get(str(raw.get("key") or "").strip().upper())
  if entry is None:
    return None, ["KEY_NOT_KNOWN"]
  try:
    value = float(str(raw.get("value")).replace(",", ""))
  except (TypeError, ValueError):
    return None, ["VALUE_NOT_A_NUMBER"]
  bar = raw.get("bar")
  
  try:
    bar = None if bar in (None, "") else int(str(bar).lstrip("#"))
  except ValueError:
    bar = None
  scope = _text(raw.get("scope"), MAX_SCOPE)
  return {"key": entry["key"], "scope": scope.lower() if scope else None, "where": (_text(raw.get("where"), MAX_SCOPE) or "").lower() or None, "bar": bar, "value": value,
    "unit": (_text(raw.get("unit"), 8) or "").lower() or None, "quote": _text(raw.get("quote"), MAX_QUOTE)}, []

def validate(parsed) -> tuple[dict | None, list[str]]:
  if not isinstance(parsed, dict) or not isinstance(parsed.get("facts"), list):
    return None, ["NOT_AN_OBJECT"]
  facts, problems = [], []
  for raw in parsed["facts"]:
    fact, found = _fact(raw)
    problems.extend(found)
    if fact is not None:
      facts.append(fact)
      
  conf = str(parsed.get("confidence") or "").strip().lower()
  if conf not in CONFIDENCE:
    problems.append("CONFIDENCE_MISSING")
  return {"facts": facts, "confidence": conf if conf in CONFIDENCE else "low"}, problems

def millimetres(fact: dict) -> float | None:
  entry = NK.get(fact["key"])
  return NK.to_mm(fact["value"], fact["unit"]) if entry and entry["unit"] == "mm" else None

def fact_checks(fact: dict, tile_text: str | None) -> list:
  entry = NK.get(fact["key"])
  quote = fact["quote"]
  out = [E.quote_printed(quote, tile_text)] if quote else [E.result("quote_printed", False, "the fact has no quote")]
  out.append(E.number_printed(fact["value"], quote))
  mm = millimetres(fact)
  
  if entry["unit"] == "mm":
    out.append(E.result("unit_parses", mm is not None, f"unit {fact['unit']}" if mm is not None else f"{fact['unit']!r} is not a length unit the note-key file knows"))
    shown = mm
  else:
    out.append(E.result("unit_parses", fact["unit"] == entry["unit"], f"unit {fact['unit']}" if fact["unit"] == entry["unit"] else f"{fact['unit']!r} is not {entry['unit']}"))
    shown = fact["value"]
  low, high = entry["range"]
  out.append(E.value_in_range(shown, low, high) if shown is not None else E.result("value_in_range", False, "the value has no unit to compare"))
  if entry.get("values"):
    out.append(E.choice_offered(int(fact["value"]) if fact["value"] == int(fact["value"]) else fact["value"], entry["values"]))
  if entry.get("scopes") and fact["scope"] is not None:
    out.append(E.choice_offered(fact["scope"], entry["scopes"]))
  if entry["shape"] == "LAP":
    out.append(E.result("bar_given", fact["bar"] is not None and 2 <= fact["bar"] <= 12, "the lap names its bar" if fact["bar"] else "a lap length needs the bar number it is for"))
  return out

def to_item(fact: dict) -> dict:
  entry = NK.get(fact["key"])
  base = {"kind": fact["key"], "text": fact["quote"][:140], "source": SOURCE, "quote": fact["quote"]}
  if entry["shape"] == "LAP":
    dia = round(fact["bar"] * PP.EIGHTH_MM, 3)
    return {**base, "value_mm": millimetres(fact), "bar_dia_mm": dia, "scope": f"lap bar {fact['bar']}"}
  if entry["shape"] == "GRADE":
    return {**base, "grade": int(fact["value"]), "scope": fact["scope"] or "all bars"}
  if entry["shape"] == "PSI":
    return {**base, "concrete_class": None, "mix": f"{int(fact['value'])} psi", "scope": fact["scope"]}
  return {**base, "value_mm": millimetres(fact), "scope": fact["scope"], "where": fact["where"] or ""}

def _scope(value) -> str:
  return re.sub(r"\s+", " ", str(value or "")).strip().lower()

def _value(item: dict):
  return item.get("value_mm") if item.get("value_mm") is not None else item.get("grade") if item.get("grade") is not None else item.get("mix")

def _same(a, b) -> bool:
  if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
    return abs(float(a) - float(b)) <= (NK.tolerance_mm() if abs(float(a)) > 40 or abs(float(b)) > 40 else 0.0)
  return str(a).lower() == str(b).lower()

def merge(rule_items: list, items: list) -> dict:
  accepted, records = [], []
  for item in items:
    mine = [r for r in rule_items if r.get("kind") == item["kind"] and _scope(r.get("scope")) == _scope(item.get("scope")) and _scope(r.get("where")) == _scope(item.get("where"))
      and (r.get("bar_dia_mm") is None or item.get("bar_dia_mm") is None or abs(float(r["bar_dia_mm"]) - float(item["bar_dia_mm"])) < 0.2)]
    label = f"{item['kind']}:{item.get('scope') or ''}"
    
    if not mine:
      accepted.append(item)
      records.append({"fact_key": label, "rule_value": None, "ai_value": str(_value(item)), "agreement": CMP.AI_ONLY, "quote": item["quote"]})
    elif any(_same(_value(r), _value(item)) for r in mine):
      records.append({"fact_key": label, "rule_value": str(_value(mine[0])), "ai_value": str(_value(item)), "agreement": CMP.AGREE, "quote": item["quote"]})
    else:
      records.append({"fact_key": label, "rule_value": str(_value(mine[0])), "ai_value": str(_value(item)), "agreement": CMP.DISAGREE, "quote": item["quote"]})
  return {"accepted": accepted, "records": records}

def accepted_from(ai_value: dict | None, rule_items: list) -> list:
  return merge(rule_items, [to_item(f) for f in (ai_value or {}).get("facts") or []])["accepted"]

async def read_notes(*, contents: bytes, page_no: int, ask, store_crop=None, cache_key: str | None = None, model: str | None = None, rule_items: list | None = None) -> dict:
  page_pt = await asyncio.to_thread(lambda: R.page_picture(contents, page_no, 64)[1]["page_pt"])
  text = await asyncio.to_thread(R.page_text, contents, page_no, page_pt)
  boxes = R.note_tiles(page_pt, len((text or "").split()))
  prompt_text = prompt()
  
  record = {"task": TASK, "purpose": PURPOSE, "prompt": prompt_text, "prompt_version": PROMPT_VERSION, "schema_version": SCHEMA_VERSION, "crop_key": None, "crop": {"tiles": boxes, "page_pt": page_pt},
    "cache_key": cache_key, "model": model, "rule_value": {"items": len(rule_items or [])}, "ai_request_id": None, "input_tokens": 0, "output_tokens": 0, "seconds": 0.0, "ai_value": None,
    "comparison": [], "totals": {}, "validators": [], "status": OK, "problems": [], "error": None, "items": []}
  facts, validators, problems, confidences = [], [], [], []
  for n, box in enumerate(boxes):
    png, _info = await asyncio.to_thread(R.box_picture, contents, page_no, box)
    if n == 0 and store_crop:
      record["crop_key"] = await store_crop(png)
    result = await ask(prompt_text, png, [])
    
    record["model"] = getattr(result, "model", None) or record["model"]
    record["ai_request_id"] = getattr(result, "ai_request_id", None) or record["ai_request_id"]
    record["input_tokens"] += getattr(result, "input_tokens", None) or 0
    record["output_tokens"] += getattr(result, "output_tokens", None) or 0
    record["seconds"] += getattr(result, "seconds", None) or 0.0
    
    if not result.success:
      record["status"], record["error"] = FAILED, str(result.error_message or "The AI request failed.")[:MAX_ERROR]
      return record
    clean, found = validate(result.parsed_output)
    problems.extend(found)
    if clean is None:
      record["status"] = INVALID
      return record
    confidences.append(clean["confidence"])
    tile_text = await asyncio.to_thread(R.text_in_boxes, contents, page_no, [box])
    for fact in clean["facts"]:
      checks = [{**c, "name": f"{c['name']}.{fact['key']}"} for c in fact_checks(fact, tile_text)]
      validators.extend(checks)
      if all(c["passed"] for c in checks):
        facts.append(fact)
      else:
        problems.append(f"{fact['key']}_DROPPED")
        
  facts = list({(f["key"], f["scope"], f["where"], f["bar"], f["value"], f["unit"]): f for f in facts}.values())
  merged = merge(rule_items or [], [to_item(f) for f in facts])
  record["items"] = merged["accepted"]
  record["ai_value"] = {"facts": facts, "confidence": min(confidences, key=CONFIDENCE.index) if confidences else "low"}
  record["validators"], record["problems"] = validators, problems
  record["comparison"] = merged["records"]
  record["totals"] = CMP.totals(merged["records"])
  return record
