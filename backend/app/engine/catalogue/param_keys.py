from __future__ import annotations
import functools
import hashlib
import json
import os
import yaml

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "param_keys.yaml")
SHAPES = ("MM", "RATIO", "MIX")
STATUSES = ("LIVE", "NO_READER", "WAITING")
LEVELS = ("LABEL", "SCHEDULE", "SECTION", "NOTE")
CONSUMER_KINDS = ("param", "spec", "question")
FIELDS = ("key", "shape", "unit", "range", "scopes", "consumer", "reader", "status", "about")
KIND_PREFIX = "PARAM_"

class ParamKeyError(Exception):
  pass

@functools.lru_cache(maxsize=1)
def _raw() -> dict:
  with open(PATH, encoding="utf-8") as fh:
    data = yaml.safe_load(fh)
  if not isinstance(data, dict) or not isinstance(data.get("keys"), list):
    raise ParamKeyError("param_keys.yaml must hold a list of keys")
  return data

def _consumer_problem(name: str, c: dict) -> str | None:
  from app.engine.measure import derived as DV
  from app.modules.drawings_boq.pricing.billing import profiles as PF
  from app.modules.drawings_boq.takeoff.questions import keys as QK
  if not isinstance(c, dict) or c.get("kind") not in CONSUMER_KINDS or not c.get("name"):
    return f"{name}: a consumer is {{kind: {'|'.join(CONSUMER_KINDS)}, name}}"
  who = str(c["name"])
  if c["kind"] == "param" and who not in DV.PARAMS and who not in DV.ASKED_PARAMS:
    return f"{name}: no calculation parameter {who}"
  if c["kind"] == "spec" and who not in PF.spec_defaults():
    return f"{name}: no billing spec {who}"
  if c["kind"] == "question" and not QK.is_question_key(who):
    return f"{name}: {who} is not a question key"
  return None

def problems(data: dict | None = None) -> list:
  from app.engine.measure import rule_registry as RR
  data = data or _raw()
  out, seen = [], set()
  if sorted(data.get("precedence") or []) != sorted(LEVELS) or len(set(data.get("precedence") or [])) != len(LEVELS):
    out.append(f"precedence must list each of {', '.join(LEVELS)} once, strongest first")
  elif list(data["precedence"]) != list(LEVELS):
    out.append(f"precedence must be {', '.join(LEVELS)}: the code ranks levels in that order")
  rules = {r["id"]: r for r in RR.load()}
  
  try:
    from app.engine.catalogue import note_keys as NK
    taken = {e["key"] for e in NK._raw()["keys"]}
  except Exception:
    taken = set()
  for e in data["keys"]:
    name = e.get("key", "?")
    out += [f"{name}: no {f}" for f in FIELDS if f not in e]
    out += [f"{name}: repeated"] if name in seen else []
    out += [f"{name}: is already a note key"] if name in taken else []
    seen.add(name)
    if e.get("shape") not in SHAPES:
      out.append(f"{name}: shape {e.get('shape')} is not one of {', '.join(SHAPES)}")
    low_high = e.get("range") or [0, 0]
    if len(low_high) != 2 or low_high[0] >= low_high[1]:
      out.append(f"{name}: the range is empty")
    if not isinstance(e.get("scopes"), list) or not e.get("scopes"):
      out.append(f"{name}: scopes must be a list")
    status = e.get("status")
    if status not in STATUSES:
      out.append(f"{name}: status {status} is not one of {', '.join(STATUSES)}")
      continue
    consumer, reader = e.get("consumer"), e.get("reader")
    if status == "WAITING":
      out += [f"{name}: a WAITING key has no consumer and no reader"] if consumer or reader else []
      continue
    bad = _consumer_problem(name, consumer)
    out += [bad] if bad else []
    if status == "NO_READER" and reader:
      out.append(f"{name}: NO_READER names a reader")
    if status == "LIVE":
      rule = rules.get(reader)
      if rule is None:
        out.append(f"{name}: the reader {reader} is not in the rule registry")
      elif rule.get("kind") != "READING":
        out.append(f"{name}: the reader {reader} must be a READING rule")
  return out

def state(data: dict | None = None) -> str:
  body = json.dumps((data or _raw())["keys"], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
  return hashlib.sha256(body.encode("utf-8")).hexdigest()[:8]

@functools.lru_cache(maxsize=1)
def keys() -> tuple:
  bad = problems()
  if bad:
    raise ParamKeyError("; ".join(bad[:5]))
  return tuple(_raw()["keys"])

def get(key: str) -> dict | None:
  return next((e for e in keys() if e["key"] == key), None)

def live(reader: str | None = None) -> tuple:
  return tuple(e for e in keys() if e["status"] == "LIVE" and (reader is None or e["reader"] == reader))

def kind_of(key: str) -> str:
  return KIND_PREFIX + key

def key_of(kind: str) -> str | None:
  k = str(kind or "")
  return k[len(KIND_PREFIX):] if k.startswith(KIND_PREFIX) and get(k[len(KIND_PREFIX):]) else None

def rank(level: str | None) -> int:
  return LEVELS.index(level) if level in LEVELS else len(LEVELS) - 1

def tolerance_mm() -> float:
  return float(_raw()["agree_tolerance_mm"])
