from __future__ import annotations
from uuid import uuid4
from app.modules.drawings_boq.takeoff.ai_reader import evidence as E

CANDIDATE, ACCEPTED, REJECTED, SHADOW = "CANDIDATE", "ACCEPTED", "REJECTED", "SHADOW"
STATUSES = (CANDIDATE, ACCEPTED, REJECTED, SHADOW)
CONFIDENCE_SCORE = {"high": 0.9, "medium": 0.6, "low": 0.3}

def score(confidence) -> float:
  return CONFIDENCE_SCORE.get(str(confidence or "").lower(), 0.0)

def status_of(validators: list, shadow: bool) -> str:
  if shadow:
    return SHADOW
  return CANDIDATE if E.passed(validators) else REJECTED

def build(*, task: str, page: int, value: dict, quotes: list, bbox, confidence, model: str, prompt: str, prompt_version: str, cache_key: str,
    validators: list, shadow: bool, input_tokens, output_tokens) -> dict:
  return {"id": str(uuid4()), "task": task, "page": int(page), "value": value, "evidence": {"text": [q for q in quotes if q], "bbox": list(bbox) if bbox else None},
    "confidence": score(confidence), "model": model, "prompt": prompt, "prompt_version": prompt_version, "cache_key": cache_key, "validators": validators,
    "status": status_of(validators, shadow), "cost": {"input_tokens": int(input_tokens or 0), "output_tokens": int(output_tokens or 0)}}
