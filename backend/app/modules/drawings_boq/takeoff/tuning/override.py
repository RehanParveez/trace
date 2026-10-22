from __future__ import annotations
import importlib
import threading
from app.modules.drawings_boq.takeoff.tuning import registry as R
from contextlib import contextmanager

class NotIsolated(RuntimeError):
  """A value was about to be set in a process that may be serving requests."""

class BadValue(ValueError):
  """A value that cannot be set: unknown constant, not a number, outside the search range, a count that is not whole, or a minimum over its maximum."""

_state = {"isolated": False, "active": False}
_lock = threading.Lock()

def mark_isolated() -> None:
  _state["isolated"] = True

def is_isolated() -> bool:
  return bool(_state["isolated"])

def check(changes: dict) -> dict:
  out = {}
  
  for key, value in changes.items():
    try:
      p = R.get(key)
    except KeyError:
      raise BadValue(f"{key} is not in the tuning register.")
    if p.status != R.SWEEPABLE:
      raise BadValue(f"{key} cannot be swept: {p.reasons[0] if p.reasons else p.status}.")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
      raise BadValue(f"{key} must be a number.")
    v = float(value)
    if p.kind == "int":
      if v != int(v):
        raise BadValue(f"{key} is a count, so {value} is not allowed.")
      v = int(v)
      
    if not (p.lo <= v <= p.hi):
      raise BadValue(f"{key} is searched between {p.lo:g} and {p.hi:g}, so {value} is not allowed.")
    out[p.key] = v
  now = {p.key: p.live for p in R.params()}
  now.update(out)
  for lo_key, hi_key in R.min_max_pairs(list(now)):
    if lo_key in out or hi_key in out:
      if now[lo_key] >= now[hi_key]:
        raise BadValue(f"{lo_key} ({now[lo_key]:g}) must stay under {hi_key} ({now[hi_key]:g}).")
  return out

def _targets(p: R.Param) -> list:
  return [(p.module, p.attr), *p.copies]

@contextmanager
def overridden(changes: dict):
  if not _state["isolated"]:
    raise NotIsolated("Constants are set only in the sweep tool's own process (call mark_isolated() first). Never in the web application.")
  values = check(changes)
  if not _lock.acquire(blocking=False):
    raise RuntimeError("A constant is already set; the sweep sets one run at a time.")
  saved = []
  
  try:
    _state["active"] = True
    for key, v in values.items():
      for mod, attr in _targets(R.get(key)):
        m = importlib.import_module(mod)
        saved.append((m, attr, getattr(m, attr)))
        setattr(m, attr, v)
    yield values
  finally:
    for m, attr, old in reversed(saved):
      setattr(m, attr, old)
    _state["active"] = False
    _lock.release()
