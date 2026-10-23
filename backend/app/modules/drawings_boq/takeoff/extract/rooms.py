from __future__ import annotations
import re
import math
from app.modules.drawings_boq.takeoff.prep.texts import TextLine, parse_dimension
from app.modules.drawings_boq.takeoff.extract import config as C
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from app.modules.drawings_boq.takeoff.extract.members import _SIZE, category_of, parse_size
from shapely.prepared import prep
from app.modules.drawings_boq.takeoff.extract.walls import run_polygon
from app.modules.drawings_boq.takeoff.extract import geo_safe as GS

_QUAL = r"(?:MASTER|ATTACHED|COMMON|MAIN|SERVANT|FRONT|REAR|UPPER|LOWER|GUEST|KIDS|GIRLS|BOYS)\s+"
_NAME = re.compile(r"(?<![A-Z0-9])(?:" + _QUAL + r")?(?:" + "|".join(re.escape(n) for n in sorted(C.ROOM_NAMES, key=len, reverse=True))
  + r")(?:[\s\-]*\d{1,2}[A-Z]?(?![\d'\"′″\-.xX×½¼¾])(?!\s+\d\s+\d))?(?P<post>\s+(?:MASTER|GUEST|KIDS|GIRLS|BOYS|SERVANT|COMMON)(?![A-Z]))?(?![A-Z])")
_QUAL_ALONE = ("MASTER", "GUEST", "KIDS", "GIRLS", "BOYS", "COMMON", "ATTACHED")
_HEIGHT_NOTE = re.compile(r"\s*(?:LOBBY\s+)?(?:HEIGHT|HT\b)")           
_JOIN = re.compile(r"\s*(?:/|&|\bAND\b)\s*")                      

def _name_of(m) -> str:
  text = m.group(0)
  post = m.group("post")
  if post:
    text = post.strip() + " " + text[:m.start("post") - m.start()]
  return _norm(text)

_NOTE_DIM = re.compile(r"\b(?:CH|HT)\s*=\s*\d+\s*['′]\s*-?\s*\d*\s*[½¼¾]?\s*[\"″”]?", re.I)
_OPENING_LABEL = re.compile(r"[WD]\s*=\s*$")                       
_AROUND_TAIL = re.compile(r"(\d+\s*['′]\s*-?\s*\d*\s*[½¼¾]?\s*[\"″”]?)\s*$")
_CROSS_TAIL = re.compile(r"(\d+\s*['′]\s*-?\s*\d*\s*[½¼¾]?\s*[\"″”]?)\s*[xX×]\s*$")
_CROSS_HEAD = re.compile(r"^\s*(\d+\s*['′]?\s*-?\s*\d*\s*[½¼¾]?\s*[\"″”]?)")
_AROUND_HEAD = re.compile(r"^\s*[xX×]\s*(\d+\s*['′]?\s*-?\s*\d*\s*[½¼¾]?\s*[\"″”]?)")
_CLOSE = 0.2

def _clean(p: Polygon) -> Polygon:
  return p.simplify(0.02, preserve_topology=True)

def wall_faces(runs: list, frames: list, stats: dict | None = None) -> list:
  st = stats if stats is not None else {}
  st.setdefault("repaired", 0)
  st.setdefault("dropped", 0)
  if not runs:
    return []
  
  polys = [run_polygon(r, frames[r.peak], extended=True) for r in runs]
  union = unary_union(polys).buffer(_CLOSE, join_style=2).buffer(-_CLOSE, join_style=2)
  parts = list(union.geoms) if hasattr(union, "geoms") else [union]
  out = []
  for part in parts:
    for ring in part.interiors:
      face = Polygon(ring)
      free, how = GS.safe_difference(face, union)
      if free is None:
        st["dropped"] += 1
        continue
      
      if how != GS.PLAIN:
        st["repaired"] += 1
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

_X_START = re.compile(r"^\s*[xX×]\s*\d")
_X_END = re.compile(r"\d[\"'″”′½¼¾]?\s*[xX×]\s*$")

def merge_split_sizes(lines: list) -> list:
  out = list(lines)
  for l2 in lines:
    if l2.angle != 0 or not l2.spans:
      continue
    starts_x, ends_x = bool(_X_START.match(l2.text)), bool(_X_END.search(l2.text.strip()))
    if not starts_x and not ends_x:
      continue
    size = max(w.size for _, _, w in l2.spans) or 1.0
    x2, y2 = l2.locate(0, len(l2.text))
    best = None
    
    for l1 in lines:
      if l1 is l2 or l1.angle != 0 or not l1.spans:
        continue
      if starts_x and not parse_dimension(l1.text.strip()):
        continue
      if ends_x and not starts_x and not parse_dimension(l1.text.strip()):
        continue
    
      x1, y1 = l1.locate(0, len(l1.text))
      dy = abs(y1 - y2)
      reach = max(len(l1.text), len(l2.text)) * size * 0.6 + size
      if 0.3 * size <= dy <= 2.6 * size and abs(x1 - x2) <= reach and (best is None or dy < best[0]):
        best = (dy, l1)
    if best is None:
      continue
    l1 = best[1]
    
    first, second = (l1, l2) if starts_x else (l2, l1)
    ft, st = first.text.strip(), second.text.strip()
    shift = len(ft)
    spans = [(a, b, w) for a, b, w in first.spans if a < shift] + [(a + shift, b + shift, w) for a, b, w in second.spans]
    out.append(TextLine(ft + st, spans, 0))
  return out


