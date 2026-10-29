from __future__ import annotations
import math
from app.modules.drawings_boq.takeoff.extract import room_types as RT
from dataclasses import dataclass
from app.modules.drawings_boq.takeoff.model.types import WallRun, Face
from shapely.strtree import STRtree
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union

OUTSIDE, UNNAMED = "OUTSIDE", "UNNAMED"
FREE = "FREE"
STEP_MM = 50.0
PROBE_SHARE = 0.18
PROBE_REACH = 0.35
MIN_ROOM_M2 = 2.0
OPEN_SHARE = 0.5
OUTSIDE_TYPES = (RT.PORCH, RT.TERRACE, RT.LAWN)

@dataclass(frozen=True)
class WallGraph:
  runs: tuple = ()
  faces: int = 0
  open_rooms: tuple = ()
  rooms_seen: int = 0

  @property
  def closed(self) -> bool:
    return self.rooms_seen > 0 and not self.open_rooms

  def sides(self) -> list:
    out = []
    for r in self.runs:
      inside = sum(f.length_share for f in r.faces if f.bounds != OUTSIDE)
      outside = sum(f.length_share for f in r.faces if f.bounds == OUTSIDE)
      out.append((round(inside, 4), round(outside, 4)))
    return out

def _end_free(w, k: int) -> bool:
  ends = (w.facts or {}).get("ends") or []
  return len(ends) > k and str(ends[k]).upper() == FREE

def _thickness_mm(w) -> float:
  f = w.facts or {}
  return float(f.get("thickness_used_mm") or (w.params or {}).get("thickness_mm") or 228.6)

def _ring(room):
  g = room.geometry or {}
  ring = g.get("outer") or g.get("points") or []
  return [tuple(p) for p in ring] if len(ring) >= 3 else None

