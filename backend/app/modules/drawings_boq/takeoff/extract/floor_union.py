from __future__ import annotations
from dataclasses import dataclass, field
import math
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

ANCHOR_CATEGORIES = ("DOOR", "WINDOW", "COLUMN", "FOOTING", "ROOM")
MIN_INLIERS = 4
MIN_INLIER_SHARE = 0.4
REGISTER_TOL_SHARE = 0.02     
MATCH_TOL_SHARE = 0.03
WALL_COVER_MIN = 0.6
ROOM_COVER_MIN = 0.7
MIN_SCALE, MAX_SCALE = 0.2, 5.0
MAX_CORRESPONDENCES = 90

@dataclass
class Registration:
  z: complex           
  c: complex           
  inliers: int
  anchors_primary: int
  anchors_secondary: int
  rms: float
  tol: float

  @property
  def scale(self) -> float:
    return abs(self.z)

  @property
  def rotation_deg(self) -> int:
    return int(round(math.degrees(math.atan2(self.z.imag, self.z.real)) / 90.0)) * 90 % 360

  def apply(self, p) -> tuple:
    w = self.z * complex(p[0], p[1]) + self.c
    return (w.real, w.imag)

  def brief(self) -> dict:
    return {"inliers": self.inliers, "anchors": [self.anchors_primary, self.anchors_secondary], "scale": round(self.scale, 4),
      "rotation_deg": self.rotation_deg, "rms": round(self.rms, 2)}

@dataclass
class Pair:
  primary: object
  secondary: object
  how: str            
  distance: float = 0.0

@dataclass
class Union:
  registration: Registration | None
  pairs: list = field(default_factory=list)
  only_primary: list = field(default_factory=list)
  only_secondary: list = field(default_factory=list)
  reason: str | None = None     

  @property
  def combined(self) -> bool:
    return self.registration is not None and self.reason is None

def points_of(c) -> list:
  g = c.geometry or {}
  if g.get("outer"):
    return [(float(p[0]), float(p[1])) for p in g["outer"]]
  return [(float(p[0]), float(p[1])) for p in g.get("points") or []]

def centroid(c):
  pts = points_of(c)
  if not pts:
    return None
  return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))

def mark_of(c) -> str | None:
  if c.category == "ROOM":
    name = (c.label or "").split(" · ")[0].strip()
    return name.upper() or None
  return (c.tag or None) and str(c.tag).upper()

def anchors(rows: list) -> list:

  out = []  
  for c in rows:
    if c.category not in ANCHOR_CATEGORIES:
      continue
    m = mark_of(c)
    if not m:
      continue
    if c.category == "ROOM":
      p = centroid(c)
      if p:
        out.append(((c.category, m), p))
    else:
      for p in points_of(c):
        out.append(((c.category, m), p))
  return out

def _extent(pts: list) -> float:
  if len(pts) < 2:
    return 0.0
  xs, ys = [p[0] for p in pts], [p[1] for p in pts]
  return max(max(xs) - min(xs), max(ys) - min(ys))

def _similarity(a1, a2, b1, b2):
  za, zb = complex(a2[0] - a1[0], a2[1] - a1[1]), complex(b2[0] - b1[0], b2[1] - b1[1])
  if abs(za) < 1e-9:
    return None
  z = zb / za
  return z, complex(*b1) - z * complex(*a1)

def _score(z: complex, c: complex, A: list, B: list, tol: float) -> tuple:
  cand = []
  for i, (ka, pa) in enumerate(A):
    w = z * complex(*pa) + c
    for j, (kb, pb) in enumerate(B):
      if ka == kb:
        d = math.hypot(w.real - pb[0], w.imag - pb[1])
        if d <= tol:
          cand.append((d, i, j))
  cand.sort()
  
  ui, uj, got = set(), set(), []
  for d, i, j in cand:
    if i in ui or j in uj:
      continue
    ui.add(i); uj.add(j); got.append((i, j, d))
  return len(got), got

