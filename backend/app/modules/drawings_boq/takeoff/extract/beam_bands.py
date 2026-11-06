from __future__ import annotations
import numpy as np
from app.engine.measure import rule_registry as RR
from app.modules.drawings_boq.takeoff.prep.details import norm_mark
from app.modules.drawings_boq.takeoff.prep import views as VW

INCH_MM = 25.4
WIDTH_MIN_IN = 6.0
WIDTH_MAX_IN = 30.0
ASPECT_MIN = 3.0
GAP_MERGE_IN = 18.0
LABEL_RADIUS_IN = 30.0
WIDTH_AGREE_IN = 1.0
WIDTH_CONFLICT_IN = 3.5
INK_MAX_A3 = 2.5
FUSE_A3 = 3.0
INK_PER_RUN_MIN = 6
DENSITY_MAX = 2.0
SPREAD_BINS = 3
SPREAD_MIN = 0.12
EDGE_TRIM = 0.02
ANGLE_TOL_DEG = 12.0
SUPPORT_REACH_FACTOR = 1.0
CURVE_KIND = 2

def _inch_pt(inches: float, mm_per_pt: float) -> float:
  return inches * INCH_MM / mm_per_pt

def ink_points(segs: np.ndarray, kinds, words: list, unit: float = 1.0) -> np.ndarray:
  if len(segs) == 0:
    return np.zeros((0, 2))
  ln = np.hypot(segs[:, 2] - segs[:, 0], segs[:, 3] - segs[:, 1])
  keep = ln < INK_MAX_A3 * unit
  if kinds is not None:
    keep &= (np.asarray(kinds, dtype=int) == 0)
    
  mid = np.c_[(segs[keep, 0] + segs[keep, 2]) / 2.0, (segs[keep, 1] + segs[keep, 3]) / 2.0]
  for w in words or []:
    r = max(float(w[4]), float(w[5]), 1.0) / 2.0 + 1.0
    near = (np.abs(mid[:, 0] - w[1]) <= r) & (np.abs(mid[:, 1] - w[2]) <= r)
    mid = mid[~near]
  return mid

def _grid(ink: np.ndarray, cell: float, box: tuple) -> tuple:
  x0, y0, x1, y1 = box
  w, h = int((x1 - x0) / cell) + 3, int((y1 - y0) / cell) + 3
  g = np.zeros((h, w), dtype=bool)
  if len(ink):
    ix = np.clip(((ink[:, 0] - x0) / cell).astype(int), 0, w - 1)
    iy = np.clip(((ink[:, 1] - y0) / cell).astype(int), 0, h - 1)
    g[iy, ix] = True
  return g, (x0, y0, cell)

def _dilate(mask: np.ndarray, r: int) -> np.ndarray:
  pad = np.pad(mask.astype(np.int32), r + 1)
  c = pad.cumsum(0).cumsum(1)
  h, w = mask.shape
  k = 2 * r + 1
  s = c[k:k + h, k:k + w] - c[:h, k:k + w] - c[k:k + h, :w] + c[:h, :w]
  return s > 0

def _runs_axis(mask: np.ndarray, min_len: int) -> np.ndarray:
  out = np.zeros_like(mask)
  for i in range(mask.shape[0]):
    row = mask[i]
    if not row.any():
      continue
    d = np.diff(np.r_[0, row.view(np.int8), 0])
    starts, ends = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
    for a, b in zip(starts, ends):
      if b - a >= min_len:
        out[i, a:b] = True
  return out

def _label(mask: np.ndarray) -> tuple:
  lab = np.zeros(mask.shape, dtype=np.int32)
  n = 0
  ys, xs = np.nonzero(mask)
  h, w = mask.shape
  for y0, x0 in zip(ys.tolist(), xs.tolist()):
    if lab[y0, x0]:
      continue
  
    n += 1
    stack = [(y0, x0)]
    lab[y0, x0] = n
    while stack:
      y, x = stack.pop()
      for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
          yy, xx = y + dy, x + dx
          if 0 <= yy < h and 0 <= xx < w and mask[yy, xx] and not lab[yy, xx]:
            lab[yy, xx] = n
            stack.append((yy, xx))
  return lab, n

