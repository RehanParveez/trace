from __future__ import annotations
import asyncio
import hashlib
import json
import re
from app.modules.drawings_boq.takeoff.ai_reader import prompts as P
from app.engine.catalogue import note_keys as NK
from app.modules.drawings_boq.takeoff.prep import printed_params as PP
from app.modules.drawings_boq.takeoff.ai_reader import cache as CACHE
from app.modules.drawings_boq.takeoff.ai_reader import compare as CMP
from app.modules.drawings_boq.takeoff.ai_reader import examples as EX
from app.modules.drawings_boq.takeoff.ai_reader import evidence as E
from app.modules.drawings_boq.takeoff.ai_reader import regions as R
from app.modules.drawings_boq.takeoff.ai_reader import picture_ink as PI
from app.modules.drawings_boq.takeoff.ai_reader import tasks as T
from app.modules.drawings_boq.takeoff.ai_reader import twice as TW
from app.modules.drawings_boq.takeoff.ai_reader.schedule import sparse
from app.modules.drawings_boq.takeoff.prep import facts as DF

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


def prompt(name: str | None = None, examples: list | None = None, need: dict | None = None) -> str:
  lines = []
  for e in NK.keys():
    if need is not None and e["key"] not in need:
      continue
    scopes = need.get(e["key"]) if need is not None and need.get(e["key"]) else e.get("scopes")
    shown = ", ".join(scopes) if scopes else "any member or material, in a few words"
    lines.append(f'- {e["key"]}: {e["about"]}; unit {e["unit"]}; scope: {shown}')
  return P.render(name or PROMPT_NAME, lists="\n".join(lines), examples=EX.render(examples or [])).rstrip()

def need_of(need: dict | None) -> dict | None:
  """The keys to ask, each with the scopes still missing (None: any scope), cleaned to what note_keys.yaml knows. None asks every key."""
  if need is None:
    return None
  known = {e["key"]: e for e in NK.keys()}
  out: dict = {}
  for key, scopes in need.items():
    if key not in known:
      continue
    offered = known[key].get("scopes") or []
    out[key] = [s for s in scopes if s in offered] if scopes else None
  return out

def ask_state(need: dict | None) -> str:
  if need is None:
    return ""
  body = json.dumps({k: sorted(v) if v else None for k, v in sorted(need.items())}, sort_keys=True, separators=(",", ":"))
  return "ask-" + hashlib.sha256(body.encode("utf-8")).hexdigest()[:8]

def missing(items: list) -> dict:
  params = set(PP.from_items(items or [])["params"])
  kinds = {str(i.get("kind")) for i in items or []}
  out: dict = {}
  for e in NK.keys():
    fills, scopes = list(e.get("fills") or []), list(e.get("scopes") or [])
    if fills:
      if len(fills) > 1 and len(fills) == len(scopes):
        left = [sc for sc, f in zip(scopes, fills) if f not in params]
        if left:
          out[e["key"]] = left
      elif any(f not in params for f in fills):
        out[e["key"]] = None
    elif e["key"] not in kinds:
      out[e["key"]] = None
  return out

def tile_wanted(tile_text: str | None, need: dict | None) -> bool:
  if need is None:
    return True
  if not need:
    return False
  if sparse(tile_text):
    return True
  hay = NK.squash(tile_text)
  return any(w in hay for key in need for w in NK.words_of(NK.get(key)))

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

def fact_checks(fact: dict, tile_text: str | None, support: tuple | None = None) -> list:
  entry = NK.get(fact["key"])
  quote = fact["quote"]
  ocr, clusters = support if support else (None, None)
  out = [E.quote_supported(quote, tile_text, ocr, clusters)] if quote else [E.result("quote_supported", False, "the fact has no quote")]
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
  base = {"kind": fact["key"], "text": fact["quote"][:140], "source": SOURCE, "quote": fact["quote"], "checks": [dict(c) for c in fact.get("checks") or []]}
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

def fills_of(item: dict) -> list:
  entry = NK.get(item["kind"])
  if entry is None or entry["shape"] != "MM":
    return []
  fills, scopes = list(entry.get("fills") or []), list(entry.get("scopes") or [])
  if len(fills) > 1 and len(fills) == len(scopes):
    return [fills[scopes.index(item.get("scope"))]] if item.get("scope") in scopes else []
  return fills

