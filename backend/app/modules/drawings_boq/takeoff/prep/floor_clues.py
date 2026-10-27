from __future__ import annotations
import re

SIZE_STEP_MM = 50
MAX_SIZES = 60
GROUND_WORDS = re.compile(r"\b(?:PORCH|LAWN|DRIVE\s?WAY|DRIVE|CAR\s+PORCH|GARAGE|ENTRANCE\s+LOBBY|MAIN\s+GATE)\b", re.I)
ROOF_WORDS = re.compile(r"\b(?:MUMTY|STAIR\s*TOWER|STAIR\s*HEAD\s*ROOM|HEAD\s*ROOM|WATER\s+TANK|PARAPET)\b", re.I)
BED_WORDS = re.compile(r"\b(?:BED\s*ROOMS?|BEDROOMS?|MASTER\s+BED|DRESSING)\b", re.I)

def _key(a: float, b: float) -> str:
  hi, lo = max(a, b), min(a, b)
  return f"{int(round(hi / SIZE_STEP_MM) * SIZE_STEP_MM)}x{int(round(lo / SIZE_STEP_MM) * SIZE_STEP_MM)}"

def read(lines: list, hint, pairs: list) -> dict:
  from app.modules.drawings_boq.takeoff.extract import rooms as R
  names, sizes = R.labels(lines, hint)
  texts = [ln.text for ln in lines]
  groups = {p.group if getattr(p, "group", -1) >= 0 else id(p) for p in pairs}
  return {"sizes": sorted(_key(a, b) for _t, (a, b), _x, _y in sizes)[:MAX_SIZES], "room_sizes": len(sizes), "dim_pairs": len(groups), "rooms": len(names),
    "ground_words": sum(1 for t in texts if GROUND_WORDS.search(t)), "roof_words": sum(1 for t in texts if ROOF_WORDS.search(t)), "bed_words": sum(1 for t in texts if BED_WORDS.search(t))}
