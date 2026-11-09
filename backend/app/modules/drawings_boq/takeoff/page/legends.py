from __future__ import annotations
from app.modules.drawings_boq.takeoff.page import settings as S
from app.modules.drawings_boq.takeoff.page.model import LEGEND, Region

def from_rows(ctx, rows: list, to_page=None) -> list:
  blocks = []
  for r in rows or []:
    b = r.get("block")
    if b and len(b) == 4:
      blocks.append(tuple(to_page(tuple(b))) if to_page else tuple(b))
  seen: list = []
  
  for b in blocks:
    if b not in seen:
      seen.append(b)
  pad = S.get("legend", "pad") * ctx.h
  out = []
  for b in seen:
    fb = ctx.frame_box(b)
    padded = (fb[0] - pad, fb[1] - pad, fb[2] + pad, fb[3] + pad)
    out.append(Region(LEGEND, ctx.user_box(padded), "", ctx.words_in(padded), lines=0, rings=0, turn=ctx.turn, confidence=0.9, source="legends.electrical"))
  return out
