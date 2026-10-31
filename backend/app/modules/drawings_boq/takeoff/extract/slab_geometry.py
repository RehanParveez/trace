from __future__ import annotations
import math
import re
from shapely.geometry import Polygon, LineString, MultiLineString, Point, box
from shapely.ops import polygonize, unary_union

INCH_MM = 25.4
BRICK_MIN_MM = 4.5 * INCH_MM
RUN_MIN_REF = 25.0
RUN_CAP = 1500
BIN_REF = 0.25
GAP_MIN_REF = 1.5
GAP_MAX_REF = 30.0
ANGLE_TOL_DEG = 1.0
OVERLAP_MIN_REF = 20.0
PEAK_MIN_PAIRS = 12
WITNESS_SHARE = 0.25
WITNESS_TOL = 0.06
ENV_RUN_MIN_MM = 600.0
CLOSE_FACTOR = 0.6
CLOSE_DEFAULT_MM = 150.0
CLOSE_SWEEP = (0.8, 1.0, 1.25)
PLATEAU_TOL = 0.03
FRAME_SHARE = 0.85
CROSS_ANGLE = (15.0, 75.0)
CROSS_MID_SHARE = 0.05
CROSS_LEN_SHARE = 0.10
VOID_MIN_M2 = 0.25
VOID_MAX_SHARE = 0.25
VOID_WORD = re.compile(r"^(?:VOID|OPENING|SHAFT|DUCT)S?$", re.I)
THICK_NOTE = re.compile(r"(\d+(?:\.\d+)?)?\s*([½¼¾])?\s*(?:\"|”|″|IN\b|INCH(?:ES)?)\s*THICK\s+(?:BRICK|WALL|MASONRY|BLOCK)", re.I)
FRACTION = {"½": 0.5, "¼": 0.25, "¾": 0.75}

def wall_notes(lines: list) -> list:
  out: list = []
  for ln in lines:
    for m in THICK_NOTE.finditer(ln.text):
      inch = float(m.group(1) or 0) + FRACTION.get(m.group(2) or "", 0.0)
      mm = round(inch * INCH_MM, 1)
      if mm > 0 and mm not in out:
        out.append(mm)
  return sorted(out)

def _solid(index, min_len: float) -> list:
  out = []
  for i in range(index.n):
    if index.kinds[i]:
      continue
    x1, y1, x2, y2 = index.seg(i)
    length = math.hypot(x2 - x1, y2 - y1)
    if length >= min_len:
      out.append((x1, y1, x2, y2, length, math.atan2(y2 - y1, x2 - x1) % math.pi))
  return out

def gap_peaks(index, unit: float = 1.0) -> list:
  runs = sorted(_solid(index, RUN_MIN_REF * unit), key=lambda s: -s[4])[:RUN_CAP]
  tol = math.radians(ANGLE_TOL_DEG)
  lo, hi, binw, overlap = GAP_MIN_REF * unit, GAP_MAX_REF * unit, BIN_REF * unit, OVERLAP_MIN_REF * unit
  
  buckets: dict = {}
  for s in runs:
    buckets.setdefault(int(math.degrees(s[5])), []).append(s)
  hist: dict = {}
  def count(s, t):
    da = abs(s[5] - t[5])
    if min(da, math.pi - da) > tol:
      return
    ux, uy = math.cos(s[5]), math.sin(s[5])
    d = abs((t[0] - s[0]) * -uy + (t[1] - s[1]) * ux)
    if d < lo or d > hi:
      return
  
    s0, s1 = sorted((0.0, (s[2] - s[0]) * ux + (s[3] - s[1]) * uy))
    t0, t1 = sorted(((t[0] - s[0]) * ux + (t[1] - s[1]) * uy, (t[2] - s[0]) * ux + (t[3] - s[1]) * uy))
    if min(s1, t1) - max(s0, t0) < overlap:
      return
    k = int(d / binw)
    
    hist[k] = hist.get(k, 0) + 1
  for key, group in buckets.items():
    after = buckets.get((key + 1) % 180, [])
    for i, s in enumerate(group):
      for t in group[i + 1:]:
        count(s, t)
      for t in after:
        count(s, t)
        
  smooth = {k: hist.get(k - 1, 0) + hist.get(k, 0) + hist.get(k + 1, 0) for k in hist}
  peaks = []
  for k, n in smooth.items():
    if n >= PEAK_MIN_PAIRS and n >= smooth.get(k - 1, 0) and n > smooth.get(k + 1, 0):
      w = hist.get(k - 1, 0) + hist.get(k, 0) + hist.get(k + 1, 0)
      centre = sum((j + 0.5) * binw * hist.get(j, 0) for j in (k - 1, k, k + 1)) / max(w, 1)
      peaks.append((round(centre, 3), n))
  return sorted(peaks, key=lambda p: (-p[1], p[0]))

def _near(peaks: list, gap: float, share: float = WITNESS_TOL) -> int:
  return max((n for g, n in peaks if abs(g - gap) <= share * gap), default=0)

def scale_from_walls(notes_mm: list, peaks: list, unit: float = 1.0) -> dict:
  if not notes_mm:
    return {"status": "NO_NOTE"}
  if not peaks:
    return {"status": "NO_WALLS"}
  t = max(notes_mm)
  if t < 2.0 * BRICK_MIN_MM - 0.5:
    return {"status": "NOT_A_FULL_BRICK", "thickness_mm": t}
  gap, pairs = peaks[0]
  
  half, double = _near(peaks, gap / 2.0), _near(peaks, gap * 2.0)
  out = {"thickness_mm": t, "gap_pt": gap, "pairs": pairs, "half_pairs": half, "double_pairs": double}
  if half < WITNESS_SHARE * pairs or double < WITNESS_SHARE * pairs:
    return {"status": "NO_WITNESS", **out}
  return {"status": "FOUND", "mm_per_pt": round(t / gap, 5), **out}

