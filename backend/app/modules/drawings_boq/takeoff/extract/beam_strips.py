from __future__ import annotations
import math
import numpy as np
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.extract import beam_dashed as BDA

HATCH_ANGLE_TOL_DEG = 6.0
HATCH_MIN_MM = 60.0
HATCH_MAX_MM = 800.0
LINK_PT = 3.0
GRID_PT = 0.25
CLOSE_FACTOR = 1.2
WIDTH_MIN_MM = 100.0
WIDTH_MAX_MM = 600.0
LEG_MIN_WIDTHS = 2.0
CROSS_MAX_WIDTHS = 1.3
LEG_MIN_MM = 600.0
MIN_PATCH_STROKES = 12
MARK_REACH_MM = 1000.0
AMBIGUOUS_RATIO = 1.25
JOIN_TOL_FACTOR = 0.75
MAX_CELLS = 4_000_000

def hatch_strokes(segments: list, mm_per_pt: float) -> list:
  """The short lines at 45 degrees that fill a strip: [(x1, y1, x2, y2)] from segments (x1, y1, x2, y2, kind)."""
  out = []
  for s in segments:
    dx, dy = s[2] - s[0], s[3] - s[1]
    ln = math.hypot(dx, dy) * mm_per_pt
    if ln < HATCH_MIN_MM or ln > HATCH_MAX_MM:
      continue
  
    a = math.degrees(math.atan2(dy, dx)) % 180.0
    if abs(a - 45.0) <= HATCH_ANGLE_TOL_DEG or abs(a - 135.0) <= HATCH_ANGLE_TOL_DEG:
      out.append((s[0], s[1], s[2], s[3]))
  return out

