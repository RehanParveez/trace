from __future__ import annotations
from app.modules.drawings_boq.takeoff.ai_reader import tasks as T

ACCEPTED, REVIEW = "ACCEPTED", "REVIEW"
AGREED, ESCALATED = "AGREED", "ESCALATED"

def _spent(result) -> dict:
  return {"model": getattr(result, "model", None), "input_tokens": int(getattr(result, "input_tokens", None) or 0), "output_tokens": int(getattr(result, "output_tokens", None) or 0),
    "seconds": float(getattr(result, "seconds", None) or 0.0), "ai_request_id": getattr(result, "ai_request_id", None)}

def _rows(parse, rows_of, result) -> tuple:
  if not result.success:
    return None, [], None
  clean, problems = parse(result.parsed_output)
  if clean is None:
    return None, problems, None
  out: dict = {}
  for key, row in rows_of(clean):
    out.setdefault(key, row)
  return out, problems, clean.get("confidence")

def decide(readings: list, strong: dict | None, signature, checks) -> dict:
  usable = [r["rows"] for r in readings if r["rows"] is not None]
  keys: list = []
  for rows in usable + ([strong["rows"]] if strong and strong["rows"] is not None else []):
    for k in rows:
      if k not in keys:
        keys.append(k)
  accepted, review = [], []
  
  for key in keys:
    mine = [rows[key] for rows in usable if key in rows]
    agreed = len(usable) >= 2 and len(mine) == len(usable) and len({signature(r) for r in mine}) == 1
    if agreed:
      done = checks(key, mine[0])
      if all(c["passed"] for c in done):
        accepted.append({"key": key, "row": mine[0], "how": AGREED, "checks": done})
        continue
      review.append({"key": key, "reasons": [c["name"] for c in done if not c["passed"]], "candidates": [mine[0]], "checks": done})
      continue
    if strong is None or strong["rows"] is None:
      review.append({"key": key, "reasons": ["READINGS_DISAGREE" if len(mine) == len(usable) else "ONE_READING_ONLY"], "candidates": mine})
      continue
    theirs = strong["rows"].get(key)
    if theirs is None:
      review.append({"key": key, "reasons": ["STRONGER_MODEL_GAVE_NO_ROW"], "candidates": mine})
      continue
    done = checks(key, theirs)
    if all(c["passed"] for c in done):
      accepted.append({"key": key, "row": theirs, "how": ESCALATED, "checks": done})
    else:
      review.append({"key": key, "reasons": ["READINGS_DISAGREE"] + [c["name"] for c in done if not c["passed"]], "candidates": mine + [theirs], "checks": done})
  return {"accepted": accepted, "review": review}

async def read_region(*, task: str, ask, prompt: str, pictures: list, parse, rows_of, signature, checks) -> dict:
  route = T.route(task)
  readings, spent, problems, confidences = [], [], [], []
  failed = None
  
  for scale, png in zip(route["scales"], pictures):
    result = await ask(prompt, png, [], model=T.model_of(T.CHEAP))
    spent.append({"tier": T.CHEAP, "scale": scale, **_spent(result)})
    rows, found, conf = _rows(parse, rows_of, result)
    problems.extend(found)
    if rows is None and not result.success:
      failed = str(getattr(result, "error_message", None) or "The AI request failed.")
    if conf:
      confidences.append(conf)
    readings.append({"scale": scale, "rows": rows})
    
  if all(r["rows"] is None for r in readings):
    return {"accepted": [], "review": [], "spent": spent, "problems": problems, "confidences": confidences, "failed": failed, "invalid": failed is None}
  strong = None
  if route["escalate"]:
    differs = _needs_strong(readings, signature)
    if differs:
      result = await ask(prompt, pictures[-1], [], model=T.model_of(T.STRONG))
      spent.append({"tier": T.STRONG, "scale": route["scales"][-1], **_spent(result)})
      rows, found, conf = _rows(parse, rows_of, result)
      problems.extend(found)
      if conf:
        confidences.append(conf)
      strong = {"rows": rows}
  got = decide(readings, strong, signature, checks)
  return {**got, "spent": spent, "problems": problems, "confidences": confidences, "failed": None, "invalid": False}

def _needs_strong(readings: list, signature) -> bool:
  usable = [r["rows"] for r in readings if r["rows"] is not None]
  if len(usable) < len(readings):
    return True
  keys = set().union(*[set(r) for r in usable]) if usable else set()
  return any(len([r for r in usable if k in r]) != len(usable) or len({signature(r[k]) for r in usable if k in r}) != 1 for k in keys)
