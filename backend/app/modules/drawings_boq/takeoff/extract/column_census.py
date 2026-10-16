from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import config as C
from collections import Counter
from app.modules.drawings_boq.takeoff.prep.details import norm_mark

def _inch_class(a: float, b: float, imperial: bool, snap) -> tuple:
  a, b = (snap(a), snap(b)) if imperial else (round(a / 5.0) * 5.0, round(b / 5.0) * 5.0)
  return (a, b) if a <= b else (b, a)

def pieces(rings: list, f: float) -> list:
  """The filled rectangles of a plan that could be (a part of) a column symbol: [x0, y0, x1, y1] in page units. A square drawn as two triangles, or
  as a rectangle and two triangles, is one piece."""
  out: list = []
  for r in rings:
    if not r.fill or r.curved or len(r.pts) > 8:
      continue
    x0, y0, x1, y1 = r.bbox
    w, h = (x1 - x0) * f, (y1 - y0) * f
    if min(w, h) < C.COLUMN_PIECE_MIN_MM or max(w, h) > C.COLUMN_PIECE_MAX_MM or r.area < C.COLUMN_FILL_MIN * (x1 - x0) * (y1 - y0):
      continue
    if any(_overlap_share((x0, y0, x1, y1), p) > 0.8 for p in out):
      continue
    out.append((x0, y0, x1, y1))
  return out

def _overlap_share(a: tuple, b: tuple) -> float:
  ix = min(a[2], b[2]) - max(a[0], b[0])
  iy = min(a[3], b[3]) - max(a[1], b[1])
  if ix <= 0 or iy <= 0:
    return 0.0
  small = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
  return ix * iy / small if small > 0 else 0.0

def _join(a: tuple, b: tuple, f: float) -> tuple | None:
  """The rectangle two pieces make when they touch along a side and line up, else None."""
  gap = C.COLUMN_JOIN_GAP_MM / f
  for ax in (0, 1):
    o = 1 - ax
    g = max(b[ax] - a[ax + 2], a[ax] - b[ax + 2])
    if abs(g) > gap:
      continue
  
    la, lb = a[o + 2] - a[o], b[o + 2] - b[o]
    shared = min(a[o + 2], b[o + 2]) - max(a[o], b[o])
    if shared < C.COLUMN_JOIN_ALIGN * min(la, lb) or abs(la - lb) > 0.15 * max(la, lb):
      continue
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))
  return None

def merge(ps: list, f: float) -> list:
  """Touching pieces that line up are one column (two squares side by side are a 9 x 18 in column). Nothing longer than a column is made."""
  cur = list(ps)
  changed = True
  
  while changed:
    changed = False
    for i in range(len(cur)):
      for j in range(i + 1, len(cur)):
        u = _join(cur[i], cur[j], f)
        if u is None or max(u[2] - u[0], u[3] - u[1]) * f > C.COLUMN_PIECE_MAX_MM:
          continue
      
        cur[i] = u
        del cur[j]
        changed = True
        break
      if changed:
        break
  return cur

def census(rings: list, f: float, imperial: bool, snap, level_hint: str | None = None) -> dict:
  """{"level_hint", "total", "classes": [{"a_mm", "b_mm", "count", "points"}]} for the filled shapes of one plan, most numerous size first."""
  by: dict = {}
  
  for x0, y0, x1, y1 in merge(pieces(rings, f), f):
    key = _inch_class((x1 - x0) * f, (y1 - y0) * f, imperial, snap)
    row = by.setdefault(key, {"a_mm": round(key[0], 1), "b_mm": round(key[1], 1), "count": 0, "points": []})
    row["count"] += 1
    if len(row["points"]) < C.COLUMN_CENSUS_POINTS:
      row["points"].append([round((x0 + x1) / 2.0, 2), round((y0 + y1) / 2.0, 2)])
  classes = sorted(by.values(), key=lambda r: (-r["count"], r["a_mm"], r["b_mm"]))
  return {"level_hint": level_hint, "total": sum(r["count"] for r in classes), "mm_per_pt": round(f, 6), "classes": classes}

def same_size(a, b) -> bool:
  return all(abs(float(x) - float(y)) <= max(C.COLUMN_CLASS_MIN_MM, C.COLUMN_CLASS_TOL * max(float(x), float(y))) for x, y in zip(sorted(a), sorted(b)))

def _tags_for(size, details: dict, own_tags: set) -> list:
  """The marks whose column detail gives this size and that the floor's framing plan does not already use."""
  out = []
  for tag, rec in sorted((details or {}).items()):
    if norm_mark(tag) in own_tags:
      continue
    sizes = [tuple(float(v) * 25.4 for v in s) for s in rec.get("sizes_in") or []]
    if any(same_size(size, s) for s in sizes):
      out.append(tag)
  return out

