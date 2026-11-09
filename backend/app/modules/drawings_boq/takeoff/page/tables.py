from __future__ import annotations
import numpy as np
from app.modules.drawings_boq.takeoff.page import settings as S
from app.modules.drawings_boq.takeoff.page.model import SCHEDULE, Region, union

def _tol(ctx) -> float:
  return S.get("table", "tol") * ctx.h

def sheet_frame(ctx) -> tuple:
  u0, v0, u1, v1 = ctx.bounds
  share = S.get("title_block", "frame_share")
  hs = [l for l in ctx.hs if l[1] - l[0] >= share * (u1 - u0)]
  vs = [l for l in ctx.vs if l[1] - l[0] >= share * (v1 - v0)]
  if len(hs) < 2 or len(vs) < 2:
    return ctx.bounds
  return (min(l[2] for l in vs), min(l[2] for l in hs), max(l[2] for l in vs), max(l[2] for l in hs))

def drop_border(ctx, frame: tuple | None = None) -> tuple:
  edge = S.get("title_block", "edge") * ctx.h
  u0, v0, u1, v1 = frame or ctx.bounds
  hs = [l for l in ctx.hs if not (min(abs(l[2] - v0), abs(v1 - l[2])) <= edge and l[1] - l[0] >= 0.5 * (u1 - u0))]
  vs = [l for l in ctx.vs if not (min(abs(l[2] - u0), abs(u1 - l[2])) <= edge and l[1] - l[0] >= 0.5 * (v1 - v0))]
  return hs, vs

