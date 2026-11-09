from __future__ import annotations
import re
from app.engine.measure import steel_grammar as SG
from app.modules.drawings_boq.takeoff.page import settings as S
from app.modules.drawings_boq.takeoff.page.model import SECTION_PICTURE, Region

SUMMED = re.compile(r"\d\s*\+\s*\d")

def bar_string(text: str) -> bool:
  got = SG.parse_callout(text or "")
  return bool((got["bars"] or got["spaced"]) and not got["unread"])

def _links(points: list, reach: float) -> list:
  parent = list(range(len(points)))
  def find(a):
    while parent[a] != a:
      parent[a] = parent[parent[a]]
      a = parent[a]
    return a
  
  order = sorted(range(len(points)), key=lambda i: points[i][0])
  for a, i in enumerate(order):
    for j in order[a + 1:]:
      if points[j][0] - points[i][0] > reach:
        break
      if abs(points[j][1] - points[i][1]) <= reach and (points[j][0] - points[i][0]) ** 2 + (points[j][1] - points[i][1]) ** 2 <= reach * reach:
        ra, rb = find(i), find(j)
        if ra != rb:
          parent[ra] = rb
  groups: dict = {}
  for i in range(len(points)):
    groups.setdefault(find(i), []).append(i)
  return list(groups.values())

def _cut(points: list, ratio: float, depth: int = 0) -> list:
  if len(points) < 2 or depth > 6:
    return [points]
  w = max(p[0] for p in points) - min(p[0] for p in points)
  h = max(p[1] for p in points) - min(p[1] for p in points)
  axis = 0 if w > ratio * max(h, 1e-9) else 1 if h > ratio * max(w, 1e-9) else None
  if axis is None:
    return [points]
  order = sorted(points, key=lambda p: p[axis])
  gaps = [(order[i + 1][axis] - order[i][axis], i) for i in range(len(order) - 1)]
  gap, at = max(gaps)
  if gap < 0.2 * (w if axis == 0 else h):
    return [points]
  return _cut(order[:at + 1], ratio, depth + 1) + _cut(order[at + 1:], ratio, depth + 1)

def _ink_around(ctx, box: tuple, reach: float):
  import numpy as np
  out = None
  for band in ((box[0], box[1] - reach, box[2], box[1]), (box[0], box[3], box[2], box[3] + reach)):
    got = _ink_band(ctx, band)
    if got:
      out = got if out is None else (min(out[0], got[0]), min(out[1], got[1]), max(out[2], got[2]), max(out[3], got[3]))
  return out

def _ink_band(ctx, band: tuple):
  import numpy as np
  ink = ctx.ink
  r0, r1, c0, c1 = ink.cells(band)
  sub = ink.grid[r0:r1, c0:c1]
  if not sub.size or not sub.any():
    return None
  rr, cc = np.nonzero(sub)
  return ink.box_of(r0 + int(rr.min()), r0 + int(rr.max()) + 1, c0 + int(cc.min()), c0 + int(cc.max()) + 1)

def count_string(text: str) -> bool:
  if SUMMED.search(text or ""):
    return False
  got = SG.parse_callout(text or "")
  return bool(got["bars"] and not got["unread"])

def find(ctx, dot_points: list, taken: list) -> list:
  link = S.get("section", "dot_link") * ctx.h
  pad = S.get("section", "pad") * ctx.h
  reach = S.get("section", "string_reach") * ctx.h
  cap_reach = S.get("section", "caption_reach") * ctx.h
  size_min, size_max = S.get("section", "min_size") * ctx.h, S.get("section", "max_size") * ctx.h
  strings = [(i, w) for i, w in enumerate(ctx.words) if bar_string(w.text)]
  free = [p for p in dot_points if not any(t[0] <= p[0] <= t[2] and t[1] <= p[1] <= t[3] for t in taken)]
  out = []
  
  groups = [pts for idx in _links(free, link) for pts in _cut([free[i] for i in idx], S.get("section", "pair_ratio"))]
  for pts in groups:
    if len(pts) < int(S.get("section", "min_dots")):
      continue
    box = (min(p[0] for p in pts) - pad, min(p[1] for p in pts) - pad, max(p[0] for p in pts) + pad, max(p[1] for p in pts) + pad)
    near = [i for i, w in strings if box[0] - reach <= (w.u0 + w.u1) / 2 <= box[2] + reach and box[1] - reach <= (w.v0 + w.v1) / 2 <= box[3] + reach]
    if len(pts) < int(S.get("section", "stand_alone")) and not near:
      continue
    if not any(count_string(ctx.words[i].text) for i in near):
      continue
    spread = min(max(p[0] for p in pts) - min(p[0] for p in pts), max(p[1] for p in pts) - min(p[1] for p in pts))
    if spread < S.get("section", "min_spread") * ctx.h:
      continue
    w, h = box[2] - box[0], box[3] - box[1]
    if not (size_min <= w <= size_max and size_min <= h <= size_max and max(w, h) <= S.get("section", "max_aspect") * min(w, h)):
      continue
    
    ids = set(ctx.words_in((box[0], box[1], box[2], box[3]), share=0.5)) | set(near)
    band = (box[0], box[1] - cap_reach, box[2], box[1])
    cap = [i for i in ctx.words_in(band, share=0.5) if i not in ids]
    lines: dict = {}
    for i in cap:
      c = ctx.words[i]
      lines.setdefault(round(((c.v0 + c.v1) / 2) / (0.6 * ctx.h)), []).append(i)
    title = " ".join(" ".join(ctx.words[i].text for i in sorted(lines[k], key=lambda i: ctx.words[i].u0)) for k in sorted(lines, reverse=True)[:2]) if lines else ""
    ids |= set(cap)
    under = _ink_around(ctx, box, cap_reach)
    full = (min([box[0]] + [ctx.words[i].u0 for i in ids]), min([box[1]] + [ctx.words[i].v0 for i in ids]), max([box[2]] + [ctx.words[i].u1 for i in ids]), max([box[3]] + [ctx.words[i].v1 for i in ids]))
    if under:
      full = (min(full[0], under[0]), min(full[1], under[1]), max(full[2], under[2]), max(full[3], under[3]))
    out.append(Region(SECTION_PICTURE, ctx.user_box(full), title, sorted(ids), lines=0, rings=len(pts), turn=ctx.turn, confidence=min(1.0, 0.4 + 0.1 * len(pts) + (0.2 if near else 0.0)), source="sections.dots", extra={"dots": len(pts), "strings": len(near)}))
  return _group(out, ctx)

def _group(regions: list, ctx) -> list:
  if not regions:
    return regions
  centres = sorted(((r.box[1] + r.box[3]) / 2 for r in regions))
  rows: list = []
  for c in centres:
    if rows and c - rows[-1][-1] <= 0.75 * max(r.box[3] - r.box[1] for r in regions):
      rows[-1].append(c)
    else:
      rows.append([c])
  for r in regions:
    mid = (r.box[1] + r.box[3]) / 2
    r.group = next(i for i, row in enumerate(rows) if mid in row)
  return regions
