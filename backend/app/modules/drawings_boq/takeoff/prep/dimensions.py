from __future__ import annotations
import math
from dataclasses import dataclass, field
import time
from app.modules.drawings_boq.takeoff.prep.spatial import VectorIndex
from app.modules.drawings_boq.takeoff.prep.extract import _rect_like
from app.modules.drawings_boq.takeoff.prep.texts import parse_dimension

PT_MM = 25.4 / 72.0
PARALLEL_SIN = math.sin(math.radians(1.0))
PERP_SIN = math.sin(math.radians(3.0))
MIN_DIM_PT = 8.0
MAX_WORDS_TRIED = 4000
RATIO_TOL = 0.015
MIN_RATIO, MAX_RATIO = 0.2, 5000.0

@dataclass
class Pair:
  text: str
  cx: float
  cy: float
  angle: float                 
  p1: tuple
  p2: tuple
  length_pt: float
  readings: list
  quality: float
  ends: str
  size: float
  key: tuple = field(default=())

def _markers(index: VectorIndex, w, ux: float, uy: float, nx: float, ny: float, off: float, lo: float, hi: float, h: float) -> list[dict]:
  def sc(x, y):
    return (x - w.cx) * ux + (y - w.cy) * uy

  def pc(x, y):
    return (x - w.cx) * nx + (y - w.cy) * ny - off

  p_lo = (w.cx + ux * lo + nx * off, w.cy + uy * lo + ny * off)
  p_hi = (w.cx + ux * hi + nx * off, w.cy + uy * hi + ny * off)
  pad = 3.0 + 3.0 * h
  x0, x1 = min(p_lo[0], p_hi[0]) - pad, max(p_lo[0], p_hi[0]) + pad
  y0, y1 = min(p_lo[1], p_hi[1]) - pad, max(p_lo[1], p_hi[1]) + pad
  found: list = []
  for j in index._candidates(x0, y0, x1, y1):
    if index.kinds[j]:
      continue
  
    a, b, c, d = index.seg(j)
    lj = math.hypot(c - a, d - b)
    if lj < 1.2:
      continue
    vx, vy = (c - a) / lj, (d - b) / lj
    cosang = abs(vx * ux + vy * uy)
    if cosang > 0.94:
      continue
  
    da, dc = pc(a, b), pc(c, d)
    if min(da, dc) > 0.9 or max(da, dc) < -0.9:
      continue
    sa, scc = sc(a, b), sc(c, d)
    if abs(dc - da) < 1e-9:
      s_x = (sa + scc) / 2.0
    else:
      t = max(0.0, min(1.0, (0.0 - da) / (dc - da)))
      s_x = sa + t * (scc - sa)
    if s_x < lo - 3.0 or s_x > hi + 3.0:
      continue
  
    if cosang <= PERP_SIN:
      if lj >= 1.5:
        found.append((((sa + scc) / 2.0), "ext"))
    elif cosang >= 0.25 and lj <= max(4.0 * h, 12.0):
      found.append((s_x, "tick"))
  mx, my = (p_lo[0] + p_hi[0]) / 2.0, (p_lo[1] + p_hi[1]) / 2.0
  half = math.hypot(p_hi[0] - p_lo[0], p_hi[1] - p_lo[1]) / 2.0
  for ring in index.small_rings_near(mx, my, half + 8.0 + 3.0 * h):
    n = len(ring.pts)
    if not ring.fill or n < 3 or n > 5:
      continue
  
    if n == 4 and _rect_like(ring.pts):
      continue
    span = max(ring.bbox[2] - ring.bbox[0], ring.bbox[3] - ring.bbox[1])
    if span > max(7.0 * h, 16.0):
      continue
  
    gx, gy = (ring.bbox[0] + ring.bbox[2]) / 2.0, (ring.bbox[1] + ring.bbox[3]) / 2.0
    if abs(pc(gx, gy)) > span * 0.6 + 0.9:
      continue
    ss = [sc(px, py) for px, py in ring.pts]
    s_c = sc(gx, gy)
    if s_c < lo - 4.0 or s_c > hi + 4.0:
      continue
  
    mean_s = sum(ss) / len(ss)
    found.append((max(ss, key=lambda v: abs(v - mean_s)), "arrow"))
  found.sort()
  merged: list[dict] = []
  for s_pos, kind in found:
    if merged and s_pos - merged[-1]["last"] <= 2.5:
      m = merged[-1]
    else:
      m = {"ext": None, "pos": [], "tick": False, "arrow": False, "last": s_pos}
      merged.append(m)
    m["last"] = s_pos
    m["pos"].append(s_pos)
    if kind == "ext":
      m["ext"] = s_pos if m["ext"] is None else m["ext"]
    elif kind == "tick":
      m["tick"] = True
    else:
      m["arrow"] = True
  out = []
  for m in merged:
    s = m["ext"] if m["ext"] is not None else sum(m["pos"]) / len(m["pos"])
    q = (0.6 if m["ext"] is not None else 0.0) + ((0.4 if m["ext"] is not None else 0.5) if (m["tick"] or m["arrow"]) else 0.0)
    out.append({"s": s, "has_ext": m["ext"] is not None, "tick": m["tick"], "arrow": m["arrow"], "q": min(q, 1.0)})
  return out

