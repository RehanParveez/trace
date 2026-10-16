from __future__ import annotations
import math
import re
from app.modules.drawings_boq.takeoff.prep.details import norm_mark

MARK = re.compile(r"^(PB|RB|TB|CB)\d{1,2}$")
KIND_OF_PREFIX = {"PB": "PLINTH", "RB": "ROOF", "TB": "TIE", "CB": "TIE"}
REACH_MM = 1500.0
AMBIGUOUS_RATIO = 1.25

def _segments(points: list) -> list:
  pts = [(float(p[0]), float(p[1])) for p in points or []]
  return list(zip(pts, pts[1:])) if len(pts) >= 2 else []

def _distance(segments: list, q: tuple) -> float | None:
  best = None
  for a, b in segments:
    vx, vy = b[0] - a[0], b[1] - a[1]
    ln2 = vx * vx + vy * vy
    s = 0.0 if ln2 <= 0 else max(0.0, min(1.0, ((q[0] - a[0]) * vx + (q[1] - a[1]) * vy) / ln2))
    d = math.hypot(q[0] - (a[0] + s * vx), q[1] - (a[1] + s * vy))
    best = d if best is None or d < best else best
  return best

def kind_of(mark: str) -> str | None:
  m = MARK.match(norm_mark(mark))
  return KIND_OF_PREFIX[m.group(1)] if m else None

def mark_words(words: list, sections: list) -> list:
  """[(mark, kind, x, y)]: the words of the plan that are the mark of a beam section read from the sheet. A word that names a section nobody read is left out."""
  known = {(s.get("mark"), s.get("kind")) for s in sections or [] if not s.get("disagree")}
  out = []
  for w in words or []:
    mark = norm_mark(getattr(w, "text", ""))
    kind = kind_of(mark)
    if kind is not None and (mark, kind) in known:
      out.append((mark, kind, float(w.cx), float(w.cy)))
  return out

def assign(walls: list, marks: list, mm_per_pt: float) -> dict:
  """Put on each brick wall the mark of each kind of beam that stands nearest to it, as facts["beam_marks"] = {kind: mark}. Returns the counts."""
  stats = {"marks": len(marks), "walls_marked": 0, "ambiguous": 0}
  if not marks or not mm_per_pt or mm_per_pt <= 0:
    return stats
  for w in walls:
    f = w.facts or {}
    if w.category != "WALL" or f.get("construction") == "RCC" or f.get("enclosure") == "TANK":
      continue
    segs = _segments((w.geometry or {}).get("points"))
    if not segs:
      continue
  
    marked = False
    for kind in sorted({k for _, k, _, _ in marks}):
      near = sorted((d * mm_per_pt, mark) for mark, k, x, y in marks if k == kind for d in [_distance(segs, (x, y))] if d is not None)
      near = [n for n in near if n[0] <= REACH_MM]
      if not near:
        continue
      other = next((n for n in near if n[1] != near[0][1]), None)
      if other is not None and other[0] <= near[0][0] * AMBIGUOUS_RATIO:
        stats["ambiguous"] += 1
        continue
      f.setdefault("beam_marks", {})[kind] = near[0][1]
      marked = True
    stats["walls_marked"] += 1 if marked else 0
    w.facts = f
  return stats

def mark_of(wall, kind: str) -> str | None:
  return ((wall.facts or {}).get("beam_marks") or {}).get(kind)
