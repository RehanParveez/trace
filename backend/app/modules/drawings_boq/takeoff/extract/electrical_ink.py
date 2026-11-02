from __future__ import annotations
import ctypes
import numpy as np
from PIL import Image, ImageDraw

BEZIER_STEPS = 6
MASK_SPAN = 48
MASK_PAD = 4
STROKE_PX = 2
PAIR_SAMPLES = 90
RADIAL_BINS = 10
RADIAL_MAX = 2.5
PAIR_BINS = 16
PAIR_MAX = 4.0
INK_OBJECT_MAX = 75.0
RUN_TOUCH = 1.5
RUN_EXTENT = 90.0
MIN_RUN_PIXELS = 12
SEPARATION_SHARE = 0.5
SHAPE_TOL_CAP = 0.10
AMBIGUOUS_SEPARATION = 0.02
AREA_RATIO_TOL = 0.35
SCALE_MIN, SCALE_MAX = 0.4, 5.0
GRID = 24
GRID_RANGE = 2.5
ANISO_MAX = 0.6
COVER_MIN = 0.9

class Ink:
  __slots__ = ("polys", "fills", "box")

  def __init__(self, polys: list, fills: list, box: tuple):
    self.polys, self.fills, self.box = polys, fills, box

def _flatten(c0, c1, c2, c3) -> list:
  out = []
  for k in range(1, BEZIER_STEPS + 1):
    t = k / BEZIER_STEPS
    u = 1.0 - t
    out.append((u ** 3 * c0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t ** 3 * c3[0], u ** 3 * c0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t ** 3 * c3[1]))
  return out

def object_ink(raw, o) -> Ink | None:
  n = int(raw.FPDFPath_CountSegments(o.raw))
  if n < 1:
    return None
  m = raw.FS_MATRIX()
  raw.FPDFPageObj_GetMatrix(o.raw, m)
  fill, stroke = ctypes.c_int(), ctypes.c_int()
  raw.FPDFPath_GetDrawMode(o.raw, fill, stroke)
  x, y = ctypes.c_float(), ctypes.c_float()
  polys: list = []
  cur: list = []
  pend: list = []
  
  for k in range(n):
    seg = raw.FPDFPath_GetPathSegment(o.raw, k)
    raw.FPDFPathSegment_GetPoint(seg, x, y)
    kind = raw.FPDFPathSegment_GetType(seg)
    
    p = (m.a * x.value + m.c * y.value + m.e, m.b * x.value + m.d * y.value + m.f)
    if kind == 2:
      if len(cur) > 1:
        polys.append(cur)
      cur, pend = [p], []
    elif kind == 1:
      pend.append(p)
      if len(pend) == 3 and cur:
        cur.extend(_flatten(cur[-1], pend[0], pend[1], pend[2]))
        pend = []
    else:
      cur.append(p)
    if raw.FPDFPathSegment_GetClose(seg) and len(cur) > 1:
      cur.append(cur[0])
      polys.append(cur)
      cur = [cur[0]]
  if len(cur) > 1:
    polys.append(cur)
  if not polys:
    return None
  arrs = [np.array(p, dtype=float) for p in polys]
  allp = np.concatenate(arrs)
  fills = [a for a in arrs if fill.value and len(a) > 3]
  return Ink(arrs, fills, (float(allp[:, 0].min()), float(allp[:, 1].min()), float(allp[:, 0].max()), float(allp[:, 1].max())))

def loader(page):
  import pypdfium2.raw as raw
  objs = list(page.get_objects(filter=[raw.FPDF_PAGEOBJ_PATH, raw.FPDF_PAGEOBJ_TEXT, raw.FPDF_PAGEOBJ_FORM], max_depth=0))
  cache: dict = {}

  def ink_of(index: int):
    if index in cache:
      return cache[index]
    got = None
    if 0 <= index < len(objs) and objs[index].type == raw.FPDF_PAGEOBJ_PATH:
      try:
        got = object_ink(raw, objs[index])
      except Exception:
        got = None
    cache[index] = got
    return got
  return ink_of

