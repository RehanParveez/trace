from __future__ import annotations
from collections import Counter
from app.modules.drawings_boq.takeoff.extract import config as C

HEAD_ROUND_MM = 10.0
HEAD_MIN_MM = 1500.0
HEAD_MAX_MM = 3500.0
DOOR_HEIGHT, COMMON_DOOR_HEAD = "DOOR_HEIGHT", "COMMON_DOOR_HEAD"

def _sane(h) -> float | None:
  try:
    v = float(h)
  except (TypeError, ValueError):
    return None
  return v if HEAD_MIN_MM <= v <= HEAD_MAX_MM else None

def door_heads(openings: list) -> list:
  """The heights of the marked doors of a plan, one per door mark counted, rounded to 10 mm."""
  out = []
  for o in openings:
    size = (o.facts or {}).get("size_schedule_mm")
    if o.category != "DOOR" or not size or len(size) < 2:
      continue
    h = _sane(size[1])
    if h is not None:
      out.extend([round(h / HEAD_ROUND_MM) * HEAD_ROUND_MM] * max(1, int(o.count or 1)))
  return out

def common_head(heights: list) -> float | None:
  """The most usual door head; the lower one when two are equally usual."""
  if not heights:
    return None
  counts = Counter(heights)
  top = max(counts.values())
  return min(h for h, n in counts.items() if n == top)

def apply(candidates: list, openings: list) -> dict:
  """Put the head of its opening on each lintel (and tie band) candidate of the plan. Returns {"at_door": n, "at_common_head": n, "none": n}."""
  common = common_head(door_heads(openings))
  stats = {"at_door": 0, "at_common_head": 0, "none": 0, "common_head_mm": common}
  
  for c in candidates:
    f = c.facts
    if c.category == "LINTEL" and f.get("opening_kind") == "DOOR" and _sane((f.get("opening_size_mm") or [None, None])[1]) is not None:
      f["head_mm"], f["head_basis"] = round(float(f["opening_size_mm"][1]), 1), DOOR_HEIGHT
      c.notes.append(C.note("LINTEL_HEAD_AT_DOOR", head_mm=f["head_mm"]))
      stats["at_door"] += 1
    elif common is not None:
      f["head_mm"], f["head_basis"] = common, COMMON_DOOR_HEAD
      c.notes.append(C.note("LINTEL_HEAD_AT_COMMON_DOOR_HEAD", head_mm=common))
      stats["at_common_head"] += 1
    else:
      stats["none"] += 1
  return stats
