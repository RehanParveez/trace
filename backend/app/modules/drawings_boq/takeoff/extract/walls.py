from __future__ import annotations
from dataclasses import dataclass, field, replace
import time
import numpy as np
import math
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.prep import units as UN
from shapely.geometry import Polygon, box
from shapely.strtree import STRtree

OFFSET_TOL_PT = 0.35      
MERGE_GAP_PT = 0.8        
PEAK_CLAIM_DEG = 0.6
JUNCTION_TOL_PT = 1.5
MAX_FACE_SPAN_PT = 1.0
MIN_SEG_PT = 0.5
BAND_SLACK_PT = 1.0
BAND_MIN_OVERLAP_PT = 2.0

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
  w: float = 0.0          

@dataclass
class Piece:
  peak: int
  d0: float
  d1: float
  s0: float
  s1: float
  w: float = 0.0        

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
  w: float = 0.0         
  pen_kept: bool = False   

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

def collect_faces(index, mm_per_pt: float, deadline: float | None = None, min_width: float = 0.0) -> tuple[list[Frame], list[Face]]:
  if len(index.kinds) == 0:
    return [], []

  raw = np.frombuffer(index.segs, dtype=np.float32).reshape(-1, 5).astype(np.float64)
  segs, wid = raw[:, :4], raw[:, 4]
  kinds = np.frombuffer(index.kinds, dtype=np.uint8)
  dx, dy = segs[:, 2] - segs[:, 0], segs[:, 3] - segs[:, 1]
  ln = np.hypot(dx, dy)
  keep = (kinds == 0) & (ln >= MIN_SEG_PT) & (wid >= min_width)
  if not keep.any():
    return [], []
  segs, dx, dy, ln, wid = segs[keep], dx[keep], dy[keep], ln[keep], wid[keep]
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
    wv = wid[sel][order]
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
      wm = float(np.average(wv[a:b], weights=np.maximum(hi[a:b] - lo[a:b], 1e-6)))
      segs_ = sorted(zip(lo[a:b].tolist(), hi[a:b].tolist()))
      cur0, cur1 = segs_[0]
      for l0, l1 in segs_[1:]:
        if l0 <= cur1 + MERGE_GAP_PT:
          cur1 = max(cur1, l1)
        else:
          if cur1 - cur0 >= min_face:
            faces.append(Face(pi, dm, cur0, cur1, wm))
          cur0, cur1 = l0, l1
      if cur1 - cur0 >= min_face:
        faces.append(Face(pi, dm, cur0, cur1, wm))
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
    pieces.append(Piece(fa.peak, fa.d, fb.d, o0, o1, min(fa.w, fb.w)))
  return pieces

def _piece_polygon(p: Piece, fr: Frame) -> Polygon:
  return Polygon([fr.pt(p.s0, p.d0), fr.pt(p.s1, p.d0), fr.pt(p.s1, p.d1), fr.pt(p.s0, p.d1)])

def straight_lines(index) -> np.ndarray:
  """Every straight line of the sheet as rows of (x0, y0, x1, y1)."""
  if len(index.kinds) == 0:
    return np.empty((0, 4))
  raw = np.frombuffer(index.segs, dtype=np.float32).reshape(-1, 5).astype(np.float64)
  kinds = np.frombuffer(index.kinds, dtype=np.uint8)
  return raw[kinds == 0][:, :4]

def band_is_clear(lines, fr: Frame, dc: float, a: float, b: float, t_pt: float) -> bool:
  """True when nothing is drawn along the wall line between a and b: no dashed beam line, no sill line, nothing inside the wall's thickness."""
  if lines is None or len(lines) == 0:
    return True
  sa = lines[:, 0] * fr.ux + lines[:, 1] * fr.uy
  sb = lines[:, 2] * fr.ux + lines[:, 3] * fr.uy
  da = lines[:, 0] * fr.nx + lines[:, 1] * fr.ny
  db = lines[:, 2] * fr.nx + lines[:, 3] * fr.ny
  along = np.abs(sb - sa)
  across = np.abs(db - da)
  inside = (np.abs((da + db) / 2.0 - dc) <= t_pt / 2.0 + BAND_SLACK_PT) & (across <= 0.2 * along + 0.5)
  over = np.minimum(np.maximum(sa, sb), b) - np.maximum(np.minimum(sa, sb), a)
  return not bool((inside & (over > BAND_MIN_OVERLAP_PT)).any())