def mask(inks: list):
  inks = [i for i in inks if i is not None]
  if not inks:
    return None
  x0, y0 = min(i.box[0] for i in inks), min(i.box[1] for i in inks)
  x1, y1 = max(i.box[2] for i in inks), max(i.box[3] for i in inks)
  span = max(x1 - x0, y1 - y0)
  if span <= 1e-6:
    return None
  k = MASK_SPAN / span
  
  size = MASK_SPAN + 2 * MASK_PAD + 1
  im = Image.new("1", (size, size), 0)
  dr = ImageDraw.Draw(im)
  for i in inks:
    for a in i.fills:
      dr.polygon([((px - x0) * k + MASK_PAD, (py - y0) * k + MASK_PAD) for px, py in a], fill=1)
    for a in i.polys:
      pts = [((px - x0) * k + MASK_PAD, (py - y0) * k + MASK_PAD) for px, py in a]
      dr.line(pts, fill=1, width=STROKE_PX)
  return np.array(im, dtype=bool), span

def describe(m) -> dict | None:
  if m is None:
    return None
  arr, span = m
  ys, xs = np.nonzero(arr)
  if len(xs) < MIN_RUN_PIXELS:
    return None
  pts = np.stack([xs, ys], axis=1).astype(float)
  c = pts.mean(axis=0)
  r = np.hypot(*(pts - c).T)
  R = float(np.sqrt((r ** 2).mean()))
  if R <= 1e-6:
    return None

  rad = np.histogram(np.minimum(r / R, RADIAL_MAX - 1e-9), bins=RADIAL_BINS, range=(0.0, RADIAL_MAX))[0].astype(float)
  sub = pts[np.linspace(0, len(pts) - 1, min(PAIR_SAMPLES, len(pts))).astype(int)]
  d = np.hypot(*(sub[:, None, :] - sub[None, :, :]).transpose(2, 0, 1))[np.triu_indices(len(sub), 1)] / R
  pair = np.histogram(np.minimum(d, PAIR_MAX - 1e-9), bins=PAIR_BINS, range=(0.0, PAIR_MAX))[0].astype(float)
  w, v = np.linalg.eigh(np.cov(pts.T))
  q = ((pts - c) @ v[:, ::-1]) / np.sqrt(np.maximum(w[::-1], 1e-9))
  g = np.histogram2d(q[:, 0], q[:, 1], bins=GRID, range=[[-GRID_RANGE, GRID_RANGE], [-GRID_RANGE, GRID_RANGE]])[0] > 0
  return {"R": R * span / MASK_SPAN, "rad": (rad / rad.sum()).tolist(), "pair": (pair / pair.sum()).tolist(), "area": float(len(xs)) / (R * R),
    "aniso": float(w[0] / max(w[1], 1e-9)), "grid": np.packbits(g.ravel()).tobytes().hex()}

def _grid(d: dict):
  return np.unpackbits(np.frombuffer(bytes.fromhex(d["grid"]), dtype=np.uint8))[:GRID * GRID].reshape(GRID, GRID).astype(bool)

def _dilate(g):
  d = g.copy()
  d[1:] |= g[:-1]
  d[:-1] |= g[1:]
  d[:, 1:] |= g[:, :-1]
  d[:, :-1] |= g[:, 1:]
  return d

def cover(a: dict, b: dict) -> float:
  ga, gb = _grid(a), _grid(b)
  best = 0.0
  for fx in (1, -1):
    for fy in (1, -1):
      g = gb[::fx, ::fy]
      best = max(best, min((ga & _dilate(g)).sum() / max(ga.sum(), 1), (g & _dilate(ga)).sum() / max(g.sum(), 1)))
  return float(best)

