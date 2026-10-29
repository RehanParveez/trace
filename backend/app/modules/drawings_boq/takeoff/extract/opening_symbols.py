from __future__ import annotations
import math
import contextvars
import numpy as np
import time
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.extract import foundation as FD
from app.modules.drawings_boq.takeoff.extract import opening_labels as OL
from app.modules.drawings_boq.takeoff.extract import label_openings as LO
from app.modules.drawings_boq.takeoff.extract import schedule_scale as SS
from app.modules.drawings_boq.takeoff.prep.texts import build_lines

DASH_MAX_PT = 18.0                 
DASH_MIN_PT = 0.8
R_MIN_PT, R_MAX_PT = 14.0, 120.0
SPAN_MIN, SPAN_MAX = 55.0, 130.0  
ARC_TOL_PT = 1.5
LEAF_COVER_MIN = 0.25          
WALL_BAND_PT = 2.0              
JAMB_REL, JAMB_ABS = 0.14, 1.5   
PICTURE_JAMB_SLACK_PT = 5.0
FROM_PICTURE: contextvars.ContextVar = contextvars.ContextVar("opening_lines_from_picture", default=False)
REF_MM_PER_PT = 26.0               
UNIT_PT: contextvars.ContextVar = contextvars.ContextVar("opening_unit_pt", default=1.0)

def _u() -> float:
  return UNIT_PT.get()

def unit_for(mm_per_pt: float) -> float:
  return min(max(REF_MM_PER_PT / mm_per_pt, 0.2), 5.0) if mm_per_pt and mm_per_pt > 0 else 1.0
HEAVY_SHARE = 0.6
BIN_MIN, SPAN_BINS_MIN = 10, 85.0   
SWING_MM = (450.0, 1300.0)     
SWING_MM_UNVERIFIED = (350.0, 1700.0)
DOUBLE_TOL = 0.12
END_TOL = 30.0                 
WINDOW_LINES_MIN = 3
WINDOW_COVER_MIN = 0.7
WINDOW_MIN_MM, WINDOW_MAX_MM = 450.0, 4500.0
LEAF_TO_WIDTH = 1.05           
SNAP_TOL = 0.06
DOOR_HEIGHT_ASSUMED_MM = 2134.0    
WINDOW_HEIGHT_ASSUMED_MM = 1219.0   
REACH_MM = 2000.0              
WIDTHS_IMPERIAL = (610.0, 686.0, 762.0, 813.0, 838.0, 914.0, 1067.0, 1219.0, 1524.0, 1829.0, 2134.0)
WIDTHS_METRIC = (600.0, 700.0, 750.0, 800.0, 900.0, 1000.0, 1200.0, 1500.0, 1800.0, 2100.0)

_KEY_OFF, _KEY_SPAN = 1 << 20, 1 << 21     

def _arrays(index) -> tuple:
  segs = np.asarray(index.segs, dtype=np.float32).reshape(-1, 5)
  kinds = np.asarray(index.kinds, dtype=np.uint8)
  n = min(len(segs), len(kinds))
  return segs[:n], kinds[:n]