def register(primary: list, secondary: list) -> Registration | None:
  P, S = anchors(primary), anchors(secondary)
  if len(P) < MIN_INLIERS or len(S) < MIN_INLIERS:
    return None
  ext = _extent([p for _, p in P])
  if ext <= 0:
    return None

  tol = max(3.0, REGISTER_TOL_SHARE * ext)
  corr = [(i, j) for i, (ks, _) in enumerate(S) for j, (kp, _) in enumerate(P) if ks == kp]
  if len(corr) < MIN_INLIERS:
    return None
  corr = corr[:MAX_CORRESPONDENCES * 6]
  sep = 0.05 * _extent([p for _, p in S])
  best = (0, None, None)
  seen = set()
  for ai in range(len(corr)):
    for bi in range(ai + 1, len(corr)):
      (i1, j1), (i2, j2) = corr[ai], corr[bi]
      
      if i1 == i2 or j1 == j2:
        continue
      if math.hypot(S[i1][1][0] - S[i2][1][0], S[i1][1][1] - S[i2][1][1]) < max(sep, 1e-6):
        continue
      t = _similarity(S[i1][1], S[i2][1], P[j1][1], P[j2][1])
      if t is None or not MIN_SCALE < abs(t[0]) < MAX_SCALE:
        continue
    
      q = math.atan2(t[0].imag, t[0].real) / (math.pi / 2)
      if abs(q - round(q)) > 0.04:
        continue
      sig = (round(abs(t[0]), 2), round(q), round(t[1].real / max(tol, 1e-6)), round(t[1].imag / max(tol, 1e-6)))
      if sig in seen:
        continue
      seen.add(sig)
      n, _ = _score(t[0], t[1], S, P, tol)
      if n > best[0]:
        best = (n, t[0], t[1])
        
  if best[1] is None or best[0] < MIN_INLIERS:
    return None
  z, c = best[1], best[2]
  for _ in range(2):    
    n, got = _score(z, c, S, P, tol)
    if n < MIN_INLIERS:
      return None
    a = [complex(*S[i][1]) for i, _, _ in got]
    b = [complex(*P[j][1]) for _, j, _ in got]
    am, bm = sum(a) / n, sum(b) / n
    den = sum(abs(x - am) ** 2 for x in a)
    
    if den <= 0:
      return None
    z = sum((y - bm) * (x - am).conjugate() for x, y in zip(a, b)) / den
    q = math.atan2(z.imag, z.real) / (math.pi / 2)
    z = abs(z) * complex(math.cos(round(q) * math.pi / 2), math.sin(round(q) * math.pi / 2))     
    c = bm - z * am
    
  n, got = _score(z, c, S, P, tol)
  if n < MIN_INLIERS or n < MIN_INLIER_SHARE * min(len(S), len(P)):
    return None
  rms = math.sqrt(sum(d * d for _, _, d in got) / n)
  return Registration(z=z, c=c, inliers=n, anchors_primary=len(P), anchors_secondary=len(S), rms=rms, tol=tol)

def _line(points, reg: Registration | None):
  pts = [reg.apply(p) if reg else p for p in points]
  return LineString(pts) if len(pts) >= 2 and len({(round(a, 3), round(b, 3)) for a, b in pts}) >= 2 else None

def _rings(c) -> list | None:
  g = c.geometry or {}
  if not g.get("outer"):
    return None
  return [(float(p[0]), float(p[1])) for p in g["outer"]]

def _iou(a: Polygon, b: Polygon) -> float:
  try:
    u = a.union(b).area
    return a.intersection(b).area / u if u > 0 else 0.0
  except Exception:
    return 0.0

