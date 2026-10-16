from __future__ import annotations
import math
import re
import numpy as np
from app.modules.drawings_boq.takeoff.extract import config as C

ALIGN_TOL_PT = 0.3
_DIRECTION = re.compile(r"\b(UP|DN|DOWN)\b", re.I)
_NOT_A_DIRECTION = re.compile(r"\bUP\s+TO\b", re.I)

def _chains(lines, axis: int, tread_pt: float, width_pt: float) -> list:
  """Stacks of equal-length lines laid one tread apart across the plan: the treads of a flight. axis 0 is treads that run left to right (steps climb
  up the page), axis 1 treads that run up the page. A tread line missing from the drawing is bridged when two treads are the gap."""
  if len(lines) == 0:
    return []

  if axis == 0:
    flat = np.abs(lines[:, 1] - lines[:, 3]) <= ALIGN_TOL_PT
    pos = (lines[:, 1] + lines[:, 3]) / 2.0
    lo, hi = np.minimum(lines[:, 0], lines[:, 2]), np.maximum(lines[:, 0], lines[:, 2])
  else:
    flat = np.abs(lines[:, 0] - lines[:, 2]) <= ALIGN_TOL_PT
    pos = (lines[:, 0] + lines[:, 2]) / 2.0
    lo, hi = np.minimum(lines[:, 1], lines[:, 3]), np.maximum(lines[:, 1], lines[:, 3])
  size = hi - lo
  keep = flat & (size >= C.STAIR_LINE_MIN * width_pt) & (size <= C.STAIR_LINE_MAX * width_pt)
  pos, lo, hi = pos[keep], lo[keep], hi[keep]
  if len(pos) < C.STAIR_MIN_TREADS:
    return []

  order = np.argsort(lo)
  pos, lo, hi = pos[order], lo[order], hi[order]
  taken = np.zeros(len(pos), dtype=bool)
  out = []
  for i in range(len(pos)):
    if taken[i]:
      continue
    same = np.where((np.abs(lo - lo[i]) <= C.STAIR_ALIGN_PT) & (np.abs(hi - hi[i]) <= C.STAIR_ALIGN_PT))[0]
    taken[same] = True
    ps = np.unique(np.round(pos[same], 1))
    run = [ps[0]]
    
    for p in list(ps[1:]) + [None]:
      ratio = None if p is None else (p - run[-1]) / tread_pt
      step = None if ratio is None else round(ratio)
      if p is not None and step in (1, 2) and abs(ratio - step) <= C.STAIR_TREAD_TOL * step:
        run.append(p)
        continue
      if len(run) >= C.STAIR_MIN_TREADS:
        a0, a1 = float(np.mean(lo[same])), float(np.mean(hi[same]))
        box = (a0, run[0], a1, run[-1]) if axis == 0 else (run[0], a0, run[-1], a1)
        out.append({"axis": axis, "treads": len(run), "box": box, "span_pt": float(a1 - a0)})
      if p is not None:
        run = [p]
  return out

def _same_way(a, b) -> bool:
  return a is None or b is None or a == b

def _merge(items: list, reach: float) -> list:
  groups = [dict(g, treads=g["treads"]) for g in items]
  changed = True
  while changed:
    changed = False
    for i in range(len(groups)):
      for j in range(i + 1, len(groups)):
        a, b = groups[i]["box"], groups[j]["box"]
        if _same_way(groups[i].get("direction"), groups[j].get("direction")) and a[0] - reach <= b[2] and b[0] - reach <= a[2] and a[1] - reach <= b[3] and b[1] - reach <= a[3]:
          groups[i] = {"axis": groups[i]["axis"], "treads": max(groups[i]["treads"], groups[j]["treads"]), "span_pt": max(groups[i]["span_pt"], groups[j]["span_pt"]),
            "direction": groups[i].get("direction") or groups[j].get("direction"),
            "box": (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))}
          del groups[j]
          changed = True
          break
      if changed:
        break
  return groups

def direction_labels(lines: list) -> list:
  """The UP / DN words of a plan with the point each stands at (page units)."""
  out = []
  for ln in lines:
    text = (getattr(ln, "text", "") or "").strip()
    if not text or len(text) > 16 or _NOT_A_DIRECTION.search(text):
      continue
    m = _DIRECTION.search(text)
    if not m:
      continue
    ws = [w for _, _, w in ln.spans]
    if not ws:
      continue
    word = m.group(1).upper()
    out.append({"direction": "UP" if word == "UP" else "DOWN", "x": sum(w.cx for w in ws) / len(ws), "y": sum(w.cy for w in ws) / len(ws)})
  return out

