"""The SCHEDULE_ROW task: the prompt built from the schedule-kind list, the check that turns a model's answer into clean rows, the checks of each row against the page, the merge with the schedule cells the rule reader read, and the read of a page of schedules in tiles."""
from __future__ import annotations
import re
import asyncio
from app.engine.catalogue import schedule_kinds as SK
from app.modules.drawings_boq.takeoff.ai_reader import prompts as P
from app.modules.drawings_boq.takeoff.ai_reader import evidence as E
from app.modules.drawings_boq.takeoff.ai_reader import compare as CMP
from app.modules.drawings_boq.takeoff.ai_reader import regions as R
from app.modules.drawings_boq.takeoff.extract import sheet_identity as SID
from app.modules.drawings_boq.takeoff.extract import structure_tables as ST
from app.modules.drawings_boq.takeoff.prep import mark_vocab as MV

TASK = "SCHEDULE_ROW"
PURPOSE = "SCHEDULE_ROW"
PROMPT_NAME = "schedule.v1"
PROMPT_VERSION = P.load(PROMPT_NAME)["version"]
SCHEMA_VERSION = "1"
SOURCE = "AI_READ"
CONFIDENCE = ("high", "medium", "low")
MAX_QUOTE = 240
MAX_CELL = 60
MAX_LAYER = 200
OK, INVALID, FAILED = "OK", "INVALID", "FAILED"
MAX_ERROR = 500
IN_MM = 25.4
METRIC_SIZE = re.compile(r"^(\d{2,4}(?:\.\d+)?)\s*(?:mm)?\s*[x×]\s*(\d{2,4}(?:\.\d+)?)\s*(?:mm)?$", re.I)
LEVELS = tuple((code, re.compile(rx, re.I)) for code, rx in SID.LEVEL)

def prompt() -> str:
  lines = [f'- {e["key"]}: {e["about"]}; fields: {", ".join(e["fields"])}' for e in SK.kinds()]
  return P.render(PROMPT_NAME, lists="\n".join(lines))

def _text(value, limit: int) -> str | None:
  text = re.sub(r"\s+", " ", str(value if value is not None else "")).strip()
  return text[:limit] if text and text.lower() != "null" else None

def _compact(value) -> str:
  return re.sub(r"[^a-z0-9]", "", str(value or "").lower().replace("×", "x"))

def _row(raw, entry: dict) -> tuple:
  if not isinstance(raw, dict):
    return None, ["ROW_NOT_AN_OBJECT"]
  row = {f: _text(raw.get(f), MAX_LAYER if f == "layer" else MAX_CELL) for f in entry["fields"]}
  row["quote"] = _text(raw.get("quote"), MAX_QUOTE)
  return row, []

def validate(parsed) -> tuple[dict | None, list[str]]:
  if not isinstance(parsed, dict) or not isinstance(parsed.get("schedules"), list):
    return None, ["NOT_AN_OBJECT"]
  schedules, problems = [], []
  
  for raw in parsed["schedules"]:
    entry = SK.get(str(raw.get("kind") or "").strip().upper()) if isinstance(raw, dict) else None
    if entry is None:
      problems.append("KIND_NOT_KNOWN")
      continue
    rows = []
    
    for item in raw.get("rows") if isinstance(raw.get("rows"), list) else []:
      row, found = _row(item, entry)
      problems.extend(found)
      if row is not None:
        rows.append(row)
        
    schedules.append({"kind": entry["key"], "rows": rows})
  conf = str(parsed.get("confidence") or "").strip().lower()
  if conf not in CONFIDENCE:
    problems.append("CONFIDENCE_MISSING")
  return {"schedules": schedules, "confidence": conf if conf in CONFIDENCE else "low"}, problems

def floor_of(text) -> str | None:
  return next((code for code, rx in LEVELS if rx.search(str(text or ""))), None)

def size_in(text) -> tuple | None:
  raw = str(text or "").strip()
  found = ST.parse_size(raw)
  if found:
    return found
  m = METRIC_SIZE.match(raw)
  return (round(float(m.group(1)) / IN_MM, 3), round(float(m.group(2)) / IN_MM, 3)) if m else None

def _in_range(size: tuple, ranges) -> bool:
  (a0, a1), (b0, b1) = ranges
  a, b = size[0] * IN_MM, size[1] * IN_MM
  return (a0 <= a <= a1 and b0 <= b <= b1) or (a0 <= b <= a1 and b0 <= a <= b1)

