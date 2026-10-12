from __future__ import annotations
from dataclasses import dataclass, field
import time
import numpy as np
import math
from app.modules.drawings_boq.takeoff.extract import config as C
from shapely.geometry import Polygon, box
from shapely.strtree import STRtree

OFFSET_TOL_PT = 0.35      
MERGE_GAP_PT = 0.8        
PEAK_CLAIM_DEG = 0.6
JUNCTION_TOL_PT = 1.5
MAX_FACE_SPAN_PT = 1.0
MIN_SEG_PT = 0.5

@dataclass
class Frame:
  ux: float
  uy: float

  @property
  def nx(self) -> float:
    return -self.uy

  @property
  def ny(self) -> float:
    return self.ux

  def pt(self, s: float, d: float) -> tuple:
    return (s * self.ux + d * self.nx, s * self.uy + d * self.ny)

  def s_of(self, x: float, y: float) -> float:
    return x * self.ux + y * self.uy

  def d_of(self, x: float, y: float) -> float:
    return x * self.nx + y * self.ny

@dataclass
class Face:
  peak: int
  d: float
  s0: float
  s1: float

@dataclass
class Piece:
  peak: int
  d0: float
  d1: float
  s0: float
  s1: float

  @property
  def t(self) -> float:
    return self.d1 - self.d0

  @property
  def dc(self) -> float:
    return (self.d0 + self.d1) / 2.0

@dataclass
class Run:
  peak: int
  dc: float
  t_pt: float
  s0: float
  s1: float
  clear_pt: float
  pieces: int
  gaps: list = field(default_factory=list)
  ext0: float = 0.0
  ext1: float = 0.0
  end0: str = "FREE"
  end1: str = "FREE"
  overlap_pt: float = 0.0

class TimeLimit(Exception):
  pass

def _check(deadline: float | None) -> None:
  if deadline is not None and time.monotonic() > deadline:
    raise TimeLimit()

def angle_peaks(theta_deg: np.ndarray, weight: np.ndarray, max_peaks: int = 12, min_share: float = 0.01) -> list[float]:
  if theta_deg.size == 0:
    return []
  hist = np.bincount((theta_deg * 10).astype(np.int64) % 1800, weights=weight, minlength=1800).astype(np.float64)
  total = float(hist.sum())
  work = hist.copy()
  peaks: list[float] = []
  kernel = np.ones(11)
  
  for _ in range(max_peaks):
    padded = np.concatenate([work[-5:], work, work[:5]])
    smooth = np.convolve(padded, kernel, mode="valid")
    k = int(smooth.argmax())
    if smooth[k] < min_share * total:
      break
    bins = [(k + j) % 1800 for j in range(-6, 7)]
    w = np.array([hist[b] for b in bins])
    if w.sum() <= 0:
      break
    centres = np.array([((k + j) + 0.5) / 10.0 for j in range(-6, 7)])
    peaks.append(float((centres * w).sum() / w.sum()) % 180.0)
    for b in bins:
      work[b] = 0.0
  return peaks

