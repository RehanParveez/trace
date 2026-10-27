from __future__ import annotations
import math
import time

MIN_PIXELS = 10
MIN_LEN_PT = 2.5
MAX_LEN_PT = 260.0
MAX_THICK_PX = 6.5
MIN_ELONG = 1.5
CHORD_PT = 6.0
STRAIGHT_RMS_PT = 0.4
STRAIGHT_MIN_PT = 10.0
MAX_PIECES = 80000
MASK_PAD_PX = 1
MERGE_PX = 1
VOTE_MAX_PT = 18.0
R_MIN_PT, R_MAX_PT = 12.0, 125.0
VOTE_CELL_PT = 3.0
MIN_VOTES = 4
SOLO_RMS_PT = 1.0
SOLO_MIN_PIECES = 4
FIT_TOL_PT = 2.5
MIN_SPAN_DEG, MAX_SPAN_DEG = 40.0, 200.0
MIN_INK_SHARE = 0.35
ARC_CHORD_PT = 4.0
MAX_ARCS = 400

def _runs(ink):
  import numpy as np
  h, w = ink.shape
  pad = np.zeros((h, w + 2), dtype="int8")
  pad[:, 1:-1] = ink
  d = np.diff(pad, axis=1)
  sr, sc = np.nonzero(d == 1)
  _, ec = np.nonzero(d == -1)
  return sr.tolist(), sc.tolist(), ec.tolist()

def components(ink, deadline: float) -> list:
  rows, starts, ends = _runs(ink)
  n = len(rows)
  parent = list(range(n))

  def find(a: int) -> int:
    while parent[a] != a:
      parent[a] = parent[parent[a]]
      a = parent[a]
    return a
    
  first: dict = {}
  for k in range(n):
    first.setdefault(rows[k], k)
  for k in range(n):
    j = first.get(rows[k] - 1)
    if j is None:
      continue
    while j < n and rows[j] == rows[k] - 1:
      if starts[j] > ends[k]:
        break
      if ends[j] >= starts[k]:
        a, b = find(k), find(j)
        if a != b:
          parent[a] = b
      j += 1

    if (k & 0x7FFF) == 0 and time.monotonic() > deadline:
      return []
  groups: dict = {}
  for k in range(n):
    groups.setdefault(find(k), []).append((rows[k], starts[k], ends[k]))
  return list(groups.values())

def _pixels(runs: list):
  import numpy as np
  xs = np.concatenate([np.arange(s, e) for _, s, e in runs]).astype("float64")
  ys = np.concatenate([np.full(e - s, r) for r, s, e in runs]).astype("float64")
  return xs, ys

def _bin_fit(px, py, scale: float):
  qx, qy = px.mean(), py.mean()
  ex, ey = px - qx, py - qy
  a, b, c = float((ex * ex).mean()), float((ey * ey).mean()), float((ex * ey).mean())
  th = 0.5 * math.atan2(2.0 * c, a - b)
  tx, ty = math.cos(th), math.sin(th)
  t = ex * tx + ey * ty
  lo, hi = float(t.min()), float(t.max())
  length = hi - lo + 1.0
  if length < 1.5 * scale:
    return None
  return (qx + tx * lo, qy + ty * lo, qx + tx * hi, qy + ty * hi), len(px) / length

def stroke_pieces(runs: list, scale: float) -> list:
  import numpy as np
  n = sum(e - s for _, s, e in runs)
  if n < MIN_PIXELS:
    return []

  c0 = min(r[1] for r in runs)
  c1 = max(r[2] for r in runs)
  r0 = min(r[0] for r in runs)
  r1 = max(r[0] for r in runs) + 1
  if max(c1 - c0, r1 - r0) < MIN_LEN_PT * scale or max(c1 - c0, r1 - r0) > MAX_LEN_PT * scale:
    return []
  xs, ys = _pixels(runs)
  mx, my = xs.mean(), ys.mean()
  dx, dy = xs - mx, ys - my
  cxx, cyy, cxy = float((dx * dx).mean()) + 1.0 / 12.0, float((dy * dy).mean()) + 1.0 / 12.0, float((dx * dy).mean())
  tr, det = cxx + cyy, cxx * cyy - cxy * cxy
  disc = math.sqrt(max(tr * tr / 4.0 - det, 0.0))
  l1, l2 = tr / 2.0 + disc, max(tr / 2.0 - disc, 1e-9)
  if math.sqrt(l1 / l2) < MIN_ELONG:
    return []

  ang = 0.5 * math.atan2(2.0 * cxy, cxx - cyy)
  ux, uy = math.cos(ang), math.sin(ang)
  u = dx * ux + dy * uy
  v = -dx * uy + dy * ux
  if float(u.max() - u.min()) + 1.0 < MIN_LEN_PT * scale:
    return []
  rms = float(np.sqrt((v * v).mean())) / scale
  step = CHORD_PT * scale
  edges = np.arange(float(u.min()), float(u.max()) + step, step)
  fits = []
  for k in range(len(edges) - 1):
    sel = (u >= edges[k]) & (u < edges[k + 1])
    if int(sel.sum()) < 4:
      continue
    f = _bin_fit(xs[sel], ys[sel], scale)
    if f is not None:
      fits.append(f)
  if not fits:
    return []

  thick_px = float(np.median([f[1] for f in fits]))
  if thick_px > MAX_THICK_PX:
    return []
  width = max(thick_px - 2.0 * MERGE_PX, 1.0) / scale
  if rms <= STRAIGHT_RMS_PT:
    p0 = (mx + ux * float(u.min()), my + uy * float(u.min()))
    p1 = (mx + ux * float(u.max()), my + uy * float(u.max()))
    return [(p0[0] / scale, p0[1] / scale, p1[0] / scale, p1[1] / scale, width, 0)]
  return [(f[0][0] / scale, f[0][1] / scale, f[0][2] / scale, f[0][3] / scale, width, 1) for f in fits]

