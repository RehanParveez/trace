from __future__ import annotations
import math
import re
import statistics
from app.modules.drawings_boq.takeoff.extract import slab_panels as SPN, rooms as R

MIN_STRINGS = 3
MIN_PANELS = 3
DETAIL = re.compile(r"\b(?:DETAILS?|SECTIONS?|TANKS?|SEPTIC)\b", re.I)

def _reach(points: list) -> float:
  if len(points) < 2:
    return 0.0
  near = [min(math.hypot(a[0] - b[0], a[1] - b[1]) for j, b in enumerate(points) if j != i) for i, a in enumerate(points)]
  return float(statistics.median(near))

def read(words: list, lines: list, hint: str | None) -> dict | None:
  if any(DETAIL.search(ln.text) for ln in lines):
    return None
  strings = [(w.cx, w.cy, SPN._string_of(w)) for w in words]
  strings = [(x, y, s) for x, y, s in strings if s]
  if len(strings) < MIN_STRINGS:
    return None

  reach = _reach([(x, y) for x, y, _ in strings])
  x0, x1 = min(x for x, _, _ in strings) - reach, max(x for x, _, _ in strings) + reach
  y0, y1 = min(y for _, y, _ in strings) - reach, max(y for _, y, _ in strings) + reach
  _, sizes = R.labels(lines, hint)
  inside = [s for s in sizes if x0 <= s[2] <= x1 and y0 <= s[3] <= y1]
  if len(inside) < MIN_PANELS:
    return None

  groups: dict = {}
  for text, (a, b), x, y in inside:
    long_, short = (float(a), float(b)) if a >= b else (float(b), float(a))
    g = groups.setdefault((round(long_), round(short)), {"length_mm": long_, "width_mm": short, "text": text, "count": 0, "points": []})
    g["count"] += 1
    g["points"].append([round(x, 3), round(y, 3)])
  panels = sorted(groups.values(), key=lambda g: (-g["length_mm"] * g["width_mm"], g["text"]))

  tally: dict = {}
  for _, _, s in strings:
    tally[s["text"]] = tally.get(s["text"], 0) + 1
  return {"panels": panels, "labels": len(inside), "labels_outside": len(sizes) - len(inside), "strings": len(strings),
    "string_text": [{"text": t, "n": n} for t, n in sorted(tally.items(), key=lambda kv: (-kv[1], kv[0]))],
    "area_m2": round(sum(g["length_mm"] * g["width_mm"] * g["count"] for g in panels) / 1e6, 3)}
