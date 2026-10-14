from __future__ import annotations
import math

RCC_T_MIN_MM = 150.0
RCC_T_MAX_MM = 420.0
RCC_MIN_PIECE_MM = 450.0
RCC_MIN_ASPECT = 2.0
RCC_MIN_RUN_MM = 1500.0
RCC_GAP_MAX_MM = 2600.0
RCC_T_SIMILAR = 0.2
OVERLAP_TOL_FACTOR = 0.75
OVERLAP_MIN_SHARE = 0.6
PARALLEL_DEG = 4.0
ENVELOPE_SIDE_SHARE = 0.5     
ENVELOPE_EDGE_TOL_MM = 600.0
ENVELOPE_MARGIN_MM = 450.0

def fill_strips(rings: list, mm_per_pt: float) -> list[dict]:
  """Solid rectangular strips (a rectangle is often drawn as two triangles, so equal boxes are counted once)."""
  seen: set = set()
  out = []
  for r in rings:
    if not r.fill or r.curved or len(r.pts) > 8:
      continue
    x0, y0, x1, y1 = r.bbox
    w, h = (x1 - x0) * mm_per_pt, (y1 - y0) * mm_per_pt
    a, b = (w, h) if w <= h else (h, w)
    if not (RCC_T_MIN_MM <= a <= RCC_T_MAX_MM) or b < RCC_MIN_PIECE_MM or b / max(a, 1e-9) < RCC_MIN_ASPECT:
      continue
    if r.area < 0.4 * (x1 - x0) * (y1 - y0):
      continue
    key = (round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1))
    
    if key in seen:
      continue
    seen.add(key)
    out.append({"x0": x0, "y0": y0, "x1": x1, "y1": y1, "horizontal": w > h, "t_mm": a})
  return out

def rcc_runs(rings: list, mm_per_pt: float) -> list[dict]:
  """Concrete wall runs: {"p0", "p1", "t_mm", "length_mm", "clear_mm", "gaps"} with points in page points, centre line."""
  strips = fill_strips(rings, mm_per_pt)
  runs: list = []
  for horizontal in (True, False):
    mine = [s for s in strips if s["horizontal"] == horizontal]
    
    for s in mine:
      s["c"] = (s["y0"] + s["y1"]) / 2.0 if horizontal else (s["x0"] + s["x1"]) / 2.0
      s["a"], s["b"] = (s["x0"], s["x1"]) if horizontal else (s["y0"], s["y1"])
    mine.sort(key=lambda s: (s["c"], s["a"]))
    groups: list = []
    for s in mine:
      placed = False
      for g in reversed(groups[-3:]):
        g0 = g[0]
        if abs(s["c"] - g0["c"]) <= 0.5 * g0["t_mm"] / mm_per_pt and abs(s["t_mm"] - g0["t_mm"]) <= RCC_T_SIMILAR * g0["t_mm"]:
          g.append(s)
          placed = True
          break
      if not placed:
        groups.append([s])
    gap_max = RCC_GAP_MAX_MM / mm_per_pt
    
    for g in groups:
      g.sort(key=lambda s: s["a"])
      c = sum(s["c"] for s in g) / len(g)
      t = sum(s["t_mm"] for s in g) / len(g)
      cur = {"a": g[0]["a"], "b": g[0]["b"], "clear": g[0]["b"] - g[0]["a"], "gaps": []}
      pieces = []
      
      for s in g[1:]:
        gap = s["a"] - cur["b"]
        if gap <= gap_max:
          if gap > 0.5:
            cur["gaps"].append((cur["b"], s["a"]))
          cur["clear"] += max(0.0, s["b"] - max(s["a"], cur["b"]))
          cur["b"] = max(cur["b"], s["b"])
        else:
          pieces.append(cur)
          cur = {"a": s["a"], "b": s["b"], "clear": s["b"] - s["a"], "gaps": []}
      pieces.append(cur)
      
      for p in pieces:
        length = (p["b"] - p["a"]) * mm_per_pt
        if length < RCC_MIN_RUN_MM:
          continue
        p0, p1 = ((p["a"], c), (p["b"], c)) if horizontal else ((c, p["a"]), (c, p["b"]))
        gaps = [[[x0, c], [x1, c]] if horizontal else [[c, x0], [c, x1]] for x0, x1 in p["gaps"]]
        runs.append({"p0": p0, "p1": p1, "t_mm": t, "length_mm": length, "clear_mm": p["clear"] * mm_per_pt,
          "gaps_mm": [round((x1 - x0) * mm_per_pt) for x0, x1 in p["gaps"]], "gap_pts": gaps})
  runs.sort(key=lambda r: -r["length_mm"])
  return runs

