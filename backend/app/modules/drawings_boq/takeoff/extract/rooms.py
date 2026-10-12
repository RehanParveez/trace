from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.prep.texts import TextLine
from app.modules.drawings_boq.takeoff.extract import config as C
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from app.modules.drawings_boq.takeoff.extract.members import _SIZE, category_of, parse_size
from shapely.prepared import prep
from app.modules.drawings_boq.takeoff.extract.walls import run_polygon

_QUAL = r"(?:MASTER|ATTACHED|COMMON|MAIN|SERVANT|FRONT|REAR|UPPER|LOWER|GUEST|KIDS|GIRLS|BOYS)\s+"
_NAME = re.compile(r"(?<![A-Z0-9])(?:" + _QUAL + r")?(?:" + "|".join(re.escape(n) for n in sorted(C.ROOM_NAMES, key=len, reverse=True))
  + r")(?:[\s\-]*\d{1,2}[A-Z]?(?![\d'\"′″\-.xX×]))?(?![A-Z])")
_CLOSE = 0.2

def _clean(p: Polygon) -> Polygon:
  return p.simplify(0.02, preserve_topology=True)

def wall_faces(runs: list, frames: list) -> list:
  
  if not runs:
    return []
  polys = [run_polygon(r, frames[r.peak], extended=True) for r in runs]
  union = unary_union(polys).buffer(_CLOSE, join_style=2).buffer(-_CLOSE, join_style=2)
  parts = list(union.geoms) if hasattr(union, "geoms") else [union]
  out = []
  for part in parts:
    for ring in part.interiors:
      face = Polygon(ring)
      free = face.difference(union)
      for g in (list(free.geoms) if hasattr(free, "geoms") else [free]):
        if isinstance(g, Polygon) and not g.is_empty:
          out.append(g)
  return out

def _norm(name: str) -> str:
  return re.sub(r"\s+", " ", name.strip().strip("-")).strip()

def _without_marks(ln):
  spans, text = [], ""
  for _, _, w in ln.spans:
    if category_of(w.text) is not None:
      continue
  
    if text:
      text += " "
    spans.append((len(text), len(text) + len(w.text), w))
    text += w.text
  return TextLine(text, spans, ln.angle)

def labels(lines: list, hint: str | None) -> tuple:
  names, sizes = [], []
  for ln in (_without_marks(l) for l in lines):
    t = ln.text.upper()
    for m in _NAME.finditer(t):
      x, y = ln.locate(m.start(), m.end())
      names.append((_norm(m.group(0)), x, y))
    for m in _SIZE.finditer(ln.text):
      size = parse_size(m.group(0), hint)
      if size and size[0] >= 600 and size[1] >= 600:
        x, y = ln.locate(m.start(), m.end())
        sizes.append((_norm(m.group(0)), size, x, y))
  return names, sizes

def _inside(pp, poly: Polygon, items: list, ix: int, iy: int) -> list:

  minx, miny, maxx, maxy = poly.bounds
  return [it for it in items if minx <= it[ix] <= maxx and miny <= it[iy] <= maxy and pp.contains(Point(it[ix], it[iy]))]

def describe(poly: Polygon, names: list, sizes: list, mm_per_pt: float) -> dict:
  pp = prep(poly)
  inside_names = _inside(pp, poly, names, 1, 2)
  inside_sizes = _inside(pp, poly, sizes, 2, 3)
  area_m2 = poly.area * mm_per_pt * mm_per_pt / 1e6
  out = {"names": list(dict.fromkeys(n[0] for n in inside_names)), "area_m2": area_m2, "perimeter_m": poly.length * mm_per_pt / 1000.0,
    "holes": len(poly.interiors), "size_text": None, "label_area_m2": None, "deviation_pct": None}
  if inside_sizes:
    t, (a, b), _, _ = inside_sizes[0]
    la = a * b / 1e6
    out.update({"size_text": t, "label_area_m2": la, "deviation_pct": (area_m2 / la - 1.0) * 100.0 if la > 0 else None})
  return out

def ring_json(ring) -> list:
  coords = list(ring.coords)[:-1]
  return [[round(x, 4), round(y, 4)] for x, y in coords]

def polygon_geometry(poly: Polygon) -> dict:
  return {"outer": ring_json(poly.exterior), "holes": [ring_json(r) for r in poly.interiors]}

def outline_rooms(index, names: list, taken: list, mm_per_pt: float, max_m2: float = 120.0) -> list:
  out = []
  k = mm_per_pt * mm_per_pt / 1e6
  seen = set()
  for _, cx, cy in names:
    hit = index.region_at(cx, cy)
    if hit is None:
      continue
  
    ring_i, holes = hit
    r = index.rings[ring_i]
    if ring_i in seen or r.area * k > max_m2 or r.area * k < C.ROOM_MIN_M2:
      continue
    poly = Polygon(r.pts)
    if not poly.is_valid or poly.is_empty:
      continue
    if any(poly.intersection(t).area > 0.5 * min(poly.area, t.area) for t in taken):
      continue
    pp = prep(poly)
    if len(_inside(pp, poly, names, 1, 2)) != 1:
      continue
    seen.add(ring_i)
    out.append(poly)
  return out