def components(ctx, hs: list, vs: list) -> list:
  tol = _tol(ctx)
  nh, nv = len(hs), len(vs)
  if not nh or not nv:
    return []
  
  H = np.array(hs, dtype=np.float64)
  V = np.array(vs, dtype=np.float64)
  parent = list(range(nh + nv))
  def find(a):
    while parent[a] != a:
      parent[a] = parent[parent[a]]
      a = parent[a]
    return a
  step = max(1, 4_000_000 // max(nv, 1))
  for s in range(0, nh, step):
    h = H[s:s + step]
    cross = (V[None, :, 2] >= h[:, None, 0] - tol) & (V[None, :, 2] <= h[:, None, 1] + tol) & (h[:, None, 2] >= V[None, :, 0] - tol) & (h[:, None, 2] <= V[None, :, 1] + tol)
    ii, jj = np.nonzero(cross)
    for i, j in zip(ii, jj):
      a, b = find(s + int(i)), find(nh + int(j))
      if a != b:
        parent[a] = b
        
  groups: dict = {}
  for i in range(nh + nv):
    groups.setdefault(find(i), []).append(i)
  out = []
  for members in groups.values():
    gh = [hs[i] for i in members if i < nh]
    gv = [vs[i - nh] for i in members if i >= nh]
    if not gh or not gv:
      continue
    box = (min(min(l[0] for l in gh), min(l[2] for l in gv)), min(min(l[2] for l in gh), min(l[0] for l in gv)), max(max(l[1] for l in gh), max(l[2] for l in gv)), max(max(l[2] for l in gh), max(l[1] for l in gv)))
    out.append({"hs": gh, "vs": gv, "box": box})
  return out

def _levels(values: list, tol: float) -> list:
  out: list = []
  for v in sorted(values):
    if out and v - out[-1] <= tol:
      continue
    out.append(v)
  return out

def grid_of(ctx, comp: dict) -> dict | None:
  tol = _tol(ctx)
  span = S.get("table", "span")
  b = comp["box"]
  w, h = b[2] - b[0], b[3] - b[1]
  if w <= 0 or h <= 0:
    return None
  
  rows = _levels([l[2] for l in comp["hs"] if l[1] - l[0] >= span * w], tol)
  cols = _levels([l[2] for l in comp["vs"] if l[1] - l[0] >= span * h], tol)
  if len(rows) < S.get("table", "min_rows") or len(cols) < S.get("table", "min_cols"):
    return None
  return {"rows": rows, "cols": cols, "box": b}

def cells_with_words(ctx, grid: dict) -> tuple:
  rows, cols = grid["rows"], grid["cols"]
  n = held = 0
  centres = [((w.u0 + w.u1) / 2, (w.v0 + w.v1) / 2) for w in ctx.words]
  for r in range(len(rows) - 1):
    for c in range(len(cols) - 1):
      n += 1
      if any(cols[c] <= x <= cols[c + 1] and rows[r] <= y <= rows[r + 1] for x, y in centres):
        held += 1
  return n, held

def too_fine(ctx, grid: dict) -> bool:
  rows = sorted(b - a for a, b in zip(grid["rows"], grid["rows"][1:]))
  cols = sorted(b - a for a, b in zip(grid["cols"], grid["cols"][1:]))
  return rows[len(rows) // 2] < S.get("table", "min_row_h") * ctx.h or cols[len(cols) // 2] < S.get("table", "min_col_w") * ctx.h

def crowded(ctx, grid: dict) -> bool:
  n, held = cells_with_words(ctx, grid)
  inside = sum(1 for w in ctx.words if grid["box"][0] <= (w.u0 + w.u1) / 2 <= grid["box"][2] and grid["box"][1] <= (w.v0 + w.v1) / 2 <= grid["box"][3])
  return n > 0 and inside / n > S.get("table", "max_words_per_cell")

def tall_cells(ctx, grid: dict) -> int:
  rows = grid["rows"]
  limit = S.get("table", "max_cell_h") * ctx.h
  return sum(1 for a, b in zip(rows, rows[1:]) if b - a > limit)

def ruled(ctx, hs: list, vs: list) -> list:
  out = []
  for comp in components(ctx, hs, vs):
    g = grid_of(ctx, comp)
    if g is None:
      continue
    n, held = cells_with_words(ctx, g)
    if n == 0 or held < S.get("table", "text_share") * n or tall_cells(ctx, g) > 0.5 * (len(g["rows"]) - 1) or too_fine(ctx, g) or crowded(ctx, g):
      continue
    out.append({"box": g["box"], "rows": len(g["rows"]) - 1, "cols": len(g["cols"]) - 1, "cells": n, "text_cells": held, "kind": "RULED"})
  return out

def unruled(ctx, taken: list) -> list:
  align = S.get("table", "align") * ctx.h
  even = S.get("table", "even")
  rows_min, cols_min = int(S.get("table", "min_rows")), int(S.get("table", "min_cols"))
  free = [w for w in ctx.words if w.turn == 0 and not any(t[0] <= (w.u0 + w.u1) / 2 <= t[2] and t[1] <= (w.v0 + w.v1) / 2 <= t[3] for t in taken)]
  lines: list = []
  
  for w in sorted(free, key=lambda w: -(w.v0 + w.v1) / 2):
    y = (w.v0 + w.v1) / 2
    for ln in lines:
      if abs(ln["y"] - y) <= 0.4 * ctx.h:
        ln["words"].append(w)
        break
    else:
      lines.append({"y": y, "words": [w]})
      
  gap = S.get("notes", "word_gap") * ctx.h
  cell_words = S.get("table", "max_cell_group_words")
  kept: list = []
  for ln in lines:
    ws = sorted(ln["words"], key=lambda w: w.u0)
    groups: list = [[ws[0]]]
    for w in ws[1:]:
      if w.u0 - groups[-1][-1].u1 > gap:
        groups.append([w])
      else:
        groups[-1].append(w)
    sizes = sorted(len(g) for g in groups)
    if len(groups) >= cols_min and sizes[len(sizes) // 2] <= cell_words:
      kept.append({"y": ln["y"], "words": ln["words"], "groups": groups})
      
  lines = kept
  out: list = []
  used: set = set()
  for edge in ("l", "r"):
    key = (lambda g: g[0].u0) if edge == "l" else (lambda g: g[-1].u1)
    cols: dict = {}
    
    for i, ln in enumerate(lines):
      for g in ln["groups"]:
        cols.setdefault(round(key(g) / max(align, 1e-6)), []).append((i, g))
    cand = [c for c in cols.values() if len({i for i, _ in c}) >= rows_min]
    for c in cand:
      idx = sorted({i for i, _ in c})
      run = [idx[0]]
      runs = []
      for a, b in zip(idx, idx[1:]):
        if b == a + 1:
          run.append(b)
        else:
          runs.append(run)
          run = [b]
          
      runs.append(run)
      for rn in runs:
        if len(rn) < rows_min:
          continue
        ys = [lines[i]["y"] for i in rn]
        gaps = [a - b for a, b in zip(ys, ys[1:])]
        mean = sum(gaps) / len(gaps)
        if mean <= 0 or any(abs(g - mean) > even * mean for g in gaps) or mean > 4.0 * ctx.h:
          continue
        members = [w for i in rn for w in lines[i]["words"]]
        
        edges: dict = {}
        for i in rn:
          for e in {round(key(g) / max(align, 1e-6)) for g in lines[i]["groups"]}:
            edges[e] = edges.get(e, 0) + 1
        n_cols = sum(1 for n in edges.values() if n >= rows_min)
        if n_cols < cols_min:
          continue
        k = (rn[0], rn[-1])
        if k in used:
          continue
        used.add(k)
        out.append({"box": (min(w.u0 for w in members), min(w.v0 for w in members), max(w.u1 for w in members), max(w.v1 for w in members)), "rows": len(rn), "cols": n_cols, "cells": len(members), "text_cells": len(members), "kind": "UNRULED"})
  return merge_overlapping(out)

def merge_overlapping(items: list) -> list:
  items = sorted(items, key=lambda t: -((t["box"][2] - t["box"][0]) * (t["box"][3] - t["box"][1])))
  keep: list = []
  for t in items:
    b = t["box"]
    a = max((b[2] - b[0]) * (b[3] - b[1]), 1e-9)
    inside = [k for k in keep if max(0.0, min(b[2], k["box"][2]) - max(b[0], k["box"][0])) * max(0.0, min(b[3], k["box"][3]) - max(b[1], k["box"][1])) / a > 0.5]
    if inside:
      continue
    keep.append(t)
  return keep

def regions(ctx, found: list) -> list:
  out = []
  for t in found:
    ids = ctx.words_in(t["box"])
    out.append(Region(SCHEDULE, ctx.user_box(t["box"]), "", ids, lines=t["rows"] + t["cols"], rings=0, turn=ctx.turn, confidence=min(1.0, t["text_cells"] / max(t["cells"], 1) + 0.2), source="tables." + t["kind"].lower(), extra={"rows": t["rows"], "cols": t["cols"]}))
  return out