def collect_faces(index, mm_per_pt: float, deadline: float | None = None) -> tuple[list[Frame], list[Face]]:
  if len(index.kinds) == 0:
    return [], []
  segs = np.frombuffer(index.segs, dtype=np.float32).reshape(-1, 5)[:, :4].astype(np.float64)
  kinds = np.frombuffer(index.kinds, dtype=np.uint8)
  dx, dy = segs[:, 2] - segs[:, 0], segs[:, 3] - segs[:, 1]
  ln = np.hypot(dx, dy)
  keep = (kinds == 0) & (ln >= MIN_SEG_PT)
  if not keep.any():
    return [], []
  segs, dx, dy, ln = segs[keep], dx[keep], dy[keep], ln[keep]
  theta = np.degrees(np.arctan2(dy, dx)) % 180.0
  peaks = angle_peaks(theta, ln)
  
  if not peaks:
    return [], []
  pk = np.array(peaks)
  diff = np.abs(((theta[:, None] - pk[None, :]) + 90.0) % 180.0 - 90.0)
  nearest = diff.argmin(axis=1)
  ok = diff[np.arange(len(theta)), nearest] <= PEAK_CLAIM_DEG
  frames = [Frame(math.cos(math.radians(a)), math.sin(math.radians(a))) for a in peaks]
  min_face = max(2.0, C.WALL_MIN_FACE_MM / mm_per_pt)
  faces: list[Face] = []
  for pi, fr in enumerate(frames):
    _check(deadline)
    sel = ok & (nearest == pi)
    if not sel.any():
      continue
  
    s = segs[sel]
    sa = s[:, 0] * fr.ux + s[:, 1] * fr.uy
    sb = s[:, 2] * fr.ux + s[:, 3] * fr.uy
    lo, hi = np.minimum(sa, sb), np.maximum(sa, sb)
    d = ((s[:, 0] + s[:, 2]) / 2.0) * fr.nx + ((s[:, 1] + s[:, 3]) / 2.0) * fr.ny
    order = np.argsort(d, kind="stable")
    d, lo, hi = d[order], lo[order], hi[order]
    start = 0
    n = len(d)
    i = 1
    clusters = []
    
    while i <= n:
      if i == n or d[i] - d[i - 1] > OFFSET_TOL_PT or d[i] - d[start] > MAX_FACE_SPAN_PT:
        clusters.append((start, i))
        start = i
      i += 1
    for a, b in clusters:
      dm = float(d[a:b].mean())
      segs_ = sorted(zip(lo[a:b].tolist(), hi[a:b].tolist()))
      cur0, cur1 = segs_[0]
      for l0, l1 in segs_[1:]:
        if l0 <= cur1 + MERGE_GAP_PT:
          cur1 = max(cur1, l1)
        else:
          if cur1 - cur0 >= min_face:
            faces.append(Face(pi, dm, cur0, cur1))
          cur0, cur1 = l0, l1
      if cur1 - cur0 >= min_face:
        faces.append(Face(pi, dm, cur0, cur1))
  return frames, faces

def _standard(t_mm: float) -> bool:
  return any(abs(t_mm / s - 1.0) <= C.STANDARD_TOL for s in C.STANDARD_WALLS_MM)

def pair_faces(faces: list[Face], mm_per_pt: float, deadline: float | None = None) -> list[Piece]:
  t_min, t_max = C.WALL_T_MIN_MM / mm_per_pt, C.WALL_T_MAX_MM / mm_per_pt
  min_overlap = C.WALL_MIN_OVERLAP_MM / mm_per_pt
  by_peak: dict = {}
  for i, fc in enumerate(faces):
    by_peak.setdefault(fc.peak, []).append(i)
  cands = []
  
  for peak, ids in by_peak.items():
    ids.sort(key=lambda i: faces[i].d)
    for a in range(len(ids)):
      _check(deadline)
      fa = faces[ids[a]]
      
      for b in range(a + 1, len(ids)):
        fb = faces[ids[b]]
        gap = fb.d - fa.d
        if gap > t_max:
          break
        if gap < t_min:
          continue
        o0, o1 = max(fa.s0, fb.s0), min(fa.s1, fb.s1)
        
        if o1 - o0 < min_overlap:
          continue
        t_mm = gap * mm_per_pt
        score = (o1 - o0) * (1.5 if _standard(t_mm) else 1.0)
        cands.append((score, ids[a], ids[b], o0, o1))
  cands.sort(key=lambda c: -c[0])
  claimed: dict = {}

  def free_fraction(fi: int, a: float, b: float) -> float:
    used = 0.0
    for u0, u1 in claimed.get(fi, ()):
      used += max(0.0, min(b, u1) - max(a, u0))
    return 1.0 - used / max(b - a, 1e-9)

  pieces: list[Piece] = []
  for score, ia, ib, o0, o1 in cands:
    if free_fraction(ia, o0, o1) < 0.6 or free_fraction(ib, o0, o1) < 0.6:
      continue
    claimed.setdefault(ia, []).append((o0, o1))
    claimed.setdefault(ib, []).append((o0, o1))
    fa, fb = faces[ia], faces[ib]
    pieces.append(Piece(fa.peak, fa.d, fb.d, o0, o1))
  return pieces

