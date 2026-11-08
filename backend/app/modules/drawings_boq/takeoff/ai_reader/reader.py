from __future__ import annotations
import asyncio
from app.modules.drawings_boq.takeoff.ai_reader import jobs as JOBS
from app.modules.drawings_boq.takeoff.ai_reader import compare as CMP
from app.modules.drawings_boq.takeoff.ai_reader import contract as C
from app.modules.drawings_boq.takeoff.ai_reader import evidence as E
from app.modules.drawings_boq.takeoff.ai_reader import regions as R
from app.modules.drawings_boq.takeoff.prep import page_role as PRL

OK, INVALID, FAILED = "OK", "INVALID", "FAILED"
MAX_ERROR = 500
TASK = "SHEET"

def _choice(name: str, values, offered) -> dict:
  found = [E.choice_offered(v, offered) for v in values]
  bad = [f["detail"] for f in found if not f["passed"]]
  return E.result(name, not bad, "; ".join(bad) if bad else f"every value is one of the {len(list(offered))} offered items")

def field_validators(contents: bytes, page_no: int, info: dict, clean: dict) -> list:
  where = {C.STRIPS: R.text_in_boxes(contents, page_no, info["boxes"]), C.WHOLE_PAGE: R.page_text(contents, page_no, info["page_pt"])}
  out = [{**E.box_on_page(box, info["page_pt"]), "name": f"box_on_page.{i}"} for i, box in enumerate(info["boxes"])]
  options = {**dict(C.CODE_KEYS), **dict(C.LIST_KEYS)}
  for key in C.KEYS:
    value = clean.get(key)
    if value is None:
      continue
    
    quote = clean["quotes"][key]
    checks = [E.quote_printed(quote, where[C.QUOTE_REGION[key]])]
    if key in C.TEXT_KEYS:
      checks.append(E.value_in_quote(value, quote))
    if key == "scale_text":
      checks.append(E.scale_parses(value))
    if key in options:
      checks.append(_choice("choice_offered", value if isinstance(value, list) else [value], options[key]))
    out.extend({**c, "name": f"{c['name']}.{key}"} for c in checks)
  return out

def drop_failed(clean: dict, validators: list) -> list:
  failed = {v["name"].rsplit(".", 1)[-1] for v in validators if not v["passed"]} & set(C.KEYS)
  for key in failed:
    clean[key] = None
    clean["quotes"].pop(key, None)
  return [f"{k.upper()}_DROPPED" for k in C.KEYS if k in failed]

async def read_sheet(*, contents: bytes, page_no: int, ask, store_crop=None, cache_key: str | None = None, model: str | None = None, rule_state: dict | None = None) -> dict:
  png, info = await asyncio.to_thread(R.title_block_picture, contents, page_no)
  page_png, _page_info = await asyncio.to_thread(R.page_picture, contents, page_no)
  crop_key = await store_crop(png) if store_crop else None
  prompt = C.prompt()
  result = await ask(prompt, png, [page_png])

  record = {"task": TASK, "purpose": C.PURPOSE, "prompt": prompt, "prompt_version": C.PROMPT_VERSION, "schema_version": C.SCHEMA_VERSION, "crop_key": crop_key, "crop": info,
    "cache_key": cache_key, "model": getattr(result, "model", None) or model, "rule_value": rule_state or {}, "ai_request_id": getattr(result, "ai_request_id", None),
    "input_tokens": getattr(result, "input_tokens", None), "output_tokens": getattr(result, "output_tokens", None), "seconds": getattr(result, "seconds", None),
    "ai_value": None, "comparison": [], "totals": {}, "validators": [], "status": OK, "problems": [], "error": None}
  if not result.success:
    record["status"], record["error"] = FAILED, str(result.error_message or "The AI request failed.")[:MAX_ERROR]
    return record

  clean, problems = C.validate(result.parsed_output)
  record["problems"] = problems
  if clean is None:
    record["status"] = INVALID
    return record
  record["validators"] = await asyncio.to_thread(field_validators, contents, page_no, info, clean)
  record["problems"] = problems + drop_failed(clean, record["validators"])
  record["ai_value"] = clean
  vote = PRL.shadow_vote({"signals": (rule_state or {}).get("signals")}, clean)
  record["comparison"] = CMP.attach_vote(CMP.compare(rule_state, clean), vote)
  record["totals"] = CMP.totals(record["comparison"])
  return record

async def shadow_read(*, contents: bytes, page_no: int, identity: dict | None, mode: str, ask, store_crop, cache_key: str | None = None, model: str | None = None) -> dict | None:
  job = JOBS.plan(identity, mode)
  if job is None:
    return None
  return await read_sheet(contents=contents, page_n=page_no, ask=ask, store_crop=store_crop, cache_key=cache_key, model=model, rule_state=job["rule_state"])
