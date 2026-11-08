from __future__ import annotations
import functools
import os
import yaml

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.yaml")

class SettingsError(ValueError):
  pass

def _number(doc: dict, path: tuple, low: float, high: float) -> float:
  node = doc
  for part in path:
    node = node.get(part) if isinstance(node, dict) else None
  if isinstance(node, bool) or not isinstance(node, (int, float)) or not low <= node <= high:
    raise SettingsError(f"{os.path.basename(PATH)}: {'.'.join(path)} must be a number from {low:g} to {high:g}")
  return node

def check(doc: dict) -> dict:
  _number(doc, ("sample", "share"), 0.01, 1.0)
  _number(doc, ("sample", "min_items"), 1, 10000)
  _number(doc, ("wrong_share_limit",), 0.0, 1.0)
  _number(doc, ("regions", "overlap"), 0.05, 1.0)
  _number(doc, ("regions", "pad_share"), 0.0, 0.5)
  _number(doc, ("unseen", "min_truth"), 1, 10000)
  gaps = (doc.get("regions") or {}).get("gap_share")
  kinds = (doc.get("regions") or {}).get("kind_of_class")
  if not isinstance(gaps, dict) or not isinstance(kinds, dict):
    raise SettingsError(f"{os.path.basename(PATH)}: regions needs gap_share and kind_of_class")
  for kind in gaps:
    _number(doc, ("regions", "gap_share", kind), 0.01, 2.0)
  for cls, kind in kinds.items():
    if kind not in gaps:
      raise SettingsError(f"{os.path.basename(PATH)}: regions.kind_of_class.{cls} is {kind!r}, which has no gap_share")
  return doc

@functools.lru_cache(maxsize=1)
def _load() -> dict:
  with open(PATH, encoding="utf-8") as fh:
    return check(yaml.safe_load(fh) or {})

def load() -> dict:
  return _load()

def reload() -> None:
  _load.cache_clear()

def sample_share() -> float:
  return float(load()["sample"]["share"])

def sample_min() -> int:
  return int(load()["sample"]["min_items"])

def unseen_min_truth() -> int:
  return int(load()["unseen"]["min_truth"])

def wrong_share_limit() -> float:
  return float(load()["wrong_share_limit"])
