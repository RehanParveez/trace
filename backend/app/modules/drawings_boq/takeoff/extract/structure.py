from __future__ import annotations
import math
import re
from app.modules.drawings_boq.takeoff.prep.texts import build_lines
from app.modules.drawings_boq.takeoff.extract import members as M
from app.modules.drawings_boq.takeoff.extract import config as C

SQUARE_MIN_MM = 150.0
SQUARE_MAX_MM = 1100.0
SQUARE_ASPECT = 2.2
SQUARE_FILL_MIN = 0.4          
FOOTING_CAPTION = re.compile(r"\bSECTION\s+OF\s+FOOTINGS?\b|\bFOOTINGS?\s+(?:SECTION|DETAIL)S?\b", re.I)
SIZE_IN_LINE = re.compile(r"\d+\s*['’′]\s*-?\s*\d*\s*[\"”″]?\s*[xX×]\s*\d+\s*['’′]\s*-?\s*\d*\s*[\"”″]?")
FOOTING_DETAIL_REACH_PT = 45.0
STAIR_FOOTING = re.compile(r"\bSTAIR\s+FOOTINGS?\b", re.I)

def square_shapes(rings: list, mm_per_pt: float) -> list[dict]:
  """Solid black squares and rectangles (column symbols): {cx, cy, a, b, kind, fill} like members.member_shapes, a <= b in mm."""
  seen: set = set()
  out = []
  
  for r in rings:
    if not r.fill or r.curved or len(r.pts) > 8:
      continue
    x0, y0, x1, y1 = r.bbox
    w, h = (x1 - x0) * mm_per_pt, (y1 - y0) * mm_per_pt
    a, b = (w, h) if w <= h else (h, w)
    if a < SQUARE_MIN_MM or b > SQUARE_MAX_MM or b / max(a, 1e-9) > SQUARE_ASPECT:
      continue
    if r.area < SQUARE_FILL_MIN * (x1 - x0) * (y1 - y0):
      continue
    key = (round(x0, 0), round(y0, 0), round(x1, 0), round(y1, 0))
    if key in seen:
      continue
    seen.add(key)
    out.append({"cx": (x0 + x1) / 2.0, "cy": (y0 + y1) / 2.0, "a": a, "b": b, "kind": "RECT", "fill": True})
  return out

DUPLICATE_REACH = 0.5          

def dedupe_solid(shapes: list, mm_per_pt: float) -> list:
  """A column drawn twice (two overlapping solid squares a few points apart, or the same square seen as a rectangle and as two triangles) is one
  column. Solid shapes only; outlines (doors, beams) are never merged. The larger shape is kept, order is preserved."""
  solid = sorted((i for i, s in enumerate(shapes) if s.get("fill")), key=lambda i: -(shapes[i]["a"] * shapes[i]["b"]))
  drop: set = set()
  kept: list = []
  for i in solid:
    s = shapes[i]
    if any(math.hypot(s["cx"] - shapes[j]["cx"], s["cy"] - shapes[j]["cy"]) * mm_per_pt < DUPLICATE_REACH * min(s["a"], shapes[j]["a"]) for j in kept):
      drop.add(i)
    else:
      kept.append(i)
  return [s for i, s in enumerate(shapes) if i not in drop]

INCH_MM = 25.4
INCH_SNAP_TOL = 0.03

def snap_inch(a: float) -> float:
  """A size on an imperial drawing is a whole number of inches (a 9 inch column drawn at 225 mm is 228.6 mm; 915 mm read from 3'-0" is 914.4 mm)."""
  n = round(a / INCH_MM)
  return round(n * INCH_MM, 1) if n >= 1 and abs(a - n * INCH_MM) <= INCH_SNAP_TOL * n * INCH_MM else a

def footing_sizes(words: list, hint: str | None, imperial: bool = False) -> list[tuple]:
  """The footing sizes printed under the footing section details ("SECTION OF FOOTING (3'-0"X3'-0")"), one per detail, in mm."""
  lines = build_lines(words)
  caps = []
  for ln in lines:
    if FOOTING_CAPTION.search(ln.text):
      ws = [w for _, _, w in ln.spans]
      caps.append((sum(w.cx for w in ws) / len(ws), sum(w.cy for w in ws) / len(ws)))
  out = []
  
  for ln in lines:
    m = SIZE_IN_LINE.search(ln.text)
    if not m or not caps:
      continue
    ws = [w for _, _, w in ln.spans]
    cx, cy = sum(w.cx for w in ws) / len(ws), sum(w.cy for w in ws) / len(ws)
    if min(math.hypot(cx - x, cy - y) for x, y in caps) > FOOTING_DETAIL_REACH_PT:
      continue
    size = M.parse_size(m.group(0), hint)
    if size is not None and M._plausible("FOOTING", size):
      a, b = (snap_inch(size[0]), snap_inch(size[1])) if imperial else size
      out.append((min(a, b), max(a, b)))
  return out

def assign_footing_sizes(groups: list, sizes: list) -> dict:
  """Which footing mark has which printed size. The details do not say, so marks and sizes are paired in order (F1 the smallest) only when
  there are as many distinct sizes as marks, and the pairing is flagged as assumed. One mark and one size need no assumption."""
  marks = sorted({g["tag"] for g in groups if g["category"] == "FOOTING"}, key=_mark_order)
  distinct = sorted(set(sizes), key=lambda s: (s[0] * s[1], s))
  if not marks or not distinct:
    return {"assigned": {}, "assumed": False, "options": [list(s) for s in distinct]}
  if len(marks) == 1 and len(distinct) == 1:
    return {"assigned": {marks[0]: distinct[0]}, "assumed": False, "options": [list(distinct[0])]}
  if len(marks) == len(distinct):
    return {"assigned": dict(zip(marks, distinct)), "assumed": True, "options": [list(s) for s in distinct]}
  return {"assigned": {}, "assumed": False, "options": [list(s) for s in distinct]}

def _mark_order(tag: str):
  m = re.search(r"(\d+)", tag)
  return (re.sub(r"\d+", "", tag), int(m.group(1)) if m else 0)

def stair_footings(words: list) -> list:
  """The words that label a stair footing; it has a name but no mark."""
  return [w for w in words if STAIR_FOOTING.search(w.text)] or _joined(words, STAIR_FOOTING)

def _joined(words: list, pat) -> list:
  out = []
  for ln in build_lines(words):
    m = pat.search(ln.text)
    if m:
      hit = [w for a, b, w in ln.spans if b > m.start() and a < m.end()]
      if hit:
        out.append(hit[0])
  return out

def column_details(meta: dict | None) -> dict:
  """{mark: {"size_mm": (a, b), "sizes_in": [[a, b]], "disagree": bool}} from the column details read on the sheet (prep meta "details").
  A mark whose details give different sizes is marked as disagreeing and carries no size."""
  by: dict = {}
  for d in (meta or {}).get("details") or []:
    if d.get("read") not in ("OCR", "OCR_SQUARE") or not d.get("w_in") or not d.get("h_in"):
      continue
    by.setdefault(d["mark"], set()).add((min(d["w_in"], d["h_in"]), max(d["w_in"], d["h_in"])))
  out = {}
  for mark, sizes in by.items():
    ordered = sorted(sizes)
    rec = {"sizes_in": [list(s) for s in ordered], "disagree": len(ordered) > 1}
    if not rec["disagree"]:
      a, b = ordered[0]
      rec["size_mm"] = (round(a * INCH_MM, 1), round(b * INCH_MM, 1))
    out[mark] = rec
  return out
