from __future__ import annotations
import asyncio
from app.modules.drawings_boq.takeoff.ai_reader import jobs as JOBS
from app.modules.drawings_boq.takeoff.ai_reader import compare as CMP
from app.modules.drawings_boq.takeoff.ai_reader import contract as C
from app.modules.drawings_boq.takeoff.ai_reader import evidence as E
from app.modules.drawings_boq.takeoff.ai_reader import regions as R

OK, INVALID, FAILED = "OK", "INVALID", "FAILED"
MAX_ERROR = 500
TASK = "SHEET"

def sheet_validators(contents: bytes, page_no: int, info: dict, clean: dict) -> list:
  text = R.text_in_boxes(contents, page_no, info["boxes"])
  out = [E.box_on_page(box, info["page_pt"]) for box in info["boxes"]]
  out = [{**v, "name": f"box_on_page.{i}"} for i, v in enumerate(out)]
  for key in C.TEXT_KEYS:
    if clean.get(key):
      out.append({**E.quote_printed(clean[key], text), "name": f"quote_printed.{key}"})
  return out

async def read_sheet(*, contents: bytes, page_no: int, ask, store_crop=None, cache_key: str | None = None, model: str | None = None, rule_state: dict | None = None) -> dict:
  png, info = await asyncio.to_thread(R.title_block_picture, contents, page_no)
  crop_key = await store_crop(png) if store_crop else None
  prompt = C.prompt()
  result = await ask(prompt, png)

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
  record["ai_value"] = clean
  record["validators"] = await asyncio.to_thread(sheet_validators, contents, page_no, info, clean)
  record["comparison"] = CMP.compare(rule_state, clean)
  record["totals"] = CMP.totals(record["comparison"])
  return record

async def shadow_read(*, contents: bytes, page_no: int, identity: dict | None, mode: str, ask, store_crop, cache_key: str | None = None, model: str | None = None) -> dict | None:
  job = JOBS.plan(identity, mode)
  if job is None:
    return None
  return await read_sheet(contents=contents, page_no=page_no, ask=ask, store_crop=store_crop, cache_key=cache_key, model=model, rule_state=job["rule_state"])
