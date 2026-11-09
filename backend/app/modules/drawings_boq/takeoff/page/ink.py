from __future__ import annotations
import math
import numpy as np
from app.modules.drawings_boq.takeoff.extract import structure_tables as ST
from app.modules.drawings_boq.takeoff.prep import page_unit as PU
from app.modules.drawings_boq.takeoff.page import settings as S

class Ctx:

  def __init__(self, raw):
    self.raw = raw
    self.words, self.f = ST.upright_words(raw)
    self.turn = ST.frame_turn(raw.words)
    c, s = (1, 0, -1, 0)[self.turn], (0, 1, 0, -1)[self.turn]
    self._back = lambda u, v: (u * c - v * s, u * s + v * c)
    x0, y0, x1, y1 = raw.cropbox
    
    corners = [self.f(x, y) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    self.bounds = (min(p[0] for p in corners), min(p[1] for p in corners), max(p[0] for p in corners), max(p[1] for p in corners))
    self.unit = PU.unit((raw.width_pt, raw.height_pt))
    sizes = sorted(w.size for w in self.words if len(w.text) >= 2 and w.size > 0)
    self.h = sizes[len(sizes) // 2] if sizes else S.top("text_ref_pt") * self.unit
    self.diag = math.hypot(self.bounds[2] - self.bounds[0], self.bounds[3] - self.bounds[1])
    self.hs, self.vs, self.ds = ST.upright_lines(raw, self.f, min_len=S.get("table", "min_rule") * self.h)
    self.hs, self.vs = ST._merge(self.hs, gap=0.3 * self.h), ST._merge(self.vs, gap=0.3 * self.h)
    self.ink = Ink(self)

  def user_box(self, b: tuple) -> tuple:
    pts = [self._back(u, v) for u, v in ((b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3]))]
    return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))

  def frame_box(self, b: tuple) -> tuple:
    pts = [self.f(x, y) for x, y in ((b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3]))]
    return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))

  def words_in(self, box: tuple, share: float = 0.5) -> list:
    out = []
    for i, w in enumerate(self.words):
      a = (w.u1 - w.u0) * (w.v1 - w.v0)
      if a <= 0:
        continue
      ix, iy = min(box[2], w.u1) - max(box[0], w.u0), min(box[3], w.v1) - max(box[1], w.v0)
      if ix > 0 and iy > 0 and ix * iy >= share * a:
        out.append(i)
    return out

