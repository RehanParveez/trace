from __future__ import annotations
import math
from app.modules.drawings_boq.takeoff.reading_score.labels import clean_points
from app.modules.drawings_boq.takeoff.prep.spatial import point_in_ring

UNCLAIMED = "UNCLAIMED_GEOMETRY"
FILLED_SHAPE, LINE_RUN = "FILLED_SHAPE", "LINE_RUN"
MAX_ITEMS = 150

DEFAULTS = {"cell_pt": 24.0, "margin_pt": 10.0, "min_run_pt": 60.0, "min_segment_pt": 6.0, "min_area_pt2": 36.0, "max_area_share": 0.4}

class _Claims:
  def __init__(self, cell: float):
    self.cell = cell
    self.cells: set = set()

  def _key(self, x: float, y: float) -> tuple:
    return (int(math.floor(x / self.cell)), int(math.floor(y / self.cell)))

  def around(self, x: float, y: float, reach: float) -> None:
    a, b = self._key(x - reach, y - reach), self._key(x + reach, y + reach)
    for ix in range(a[0], b[0] + 1):
      for iy in range(a[1], b[1] + 1):
        self.cells.add((ix, iy))

  def along(self, pts: list, reach: float, closed: bool = False) -> None:
    n = len(pts)
    for i in range(n if closed else n - 1):
      (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
      steps = max(1, int(math.hypot(x1 - x0, y1 - y0) / max(self.cell * 0.5, 1.0)))
      for k in range(steps + 1):
        t = k / steps
        self.around(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, reach)

  def has(self, x: float, y: float) -> bool:
    return self._key(x, y) in self.cells

def claims_of(candidates: list, cell: float, reach: float) -> _Claims:
  c = _Claims(cell)
  for cand in candidates:
    g = getattr(cand, "geometry", None) or {}
    pts = clean_points(g.get("points"))
    outer = clean_points(g.get("outer"))
    if outer:
      c.along(outer, reach, closed=True)
    elif len(pts) >= 2 and str(getattr(cand, "category", "")) in ("WALL", "BEAM", "LINTEL", "SLAB", "STAIR", "ROOM"):
      c.along(pts, reach)
    for x, y in pts:
      c.around(x, y, reach)
  return c

def _inside(boxes: list, x: float, y: float) -> bool:
  return any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for b in boxes)

def unclaimed_geometry(index, candidates: list, plan_boxes: list | None, **kw) -> dict:
  rule = {**DEFAULTS, **{k: v for k, v in kw.items() if k in DEFAULTS and v is not None}}
  max_items = int(kw.get("max_items") or MAX_ITEMS)
  boxes = [list(map(float, b)) for b in (plan_boxes or []) if b and len(b) >= 4]
  whole = not boxes
  if whole:
    boxes = [[float(v) for v in index.bbox]]
  area_total = sum(max(b[2] - b[0], 0.0) * max(b[3] - b[1], 0.0) for b in boxes) or 1.0
  claims = claims_of(candidates, rule["cell_pt"], rule["margin_pt"])
  
  items: list = []
  for r in index.rings:
    if not r.fill or r.area < rule["min_area_pt2"] or r.area > rule["max_area_share"] * area_total:
      continue
    cx, cy = (r.bbox[0] + r.bbox[2]) / 2.0, (r.bbox[1] + r.bbox[3]) / 2.0
    if not _inside(boxes, cx, cy) or claims.has(cx, cy):
      continue
    items.append({"reason": UNCLAIMED, "kind": FILLED_SHAPE, "anchor": [round(cx, 2), round(cy, 2)], "size_pt": round(4.0 * math.sqrt(r.area), 1), "bbox": [round(v, 2) for v in r.bbox]})
    
  runs: dict = {}
  for i in range(index.n):
    if index.kinds[i]:
      continue
    x1, y1, x2, y2 = index.seg(i)
    length = math.hypot(x2 - x1, y2 - y1)
    mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    
    if length < rule["min_segment_pt"] or not _inside(boxes, mx, my) or claims.has(mx, my):
      continue
    key = (int(math.floor(mx / rule["cell_pt"])), int(math.floor(my / rule["cell_pt"])))
    a = runs.setdefault(key, [0.0, 0.0, 0.0, 1e18, 1e18, -1e18, -1e18])
    a[0] += length
    a[1] += mx * length
    a[2] += my * length
    a[3], a[4], a[5], a[6] = min(a[3], x1, x2), min(a[4], y1, y2), max(a[5], x1, x2), max(a[6], y1, y2)
    
  for key, a in sorted(runs.items()):
    if a[0] >= rule["min_run_pt"]:
      items.append({"reason": UNCLAIMED, "kind": LINE_RUN, "anchor": [round(a[1] / a[0], 2), round(a[2] / a[0], 2)], "size_pt": round(a[0], 1),
        "bbox": [round(v, 2) for v in a[3:7]]})
  items.sort(key=lambda t: (-t["size_pt"], t["anchor"][0], t["anchor"][1], t["kind"]))
  return {"items": items[:max_items], "cut": max(0, len(items) - max_items), "whole_sheet": whole,
    "counts": {"filled": sum(1 for t in items if t["kind"] == FILLED_SHAPE), "lines": sum(1 for t in items if t["kind"] == LINE_RUN)}, "rule": rule}
