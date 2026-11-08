from __future__ import annotations
from app.modules.drawings_boq.takeoff.ai_reader import prompts as P
from app.engine.catalogue import legend_choices as LC
from app.modules.drawings_boq.takeoff.extract import electrical as EL
from app.modules.drawings_boq.takeoff.extract import electrical_symbols as ES
from app.modules.drawings_boq.takeoff.ai_reader import compare as CMP
from app.modules.drawings_boq.takeoff.ai_reader import regions as R
import re
from app.modules.drawings_boq.takeoff.extract import electrical_rules as ER
from app.modules.drawings_boq.takeoff.prep.extract import open_document
from app.modules.drawings_boq.takeoff.ai_reader import evidence as E
from app.modules.drawings_boq.takeoff.ai_reader import cache as CACHE
import asyncio

TASK = "LEGEND_ENTRY"
PURPOSE = "LEGEND_ENTRY"
PROMPT_NAME = "legend.v1"
PROMPT_VERSION = P.load(PROMPT_NAME)["version"]
SCHEMA_VERSION = "1"
SOURCE = "AI_READ"
CONFIDENCE = ("high", "medium", "low")
MAX_QUOTE = 240
MAX_ERROR = 500
ROW_PAD_SHARE = 0.01
OK, INVALID, FAILED = "OK", "INVALID", "FAILED"
WEAK, ALL = "WEAK", "ALL"

def prompt() -> str:
  return P.render(PROMPT_NAME, choices="\n".join(f'- {e["key"]}: {e["about"]}' for e in LC.choices()))

def region(mode: str) -> dict:
  return {"zone": "LEGEND_ROWS", "mode": mode, "pad_share": ROW_PAD_SHARE, "long_side_px": R.BOX_LONG_SIDE_PX}

def validate(parsed) -> tuple[dict | None, list[str]]:
  if not isinstance(parsed, dict):
    return None, ["NOT_AN_OBJECT"]
  problems = []
  meaning = parsed.get("meaning")
  meaning = None if meaning is None or str(meaning).strip().lower() in ("", "null", "none") else str(meaning).strip().upper()
  quote = re.sub(r"\s+", " ", str(parsed.get("quote") or "")).strip()[:MAX_QUOTE]
  conf = str(parsed.get("confidence") or "").strip().lower()
  if conf not in CONFIDENCE:
    problems.append("CONFIDENCE_MISSING")
  return {"meaning": meaning, "quote": quote, "confidence": conf if conf in CONFIDENCE else "low"}, problems

def row_box(row: dict, pad: float) -> list | None:
  block, objects = row.get("block"), row.get("objects") or []
  if not block or not objects:
    return None
  top, bottom = min(o[3] for o in objects), max(o[5] for o in objects)
  return [float(block[0]), float(top) - pad, float(block[2]), float(bottom) + pad]

def pad_of(page_pt) -> float:
  return ROW_PAD_SHARE * min(float(v) for v in page_pt)

def wanted(rows: list, mode: str, pad: float = 0.0) -> list:
  seen: set = set()
  out = []
  for r in rows:
    name = r.get("name")
    if name in seen or row_box(r, pad) is None or (mode != ALL and EL.kind_of(name) != ER.OTHER):
      continue
    seen.add(name)
    out.append(r)
  return out

def _ocr(contents: bytes, page_no: int, box) -> str:
  doc = open_document(contents)
  try:
    return ES.read_cell(doc[page_no - 1], tuple(box))
  finally:
    doc.close()

def row_text(contents: bytes, page_no: int, row: dict, box) -> str:
  layer = R.text_in_boxes(contents, page_no, [box])
  words = layer if (layer or "").strip() else _ocr(contents, page_no, box)
  return " ".join(p for p in (row.get("description"), words) if p)

def row_checks(answer: dict, row: dict, text: str) -> list:
  out = [E.quote_printed(answer["quote"], text) if answer["quote"] else E.result("quote_printed", False, "the answer has no quote")]
  out.append(E.choice_offered(answer["meaning"], LC.keys()))
  out.append(E.result("meaning_given", answer["meaning"] is not None, "the answer names a meaning" if answer["meaning"] else "the answer names no meaning"))
  out.append(E.result("symbol_present", bool(row.get("objects")) and (len(row["objects"]) >= ES.MIN_SYMBOL_OBJECTS or bool(row.get("token"))), "the row has a symbol to count" if row.get("objects") else "the row has no drawn symbol"))
  seen = EL.kind_of(answer["quote"]) if answer["quote"] else ER.OTHER
  out.append(E.result("meaning_not_contradicted", seen in (ER.OTHER, answer["meaning"]), "the words name no other kind" if seen in (ER.OTHER, answer["meaning"]) else f"the words read as {seen}"))
  return out

