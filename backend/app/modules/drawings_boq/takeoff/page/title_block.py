from __future__ import annotations
from app.modules.drawings_boq.takeoff.page import settings as S
from app.modules.drawings_boq.takeoff.page import tables as TB
from app.modules.drawings_boq.takeoff.page.model import TITLE_BLOCK, Region

MIN_RULES = 6

def _strips(comps: list, side: str, gap: float) -> list:
  axis = 0 if side in ("bottom", "top") else 1
  order = sorted(comps, key=lambda c: c["box"][axis])
  out: list = []
  for c in order:
    if out and c["box"][axis] - out[-1]["end"] <= gap:
      out[-1]["members"].append(c)
      out[-1]["end"] = max(out[-1]["end"], c["box"][axis + 2])
    else:
      out.append({"members": [c], "end": c["box"][axis + 2]})
  return out

def find(ctx, hs: list, vs: list, frame: tuple | None = None) -> tuple:
  edge = S.get("title_block", "edge") * ctx.h
  side_share = S.get("title_block", "min_side")
  gap = S.get("title_block", "strip_gap") * ctx.h
  u0, v0, u1, v1 = frame or ctx.bounds
  comps = TB.components(ctx, hs, vs)
  best = None
  for side in ("bottom", "right", "top", "left"):
    near = []
    
    for c in comps:
      b = c["box"]
      touch = {"bottom": b[1] - v0 <= edge, "top": v1 - b[3] <= edge, "left": b[0] - u0 <= edge, "right": u1 - b[2] <= edge}[side]
      if touch:
        near.append(c)
    for strip in _strips(near, side, gap):
      members = strip["members"]
      n = sum(len(m["hs"]) + len(m["vs"]) for m in members)
      box = (min(m["box"][0] for m in members), min(m["box"][1] for m in members), max(m["box"][2] for m in members), max(m["box"][3] for m in members))
      w, h = box[2] - box[0], box[3] - box[1]
      along = w / max(u1 - u0, 1e-9) if side in ("bottom", "top") else h / max(v1 - v0, 1e-9)
      depth = h / max(v1 - v0, 1e-9) if side in ("bottom", "top") else w / max(u1 - u0, 1e-9)
      if n >= MIN_RULES and along >= side_share and depth <= 0.35 and (best is None or along * n > best[0]):
        best = (along * n, members, side, box)
        
  if best is None:
    return [], hs, vs
  _score, members, side, box = best
  taken = {id(l) for m in members for l in m["hs"]} | {id(l) for m in members for l in m["vs"]}
  region = Region(TITLE_BLOCK, ctx.user_box(box), "", ctx.words_in(box), lines=len(taken), rings=0, turn=ctx.turn, confidence=0.9, source="title_block.attached", extra={"side": side})
  return [region], [l for l in hs if id(l) not in taken], [l for l in vs if id(l) not in taken]