def length_labels(lines: list, parse) -> list:
  """The lengths a plan prints as text (3'-0", 36"), each with the point it stands at (page units). `parse` turns the text into millimetres or None."""
  out = []
  for ln in lines:
    text = (getattr(ln, "text", "") or "").strip()
    if not text or len(text) > 12:
      continue
    mm = parse(text)
    if mm is None:
      continue
    ws = [w for _, _, w in ln.spans]
    if not ws:
      continue
    out.append({"mm": float(mm), "text": text, "x": sum(w.cx for w in ws) / len(ws), "y": sum(w.cy for w in ws) / len(ws)})
  return out

def _gap(box, x: float, y: float) -> float:
  x0, y0, x1, y1 = box
  return math.hypot(max(x0 - x, 0.0, x - x1), max(y0 - y, 0.0, y - y1))

def _nearest_way(box, labels: list, reach_pt: float, skip: set | None = None) -> str | None:
  best, best_d = None, reach_pt
  for i, lab in enumerate(labels or []):
    if skip and i in skip:
      continue
    d = _gap(box, lab["x"], lab["y"])
    if d <= best_d:
      best, best_d = lab["direction"], d
  return best

def _assign_ways(chains: list, labels: list, reach_pt: float) -> set:
  pairs = []
  for ci, ch in enumerate(chains):
    for li, lab in enumerate(labels or []):
      d = _gap(ch["box"], lab["x"], lab["y"])
      if d <= reach_pt:
        pairs.append((d, ci, li))
  pairs.sort()
  done_c, used = set(), set()
  for d, ci, li in pairs:
    if ci in done_c or li in used:
      continue
    chains[ci]["direction"] = labels[li]["direction"]
    done_c.add(ci)
    used.add(li)
  return used

def printed_width(box, drawn_mm: float, dims: list, mm_per_pt: float) -> dict | None:
  reach = C.STAIR_DIM_REACH_MM / mm_per_pt
  best = None
  for d in dims or []:
    if abs(d["mm"] - drawn_mm) > C.STAIR_DIM_MATCH * drawn_mm:
      continue
  
    gap = _gap(box, d["x"], d["y"])
    if gap > reach:
      continue
    key = (abs(d["mm"] - drawn_mm), gap)
    if best is None or key < best[0]:
      best = (key, d)
  return None if best is None else {"mm": round(best[1]["mm"], 1), "text": best[1]["text"]}

def find_stairs(lines, spec: dict, mm_per_pt: float, labels: list | None = None, dims: list | None = None) -> list:
  tread_mm, width_mm = spec.get("tread_mm"), spec.get("width_mm")
  if not tread_mm or not width_mm or mm_per_pt <= 0:
    return []

  tread_pt, width_pt = float(tread_mm) / mm_per_pt, float(width_mm) / mm_per_pt
  reach = C.STAIR_LABEL_REACH_MM / mm_per_pt
  found = _chains(lines, 0, tread_pt, width_pt) + _chains(lines, 1, tread_pt, width_pt)
  for ch in found:
    ch["direction"] = None
  used = _assign_ways(found, labels, reach)
  groups = _merge(found, tread_pt)

  out = []
  for g in sorted(groups, key=lambda g: (-g["box"][3], g["box"][0])):
    x0, y0, x1, y1 = g["box"]
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    way = g.get("direction") or _nearest_way(g["box"], labels, reach, used)
    drawn = g["span_pt"] * mm_per_pt
    own = printed_width(g["box"], drawn, dims, mm_per_pt)
    area_m2 = (x1 - x0) * (y1 - y0) * mm_per_pt * mm_per_pt / 1e6
    out.append({"x": cx, "y": cy, "box": [round(v, 3) for v in g["box"]], "treads_drawn": g["treads"], "axis": g["axis"], "flight_area_m2": round(area_m2, 3),
      "width_drawn_mm": round(drawn, 1), "direction": way, "width_printed_mm": own["mm"] if own else None, "width_printed_text": own["text"] if own else None})
  return out
