from __future__ import annotations
import functools
import os
import yaml
from app.engine.catalogue import loader as CL

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tolerances.yaml")
MAX_PCT = 100.0
FLAT, ITEM = "FLAT", "ITEM"

@functools.lru_cache(maxsize=1)
def _load() -> dict:
  with open(PATH, encoding="utf-8") as fh:
    return yaml.safe_load(fh) or {}

def reload() -> None:
  _load.cache_clear()

def _pct_ok(v) -> bool:
  return isinstance(v, (int, float)) and not isinstance(v, bool) and 0 < v <= MAX_PCT

def problems(doc: dict | None = None) -> list:
  doc = _load() if doc is None else doc
  out = []

  if not _pct_ok(doc.get("default_pct")):
    out.append(f"tolerances.yaml: default_pct must be a number above 0 and at most {MAX_PCT:g}")
  per = doc.get("per_item")
  if not isinstance(per, dict):
    return out + ["tolerances.yaml: per_item must be a mapping of item id to a percentage"]
  ids = {i.id for i in CL.items()}
  
  for k, v in sorted(per.items()):
    if k not in ids:
      out.append(f"tolerances.yaml: {k} is not a catalogue item")
    if not _pct_ok(v):
      out.append(f"tolerances.yaml: {k} must be a number above 0 and at most {MAX_PCT:g}")
  if per and not (doc.get("confirmed_by") and doc.get("confirmed_date")):
    out.append("tolerances.yaml: per_item figures need confirmed_by and confirmed_date (the QS who gave them); without them they are not used")
  return out

def pct_for(item_id: str) -> tuple:
  doc = _load()
  per = doc.get("per_item") or {}
  if item_id in per and doc.get("confirmed_by") and doc.get("confirmed_date") and _pct_ok(per[item_id]):
    return float(per[item_id]), ITEM
  return float(doc["default_pct"]), FLAT
