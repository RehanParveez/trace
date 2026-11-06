from __future__ import annotations
from app.modules.drawings_boq.takeoff.questions import keys as QK
from datetime import datetime, timezone

META_ANSWERS = "takeoff_answers"
META_LEDGER = "completeness"

def stored(meta: dict | None) -> dict:
  raw = (meta or {}).get(META_ANSWERS) or {}
  return {k: dict(v) for k, v in raw.items() if QK.is_question_key(k) and isinstance(v, dict) and v.get("value") is not None}

def merge(metas: list) -> dict:
  out: dict = {}
  for meta in metas:
    for k, v in stored(meta).items():
      if k not in out or str(v.get("at") or "") >= str(out[k].get("at") or ""):
        out[k] = v
  return out

def put(meta: dict | None, key: str, value, user_id, now: datetime | None = None) -> dict:
  held = dict((meta or {}).get(META_ANSWERS) or {})
  held[key] = {"value": str(value), "by": str(user_id), "at": (now or datetime.now(timezone.utc)).isoformat()}
  return {**(meta or {}), META_ANSWERS: held}

def clear(meta: dict | None, key: str) -> dict:
  held = dict((meta or {}).get(META_ANSWERS) or {})
  held.pop(key, None)
  return {**(meta or {}), META_ANSWERS: held}

def split_case(decisions: list) -> tuple:
  engine, answers = [], {}
  for d in decisions:
    if QK.is_question_key(d["id"]):
      answers[d["id"]] = {"value": str(d["value"]), "by": d["answered_by"], "at": d["date"], "source": d.get("source")}
    else:
      engine.append(d)
  return engine, answers
