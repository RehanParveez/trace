from __future__ import annotations
import math
import hashlib
from app.modules.drawings_boq.takeoff.prep.texts import is_tag

MIN_SHAPE_PT = 2.5
MAX_POINTS_PER_GROUP = 3000
DENSE_NEIGHBOURS = 40

def _is_rectangle(pts) -> tuple | None:
  if len(pts) != 4:
    return None
  e = [(pts[(i + 1) % 4][0] - pts[i][0], pts[(i + 1) % 4][1] - pts[i][1]) for i in range(4)]
  ln = [math.hypot(*v) for v in e]
  if min(ln) < 1e-6:
    return None
  for i in range(4):
    dot = (e[i][0] * e[(i + 1) % 4][0] + e[i][1] * e[(i + 1) % 4][1]) / (ln[i] * ln[(i + 1) % 4])
    if abs(dot) > 0.03:
      return None
  if abs(ln[0] - ln[2]) > 0.02 * max(ln[0], ln[2]) + 0.1 or abs(ln[1] - ln[3]) > 0.02 * max(ln[1], ln[3]) + 0.1:
    return None
  return (ln[0] + ln[2]) / 2.0, (ln[1] + ln[3]) / 2.0

def _centroid(r) -> tuple:
  return ((r.bbox[0] + r.bbox[2]) / 2.0, (r.bbox[1] + r.bbox[3]) / 2.0)

def _cluster(items: list, tol_rel: float = 0.02, tol_abs: float = 0.25) -> list[list]:

  items = sorted(items, key=lambda t: (t[0], t[1]))
  groups: list[list] = []
  for it in items:
    placed = False
    for g in reversed(groups[-6:]):
      a0, b0 = g[0][0], g[0][1]
      if abs(it[0] - a0) <= max(tol_abs, tol_rel * a0) and abs(it[1] - b0) <= max(tol_abs, tol_rel * b0):
        g.append(it)
        placed = True
        break
    if not placed:
      groups.append([it])
  return groups

def shape_groups(rings: list, page_area: float, min_count: int = 2, limit: int = 60) -> list[dict]:
  rects, circles, polys = [], [], []
  for r in rings:
    w = r.bbox[2] - r.bbox[0]
    h = r.bbox[3] - r.bbox[1]
    if min(w, h) < MIN_SHAPE_PT or w * h > 0.05 * page_area:
      continue
    rect = _is_rectangle(r.pts)
    
    if rect is not None and not r.curved:
      a, b = sorted(rect)
      rects.append((a, b, r))
    elif r.curved and len(r.pts) >= 8 and abs(w - h) <= 0.04 * max(w, h) and abs(r.area - math.pi * (w + h) ** 2 / 16.0) <= 0.08 * r.area:
      d = (w + h) / 2.0
      circles.append((d, d, r))
      
    elif len(r.pts) >= 3:
      per = sum(math.dist(r.pts[i], r.pts[(i + 1) % len(r.pts)]) for i in range(len(r.pts)))
      polys.append((math.sqrt(r.area), per / 4.0, r))
  out = []
  for shape, items in (("RECT", rects), ("CIRCLE", circles), ("POLY", polys)):
    for g in _cluster(items):
      if len(g) < min_count:
        continue
      a = sum(t[0] for t in g) / len(g)
      b = sum(t[1] for t in g) / len(g)
      
      if len(g) > 500 and min(a, b) < 4.0:
        continue  
      pts = [list(map(lambda v: round(v, 3), _centroid(t[2]))) for t in g][:MAX_POINTS_PER_GROUP]
      n_vertices = len(g[0][2].pts)
      gid = hashlib.sha1(f"{shape}|{round(a, 1)}|{round(b, 1)}|{n_vertices}".encode()).hexdigest()[:10]
      out.append({"id": gid, "shape": shape, "a_pt": round(a, 3), "b_pt": round(b, 3), "count": len(g),
        "filled": sum(1 for t in g if t[2].fill), "points": pts,
        "bbox": [round(min(t[2].bbox[0] for t in g), 2), round(min(t[2].bbox[1] for t in g), 2),
          round(max(t[2].bbox[2] for t in g), 2), round(max(t[2].bbox[3] for t in g), 2)]})
  out.sort(key=lambda d: (-d["count"], -d["a_pt"] * d["b_pt"]))
  return out[:limit]

def dense_flags(words: list, radius: float = 90.0) -> list[bool]:
  cell = radius
  grid: dict = {}
  for i, w in enumerate(words):
    grid.setdefault((int(w.cx // cell), int(w.cy // cell)), []).append(i)
  flags = []
  for w in words:
    cx, cy = int(w.cx // cell), int(w.cy // cell)
    n = 0
    for ix in (cx - 1, cx, cx + 1):
      for iy in (cy - 1, cy, cy + 1):
        for j in grid.get((ix, iy), ()):
          o = words[j]
          if math.hypot(o.cx - w.cx, o.cy - w.cy) <= radius:
            n += 1
    flags.append(n > DENSE_NEIGHBOURS)
  return flags

def tag_census(words: list, limit: int = 80) -> list[dict]:
  flags = dense_flags(words) if words else []
  groups: dict = {}
  
  for w, dense in zip(words, flags):
    if not is_tag(w.text):
      continue
    key = w.text.strip().upper()
    g = groups.setdefault(key, {"tag": key, "count": 0, "in_drawing": 0, "points": []})
    g["count"] += 1
    if not dense:
      g["in_drawing"] += 1
    g["points"].append({"x": round(w.cx, 3), "y": round(w.cy, 3), "dense": bool(dense)})
  out = sorted(groups.values(), key=lambda g: (-g["in_drawing"], -g["count"], g["tag"]))
  return out[:limit]

def find_words(words: list, query: str, mode: str = "TAG", case_sensitive: bool = False) -> list[dict]:
  q = query.strip()
  if not q:
    return []
  flags = dense_flags(words)
  out = []
  for w, dense in zip(words, flags):
    t = w.text.strip()
    a, b = (t, q) if case_sensitive else (t.upper(), q.upper())
    hit = (a == b) if mode in ("TAG", "WORD") else (b in a)
    if hit:
      out.append({"text": t, "x": round(w.cx, 3), "y": round(w.cy, 3), "angle": round(w.angle, 1), "size": round(w.size, 2),
        "dense": bool(dense)})
  return out
