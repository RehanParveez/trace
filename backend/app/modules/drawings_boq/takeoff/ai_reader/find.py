from __future__ import annotations
import asyncio
import math
from app.modules.drawings_boq.takeoff.ai_reader import prompts as P
from app.modules.drawings_boq.takeoff.ai_reader import evidence as E
from app.modules.drawings_boq.takeoff.ai_reader import regions as R
from app.modules.drawings_boq.takeoff.ai_reader import tasks as T

TASK = "FIND"
PURPOSE = "REGION_FIND"
PROMPT_NAME = "find.v1"
PROMPT_VERSION = P.load(PROMPT_NAME)["version"]
SCHEMA_VERSION = "1"
KINDS = ("SCHEDULE", "SECTION_PICTURE")
CONFIDENCE = ("high", "medium", "low")
MAX_REGIONS = 12
MIN_SHARE = 0.01
OK, INVALID, FAILED = "OK", "INVALID", "FAILED"
MAX_ERROR = 500

def prompt() -> str:
  return P.render(PROMPT_NAME)

def validate(parsed) -> tuple:
  if not isinstance(parsed, dict) or not isinstance(parsed.get("regions"), list):
    return None, ["NOT_AN_OBJECT"]
  out, problems = [], []
  for raw in parsed["regions"][:MAX_REGIONS]:
    kind = str(raw.get("kind") or "").strip().upper() if isinstance(raw, dict) else ""
    box = raw.get("box") if isinstance(raw, dict) else None
    if kind not in KINDS:
      problems.append("KIND_NOT_KNOWN")
      continue
    try:
      l, t, r, b = (float(v) for v in box)
    except (TypeError, ValueError):
      problems.append("BOX_NOT_FOUR_NUMBERS")
      continue
    if not all(math.isfinite(v) and -0.001 <= v <= 1.001 for v in (l, t, r, b)) or r - l < MIN_SHARE or b - t < MIN_SHARE:
      problems.append("BOX_OFF_PICTURE")
      continue
    title = raw.get("title")
    out.append({"kind": kind, "share": [max(0.0, l), max(0.0, t), min(1.0, r), min(1.0, b)], "title": str(title).strip()[:120] if title else ""})
  conf = str(parsed.get("confidence") or "").strip().lower()
  if conf not in CONFIDENCE:
    problems.append("CONFIDENCE_MISSING")
  return {"regions": out, "confidence": conf if conf in CONFIDENCE else "low"}, problems

def proposals(clean: dict, page_pt) -> list:
  w, h = (float(v) for v in page_pt)
  return [{"kind": r["kind"], "box": [round(r["share"][0] * w, 2), round(r["share"][1] * h, 2), round(r["share"][2] * w, 2), round(r["share"][3] * h, 2)], "title": r["title"]} for r in clean["regions"]]

async def read_find(*, contents: bytes, page_no: int, ask, store_crop=None, cache_key: str | None = None, model: str | None = None) -> dict:
  png, info = await asyncio.to_thread(R.page_picture, contents, page_no)
  crop_key = await store_crop(png) if store_crop else None
  prompt_text = prompt()
  
  record = {"task": TASK, "purpose": PURPOSE, "prompt": prompt_text, "prompt_version": PROMPT_VERSION, "schema_version": SCHEMA_VERSION, "crop_key": crop_key, "crop": {**info, "reads": []},
    "cache_key": cache_key, "model": model, "rule_value": {}, "ai_request_id": None, "input_tokens": 0, "output_tokens": 0, "seconds": 0.0, "ai_value": None, "comparison": [], "totals": {},
    "validators": [], "status": OK, "problems": [], "error": None, "proposals": []}
  result = await ask(prompt_text, png, [], model=T.model_of(T.CHEAP))
  spent = {"tier": T.CHEAP, "scale": 1.0, "model": getattr(result, "model", None), "input_tokens": int(getattr(result, "input_tokens", None) or 0),
    "output_tokens": int(getattr(result, "output_tokens", None) or 0), "seconds": float(getattr(result, "seconds", None) or 0.0)}
  
  record["crop"]["reads"].append(spent)
  record["model"] = spent["model"] or model
  record["ai_request_id"] = getattr(result, "ai_request_id", None)
  record["input_tokens"], record["output_tokens"], record["seconds"] = spent["input_tokens"], spent["output_tokens"], spent["seconds"]
  if not result.success:
    record["status"], record["error"] = FAILED, str(result.error_message or "The AI request failed.")[:MAX_ERROR]
    return record
  
  clean, problems = validate(result.parsed_output)
  record["problems"] = problems
  if clean is None:
    record["status"] = INVALID
    return record
  
  record["validators"] = [{**E.box_on_page(p["box"], info["page_pt"]), "name": f"box_on_page.{i}"} for i, p in enumerate(proposals(clean, info["page_pt"]))]
  record["proposals"] = [p for p, v in zip(proposals(clean, info["page_pt"]), record["validators"]) if v["passed"]]
  record["ai_value"] = {"regions": clean["regions"], "proposals": record["proposals"], "confidence": clean["confidence"]}
  record["totals"] = {"accepted": 0, "review": 0, "proposed": len(record["proposals"])}
  return record