def _hough(segs, kinds, ln, deadline: float | None) -> list:
  u = _u()
  ok = np.where((kinds < 2) & (ln >= DASH_MIN_PT * u) & (ln <= DASH_MAX_PT * u))[0]
  if len(ok) == 0:
    return []

  if len(ok) > 60000:
    ok = ok[:: int(math.ceil(len(ok) / 60000.0))]
  s = segs[ok]
  l = ln[ok]
  
  mx, my = (s[:, 0] + s[:, 2]) / 2.0, (s[:, 1] + s[:, 3]) / 2.0
  nx, ny = -(s[:, 3] - s[:, 1]) / l, (s[:, 2] - s[:, 0]) / l
  rc = np.arange(R_MIN_PT, R_MAX_PT + 1.0, 1.0)     
  rs = rc * u
  keys, who = [], []
  step = 6000
  for lo in range(0, len(ok), step):
    if deadline is not None and time.monotonic() > deadline:
      return []
    sl = slice(lo, lo + step)
    for sign in (1.0, -1.0):
      kx = np.round((mx[sl, None] + sign * nx[sl, None] * rs[None, :]) / u).astype(np.int64)
      ky = np.round((my[sl, None] + sign * ny[sl, None] * rs[None, :]) / u).astype(np.int64)
      kr = np.broadcast_to(rc.astype(np.int64)[None, :], kx.shape)
      keys.append((((kx + _KEY_OFF) * _KEY_SPAN + (ky + _KEY_OFF)) * 256 + kr).ravel())
      who.append(np.repeat(np.arange(lo, min(lo + step, len(ok))), len(rs)))
      
  keys, who = np.concatenate(keys), np.concatenate(who)
  order = np.argsort(keys, kind="stable")
  keys, who = keys[order], who[order]
  uk, start, cnt = np.unique(keys, return_index=True, return_counts=True)
  
  peaks = []
  for ci in np.where(cnt >= 4)[0]:
    sel = np.unique(who[start[ci]:start[ci] + cnt[ci]])
    k = int(uk[ci])
    peaks.append((((k // 256) // _KEY_SPAN - _KEY_OFF) * u, ((k // 256) % _KEY_SPAN - _KEY_OFF) * u, (k % 256) * u, sel))
  peaks.sort(key=lambda t: -len(t[3]))

  out, used = [], []
  for x, y, r, sel in peaks:
    d = np.hypot(mx[sel] - x, my[sel] - y)
    good = np.abs(d - r) <= ARC_TOL_PT * u
    if int(good.sum()) < 6:
      continue
    chosen = frozenset(sel[good].tolist())
    if any(len(chosen & u) > 0.6 * len(chosen) for u in used):
      continue
    used.append(chosen)
    
    th = np.sort(np.mod(np.degrees(np.arctan2(my[sel[good]] - y, mx[sel[good]] - x)), 360.0))
    gaps = np.diff(np.r_[th, th[0] + 360.0])
    span = 360.0 - float(gaps.max())
    if SPAN_MIN <= span <= SPAN_MAX:
      out.append({"x": float(x), "y": float(y), "r": float(r), "n": int(good.sum()), "span": span, "a0": float(th[(int(np.argmax(gaps)) + 1) % len(th)]), "by": "ARC"})
  return out

def _coverage(cx: float, cy: float, r: float, ang: float, segs, ln, idx) -> float:
  u = _u()
  tol = max(2.5 * u, 0.2 * r)
  ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
  spans = []
  
  for i in idx:
    x1, y1, x2, y2 = (float(v) for v in segs[i, :4])
    dx, dy = (x2 - x1) / ln[i], (y2 - y1) / ln[i]
    if abs(dx * uy - dy * ux) > 0.07 or abs((x1 - cx) * uy - (y1 - cy) * ux) > tol:
      continue
  
    t1, t2 = (x1 - cx) * ux + (y1 - cy) * uy, (x2 - cx) * ux + (y2 - cy) * uy
    lo, hi = max(min(t1, t2), -1.0 * u), min(max(t1, t2), 0.97 * r)      
    if hi - lo > 0.5 * u:
      spans.append((lo, hi))
  spans.sort()
  
  total, cur = 0.0, None
  for lo, hi in spans:
    if cur is None or lo > cur[1] + 1.5 * u:
      total += 0.0 if cur is None else cur[1] - cur[0]
      cur = [lo, hi]
    else:
      cur[1] = max(cur[1], hi)
  total += 0.0 if cur is None else cur[1] - cur[0]
  return total / r

def _leaf(a: dict, segs, kinds, ln) -> tuple:
  cx, cy, r = a["x"], a["y"], a["r"]
  near = np.minimum(np.hypot(segs[:, 0] - cx, segs[:, 1] - cy), np.hypot(segs[:, 2] - cx, segs[:, 3] - cy))
  idx = np.where((kinds == 0) & (ln >= 1.0 * _u()) & (near <= r + 4.0 * _u()))[0]
  best = (0.0, None)
  
  for end in (a["a0"], a["a0"] + a["span"]):
    for da in range(-9, 10):
      c = _coverage(cx, cy, r, end + da, segs, ln, idx)
      if c > best[0]:
        best = (c, (end + da) % 360.0)
  return best

def _heavy_ends(segs, kinds, heavy: float):
  hv = np.where((kinds == 0) & (segs[:, 4] >= HEAVY_SHARE * heavy))[0]
  if len(hv) == 0:
    return np.zeros((0, 2)), np.zeros((0, 2))
  ends = np.unique(np.round(np.r_[segs[hv, 0:2], segs[hv, 2:4]], 1), axis=0)
  return ends, hv

def _leaf_first(segs, kinds, ln, ends, bands: list, deadline: float | None) -> list:
  u = _u()
  thin = np.where((kinds < 2) & (ln <= DASH_MAX_PT * u) & (ln >= DASH_MIN_PT * u))[0]
  if len(thin) == 0 or (len(ends) == 0 and not bands):
    return []

  mids = np.c_[(segs[thin, 0] + segs[thin, 2]) / 2.0, (segs[thin, 1] + segs[thin, 3]) / 2.0]
  order = np.argsort(mids[:, 0])
  mids = mids[order]
  xs = mids[:, 0]
  leaves = np.where((kinds == 0) & (ln >= 12.0 * u) & (ln <= 110.0 * u))[0]
  out = []
  
  for n_i, i in enumerate(leaves):
    if deadline is not None and (n_i & 255) == 0 and time.monotonic() > deadline:
      break
    for (px, py, qx, qy) in ((segs[i, 0], segs[i, 1], segs[i, 2], segs[i, 3]), (segs[i, 2], segs[i, 3], segs[i, 0], segs[i, 1])):
      px, py, qx, qy, L = float(px), float(py), float(qx), float(qy), float(ln[i])
      if not _at_jamb(px, py, L, ends) and not _in_wall(px, py, bands):
        continue
      lo, hi = np.searchsorted(xs, px - L - 2.5 * u), np.searchsorted(xs, px + L + 2.5 * u)
      sub = mids[lo:hi]
      d = np.hypot(sub[:, 0] - px, sub[:, 1] - py)
      sel = sub[np.abs(d - L) <= 2.0 * u]
      if len(sel) < 4:
        continue
    
      th0 = math.degrees(math.atan2(qy - py, qx - px))
      a = (np.degrees(np.arctan2(sel[:, 1] - py, sel[:, 0] - px)) - th0 + 540.0) % 360.0 - 180.0
      for sgn in (1.0, -1.0):
        part = a[(sgn * a >= -6.0) & (sgn * a <= 100.0)]
        if len(part) < 4 or int(((sgn * a > 125.0) & (sgn * a <= 180.0)).sum()) >= 3:      
          continue
        bins = len(np.unique(np.round(part / 10.0)))
        span = float(part.max() - part.min())
        if bins >= BIN_MIN and span >= SPAN_BINS_MIN:
          out.append({"x": px, "y": py, "r": L, "n": int(len(part)), "span": span, "a0": (th0 + float(part.min())) % 360.0, "by": "LEAF", "leaf": 1.0, "ends": (th0 % 360.0, (th0 + sgn * 90.0) % 360.0), "bins": bins})
  return out

def _snap_point(x: float, y: float, segs, reach: float) -> tuple:
  d1 = np.hypot(segs[:, 0] - x, segs[:, 1] - y)
  d2 = np.hypot(segs[:, 2] - x, segs[:, 3] - y)
  i1, i2 = int(np.argmin(d1)), int(np.argmin(d2))
  if min(d1[i1], d2[i2]) > reach:
    return x, y
  return (float(segs[i1, 0]), float(segs[i1, 1])) if d1[i1] <= d2[i2] else (float(segs[i2, 2]), float(segs[i2, 3]))

def _merge(found: list) -> list:
  found = sorted(found, key=lambda a: (-(a.get("leaf") or 0.0), -a["n"]))
  keep = []
  
  for a in found:
    if any(math.hypot(a["x"] - b["x"], a["y"] - b["y"]) <= max(6.0 * _u(), 0.2 * a["r"]) and abs(a["r"] - b["r"]) <= max(4.0 * _u(), 0.2 * a["r"]) for b in keep):
      continue
    keep.append(a)
  return keep

def _at_jamb(x: float, y: float, r: float, ends, slack: float = 0.0) -> bool:
  return len(ends) > 0 and float(np.hypot(ends[:, 0] - x, ends[:, 1] - y).min()) <= JAMB_REL * r + (JAMB_ABS + slack) * _u()

def _wall_bands(walls: list, mm_per_pt: float) -> list:
  out = []
  for w in walls or []:
    f = w.facts or {}
    pts = (w.geometry or {}).get("points") or []
    if w.category != "WALL" or f.get("enclosure") == "TANK" or w.status == "INVALID" or len(pts) < 2:
      continue
    out.append((pts[0], pts[1], float(f.get("thickness_mm") or 230.0) / mm_per_pt / 2.0))
  return out

def _in_wall(x: float, y: float, bands: list) -> bool:
  for p0, p1, half in bands:
    vx, vy = p1[0] - p0[0], p1[1] - p0[1]
    l2 = vx * vx + vy * vy
    t = 0.0 if l2 <= 0.0 else max(0.0, min(1.0, ((x - p0[0]) * vx + (y - p0[1]) * vy) / l2))
    if math.hypot(x - (p0[0] + t * vx), y - (p0[1] + t * vy)) <= half + WALL_BAND_PT * _u():
      return True
  return False

def find_swings(index, mm_per_pt: float, *, scale_verified: bool = True, deadline: float | None = None, wall_pen: float | None = None, walls: list | None = None) -> tuple:
  segs, kinds = _arrays(index)
  stats = {"arcs": 0, "rejected_no_hinge": 0, "rejected_no_leaf": 0, "rejected_size": 0, "by_leaf_pass": 0}
  if len(segs) == 0 or mm_per_pt <= 0.0:
    return [], stats

  ln = np.hypot(segs[:, 2] - segs[:, 0], segs[:, 3] - segs[:, 1])
  pens = segs[kinds == 0, 4]
  heavy = float(wall_pen) if wall_pen else float(np.percentile(pens, 99)) if len(pens) else 0.0
  ends, _ = _heavy_ends(segs, kinds, heavy)
  bands = _wall_bands(walls, mm_per_pt)
  slack = PICTURE_JAMB_SLACK_PT if FROM_PICTURE.get() else 0.0
  lo_mm, hi_mm = SWING_MM if scale_verified else SWING_MM_UNVERIFIED
  arcs = _hough(segs, kinds, ln, deadline)
  stats["arcs"] = len(arcs)
  
  accepted = []
  for a in arcs:
    if not (lo_mm <= a["r"] * mm_per_pt <= hi_mm):
      stats["rejected_size"] += 1
      continue
  
    if not _at_jamb(a["x"], a["y"], a["r"], ends, slack) and not _in_wall(a["x"], a["y"], bands):
      stats["rejected_no_hinge"] += 1
      continue
    cov, ang = _leaf(a, segs, kinds, ln)
    if cov < LEAF_COVER_MIN:
      stats["rejected_no_leaf"] += 1
      continue
  
    a["leaf"] = cov
    a["ends"] = (a["a0"] % 360.0, (a["a0"] + a["span"]) % 360.0)
    accepted.append(a)
  second = [a for a in _leaf_first(segs, kinds, ln, ends, bands, deadline) if lo_mm <= a["r"] * mm_per_pt <= hi_mm]
  swings = _merge(accepted + second)
  stats["by_leaf_pass"] = sum(1 for a in swings if a["by"] == "LEAF")
  
  out = []
  for a in swings:
    x, y = _snap_point(a["x"], a["y"], segs, JAMB_REL * a["r"] + (JAMB_ABS + 2.0) * _u())
    out.append({"x": x, "y": y, "hx": a["x"], "hy": a["y"], "r_pt": a["r"], "leaf_mm": a["r"] * mm_per_pt, "span": a["span"], "by": a["by"],
      "ends": a["ends"]})
  return out, stats

def pair_doors(swings: list, mm_per_pt: float) -> list:
  used: set = set()
  doors = []
  
  order = sorted(range(len(swings)), key=lambda i: (swings[i]["y"], swings[i]["x"]))
  for ai, i in enumerate(order):
    if i in used:
      continue
    a = swings[i]
    mate = None
    for j in order[ai + 1:]:
      if j in used:
        continue
      b = swings[j]
      
      s = a["r_pt"] + b["r_pt"]
      d = math.hypot(a["hx"] - b["hx"], a["hy"] - b["hy"])
      if abs(a["r_pt"] - b["r_pt"]) > 0.15 * max(a["r_pt"], b["r_pt"]) or abs(d - s) > DOUBLE_TOL * s + 3.0 * _u():
        continue
      to_b = math.degrees(math.atan2(b["hy"] - a["hy"], b["hx"] - a["hx"])) % 360.0
      if _facing(a, b, to_b):
        mate = j
        break
    
    if mate is None:
      doors.append({"x": a["x"], "y": a["y"], "width_mm": a["leaf_mm"] * LEAF_TO_WIDTH, "leaves": 1, "by": a["by"]})
      used.add(i)
    else:
      b = swings[mate]
      used.update((i, mate))
      doors.append({"x": (a["x"] + b["x"]) / 2.0, "y": (a["y"] + b["y"]) / 2.0, "width_mm": (a["leaf_mm"] + b["leaf_mm"]) * LEAF_TO_WIDTH, "leaves": 2, "by": a["by"]})
  return doors

def _turn(x: float, y: float) -> float:
  return abs((x - y + 180.0) % 360.0 - 180.0)

def _facing(a: dict, b: dict, to_b: float) -> bool:
  for ca, oa in (a["ends"], a["ends"][::-1]):
    for cb, ob in (b["ends"], b["ends"][::-1]):
      if _turn(ca, to_b) <= END_TOL and _turn(cb, to_b + 180.0) <= END_TOL and _turn(oa, ob) <= 25.0:
        return True
  return False

def _glazing(segs, kinds, ln, a, b, t_pt: float) -> tuple:
  ax, ay, bx, by = float(a[0]), float(a[1]), float(b[0]), float(b[1])
  L = math.hypot(bx - ax, by - ay)
  u = _u()
  if L < 4.0 * u:
    return 0, 0.0
  dx, dy = (bx - ax) / L, (by - ay) / L
  nx, ny = -dy, dx
  idx = np.where((kinds == 0) & (ln >= WINDOW_COVER_MIN * L))[0]
  if len(idx) == 0:
    return 0, 0.0
  s = segs[idx]
  l = ln[idx]
  
  parallel = np.abs((s[:, 2] - s[:, 0]) / l * dy - (s[:, 3] - s[:, 1]) / l * dx) <= 0.045
  s = s[parallel]
  if len(s) == 0:
    return 0, 0.0
  off = (((s[:, 0] - ax) * nx + (s[:, 1] - ay) * ny) + ((s[:, 2] - ax) * nx + (s[:, 3] - ay) * ny)) / 2.0
  t1, t2 = (s[:, 0] - ax) * dx + (s[:, 1] - ay) * dy, (s[:, 2] - ax) * dx + (s[:, 3] - ay) * dy
  cover = (np.clip(np.maximum(t1, t2), 0.0, L) - np.clip(np.minimum(t1, t2), 0.0, L)) / L
  keep = (np.abs(off) <= t_pt / 2.0 + 1.5 * u) & (cover >= WINDOW_COVER_MIN)
  groups: list = []
  
  for o in np.sort(off[keep]):
    if not groups or o - groups[-1][-1] > 0.35 * u:
      groups.append([float(o)])
    else:
      groups[-1].append(float(o))
  if not groups:
    return 0, 0.0
  mids = [sum(g) / len(g) for g in groups]
  return len(groups), mids[len(mids) // 2]

def find_windows(index, walls: list, mm_per_pt: float, deadline: float | None = None) -> tuple:
  segs, kinds = _arrays(index)
  stats = {"gaps": 0, "glazed": 0, "open": 0}
  if len(segs) == 0 or mm_per_pt <= 0.0:
    return [], stats

  ln = np.hypot(segs[:, 2] - segs[:, 0], segs[:, 3] - segs[:, 1])
  out = []
  for w in walls:
    f = w.facts or {}
    if w.category != "WALL" or f.get("enclosure") == "TANK" or w.status == "INVALID":
      continue
  
    t_pt = float(f.get("thickness_mm") or 230.0) / mm_per_pt
    for (a, b), g in zip(f.get("gap_pts") or [], f.get("gaps_mm") or []):
      if deadline is not None and time.monotonic() > deadline:
        return out, stats
      g = float(g)
      if not (WINDOW_MIN_MM <= g <= WINDOW_MAX_MM):
        continue
      stats["gaps"] += 1
      n, off = _glazing(segs, kinds, ln, a, b, t_pt)
      if n < WINDOW_LINES_MIN:
        stats["open"] += 1
        continue
    
      stats["glazed"] += 1
      L = math.hypot(b[0] - a[0], b[1] - a[1])
      dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
      mx, my = (a[0] + b[0]) / 2.0 - dy * off, (a[1] + b[1]) / 2.0 + dx * off
      px, py = _snap_point(mx, my, segs, 1.0 * _u())
      out.append({"x": px, "y": py, "width_mm": g, "lines": n, "wall_key": w.key})
  return out, stats

def snap_width(mm: float, imperial: bool) -> float:
  best = min(WIDTHS_IMPERIAL if imperial else WIDTHS_METRIC, key=lambda s: abs(s - mm))
  return best if abs(best - mm) <= SNAP_TOL * best else float(round(mm / 5.0) * 5)

def read(index, walls: list, mm_per_pt: float, *, scale_verified: bool = True, deadline: float | None = None, wall_pen: float | None = None, imperial: bool = True) -> dict:
  token = UNIT_PT.set(unit_for(mm_per_pt))
  try:
    return _read(index, walls, mm_per_pt, scale_verified=scale_verified, deadline=deadline, wall_pen=wall_pen, imperial=imperial)
  finally:
    UNIT_PT.reset(token)

def _read(index, walls: list, mm_per_pt: float, *, scale_verified: bool = True, deadline: float | None = None, wall_pen: float | None = None, imperial: bool = True) -> dict:
  started = time.monotonic()
  swings, sstats = find_swings(index, mm_per_pt, scale_verified=scale_verified, deadline=deadline, wall_pen=wall_pen, walls=walls)
  doors = pair_doors(swings, mm_per_pt)
  windows, wstats = find_windows(index, walls, mm_per_pt, deadline)
  words = list(getattr(index, "words", None) or [])
  printed = OL.read(words, imperial)
  
  paired = {"DOOR": OL.pair(doors, printed["labels"], "DOOR", mm_per_pt, scale_verified), "WINDOW": OL.pair(windows, printed["labels"], "WINDOW", mm_per_pt, scale_verified)}
  height_notes = OL.height_notes(build_lines(words)) if words else {}
  made = LO.make(printed["labels"], walls, {"DOOR": doors, "WINDOW": windows}, mm_per_pt)
  printed["unread"] += made["stats"]["no_wall"]
  stats = {"swings": len(swings),"doors": len(doors), "double_doors": sum(1 for d in doors if d["leaves"] == 2), "windows": len(windows), "swing_search": sstats,
    "window_search": wstats, "timed_out": bool(deadline is not None and time.monotonic() > deadline), "seconds": round(time.monotonic() - started, 3),
    "labels": {"read": len(printed["labels"]), "unread": printed["unread"], "paired": paired,
      "unpaired": sum(1 for l in printed["labels"] if not l.get("paired") and not l.get("opened")), "opened": made["stats"]},
    "height_notes": height_notes}
  return {"doors": doors, "windows": windows, "label_doors": made["DOOR"], "label_windows": made["WINDOW"], "stats": stats, "labels": printed["labels"], "height_notes": height_notes}

KINDS = ("DOOR", "WINDOW")
HEIGHT_ASSUMED_MM = {"DOOR": DOOR_HEIGHT_ASSUMED_MM, "WINDOW": WINDOW_HEIGHT_ASSUMED_MM}
WIDTH_DIFFERS_TOL = 0.15
LABEL_HEIGHT_DIFFERS_TOL = 0.05

def _median(values: list) -> float:
  v = sorted(values)
  n = len(v)
  return float(v[n // 2]) if n % 2 else (float(v[n // 2 - 1]) + float(v[n // 2])) / 2.0

def _marks(cands: list, category: str) -> list:
  rows = []
  for c in cands:
    f = c.facts or {}
    if c.category != category or c.status == "INVALID" or f.get("found_by") in ("SYMBOL_SCAN", "LABEL") or f.get("opening_kind") == "VENTILATOR":
      continue
    rows.extend((c, k) for k in range(len((c.geometry or {}).get("points") or [])))
  return rows

def _match(rows: list, symbols: list, reach_pt: float) -> dict:
  pairs = []
  
  for ri, (c, k) in enumerate(rows):
    p = c.geometry["points"][k]
    for si, s in enumerate(symbols):
      d = math.hypot(float(p[0]) - s["x"], float(p[1]) - s["y"])
      if d <= reach_pt:
        pairs.append((d, ri, si))
        
  pairs.sort()
  taken_r, taken_s, out = set(), set(), {}
  for d, ri, si in pairs:
    if ri in taken_r or si in taken_s:
      continue
    taken_r.add(ri)
    taken_s.add(si)
    out[(id(rows[ri][0]), rows[ri][1])] = si
  return out

def _class_width(width_mm: float, scale_verified: bool, imperial: bool) -> float:
  return snap_width(width_mm, imperial) if scale_verified else float(round(width_mm / 50.0) * 50)

def _height_of(kind: str, height_notes: dict | None, set_heights: dict | None = None) -> tuple:
  noted = (height_notes or {}).get(kind)
  if noted:
    return float(noted), "NOTE"
  shared = (set_heights or {}).get(kind)
  if shared and shared.get("height_mm"):
    return float(shared["height_mm"]), "SET_LABELS"
  return HEIGHT_ASSUMED_MM[kind], "ASSUMED"

def _height_note(basis: str, height: float, label_n: int = 0) -> dict | None:
  if basis == "LABEL":
    return C.note("OPENING_SIZE_FROM_PLAN_LABEL")
  if basis == "NOTE":
    return C.note("OPENING_HEIGHT_FROM_NOTE", height_mm=height)
  if basis == "SET_LABELS":
    return C.note("OPENING_HEIGHT_FROM_SET", height_mm=height)
  return C.note("OPENING_HEIGHT_ASSUMED", height_mm=height)

def _group_candidate(kind: str, width: float, items: list, ctx: dict, cls, finish, scale_verified: bool, height: float | None = None, basis: str = "ASSUMED", sill: float | None = None, label_only: bool = False):
  work_item, mode, ckind = C.SUGGESTIONS[kind]
  height = HEIGHT_ASSUMED_MM[kind] if height is None else height
  n = len(items)
  
  facts = {"opening_kind": kind, "found_by": "LABEL" if label_only else "SYMBOL_SCAN", "symbols": 0 if label_only else n, "double_leaf": sum(1 for i in items if i.get("leaves") == 2), "width_drawn_mm": width,
    "widths_measured_mm": sorted(round(i["width_mm"]) for i in items), "size_drawn_mm": [width, height], "height_assumed": basis == "ASSUMED", "area_each_m2": round(width * height / 1e6, 3),
    "width_snapped": bool(scale_verified)}
  if basis != "ASSUMED":
    facts["height_source"] = basis
  if basis == "LABEL":
    facts["size_from_label"] = True
    facts["label_texts"] = sorted({i["label"]["text"] for i in items if i.get("label")})[:6]
  if sill is not None:
    facts["sill_mm"] = sill
  in_gap = sum(1 for i in items if i.get("gap")) if label_only else n
  if label_only:
    facts["labels"] = n
    facts["in_gap"] = in_gap
    facts["label_texts"] = sorted({i["label"]["text"] for i in items if i.get("label")})[:6]
    if any(i.get("ventilator") for i in items):
      facts["ventilator"] = True
    if in_gap < n:
      facts["gap_check"] = "NO_GAP"
    
  notes = [C.note("OPENING_FROM_LABEL" if label_only else "OPENING_FROM_SYMBOLS"), _height_note(basis, height)]
  if label_only and in_gap < n:
    notes.append(C.note("OPENING_LABEL_NO_GAP"))
  noun = "Door" if kind == "DOOR" else "Window"
  size_text = f"{width:g} mm" if basis == "ASSUMED" else f"{width:g}×{height:g} mm"
  how = "drawn, no mark" if basis == "ASSUMED" else ("size from the plan labels, no mark" if basis == "LABEL" else "drawn, height from a note, no mark" if basis == "NOTE" else "drawn, height from the set's labels, no mark")
  if label_only:
    how = "from the plan label, no symbol" + {"ASSUMED": "", "LABEL": "", "NOTE": " · height from a note", "SET_LABELS": " · height from the set's labels"}[basis] + ("" if in_gap == n else " · no gap in the wall")
  pre = "LABEL" if label_only else "DRAWN"
  tag = f"{pre}-{kind}-{width:g}" if basis == "ASSUMED" else f"{pre}-{kind}-{width:g}x{height:g}" + (f"s{sill:g}" if sill is not None else "")
  key = (("OPNLBL" if label_only else "OPNSYM"), kind, width) if basis == "ASSUMED" else (("OPNLBL" if label_only else "OPNSYM"), kind, width, height, sill) + ((in_gap == n,) if label_only else ())
  if label_only and basis == "ASSUMED":
    key += (in_gap == n,)
  cand = cls(key=FD._key_of(key), category=kind, kind=ckind, quantity_mode=mode, label=f"{noun} {size_text} ×{n} · {how}", tag=tag,
    geometry={"points": [[round(i["x"], 3), round(i["y"], 3)] for i in items]}, params={}, missing=[], work_item=work_item, status="VALID", confidence=0.0, facts=facts, notes=notes,
    source="VECTOR_SNAP", count=n)
  return finish(cand, ctx, 0.6)

def _sizes_from_labels(found: list) -> dict | None:
  labs = [s["label"] for s in found if s.get("label")]
  if not labs:
    return None
  out = {"w_mm": _median([l["w_mm"] for l in labs]), "n": len(labs), "texts": sorted({l["text"] for l in labs})[:4]}
  for key in ("h_mm", "sill_mm"):
    vals = [l[key] for l in labs if l.get(key) is not None]
    out[key] = _median(vals) if vals else None
  return out

def _schedule_pairs(cands: list, symbols: dict, reach: float) -> list:
  out = []
  for kind, key in (("DOOR", "doors"), ("WINDOW", "windows")):
    syms = symbols.get(key) or []
    rows = _marks(cands, kind)
    if not syms or not rows:
      continue
  
    per: dict = {}
    for (cid, k), si in _match(rows, syms, reach).items():
      per.setdefault(cid, []).append(syms[si])
    for c in {id(r[0]): r[0] for r in rows}.values():
      found, sched = per.get(id(c), []), (c.facts or {}).get("size_schedule_mm")
      if not found or not sched or not sched[0]:
        continue
      width = _median([s["width_mm"] for s in found])
      if width > 0:
        out.append({"kind": kind, "tag": getattr(c, "tag", None), "factor": float(sched[0]) / width})
  return out

def reconcile(cands: list, symbols: dict, mm_per_pt: float, *, scale_verified: bool, imperial: bool, ctx: dict, cls, finish, set_heights: dict | None = None) -> dict:
  new, notes = [], []
  hnotes = symbols.get("height_notes") or {}
  sets = set_heights or {}
  
  stats = {"marks": {}, "symbols": {}, "matched": {}, "unmatched_symbols": {}, "marks_without_symbol": {}, "drawn_items": 0, "label_items": {}, "set_heights": sets}
  reach = REACH_MM / mm_per_pt
  verdict = SS.verdict(_schedule_pairs(cands, symbols, reach))
  stats["schedule_scale"] = verdict
  settled = verdict["status"] == "SETTLED" and not scale_verified
  scale_verified = scale_verified or settled
  
  for kind, key in (("DOOR", "doors"), ("WINDOW", "windows")):
    syms = symbols.get(key) or []
    lonly = symbols.get("label_" + key) or []
    rows = _marks(cands, kind)
    stats["symbols"][kind], stats["marks"][kind] = len(syms), len(rows)
    if rows and lonly:
      for s in lonly:
        s["label"]["opened"] = False
      stats["label_items"][kind] = {"made": len(lonly), "kept": 0, "reason": "MARKS_COUNT_THE_OPENINGS"}
      
      lonly = []
    if not syms and not rows and not lonly:
      continue
    if not rows:
      groups: dict = {}
      for s in syms:
        lab = s.get("label")
        if lab and lab.get("h_mm"):
          key = (float(lab["w_mm"]), float(lab["h_mm"]), "LABEL", lab.get("sill_mm"))
        else:
          height, basis = _height_of(kind, hnotes, sets)
          key = (float(lab["w_mm"]) if lab else _class_width(s["width_mm"], scale_verified, imperial), height, basis, lab.get("sill_mm") if lab else None)
        groups.setdefault(key, []).append(s)
      for key in sorted(groups, key=lambda k: (k[0], k[1], k[3] or 0.0, k[2])):
        new.append(_group_candidate(kind, key[0], groups[key], ctx, cls, finish, scale_verified, height=key[1], basis=key[2], sill=key[3]))
      stats["drawn_items"] += len(groups)
      stats["matched"][kind] = 0
      
      lgroups: dict = {}
      for s in lonly:
        lab = s["label"]
        if lab.get("h_mm"):
          lkey = (float(lab["w_mm"]), float(lab["h_mm"]), "LABEL", lab.get("sill_mm"), bool(s.get("gap")))
        else:
          height, basis = _height_of(kind, None if s.get("ventilator") else hnotes, None if s.get("ventilator") else sets)
          lkey = (float(lab["w_mm"]), height, basis, lab.get("sill_mm"), bool(s.get("gap")))
        lgroups.setdefault(lkey, []).append(s)
      for lkey in sorted(lgroups, key=lambda k: (k[0], k[1], k[3] or 0.0, k[2], k[4])):
        new.append(_group_candidate(kind, lkey[0], lgroups[lkey], ctx, cls, finish, scale_verified, height=lkey[1], basis=lkey[2], sill=lkey[3], label_only=True))
      if lonly:
        stats["label_items"][kind] = {"made": len(lonly), "kept": len(lonly), "groups": len(lgroups)}
        stats["drawn_items"] += len(lgroups)
      continue
  
    match = _match(rows, syms, reach)
    stats["matched"][kind] = len(match)
    
    per: dict = {}
    for (cid, k), si in match.items():
      per.setdefault(cid, []).append(syms[si])
    for c in {id(r[0]): r[0] for r in rows}.values():
      f = c.facts
      found = per.get(id(c), [])
      marks = len((c.geometry or {}).get("points") or [])
      f["symbols"] = {"marks": marks, "found": len(found)}
      if not found:
        continue
    
      width = _median([s["width_mm"] for s in found])
      f["width_drawn_mm"] = float(round(width / 5.0) * 5)
      sched = f.get("size_schedule_mm")
      printed = _sizes_from_labels(found)
      if sched and sched[0]:
        if scale_verified and abs(width - float(sched[0])) > WIDTH_DIFFERS_TOL * float(sched[0]):
          c.notes.append(C.note("OPENING_DRAWN_WIDTH_DIFFERS", drawn_mm=f["width_drawn_mm"], schedule_mm=round(float(sched[0]))))
        if printed and printed.get("h_mm") and len(sched) > 1 and sched[1] and abs(printed["h_mm"] - float(sched[1])) > LABEL_HEIGHT_DIFFERS_TOL * float(sched[1]):
          c.notes.append(C.note("OPENING_LABEL_DIFFERS_FROM_SCHEDULE", label_mm=[round(printed["w_mm"]), round(printed["h_mm"])], schedule_mm=[round(float(sched[0])), round(float(sched[1]))]))
      elif not f.get("size_drawn_mm"):
        if printed and printed.get("h_mm"):
          w, h = float(printed["w_mm"]), float(printed["h_mm"])
          f["size_drawn_mm"] = [w, h]
          f["height_assumed"] = False
          f["height_source"] = "LABEL"
          f["size_from_label"] = True
          f["label_texts"] = printed["texts"]
          
          if printed.get("sill_mm") is not None:
            f["sill_mm"] = printed["sill_mm"]
          f["area_each_m2"] = round(w * h / 1e6, 3)
          c.notes.append(C.note("OPENING_SIZE_FROM_PLAN_LABEL"))
        else:
          w = float(printed["w_mm"]) if printed else _class_width(width, scale_verified, imperial)
          h, basis = _height_of(kind, hnotes, sets)
          f["size_drawn_mm"] = [w, h]
          f["height_assumed"] = basis == "ASSUMED"
          if basis != "ASSUMED":
            f["height_source"] = basis
          f["area_each_m2"] = round(w * h / 1e6, 3)
          c.notes.append(_height_note(basis, h))
      c.status = _worst(c)
    unmatched = len(syms) - len(match)
    lacking = len(rows) - len(match)
    stats["unmatched_symbols"][kind], stats["marks_without_symbol"][kind] = unmatched, lacking
    
    if unmatched:
      stats.setdefault("unmatched_at", {})[kind] = [[round(sy["x"], 1), round(sy["y"], 1), round(sy["width_mm"])] for si, sy in enumerate(syms) if si not in set(match.values())]
    if unmatched or lacking:
      notes.append(C.note("OPENING_SYMBOLS_VS_MARKS", kind=kind, marks=len(rows), symbols=len(syms), matched=len(match)))
  unpaired = [l for l in (symbols.get("labels") or []) if not l.get("paired") and not l.get("opened")]
  if unpaired:
    notes.append(C.note("OPENING_LABELS_UNPAIRED", count=len(unpaired), labels=sorted({l["text"] for l in unpaired})[:8]))
  if verdict["status"] == "DISAGREES":
    implied = mm_per_pt * verdict["factor"]
    stats["implied_mm_per_pt"], stats["scale_pairs"] = round(implied, 3), verdict["agree"]
    notes.append(C.note("OPENING_SCALE_FROM_SCHEDULE_DISAGREES", used_mm_per_pt=round(mm_per_pt, 3), implied_mm_per_pt=round(implied, 3), pairs=verdict["agree"], of=verdict["pairs"]))
  elif settled:
    notes.append(C.note("SCALE_SETTLED_BY_SCHEDULE", pairs=verdict["agree"], of=verdict["pairs"], factor=verdict["factor"]))
  _mark_doors_by_width(new, cands)
  return {"new": new, "notes": notes, "stats": stats, "settled": settled}

def _mark_doors_by_width(new: list, existing: list) -> None:
  marked: dict = {}
  for c in existing:
    f = c.facts or {}
    size = f.get("size_schedule_mm") or f.get("size_drawn_mm")
    if c.category == "DOOR" and c.tag and not str(c.tag).upper().startswith(("DRAWN-", "LABEL-")) and size and size[0]:
      marked.setdefault(str(c.tag).upper(), float(size[0]))
  for c in new:
    f = c.facts or {}
    if c.category != "DOOR" or not str(c.tag or "").upper().startswith(("DRAWN-", "LABEL-")) or not (f.get("size_drawn_mm") or [None])[0]:
      continue
    width = float(f["size_drawn_mm"][0])
    hits = sorted(m for m, w in marked.items() if abs(w - width) <= C.MARK_BY_SIZE_TOL_MM)
    f["tag_drawn"] = c.tag
    c.tag = hits[0] if len(hits) == 1 else f"D-{round(width):d}"
    c.notes.append(C.note("DOOR_MARK_FROM_WIDTH", mark=c.tag, how="DOOR" if len(hits) == 1 else "NAMED"))

def _worst(c) -> str:
  return NS.status_of(c.notes)