def components(strokes: list, unit: float = 1.0) -> list:
  """Strokes whose middles lie within LINK_PT of each other form one patch of hatch: [[stroke, ...]]. LINK_PT is the distance on the reference sheet; unit is the sheet's size against it."""
  cell = LINK_PT * unit
  mids = [((s[0] + s[2]) / 2.0, (s[1] + s[3]) / 2.0) for s in strokes]
  grid: dict = {}
  for i, m in enumerate(mids):
    grid.setdefault((int(m[0] // cell), int(m[1] // cell)), []).append(i)
  seen: set = set()
  out = []
  
  for i in range(len(mids)):
    if i in seen:
      continue
    seen.add(i)
    stack, comp = [i], [i]
    while stack:
      j = stack.pop()
      
      gx, gy = int(mids[j][0] // cell), int(mids[j][1] // cell)
      for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
          for k in grid.get((gx + dx, gy + dy), ()):
            if k not in seen and math.hypot(mids[k][0] - mids[j][0], mids[k][1] - mids[j][1]) <= cell:
              seen.add(k)
              stack.append(k)
              comp.append(k)
    out.append([strokes[k] for k in comp])
  return out

def _pitch(strokes: list) -> float:
  """The usual distance between neighbouring hatch lines, in points."""
  mids = np.array([((s[0] + s[2]) / 2.0, (s[1] + s[3]) / 2.0) for s in strokes])
  if len(mids) < 3:
    return 1.0
  sub = mids[:: max(1, len(mids) // 400)]
  d = np.hypot(sub[:, None, 0] - mids[None, :, 0], sub[:, None, 1] - mids[None, :, 1])
  d[d < 1e-6] = np.inf
  return float(np.median(d.min(axis=1)))

def _dilate(mask, r: int):
  """Dilation by a square of half-size r cells."""
  pad = np.pad(mask.astype(np.int32), r + 1)
  c = pad.cumsum(0).cumsum(1)
  h, w = mask.shape
  ys, xs = np.arange(h)[:, None] + 1, np.arange(w)[None, :] + 1
  tot = c[ys + 2 * r, xs + 2 * r] - c[ys - 1, xs + 2 * r] - c[ys + 2 * r, xs - 1] + c[ys - 1, xs - 1]
  return tot > 0

def _close(mask, r: int):
  big = np.pad(mask, r + 1)
  closed = ~_dilate(~_dilate(big, r), r)
  return closed[r + 1:-(r + 1), r + 1:-(r + 1)]

def _runs(mask, axis: int):
  """For each True cell, the length in cells of the run of True cells it lies in, along a row (axis 1) or a column (axis 0)."""
  m = mask if axis == 1 else mask.T
  out = np.zeros(m.shape, dtype=np.int32)
  for i in range(m.shape[0]):
    row = m[i]
    
    if not row.any():
      continue
    d = np.diff(np.concatenate(([0], row.astype(np.int8), [0])))
    for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)):
      out[i, a:b] = b - a
  return out if axis == 1 else out.T

def _label(mask):
  """Connected cells (4 neighbours): (labels, count)."""
  h, w = mask.shape
  lab = np.zeros((h, w), dtype=np.int32)
  n = 0
  for y, x in zip(*np.nonzero(mask)):
    if lab[y, x]:
      continue
  
    n += 1
    lab[y, x] = n
    stack = [(int(y), int(x))]
    while stack:
      cy, cx = stack.pop()
      for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
        if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not lab[ny, nx]:
          lab[ny, nx] = n
          stack.append((ny, nx))
  return lab, n

def legs_of(strokes: list, mm_per_pt: float, unit: float = 1.0) -> list:
  """The straight legs of one patch of hatch: [{"axis": "H" | "V", "p0", "p1", "width_pt", "length_pt"}], p0 and p1 the ends of the centre line (page units).
  The width is that of the hatched band, the length runs end to end on the centre line."""
  xs = [v for s in strokes for v in (s[0], s[2])]
  ys = [v for s in strokes for v in (s[1], s[3])]
  g = GRID_PT * unit
  r = max(2, int(round(CLOSE_FACTOR * _pitch(strokes) / g)))
  
  x0, y0 = min(xs) - (r + 2) * g, min(ys) - (r + 2) * g
  wc, hc = int((max(xs) - x0) / g) + r + 4, int((max(ys) - y0) / g) + r + 4
  if wc * hc > MAX_CELLS:
    return []
  mask = np.zeros((hc, wc), dtype=bool)
  for s in strokes:
    n = max(2, int(math.hypot(s[2] - s[0], s[3] - s[1]) / (g * 0.5)) + 1)
    for k in range(n + 1):
      t = k / n
      mask[int((s[1] + (s[3] - s[1]) * t - y0) / g), int((s[0] + (s[2] - s[0]) * t - x0) / g)] = True
      
  mask = _close(mask, r)
  hr, vr = _runs(mask, 1), _runs(mask, 0)
  lo, hi = WIDTH_MIN_MM / mm_per_pt / g, WIDTH_MAX_MM / mm_per_pt / g
  short = np.minimum(hr, vr)[mask]
  short = short[(short >= lo) & (short <= hi)]
  if short.size < 8:
    return []

  vals, cnt = np.unique(short, return_counts=True)
  w = float(vals[int(np.argmax(cnt))])
  hcell = mask & (hr >= LEG_MIN_WIDTHS * w) & (vr <= CROSS_MAX_WIDTHS * w)
  vcell = mask & (vr >= LEG_MIN_WIDTHS * w) & (hr <= CROSS_MAX_WIDTHS * w)
  other = mask & ~hcell & ~vcell
  out = []
  
  for axis, cells in (("H", hcell), ("V", vcell)):
    lab, n = _label(cells)
    for k in range(1, n + 1):
      yy, xx = np.nonzero(lab == k)
      ya, yb, xa, xb = int(yy.min()), int(yy.max()), int(xx.min()), int(xx.max())
      if axis == "H":
        corner0 = xa > 0 and bool(other[ya:yb + 1, xa - 1].any())
        corner1 = xb + 1 < wc and bool(other[ya:yb + 1, xb + 1].any())
        width = (yb - ya + 1) * g
        c = y0 + (ya + yb + 1) / 2.0 * g
        p0, p1 = (x0 + xa * g - (0.5 * width if corner0 else 0.0), c), (x0 + (xb + 1) * g + (0.5 * width if corner1 else 0.0), c)
      else:
        corner0 = ya > 0 and bool(other[ya - 1, xa:xb + 1].any())
        corner1 = yb + 1 < hc and bool(other[yb + 1, xa:xb + 1].any())
        width = (xb - xa + 1) * g
        c = x0 + (xa + xb + 1) / 2.0 * g
        p0, p1 = (c, y0 + ya * g - (0.5 * width if corner0 else 0.0)), (c, y0 + (yb + 1) * g + (0.5 * width if corner1 else 0.0))
      length = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
      
      if length * mm_per_pt < LEG_MIN_MM:
        continue
      out.append({"axis": axis, "p0": p0, "p1": p1, "width_pt": width, "length_pt": length, "corners": (corner0, corner1)})
  return out

def _axis_lines(segments: list) -> tuple:
  """The lines that run along the page, as ([(y, x_from, x_to)], [(x, y_from, y_to)]): the edges of a strip are among them."""
  h, v = [], []
  for sg in segments:
    x1, y1, x2, y2 = sg[0], sg[1], sg[2], sg[3]
    if abs(y2 - y1) <= 0.02 and abs(x2 - x1) >= 0.5:
      h.append(((y1 + y2) / 2.0, min(x1, x2), max(x1, x2)))
    elif abs(x2 - x1) <= 0.02 and abs(y2 - y1) >= 0.5:
      v.append(((x1 + x2) / 2.0, min(y1, y2), max(y1, y2)))
  return h, v

EDGE_SPACING = (0.8, 1.2)
EDGE_MIN_COVER = 0.4

def _refine_edges(leg: dict, lines: tuple) -> None:
  """The strip is bounded by two lines a beam width apart. When both are drawn along the leg, the width and the centre line are taken from them (the hatch
  alone gives them only to a quarter of a point)."""
  h, v = lines
  horizontal = leg["axis"] == "H"
  cand = h if horizontal else v
  a0 = min(leg["p0"][0], leg["p1"][0]) if horizontal else min(leg["p0"][1], leg["p1"][1])
  a1 = max(leg["p0"][0], leg["p1"][0]) if horizontal else max(leg["p0"][1], leg["p1"][1])
  c = leg["p0"][1] if horizontal else leg["p0"][0]
  w = leg["width_pt"]
  low: dict = {}
  high: dict = {}
  
  for cc, lo, hi in cand:
    if abs(cc - c) > 0.8 * w or abs(cc - c) < 0.3 * w:
      continue
    ov = min(hi, a1) - max(lo, a0)
    if ov <= 0:
      continue
    side = low if cc < c else high
    cover, weighted = side.get(round(cc, 1), (0.0, 0.0))
    side[round(cc, 1)] = (cover + ov, weighted + ov * cc)
  best = None
  
  for ol, wl in low.values():
    for oh, wh in high.values():
      yl, yh = wl / ol, wh / oh
      if not (EDGE_SPACING[0] * w <= yh - yl <= EDGE_SPACING[1] * w) or min(ol, oh) < EDGE_MIN_COVER * (a1 - a0):
        continue
    
      if best is None or ol + oh > best[0]:
        best = (ol + oh, yl, yh)
  if best is None:
    return
  yl, yh = best[1], best[2]
  leg["width_pt"] = yh - yl
  mid = (yl + yh) / 2.0
  if horizontal:
    leg["p0"], leg["p1"] = (leg["p0"][0], mid), (leg["p1"][0], mid)
  else:
    leg["p0"], leg["p1"] = (mid, leg["p0"][1]), (mid, leg["p1"][1])
  leg["edges"] = True

def _dist_to_leg(leg: dict, x: float, y: float) -> float:
  (ax, ay), (bx, by) = leg["p0"], leg["p1"]
  vx, vy = bx - ax, by - ay
  ln2 = vx * vx + vy * vy
  s = 0.0 if ln2 <= 0 else max(0.0, min(1.0, ((x - ax) * vx + (y - ay) * vy) / ln2))
  return math.hypot(x - (ax + s * vx), y - (ay + s * vy))

def _text_axis(angle: float) -> str:
  """The way a word runs on the page: "H" (upright or upside down) or "V" (turned a quarter)."""
  a = float(angle or 0.0) % 180.0
  return "H" if a < 45.0 or a >= 135.0 else "V"

def _ends(leg: dict) -> list:
  return [leg["p0"], leg["p1"]]

def _meets(a: dict, b: dict, tol: float) -> bool:
  """The two legs touch: an end of one lies on the centre line of the other."""
  return any(_dist_to_leg(b, *p) <= tol for p in _ends(a)) or any(_dist_to_leg(a, *p) <= tol for p in _ends(b))

def _collinear(a: dict, b: dict, tol: float) -> bool:
  if a["axis"] != b["axis"]:
    return False
  return abs((a["p0"][1] - b["p0"][1]) if a["axis"] == "H" else (a["p0"][0] - b["p0"][0])) <= tol

def assign(legs: list, marks: list, mm_per_pt: float) -> dict:
  stats = {"unplaced": {}, "conflicts": 0, "inherited": 0}
  reach = MARK_REACH_MM / mm_per_pt
  for leg in legs:
    leg["tag"], leg["via"], leg["labels"] = None, None, set()
  for tag, x, y, angle in marks:
    near = sorted((_dist_to_leg(leg, x, y), i) for i, leg in enumerate(legs))
    near = [n for n in near if n[0] <= reach]
    if not near:
      stats["unplaced"][tag] = stats["unplaced"].get(tag, 0) + 1
      continue
  
    best = near[0]
    close = [n for n in near if n[0] <= best[0] * AMBIGUOUS_RATIO]
    if len(close) > 1:
      parallel = [n for n in close if legs[n[1]]["axis"] == _text_axis(angle)]
      if len(parallel) == 1:
        best = parallel[0]
      elif parallel:
        best = parallel[0] if all(legs[n[1]]["labels"] | {tag} == legs[parallel[0][1]]["labels"] | {tag} for n in parallel) else best
    legs[best[1]]["labels"].add(tag)
  for leg in legs:
    if len(leg["labels"]) == 1:
      leg["tag"], leg["via"] = next(iter(leg["labels"])), "LABEL"
    elif len(leg["labels"]) > 1:
      stats["conflicts"] += 1
  for _ in range(len(legs)):
    moved = False
    
    for leg in legs:
      if leg["tag"] is not None or leg["labels"]:
        continue
      tol = JOIN_TOL_FACTOR * leg["width_pt"]
      joined = [o for o in legs if o is not leg and o["tag"] is not None and _meets(leg, o, tol)]
      straight = {o["tag"] for o in joined if _collinear(leg, o, tol)}
      if len(straight) == 1:
        leg["tag"], leg["via"] = next(iter(straight)), "CONTINUES"
        
      else:
        bent = {o["tag"] for o in joined if o["axis"] != leg["axis"]}
        arms = [o for o in legs if o is not leg and _meets(leg, o, tol)]
        if not straight and len(bent) == 1 and len(arms) == 1:
          leg["tag"], leg["via"] = next(iter(bent)), "BEND"
      if leg["tag"] is not None:
        stats["inherited"] += 1
        moved = True
    if not moved:
      break
  return stats

def _span(leg: dict) -> tuple:
  i = 0 if leg["axis"] == "H" else 1
  a, b = leg["p0"][i], leg["p1"][i]
  return (a, b) if a <= b else (b, a)

def _line(leg: dict) -> float:
  return leg["p0"][1] if leg["axis"] == "H" else leg["p0"][0]

def _crossing(legs: list, a: dict, b: dict, lo: float, hi: float, pad_pt: float) -> dict | None:
  """The widest leg of the other axis whose centre line passes through the stretch between the inner ends of a and b: the beam that cut them in two."""
  mid, line = (lo + hi) / 2.0, (_line(a) + _line(b)) / 2.0
  point = (mid, line) if a["axis"] == "H" else (line, mid)
  best = None
  for o in legs:
    if o is a or o is b or o["axis"] == a["axis"]:
      continue
    if _dist_to_leg(o, *point) <= 0.5 * o["width_pt"] + pad_pt and (best is None or o["width_pt"] > best["width_pt"]):
      best = o
  return best

def _can_join(legs: list, a: dict, b: dict, mm_per_pt: float) -> bool:
  """a and b run along one line, carry the same mark or no mark, and a beam crosses between them: the gap is no wider than that beam plus BEAM_JOIN_PAD_MM, or they overlap by no more than a width."""
  if a["axis"] != b["axis"] or abs(_line(a) - _line(b)) > JOIN_TOL_FACTOR * min(a["width_pt"], b["width_pt"]):
    return False
  if a["tag"] is not None and b["tag"] is not None and a["tag"] != b["tag"]:
    return False
  (a_lo, a_hi), (b_lo, b_hi) = _span(a), _span(b)
  if b_lo < a_lo:
    a_lo, a_hi, b_lo, b_hi = b_lo, b_hi, a_lo, a_hi
  gap = b_lo - a_hi
  pad_pt = C.BEAM_JOIN_PAD_MM / mm_per_pt
  cross = _crossing(legs, a, b, min(a_hi, b_lo), max(a_hi, b_lo), pad_pt)
  if cross is None:
    return False
  return gap <= cross["width_pt"] + pad_pt if gap > 0 else -gap <= max(a["width_pt"], b["width_pt"])

def _merged(a: dict, b: dict, mm_per_pt: float) -> dict:
  (a_lo, a_hi), (b_lo, b_hi) = _span(a), _span(b)
  lo, hi = min(a_lo, b_lo), max(a_hi, b_hi)
  la, lb = a["length_pt"], b["length_pt"]
  longer = a if la >= lb else b
  tagged = a if a["tag"] is not None else b
  line = (_line(a) * la + _line(b) * lb) / (la + lb)
  p0, p1 = ((lo, line), (hi, line)) if a["axis"] == "H" else ((line, lo), (line, hi))
  delta = float(a.get("join_delta_mm") or 0.0) + float(b.get("join_delta_mm") or 0.0) + ((hi - lo) - (la + lb)) * mm_per_pt
  return {**longer, "p0": p0, "p1": p1, "length_pt": hi - lo, "tag": tagged["tag"], "via": tagged["via"], "labels": set(a["labels"]) | set(b["labels"]),
    "joined": int(a.get("joined") or 0) + int(b.get("joined") or 0) + 1, "join_delta_mm": delta}

def join_across(legs: list, mm_per_pt: float) -> int:
  joins = 0
  while True:
    pair = next(((i, j) for i in range(len(legs)) for j in range(i + 1, len(legs)) if _can_join(legs, legs[i], legs[j], mm_per_pt)), None)
    if pair is None:
      return joins
    i, j = pair
    legs[i] = _merged(legs[i], legs[j], mm_per_pt)
    del legs[j]
    joins += 1

def read(segments: list, marks: list, mm_per_pt: float, unit: float = 1.0, dashed: bool = False) -> dict:
  """The hatched beams of one plan. segments: the lines inside the plan, (x1, y1, x2, y2, kind); marks: [(tag, x, y, angle)] its beam marks.
  Returns {"legs": [{"axis", "p0", "p1", "width_mm", "length_mm", "tag", "via"}], "unplaced": {tag: n}, "conflicts": n, "inherited": n}."""
  strokes = hatch_strokes(segments, mm_per_pt)
  legs: list = []
  
  for comp in components(strokes, unit):
    if len(comp) >= MIN_PATCH_STROKES:
      legs.extend(legs_of(comp, mm_per_pt, unit))
  if not legs and dashed:
    legs = BDA.legs(segments, mm_per_pt)
  lines = _axis_lines(segments) if legs else ([], [])
  for leg in legs:
    if not leg.get("dashed"):
      _refine_edges(leg, lines)
  stats = assign(legs, marks, mm_per_pt)
  stats["joins"] = join_across(legs, mm_per_pt)
  out = []
  
  for leg in legs:
    out.append({"axis": leg["axis"], "p0": [round(leg["p0"][0], 3), round(leg["p0"][1], 3)], "p1": [round(leg["p1"][0], 3), round(leg["p1"][1], 3)],
      "width_mm": round(leg["width_pt"] * mm_per_pt, 1), "length_mm": round(leg["length_pt"] * mm_per_pt, 1), "tag": leg["tag"], "via": leg["via"],
      "joined": int(leg.get("joined") or 0), "join_delta_mm": round(float(leg.get("join_delta_mm") or 0.0), 1), **({"dashed": True} if leg.get("dashed") else {})})
  out.sort(key=lambda l: (str(l["tag"] or "~"), l["axis"], l["p0"]))
  return {"legs": out, "unplaced": stats["unplaced"], "conflicts": stats["conflicts"], "inherited": stats["inherited"], "joins": stats["joins"]}

def by_tag(result: dict) -> dict:
  """{tag: [leg, ...]} for the legs that have a mark, and the legs that have none under None."""
  out: dict = {}
  for leg in result["legs"]:
    out.setdefault(leg["tag"], []).append(leg)
  return out