def join_runs(pieces: list[Piece], frames: list[Frame], mm_per_pt: float, deadline: float | None = None, lines=None) -> list[Run]:
  if not pieces:
    return []
  gap_max = C.WALL_GAP_MAX_MM / mm_per_pt
  gap_clear_max = C.WALL_GAP_CLEAR_MAX_MM / mm_per_pt
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
          cur = Run(peak, dc, p.t, p.s0, p.s1, p.s1 - p.s0, 1, w=p.w)
          cur_t = [p.t * (p.s1 - p.s0), p.s1 - p.s0]
          cur_w = [p.w * (p.s1 - p.s0), p.s1 - p.s0]
          continue
      
        gap = p.s0 - cur.s1
        join = gap <= MERGE_GAP_PT
        reach = gap_max
        if not join and gap_max < gap <= gap_clear_max and band_is_clear(lines, frames[peak], dc, cur.s1, p.s0, cur.t_pt):
          reach = gap_clear_max
        if not join and gap <= reach:
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
          cur_w[0] += p.w * (p.s1 - p.s0)
          cur_w[1] += p.s1 - p.s0
          cur.w = cur_w[0] / cur_w[1]
        else:
          runs.append(cur)
          cur = Run(peak, dc, p.t, p.s0, p.s1, p.s1 - p.s0, 1, w=p.w)
          cur_t = [p.t * (p.s1 - p.s0), p.s1 - p.s0]
          cur_w = [p.w * (p.s1 - p.s0), p.s1 - p.s0]
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

LIGHT_RATIO = 0.75        
def weight_reference(runs: list[Run]) -> float:
  ws = sorted(((r.w, r.s1 - r.s0) for r in runs), key=lambda t: t[0])
  total = sum(l for _, l in ws)
  if total <= 0:
    return 0.0
  acc = 0.0
  for w, l in ws:
    acc += l
    if acc >= total / 2.0:
      return w
  return ws[-1][0]

def is_light(r: Run, ref: float) -> bool:
  return ref > 0.0 and r.w < LIGHT_RATIO * ref

def _detect_once(index, mm_per_pt: float, deadline: float | None, min_width: float) -> tuple[list[Frame], list[Run], dict]:
  frames, faces = collect_faces(index, mm_per_pt, deadline, min_width)
  pieces = pair_faces(faces, mm_per_pt, deadline)
  runs = join_runs(pieces, frames, mm_per_pt, deadline, straight_lines(index))
  from app.modules.drawings_boq.takeoff.extract import frame_band as FB
  border = {id(r) for r in FB.frame_runs(index, runs, frames)}
  if border:
    runs = [r for r in runs if id(r) not in border]
  stats = settle_junctions(runs, frames, mm_per_pt)
  ref = weight_reference(runs)
  
  loose = [r for r in runs if is_light(r, ref) and (r.end0 == "FREE" or r.end1 == "FREE")]
  if loose:
    gone = {id(r) for r in loose}
    runs = [r for r in runs if id(r) not in gone]
    for r in runs:
      r.end0 = r.end1 = "FREE"
      r.ext0 = r.ext1 = 0.0
    stats = settle_junctions(runs, frames, mm_per_pt)
  stats.update({"faces": len(faces), "pieces": len(pieces), "runs": len(runs), "dropped_light_loose": len(loose), "weight_ref_pt": round(ref, 4), "frame_runs_dropped": len(border)})
  return frames, runs, stats

PEN_MIN_SHARE = 0.05
PEN_KEEP_SHARE = 0.25
PEN_MIN_RUNS = 4

def pen_classes(index) -> list:
  """(line weight, share of all straight line length), heaviest first."""
  if len(index.kinds) == 0:
    return []
  raw = np.frombuffer(index.segs, dtype=np.float32).reshape(-1, 5).astype(np.float64)
  kinds = np.frombuffer(index.kinds, dtype=np.uint8)
  ln = np.hypot(raw[:, 2] - raw[:, 0], raw[:, 3] - raw[:, 1])
  keep = (kinds == 0) & (ln >= MIN_SEG_PT)
  total = float(ln[keep].sum())
  if total <= 0:
    return []
  out: dict = {}
  for w, length in zip(np.round(raw[keep, 4], 2).tolist(), ln[keep].tolist()):
    out[w] = out.get(w, 0.0) + length
  return sorted(((w, v / total) for w, v in out.items()), reverse=True)