def merge(rule_items: list, items: list) -> dict:
  held = PP.from_items(rule_items or [])["params"] if rule_items else {}
  accepted, records = [], []
  
  for item in items:
    mine = [r for r in rule_items if r.get("kind") == item["kind"] and _scope(r.get("scope")) == _scope(item.get("scope")) and _scope(r.get("where")) == _scope(item.get("where"))
      and (r.get("bar_dia_mm") is None or item.get("bar_dia_mm") is None or abs(float(r["bar_dia_mm"]) - float(item["bar_dia_mm"])) < 0.2)]
    label = f"{item['kind']}:{item.get('scope') or ''}"
    
    taken = [p for p in fills_of(item) if p in held] if not mine and item.get("value_mm") is not None else []
    if taken:
      same = _same(held[taken[0]], item["value_mm"])
      records.append({"fact_key": label, "rule_value": str(held[taken[0]]), "ai_value": str(_value(item)), "agreement": CMP.AGREE if same else CMP.DISAGREE, "quote": item["quote"]})
    elif not mine:
      accepted.append(item)
      records.append({"fact_key": label, "rule_value": None, "ai_value": str(_value(item)), "agreement": CMP.AI_ONLY, "quote": item["quote"]})
    elif any(_same(_value(r), _value(item)) for r in mine):
      records.append({"fact_key": label, "rule_value": str(_value(mine[0])), "ai_value": str(_value(item)), "agreement": CMP.AGREE, "quote": item["quote"]})
    else:
      records.append({"fact_key": label, "rule_value": str(_value(mine[0])), "ai_value": str(_value(item)), "agreement": CMP.DISAGREE, "quote": item["quote"]})
  return {"accepted": accepted, "records": records}

def accepted_from(ai_value: dict | None, rule_items: list) -> list:
  return merge(rule_items, [to_item(f) for f in (ai_value or {}).get("facts") or []])["accepted"]

def fact_key(fact: dict) -> tuple:
  return (fact["key"], _scope(fact.get("scope")), _scope(fact.get("where")), fact.get("bar"))

def facts_of(clean: dict):
  for fact in clean["facts"]:
    yield fact_key(fact), fact

def fact_signature(fact: dict) -> tuple:
  return (fact["key"], _scope(fact.get("scope")), _scope(fact.get("where")), fact.get("bar"), str(fact.get("value")), str(fact.get("unit") or "").lower())

