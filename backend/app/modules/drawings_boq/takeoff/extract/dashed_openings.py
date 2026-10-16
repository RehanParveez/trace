from __future__ import annotations
import math
import numpy as np
from collections import defaultdict

DASH_MIN_PT = 2.0
DASH_MAX_PT = 25.0
CHAIN_GAP_MAX_PT = 8.0
CHAIN_MIN_DASHES = 5
OPENING_MIN_MM = 1800.0
PAIR_MIN_MM = 90.0
PAIR_MAX_MM = 520.0
OVERLAP_MIN = 0.85
AXIS_TOL_PT = 0.05
LIGHTER_THAN_WALL = 0.95
END_TOUCH_PT = 0.9
END_RUN_MIN_PT = 3.0

def _chains(segs: np.ndarray, kinds: np.ndarray, wall_pen_pt: float) -> list:
  """[(orient, offset, start, end, dashes)]: runs of at least CHAIN_MIN_DASHES short axis-parallel segments in a pen lighter than the walls, on one line."""
  dx, dy = segs[:, 2] - segs[:, 0], segs[:, 3] - segs[:, 1]
  ln = np.hypot(dx, dy)
  ok = (kinds == 0) & (ln >= DASH_MIN_PT) & (ln <= DASH_MAX_PT) & (segs[:, 4] < LIGHTER_THAN_WALL * wall_pen_pt)
  groups: dict = defaultdict(list)
  for s in segs[ok]:
    x0, y0, x1, y1 = (float(v) for v in s[:4])
    if abs(y1 - y0) < AXIS_TOL_PT:
      groups[("H", round(y0, 1))].append((min(x0, x1), max(x0, x1)))
    elif abs(x1 - x0) < AXIS_TOL_PT:
      groups[("V", round(x0, 1))].append((min(y0, y1), max(y0, y1)))
  out = []
  
  for (orient, c), items in groups.items():
    items.sort()
    chain = [items[0]]
    def close():
      if len(chain) >= CHAIN_MIN_DASHES:
        out.append((orient, c, chain[0][0], max(b for _, b in chain), len(chain)))
    for it in items[1:]:
      if it[0] - chain[-1][1] <= CHAIN_GAP_MAX_PT:
        chain.append(it)
      else:
        close()
        chain = [it]
    close()
  return out

def _solid_lines(segs: np.ndarray, kinds: np.ndarray, wall_pen_pt: float) -> dict:
  """{(orient, offset): [(start, end)]}: the axis-parallel segments drawn in the wall pen."""
  out: dict = defaultdict(list)
  heavy = (kinds == 0) & (segs[:, 4] >= LIGHTER_THAN_WALL * wall_pen_pt)
  for s in segs[heavy]:
    x0, y0, x1, y1 = (float(v) for v in s[:4])
    if abs(y1 - y0) < AXIS_TOL_PT and abs(x1 - x0) >= END_RUN_MIN_PT:
      out[("H", round(y0, 1))].append((min(x0, x1), max(x0, x1)))
    elif abs(x1 - x0) < AXIS_TOL_PT and abs(y1 - y0) >= END_RUN_MIN_PT:
      out[("V", round(x0, 1))].append((min(y0, y1), max(y0, y1)))
  return out

def _lines_near(solid: dict, orient: str, c: float) -> list:
  return [v for (o, k), vs in solid.items() if o == orient and abs(k - c) <= 0.15 for v in vs]

def _wall_ends_here(solid: dict, rings: list, orient: str, c1: float, c2: float, e: float, outward: int) -> bool:
  """True when the opening stops against wall: a wall-pen line on one of its two faces ends at e and runs on away from the opening, or a filled shape
  (a column) covers the end of the opening."""
  for c in (c1, c2):
    for lo, hi in _lines_near(solid, orient, c):
      if outward < 0 and abs(hi - e) <= END_TOUCH_PT and hi - lo >= END_RUN_MIN_PT:
        return True
      if outward > 0 and abs(lo - e) <= END_TOUCH_PT and hi - lo >= END_RUN_MIN_PT:
        return True
  mid = (c1 + c2) / 2.0
  for (bx0, by0, bx1, by1) in rings:
    x, y = (e, mid) if orient == "H" else (mid, e)
    if bx0 - END_TOUCH_PT <= x <= bx1 + END_TOUCH_PT and by0 - END_TOUCH_PT <= y <= by1 + END_TOUCH_PT:
      return True
  return False

def find(index, mm_per_pt: float, wall_pen_pt: float | None) -> list:
  """The dashed openings of a plan: [{"p0", "p1", "span_mm", "t_mm", "dashes"}] with the centre line of the opening in page points."""
  if not wall_pen_pt or len(index.kinds) == 0:
    return []
  segs = np.frombuffer(index.segs, dtype=np.float32).reshape(-1, 5).astype(np.float64)
  kinds = np.frombuffer(index.kinds, dtype=np.uint8)
  chains = _chains(segs, kinds, float(wall_pen_pt))
  solid = _solid_lines(segs, kinds, float(wall_pen_pt))
  rings = [r.bbox for r in index.rings if r.fill and not r.curved]
  out, used = [], set()
  
  for i, a in enumerate(chains):
    for j in range(i + 1, len(chains)):
      b = chains[j]
      if i in used or j in used or a[0] != b[0]:
        continue
      off_mm = abs(a[1] - b[1]) * mm_per_pt
      if not (PAIR_MIN_MM <= off_mm <= PAIR_MAX_MM):
        continue
      lo, hi = max(a[2], b[2]), min(a[3], b[3])
      shorter = min(a[3] - a[2], b[3] - b[2])
      
      if hi - lo < OVERLAP_MIN * shorter or (hi - lo) * mm_per_pt < OPENING_MIN_MM:
        continue
      if not (_wall_ends_here(solid, rings, a[0], a[1], b[1], lo, -1) and _wall_ends_here(solid, rings, a[0], a[1], b[1], hi, 1)):
        continue
      c = (a[1] + b[1]) / 2.0
      p0, p1 = ((lo, c), (hi, c)) if a[0] == "H" else ((c, lo), (c, hi))
      out.append({"p0": p0, "p1": p1, "span_mm": (hi - lo) * mm_per_pt, "t_mm": off_mm, "dashes": a[4] + b[4]})
      used.update((i, j))
  out.sort(key=lambda o: -o["span_mm"])
  return out
