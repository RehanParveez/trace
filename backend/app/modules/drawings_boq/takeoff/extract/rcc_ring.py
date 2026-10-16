from __future__ import annotations

RCC_MIN_RUN_MM = 1500.0
RING_SIDE_CLOSED = 0.8        
RING_MIN_CLOSED_SIDES = 3
RING_MIN_PIECE_MM = 1500.0    
RING_MAX_MISSING_SHARE = 0.4  
RING_EDGE_TOL_MM = 600.0

def _union(spans: list) -> list:
  out: list = []
  for a, b in sorted(spans):
    if out and a <= out[-1][1]:
      out[-1][1] = max(out[-1][1], b)
    else:
      out.append([a, b])
  return out

def _uncovered(lo: float, hi: float, spans: list) -> list:
  out, at = [], lo
  for a, b in _union(spans):
    if a > at:
      out.append((at, min(a, hi)))
    at = max(at, b)
  if at < hi:
    out.append((at, hi))
  return [(a, b) for a, b in out if b > a]

def ring_gaps(runs: list, mm_per_pt: float) -> dict | None:

  if len(runs) < 3:
    return None
  xs = [q[0] for r in runs for q in (r["p0"], r["p1"])]
  ys = [q[1] for r in runs for q in (r["p0"], r["p1"])]
  x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
  w, h = x1 - x0, y1 - y0
  if w * mm_per_pt < RCC_MIN_RUN_MM or h * mm_per_pt < RCC_MIN_RUN_MM:
    return None

  tol = RING_EDGE_TOL_MM / mm_per_pt
  spans = {"left": [], "right": [], "low": [], "high": []}
  for r in runs:
    (ax, ay), (bx, by) = r["p0"], r["p1"]
    if abs(ax - bx) < 1e-6:
      for side, edge in (("left", x0), ("right", x1)):
        if abs(ax - edge) <= tol:
          spans[side].append((min(ay, by), max(ay, by)))
    elif abs(ay - by) < 1e-6:
      for side, edge in (("low", y0), ("high", y1)):
        if abs(ay - edge) <= tol:
          spans[side].append((min(ax, bx), max(ax, bx)))
          
  extent = {"left": (y0, y1), "right": (y0, y1), "low": (x0, x1), "high": (x0, x1)}
  share, missing = {}, {}
  for side, (lo, hi) in extent.items():
    gaps = _uncovered(lo, hi, spans[side])
    missing[side] = [(a, b) for a, b in gaps if (b - a) * mm_per_pt >= RING_MIN_PIECE_MM]
    share[side] = 1.0 - sum(b - a for a, b in _uncovered(lo, hi, spans[side])) / max(hi - lo, 1e-9)
  closed = [s for s, v in share.items() if v >= RING_SIDE_CLOSED]
  if len(closed) < RING_MIN_CLOSED_SIDES:
    return None
  perimeter = 2.0 * (w + h)
  total_missing = sum(b - a for side in missing for a, b in missing[side])
  if total_missing <= 0.0 or total_missing / perimeter > RING_MAX_MISSING_SHARE:
    return None
  t = sum(r["t_mm"] * r["length_mm"] for r in runs) / max(sum(r["length_mm"] for r in runs), 1e-9)
  pieces = []
  
  for side, gaps in missing.items():
    for a, b in gaps:
      if side == "left":
        p0, p1 = (x0, a), (x0, b)
      elif side == "right":
        p0, p1 = (x1, a), (x1, b)
      elif side == "low":
        p0, p1 = (a, y0), (b, y0)
      else:
        p0, p1 = (a, y1), (b, y1)
      pieces.append({"side": side, "p0": p0, "p1": p1, "length_mm": (b - a) * mm_per_pt, "t_mm": t})
  pieces.sort(key=lambda p: -p["length_mm"])
  return {"box": (x0, y0, x1, y1), "sides": {k: round(v, 3) for k, v in share.items()}, "pieces": pieces}