def row_checks(entry: dict, row: dict, tile_text: str | None) -> list:
  quote = row["quote"]
  out = [E.quote_printed(quote, tile_text)] if quote else [E.result("quote_printed", False, "the row has no quote")]
  gone = [f for f in entry["needs"] if not row.get(f)]
  out.append(E.result("fields_given", not gone, "every needed field is given" if not gone else "not given: " + ", ".join(gone)))
  inside = [f for f in entry["quoted"] if row.get(f) and f != "floor" and _compact(row[f]) not in _compact(quote)]
  out.append(E.result("cells_in_quote", not inside, "every cell is inside the quote" if not inside else "not inside the quote: " + ", ".join(inside)))
  if entry.get("mark_category") and row.get("mark"):
    got = MV.default_category(row["mark"])
    out.append(E.result("mark_in_vocab", got == entry["mark_category"], f"{row['mark']} is a {got or 'mark of no kind'}"))
    
  if entry.get("floors"):
    out.append(E.result("floor_known", floor_of(row.get("floor")) is not None, f"floor {floor_of(row.get('floor'))}" if floor_of(row.get("floor")) else f"{row.get('floor')!r} names no floor"))
  if entry.get("size_mm") and row.get("size"):
    size = size_in(row["size"])
    out.append(E.result("size_parses", size is not None, f"{size[0]:g} by {size[1]:g} in" if size else f"{row['size']!r} is not a size the schedule reader knows"))
    if size:
      out.append(E.result("size_in_range", _in_range(size, entry["size_mm"]), "inside the range of the kind" if _in_range(size, entry["size_mm"]) else "outside the range of the kind"))
  return out

def to_item(kind: str, row: dict) -> dict:
  mark = re.sub(r"\s+", "", row["mark"]).upper()
  base = {"source": SOURCE, "quote": row["quote"]}
  if kind == "COLUMN_SCHEDULE":
    a, b = size_in(row["size"])
    return {**base, "mark": mark, "floor": floor_of(row["floor"]), "state": "READ", "cell_uv": None, "size": {"raw": row["size"], "text": row["size"], "size_in": (a, b), "how": SOURCE, "confirmed": False},
      "steel": None, "mid": None, "joint": None, "sketch": {"conflicts": []}, "anchor_native": None, "bars": row.get("bars"), "ties": row.get("ties")}
  if kind == "BEAM_SCHEDULE":
    a, b = size_in(row["size"])
    return {**base, "mark": mark, "width_in": min(a, b), "depth_in": max(a, b), "conflicts": [], "bars": row.get("bars"), "ties": row.get("ties")}
  return {**base, "mark": re.sub(r"\s+", " ", row["mark"]).strip().upper(), "text": row["layer"], "thickness": row.get("thickness")}

def _key(kind: str, item: dict) -> tuple:
  return (kind, _compact(item["mark"]), item.get("floor") if kind == "COLUMN_SCHEDULE" else _compact(item.get("text")) if kind == "FINISH_SCHEDULE" else None)

def _sizes_agree(a: tuple, b: tuple) -> bool:
  tol = SK.tolerance_in()
  return (abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol) or (abs(a[0] - b[1]) <= tol and abs(a[1] - b[0]) <= tol)

def rule_rows(tables: dict | None) -> dict:
  t = tables or {}
  out: dict = {"COLUMN_SCHEDULE": {}, "BEAM_SCHEDULE": {}, "FINISH_SCHEDULE": {}}
  for c in (t.get("column_schedule") or {}).get("cells") or []:
    if c.get("state") == "READ" and (c.get("size") or {}).get("size_in"):
      out["COLUMN_SCHEDULE"][("COLUMN_SCHEDULE", _compact(c["mark"]), c["floor"])] = tuple(c["size"]["size_in"])
  for s in (t.get("beam_sections") or {}).get("sections") or []:
    out["BEAM_SCHEDULE"][("BEAM_SCHEDULE", _compact(s["mark"]), None)] = (s["width_in"], s["depth_in"])
  for b in (t.get("finish_specs") or {}).get("blocks") or []:
    for layer in b.get("layers") or []:
      out["FINISH_SCHEDULE"][("FINISH_SCHEDULE", _compact(b["mark"]), _compact(layer["text"]))] = layer["text"]
  return out

def _finish_agrees(item: dict, mine: dict) -> bool | None:
  area = [text for (_k, mark, _t), text in mine.items() if mark == _compact(item["mark"])]
  if not area:
    return None
  mine_text = _compact(item["text"])
  return any(mine_text in _compact(t) or _compact(t) in mine_text for t in area)

