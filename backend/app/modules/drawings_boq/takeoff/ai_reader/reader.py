from __future__ import annotations
import asyncio
from app.modules.drawings_boq.takeoff.ai_reader import jobs as JOBS
from app.modules.drawings_boq.takeoff.ai_reader import compare as CMP
from app.modules.drawings_boq.takeoff.ai_reader import contract as C
from app.modules.drawings_boq.takeoff.ai_reader import region as R

OK, INVALID, FAILED = "OK", "INVALID", "FAILED"
MAX_ERROR = 500

async def shadow_read(*, contents: bytes, page_no: int, identity: dict | None, mode: str, ask, store_crop) -> dict | None:
  job = JOBS.plan(identity, mode)
  if job is None:
    return None

  png, info = await asyncio.to_thread(R.title_block_picture, contents, page_no)
  crop_key = await store_crop(png)
  result = await ask(C.prompt(), png)

  record = {"purpose": C.PURPOSE, "prompt_version": C.PROMPT_VERSION, "schema_version": C.SCHEMA_VERSION, "crop_key": crop_key, "crop": info,
    "rule_value": job["rule_state"], "ai_request_id": getattr(result, "ai_request_id", None), "ai_value": None, "comparison": [], "totals": {},
    "status": OK, "problems": [], "error": None}
  if not result.success:
    record["status"], record["error"] = FAILED, str(result.error_message or "The AI request failed.")[:MAX_ERROR]
    return record
    
  clean, problems = C.validate(result.parsed_output)
  record["problems"] = problems
  if clean is None:
    record["status"] = INVALID
    return record
  record["ai_value"] = clean
  record["comparison"] = CMP.compare(job["rule_state"], clean)
  record["totals"] = CMP.totals(record["comparison"])
  return record