def find_bands(ink: np.ndarray, mm_per_pt: float, unit: float, box: tuple) -> tuple:
  rej = {"TOO_NARROW": 0, "TOO_WIDE": 0, "TOO_SHORT": 0, "TOO_SPARSE": 0, "TOO_DENSE": 0}
  if len(ink) == 0:
    return [], rej
  cell = unit
  
  g, (ox, oy, _) = _grid(ink, cell, box)
  r = max(int(round(FUSE_A3 * unit / cell)), 1)
  fused = _dilate(g, r)
  wmin, wmax = _inch_pt(WIDTH_MIN_IN, mm_per_pt), _inch_pt(WIDTH_MAX_IN, mm_per_pt)
  
  out: list = []
  for axis in ("H", "V"):
    m = fused if axis == "H" else fused.T
    run = _runs_axis(m, max(int(ASPECT_MIN * (wmin + 2 * r * cell) / cell), 3))
    lab, n = _label(run)
    for k in range(1, n + 1):
      ys, xs = np.nonzero(lab == k)
      lo, hi = int(xs.min()), int(xs.max()) + 1
      across_min, across_max = int(ys.min()), int(ys.max()) + 1
      if axis == "H":
        sel = (ink[:, 0] >= ox + lo * cell) & (ink[:, 0] <= ox + hi * cell) & (ink[:, 1] >= oy + across_min * cell) & (ink[:, 1] <= oy + across_max * cell)
        pts_across, pts_along = ink[sel, 1], ink[sel, 0]
      else:
        sel = (ink[:, 1] >= oy + lo * cell) & (ink[:, 1] <= oy + hi * cell) & (ink[:, 0] >= ox + across_min * cell) & (ink[:, 0] <= ox + across_max * cell)
        pts_across, pts_along = ink[sel, 0], ink[sel, 1]
      if len(pts_across) < INK_PER_RUN_MIN:
        rej["TOO_SPARSE"] += 1
        continue
      a_lo, a_hi = float(np.percentile(pts_across, 100 * EDGE_TRIM)), float(np.percentile(pts_across, 100 - 100 * EDGE_TRIM))
      width = a_hi - a_lo
      if width < wmin:
        rej["TOO_NARROW"] += 1
        continue
      if width > wmax:
        rej["TOO_WIDE"] += 1
        continue
      counts, _ = np.histogram(pts_across, bins=SPREAD_BINS, range=(a_lo, a_hi))
      if counts.min() < SPREAD_MIN * len(pts_across):
        rej["TOO_SPARSE"] += 1
        continue
      l_lo, l_hi = float(pts_along.min()), float(pts_along.max())
      if l_hi - l_lo < ASPECT_MIN * width:
        rej["TOO_SHORT"] += 1
        continue
      if len(pts_across) / max(width * (l_hi - l_lo), 1e-6) > DENSITY_MAX / (unit * unit):
        rej["TOO_DENSE"] += 1
        continue
      out.append({"axis": axis, "c0": a_lo, "c1": a_hi, "lo": l_lo, "hi": l_hi, "ink": int(len(pts_across)), "source": "DOTS"})
      
  return out, rej

def from_strips(legs: list, mm_per_pt: float) -> list:
  out = []
  for leg in legs or []:
    (x0, y0), (x1, y1) = leg["p0"], leg["p1"]
    half = float(leg["width_mm"]) / mm_per_pt / 2.0
    if abs(y1 - y0) <= 0.05 * max(abs(x1 - x0), 1e-6):
      out.append({"axis": "H", "c0": (y0 + y1) / 2.0 - half, "c1": (y0 + y1) / 2.0 + half, "lo": min(x0, x1), "hi": max(x0, x1), "ink": 0, "source": "HATCH", "tag": leg.get("tag")})
    elif abs(x1 - x0) <= 0.05 * max(abs(y1 - y0), 1e-6):
      out.append({"axis": "V", "c0": (x0 + x1) / 2.0 - half, "c1": (x0 + x1) / 2.0 + half, "lo": min(y0, y1), "hi": max(y0, y1), "ink": 0, "source": "HATCH", "tag": leg.get("tag")})
  return out

def _square_between(squares: list | None, axis: str, ctr: float, a: float, b: float, width: float) -> bool:
  for cx, cy, _w, _h in squares or []:
    along, across = (cx, cy) if axis == "H" else (cy, cx)
    if a - width <= along <= b + width and abs(across - ctr) <= width:
      return True
  return False

