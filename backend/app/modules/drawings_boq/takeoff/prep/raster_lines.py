from __future__ import annotations
import os
import math
import time

ENABLED = os.environ.get("TRACE_RASTER_LINES", "1") != "0"
BUDGET_S = float(os.environ.get("TRACE_RASTER_LINES_BUDGET_S", "30"))
SKEW_MIN_DEG = 0.3
LINE_DPI = 200.0
MIN_DPI = 100.0
MAX_SIDE_PX = 7000
MIN_RUN_PT = 10.0
BRIDGE_PX = 2
MIN_OVERLAP = 0.8
JOIN_GAP_PT = 1.5
MAX_BAR_PT = 14.0
MIN_SEG_PT = 10.0
MAX_SEGMENTS = 120000
INK_MIN, INK_MAX = 90, 190
PEN_JITTER_PX = 0.6
PEN_RATIO = 1.45
FRINGE_PX = 1.5
FRINGE_THICKER_PX = 1.0
FRINGE_OVERLAP = 0.5
CHAIN_GAP_PT = 3.0
CHAIN_OFFSET_PX = 1.5

def ink_level(gray) -> int:
  import numpy as np
  hist = np.bincount(gray.ravel(), minlength=256).astype("float64")
  total = hist.sum()
  if total <= 0:
    return INK_MAX
  cum = np.cumsum(hist)
  mean = np.cumsum(hist * np.arange(256))
  m_all = mean[-1]
  w0 = cum
  w1 = total - cum

  with np.errstate(divide="ignore", invalid="ignore"):
    between = (m_all * w0 - mean * total) ** 2 / (w0 * w1)
  between = np.nan_to_num(between)
  t = int(np.argmax(between))
  return max(INK_MIN, min(INK_MAX, t))

def _runs(ink, min_len: int):
  import numpy as np
  h, w = ink.shape
  bridged = ink.copy()
  for g in range(1, BRIDGE_PX + 1):
   
    left = np.zeros_like(ink)
    right = np.zeros_like(ink)
    left[:, g + 1:] = ink[:, :-(g + 1)]
    right[:, :-(g + 1)] = ink[:, g + 1:]
    bridged |= (left & right)
  pad = np.zeros((h, w + 2), dtype="int8")
  pad[:, 1:-1] = bridged
  d = np.diff(pad, axis=1)
  sr, sc = np.nonzero(d == 1)
  er, ec = np.nonzero(d == -1)
  keep = (ec - sc) >= min_len
  return sr[keep], sc[keep], ec[keep]

def _bars(rows, starts, ends, min_overlap: float, max_thick: int):
  rows, starts, ends = rows.tolist(), starts.tolist(), ends.tolist()
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
      if starts[j] >= ends[k]:
        break
      ov = min(ends[k], ends[j]) - max(starts[k], starts[j])
      if ov > 0 and ov >= min_overlap * min(ends[k] - starts[k], ends[j] - starts[j]):
        a, b = find(k), find(j)
        if a != b:
          parent[a] = b
      j += 1

  groups: dict = {}
  for k in range(n):
    groups.setdefault(find(k), []).append(k)
  out = []
  for g in groups.values():
    r0, r1 = min(rows[k] for k in g), max(rows[k] for k in g)
    if r1 - r0 + 1 > max_thick + 2:
      continue

    longest = max(ends[k] - starts[k] for k in g)
    core = [k for k in g if ends[k] - starts[k] >= 0.5 * longest]
    x0, x1 = min(starts[k] for k in core), max(ends[k] for k in core)
    area = sum(ends[k] - starts[k] for k in g)
    thick = area / float(max(x1 - x0, 1))
    if thick > max_thick:
      continue
    mid = sum((rows[k] + 0.5) * (ends[k] - starts[k]) for k in g) / area
    out.append([x0, x1, r0, r1, thick, mid])
  return out

def find_bars(ink, scale: float, horizontal: bool, deadline: float):
  import numpy as np
  img = ink if horizontal else np.ascontiguousarray(ink.T)
  rows, starts, ends = _runs(img, max(3, int(round(MIN_RUN_PT * scale))))
  if time.monotonic() > deadline or len(rows) == 0:
    return []
  bars = _bars(rows, starts, ends, MIN_OVERLAP, int(round(MAX_BAR_PT * scale)))
  out = []
  for s, e, r0, r1, thick, mid in bars:
    out.append((float(s), float(e), float(mid), float(thick)))
  return _same_pen(_drop_fringe(_join(out, int(round(JOIN_GAP_PT * scale)))), int(round(CHAIN_GAP_PT * scale)))