def _along(p0, p1, q) -> tuple:
  """(s, d): where point q falls along the segment p0-p1 (0..1) and its distance from the line, in points."""
  vx, vy = p1[0] - p0[0], p1[1] - p0[1]
  ln = math.hypot(vx, vy) or 1e-9
  ux, uy = vx / ln, vy / ln
  s = ((q[0] - p0[0]) * ux + (q[1] - p0[1]) * uy) / ln
  d = abs((q[0] - p0[0]) * -uy + (q[1] - p0[1]) * ux)
  return s, d

def covered_share(run: dict, p0, p1, mm_per_pt: float) -> float:
  """The share of a masonry run (p0 to p1) that lies along the concrete run, on the same line and in the same direction."""
  ax, ay = run["p1"][0] - run["p0"][0], run["p1"][1] - run["p0"][1]
  bx, by = p1[0] - p0[0], p1[1] - p0[1]
  la, lb = math.hypot(ax, ay), math.hypot(bx, by)
  if la <= 0 or lb <= 0:
    return 0.0
  cos = abs(ax * bx + ay * by) / (la * lb)
  if cos < math.cos(math.radians(PARALLEL_DEG)):
    return 0.0
  tol_pt = (OVERLAP_TOL_FACTOR * run["t_mm"] + 40.0) / mm_per_pt
  n = max(4, int(lb * mm_per_pt / 200.0))
  hit = 0
  for i in range(n + 1):
    q = (p0[0] + bx * i / n, p0[1] + by * i / n)
    s, d = _along(run["p0"], run["p1"], q)
    if -0.001 <= s <= 1.001 and d <= tol_pt:
      hit += 1
  return hit / (n + 1)

def covered_by(runs: list, p0, p1, mm_per_pt: float) -> bool:
  return any(covered_share(r, p0, p1, mm_per_pt) >= OVERLAP_MIN_SHARE for r in runs)

def envelope(runs: list, mm_per_pt: float) -> tuple | None:
  """(x0, y0, x1, y1) the concrete walls enclose, when they bound at least three sides of a box (a basement: retaining walls on the earth sides).
  Where a side is open, the box ends at the inner end of the two walls beside it. None when the concrete walls do not enclose anything."""
  if len(runs) < 3:
    return None

  xs = [q[0] for r in runs for q in (r["p0"], r["p1"])]
  ys = [q[1] for r in runs for q in (r["p0"], r["p1"])]
  x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
  w, h = x1 - x0, y1 - y0
  if w <= 0 or h <= 0:
    return None
  tol = ENVELOPE_EDGE_TOL_MM / mm_per_pt
  vert = [r for r in runs if abs(r["p0"][0] - r["p1"][0]) < 1e-6]
  horiz = [r for r in runs if abs(r["p0"][1] - r["p1"][1]) < 1e-6]
  def side(group, axis, edge, span):
    return [r for r in group if abs(r["p0"][axis] - edge) <= tol and abs(r["p1"][1 - axis] - r["p0"][1 - axis]) >= ENVELOPE_SIDE_SHARE * span]
  sides = {"left": side(vert, 0, x0, h), "right": side(vert, 0, x1, h), "low": side(horiz, 1, y0, w), "high": side(horiz, 1, y1, w)}
  closed = [k for k, v in sides.items() if v]
  if len(closed) < 3:
    return None

  box = [x0, y0, x1, y1]
  if len(closed) == 3:
    open_side = next(k for k, v in sides.items() if not v)
    if open_side in ("low", "high"):
      beside = sides["left"] + sides["right"]
      if open_side == "low":
        box[1] = max(min(q[1] for q in (r["p0"], r["p1"])) for r in beside)
      else:
        box[3] = min(max(q[1] for q in (r["p0"], r["p1"])) for r in beside)
    else:
      beside = sides["low"] + sides["high"]
      if open_side == "left":
        box[0] = max(min(q[0] for q in (r["p0"], r["p1"])) for r in beside)
      else:
        box[2] = min(max(q[0] for q in (r["p0"], r["p1"])) for r in beside)
  margin = ENVELOPE_MARGIN_MM / mm_per_pt
  return (box[0] - margin, box[1] - margin, box[2] + margin, box[3] + margin)

def outside(box: tuple, p0, p1) -> bool:
  """True when the middle of the segment p0-p1 lies outside the box."""
  mx, my = (p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0
  return not (box[0] <= mx <= box[2] and box[1] <= my <= box[3])
