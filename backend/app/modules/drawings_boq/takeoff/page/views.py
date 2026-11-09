from __future__ import annotations
import math
import numpy as np
from app.modules.drawings_boq.takeoff.page import settings as S
from app.modules.drawings_boq.takeoff.page.model import VIEW, Region

def _radius(ctx) -> int:
  return max(1, int(math.ceil(0.5 * S.get("view", "gap") * ctx.h / ctx.ink.cell)))

def mask(ctx, boxes: list) -> np.ndarray:
  g = ctx.ink.grid.copy()
  for b in boxes:
    ctx.ink.clear_box(b, g)
  return g

def _frames(ctx, g: np.ndarray, rounds: int = 3) -> tuple:
  thin = S.get("frame", "max_density")
  found: list = []
  ink = ctx.ink
  for _ in range(rounds):
    saved = ink.grid
    ink.grid = g
    comps, lab = ink.components(g, with_labels=True)
    ink.grid = saved
    changed = False
    for c in comps:
      b = c["box"]
      
      r0, r1, c0, c1 = ink.cells(b)
      area_cells = max((r1 - r0) * (c1 - c0), 1)
      if (r1 - r0) <= 4 or (c1 - c0) <= 4 or c["ink"] / area_cells > thin:
        continue
      inner = sum(o["ink"] for o in comps if o is not c and o["box"][0] >= b[0] and o["box"][1] >= b[1] and o["box"][2] <= b[2] and o["box"][3] <= b[3])
      if inner >= S.get("frame", "inner_share") * c["ink"]:
        g = g.copy()
        g[(lab == c["label"]) & g] = False
        found.append(b)
        changed = True
        
    if not changed:
      break
  return g, found

def clusters(ctx, boxes: list) -> tuple:
  g, frames = _frames(ctx, mask(ctx, boxes))
  ink = ctx.ink
  saved = ink.grid
  ink.grid = g
  comps = ink.components(ink.dilate(g, _radius(ctx)))
  out = []
  
  for c in comps:
    b = c["box"]
    r0, r1, c0, c1 = ink.cells(b)
    inner = int(g[r0:r1, c0:c1].sum())
    if inner:
      rr, cc = np.nonzero(g[r0:r1, c0:c1])
      tight = ink.box_of(r0 + int(rr.min()), r0 + int(rr.max()) + 1, c0 + int(cc.min()), c0 + int(cc.max()) + 1)
      out.append({"box": tight, "cells": c["cells"], "ink": inner})
  ink.grid = saved
  return out, frames

def title_of(ctx, box: tuple, taken: set) -> tuple:
  reach = S.get("view", "title_reach") * ctx.h
  tall = S.get("view", "title_height") * ctx.h
  cand = []
  
  for i, w in enumerate(ctx.words):
    if i in taken or w.turn != 0:
      continue
    x = (w.u0 + w.u1) / 2
    if not (box[0] - ctx.h <= x <= box[2] + ctx.h):
      continue
    below = box[1] - reach <= w.v1 <= box[1] + 2.5 * ctx.h
    above = box[3] - 2.5 * ctx.h <= w.v0 <= box[3] + reach
    if not (below or above):
      continue
    underlined = any(abs(l[2] - w.v0) <= 0.8 * ctx.h and l[0] <= w.u0 + 0.3 * ctx.h and l[1] >= w.u1 - 0.3 * ctx.h for l in ctx.hs)
    if w.size >= tall or underlined:
      cand.append((min(abs(w.v1 - box[1]), abs(w.v0 - box[3])), i))
      
  if not cand:
    return "", []
  best = min(cand)[1]
  v = (ctx.words[best].v0 + ctx.words[best].v1) / 2
  line = sorted([i for i, w in enumerate(ctx.words) if i not in taken and w.turn == 0 and abs((w.v0 + w.v1) / 2 - v) <= 0.5 * ctx.h and box[0] - ctx.h <= (w.u0 + w.u1) / 2 <= box[2] + ctx.h], key=lambda i: ctx.words[i].u0)
  return " ".join(ctx.words[i].text for i in line), line

def regions(ctx, found: list) -> list:
  size = S.get("view", "min_size") * ctx.h
  ink_min = S.get("view", "min_ink")
  out = []
  for c in found:
    b = c["box"]
    if b[2] - b[0] < size or b[3] - b[1] < size or c["ink"] < ink_min:
      continue
    ids = ctx.words_in(b)
    text, line = title_of(ctx, b, set())
    out.append(Region(VIEW, ctx.user_box(b), text, ids, lines=0, rings=0, turn=ctx.turn, confidence=0.8 if text else 0.6, source="views.ink", extra={"title_words": line}))
  return out