def merge(bands: list, mm_per_pt: float, squares: list | None = None) -> list:
  gap_pt = _inch_pt(GAP_MERGE_IN, mm_per_pt)
  out: list = []
  
  for axis in ("H", "V"):
    mine = sorted([b for b in bands if b["axis"] == axis], key=lambda b: ((b["c0"] + b["c1"]) / 2.0, b["lo"]))
    done: list = []
    for b in mine:
      for d in done:
        ctr_d, ctr_b = (d["c0"] + d["c1"]) / 2.0, (b["c0"] + b["c1"]) / 2.0
        w_d, w_b = d["c1"] - d["c0"], b["c1"] - b["c0"]
        if abs(ctr_d - ctr_b) > 0.5 * min(w_d, w_b) or abs(w_d - w_b) > 0.35 * max(w_d, w_b):
          continue
      
        gap = max(b["lo"] - d["hi"], d["lo"] - b["hi"])
        if gap <= gap_pt or _square_between(squares, axis, ctr_d, min(d["hi"], b["hi"]), max(d["lo"], b["lo"]), max(w_d, w_b)):
          n = d["ink"] + b["ink"]
          if n:
            d["c0"], d["c1"] = (d["c0"] * d["ink"] + b["c0"] * b["ink"]) / n, (d["c1"] * d["ink"] + b["c1"] * b["ink"]) / n
          d["lo"], d["hi"], d["ink"] = min(d["lo"], b["lo"]), max(d["hi"], b["hi"]), n
          d["source"] = d["source"] if d["source"] == b["source"] else "BOTH"
          d["tag"] = d.get("tag") or b.get("tag")
          break
      else:
        done.append(dict(b))
    out.extend(done)
  return out

def centreline(b: dict) -> list:
  ctr = (b["c0"] + b["c1"]) / 2.0
  if b["axis"] == "H":
    return [[round(b["lo"], 3), round(ctr, 3)], [round(b["hi"], 3), round(ctr, 3)]]
  return [[round(ctr, 3), round(b["lo"], 3)], [round(ctr, 3), round(b["hi"], 3)]]

def supports(bands: list, squares: list | None) -> None:
  for b in bands:
    reach = (b["c1"] - b["c0"]) * SUPPORT_REACH_FACTOR
    b["supports"] = []
    for end in (tuple(centreline(b)[0]), tuple(centreline(b)[1])):
      found = None
      for cx, cy, w, h in squares or []:
        if abs(end[0] - cx) <= w / 2.0 + reach and abs(end[1] - cy) <= h / 2.0 + reach:
          found = {"on": "COLUMN", "at": [round(cx, 3), round(cy, 3)]}
          break
      
      if found is None:
        for o in bands:
          if o is b or o["axis"] == b["axis"]:
            continue
        
          if o["axis"] == "V" and o["c0"] - reach <= end[0] <= o["c1"] + reach and o["lo"] - reach <= end[1] <= o["hi"] + reach:
            found = {"on": "BAND", "at": [round((o["c0"] + o["c1"]) / 2.0, 3), round(end[1], 3)]}
          elif o["axis"] == "H" and o["c0"] - reach <= end[1] <= o["c1"] + reach and o["lo"] - reach <= end[0] <= o["hi"] + reach:
            found = {"on": "BAND", "at": [round(end[0], 3), round((o["c0"] + o["c1"]) / 2.0, 3)]}
          if found:
            break
      b["supports"].append(found)

def _angle_ok(angle: float, axis: str) -> bool:
  a = float(angle or 0.0) % 180.0
  want = 0.0 if axis == "H" else 90.0
  return min(abs(a - want), 180.0 - abs(a - want)) <= ANGLE_TOL_DEG

def label(bands: list, words: list, known: set, mm_per_pt: float) -> dict:
  reach = _inch_pt(LABEL_RADIUS_IN, mm_per_pt)
  marks = [(norm_mark(w[0]), float(w[1]), float(w[2]), w[3]) for w in words or [] if norm_mark(w[0]) in known]
  stats = {"marks": len(marks), "bands_marked": 0, "bands_unmarked": 0}
  for b in bands:
    ctr = (b["c0"] + b["c1"]) / 2.0
    
    near = []
    for text, x, y, ang in marks:
      along, across = (x, y) if b["axis"] == "H" else (y, x)
      if b["lo"] - reach <= along <= b["hi"] + reach and abs(across - ctr) <= (b["c1"] - b["c0"]) / 2.0 + reach and _angle_ok(ang, b["axis"]):
        near.append((abs(across - ctr), along, text))
        
    near.sort()
    b["marks"] = [{"mark": t, "along": round(a, 3)} for _d, a, t in near]
    if b.get("tag") and not near:
      b["marks"] = [{"mark": norm_mark(b["tag"]), "along": round((b["lo"] + b["hi"]) / 2.0, 3)}]
    stats["bands_marked" if b["marks"] else "bands_unmarked"] += 1
  return stats