def build(walls: list, rooms: list, mm_per_pt: float, floor: str | None = None, bridge_mm: float = 0.0) -> WallGraph:
  segs = []
  for w in walls:
    pts = (w.geometry or {}).get("points") or []
    a, b = (tuple(pts[0]), tuple(pts[-1])) if len(pts) >= 2 else (None, None)
    segs.append((w, a, b))
  live = [(w, a, b) for w, a, b in segs if a is not None and (a[0] != b[0] or a[1] != b[1])]
  if not live or not mm_per_pt:
    return WallGraph(tuple(WallRun(str(i), floor, (0.0, 0.0), (0.0, 0.0), _thickness_mm(w), ()) for i, (w, _a, _b) in enumerate(segs)))

  rects: dict = {}
  for k, (w, a, b) in enumerate(segs):
    if a is None or (a[0] == b[0] and a[1] == b[1]):
      continue
    t = _thickness_mm(w) / mm_per_pt
    n = math.hypot(b[0] - a[0], b[1] - a[1])
    ux, uy = (b[0] - a[0]) / n, (b[1] - a[1]) / n
    ea = 0.0 if _end_free(w, 0) else t / 2.0
    eb = 0.0 if _end_free(w, 1) else t / 2.0
    rects[k] = LineString([(a[0] - ux * ea, a[1] - uy * ea), (b[0] + ux * eb, b[1] + uy * eb)]).buffer(t / 2.0, cap_style=2, join_style=2)
  solid = unary_union(list(rects.values()))
  
  if bridge_mm:
    reach = bridge_mm / mm_per_pt
    extra = []
    for k, (w, a, b) in enumerate(segs):
      if k not in rects:
        continue
      t = _thickness_mm(w) / mm_per_pt
      n = math.hypot(b[0] - a[0], b[1] - a[1])
      ux, uy = (b[0] - a[0]) / n, (b[1] - a[1]) / n
      others = unary_union([r for j, r in rects.items() if j != k])
      for end, (px, py), sign in ((0, a, -1.0), (1, b, 1.0)):
        if not _end_free(w, end):
          continue
        tip = (px + sign * ux * t / 2.0, py + sign * uy * t / 2.0)
        ray = LineString([tip, (tip[0] + sign * ux * reach, tip[1] + sign * uy * reach)])
        hit = ray.intersection(others)
        if hit.is_empty:
          continue
        parts = list(hit.geoms) if hasattr(hit, "geoms") else [hit]
        near = min(ray.project(Point(c)) for g in parts for c in g.coords)
        if near > 0:
          extra.append(LineString([tip, (tip[0] + sign * ux * (near + 1e-6), tip[1] + sign * uy * (near + 1e-6))]).buffer(t / 2.0, cap_style=2, join_style=2))
    if extra:
      solid = unary_union([solid, *extra])
      
  minx, miny, maxx, maxy = solid.bounds
  pad = max(maxx - minx, maxy - miny) * 0.05 + 10.0
  frame = box(minx - pad, miny - pad, maxx + pad, maxy + pad)
  free = frame.difference(solid)
  comps = list(free.geoms) if hasattr(free, "geoms") else [free]
  touching = [c for c in comps if c.intersects(frame.exterior)]
  outside = max(touching or comps, key=lambda c: c.area)
  closed_spaces = [c for c in comps if c is not outside]
  sqm = (mm_per_pt ** 2) / 1e6
  
  room_rows = []
  for idx, r in enumerate(rooms):
    ring = _ring(r)
    if ring is None:
      continue
    poly = Polygon(ring)
    if not poly.is_valid:
      poly = poly.buffer(0)
    name = str((r.facts or {}).get("name") or "").strip()
    bound = OUTSIDE if RT.of_room(r) in OUTSIDE_TYPES else f"{name or UNNAMED}#{idx}"
    room_rows.append((r, poly, bound))
  open_rooms = tuple((r.facts or {}).get("name") or UNNAMED for r, poly, bound in room_rows
    if poly.area * sqm >= MIN_ROOM_M2 and bound != OUTSIDE and outside.intersection(poly).area > OPEN_SHARE * poly.area)
  room_tree = STRtree([p for _, p, _ in room_rows]) if room_rows else None
  
  space_tree = STRtree(comps)
  def where(pt, reach):
    p = Point(pt)
    if room_tree is not None:
      hits = [j for j in room_tree.query(p.buffer(reach)) if room_rows[j][1].distance(p) <= reach]
      if hits:
        return room_rows[min(hits, key=lambda j: room_rows[j][1].distance(p))][2]
    for j in space_tree.query(p):
      if comps[j].contains(p):
        return OUTSIDE if comps[j] is outside else UNNAMED
    return None

  runs = []
  for k, (w, a, b) in enumerate(segs):
    if k not in rects:
      runs.append(WallRun(str(k), floor, (0.0, 0.0), (0.0, 0.0), _thickness_mm(w), ()))
      continue
    t = _thickness_mm(w) / mm_per_pt
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy)
    ux, uy = dx / n, dy / n
    nx, ny = -uy, ux
    steps = max(1, int(round(n * mm_per_pt / STEP_MM)))
    off = t / 2.0 + PROBE_SHARE * t
    seen = {"L": [], "R": []}
    for s in range(steps):
      f = (s + 0.5) / steps
      cx, cy = a[0] + dx * f, a[1] + dy * f
      for side, sign in (("L", 1.0), ("R", -1.0)):
        seen[side].append(where((cx + sign * nx * off, cy + sign * ny * off), PROBE_REACH * t))
        
    tally = {"L": {}, "R": {}}
    for side in ("L", "R"):
      row = seen[side]
      for i, bound in enumerate(row):
        if bound is None:
    
          near = next((row[j] for d in range(1, len(row)) for j in (i - d, i + d) if 0 <= j < len(row) and row[j] is not None), None)
          bound = near
        if bound is not None:
          tally[side][bound] = tally[side].get(bound, 0) + 1
    faces = tuple(Face(side, bound, round(cnt / steps, 4)) for side in ("L", "R") for bound, cnt in sorted(tally[side].items()))
    runs.append(WallRun(str(k), floor, (round(a[0], 3), round(a[1], 3)), (round(b[0], 3), round(b[1], 3)), _thickness_mm(w), faces))
  return WallGraph(tuple(runs), len(closed_spaces), open_rooms, sum(1 for _r, p, bd in room_rows if p.area * sqm >= MIN_ROOM_M2 and bd != OUTSIDE))