def _drop_fringe(bars: list) -> list:
  import bisect
  order = sorted(range(len(bars)), key=lambda i: bars[i][2])
  centres = [bars[i][2] for i in order]
  heavy_max = max((b[3] for b in bars), default=0.0)
  drop: set = set()

  for i, b in enumerate(bars):
    a0, a1, c, t = b
    reach = heavy_max / 2.0 + FRINGE_PX
    lo = bisect.bisect_left(centres, c - reach)
    hi = bisect.bisect_right(centres, c + reach)
    for k in range(lo, hi):
      j = order[k]
      if j == i:
        continue
      o = bars[j]

      if o[3] < t + FRINGE_THICKER_PX or abs(o[2] - c) > o[3] / 2.0 + FRINGE_PX:
        continue
      ov = min(a1, o[1]) - max(a0, o[0])
      if ov >= FRINGE_OVERLAP * (a1 - a0):
        drop.add(i)
        break
  return [b for i, b in enumerate(bars) if i not in drop]

def _same_pen(bars: list, gap: int) -> list:
  order = sorted(range(len(bars)), key=lambda i: (round(bars[i][2]), bars[i][0]))
  chains: list = []
  for i in order:
    b = bars[i]
    placed = False
    for ch in reversed(chains[-12:]):
      last = bars[ch[-1]]
      if abs(last[2] - b[2]) <= CHAIN_OFFSET_PX and b[0] - last[1] <= gap and b[1] >= last[0]:
        ch.append(i)
        placed = True
        break
    if not placed:
      chains.append([i])

  out = list(bars)
  for ch in chains:
    total = sum(bars[i][1] - bars[i][0] for i in ch)
    if len(ch) < 2 or total <= 0:
      continue
    t = sum((bars[i][1] - bars[i][0]) * bars[i][3] for i in ch) / total
    c = sum((bars[i][1] - bars[i][0]) * bars[i][2] for i in ch) / total
    for i in ch:
      a0, a1, _, _ = bars[i]
      out[i] = (a0, a1, c, t)
  return out

def _join(bars: list, gap: int) -> list:
  bars.sort(key=lambda b: (round(b[2] * 2), b[0]))
  merged: list = []
  for b in bars:
    if merged:
      m = merged[-1]
      if abs(m[2] - b[2]) <= 1.0 and abs(m[3] - b[3]) <= 1.5 and 0 <= b[0] - m[1] <= gap:
        merged[-1] = (m[0], max(m[1], b[1]), m[2], max(m[3], b[3]))
        continue
    merged.append(b)
  return merged

def pen_levels(items: list) -> dict:
  weight: dict = {}
  for length, px in items:
    k = round(px * 4) / 4.0
    weight[k] = weight.get(k, 0.0) + length

  free = dict(weight)
  out: dict = {}
  while free:
    peak = max(free, key=lambda k: free[k])
    group = [k for k in free if abs(k - peak) <= PEN_JITTER_PX or (k > 0 and peak > 0 and max(k, peak) / min(k, peak) <= PEN_RATIO)]
    total = sum(free[k] for k in group)
    mean = sum(k * free[k] for k in group) / total if total > 0 else float(peak)
    for k in group:
      out[k] = mean
      del free[k]
  return out

def segments_from_image(gray, scale: float, deadline: float, arcs: bool = True) -> list:
  import numpy as np
  from app.modules.drawings_boq.takeoff.prep import raster_arcs as RA
  arr = np.asarray(gray, dtype="uint8")
  level = ink_level(arr)
  ink = arr < level
  raw: list = []
  for horizontal in (True, False):
    for a0, a1, b, t in find_bars(ink, scale, horizontal, deadline):
      length = (a1 - a0) / scale
      if length < MIN_SEG_PT:
        continue
      raw.append((horizontal, a0, a1, b, t, length))

  levels = pen_levels([(r[5], r[4]) for r in raw])
  segs: list = []
  for horizontal, a0, a1, b, t, length in raw:
    w = levels.get(round(t * 4) / 4.0, t) / scale
    if horizontal:
      segs.append((a0 / scale, b / scale, a1 / scale, b / scale, w, 0))
    else:
      segs.append((b / scale, a0 / scale, b / scale, a1 / scale, w, 0))
  if len(segs) > MAX_SEGMENTS:
    segs.sort(key=lambda s: -math.hypot(s[2] - s[0], s[3] - s[1]))
    segs = segs[:MAX_SEGMENTS]
  if arcs and time.monotonic() < deadline:
    try:
      segs.extend(RA.find_curves(ink, [(r[0], r[1], r[2], r[3], r[4]) for r in raw], scale, deadline))
    except Exception:
      pass
  return segs