def find_pairs(index: VectorIndex, words: list, hint: str | None, deadline: float | None = None) -> list[Pair]:
  
  pairs: dict = {}
  tried = 0
  numeric = []
  for w in words:
    if w.size <= 0.4 or w.length <= 0.5:
      continue
    readings = parse_dimension(w.text, hint)
    if readings:
      numeric.append((w, readings))
  numeric.sort(key=lambda t: -t[0].size)
  for w, readings in numeric:
    tried += 1
    if tried > MAX_WORDS_TRIED or (deadline is not None and time.monotonic() > deadline):
      break
    th = math.radians(w.angle)
    ux, uy = math.cos(th), math.sin(th)
    nx, ny = -uy, ux
    h = max(w.height, 0.6 * w.size)
    tw = w.length
    off_max = 2.4 * h + 1.0
    reach = 0.5 * tw + max(14.0 * h, 60.0)
    groups: dict = {}
    for i in index._candidates(w.cx - reach, w.cy - reach, w.cx + reach, w.cy + reach):
      if index.kinds[i]:
        continue
      a, b, c, d = index.seg(i)
      length = math.hypot(c - a, d - b)
      if length < 3.0:
        continue
      vx, vy = (c - a) / length, (d - b) / length
      if abs(ux * vy - uy * vx) > PARALLEL_SIN:
        continue
      oa = (a - w.cx) * nx + (b - w.cy) * ny
      oc = (c - w.cx) * nx + (d - w.cy) * ny
      if abs(oa - oc) > 0.3:
        continue
      off = (oa + oc) / 2.0
      if abs(off) > off_max:
        continue
    
      s1 = (a - w.cx) * ux + (b - w.cy) * uy
      s2 = (c - w.cx) * ux + (d - w.cy) * uy
      groups.setdefault(round(off / 0.4), []).append((min(s1, s2), max(s1, s2), off))
    best = None
    for frags in groups.values():
      frags.sort()
      off = sum(f[2] for f in frags) / len(frags)
      intervals = []
      cur = [frags[0][0], frags[0][1]]
      for lo, hi, _ in frags[1:]:
        gap = lo - cur[1]
        if gap <= 0.8:
          cur[1] = max(cur[1], hi)
        elif gap <= tw + 8.0 * h and cur[1] <= 0.35 * tw + 1.5 and lo >= -0.35 * tw - 1.5:
          cur[1] = max(cur[1], hi)
        else:
          intervals.append(cur)
          cur = [lo, hi]
      intervals.append(cur)
      for lo, hi in intervals:
        if not (lo < -1.0 and hi > 1.0):
          continue
        markers = _markers(index, w, ux, uy, nx, ny, off, lo, hi, h)
        left = [m for m in markers if m["s"] < -1.0 and m["q"] >= 0.5]
        right = [m for m in markers if m["s"] > 1.0 and m["q"] >= 0.5]
        if not left or not right:
          continue
      
        ml, mr = max(left, key=lambda m: m["s"]), min(right, key=lambda m: m["s"])
        length = mr["s"] - ml["s"]
        if length < MIN_DIM_PT or abs((ml["s"] + mr["s"]) / 2.0) > 0.45 * length + 0.5 * tw:
          continue
        q = (ml["q"] + mr["q"]) / 2.0
        if not (ml["has_ext"] or mr["has_ext"]):
          q = min(q, 0.6)
        tick = ml["tick"] and mr["tick"]
        arrow = ml["arrow"] and mr["arrow"]
        label = "EXT" if (ml["has_ext"] and mr["has_ext"]) else "EXT/LINE" if (ml["has_ext"] or mr["has_ext"]) else "LINE"
        label += "+TICK" if tick else "+ARROW" if arrow else ""
        cand = (q, -abs(off), length, off, ml["s"], mr["s"], label)
        if best is None or cand[:3] > best[:3]:
          best = cand
          
    if best is None:
      continue
    q, _, length, off, sa, sb, label = best
    p1 = (w.cx + ux * sa + nx * off, w.cy + uy * sa + ny * off)
    p2 = (w.cx + ux * sb + nx * off, w.cy + uy * sb + ny * off)
    key = (round(min(p1[0], p2[0]) / 0.6), round(min(p1[1], p2[1]) / 0.6), round(max(p1[0], p2[0]) / 0.6), round(max(p1[1], p2[1]) / 0.6))
    hit = pairs.get(key)
    ang = w.angle % 180.0
    if hit is None:
      pairs[key] = Pair(text=w.text, cx=w.cx, cy=w.cy, angle=ang, p1=p1, p2=p2, length_pt=length, readings=list(readings),
        quality=q, ends=label, size=w.size, key=key)
    else:
      hit.readings.extend(readings)
      hit.text = hit.text + " | " + w.text
      hit.quality = max(hit.quality, q)
  return list(pairs.values())

