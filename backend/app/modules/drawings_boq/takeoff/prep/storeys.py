from __future__ import annotations
import re
from collections import Counter
from app.modules.drawings_boq.takeoff.prep import facts as F
from statistics import median

MIN_CLEAR_MM = 2438.4    
MAX_CLEAR_MM = 4500.0
SLOT_TOL_PT = 12.0         
MIN_SLOT_COUNT = 2         
_FEET_INCH = re.compile(r"^(?P<ft>\d{1,2})\s*'\s*-?\s*(?P<in>\d{1,2})?(?:\s+(?P<n>\d)/(?P<d>\d))?\s*(?:\"|″|”|'')?$")

def feet_inch_mm(text: str) -> float | None:
  """A bare feet-and-inches dimension such as 10'-0", 9'-0" or 7'-10½", in millimetres. Anything else on the text makes it not a bare dimension."""
  m = _FEET_INCH.match(F._fix(text or ""))
  if not m:
    return None
  inch = int(m.group("in") or 0)
  if m.group("n"):
    if int(m.group("d")) == 0:
      return None
    inch += int(m.group("n")) / int(m.group("d"))
  return round(int(m.group("ft")) * F.MM_FOOT + inch * F.MM_INCH, 1)

def _snap(angle: float) -> int | None:
  a = angle % 360.0
  nearest = round(a / 90.0) % 4 * 90
  return nearest if abs(((a + 45.0) % 90.0) - 45.0) <= 6.0 else None

AXES = ((1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0))
BELOW_GROUND_MM = 4600.0   
_SECTION_TITLE = re.compile(r"\bSECTIONS?\s+(?:AT\s+)?['\"“”‘’]?[A-Z]\s*-\s*[A-Z]\b", re.I)

def _along(w, axis: tuple) -> float:
  return w.cx * axis[0] + w.cy * axis[1]

def _up_axis(marks: dict) -> tuple | None:
  """The direction on the sheet in which the level marks rise: the one axis along which three or more different levels climb steadily."""
  pts = sorted((mm, ws) for mm, ws in marks.items())
  if len(pts) < 3:
    return None
  for axis in AXES:
    pos = [median(_along(w, axis) for w in ws) for _, ws in pts]
    if all(b - a > 1.0 for a, b in zip(pos, pos[1:])):
      return axis
  return None

def read_storeys(words: list, lines: list) -> dict | None:
  """{"clusters": [{"clear_mm", "count", "agree", "below_ground", "between_mm", "implied_slab_mm"}, ...] lowest storey first, "consistent"} or None when
  the sheet shows no building section with level marks and storey dimensions."""
  if not words or not any(_SECTION_TITLE.search(getattr(ln, "text", "") or "") for ln in lines or []):
    return None
  main = Counter(a for a in (_snap(w.angle) for w in words) if a is not None).most_common(1)
  if not main:
    return None

  vertical = {(main[0][0] + 90) % 360, (main[0][0] + 270) % 360}
  marks: dict = {}
  for w in words:
    mm = F.level_mark_mm(w.text)
    if mm is not None:
      marks.setdefault(mm, []).append(w)
  axis = _up_axis(marks)
  if axis is None:
    return None

  levels = sorted((median(_along(w, axis) for w in ws), mm) for mm, ws in marks.items())
  span_mm = levels[-1][1] - levels[0][1]
  if span_mm <= 0:
    return None
  pt_per_mm = (levels[-1][0] - levels[0][0]) / span_mm
  floor_up, ceil_up = levels[0][0] - BELOW_GROUND_MM * pt_per_mm, levels[-1][0] + 300.0 * pt_per_mm
  slots: list = []
  found = []
  
  for w in words:
    if _snap(w.angle) not in vertical:
      continue
    mm = feet_inch_mm(w.text)
    if mm is None or not MIN_CLEAR_MM <= mm <= MAX_CLEAR_MM:
      continue
    up = _along(w, axis)
    if floor_up <= up <= ceil_up:
      found.append((up, mm))
  for up, mm in sorted(found):
    if slots and up - slots[-1]["ups"][-1] <= SLOT_TOL_PT:
      slots[-1]["ups"].append(up)
      slots[-1]["mms"].append(mm)
    else:
      slots.append({"ups": [up], "mms": [mm]})
  clusters, used = [], []
  
  for s in slots:
    if len(s["mms"]) < MIN_SLOT_COUNT:
      continue
    group, n = Counter(round(m / 5.0) * 5.0 for m in s["mms"]).most_common(1)[0]
    top = median(m for m in s["mms"] if round(m / 5.0) * 5.0 == group)
    up = sum(s["ups"]) / len(s["ups"])
    lo = max((lv for lv in levels if lv[0] <= up), default=None, key=lambda lv: lv[0])
    hi = min((lv for lv in levels if lv[0] > up), default=None, key=lambda lv: lv[0])
    between = [lo[1], hi[1]] if lo and hi else None
    
    slab = round(between[1] - between[0] - top, 1) if between else None
    clusters.append({"clear_mm": round(float(top), 1), "count": len(s["mms"]), "agree": round(n / len(s["mms"]), 2), "below_ground": lo is None,
      "between_mm": between, "implied_slab_mm": slab})
    used.append(between[0] if between else None)
  if not clusters:
    return None
  filled = [u for u in used if u is not None]
  consistent = len(filled) == len(set(filled)) and all(c["agree"] >= 0.75 for c in clusters)
  return {"clusters": clusters, "consistent": consistent}

FLOOR_ORDER = F.FLOOR_ORDER

def storey_heights(floor_keys: list, storeys: dict | None) -> dict:
  """The clear height of each floor, taken from the storeys printed on the sections. A floor gets a height only when the number of storeys on the
  sections equals the number of floors the drawing shows (the roof floor is the storey above the roof slab, when there is one); otherwise nothing
  is offered, because the heights could be matched to the wrong floors."""
  if not storeys or not storeys.get("consistent"):
    return {}
  clusters = storeys.get("clusters") or []
  keys = [k for k in FLOOR_ORDER if k in (floor_keys or [])]
  if len(clusters) != len(keys):
    keys = [k for k in keys if k != "ROOF"]
    if len(clusters) != len(keys):
      return {}
  
  out = {}
  for key, c in zip(keys, clusters):
    between = c.get("between_mm")
    out[key] = {"clear_mm": c["clear_mm"], "floor_to_floor_mm": round(between[1] - between[0], 1) if between else None, "basis": "SECTION",
      "count": c["count"], "level_mm": between[0] if between else None}
  return out
