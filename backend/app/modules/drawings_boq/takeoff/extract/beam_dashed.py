from __future__ import annotations

DASH_MIN_MM = 120.0
DASH_MAX_MM = 700.0
PERP_TOL_MM = 5.0
CHAIN_GAP_SHARE = 1.0
CHAIN_MIN_DASHES = 5
DASH_SPREAD = 0.25
WIDTH_MIN_MM = 217.0
WIDTH_MAX_MM = 610.0
OVERLAP_MIN_MM = 900.0

def _dashes(segments: list, mm_per_pt: float) -> dict:
  perp = PERP_TOL_MM / mm_per_pt
  out: dict = {"H": [], "V": []}
  for s in segments:
    x1, y1, x2, y2 = s[0], s[1], s[2], s[3]
    dx, dy = abs(x2 - x1), abs(y2 - y1)
    length = max(dx, dy) * mm_per_pt
    if length < DASH_MIN_MM or length > DASH_MAX_MM:
      continue
  
    if dy <= perp and dx > dy:
      out["H"].append(((y1 + y2) / 2.0, min(x1, x2), max(x1, x2)))
    elif dx <= perp and dy > dx:
      out["V"].append(((x1 + x2) / 2.0, min(y1, y2), max(y1, y2)))
  return out

def chains(segments: list, mm_per_pt: float) -> list:
  perp = PERP_TOL_MM / mm_per_pt
  out = []
  for axis, items in _dashes(segments, mm_per_pt).items():
    items.sort()
    rows: list = []
    for it in items:
      if rows and it[0] - rows[-1][-1][0] <= perp:
        rows[-1].append(it)
      else:
        rows.append([it])
        
    for row in rows:
      row.sort(key=lambda d: (d[1], d[2]))
      run: list = [row[0]]
      for d in row[1:]:
        gap = d[1] - run[-1][2]
        size = max(run[-1][2] - run[-1][1], 1e-9)
        if gap <= CHAIN_GAP_SHARE * size:
          run.append(d)
        else:
          out.extend(_chain(axis, run))
          run = [d]
      out.extend(_chain(axis, run))
  return out

def _chain(axis: str, run: list) -> list:
  if len(run) < CHAIN_MIN_DASHES:
    return []
  sizes = sorted(d[2] - d[1] for d in run)
  mid = sizes[len(sizes) // 2]
  same = [d for d in run if abs((d[2] - d[1]) - mid) <= DASH_SPREAD * mid]
  if len(same) < CHAIN_MIN_DASHES:
    return []
  line = sum(d[0] for d in same) / len(same)
  return [{"axis": axis, "line": line, "lo": same[0][1], "hi": same[-1][2], "dashes": len(same)}]

def legs(segments: list, mm_per_pt: float) -> list:
  found = chains(segments, mm_per_pt)
  lo_w, hi_w, need = WIDTH_MIN_MM / mm_per_pt, WIDTH_MAX_MM / mm_per_pt, OVERLAP_MIN_MM / mm_per_pt
  near: list = [[] for _ in found]
  for i, a in enumerate(found):
    for j, b in enumerate(found):
      if i != j and a["axis"] == b["axis"] and abs(a["line"] - b["line"]) <= hi_w and min(a["hi"], b["hi"]) - max(a["lo"], b["lo"]) >= need:
        near[i].append(j)
  out = []
  
  for i, a in enumerate(found):
    if len(near[i]) != 1 or i > near[i][0] or len(near[near[i][0]]) != 1:
      continue
    b = found[near[i][0]]
    gap = abs(a["line"] - b["line"])
    if gap < lo_w:
      continue
  
    lo, hi = max(a["lo"], b["lo"]), min(a["hi"], b["hi"])
    c = (a["line"] + b["line"]) / 2.0
    p0, p1 = ((lo, c), (hi, c)) if a["axis"] == "H" else ((c, lo), (c, hi))
    out.append({"axis": a["axis"], "p0": p0, "p1": p1, "width_pt": gap, "length_pt": hi - lo, "dashed": True})
  return out
