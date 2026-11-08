from __future__ import annotations
import contextvars
import os
from contextlib import contextmanager
import yaml

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rule_registry.yaml")
KINDS = ("READING", "MEASUREMENT", "CONVENTION", "PIPELINE")
STATUSES = ("CANDIDATE", "GENERAL", "RETIRED")
DEFAULTS = ("on", "off")
MIN_OFFICES = 2
OVERRIDES_FILE = "proof_overrides.yaml"
RETIRED_CASE_FILES = ("beam_runs.yaml",)
FIELDS = ("id", "module", "kind", "default", "status", "evidence", "notes")
EVIDENCE_FIELDS = ("office", "sets", "metric", "value", "pack", "met")
CLASS_FIELDS = ("recall", "precision", "accuracy")
_FORCED = contextvars.ContextVar("rule_forced", default=None)
_CACHE: dict = {}

def load(path: str = PATH) -> list:
  if path not in _CACHE:
    with open(path, encoding="utf-8") as fh:
      rules = yaml.safe_load(fh) or []
    for r in rules:
      if isinstance(r.get("default"), bool):
        r["default"] = "on" if r["default"] else "off"
    _CACHE[path] = rules
  return _CACHE[path]

def offices_met(rule: dict) -> set:
  return {str(e.get("office")) for e in rule.get("evidence") or [] if e.get("met") is True and e.get("value") is not None and not e.get("unseen")}

def unseen_met(rule: dict) -> bool:
  return any(e.get("unseen") is True and e.get("met") is True and e.get("value") is not None for e in rule.get("evidence") or [])

def unseen_gap(rules: list) -> list:
  return [r["id"] for r in rules if r.get("status") == "GENERAL" and not unseen_met(r)]

def problems(rules: list) -> list:
  """What is wrong with the registry: a missing field, an unknown kind or status, a rule on by default without status GENERAL, or GENERAL without evidence from two offices inside the target."""
  out: list = []
  seen: set = set()
  for i, r in enumerate(rules, 1):
    rid = str(r.get("id") or f"entry {i}")
    for f in FIELDS:
      if f not in r:
        out.append(f"{rid}: field {f} is missing")
    if rid in seen:
      out.append(f"{rid}: listed twice")
    seen.add(rid)
    if r.get("kind") not in KINDS:
      out.append(f"{rid}: kind must be one of {', '.join(KINDS)}")
    if r.get("status") not in STATUSES:
      out.append(f"{rid}: status must be one of {', '.join(STATUSES)}")
    if r.get("default") not in DEFAULTS:
      out.append(f"{rid}: default must be on or off")
    for e in r.get("evidence") or []:
      missing = [k for k in EVIDENCE_FIELDS if k not in e]
      if missing:
        out.append(f"{rid}: an evidence entry lacks {', '.join(missing)}")
    if r.get("class"):
      for f in CLASS_FIELDS:
        if not isinstance(r.get(f), (int, float)) or not 0 < r[f] <= 1:
          out.append(f"{rid}: {f} must be a number above 0 and at most 1 when the rule names a class")
    if r.get("default") == "on" and r.get("status") != "GENERAL":
      out.append(f"{rid}: default on needs status GENERAL")
    if r.get("status") == "GENERAL" and len(offices_met(r)) < MIN_OFFICES:
      out.append(f"{rid}: status GENERAL needs evidence from {MIN_OFFICES} offices inside the target; it has {len(offices_met(r))}")
    if r.get("status") == "RETIRED" and r.get("default") != "off":
      out.append(f"{rid}: a retired rule is off")
  return out

def reload() -> None:
  _CACHE.clear()

def rules() -> list:
  return load()

def get(rule_id: str) -> dict:
  for r in load():
    if r["id"] == rule_id:
      return r
  raise KeyError(f"{rule_id} is not in the rule registry")

def default_of(rule_id: str) -> bool:
  return get(rule_id)["default"] == "on"

def resolve(overrides: dict | None = None) -> dict:
  states = {r["id"]: r["default"] == "on" for r in load()}
  for k, v in (overrides or {}).items():
    if k not in states:
      raise KeyError(f"{k} is not in the rule registry")
    states[k] = bool(v)
  return states

def on(rule_id: str) -> bool:
  forced = _FORCED.get()
  if forced is not None and rule_id in forced:
    get(rule_id)
    return bool(forced[rule_id])
  return default_of(rule_id)

@contextmanager
def using(overrides: dict | None):
  if not overrides:
    yield
    return
  resolve(overrides)
  token = _FORCED.set({**(_FORCED.get() or {}), **{k: bool(v) for k, v in overrides.items()}})
  try:
    yield
  finally:
    _FORCED.reset(token)