def _solo_arc(ps: list):
  import numpy as np
  mx = np.array([(p[0] + p[2]) / 2.0 for p in ps])
  my = np.array([(p[1] + p[3]) / 2.0 for p in ps])

  fit = _fit_circle(mx, my)
  if fit is None:
    return None
  cx, cy, r = fit
  if r < R_MIN_PT or r > R_MAX_PT:
    return None
  res = np.hypot(mx - cx, my - cy) - r
  if float(np.sqrt((res * res).mean())) > SOLO_RMS_PT:
    return None

  ends = np.array([[p[0], p[1]] for p in ps] + [[p[2], p[3]] for p in ps])
  ang = np.sort(np.degrees(np.arctan2(ends[:, 1] - cy, ends[:, 0] - cx)) % 360.0)
  gaps = np.diff(np.concatenate([ang, [ang[0] + 360.0]]))
  k = int(np.argmax(gaps))
  span = 360.0 - float(gaps[k])
  if span < MIN_SPAN_DEG or span > MAX_SPAN_DEG:
    return None
  a0 = float(ang[(k + 1) % len(ang)])
  m = max(4, int(round(r * math.radians(span) / ARC_CHORD_PT)))
  pts = [(cx + r * math.cos(math.radians(a0 + span * j / m)), cy + r * math.sin(math.radians(a0 + span * j / m))) for j in range(m + 1)]
  return [(pts[j][0], pts[j][1], pts[j + 1][0], pts[j + 1][1], ps[0][4], 1) for j in range(m)]