def _unskew_point(x: float, y: float, phi: float, cx: float, cy: float) -> tuple:
  r = math.radians(phi)
  dx, dy = x - cx, y - cy
  return cx + dx * math.cos(r) - dy * math.sin(r), cy + dx * math.sin(r) + dy * math.cos(r)

def lines_of_picture(gray, scale: float, deadline: float, skew_fn=None, back: bool = True) -> tuple:
  from PIL import Image
  phi = 0.0
  if skew_fn is not None:
    try:
      phi = float(skew_fn(gray))
    except Exception:
      phi = 0.0
  work = gray.rotate(phi, resample=Image.BICUBIC, fillcolor=255) if phi else gray
  segs = segments_from_image(work, scale, deadline)
  if phi and back:
    cx, cy = work.size[0] / scale / 2.0, work.size[1] / scale / 2.0
    segs = [(*_unskew_point(s[0], s[1], phi, cx, cy), *_unskew_point(s[2], s[3], phi, cx, cy), s[4], s[5]) for s in segs]
  return segs, phi

def line_dpi(images: list) -> float:
  best = max((im.get("dpi") or 0.0 for im in images), default=0.0)
  if best <= 0:
    return LINE_DPI
  return max(MIN_DPI, min(LINE_DPI, best))

def read_page(page, rotation: int, cropbox: tuple, images: list, budget_s: float = BUDGET_S) -> tuple:
  from app.modules.drawings_boq.takeoff.prep import ocr_layer
  info: dict = {"source": "PICTURE"}
  if not ENABLED:
    info["error"] = "DISABLED"
    return [], info
  try:
    import numpy
    import PIL
  except ImportError:
    info["error"] = "UNAVAILABLE"
    return [], info
  started = time.monotonic()
  scale = line_dpi(images) / 72.0
  try:
    w_pt, h_pt = page.get_size()
    longest = max(w_pt, h_pt) * scale
    if longest > MAX_SIDE_PX:
      scale *= MAX_SIDE_PX / longest
    gray = page.render(scale=scale).to_pil().convert("L")
  except Exception:
    info["error"] = "RENDER"
    return [], info
  try:
    view_segs, phi = lines_of_picture(gray, scale, started + max(5.0, budget_s), lambda g: ocr_layer.skew_angle(g, SKEW_MIN_DEG))
  except Exception:
    info["error"] = "ENGINE"
    return [], info

  segs: list = []
  arcs = 0
  for x0, y0, x1, y1, w, kind in view_segs:
    a = ocr_layer.view_to_user(x0, y0, rotation, cropbox)
    b = ocr_layer.view_to_user(x1, y1, rotation, cropbox)
    segs.append((a[0], a[1], b[0], b[1], w, kind))
    arcs += kind
  info.update(segments=len(segs), arc_pieces=arcs, dpi=round(scale * 72.0, 1), elapsed_s=round(time.monotonic() - started, 2))
  if phi:
    info["deskew_deg"] = phi
  if len(view_segs) >= MAX_SEGMENTS:
    info["capped"] = True
  return segs, info

VECTOR_ENOUGH = 30.0

def add_to_page(out, page, budget_s: float = BUDGET_S) -> dict:
  diag = math.hypot(out.width_pt, out.height_pt)
  s = out.segs
  have = sum(math.hypot(s[5 * i + 2] - s[5 * i], s[5 * i + 3] - s[5 * i + 1]) for i in range(len(out.kinds)))
  if have >= VECTOR_ENOUGH * diag:
    return {"skipped": "VECTOR_PRESENT"}
  segs, info = read_page(page, out.rotation, out.cropbox, out.images, budget_s)
  for seg in segs:
    out.segs.extend(seg[:5])
    out.kinds.append(seg[5])
  return info