async def read_notes(*, contents: bytes, page_no: int, ask, store_crop=None, cache_key: str | None = None, model: str | None = None, rule_items: list | None = None, prompt_name: str | None = None,
    examples: list | None = None, leave_out_office: bool = False, need: dict | None = None) -> dict:
  page_pt = await asyncio.to_thread(lambda: R.page_picture(contents, page_no, 64)[1]["page_pt"])
  text = await asyncio.to_thread(R.page_text, contents, page_no, page_pt)
  every = R.note_tiles(page_pt, len((text or "").split()))
  need = need_of(need)
  
  tile_texts = [await asyncio.to_thread(R.text_in_boxes, contents, page_no, [box]) for box in every]
  pairs = [(b, t) for b, t in zip(every, tile_texts) if tile_wanted(t, need)]
  boxes = [b for b, _t in pairs]
  version = P.load(prompt_name or PROMPT_NAME)["version"]
  shown = examples if "{examples}" in P.load(prompt_name or PROMPT_NAME)["text"] else []
  prompt_text = prompt(prompt_name, shown, need)
  route = T.route(TASK)
  
  record = {"task": TASK, "purpose": PURPOSE, "prompt": prompt_text, "prompt_version": EX.prompt_version(version, shown, leave_out_office), "schema_version": SCHEMA_VERSION, "crop_key": None, "crop": {"tiles": boxes, "page_pt": page_pt, "reads": [], "review": [], "support": {}, "examples": EX.record(version, shown, leave_out_office)},
    "cache_key": cache_key, "model": model, "rule_value": {"items": len(rule_items or [])}, "ai_request_id": None, "input_tokens": 0, "output_tokens": 0, "seconds": 0.0, "ai_value": None,
    "comparison": [], "totals": {}, "validators": [], "status": OK, "problems": [], "error": None, "items": []}
  if need is not None:
    record["crop"]["ask"] = {"need": need, "tiles_all": len(every), "tiles_asked": len(boxes)}
  facts, validators, problems, confidences, held = [], [], [], [], 0
  how: dict = {}
  by_fact: dict = {}
  
  for n, (box, tile_text) in enumerate(pairs):
    pictures = [(await asyncio.to_thread(R.box_picture, contents, page_no, box, int(R.BOX_LONG_SIDE_PX * scale)))[0] for scale in route["scales"]]
    if n == 0 and store_crop:
      record["crop_key"] = await store_crop(pictures[0])
    support = await asyncio.to_thread(PI.support_inputs, pictures[0]) if sparse(tile_text) else None

    def checks(_key, fact, tile_text=tile_text, support=support):
      return [{**c, "name": f"{c['name']}.{fact['key']}"} for c in fact_checks(fact, tile_text, support)]

    got = await TW.read_region(task=TASK, ask=ask, prompt=prompt_text, pictures=pictures, parse=validate, rows_of=facts_of, signature=fact_signature, checks=checks)
    for spent in got["spent"]:
      record["crop"]["reads"].append({k: (str(v) if k == "ai_request_id" and v is not None else v) for k, v in spent.items()})
      record["model"] = spent.get("model") or record["model"]
      record["ai_request_id"] = spent.get("ai_request_id") or record["ai_request_id"]
      record["input_tokens"] += spent["input_tokens"]
      record["output_tokens"] += spent["output_tokens"]
      record["seconds"] += spent["seconds"]
      
    if got["failed"]:
      record["status"], record["error"] = FAILED, got["failed"][:MAX_ERROR]
      return record
    if got["invalid"]:
      record["status"] = INVALID
      return record
    problems.extend(got["problems"])
    confidences.extend(got["confidences"])
    for a in got["accepted"]:
      validators.extend(a["checks"])
      facts.append(a["row"])
      by_fact[fact_signature(a["row"])] = a["checks"]
      support_of = next((c.get("support") for c in a["checks"] if c["name"].startswith("quote_supported")), None)
      how[a["how"]] = how.get(a["how"], 0) + 1
      record["crop"]["support"][support_of or "NONE"] = record["crop"]["support"].get(support_of or "NONE", 0) + 1
    for r in got["review"]:
      held += 1
      validators.extend(r.get("checks") or [])
      record["crop"]["review"].append({"key": [str(x) for x in r["key"]], "reasons": r["reasons"], "candidates": r["candidates"]})
      problems.append(f"{r['key'][0]}_DROPPED")
        
  facts = list({(f["key"], f["scope"], f["where"], f["bar"], f["value"], f["unit"]): f for f in facts}.values())
  facts = [{**f, "checks": [{**c, "name": c["name"].split(".")[0]} for c in by_fact.get(fact_signature(f), [])]} for f in facts]
  merged = merge(rule_items or [], [to_item(f) for f in facts])
  if need is not None:
    record["crop"]["examples"]["variant"] = f"{record['crop']['examples']['variant']}+ask"
  record["items"] = merged["accepted"]
  record["ai_value"] = {"facts": facts, "confidence": min(confidences, key=CONFIDENCE.index) if confidences else "low"}
  record["validators"], record["problems"] = validators, problems
  record["comparison"] = merged["records"]
  record["totals"] = {**CMP.totals(merged["records"]), "accepted": len(facts), "review": held, "escalated": how.get(TW.ESCALATED, 0)}
  return record

def cached(case_dir: str, variant: str | None = None) -> dict:
  best: dict = {}
  for e in CACHE.read_all(case_dir):
    if e.get("task") != TASK or e.get("status") != OK or not e.get("answer"):
      continue
    if variant is not None and e.get("variant") != variant:
      continue
    slot = (str(e["pdf_sha256"]), int(e["page"]))
    if slot not in best or (e.get("at") or "", e["cache_key"]) > (best[slot].get("at") or "", best[slot]["cache_key"]):
      best[slot] = e
  out: dict = {}
  for (sha, page), e in best.items():
    out.setdefault(sha, {})[page] = e["answer"]
  return out

def set_items(prepared: list) -> list:
  sheets = [{"page_no": n * 10000 + no, "label": None, "facts": a.meta.get("facts"), "ai_facts": None} for n, (_doc, analysed, _problems) in enumerate(prepared) for no, a in sorted(analysed.items()) if (a.meta or {}).get("facts") is not None]
  return DF.gather(sheets)["items"]

def attach(items: list, prepared: list, notes: dict) -> None:
  ruled = set_items(prepared)
  for (_name, data), (_doc, analysed, _problems) in zip(items, prepared):
    by_page = notes.get(CACHE.pdf_sha256(data)) or {}
    for no, a in analysed.items():
      if no in by_page:
        a.meta["ai_facts"] = accepted_from(by_page[no], ruled)