def read(segs, kinds, words, mm_per_pt: float, box: tuple, *, unit: float = 1.0, squares: list | None = None, known_marks: set | None = None, widths_in: dict | None = None, strips: list | None = None) -> dict:
  if not mm_per_pt or mm_per_pt <= 0:
    return {"bands": [], "rejected": {}, "stats": {"status": "NO_SCALE"}}

  segs = np.asarray(segs, dtype=float).reshape(len(segs), -1)[:, :4] if len(segs) else np.zeros((0, 4))
  ink = ink_points(segs, kinds, words, unit)
  ink = ink[(ink[:, 0] >= box[0]) & (ink[:, 0] <= box[2]) & (ink[:, 1] >= box[1]) & (ink[:, 1] <= box[3])] if len(ink) else ink
  found, rej = find_bands(ink, mm_per_pt, unit, box)
  bands = merge(found + from_strips(strips, mm_per_pt), mm_per_pt, squares)
  supports(bands, squares)
  lstats = label(bands, words, known_marks or set(), mm_per_pt)
  
  out = []
  widths_ok = 0
  for b in bands:
    w_in = (b["c1"] - b["c0"]) * mm_per_pt / INCH_MM
    item = {"axis": b["axis"], "polyline": centreline(b), "width_in": round(w_in, 2), "length_mm": round((b["hi"] - b["lo"]) * mm_per_pt, 1), "ink": b["ink"], "source": b["source"],
      "supports": b["supports"], "marks": b["marks"], "reasons": []}
    
    names = sorted({m["mark"] for m in b["marks"]})
    if not names:
      item["reasons"].append("JOIN_MISSING")
    else:
      item["mark"] = names[0]
      want = sorted({(widths_in or {}).get(n) for n in names if (widths_in or {}).get(n)})
      if want and abs(w_in - min(want, key=lambda x: abs(w_in - x))) <= WIDTH_AGREE_IN:
        widths_ok += 1
      if want and all(abs(w_in - x) > WIDTH_CONFLICT_IN for x in want):
        item["reasons"].append("CONFLICT_IN_DRAWING")
        item["section_width_in"] = want
    out.append(item)
    
  return {"bands": out, "rejected": rej, "stats": {**lstats, "ink": int(len(ink)), "found": len(found), "bands": len(out), "width_within_1in": widths_ok}}

def _widths(sections: list | None) -> dict:
  out: dict = {}
  for s in sections or []:
    mark = norm_mark(str(s.get("mark") or ""))
    w = s.get("width_in") or (float(s["width_mm"]) / INCH_MM if s.get("width_mm") else None)
    if mark and w and not s.get("disagree"):
      out[mark] = float(w)
  return out

def of_page(index, mm_per_pt: float, unit: float, views: list, sections: list | None = None, square_list: list | None = None) -> dict | None:
  from app.modules.drawings_boq.takeoff.extract import structure as ST
  plans = [v for v in views if v.get("structural") and not v.get("foundation")]
  if not plans or not mm_per_pt or not len(index.segs):
    return None

  segs = np.asarray(index.segs, dtype=float).reshape(-1, 5)[:, :4]
  kinds = np.asarray(index.kinds, dtype=int) if index.kinds is not None else None
  words = [(w.text, w.cx, w.cy, w.angle, w.length, w.height) for w in index.words]
  squares = square_list if square_list is not None else ([(s["cx"], s["cy"], s["b"] / mm_per_pt, s["b"] / mm_per_pt) for s in ST.dedupe_solid(ST.square_shapes(index.rings, mm_per_pt), mm_per_pt)] if RR.on("BEAM_BAND_SQUARE_OUTLINES") else [])
  widths = _widths(sections)
  known = set(widths) | {norm_mark(str(s.get("mark"))) for s in sections or [] if s.get("mark")}
  
  out = []
  for v in plans:
    box = tuple(float(x) for x in v["bbox"])
    mine = [w for w in words if VW.contains(v, w[1], w[2])]
    sq = [s for s in squares if box[0] <= s[0] <= box[2] and box[1] <= s[1] <= box[3]]
    res = read(segs, kinds, mine, mm_per_pt, box, unit=unit, squares=sq, known_marks=known, widths_in=widths)
    out.append({"key": v.get("key"), "level_hint": v.get("level_hint"), **res})
  return {"views": out, "mm_per_pt": round(float(mm_per_pt), 5)}
