from __future__ import annotations
import math
from array import array

PARALLEL_TOL_DEG = 1.5
EPS = 1e-9

def _seg_dist(px, py, x1, y1, x2, y2):
  dx, dy = x2 - x1, y2 - y1
  l2 = dx * dx + dy * dy
  if l2 < EPS:
    return math.hypot(px - x1, py - y1), x1, y1, 0.0
  t = ((px - x1) * dx + (py - y1) * dy) / l2
  t = 0.0 if t < 0 else 1.0 if t > 1 else t
  cx, cy = x1 + t * dx, y1 + t * dy
  return math.hypot(px - cx, py - cy), cx, cy, t

def _intersect(a, b):
  x1, y1, x2, y2 = a
  x3, y3, x4, y4 = b
  d = (x2 - x1) * (y4 - y3) - (y2 - y1) * (x4 - x3)
  if abs(d) < EPS:
    return None
  t = ((x3 - x1) * (y4 - y3) - (y3 - y1) * (x4 - x3)) / d
  u = ((x3 - x1) * (y2 - y1) - (y3 - y1) * (x2 - x1)) / d
  tol = 1e-6
  if -tol <= t <= 1 + tol and -tol <= u <= 1 + tol:
    return x1 + t * (x2 - x1), y1 + t * (y2 - y1)
  return None

def point_in_ring(x: float, y: float, pts) -> bool:
  inside = False
  n = len(pts)
  j = n - 1
  for i in range(n):
    xi, yi = pts[i]
    xj, yj = pts[j]
    if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or EPS) + xi:
      inside = not inside
    j = i
  return inside

