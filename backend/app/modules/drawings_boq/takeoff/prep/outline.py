from __future__ import annotations
import math
import time

GRID = (6.0, 8.0, 11.0, 15.0, 20.0, 27.0, 36.0, 48.0)
MIN_RUNS = 6
BUDGET_S = 6.0
VERSION = 1

def _runs_segments(frames: list, runs: list) -> list:
  out = []
  for r in runs:
    fr = frames[r.peak]
    out.append((fr.pt(r.s0 - r.ext0, r.dc), fr.pt(r.s1 + r.ext1, r.dc), float(r.t_pt)))
  return out

def _biggest_group(segs: list) -> list:
  from shapely.geometry import LineString
  from shapely.strtree import STRtree
  geoms = [LineString([s[0], s[1]]).buffer(1.5 * s[2]) for s in segs]
  tree = STRtree(geoms)
  parent = list(range(len(segs)))
  def find(i: int) -> int:
    while parent[i] != i:
      parent[i] = parent[parent[i]]
      i = parent[i]
    return i

  for i, g in enumerate(geoms):
    for j in tree.query(g):
      j = int(j)
      if j > i and g.intersects(geoms[j]):
        parent[find(j)] = find(i)
  groups: dict = {}
  for i, s in enumerate(segs):
    groups.setdefault(find(i), []).append(s)
  return max(groups.values(), key=lambda g: sum(math.dist(s[0], s[1]) for s in g))

def sample(index, f: float, deadline: float | None = None) -> dict | None:
  from app.modules.drawings_boq.takeoff.extract import walls as W
  from shapely.geometry import MultiPoint
  frames, runs, _st = W.detect_walls(index, f, deadline, False)
  if len(runs) < MIN_RUNS:
    return None

  segs = _runs_segments(frames, runs)
  best = _biggest_group(segs)
  pts = [p for s in best for p in (s[0], s[1])]
  rect = MultiPoint(pts).convex_hull.minimum_rotated_rectangle
  if rect.geom_type != "Polygon":
    return None

  xs = list(rect.exterior.coords)[:4]
  a, b = math.dist(xs[0], xs[1]), math.dist(xs[1], xs[2])
  if min(a, b) <= 0:
    return None
  return {"f": f, "short_pt": round(min(a, b), 2), "long_pt": round(max(a, b), 2), "runs": len(runs), "group": len(best),
    "wall_pt": round(sum(math.dist(s[0], s[1]) for s in best), 1)}

def samples(index, deadline: float | None = None, budget_s: float = BUDGET_S) -> dict:
  started = time.monotonic()
  limit = min(deadline, started + budget_s) if deadline is not None else started + budget_s
  out = []
  for f in GRID:
    if time.monotonic() > limit:
      break
    try:
      s = sample(index, f, limit)
    except Exception:
      s = None
    if s:
      out.append(s)
  return {"version": VERSION, "samples": out}
