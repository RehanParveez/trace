from __future__ import annotations

MIN_SIDE_SHARE = 0.30
MARGIN_SHARE = 0.18
MAX_ASPECT = 2.0

def points_of(geometry: dict | None) -> list[tuple[float, float]]:
  g = geometry or {}
  raw = g.get("outer") if g.get("outer") else g.get("points")
  out: list[tuple[float, float]] = []
  for p in raw or []:
    try:
      out.append((float(p[0]), float(p[1])))
    except (TypeError, ValueError, IndexError):
      continue
  return out

def candidate_box(geometry: dict | None, width: float, height: float) -> tuple[float, float, float, float] | None:
  pts = points_of(geometry)
  if not pts or width <= 0 or height <= 0:
    return None

  x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
  y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
  margin = max(x1 - x0, y1 - y0) * MARGIN_SHARE
  x0, x1, y0, y1 = x0 - margin, x1 + margin, y0 - margin, y1 + margin
  floor = min(width, height) * MIN_SIDE_SHARE
  w, h = max(x1 - x0, floor), max(y1 - y0, floor)
  if w > h * MAX_ASPECT:
    h = w / MAX_ASPECT
  elif h > w * MAX_ASPECT:
    w = h / MAX_ASPECT

  w, h = min(w, width), min(h, height)
  cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
  bx0 = min(max(cx - w / 2.0, 0.0), width - w)
  by0 = min(max(cy - h / 2.0, 0.0), height - h)
  return bx0, by0, bx0 + w, by0 + h