def _arcs_from_pieces(pieces: list, ink, scale: float, deadline: float) -> list:
  import numpy as np
  vote = [p for p in pieces if math.hypot(p[2] - p[0], p[3] - p[1]) <= VOTE_MAX_PT]
  if len(vote) < MIN_VOTES:
    return []

  P = np.array([[p[0], p[1], p[2], p[3]] for p in vote], dtype="float64")
  ln = np.hypot(P[:, 2] - P[:, 0], P[:, 3] - P[:, 1])
  ok = ln > 0.5
  P, ln = P[ok], ln[ok]
  mx, my = (P[:, 0] + P[:, 2]) / 2.0, (P[:, 1] + P[:, 3]) / 2.0
  nx, ny = -(P[:, 3] - P[:, 1]) / ln, (P[:, 2] - P[:, 0]) / ln
  rs = np.arange(R_MIN_PT, R_MAX_PT + 1.0, VOTE_CELL_PT)
  keys, who = [], []
  step = 3000
  for lo in range(0, len(P), step):
    if time.monotonic() > deadline:
      return []
    sl = slice(lo, lo + step)
    for sign in (1.0, -1.0):
      kx = np.round((mx[sl, None] + sign * nx[sl, None] * rs[None, :]) / VOTE_CELL_PT).astype(np.int64)
      ky = np.round((my[sl, None] + sign * ny[sl, None] * rs[None, :]) / VOTE_CELL_PT).astype(np.int64)
      kr = np.broadcast_to(np.arange(len(rs), dtype=np.int64)[None, :], kx.shape)
      keys.append(((kx + 2000) * 40_000_000 + (ky + 2000) * 1000 + kr).ravel())
      who.append(np.repeat(np.arange(lo, min(lo + step, len(P))), len(rs)))

  keys, who = np.concatenate(keys), np.concatenate(who)
  order = np.argsort(keys, kind="stable")
  keys, who = keys[order], who[order]
  uk, start, cnt = np.unique(keys, return_index=True, return_counts=True)
  cand = np.where(cnt >= MIN_VOTES)[0]
  cand = cand[np.argsort(-cnt[cand])][:3000]
  h, w = ink.shape
  out: list = []
  used: list = []

  for ci in cand:
    if time.monotonic() > deadline or len(used) >= MAX_ARCS:
      break
    sel = np.unique(who[start[ci]:start[ci] + cnt[ci]])
    k = int(uk[ci])
    cx0 = (k // 40_000_000 - 2000) * VOTE_CELL_PT
    cy0 = ((k // 1000) % 40_000 - 2000) * VOTE_CELL_PT
    r0 = rs[k % 1000]
    d = np.abs(np.hypot(mx[sel] - cx0, my[sel] - cy0) - r0)
    sel = sel[d <= FIT_TOL_PT]
    if len(sel) < MIN_VOTES:
      continue
    fit = _fit_circle(mx[sel], my[sel])
    if fit is None:
      continue
    cx, cy, r = fit
    if r < R_MIN_PT or r > R_MAX_PT:
      continue
    d = np.abs(np.hypot(mx[sel] - cx, my[sel] - cy) - r)
    sel = sel[d <= 1.2]
    if len(sel) < MIN_VOTES:
      continue

    ang = np.sort(np.degrees(np.arctan2(my[sel] - cy, mx[sel] - cx)) % 360.0)
    gaps = np.diff(np.concatenate([ang, [ang[0] + 360.0]]))
    kmax = int(np.argmax(gaps))
    span = 360.0 - float(gaps[kmax])
    a0 = float(ang[(kmax + 1) % len(ang)])
    if span < MIN_SPAN_DEG or span > MAX_SPAN_DEG:
      continue
    key = frozenset(sel.tolist())
    if any(len(key & u) > 0.5 * len(key) for u in used):
      continue

    length = r * math.radians(span)
    n = max(8, int(length / 1.0))
    t = np.radians(a0 + span * np.arange(n + 1) / n)
    px = np.clip(np.round((cx + r * np.cos(t)) * scale).astype(int), 0, w - 1)
    py = np.clip(np.round((cy + r * np.sin(t)) * scale).astype(int), 0, h - 1)
    hit = np.zeros(len(t), dtype=bool)
    for dx in (-1, 0, 1):
      for dy in (-1, 0, 1):
        hit |= ink[np.clip(py + dy, 0, h - 1), np.clip(px + dx, 0, w - 1)]
    if float(hit.mean()) < MIN_INK_SHARE:
      continue
    used.append(key)

    m = max(4, int(round(length / ARC_CHORD_PT)))
    pts = [(cx + r * math.cos(math.radians(a0 + span * j / m)), cy + r * math.sin(math.radians(a0 + span * j / m))) for j in range(m + 1)]
    wd = float(np.median([vote[0][4]]))
    out.extend((pts[j][0], pts[j][1], pts[j + 1][0], pts[j + 1][1], wd, 1) for j in range(m))
  return out

def _fit_circle(xs, ys):
  import numpy as np
  A = np.column_stack([xs, ys, np.ones_like(xs)])
  b = -(xs * xs + ys * ys)
  try:
    sol = np.linalg.lstsq(A, b, rcond=None)[0]
  except Exception:
    return None
  cx, cy = -sol[0] / 2.0, -sol[1] / 2.0
  r2 = cx * cx + cy * cy - sol[2]
  if r2 <= 0:
    return None
  return float(cx), float(cy), float(math.sqrt(r2))

def find_curves(ink, bars: list, scale: float, deadline: float) -> list:
  import numpy as np
  mask = np.zeros(ink.shape, dtype=bool)
  for horizontal, a0, a1, b, t in bars:
    lo = int(max(0, math.floor(b - t / 2.0 - MASK_PAD_PX)))
    hi = int(math.ceil(b + t / 2.0 + MASK_PAD_PX))
    s, e = int(max(0, a0 - MASK_PAD_PX)), int(math.ceil(a1 + MASK_PAD_PX))
    if horizontal:
      mask[lo:hi, s:e] = True
    else:
      mask[s:e, lo:hi] = True

  near = ink & ~mask
  for _ in range(MERGE_PX):
    grown = near.copy()
    grown[1:, :] |= near[:-1, :]
    grown[:-1, :] |= near[1:, :]
    grown[:, 1:] |= near[:, :-1]
    grown[:, :-1] |= near[:, 1:]
    near = grown

  straight: list = []
  voters: list = []
  solid: list = []
  for g in components(near, deadline):
    if time.monotonic() > deadline or len(voters) >= MAX_PIECES:
      break
    ps = stroke_pieces(g, scale)
    arc = _solo_arc(ps) if len(ps) >= SOLO_MIN_PIECES and ps[0][5] == 1 else None
    if arc is not None:
      solid.extend(arc)
      continue
    for p in ps:
      voters.append(p)
      if p[5] == 0:
        straight.append(p)
  return straight + solid + _arcs_from_pieces(voters, ink, scale, deadline)