@dataclass
class Cluster:
  ratio: float
  support: int
  weight: float
  spread_pct: float
  members: list            
  total_pairs: int

def _weighted_median(items: list) -> float:
  items = sorted(items)
  total = sum(w for _, w in items)
  acc = 0.0
  for v, w in items:
    acc += w
    if acc >= total / 2.0:
      return v
  return items[-1][0]

def consensus(pairs: list[Pair], user_unit: float = 1.0, tol: float = RATIO_TOL, max_clusters: int = 3) -> list[Cluster]:

  entries = []
  for i, p in enumerate(pairs):
    lw = max(0.25, min(1.0, (p.length_pt / 150.0) ** 0.5))
    for j, rd in enumerate(p.readings):
      r = rd.value_mm / (p.length_pt * PT_MM * user_unit)
      
      if MIN_RATIO <= r <= MAX_RATIO:
        entries.append((r, p.quality * rd.prior * lw, i, j))
  if len(entries) > 800:
    entries = sorted(entries, key=lambda e: -e[1])[:800]
  clusters: list[Cluster] = []
  used: set = set()
  total_pairs = len(pairs)
  while len(clusters) < max_clusters:
    avail = sorted((e for e in entries if e[2] not in used), key=lambda e: e[0])
    
    if not avail:
      break
    best = None
    n = len(avail)
    for left in range(n):
      hi = avail[left][0] * (1.0 + 2.0 * tol)
      per_pair: dict = {}
      
      k = left
      while k < n and avail[k][0] <= hi:
        r, wgt, i, j = avail[k]
        if i not in per_pair or wgt > per_pair[i][0]:
          per_pair[i] = (wgt, r, j)
        k += 1
      score = sum(v[0] for v in per_pair.values())
      cand = (score, len(per_pair), left)
      if best is None or cand > best[0]:
        best = (cand, per_pair)
    if best is None or best[0][1] < 2:
      break
    per_pair = best[1]
    center = _weighted_median([(v[1], v[0]) for v in per_pair.values()])
    members = {}
    for r, wgt, i, j in avail:
      if abs(r / center - 1.0) <= tol and (i not in members or wgt > members[i][0]):
        members[i] = (wgt, j, r)
        
    if len(members) < 2:
      break
    center = _weighted_median([(v[2], v[0]) for v in members.values()])
    tw = sum(v[0] for v in members.values())
    mean = sum(v[2] * v[0] for v in members.values()) / tw
    var = sum(v[0] * (v[2] - mean) ** 2 for v in members.values()) / tw
    clusters.append(Cluster(ratio=center, support=len(members), weight=tw, spread_pct=100.0 * math.sqrt(var) / mean,
      members=[(i, v[1]) for i, v in sorted(members.items())], total_pairs=total_pairs))
    used.update(members.keys())
  return clusters