def _piece_polygon(p: Piece, fr: Frame) -> Polygon:
  return Polygon([fr.pt(p.s0, p.d0), fr.pt(p.s1, p.d0), fr.pt(p.s1, p.d1), fr.pt(p.s0, p.d1)])

def join_runs(pieces: list[Piece], frames: list[Frame], mm_per_pt: float, deadline: float | None = None) -> list[Run]:
  if not pieces:
    return []
  gap_max = C.WALL_GAP_MAX_MM / mm_per_pt
  polys = [_piece_polygon(p, frames[p.peak]) for p in pieces]
  tree = STRtree(polys)

  def bridge_kind(peak: int, dc: float, a: float, b: float, t_pt: float) -> str:
    
    fr = frames[peak]
    band = Polygon([fr.pt(a + 0.3, dc - 0.25), fr.pt(b - 0.3, dc - 0.25), fr.pt(b - 0.3, dc + 0.25), fr.pt(a + 0.3, dc + 0.25)])
    join_t = 0.0
    for j in tree.query(band.buffer(t_pt / 2.0 + 1.5)):
      j = int(j)
      if pieces[j].peak == peak:
        continue
      if polys[j].intersects(band):
        return "BLOCKED"
      if polys[j].distance(band) <= t_pt / 2.0 + 1.0:
        join_t = max(join_t, pieces[j].t)
    if join_t and (b - a) <= join_t + 2.0:
      return "JUNCTION"
    return "OPENING"

  runs: list[Run] = []
  by_peak: dict = {}
  
  for p in pieces:
    by_peak.setdefault(p.peak, []).append(p)
  for peak, plist in by_peak.items():
    plist.sort(key=lambda p: (p.dc, p.s0))
    clusters: list[list[Piece]] = []
    for p in plist:
      placed = False
      for cl in reversed(clusters[-4:]):
        c0 = cl[0]
        if abs(p.dc - c0.dc) <= 0.6 and abs(p.t - c0.t) <= 0.06 * c0.t + 0.3:
          cl.append(p)
          placed = True
          break
      if not placed:
        clusters.append([p])
        
    for cl in clusters:
      _check(deadline)
      cl.sort(key=lambda p: p.s0)
      dc = sum(p.dc for p in cl) / len(cl)
      cur = None
      for p in cl:
        if cur is None:
          cur = Run(peak, dc, p.t, p.s0, p.s1, p.s1 - p.s0, 1)
          cur_t = [p.t * (p.s1 - p.s0), p.s1 - p.s0]
          continue
      
        gap = p.s0 - cur.s1
        join = gap <= MERGE_GAP_PT
        if not join and gap <= gap_max:
          kind = bridge_kind(peak, dc, cur.s1, p.s0, cur.t_pt)
          if kind == "OPENING":
            cur.gaps.append((cur.s1, p.s0))
          if kind != "BLOCKED":
            join = True
            
        if join:
          cur.clear_pt += max(0.0, p.s1 - max(p.s0, cur.s1))
          cur.s1 = max(cur.s1, p.s1)
          cur.pieces += 1
          cur_t[0] += p.t * (p.s1 - p.s0)
          cur_t[1] += p.s1 - p.s0
          cur.t_pt = cur_t[0] / cur_t[1]
          
        else:
          runs.append(cur)
          cur = Run(peak, dc, p.t, p.s0, p.s1, p.s1 - p.s0, 1)
          cur_t = [p.t * (p.s1 - p.s0), p.s1 - p.s0]
      if cur is not None:
        runs.append(cur)
  min_run = C.WALL_MIN_RUN_MM / mm_per_pt
  return [r for r in runs if (r.s1 - r.s0) >= min_run]