def _standard_length_mm(runs: list, mm_per_pt: float) -> float:
  return sum((r.s1 - r.s0) * mm_per_pt for r in runs if standard_thickness(r.t_pt * mm_per_pt))

LIGHT_KEEP_MIN_MM = 3000.0     
LIGHT_KEEP_LONG_MM = 8000.0    
LIGHT_KEEP_MAX_MM = 160.0      

def _wall_like_thickness(t_mm: float) -> bool:
  """A thin brick wall (4.5 or 6 inch; 90 to 160 mm) as boundary, lawn and partition walls are, not a stair tread (250 mm) or a beam or a slab edge."""
  if t_mm > LIGHT_KEEP_MAX_MM or t_mm < 90.0:
    return False
  if standard_thickness(t_mm) is not None:
    return True
  return any(abs(t_mm / s - 1.0) <= C.IMPERIAL_TOL for s in C.IMPERIAL_WALLS_MM[:3])

def _seg(run: Run, frames: list) -> tuple:
  fr = frames[run.peak]
  return fr.pt(run.s0, run.dc), fr.pt(run.s1, run.dc)

def _lies_on(a: tuple, b: tuple, c: tuple, d: tuple, reach: float) -> bool:
  """True when segment a-b runs along segment c-d (parallel, within reach across, and over half of a-b alongside)."""
  la = math.hypot(b[0] - a[0], b[1] - a[1])
  lc = math.hypot(d[0] - c[0], d[1] - c[1])
  if la <= 0.0 or lc <= 0.0:
    return False
  ux, uy = (d[0] - c[0]) / lc, (d[1] - c[1]) / lc
  if abs((b[0] - a[0]) * uy - (b[1] - a[1]) * ux) > 0.05 * la:
    return False
  across = max(abs((p[0] - c[0]) * uy - (p[1] - c[1]) * ux) for p in (a, b))
  if across > reach:
    return False
  t0 = (a[0] - c[0]) * ux + (a[1] - c[1]) * uy
  t1 = (b[0] - c[0]) * ux + (b[1] - c[1]) * uy
  lo, hi = max(min(t0, t1), 0.0), min(max(t0, t1), lc)
  return hi - lo > 0.5 * la

def add_light_walls(frames: list, runs: list, all_frames: list, all_runs: list, wall_pen: float, mm_per_pt: float) -> tuple:
  keep = []
  
  for r in all_runs:
    if r.w >= wall_pen - 0.005:
      continue
    t = r.t_pt * mm_per_pt
    length = (r.s1 - r.s0) * mm_per_pt
    if not _wall_like_thickness(t) or length < LIGHT_KEEP_MIN_MM:
      continue
    if length < LIGHT_KEEP_LONG_MM and r.end0 == "FREE" and r.end1 == "FREE":
      continue
    a, b = _seg(r, all_frames)
    if any(_lies_on(a, b, *_seg(h, frames), max(h.t_pt, r.t_pt) * 1.5) for h in runs):
      continue
  
    keep.append(r)
  if not keep:
    return frames, runs, {"light_walls_kept": 0, "light_walls_m": 0.0}
  base = len(frames)
  frames = list(frames) + list(all_frames)
  runs = list(runs)
  for r in keep:
    runs.append(replace(r, peak=base + r.peak, end0="FREE", end1="FREE", ext0=0.0, ext1=0.0, pen_kept=True, gaps=list(r.gaps)))
  for r in runs:
    r.end0 = r.end1 = "FREE"
    r.ext0 = r.ext1 = 0.0
  settle_junctions(runs, frames, mm_per_pt)
  metres = sum((r.s1 - r.s0) for r in keep) * mm_per_pt / 1000.0
  return frames, runs, {"light_walls_kept": len(keep), "light_walls_m": round(metres, 1)}

