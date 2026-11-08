from __future__ import annotations
import functools
import os
import yaml

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "confidence.yaml")
HIGH, MEDIUM, LOW = "High", "Medium", "Low"
ORDER = (LOW, MEDIUM, HIGH)
CHECKS_PASS, CHECK_FAILS, NO_CHECK = "checks_pass", "check_fails", "no_check"
CONDITIONS = (CHECKS_PASS, CHECK_FAILS, NO_CHECK)

@functools.lru_cache(maxsize=1)
def _load() -> dict:
  with open(PATH, encoding="utf-8") as fh:
    return yaml.safe_load(fh) or {}

def reload() -> None:
  _load.cache_clear()

def doc() -> dict:
  return _load()

def _share(v) -> bool:
  return isinstance(v, (int, float)) and not isinstance(v, bool) and 0 < v <= 1

def share_of(cell: dict | None) -> float | None:
  if not cell or not cell.get("items"):
    return None
  return cell["right"] / cell["items"]

def shown_by_numbers(d: dict) -> bool:
  c = d.get("calibrated") or {}
  s = d.get("show_when") or {}
  return bool(c) and c.get("high_items", 0) >= s.get("min_items", 1) and c.get("high_right_out_of_sample") is not None and c["high_right_out_of_sample"] >= s.get("high_right", 1.0)

def problems(d: dict | None = None) -> list:
  d = _load() if d is None else d
  out = []
  
  t = d.get("thresholds") or {}
  if not (_share(t.get("high")) and _share(t.get("low")) and t["low"] < t["high"]):
    out.append("confidence.yaml: thresholds needs low and high, shares with low below high")
  for k in ("show_when", "kill"):
    if not _share((d.get(k) or {}).get("high_right")):
      out.append(f"confidence.yaml: {k} needs high_right, a share")
  if not isinstance((d.get("show_when") or {}).get("min_items"), int):
    out.append("confidence.yaml: show_when needs min_items")
  if not isinstance(d.get("min_cell"), int) or d["min_cell"] < 1:
    out.append("confidence.yaml: min_cell must be a whole number from 1")
  if not isinstance(d.get("shown"), bool):
    out.append("confidence.yaml: shown must be true or false")
  text = d.get("text") or {}
  for k in (HIGH, MEDIUM, LOW, "assumed", "unread", "check_failed", "few", "line_assumed"):
    if not isinstance(text.get(k), str) or not text[k]:
      out.append(f"confidence.yaml: text needs a sentence for {k}")
      
  classes = d.get("classes")
  if not isinstance(classes, dict):
    return out + ["confidence.yaml: classes must be a mapping of reading class to its calibration"]
  for cls, cells in sorted(classes.items()):
    for cond, cell in sorted((cells or {}).items()):
      if cond not in CONDITIONS:
        out.append(f"confidence.yaml: {cls} has a condition {cond} that is not one of {', '.join(CONDITIONS)}")
      elif not (isinstance(cell, dict) and all(isinstance(cell.get(k), int) and cell[k] >= 0 for k in ("items", "right", "sets")) and cell["right"] <= cell["items"]):
        out.append(f"confidence.yaml: {cls}/{cond} needs whole numbers items, right and sets, with right not above items")
        
  cal = d.get("calibrated")
  if d.get("shown") and not shown_by_numbers(d):
    out.append("confidence.yaml: shown is true but the calibration does not reach show_when: confidence is not shown before it is calibrated")
  if not cal and d.get("shown"):
    out.append("confidence.yaml: shown is true with no calibration")
  if cal and cal.get("high_right_out_of_sample") is not None and cal["high_right_out_of_sample"] < d["kill"]["high_right"] and d.get("shown"):
    out.append("confidence.yaml: High was right less often than the kill figure out of sample, so confidence must not be shown")
  return out

def thresholds() -> dict:
  return dict(_load()["thresholds"])

def shown() -> bool:
  d = _load()
  return bool(d.get("shown")) and not problems(d)

def text(key: str) -> str:
  return _load()["text"][key]

def cell(cls: str, cond: str, d: dict | None = None) -> dict | None:
  return ((d or _load()).get("classes") or {}).get(cls, {}).get(cond)

def band(cls: str, cond: str, d: dict | None = None) -> tuple:
  d = _load() if d is None else d
  t = d["thresholds"]
  if cond == CHECK_FAILS:
    return LOW, "check_failed"
  c = cell(cls, cond, d)
  share = share_of(c)
  
  if share is None or c["items"] < d["min_cell"]:
    return MEDIUM, "few"
  if share < t["low"]:
    return LOW, LOW
  if cond == CHECKS_PASS and share >= t["high"]:
    return HIGH, HIGH
  return MEDIUM, MEDIUM

def lowest(bands: list) -> str:
  return min(bands, key=ORDER.index)
