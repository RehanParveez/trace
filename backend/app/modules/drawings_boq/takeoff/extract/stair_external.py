from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.extract import config as C

_EXT = re.compile(r"(?<![A-Z])(?:EXT\.?|EXTERNAL|EXTERIOR|OUTSIDE)(?![A-Z])", re.I)
_STAIR = re.compile(r"STAIR|(?<![A-Z])STEPS?(?![A-Z])", re.I)

def labels(lines: list) -> list:
  out = []
  for ln in lines:
    text = (getattr(ln, "text", "") or "").strip()
    if not text or len(text) > 40 or not _EXT.search(text) or not _STAIR.search(text):
      continue
    ws = [w for _, _, w in ln.spans]
    if not ws:
      continue
    out.append({"text": text, "x": sum(w.cx for w in ws) / len(ws), "y": sum(w.cy for w in ws) / len(ws)})
  return out

def outline(walls: list, mm_per_pt: float) -> tuple | None:
  pts = []
  n = 0
  for w in walls:
    f = w.facts or {}
    
    t = f.get("thickness_used_mm") or f.get("thickness_mm")
    if t is None or float(t) < C.OUTER_CORE_MIN_MM:
      continue
    got = [(float(p[0]), float(p[1])) for p in (w.geometry or {}).get("points") or []]
    if got:
      n += 1
      pts += got
  if n < C.STAIR_EXTERNAL_MIN_WALLS:
    return None
  tol = C.OUTER_TOL_MM / mm_per_pt
  return min(p[0] for p in pts) - tol, min(p[1] for p in pts) - tol, max(p[0] for p in pts) + tol, max(p[1] for p in pts) + tol

def _gap(box, x: float, y: float) -> float:
  x0, y0, x1, y1 = box
  return max(x0 - x, 0.0, x - x1) ** 2 + max(y0 - y, 0.0, y - y1) ** 2

def _outside(box, frame: tuple) -> bool:
  x0, y0, x1, y1 = (float(v) for v in box)
  return x1 < frame[0] or x0 > frame[2] or y1 < frame[1] or y0 > frame[3]

def mark(stairs: list, lines: list, walls: list, mm_per_pt: float | None) -> int:
  if not stairs or not mm_per_pt:
    return 0
  boxed = [c for c in stairs if (c.facts or {}).get("flight_box")]
  reach2 = (C.STAIR_LABEL_REACH_MM / mm_per_pt) ** 2
  named: set = set()
  for lab in labels(lines):
    best, best_d = None, reach2
    for c in boxed:
      d = _gap(c.facts["flight_box"], lab["x"], lab["y"])
      if d <= best_d:
        best, best_d = c, d
    if best is not None:
      named.add(id(best))
      
  frame = outline(walls, mm_per_pt)
  count = 0
  for c in stairs:
    box = (c.facts or {}).get("flight_box")
    by = "LABEL" if id(c) in named else ("OUTLINE" if frame is not None and box and _outside(box, frame) else None)
    if by is None:
      continue
    c.facts = {**(c.facts or {}), "external": True, "external_by": by}
    c.notes.append(C.note("STAIR_EXTERNAL"))
    count += 1
  return count