def run_polygon(r: Run, fr: Frame, extended: bool = False) -> Polygon:
  a = r.s0 - (r.ext0 if extended else 0.0)
  b = r.s1 + (r.ext1 if extended else 0.0)
  h = r.t_pt / 2.0
  return Polygon([fr.pt(a, r.dc - h), fr.pt(b, r.dc - h), fr.pt(b, r.dc + h), fr.pt(a, r.dc + h)])

def settle_junctions(runs: list[Run], frames: list[Frame], mm_per_pt: float) -> dict:

  stats = {"L": 0, "T": 0, "free": 0}
  if not runs:
    return stats
  polys = [run_polygon(r, frames[r.peak]) for r in runs]
  tree = STRtree(polys)
  max_t = max(r.t_pt for r in runs)
  for ia, A in enumerate(runs):
    fa = frames[A.peak]
    
    for end in (0, 1):
      s_e = A.s0 if end == 0 else A.s1
      sign = -1.0 if end == 0 else 1.0
      ex, ey = fa.pt(s_e, A.dc)
      r = A.t_pt / 2.0 + max_t / 2.0 + 3 * JUNCTION_TOL_PT
      best = None
      for j in tree.query(box(ex - r, ey - r, ex + r, ey + r)):
        j = int(j)
        if j == ia:
          continue
        B = runs[j]
        fb = frames[B.peak]
        cross = abs(fa.ux * fb.uy - fa.uy * fb.ux)
        
        if cross < math.cos(math.radians(3.0)):
          continue
        sB, dB = fb.s_of(ex, ey), fb.d_of(ex, ey)
        out_n = sign * (fa.ux * fb.nx + fa.uy * fb.ny)
        ahead = (B.dc - dB) * (1.0 if out_n > 0 else -1.0)
        hb = B.t_pt / 2.0
        if ahead < -(hb + JUNCTION_TOL_PT) or ahead > hb + JUNCTION_TOL_PT:
          continue
        slack = A.t_pt / 2.0 + JUNCTION_TOL_PT
        if sB < B.s0 - slack or sB > B.s1 + slack:
          continue
        through = (B.s0 < sB - slack) and (B.s1 > sB + slack)
       
        move = (ahead - hb) if through else ahead
        if best is None or abs(ahead) < best[0]:
          best = (abs(ahead), through, move)
      if best is None:
        stats["free"] += 1
        continue
      _, through, ext = best
      
      if through:
        stats["T"] += 1
        trim = min(ext, 0.0)
        if end == 0:
          A.end0, A.ext0 = "T", trim
        else:
          A.end1, A.ext1 = "T", trim
      else:
        stats["L"] += 1
        if end == 0:
          A.end0, A.ext0 = "L", ext
        else:
          A.end1, A.ext1 = "L", ext
  return stats

def detect_walls(index, mm_per_pt: float, deadline: float | None = None) -> tuple[list[Frame], list[Run], dict]:
  frames, faces = collect_faces(index, mm_per_pt, deadline)
  pieces = pair_faces(faces, mm_per_pt, deadline)
  runs = join_runs(pieces, frames, mm_per_pt, deadline)
  stats = settle_junctions(runs, frames, mm_per_pt)
  stats.update({"faces": len(faces), "pieces": len(pieces), "runs": len(runs)})
  return frames, runs, stats

def standard_thickness(t_mm: float) -> int | None:
  best = min(C.STANDARD_WALLS_MM, key=lambda s: abs(t_mm / s - 1.0))
  return best if abs(t_mm / best - 1.0) <= C.STANDARD_TOL else None

def run_ends(r: Run, fr: Frame) -> tuple:
  return fr.pt(r.s0 - r.ext0, r.dc), fr.pt(r.s1 + r.ext1, r.dc)