def detect_walls(index, mm_per_pt: float, deadline: float | None = None, at_grade: bool = False) -> tuple[list[Frame], list[Run], dict]:
  frames, runs, stats = _detect_once(index, mm_per_pt, deadline, 0.0)
  classes = pen_classes(index)
  stats["pens"] = [[w, round(s, 3)] for w, s in classes]
  stats["wall_pen_pt"] = None
  base = _standard_length_mm(runs, mm_per_pt)
  if len(classes) < 2 or base <= 0:
    return frames, runs, stats
  lightest = classes[-1][0]
  
  for w, share in classes:
    if w <= lightest + 1e-6:
      break
    if share < PEN_MIN_SHARE:
      continue
    f2, r2, s2 = _detect_once(index, mm_per_pt, deadline, w - 0.005)
    if len(r2) >= PEN_MIN_RUNS and _standard_length_mm(r2, mm_per_pt) >= PEN_KEEP_SHARE * base:
      if at_grade:
        f2, r2, kept = add_light_walls(f2, r2, frames, runs, w, mm_per_pt)
        s2 = dict(s2, **kept)
      s2["pens"] = stats["pens"]
      s2["wall_pen_pt"] = w
      s2["runs_all_pens"] = len(runs)
      s2["wall_m_all_pens"] = round(sum((r.s1 - r.s0) for r in runs) * mm_per_pt / 1000.0, 1)
      return f2, r2, s2
  return frames, runs, stats

def snap_thickness(t_mm: float, imperial: bool = False, vocab: list | None = None) -> tuple:
  """(standard thickness found or None, thickness to use in mm). In a drawing in feet and inches a wall is a thickness this drawing uses (vocab, within 15%), a usual
  inch wall, or the nearest half inch; the metric list (230, 250 mm ...) is not tried, because 250 mm in an inch drawing is a 9 inch wall measured loosely. Any
  other drawing has the metric 115 and 230 mm walls."""
  return UN.snap_wall(t_mm, imperial, vocab, C.IMPERIAL_WALLS_MM, standard_thickness)

def standard_thickness(t_mm: float) -> int | None:
  best = min(C.STANDARD_WALLS_MM, key=lambda s: abs(t_mm / s - 1.0))
  return best if abs(t_mm / best - 1.0) <= C.STANDARD_TOL else None

def bridge_ends(runs: list[Run], frames: list[Frame], mm_per_pt: float) -> dict:
  """For each free wall end, how far the wall runs on to reach a cross wall straight ahead (a door or window opening of up to WALL_BRIDGE_MAX_MM
  where the wall lines stop). Returns {id(run): [extra at start, extra at end]} in points; nothing is changed on the runs themselves.
  The extra length is counted as wall, and the door or window that stands in it is deducted when the wall is measured."""
  out: dict = {}
  if not runs:
    return out
  reach = C.WALL_BRIDGE_MAX_MM / mm_per_pt
  for ia, A in enumerate(runs):
    fa = frames[A.peak]
    for end in (0, 1):
      if (A.end0 if end == 0 else A.end1) != "FREE":
        continue
    
      s_e = (A.s0 - A.ext0) if end == 0 else (A.s1 + A.ext1)
      sign = -1.0 if end == 0 else 1.0
      ex, ey = fa.pt(s_e, A.dc)
      dx, dy = sign * fa.ux, sign * fa.uy
      best = None
      for jb, B in enumerate(runs):
        if jb == ia:
          continue
        fb = frames[B.peak]
        if abs(fa.ux * fb.uy - fa.uy * fb.ux) < math.cos(math.radians(3.0)):
          continue
        dn = dx * fb.nx + dy * fb.ny
        if abs(dn) < 0.7:
          continue
        t = (B.dc - fb.d_of(ex, ey)) / dn
        hb = B.t_pt / 2.0
        if t <= 0.0 or t - hb > reach:
          continue
      
        hx, hy = ex + dx * t, ey + dy * t
        sb = fb.s_of(hx, hy)
        slack = A.t_pt / 2.0 + JUNCTION_TOL_PT
        if sb < B.s0 - slack or sb > B.s1 + slack:
          continue
        through = (B.s0 < sb - slack) and (B.s1 > sb + slack)
        run_on = t - hb if through else t
        if run_on > 0.0 and (best is None or run_on < best):
          best = run_on
      if best is not None:
        out.setdefault(id(A), [0.0, 0.0])[end] = best
  return out

def run_ends(r: Run, fr: Frame) -> tuple:
  return fr.pt(r.s0 - r.ext0, r.dc), fr.pt(r.s1 + r.ext1, r.dc)