def reconcile(marks: list, shapes: dict | None, details: dict | None = None) -> dict:
  out = {"extra": [], "short": [], "shapes": 0, "marked": sum(int(m.get("count") or 0) for m in marks), "ignored": []}
  if not shapes or not shapes.get("classes"):
    return out

  left = [[c, int(c["count"])] for c in shapes["classes"]]
  out["shapes"] = int(shapes.get("total") or sum(c["count"] for c in shapes["classes"]))
  for m in sorted(marks, key=lambda m: -int(m.get("count") or 0)):
    need = int(m.get("count") or 0)
    
    got = 0
    for size in m.get("sizes_mm") or []:
      for row in left:
        if need - got <= 0:
          break
        if row[1] > 0 and same_size(size, (row[0]["a_mm"], row[0]["b_mm"])):
          t = min(need - got, row[1])
          row[1] -= t
          got += t
    if got < need:
      out["short"].append({"tag": m.get("tag"), "count": need, "shapes": got})
  own_tags = {norm_mark(m["tag"]) for m in marks if m.get("tag")}
  known = [s for m in marks for s in (m.get("sizes_mm") or [])]
  for row, n in left:
    if n <= 0:
      continue
  
    size = (row["a_mm"], row["b_mm"])
    matches_marks = any(same_size(size, s) for s in known)
    tags = _tags_for(size, details or {}, own_tags)
    if not matches_marks and not tags:
      out["ignored"].append({"a_mm": size[0], "b_mm": size[1], "count": n})
      continue
    out["extra"].append({"a_mm": size[0], "b_mm": size[1], "count": n, "tag": None if matches_marks or len(tags) != 1 else tags[0], "tags": tags,
      "matches_marks": matches_marks, "points": list(row["points"])})
  return out

def signature(marks: list) -> tuple:
  return tuple(sorted((norm_mark(m.get("tag")) if m.get("tag") else "", int(m.get("count") or 0)) for m in marks))

def _mm_points(shapes: dict) -> list:
  f = float(shapes.get("mm_per_pt") or 0.0)
  return [(x * f, y * f) for c in shapes.get("classes") or [] for x, y in c.get("points") or []]

def translation(upper: list, lower: list) -> tuple | None:
  """(dx, dy) in mm that moves the points of the upper plan onto the same columns of the lower plan, found by voting over all pairs; None when too few
  columns line up to trust it."""
  if not upper or not lower:
    return None

  step = C.COLUMN_GRID_BIN_MM
  votes: Counter = Counter()
  for ux, uy in upper:
    for lx, ly in lower:
      votes[(round((lx - ux) / step), round((ly - uy) / step))] += 1
  best, top = None, 0
  for (i, j) in list(votes):
    n = sum(votes.get((i + a, j + b), 0) for a in (-1, 0, 1) for b in (-1, 0, 1))
    if n > top:
      best, top = (i, j), n
  if best is None or top < max(C.COLUMN_GRID_MIN_VOTES, C.COLUMN_GRID_MIN_SHARE * min(len(upper), len(lower))):
    return None
  near = [(lx - ux, ly - uy) for ux, uy in upper for lx, ly in lower if abs((lx - ux) - best[0] * step) <= 1.5 * step and abs((ly - uy) - best[1] * step) <= 1.5 * step]
  return sum(d[0] for d in near) / len(near), sum(d[1] for d in near) / len(near)

def project_points(upper_shapes: dict, lower_shapes: dict, from_points: list, size_mm: float, n: int) -> list:
  t = translation(_mm_points(upper_shapes), _mm_points(lower_shapes))
  if t is None:
    return []

  fu, fl = float(upper_shapes["mm_per_pt"]), float(lower_shapes["mm_per_pt"])
  have = _mm_points(lower_shapes)
  out = []
  for x, y in from_points:
    px, py = x * fu + t[0], y * fu + t[1]
    if any(abs(px - hx) <= 0.7 * size_mm and abs(py - hy) <= 0.7 * size_mm for hx, hy in have):
      continue
    out.append([round(px / fl, 2), round(py / fl, 2)])
    if len(out) == n:
      break
  return out

def project(floors: list) -> None:
  """floors: [{"level", "marks", "shapes", "result"}] from the top floor down. A floor that carries the same marks as the floor above but shows fewer
  unmarked shapes (columns fused into a wall on its plan) gets the difference from the floor above, flagged as inferred, and placed on its plan by the
  grid of the floor above."""
  for upper, lower in zip(floors, floors[1:]):
    if not lower["shapes"] or not upper["result"]["extra"] or signature(lower["marks"]) != signature(upper["marks"]):
      continue
    for e in upper["result"]["extra"]:
      mine = next((x for x in lower["result"]["extra"] if same_size((x["a_mm"], x["b_mm"]), (e["a_mm"], e["b_mm"]))), None)
      have = mine["count"] if mine else 0
      
      if have >= e["count"]:
        continue
      if mine is None:
        mine = {k: v for k, v in e.items() if k != "points"}
        mine.update(count=0, points=[])
        lower["result"]["extra"].append(mine)
      missing = e["count"] - have
      placed = project_points(upper["shapes"], lower["shapes"], e.get("points") or [], min(e["a_mm"], e["b_mm"]), missing)
      mine["inferred"] = missing
      mine["inferred_from"] = upper["level"]
      mine["count"] = e["count"]
      mine["points"] = list(mine.get("points") or []) + placed

FLOOR_TOP_DOWN = ("ROOF", "FOURTH", "THIRD", "SECOND", "FIRST", "GROUND", "BASEMENT")

def plan(floors: list, details: dict | None) -> list:
  rows = sorted((r for r in floors if r["level"] in FLOOR_TOP_DOWN and r.get("marks")), key=lambda r: FLOOR_TOP_DOWN.index(r["level"]))
  for r in rows:
    r["result"] = reconcile(r["marks"], r.get("shapes"), details)
  with_shapes = [r for r in rows if r.get("shapes")]
  project(with_shapes)
  return with_shapes
