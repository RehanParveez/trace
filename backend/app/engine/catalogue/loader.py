from __future__ import annotations
import functools
import os
import yaml
from app.engine.catalogue import model as M

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "elements.yaml")

class CatalogueError(Exception):
  pass

def _raw(path: str = PATH) -> list:
  with open(path, encoding="utf-8") as fh:
    data = yaml.safe_load(fh)
  if not isinstance(data, list):
    raise CatalogueError("elements.yaml must be a list of items")
  return data

def problems(path: str = PATH) -> list:
  from app.engine.measure import rule_registry as RR
  from app.engine.catalogue import conventions as CV
  return M.validate(_raw(path), {r["id"] for r in RR.load()} | set(CV.raw_ids()))

@functools.lru_cache(maxsize=1)
def _load() -> tuple:
  raws = _raw()
  bad = M.validate(raws)
  if bad:
    raise CatalogueError("; ".join(bad[:5]) + (f"; and {len(bad) - 5} more" if len(bad) > 5 else ""))
  return tuple(M.parse(r) for r in raws)

def items() -> tuple:
  return _load()

def get(item_id: str) -> M.Item | None:
  return next((i for i in _load() if i.id == item_id), None)

def by_owner(owner: str) -> list:
  return [i for i in _load() if i.owner_pack == owner]

def by_line(line: str) -> list:
  return [i for i in _load() if any(b.line == line for b in i.billing.PRIVATE_QS)]

def lines() -> dict:
  out: dict = {}
  for i in _load():
    for b in i.billing.PRIVATE_QS:
      out.setdefault(b.line, []).append(i.id)
  return out

def reload() -> None:
  _load.cache_clear()

def expected_classes() -> dict:
  return M.expected_classes(list(_load()))
