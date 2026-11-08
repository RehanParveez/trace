from __future__ import annotations
import functools
import os
import yaml

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schedule_kinds.yaml")
FIELDS = ("key", "about", "mark_category", "size_mm", "fields", "quoted", "needs", "floors", "feeds")
ROW_FIELDS = ("mark", "floor", "size", "bars", "ties", "layer", "thickness")

class ScheduleKindError(Exception):
  """Raised when the schedule kinds file is wrong or missing."""

@functools.lru_cache(maxsize=1)
def _raw() -> dict:
  with open(PATH, encoding="utf-8") as fh:
    data = yaml.safe_load(fh)
  if not isinstance(data, dict) or not isinstance(data.get("kinds"), list):
    raise ScheduleKindError("schedule_kinds.yaml must hold a list of kinds")
  return data

def problems(data: dict | None = None) -> list:
  from app.modules.drawings_boq.takeoff.extract import members as MB
  from app.modules.drawings_boq.takeoff.prep import mark_vocab as MV
  data = data or _raw()
  out, seen = [], set()
  
  for e in data["kinds"]:
    name = e.get("key", "?")
    out += [f"{name}: no {f}" for f in FIELDS if f not in e]
    out += [f"{name}: repeated"] if name in seen else []
    seen.add(name)
    out += [f"{name}: {f} is not a field a row can have" for f in e.get("fields") or [] if f not in ROW_FIELDS]
    out += [f"{name}: {f} is needed but not listed" for f in e.get("needs") or [] if f not in (e.get("fields") or [])]
    out += [f"{name}: {f} is to be quoted but not listed" for f in e.get("quoted") or [] if f not in (e.get("fields") or [])]
    cat = e.get("mark_category")
    out += [f"{name}: {cat} is not a category of the mark vocabulary"] if cat and cat not in MV.CATEGORIES else []
    if cat in MB._PLAUSIBLE:
      want = [list(r) for r in MB._PLAUSIBLE[cat]]
      out += [f"{name}: the size range {e.get('size_mm')} differs from the range {want} the member reader uses"] if [list(r) for r in e.get("size_mm") or []] != want else []
  return out

def kinds() -> tuple:
  bad = problems()
  if bad:
    raise ScheduleKindError("; ".join(bad[:5]))
  return tuple(_raw()["kinds"])

def get(key: str) -> dict | None:
  return next((e for e in kinds() if e["key"] == key), None)

def tolerance_in() -> float:
  return float(_raw()["agree_tolerance_in"])