def labels(lines: list, hint: str | None) -> tuple:
  names, sizes = [], []
  quals, name_size = [], []
  for ln in merge_split_sizes([_without_marks(l) for l in lines]):
    t = ln.text.upper()
    found = [m for m in _NAME.finditer(t) if not _HEIGHT_NOTE.match(t, m.end())]
    joined = []
    
    for m in found:
      if joined and _JOIN.fullmatch(t[joined[-1][1]:m.start()]):
        joined[-1] = (joined[-1][0] + " / " + _name_of(m), m.end(), joined[-1][2])
      else:
        joined.append((_name_of(m), m.end(), m.start()))
    for nm, end, start in joined:
      x, y = ln.locate(start, end)
      names.append((nm, x, y))
      name_size.append(max((w.size for _, _, w in ln.spans), default=1.0) or 1.0)
    if t.strip() in _QUAL_ALONE:
      x, y = ln.locate(0, len(ln.text))
      quals.append((t.strip(), x, y, max((w.size for _, _, w in ln.spans), default=1.0) or 1.0))
    stext = _NOTE_DIM.sub(lambda m: " " * len(m.group(0)), ln.text)
    for m in _SIZE.finditer(stext):
      if _OPENING_LABEL.search(ln.text[:m.start()].upper()):
        continue
      
      size = parse_size(m.group(0), hint)
      if size and size[0] >= 600 and size[1] >= 600:
        x, y = ln.locate(m.start(), m.end())
        sizes.append((_norm(m.group(0)), size, x, y))
        
    for m in _NAME.finditer(t):                                  
      tail, head = _AROUND_TAIL.search(ln.text[:m.start()]), _AROUND_HEAD.match(ln.text[m.end():])
      if tail is None or head is None:
        tail, head = _CROSS_TAIL.search(ln.text[:m.start()]), _CROSS_HEAD.match(ln.text[m.end():])
        if tail is None or head is None:
          continue
      text = f"{tail.group(1).strip()} x {head.group(1).strip()}"
      size = parse_size(text, hint)
      if size and size[0] >= 600 and size[1] >= 600:
        x, y = ln.locate(m.start(), m.end())
        sizes.append((_norm(text), size, x, y))
        
  cand = []
  for i, (nm, nx, ny) in enumerate(names):
    if nm.split(" ")[0] in _QUAL_ALONE:
      continue
    for j, (q, qx, qy, qs) in enumerate(quals):
      dy = abs(qy - ny)
      if 0.3 * qs <= dy <= 2.6 * qs and abs(qx - nx) <= max(len(nm), len(q)) * qs * 0.6 + qs:
        cand.append((dy, i, j))
  cand.sort()
  used_n, used_q = set(), set()
  for _, i, j in cand:
    if i in used_n or j in used_q:
      continue
    used_n.add(i)
    used_q.add(j)
    names[i] = (quals[j][0] + " " + names[i][0], names[i][1], names[i][2])
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

LABEL_REACH_MM = 2600.0
LABEL_ROOM_MIN_M2 = 2.4
_SMALL_ROOMS = ("W.C", "WC", "W/C", "BATH", "TOILET", "LAVATORY", "STORE", "PANTRY", "LOBBY", "WARDROBE", "DRESSING", "LIFT", "STAIR")

def pair_labels(names: list, sizes: list, mm_per_pt: float) -> list:
  reach = LABEL_REACH_MM / mm_per_pt
  cand = []
  for ni, (_, nx, ny) in enumerate(names):
    for si, (_, _, sx, sy) in enumerate(sizes):
      d = math.hypot(nx - sx, ny - sy)
      if d <= reach:
        cand.append((d, ni, si))
        
  cand.sort()
  used_n, used_s, out = set(), set(), []
  for _, ni, si in cand:
    if ni in used_n or si in used_s:
      continue
    used_n.add(ni)
    used_s.add(si)
    nm, nx, ny = names[ni]
    st, (a, b), sx, sy = sizes[si]
    out.append({"name": nm, "size_text": st, "a_mm": float(a), "b_mm": float(b), "x": (nx + sx) / 2.0, "y": (ny + sy) / 2.0,
      "sx": sx, "sy": sy})
  return out

def plausible_room(pair: dict) -> bool:

  a, b = pair["a_mm"], pair["b_mm"]
  area = a * b / 1e6
  small = any(t in pair["name"] for t in _SMALL_ROOMS)
  if area > C.ROOM_MAX_M2 or area < (C.ROOM_MIN_M2 if small else LABEL_ROOM_MIN_M2):
    return False
  return min(a, b) >= 900.0

def pairs_inside(poly: Polygon, pairs: list) -> list:
  pp = prep(poly)
  minx, miny, maxx, maxy = poly.bounds
  return [i for i, p in enumerate(pairs) if minx <= p["sx"] <= maxx and miny <= p["sy"] <= maxy and pp.contains(Point(p["sx"], p["sy"]))]

def label_polygon(pair: dict, mm_per_pt: float) -> Polygon:
  w, h = pair["a_mm"] / mm_per_pt, pair["b_mm"] / mm_per_pt
  cx, cy = pair["x"], pair["y"]
  return Polygon([(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)])