def _diagonal(s) -> bool:
  deg = math.degrees(s[5])
  return CROSS_ANGLE[0] < deg < CROSS_ANGLE[1] or 180.0 - CROSS_ANGLE[1] < deg < 180.0 - CROSS_ANGLE[0]

def _crosses(runs: list) -> list:
  diag = [s for s in runs if _diagonal(s)]
  out, used = [], set()
  for i, s in enumerate(diag):
    if i in used:
      continue
    ms = ((s[0] + s[2]) / 2.0, (s[1] + s[3]) / 2.0)
    for j in range(i + 1, len(diag)):
      t = diag[j]
      if j in used:
        continue
    
      mt = ((t[0] + t[2]) / 2.0, (t[1] + t[3]) / 2.0)
      if math.dist(ms, mt) < CROSS_MID_SHARE * s[4] and abs(s[4] - t[4]) < CROSS_LEN_SHARE * s[4]:
        used.update((i, j))
        xs, ys = [s[0], s[2], t[0], t[2]], [s[1], s[3], t[1], t[3]]
        out.append((min(xs), min(ys), max(xs), max(ys), s, t))
        break
  return out

def _outer_of(geom, page_wh: tuple):
  parts = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
  best = None
  for p in parts:
    x0, y0, x1, y1 = p.bounds
    if (x1 - x0) > FRAME_SHARE * page_wh[0] or (y1 - y0) > FRAME_SHARE * page_wh[1]:
      continue
    filled = Polygon(p.exterior)
    if best is None or filled.area > best.area:
      best = filled
  return best

def _filled(lines: list, r: float, page_wh: tuple):
  u = unary_union([LineString([(s[0], s[1]), (s[2], s[3])]).buffer(r) for s in lines])
  outer = _outer_of(u, page_wh)
  return outer.buffer(-r) if outer is not None else None

def _largest(geom):
  if geom is None or geom.is_empty:
    return None
  if geom.geom_type == "Polygon":
    return geom
  parts = [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon"]
  return max(parts, key=lambda g: g.area) if parts else None

def envelope(index, words: list, mm_per_pt: float, unit: float = 1.0, wall_gap_pt: float | None = None) -> dict | None:
  page_wh = (index.bbox[2] - index.bbox[0], index.bbox[3] - index.bbox[1])
  runs = _solid(index, ENV_RUN_MIN_MM / mm_per_pt)
  if len(runs) < 4:
    return None
  crosses = _crosses(runs)
  crossed = {id(c[4]) for c in crosses} | {id(c[5]) for c in crosses}
  keep = [s for s in runs if id(s) not in crossed]
  base = (CLOSE_FACTOR * wall_gap_pt) if wall_gap_pt else CLOSE_DEFAULT_MM / mm_per_pt
  areas, polys = {}, {}
  for f in CLOSE_SWEEP:
    poly = _largest(_filled(keep, base * f, page_wh))
    if poly is None:
      return None
  
    polys[f], areas[f] = poly, poly.area * mm_per_pt * mm_per_pt / 1e6
  env = polys[1.0]
  spread = (max(areas.values()) - min(areas.values())) / max(areas[1.0], 1e-9)
  voids = []
  faces = None
  for w in words:
    if not VOID_WORD.match(w.text.strip()):
      continue
    pt = Point(w.cx, w.cy)
    shape = None
    
    for c in crosses:
      if c[0] <= w.cx <= c[2] and c[1] <= w.cy <= c[3]:
        shape = box(c[0], c[1], c[2], c[3])
        how = "X_MARK"
        break
    if shape is None:
      if faces is None:
        faces = list(polygonize(unary_union(MultiLineString([[(s[0], s[1]), (s[2], s[3])] for s in keep]))))
      hit = [g for g in faces if g.contains(pt)]
      if hit:
        shape, how = min(hit, key=lambda g: g.area), "CLOSED_FACE"
    if shape is None:
      continue
    inside = shape.intersection(env)
    m2 = inside.area * mm_per_pt * mm_per_pt / 1e6
    if m2 < VOID_MIN_M2 or m2 > VOID_MAX_SHARE * areas[1.0]:
      continue
    if any(v["shape"].intersects(shape) and v["shape"].intersection(shape).area > 0.5 * shape.area for v in voids):
      continue
  
    voids.append({"shape": inside, "how": how, "area_m2": round(m2, 3), "at": [round(w.cx, 1), round(w.cy, 1)]})
  void_union = unary_union([v["shape"] for v in voids]) if voids else None
  net = env.difference(void_union) if void_union is not None else env
  x0, y0, x1, y1 = env.bounds
  
  sides = sorted(((x1 - x0) * mm_per_pt, (y1 - y0) * mm_per_pt), reverse=True)
  return {"gross_m2": round(areas[1.0], 3), "net_m2": round(net.area * mm_per_pt * mm_per_pt / 1e6, 3), "sweep_m2": {f"{f:g}": round(a, 3) for f, a in areas.items()},
    "spread": round(spread, 4), "stable": spread <= PLATEAU_TOL, "bbox_mm": [round(sides[0], 1), round(sides[1], 1)], "close_radius_pt": round(base, 2),
    "voids": [{"how": v["how"], "area_m2": v["area_m2"], "at": v["at"]} for v in voids], "lines": len(keep), "bounds_pt": [round(v, 1) for v in env.bounds]}
