from __future__ import annotations
import numpy as np
from app.modules.drawings_boq.takeoff.extract import beam_strips as BS
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.extract.walls import Run

LINK = 7.5
GRID = 1.0
MIN_STROKES = 6
LEG_MIN_MM = 300.0
MERGE_WIDTH_TOL = 0.25
ZERO_WIDTH = 0.01

def _lines(index) -> tuple:
  raw = np.frombuffer(index.segs, dtype=np.float32).reshape(-1, 5).astype(np.float64)
  kinds = np.frombuffer(index.kinds, dtype=np.uint8)
  plain = kinds == 0
  every = [(float(r[0]), float(r[1]), float(r[2]), float(r[3]), 0) for r in raw[plain]]
  fine = (plain | (kinds == 2)) & (raw[:, 4] <= ZERO_WIDTH)
  fills = [(float(r[0]), float(r[1]), float(r[2]), float(r[3]), 0) for r in raw[fine]]
  return every, fills

def legs(index, mm_per_pt: float, unit: float) -> tuple:
  every, fills = _lines(index)
  strokes = BS.hatch_strokes(fills, mm_per_pt)
  share = len(strokes) / max(1, len(every))
  if share < C.HATCH_WALL_SHARE_MIN:
    return [], share, len(strokes)
  out: list = []
  
  for comp in BS.components(strokes, unit, LINK):
    if len(comp) >= MIN_STROKES:
      out.extend(BS.legs_of(comp, mm_per_pt, unit, GRID, C.HATCH_WALL_WIDTH_MM, LEG_MIN_MM))
  edges = BS._axis_lines(every)
  for leg in out:
    BS._refine_edges(leg, edges)
  return [leg for leg in out if leg.get("edges") and C.WALL_T_MIN_MM <= leg["width_pt"] * mm_per_pt <= C.WALL_T_MAX_MM], share, len(strokes)

def _line(leg: dict) -> float:
  return BS._line(leg)

def merged(found: list) -> list:
  out: list = []
  for axis in ("H", "V"):
    rest = sorted((dict(l) for l in found if l["axis"] == axis), key=lambda l: (_line(l), BS._span(l)[0]))
    groups: list = []
    for l in rest:
      for g in reversed(groups[-6:]):
        head = g[0]
        if abs(_line(l) - _line(head)) <= 0.5 * min(l["width_pt"], head["width_pt"]) and abs(l["width_pt"] / head["width_pt"] - 1.0) <= MERGE_WIDTH_TOL:
          g.append(l)
          break
      else:
        groups.append([l])
    for g in groups:
      g.sort(key=lambda l: BS._span(l)[0])
      cur = None
      
      for l in g:
        lo, hi = BS._span(l)
        if cur is not None and lo <= cur["hi"] + 0.5 * cur["w"]:
          cur["hi"] = max(cur["hi"], hi)
          cur["wsum"] += l["width_pt"] * (hi - lo)
          cur["lsum"] += _line(l) * (hi - lo)
          cur["n"] += hi - lo
          continue
        if cur is not None:
          out.append(cur)
        cur = {"axis": axis, "lo": lo, "hi": hi, "w": l["width_pt"], "wsum": l["width_pt"] * (hi - lo), "lsum": _line(l) * (hi - lo), "n": hi - lo}
      if cur is not None:
        out.append(cur)
  for m in out:
    m["width_pt"], m["line"] = m["wsum"] / m["n"], m["lsum"] / m["n"]
  return out

def _in_frame(fr, axis: str, line: float, lo: float, hi: float) -> tuple:
  a, b = ((lo, line), (hi, line)) if axis == "H" else ((line, lo), (line, hi))
  s0, s1 = fr.s_of(*a), fr.s_of(*b)
  return fr.d_of(*a), min(s0, s1), max(s0, s1)

def _frame_of(frames: list, axis: str) -> int | None:
  for i, fr in enumerate(frames):
    if (axis == "H" and abs(fr.uy) <= C.HATCH_WALL_FRAME_TAN and fr.ux > 0) or (axis == "V" and abs(fr.ux) <= C.HATCH_WALL_FRAME_TAN and fr.uy > 0):
      return i
  return None

def _open(lo: float, hi: float, taken: list) -> list:
  pieces = [(lo, hi)]
  for a, b in sorted(taken):
    nxt: list = []
    for p, q in pieces:
      if b <= p or a >= q:
        nxt.append((p, q))
        continue
      if a > p:
        nxt.append((p, a))
      if b < q:
        nxt.append((b, q))
    pieces = nxt
  return pieces

def add_runs(index, frames: list, runs: list, mm_per_pt: float, unit: float = 1.0) -> tuple:
  found, share, strokes = legs(index, mm_per_pt, unit)
  stats = {"hatch_strokes": strokes, "hatch_share": round(share, 3), "hatch_legs": len(found), "hatch_runs": 0, "hatch_m": 0.0}
  if not found or not frames:
    return [], stats
  new: list = []
  
  floor = C.HATCH_WALL_MIN_MM / mm_per_pt
  for m in merged(found):
    i = _frame_of(frames, m["axis"])
    if i is None:
      continue
    t = m["width_pt"]
    
    dc, s_lo, s_hi = _in_frame(frames[i], m["axis"], m["line"], m["lo"], m["hi"])
    taken = [(r.s0 - r.ext0, r.s1 + r.ext1) for r in runs if r.peak == i and abs(r.dc - dc) <= 0.5 * max(r.t_pt, t)]
    taken += [(n.s0, n.s1) for n in new if n.peak == i and abs(n.dc - dc) <= 0.5 * max(n.t_pt, t)]
    for lo, hi in _open(s_lo, s_hi, taken):
      if hi - lo >= floor:
        new.append(Run(i, dc, t, lo, hi, hi - lo, 1, hatch=True))
        
  stats["hatch_runs"] = len(new)
  stats["hatch_m"] = round(sum(r.s1 - r.s0 for r in new) * mm_per_pt / 1000.0, 2)
  return new, stats
