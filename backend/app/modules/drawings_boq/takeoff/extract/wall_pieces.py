from __future__ import annotations
import math
from app.engine.measure import rule_registry as RR

RULE = "WALL_PIECES_AT_DOORS"
JUNCTION_RULE = "WALL_PIECES_AT_JUNCTIONS"
DOOR = "DOOR"
WIDTH_SHARE = 0.15
PARALLEL_SINE = 0.34
REACH_THICKNESSES = 1.0

def enabled() -> bool:
  return RR.on(RULE)

def junctions_enabled() -> bool:
  return RR.on(JUNCTION_RULE)

def active() -> bool:
  return enabled() or junctions_enabled()

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


def thickness_pt(cand, mm_per_pt: float | None) -> float:
  thickness = (cand.params or {}).get("thickness_mm")
  return float(thickness) / mm_per_pt if thickness and mm_per_pt else 0.0

def straight(cand) -> list | None:
  points = [[float(p[0]), float(p[1])] for p in ((cand.geometry or {}).get("points") or []) if isinstance(p, (list, tuple)) and len(p) >= 2]
  return points if len(points) == 2 and _dist(points[0], points[1]) > 0 else None

def sheet_walls(cands: list, mm_per_pt: float | None) -> list:
  out = []
  for c in cands:
    points = straight(c)
    if points:
      out.append((id(c), points, thickness_pt(c, mm_per_pt)))
  return out

def junction_gaps(points: list, own: int, thick: float, walls: list) -> list:
  a, b = points[0], points[-1]
  length = _dist(a, b)
  ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
  reach = REACH_THICKNESSES * thick
  out = []
  
  for ident, (p, q), w in walls:
    vx, vy = q[0] - p[0], q[1] - p[1]
    span = math.hypot(vx, vy)
    cross = ux * vy - uy * vx
    if ident == own or span <= 0 or abs(cross) / span < PARALLEL_SINE:
      continue
    dx, dy = p[0] - a[0], p[1] - a[1]
    along = (dx * vy - dy * vx) / cross
    beyond = (dx * uy - dy * ux) / cross
    if -reach <= beyond * span and beyond * span <= span + reach and 0.0 < along < length:
      out.append([[a[0] + ux * (along - w / 2.0), a[1] + uy * (along - w / 2.0)], [a[0] + ux * (along + w / 2.0), a[1] + uy * (along + w / 2.0)]])
  return out

def pieces_of(cand, mm_per_pt: float | None, walls: list | None = None) -> list:
  points = [[float(p[0]), float(p[1])] for p in ((cand.geometry or {}).get("points") or []) if isinstance(p, (list, tuple)) and len(p) >= 2]
  if not active() or len(points) < 2:
    return [points]
  thick = thickness_pt(cand, mm_per_pt)
  gaps = door_gaps(cand.facts, cand.params) if enabled() else []
  if junctions_enabled() and walls and len(points) == 2 and thick > 0:
    gaps = [*gaps, *junction_gaps(points, id(cand), thick, walls)]
  return pieces(points, gaps, thick)