class Ink:

  def __init__(self, ctx: Ctx, skip_words: bool = False):
    self.ctx = ctx
    u0, v0, u1, v1 = ctx.bounds
    cell = S.get("ink", "cell") * ctx.h
    cap = S.get("ink", "max_cells")
    while ((u1 - u0) / cell) * ((v1 - v0) / cell) > cap:
      cell *= 1.5
      
    self.cell, self.u0, self.v0 = cell, u0, v0
    self.nx, self.ny = max(1, int(math.ceil((u1 - u0) / cell))), max(1, int(math.ceil((v1 - v0) / cell)))
    self.grid = np.zeros((self.ny, self.nx), dtype=bool)
    self._paint_segments(ctx)
    for r in ctx.raw.rings:
      self.paint_box(ctx.frame_box(r.bbox))
    for im in ctx.raw.images:
      b = im.get("bbox")
      if b and (b[2] - b[0]) * (b[3] - b[1]) < 0.5 * ctx.raw.width_pt * ctx.raw.height_pt:
        self.paint_box(ctx.frame_box(tuple(b)))
    if not skip_words:
      for w in ctx.words:
        self.paint_box((w.u0, w.v0, w.u1, w.v1))

  def _paint_segments(self, ctx: Ctx) -> None:
    s = np.asarray(ctx.raw.segs, dtype=np.float64).reshape(-1, 5)
    if not len(s):
      return
    
    c, sn = (1, 0, -1, 0)[ctx.turn], (0, 1, 0, -1)[ctx.turn]
    ax, ay, bx, by = s[:, 0], s[:, 1], s[:, 2], s[:, 3]
    au, av = ax * c + ay * sn, -ax * sn + ay * c
    bu, bv = bx * c + by * sn, -bx * sn + by * c
    n = np.maximum(1, np.ceil(np.hypot(bu - au, bv - av) / self.cell * 2)).astype(int)
    total = int(n.sum() + len(n))
    
    if total > 12_000_000:
      keep = np.argsort(-np.hypot(bu - au, bv - av))[:max(1, len(n) // 2)]
      au, av, bu, bv, n = au[keep], av[keep], bu[keep], bv[keep], n[keep]
    idx = np.repeat(np.arange(len(n)), n + 1)
    first = np.cumsum(np.r_[0, n + 1])[:-1]
    t = (np.arange(len(idx)) - np.repeat(first, n + 1)) / np.repeat(n, n + 1)
    us, vs = au[idx] + t * (bu[idx] - au[idx]), av[idx] + t * (bv[idx] - av[idx])
    cu, cv = ((us - self.u0) / self.cell).astype(int), ((vs - self.v0) / self.cell).astype(int)
    ok = (cu >= 0) & (cu < self.nx) & (cv >= 0) & (cv < self.ny)
    self.grid[cv[ok], cu[ok]] = True

  def cells(self, box: tuple) -> tuple:
    c0, c1 = int(math.floor((box[0] - self.u0) / self.cell)), int(math.ceil((box[2] - self.u0) / self.cell))
    r0, r1 = int(math.floor((box[1] - self.v0) / self.cell)), int(math.ceil((box[3] - self.v0) / self.cell))
    return max(0, r0), min(self.ny, r1), max(0, c0), min(self.nx, c1)

  def paint_box(self, box: tuple) -> None:
    r0, r1, c0, c1 = self.cells(box)
    if r1 > r0 and c1 > c0:
      self.grid[r0:r1, c0:c1] = True

  def clear_box(self, box: tuple, grid: np.ndarray | None = None) -> None:
    r0, r1, c0, c1 = self.cells(box)
    (self.grid if grid is None else grid)[r0:r1, c0:c1] = False

  def count(self, box: tuple) -> int:
    r0, r1, c0, c1 = self.cells(box)
    return int(self.grid[r0:r1, c0:c1].sum()) if r1 > r0 and c1 > c0 else 0

  def box_of(self, r0: int, r1: int, c0: int, c1: int) -> tuple:
    return (self.u0 + c0 * self.cell, self.v0 + r0 * self.cell, self.u0 + c1 * self.cell, self.v0 + r1 * self.cell)

  def dilate(self, grid: np.ndarray, radius_cells: int) -> np.ndarray:
    if radius_cells <= 0:
      return grid.copy()
    out = grid.copy()
    for _ in range(1):
      pad = np.pad(grid, radius_cells)
      acc = np.zeros_like(grid)
      for dy in range(-radius_cells, radius_cells + 1):
        for dx in range(-radius_cells, radius_cells + 1):
          acc |= pad[radius_cells + dy:radius_cells + dy + grid.shape[0], radius_cells + dx:radius_cells + dx + grid.shape[1]]
      out |= acc
    return out

  def components(self, grid: np.ndarray, with_labels: bool = False, four: bool = False):
    ny, nx = grid.shape
    label = np.zeros((ny, nx), dtype=np.int32)
    parent: list = [0]
    def find(a):
      while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
      return a
    prev: list = []
    for r in range(ny):
      row = grid[r]
      if not row.any():
        prev = []
        continue
      
      d = np.diff(np.r_[False, row, False].astype(np.int8))
      starts, ends = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
      cur: list = []
      j = 0
      for s0, e0 in zip(starts, ends):
        ids = []
        while j < len(prev) and prev[j][1] < s0 + (1 if four else 0):
          j += 1
        k = j
        while k < len(prev) and prev[k][0] < e0 + (0 if four else 1):
          ids.append(prev[k][2])
          k += 1
        if ids:
          root = find(ids[0])
          for o in ids[1:]:
            ro = find(o)
            if ro != root:
              parent[ro] = root
          lab = root
          
        else:
          parent.append(len(parent))
          lab = len(parent) - 1
        label[r, s0:e0] = lab
        cur.append((s0, e0, lab))
        if k > 0:
          j = max(j, k - 1)
      prev = cur
      
    flat = np.array([find(i) for i in range(len(parent))], dtype=np.int32)
    lab = flat[label]
    lab[label == 0] = 0
    out = []
    rr, cc = np.nonzero(lab)
    if len(rr):
      ll = lab[rr, cc]
      order = np.argsort(ll, kind="stable")
      rr, cc, ll = rr[order], cc[order], ll[order]
      cut = np.flatnonzero(np.r_[True, ll[1:] != ll[:-1]])
      cnt = np.diff(np.r_[cut, len(ll)])
      r_lo, r_hi = np.minimum.reduceat(rr, cut), np.maximum.reduceat(rr, cut)
      c_lo, c_hi = np.minimum.reduceat(cc, cut), np.maximum.reduceat(cc, cut)
      ink = np.add.reduceat(self.grid[rr, cc].astype(np.int64), cut)
      for i in range(len(cut)):
        out.append({"box": self.box_of(int(r_lo[i]), int(r_hi[i]) + 1, int(c_lo[i]), int(c_hi[i]) + 1), "cells": int(cnt[i]), "ink": int(ink[i]), "label": int(ll[cut[i]])})
    return (out, lab) if with_labels else out

def dots(ctx: Ctx) -> list:
  import numpy as _np
  raw = ctx.raw
  cell = 0.2 * ctx.h
  u0, v0, u1, v1 = ctx.bounds
  nx, ny = int(math.ceil((u1 - u0) / cell)) + 1, int(math.ceil((v1 - v0) / cell)) + 1
  if nx * ny > 12_000_000:
    return []
  
  g = _np.zeros((ny, nx), dtype=bool)
  s = _np.asarray(raw.segs, dtype=_np.float64).reshape(-1, 5)
  k = _np.asarray(raw.kinds)
  c, sn = (1, 0, -1, 0)[ctx.turn], (0, 1, 0, -1)[ctx.turn]
  cur = s[k != 0] if len(k) == len(s) else s[:0]
  limit = S.get("section", "dot_max") * ctx.h
  for a in cur:
    au, av = a[0] * c + a[1] * sn, -a[0] * sn + a[1] * c
    bu, bv = a[2] * c + a[3] * sn, -a[2] * sn + a[3] * c
    if abs(bu - au) > limit or abs(bv - av) > limit:
      continue
    g[int((min(av, bv) - v0) / cell):int((max(av, bv) - v0) / cell) + 1, int((min(au, bu) - u0) / cell):int((max(au, bu) - u0) / cell) + 1] = True
  for r in raw.rings:
    if r.fill and r.curved and (r.bbox[2] - r.bbox[0]) <= limit and (r.bbox[3] - r.bbox[1]) <= limit:
      b = ctx.frame_box(r.bbox)
      g[int((b[1] - v0) / cell):int((b[3] - v0) / cell) + 1, int((b[0] - u0) / cell):int((b[2] - u0) / cell) + 1] = True
  if not g.any():
    return []
  
  tmp = Ink.__new__(Ink)
  tmp.ctx, tmp.cell, tmp.u0, tmp.v0, tmp.nx, tmp.ny, tmp.grid = ctx, cell, u0, v0, nx, ny, g
  out = []
  
  for comp in tmp.components(g):
    b = comp["box"]
    w, h = b[2] - b[0], b[3] - b[1]
    if w <= limit and h <= limit and w >= 0.15 * ctx.h and h >= 0.15 * ctx.h and max(w, h) <= 1.7 * min(w, h) and comp["cells"] >= 0.55 * (w / cell) * (h / cell):
      out.append(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2))
  return out