def distance(a: dict, b: dict) -> float:
  return 0.25 * (float(np.abs(np.array(a["rad"]) - np.array(b["rad"])).sum()) + float(np.abs(np.array(a["pair"]) - np.array(b["pair"])).sum()))

def _same_kind(a: dict, b: dict) -> bool:
  return abs(np.log(max(a["area"], 1e-6) / max(b["area"], 1e-6))) <= AREA_RATIO_TOL

def tolerances(rows: list, inner: list) -> list:
  out: list = []
  for i, d in enumerate(rows):
    if d is None:
      out.append(0.0)
      continue
    near = min([distance(d, e) for j, e in enumerate(rows) if e is not None and j != i and tuple(inner[i]) == tuple(inner[j]) and _same_kind(d, e)], default=1.0)
    out.append(0.0 if near < AMBIGUOUS_SEPARATION else min(SHAPE_TOL_CAP, SEPARATION_SHARE * near))
  return out

def runs(plan: list, ink_of) -> list:
  out: list = []
  cur: list = []
  box = None

  def flush():
    if cur:
      out.append((cur[0][0], cur[-1][0], box, [c[1] for c in cur]))
  for o in plan:
    ink = ink_of(o.index) if o.kind == 2 and max(o.box[2] - o.box[0], o.box[3] - o.box[1]) <= INK_OBJECT_MAX else None
    if ink is None:
      flush()
      cur, box = [], None
      continue
    b = o.box
    if cur and o.index == cur[-1][0] + 1 and b[0] <= box[2] + RUN_TOUCH and b[2] >= box[0] - RUN_TOUCH and b[1] <= box[3] + RUN_TOUCH and b[3] >= box[1] - RUN_TOUCH \
        and max(box[2], b[2]) - min(box[0], b[0]) <= RUN_EXTENT and max(box[3], b[3]) - min(box[1], b[1]) <= RUN_EXTENT:
      cur.append((o.index, ink))
      box = (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
    else:
      flush()
      cur, box = [(o.index, ink)], b
  flush()
  return out

def _text_inside(box: tuple, keys: tuple, tokens: list) -> bool:
  pad = 2.0 * RUN_TOUCH
  want = list(keys)
  for _i, key, tb in tokens:
    cx, cy = (tb[0] + tb[2]) / 2.0, (tb[1] + tb[3]) / 2.0
    if key in want and box[0] - pad <= cx <= box[2] + pad and box[1] - pad <= cy <= box[3] + pad:
      want.remove(key)
  return not want

def match(plan: list, ink_of, rows: list, inner: list, wanted: list, taken: list, tokens: list) -> list:
  tol = tolerances(rows, inner)
  found: list = []
  for first, last, box, inks in runs(plan, ink_of):
    if any(not (last < a or first > b) for a, b in taken):
      continue
    w = describe(mask(inks))
    if w is None:
      continue
    best = None
    for ri in wanted:
      t = rows[ri]
      if t is None or tol[ri] <= 0.0:
        continue
    
      d = distance(w, t)
      scale = w["R"] / t["R"]
      if d > tol[ri] or not SCALE_MIN <= scale <= SCALE_MAX or not _same_kind(w, t):
        continue
      if inner[ri] and not _text_inside(box, tuple(inner[ri]), tokens):
        continue
      if t["aniso"] < ANISO_MAX and cover(w, t) < COVER_MIN:
        continue
      if best is None or d / tol[ri] < best[0]:
        best = (d / tol[ri], ri, scale, d)
    if best is not None:
      found.append((best[1], first, last, round(best[2], 2), box, best[3], best[0]))
      
  found.sort(key=lambda f: f[6])
  kept: list = []
  used: list = []
  for f in found:
    if any(not (f[2] < a or f[1] > b) for a, b in used):
      continue
    used.append((f[1], f[2]))
    kept.append(f[:6])
  return sorted(kept, key=lambda f: f[1])