def entry(row: dict, answer: dict) -> dict:
  return {"name": row["name"], "kind": answer["meaning"], "source": SOURCE, "quote": answer["quote"], "confidence": answer["confidence"]}

def compare_row(row: dict, answer: dict) -> dict | None:
  mine = EL.kind_of(row["name"])
  rule = None if mine == ER.OTHER else mine
  if rule is None and answer["meaning"] is None:
    return None
  verdict = CMP.AI_ONLY if rule is None else CMP.RULE_ONLY if answer["meaning"] is None else CMP.AGREE if rule == answer["meaning"] else CMP.DISAGREE
  return {"fact_key": f"LEGEND:{row['name']}", "rule_value": rule, "ai_value": answer["meaning"], "agreement": verdict, "quote": answer["quote"]}

def accepted_from(ai_value: dict | None, rows: list) -> list:
  by = {r.get("name"): r for r in rows or []}
  out = []
  for a in (ai_value or {}).get("rows") or []:
    row = by.get(a["name"])
    if row is not None and a.get("meaning") and EL.kind_of(a["name"]) == ER.OTHER:
      out.append(entry(row, a))
  return out

def page_rows(contents: bytes, page_no: int) -> list:
  doc = open_document(contents)
  try:
    return EL.pack_legend(ES.read_legend(doc[page_no - 1]))
  finally:
    doc.close()

def cached(case_dir: str) -> dict:
  out: dict = {}
  for e in CACHE.read_all(case_dir):
    if e.get("task") == TASK and e.get("status") == OK and e.get("answer"):
      out.setdefault(e["pdf_sha256"], {})[int(e["page"])] = e["answer"]
  return out

def attach(items: list, prepared: list, legends: dict) -> None:
  for (_name, data), (_doc, analysed, _problems) in zip(items, prepared):
    by_page = legends.get(CACHE.pdf_sha256(data)) or {}
    for no, a in analysed.items():
      if no in by_page:
        a.meta["ai_legend"] = accepted_from(by_page[no], a.meta.get("electrical_legend") or [])

async def read_legends(*, contents: bytes, page_no: int, rows: list, mode: str, ask, store_crop=None, cache_key: str | None = None, model: str | None = None) -> dict:
  page_pt = await asyncio.to_thread(lambda: R.page_picture(contents, page_no, 64)[1]["page_pt"])
  pad = pad_of(page_pt)
  todo = wanted(rows, mode, pad)
  prompt_text = prompt()
  
  record = {"task": TASK, "purpose": PURPOSE, "prompt": prompt_text, "prompt_version": PROMPT_VERSION, "schema_version": SCHEMA_VERSION, "crop_key": None, "crop": {"rows": [r["name"] for r in todo], "page_pt": page_pt},
    "cache_key": cache_key, "model": model, "rule_value": {"rows": len(rows), "placed": sum(1 for r in rows if EL.kind_of(r.get("name")) != ER.OTHER)}, "ai_request_id": None, "input_tokens": 0, "output_tokens": 0, "seconds": 0.0,
    "ai_value": None, "comparison": [], "totals": {}, "validators": [], "status": OK, "problems": [], "error": None, "items": []}
  given, held, validators, problems, records, confidences = [], [], [], [], [], []
  
  for n, row in enumerate(todo):
    box = row_box(row, pad)
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
    
    text = await asyncio.to_thread(row_text, contents, page_no, row, box)
    checks = [{**c, "name": f"{c['name']}.{row['name']}"} for c in row_checks(clean, row, text)]
    validators.extend(checks)
    confidences.append(clean["confidence"])
    found_row = {"name": row["name"], **clean}
    if all(c["passed"] for c in checks):
      given.append(found_row)
      record["items"].append(entry(row, clean))
    else:
      held.append({"name": row["name"], "reasons": [c["name"].split(".")[0] for c in checks if not c["passed"]], "quote": clean["quote"], "meaning": clean["meaning"]})
      problems.append("LEGEND_ROW_HELD")
    compared = compare_row(row, clean)
    if compared is not None:
      records.append(compared)
      
  record["ai_value"] = {"rows": given, "held": held, "compared": records, "confidence": min(confidences, key=CONFIDENCE.index) if confidences else "low"}
  record["validators"], record["problems"] = validators, problems
  record["comparison"] = records
  record["totals"] = CMP.totals(records)
  return record