def combine(primary: list, secondary: list, reg: Registration | None = None) -> Union:
  reg = reg or register(primary, secondary)
  if reg is None:
    return Union(None, only_primary=list(primary), only_secondary=list(secondary), reason="NOT_REGISTERED")
  tol = max(reg.tol * 1.5, MATCH_TOL_SHARE * _extent([p for _, p in anchors(primary)]))
  pairs: list = []
  taken: set = set()

  def take(p, s, how, d=0.0):
    taken.add(id(p)); taken.add(id(s))
    pairs.append(Pair(p, s, how, round(d, 3)))

  def free(rows, cat):
    return [c for c in rows if c.category == cat and id(c) not in taken]

  rp, rs = free(primary, "ROOM"), free(secondary, "ROOM")
  cand = []
  for s in rs:
    ring = _rings(s)
    if not ring or len(ring) < 3:
      continue
    ps = Polygon([reg.apply(p) for p in ring]).buffer(0)
    for p in rp:
      rr = _rings(p)
      if rr and len(rr) >= 3:
        cand.append((-_iou(ps, Polygon(rr).buffer(0)), id(s), id(p), s, p))
  for neg, _, _, s, p in sorted(cand, key=lambda t: t[0]):
    if -neg < 0.5 or id(s) in taken or id(p) in taken:
      continue
    take(p, s, "OUTLINES_OVERLAP", 1 + neg)

  rp_all = [(p, Polygon(_rings(p)).buffer(0)) for p in rp if _rings(p) and len(_rings(p)) >= 3]
  for s in rs:
    ring = _rings(s)
    if id(s) in taken or not ring or len(ring) < 3 or not rp_all:
      continue
    ps = Polygon([reg.apply(p) for p in ring]).buffer(0)
    if ps.area <= 0:
      continue
    inter = [(ps.intersection(g).area, p) for p, g in rp_all]
    if sum(a for a, _ in inter) / ps.area >= ROOM_COVER_MIN:
      taken.add(id(s))
      pairs.append(Pair(max(inter, key=lambda t: t[0])[1], s, "OUTLINES_OVERLAP", 0.0))

  sp, ss = free(primary, "STAIR"), free(secondary, "STAIR")
  for s in ss:
    cs = centroid(s)
    left = [p for p in sp if id(p) not in taken and centroid(p)]
    if cs is None or not left:
      continue
    w = reg.apply(cs)
    p = min(left, key=lambda q: math.hypot(w[0] - centroid(q)[0], w[1] - centroid(q)[1]))
    take(p, s, "NEAREST_FLIGHT", math.hypot(w[0] - centroid(p)[0], w[1] - centroid(p)[1]))

  def marked(rows):
    g: dict = {}
    for c in rows:
      if id(c) in taken or c.category == "STAIR":
        continue
      m = mark_of(c)
      if c.category == "WALL" and not c.tag:
        continue
      if m:
        g.setdefault((c.category, m), []).append(c)
    return g

  gp, gs = marked(primary), marked(secondary)
  for key, srows in gs.items():
    prows = gp.get(key) or []
    if not prows:
      continue
    if len(prows) == 1 and len(srows) == 1:
      take(prows[0], srows[0], "MARK")
      continue
  
    cand = []
    for s in srows:
      cs = centroid(s)
      if cs is None:
        continue
      w = reg.apply(cs)
      for p in prows:
        cp = centroid(p)
        if cp is not None:
          d = math.hypot(w[0] - cp[0], w[1] - cp[1])
          if d <= tol:
            cand.append((d, id(s), id(p), s, p))
            
    for d, _, _, s, p in sorted(cand, key=lambda t: t[0]):
      if id(s) not in taken and id(p) not in taken:
        take(p, s, "MARK_AND_PLACE", d)

  pw = [(p, _line(points_of(p), None)) for p in primary if p.category == "WALL" and not p.tag]
  pw = [(p, ln) for p, ln in pw if ln is not None]
  if pw:
    zone = unary_union([ln.buffer(max(tol * 0.5, 2.0)) for _, ln in pw])
    for s in secondary:
      if s.category != "WALL" or s.tag or id(s) in taken:
        continue
      ln = _line(points_of(s), reg)
      if ln is None or ln.length <= 0:
        continue
      share = ln.intersection(zone).length / ln.length
      if share >= WALL_COVER_MIN:
        near = min(pw, key=lambda t: t[1].distance(ln.interpolate(0.5, normalized=True)))[0]
        taken.add(id(s))
        pairs.append(Pair(near, s, "ALONG_WALL", round(1.0 - share, 3)))

  for s in secondary:
    if id(s) in taken or s.category in ("ROOM", "STAIR", "WALL") or mark_of(s):
      continue
    cs = centroid(s)
    if cs is None:
      continue
    w = reg.apply(cs)
    best = None
    for p in primary:
      if id(p) in taken or p.category != s.category or mark_of(p) or centroid(p) is None:
        continue
      d = math.hypot(w[0] - centroid(p)[0], w[1] - centroid(p)[1])
      if d <= tol and (best is None or d < best[0]):
        best = (d, p)
        
    if best:
      take(best[1], s, "PLACE", best[0])
  paired_p = {id(p.primary) for p in pairs if p.how != "ALONG_WALL"}
  return Union(reg, pairs=pairs,
    only_primary=[c for c in primary if id(c) not in paired_p],
    only_secondary=[c for c in secondary if id(c) not in taken])

def counts_differ(u: Union) -> list:
  out = []
  for p in u.pairs:
    if p.how in ("MARK", "MARK_AND_PLACE") and p.primary.category in ("DOOR", "WINDOW", "LINTEL", "COLUMN", "FOOTING"):
      a, b = int(getattr(p.primary, "count", 1) or 1), int(getattr(p.secondary, "count", 1) or 1)
      if a != b:
        out.append((p.primary, p.secondary))
  return out

def summary(u: Union) -> dict:
  by: dict = {}
  for p in u.pairs:
    by[p.secondary.category] = by.get(p.secondary.category, 0) + 1
  return {"combined": u.combined, "reason": u.reason, "registration": u.registration.brief() if u.registration else None,
    "same": len(u.pairs), "same_by_category": by, "only_primary": len(u.only_primary), "only_secondary": len(u.only_secondary),
    "only_secondary_by_category": _count(u.only_secondary)}

def _count(rows: list) -> dict:
  out: dict = {}
  for c in rows:
    out[c.category] = out.get(c.category, 0) + 1
  return out