class VectorIndex:

  def __init__(self, segs: array, kinds: array, rings: list, words: list, bbox: tuple):
    self.segs = segs
    self.kinds = kinds
    self.rings = rings
    self.words = words
    self.bbox = bbox
    self.n = len(kinds)
    w = max(bbox[2] - bbox[0], 1.0)
    h = max(bbox[3] - bbox[1], 1.0)
    target = max(self.n, 1) / 18.0
    cell = math.sqrt(w * h / max(target, 1.0))
    self.cell = min(max(cell, 6.0), 250.0)
    self._grid: dict = {}
    self._build()
    self._ring_order = sorted(range(len(rings)), key=lambda i: rings[i].area)

  def seg(self, i: int):
    s = self.segs
    k = i * 5
    return s[k], s[k + 1], s[k + 2], s[k + 3]

  def _cells_of(self, x1, y1, x2, y2):
    c = self.cell
    ax, ay = int(math.floor(x1 / c)), int(math.floor(y1 / c))
    bx, by = int(math.floor(x2 / c)), int(math.floor(y2 / c))
    if ax == bx and ay == by:
      return ((ax, ay),)
    if abs(bx - ax) <= 1 and abs(by - ay) <= 1:
      return {(ax, ay), (bx, by), (ax, by), (bx, ay)}
    steps = int(max(abs(x2 - x1), abs(y2 - y1)) / (c * 0.5)) + 2
    out = set()
    for k in range(steps + 1):
      t = k / steps
      out.add((int(math.floor((x1 + (x2 - x1) * t) / c)), int(math.floor((y1 + (y2 - y1) * t) / c))))
    return out

  def _build(self) -> None:
    g = self._grid
    for i in range(self.n):
      x1, y1, x2, y2 = self.seg(i)
      for key in self._cells_of(x1, y1, x2, y2):
        g.setdefault(key, []).append(i)

  def _candidates(self, x0, y0, x1, y1) -> list:
    c = self.cell
    seen = set()
    out = []
    g = self._grid
    for ix in range(int(math.floor(x0 / c)), int(math.floor(x1 / c)) + 1):
      for iy in range(int(math.floor(y0 / c)), int(math.floor(y1 / c)) + 1):
        for i in g.get((ix, iy), ()):
          if i not in seen:
            seen.add(i)
            out.append(i)
    return out

  def window(self, x0, y0, x1, y1, max_segments: int = 20000, include_curves: bool = True):
    cand = []
    for i in self._candidates(x0, y0, x1, y1):
      a, b, c, d = self.seg(i)
      if max(a, c) < x0 or min(a, c) > x1 or max(b, d) < y0 or min(b, d) > y1:
        continue
      if not include_curves and self.kinds[i]:
        continue
      cand.append(i)
    total = len(cand)
    truncated = total > max_segments
    if truncated:
      cand.sort(key=lambda i: -math.hypot(self.segs[i * 5 + 2] - self.segs[i * 5], self.segs[i * 5 + 3] - self.segs[i * 5 + 1]))
      cand = sorted(cand[:max_segments])
    else:
      cand.sort()
    return [(*self.seg(i), int(self.kinds[i])) for i in cand], total, truncated

  def nearest(self, x: float, y: float, radius: float, want: tuple = ("ENDPOINT", "INTERSECTION", "MIDPOINT", "EDGE")):
    want = want or ("ENDPOINT", "INTERSECTION", "MIDPOINT", "EDGE")
    near = []
    for i in self._candidates(x - radius, y - radius, x + radius, y + radius):
      x1, y1, x2, y2 = self.seg(i)
      d, cx, cy, t = _seg_dist(x, y, x1, y1, x2, y2)
      if d <= radius:
        near.append((d, i, cx, cy))
    if not near:
      return None
    near.sort()
    kind_of = self.kinds
    
    if "ENDPOINT" in want:
      best = None
      for d, i, _, _ in near:
        x1, y1, x2, y2 = self.seg(i)
        for ex, ey in ((x1, y1), (x2, y2)):
          de = math.hypot(x - ex, y - ey)
          if de <= radius and (best is None or de < best[0]):
            best = (de, ex, ey, i)
      if best is not None:
        return {"x": best[1], "y": best[2], "kind": "ENDPOINT", "distance": best[0], "segment": best[3]}
    
    if "INTERSECTION" in want and len(near) >= 2:
      best = None
      pool = near[:14]
      for a in range(len(pool)):
        for b in range(a + 1, len(pool)):
          p = _intersect(self.seg(pool[a][1]), self.seg(pool[b][1]))
          if p is not None:
            de = math.hypot(x - p[0], y - p[1])
            if de <= radius and (best is None or de < best[0]):
              best = (de, p[0], p[1], pool[a][1])
      if best is not None:
        return {"x": best[1], "y": best[2], "kind": "INTERSECTION", "distance": best[0], "segment": best[3]}
    
    if "MIDPOINT" in want:
      best = None
      for d, i, _, _ in near:
        x1, y1, x2, y2 = self.seg(i)
        if math.hypot(x2 - x1, y2 - y1) < 2.0 or kind_of[i]:
          continue
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        de = math.hypot(x - mx, y - my)
        if de <= radius and (best is None or de < best[0]):
          best = (de, mx, my, i)
      if best is not None:
        return {"x": best[1], "y": best[2], "kind": "MIDPOINT", "distance": best[0], "segment": best[3]}
    if "EDGE" in want:
      d, i, cx, cy = near[0]
      return {"x": cx, "y": cy, "kind": "EDGE", "distance": d, "segment": i}
    return None

  def on_geometry(self, x: float, y: float, tol: float) -> bool:
    for i in self._candidates(x - tol, y - tol, x + tol, y + tol):
      x1, y1, x2, y2 = self.seg(i)
      if _seg_dist(x, y, x1, y1, x2, y2)[0] <= tol:
        return True
    return False

  def run_of(self, i: int, gap: float = 0.6, max_steps: int = 400) -> tuple:

    x1, y1, x2, y2 = self.seg(i)
    length = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / length, (y2 - y1) / length
    lo, hi = (x1, y1), (x2, y2)
    s_lo, s_hi = 0.0, length
    origin = (x1, y1)
    changed = True
    steps = 0
    while changed and steps < max_steps:
      changed = False
      steps += 1
      
      for end in (0, 1):
        px, py = (hi if end else lo)
        for j in self._candidates(px - gap, py - gap, px + gap, py + gap):
          if self.kinds[j]:
            continue
          a, b, c, d = self.seg(j)
          l2 = math.hypot(c - a, d - b)
          if l2 < EPS:
            continue
          vx, vy = (c - a) / l2, (d - b) / l2
          if abs(ux * vy - uy * vx) > math.sin(math.radians(0.6)):
            continue
          for qx, qy, rx, ry in ((a, b, c, d), (c, d, a, b)):
            if math.hypot(qx - px, qy - py) <= gap:
              s_far = (rx - origin[0]) * ux + (ry - origin[1]) * uy
              perp = abs(-(rx - origin[0]) * uy + (ry - origin[1]) * ux)
              if perp > 0.35:
                continue
              if end and s_far > s_hi + 1e-6:
                s_hi, hi, changed = s_far, (rx, ry), True
              elif not end and s_far < s_lo - 1e-6:
                s_lo, lo, changed = s_far, (rx, ry), True
    return lo, hi

  def wall_at(self, x: float, y: float, mm_per_pt: float, radius: float = 3.0, t_min_mm: float = 60.0, t_max_mm: float = 700.0):

    hit = self.nearest(x, y, radius, want=("EDGE",))
    if hit is None:
      return None
    i0 = hit["segment"]
    if self.kinds[i0]:
      return None
    x1, y1, x2, y2 = self.seg(i0)
    l0 = math.hypot(x2 - x1, y2 - y1)
    if l0 < 4.0:
      return None
    lo, hi = self.run_of(i0)
    ux, uy = hi[0] - lo[0], hi[1] - lo[1]
    run_len = math.hypot(ux, uy)
    ux, uy = ux / run_len, uy / run_len
    nx, ny = -uy, ux
    t_min, t_max = t_min_mm / mm_per_pt, t_max_mm / mm_per_pt
    margin = t_max + 2
    groups: dict = {}
    sin_tol = math.sin(math.radians(PARALLEL_TOL_DEG))
    for j in self._candidates(min(lo[0], hi[0]) - margin, min(lo[1], hi[1]) - margin, max(lo[0], hi[0]) + margin, max(lo[1], hi[1]) + margin):
      if j == i0 or self.kinds[j]:
        continue
    
      a, b, c, d = self.seg(j)
      lj = math.hypot(c - a, d - b)
      if lj < 2.0:
        continue
      vx, vy = (c - a) / lj, (d - b) / lj
      if abs(ux * vy - uy * vx) > sin_tol:
        continue
      da = (a - lo[0]) * nx + (b - lo[1]) * ny
      dc = (c - lo[0]) * nx + (d - lo[1]) * ny
      if abs(da - dc) > 0.4:
        continue
      delta = (da + dc) / 2
      if not (t_min <= abs(delta) <= t_max):
        continue
    
      s1 = (a - lo[0]) * ux + (b - lo[1]) * uy
      s2 = (c - lo[0]) * ux + (d - lo[1]) * uy
      key = (1 if delta > 0 else -1, round(abs(delta) / 0.4))
      groups.setdefault(key, []).append((min(s1, s2), max(s1, s2), delta))
    best = None
    for key, spans in groups.items():
      spans.sort()
      covered = 0.0
      cur_lo, cur_hi = spans[0][0], spans[0][1]
      for a, b, _ in spans[1:]:
        if a <= cur_hi + 0.6:
          cur_hi = max(cur_hi, b)
          
        else:
          covered += max(0.0, min(cur_hi, run_len) - max(cur_lo, 0.0))
          cur_lo, cur_hi = a, b
      covered += max(0.0, min(cur_hi, run_len) - max(cur_lo, 0.0))
      overlap = covered / run_len
      delta = sum(s[2] for s in spans) / len(spans)
      score = overlap - 0.0005 * abs(delta)
      if overlap >= 0.35 and (best is None or score > best[0]):
        best = (score, overlap, delta, key)
    if best is None:
      return {"run": [lo, hi], "partner": None}
    _, overlap, delta, key = best
    half = delta / 2
    c1 = (lo[0] + nx * half, lo[1] + ny * half)
    c2 = (hi[0] + nx * half, hi[1] + ny * half)
    return {"run": [lo, hi], "partner": {"offset_pt": delta, "overlap": overlap, "thickness_mm": abs(delta) * mm_per_pt},
      "centreline": [c1, c2]}


  def small_rings_near(self, x: float, y: float, reach: float) -> list:
    if not hasattr(self, "_small_grid"):
      g: dict = {}
      for r in self.rings:
        if max(r.bbox[2] - r.bbox[0], r.bbox[3] - r.bbox[1]) <= 16.0:
          g.setdefault((int(r.bbox[0] // 8), int(r.bbox[1] // 8)), []).append(r)
      self._small_grid = g
    out = []
    
    for ix in range(int((x - reach) // 8), int((x + reach) // 8) + 1):
      for iy in range(int((y - reach) // 8), int((y + reach) // 8) + 1):
        out.extend(self._small_grid.get((ix, iy), ()))
    return out

  def region_at(self, x: float, y: float, min_area: float = 4.0, max_area_fraction: float = 0.5):
    page_area = max((self.bbox[2] - self.bbox[0]) * (self.bbox[3] - self.bbox[1]), 1.0)
    for idx in self._ring_order:
      r = self.rings[idx]
      if r.area < min_area:
        continue
      if r.area > max_area_fraction * page_area:
        break
    
      bx0, by0, bx1, by1 = r.bbox
      if x < bx0 or x > bx1 or y < by0 or y > by1:
        continue
      if point_in_ring(x, y, r.pts):
        holes = []
        for j in self._ring_order:
          o = self.rings[j]
          if o.area >= r.area:
            break
          if o.area < min_area or j == idx:
            continue
          ox0, oy0, ox1, oy1 = o.bbox
          if ox0 >= bx0 and oy0 >= by0 and ox1 <= bx1 and oy1 <= by1 and point_in_ring((ox0 + ox1) / 2, (oy0 + oy1) / 2, r.pts):
            holes.append(j)
            if len(holes) >= 60:
              break
        return idx, holes
    return None
