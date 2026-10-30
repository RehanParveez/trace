from __future__ import annotations
import math
from app.modules.drawings_boq.takeoff.extract import room_types as RT
from dataclasses import dataclass
from app.modules.drawings_boq.takeoff.model.types import WallRun, Face
from shapely.strtree import STRtree
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union
from shapely.prepared import prep

DRAWN, PLASTER_DRAWN, DRAWN_UNMATCHED = "DRAWN", "PLASTER_DRAWN", "DRAWN_UNMATCHED"

def brick_thickness(drawn_mm: float, sizes: tuple, plaster_mm: float, tol_mm: float = 6.0) -> tuple:
  best = None
  for s in sizes:
    for extra, basis in ((0.0, DRAWN), (2.0 * float(plaster_mm), PLASTER_DRAWN)):
      gap = abs(float(drawn_mm) - (s + extra))
      if gap <= tol_mm and (best is None or gap < best[0] - 1e-9):
        best = (gap, float(s), basis)
  return (best[1], best[2]) if best else (float(drawn_mm), DRAWN_UNMATCHED)

def plaster_band(drawn_mm: float, sizes: tuple, plaster_mm: float, tol_mm: float = 6.0) -> float | None:
  for s in sizes:
    if s - tol_mm <= float(drawn_mm) <= s + 2.0 * float(plaster_mm) + tol_mm:
      return float(s)
  return None

def sheet_basis(lengths: dict) -> tuple:
  p, d = float(lengths.get(PLASTER_DRAWN, 0.0)), float(lengths.get(DRAWN, 0.0))
  return (PLASTER_DRAWN if p > d else DRAWN), (p > 0.0 and d > 0.0)

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
  return float(f.get("thickness_face_mm") or f.get("thickness_used_mm") or (w.params or {}).get("thickness_mm") or 228.6)

def _ring(room):
  g = room.geometry or {}
  ring = g.get("outer") or g.get("points") or []
  return [tuple(p) for p in ring] if len(ring) >= 3 else None

def _solid_of(segs: list, mm_per_pt: float, bridge_mm: float) -> tuple:
  """The rectangle of every wall and their union, with the free ends that meet another wall within bridge_mm run on to it. (rects by index, solid.)"""
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
      
  return rects, solid

def build(walls: list, rooms: list, mm_per_pt: float, floor: str | None = None, bridge_mm: float = 0.0) -> WallGraph:
  segs = []
  for w in walls:
    pts = (w.geometry or {}).get("points") or []
    a, b = (tuple(pts[0]), tuple(pts[-1])) if len(pts) >= 2 else (None, None)
    segs.append((w, a, b))
  live = [(w, a, b) for w, a, b in segs if a is not None and (a[0] != b[0] or a[1] != b[1])]
  if not live or not mm_per_pt:
    return WallGraph(tuple(WallRun(str(i), floor, (0.0, 0.0), (0.0, 0.0), _thickness_mm(w), ()) for i, (w, _a, _b) in enumerate(segs)))

  rects, solid = _solid_of(segs, mm_per_pt, bridge_mm)
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

def outline_sides(walls: list, rooms: list, mm_per_pt: float, bridge_mm: float = 0.0, close_mm: float = 0.0, courtyard_external: bool = True) -> tuple:
  segs = []
  
  for w in walls:
    pts = (w.geometry or {}).get("points") or []
    a, b = (tuple(pts[0]), tuple(pts[-1])) if len(pts) >= 2 else (None, None)
    segs.append((w, a, b))
    
  live = [k for k, (w, a, b) in enumerate(segs) if a is not None and (a[0] != b[0] or a[1] != b[1])]
  if not live or not mm_per_pt:
    return [(0.0, 0.0)] * len(segs), {"perimeter_m": 0.0, "outer_face_m": 0.0, "area_m2": 0.0}
  rects, solid = _solid_of(segs, mm_per_pt, bridge_mm)
  closed = solid.buffer(close_mm / mm_per_pt).buffer(-close_mm / mm_per_pt) if close_mm else solid
  polys = list(closed.geoms) if hasattr(closed, "geoms") else [closed]
  outline = unary_union([Polygon(p.exterior) for p in polys if not p.is_empty and hasattr(p, "exterior")])
  
  if courtyard_external:
    courts = [Polygon(ring) for r in rooms if RT.of_room(r) in OUTSIDE_TYPES and (ring := _ring(r)) is not None]
    courts = [c.buffer(0) for c in courts]
    inner = [c for c in courts if outline.contains(c.representative_point()) and outline.buffer(-1e-6).contains(c)]
    if inner:
      outline = outline.difference(unary_union(inner))
      
  sqm = (mm_per_pt ** 2) / 1e6
  inside_outline = prep(outline)
  out, outer_cc = [], 0.0
  for k, (w, a, b) in enumerate(segs):
    if k not in rects:
      out.append((0.0, 0.0))
      continue
    t = _thickness_mm(w) / mm_per_pt
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy)
    ux, uy = dx / n, dy / n
    nx, ny = -uy, ux
    steps = max(1, int(round(n * mm_per_pt / STEP_MM)))
    off = t / 2.0 + PROBE_SHARE * t
    inside = outside = 0
    for s_ in range(steps):
      f = (s_ + 0.5) / steps
      cx, cy = a[0] + dx * f, a[1] + dy * f
      for sign in (1.0, -1.0):
        if inside_outline.contains(Point(cx + sign * nx * off, cy + sign * ny * off)):
          inside += 1
        else:
          outside += 1
    out.append((round(inside / steps, 4), round(outside / steps, 4)))
    outer_cc += (outside / steps) * n * mm_per_pt / 1000.0
  perimeter = sum(p.length for p in (list(outline.geoms) if hasattr(outline, "geoms") else [outline])) * mm_per_pt / 1000.0
  parts = sorted((round(g.length * mm_per_pt / 1000.0, 2) for g in (list(outline.geoms) if hasattr(outline, "geoms") else [outline])), reverse=True)
  return out, {"perimeter_m": round(perimeter, 3), "outer_face_m": round(outer_cc, 3), "area_m2": round(outline.area * sqm, 3), "parts_m": parts[:6]}
