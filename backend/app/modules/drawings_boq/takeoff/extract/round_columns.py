from __future__ import annotations
import math
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.extract import slab_panels as SPN
from app.modules.drawings_boq.takeoff.extract import slab_plan as SPL

CELL = 1.0
JOIN = 0.3
MIN_SEGS = 8
FIT_TOL = 0.04
MAX_CHAIN = 240
MAX_GAP = math.pi / 3.0

def _curves(index, f: float) -> list:
  limit = C.COLUMN_PIECE_MAX_MM * 0.5
  out = []
  for i in range(index.n):
    if not index.kinds[i]:
      continue
    g = index.seg(i)
    if math.hypot(g[2] - g[0], g[3] - g[1]) * f <= limit:
      out.append(g)
  return out

def _chains(segs: list) -> list:
  parent = list(range(len(segs)))
  def find(x: int) -> int:
    while parent[x] != x:
      parent[x] = parent[parent[x]]
      x = parent[x]
    return x

  grid: dict = {}
  for i, g in enumerate(segs):
    for p in ((g[0], g[1]), (g[2], g[3])):
      grid.setdefault((round(p[0] / CELL), round(p[1] / CELL)), []).append(i)
  for i, g in enumerate(segs):
    for p in ((g[0], g[1]), (g[2], g[3])):
      cx, cy = round(p[0] / CELL), round(p[1] / CELL)
      for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
          for j in grid.get((cx + dx, cy + dy), []):
            if j == i:
              continue
            h = segs[j]
            if min(math.hypot(p[0] - h[0], p[1] - h[1]), math.hypot(p[0] - h[2], p[1] - h[3])) <= JOIN:
              a, b = find(i), find(j)
              if a != b:
                parent[a] = b
                
  comps: dict = {}
  for i in range(len(segs)):
    comps.setdefault(find(i), []).append(i)
  return list(comps.values())

def _centre(a: tuple, b: tuple) -> tuple | None:
  ax, ay, bx, by = (a[0] + a[2]) / 2.0, (a[1] + a[3]) / 2.0, (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0
  ux, uy, vx, vy = a[2] - a[0], a[3] - a[1], b[2] - b[0], b[3] - b[1]
  det = ux * vy - uy * vx

  if abs(det) < 1e-9 * max(1.0, math.hypot(ux, uy) * math.hypot(vx, vy)):
    return None
  c1, c2 = ux * ax + uy * ay, vx * bx + vy * by
  return (c1 * vy - uy * c2) / det, (ux * c2 - c1 * vx) / det

def _fits(segs: list, ids: list, cx: float, cy: float, r: float) -> list:
  return [i for i in ids if abs(math.hypot(segs[i][0] - cx, segs[i][1] - cy) - r) <= FIT_TOL * r and abs(math.hypot(segs[i][2] - cx, segs[i][3] - cy) - r) <= FIT_TOL * r]

def _closed(segs: list, ids: list, cx: float, cy: float) -> bool:
  angles = sorted(math.atan2((segs[i][1] + segs[i][3]) / 2.0 - cy, (segs[i][0] + segs[i][2]) / 2.0 - cx) for i in ids)
  gaps = [b - a for a, b in zip(angles, angles[1:])] + [angles[0] + 2.0 * math.pi - angles[-1]]
  return max(gaps) <= MAX_GAP

def _rings_in(segs: list, ids: list, f: float) -> list:
  left = list(ids)
  out: list = []
  lo, hi = C.COLUMN_PIECE_MIN_MM / f / 2.0, C.COLUMN_PIECE_MAX_MM / f / 2.0
  while len(left) >= MIN_SEGS:
    longest = sorted(left, key=lambda i: -math.hypot(segs[i][2] - segs[i][0], segs[i][3] - segs[i][1]))[:12]
    best: tuple | None = None
    for x in range(len(longest)):
      for y in range(x + 1, len(longest)):
        c = _centre(segs[longest[x]], segs[longest[y]])
        if c is None:
          continue
        r = math.hypot(segs[longest[x]][0] - c[0], segs[longest[x]][1] - c[1])
        if not lo <= r <= hi:
          continue
        got = _fits(segs, left, c[0], c[1], r)
        if len(got) >= MIN_SEGS and (best is None or len(got) > len(best[3])):
          best = (c[0], c[1], r, got)

    if best is None or not _closed(segs, best[3], best[0], best[1]):
      break
    out.append((best[0], best[1], best[2]))
    taken = set(best[3])
    left = [i for i in left if i not in taken]
  return out

def circles(index, f: float, words: list | None = None) -> list:
  if sum(1 for w in words or [] if SPN._string_of(w)) >= SPL.MIN_STRINGS:
    return []
  segs = _curves(index, f)

  out: list = []
  for ids in _chains(segs):
    if len(ids) < MIN_SEGS or len(ids) > MAX_CHAIN:
      continue
    for cx, cy, r in _rings_in(segs, ids, f):
      if any(math.hypot(wd.cx - cx, wd.cy - cy) <= r for wd in words or []):
        continue
      out.append({"cx": cx, "cy": cy, "d": 2.0 * r * f, "r": r})

  out.sort(key=lambda c: -c["d"])
  kept: list = []
  for c in out:
    if any(math.hypot(c["cx"] - k["cx"], c["cy"] - k["cy"]) <= 0.3 * k["r"] for k in kept):
      continue
    kept.append(c)
  return kept
