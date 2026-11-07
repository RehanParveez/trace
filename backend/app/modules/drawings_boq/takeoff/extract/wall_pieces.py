from __future__ import annotations
import math
from app.engine.measure import rule_registry as RR

RULE = "WALL_PIECES_AT_DOORS"
DOOR = "DOOR"
WIDTH_SHARE = 0.15

def enabled() -> bool:
  return RR.on(RULE)

def _dist(a, b) -> float:
  return math.hypot(a[0] - b[0], a[1] - b[1])

def door_gaps(facts: dict | None, params: dict | None) -> list:
  facts, params = facts or {}, params or {}
  gaps, widths, opens = facts.get("gap_pts") or [], facts.get("gaps_mm") or [], params.get("openings") or []
  out = []
  
  for i, gap in enumerate(gaps):
    width = widths[i] if i < len(widths) else None
    if not width or not opens or len(gap) < 2:
      continue
    best = min(opens, key=lambda o: abs((o.get("width_mm") or 0.0) - width))
    if best.get("role") == DOOR and abs((best.get("width_mm") or 0.0) - width) <= WIDTH_SHARE * width:
      out.append([[float(gap[0][0]), float(gap[0][1])], [float(gap[1][0]), float(gap[1][1])]])
  return out

def pieces(points: list, gaps: list, min_len: float = 0.0) -> list:
  if len(points) < 2 or not gaps:
    return [points]
  a, b = points[0], points[-1]
  length = _dist(a, b)
  if length <= 0:
    return [points]
  ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
  spans = []
  
  for p, q in gaps:
    s, e = sorted(((p[0] - a[0]) * ux + (p[1] - a[1]) * uy, (q[0] - a[0]) * ux + (q[1] - a[1]) * uy))
    spans.append((max(0.0, s), min(length, e)))
  spans.sort()
  parts, at = [], 0.0
  for s, e in spans:
    if s - at > min_len:
      parts.append((at, s))
    at = max(at, e)
  if length - at > min_len:
    parts.append((at, length))
  if not parts:
    return [points]
  return [[[a[0] + ux * s, a[1] + uy * s], [a[0] + ux * e, a[1] + uy * e]] for s, e in parts]

def pieces_of(cand, mm_per_pt: float | None) -> list:
  points = [[float(p[0]), float(p[1])] for p in ((cand.geometry or {}).get("points") or []) if isinstance(p, (list, tuple)) and len(p) >= 2]
  if not enabled() or len(points) < 2:
    return [points]
  thickness = (cand.params or {}).get("thickness_mm")
  min_len = (float(thickness) / mm_per_pt) if thickness and mm_per_pt else 0.0
  return pieces(points, door_gaps(cand.facts, cand.params), min_len)