def merge(rule: dict, items: list) -> dict:
  accepted = {"column_schedule": [], "beam_sections": [], "finish_specs": []}
  records = []
  
  for kind, item in items:
    mine = rule.get(kind) or {}
    key = _key(kind, item)
    label = f"{kind}:{item['mark']}" + (f":{item['floor']}" if kind == "COLUMN_SCHEDULE" else "")
    quote = item["quote"]
    if kind == "FINISH_SCHEDULE":
      same, shown, theirs = _finish_agrees(item, mine), item["text"], next((t for (_k, m, _x), t in mine.items() if m == _compact(item["mark"])), None)
    else:
      held = mine.get(key)
      same = None if held is None else _sizes_agree(held, (item["size"]["size_in"] if kind == "COLUMN_SCHEDULE" else (item["width_in"], item["depth_in"])))
      shown = item["size"]["raw"] if kind == "COLUMN_SCHEDULE" else f"{item['width_in']:g}x{item['depth_in']:g}"
      theirs = None if held is None else f"{held[0]:g}x{held[1]:g}"
    if same is None:
      records.append({"fact_key": label, "rule_value": None, "ai_value": shown, "agreement": CMP.AI_ONLY, "quote": quote})
      accepted[{"COLUMN_SCHEDULE": "column_schedule", "BEAM_SCHEDULE": "beam_sections", "FINISH_SCHEDULE": "finish_specs"}[kind]].append(item)
    else:
      records.append({"fact_key": label, "rule_value": theirs, "ai_value": shown, "agreement": CMP.AGREE if same else CMP.DISAGREE, "quote": quote})
      
  accepted["finish_specs"] = _blocks(accepted["finish_specs"])
  return {"accepted": accepted, "records": records}

def _blocks(layers: list) -> list:
  order: dict = {}
  for item in layers:
    order.setdefault(item["mark"], []).append(item)
  return [{"mark": mark, "source": SOURCE, "layers": [{"order": n, "text": i["text"], "thickness": i.get("thickness"), "quote": i["quote"]} for n, i in enumerate(group, 1)]} for mark, group in order.items()]

def accepted_from(ai_value: dict | None, tables: dict | None) -> dict:
  items = [(s["kind"], to_item(s["kind"], r)) for s in (ai_value or {}).get("schedules") or [] for r in s["rows"]]
  return merge(rule_rows(tables), items)["accepted"]

async def read_schedules(*, contents: bytes, page_no: int, ask, store_crop=None, cache_key: str | None = None, model: str | None = None, tables: dict | None = None) -> dict:
  page_pt = await asyncio.to_thread(lambda: R.page_picture(contents, page_no, 64)[1]["page_pt"])
  text = await asyncio.to_thread(R.page_text, contents, page_no, page_pt)
  boxes = R.note_tiles(page_pt, len((text or "").split()))
  prompt_text = prompt()
  
  record = {"task": TASK, "purpose": PURPOSE, "prompt": prompt_text, "prompt_version": PROMPT_VERSION, "schema_version": SCHEMA_VERSION, "crop_key": None, "crop": {"tiles": boxes, "page_pt": page_pt},
    "cache_key": cache_key, "model": model, "rule_value": {"cells": sum(len(v) for v in rule_rows(tables).values())}, "ai_request_id": None, "input_tokens": 0, "output_tokens": 0, "seconds": 0.0,
    "ai_value": None, "comparison": [], "totals": {}, "validators": [], "status": OK, "problems": [], "error": None, "items": {}}
  kept, held, validators, problems, confidences = [], [], [], [], []
  
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
    for schedule in clean["schedules"]:
      entry = SK.get(schedule["kind"])
      for row in schedule["rows"]:
        checks = [{**c, "name": f"{c['name']}.{schedule['kind']}"} for c in row_checks(entry, row, tile_text)]
        validators.extend(checks)
        if all(c["passed"] for c in checks):
          kept.append((schedule["kind"], row))
        else:
          held.append({"kind": schedule["kind"], "mark": row.get("mark"), "reasons": [c["name"].split(".")[0] for c in checks if not c["passed"]], "quote": row.get("quote")})
          problems.append(f"{schedule['kind']}_ROW_HELD")
          
  unique = list({_key(k, to_item(k, r)): (k, r) for k, r in kept}.values())
  merged = merge(rule_rows(tables), [(k, to_item(k, r)) for k, r in unique])
  record["items"] = merged["accepted"]
  grouped: dict = {}
  for kind, row in unique:
    grouped.setdefault(kind, []).append(row)
  record["ai_value"] = {"schedules": [{"kind": k, "rows": rows} for k, rows in grouped.items()], "held": held, "confidence": min(confidences, key=CONFIDENCE.index) if confidences else "low"}
  record["validators"], record["problems"] = validators, problems
  record["comparison"] = merged["records"]
  record["totals"] = CMP.totals(merged["records"])
  return record
