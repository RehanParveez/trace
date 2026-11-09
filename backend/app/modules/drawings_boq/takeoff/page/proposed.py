from __future__ import annotations
from app.modules.drawings_boq.takeoff.page import ink as I
from app.modules.drawings_boq.takeoff.page import tables as TB
from app.modules.drawings_boq.takeoff.page import settings as S
from app.modules.drawings_boq.takeoff.page.model import SCHEDULE, SECTION_PICTURE, Region, area, share_inside

KINDS = (SCHEDULE, SECTION_PICTURE)
SOURCE = "ai.find"

def _inside(box: tuple, u0: float, v0: float, u1: float, v1: float) -> bool:
  return u0 >= box[0] - 1e-6 and u1 <= box[2] + 1e-6 and v0 >= box[1] - 1e-6 and v1 <= box[3] + 1e-6

def grid_in(ctx, box: tuple) -> dict:
  hs = [l for l in ctx.hs if _inside(box, l[0], l[2], l[1], l[2])]
  vs = [l for l in ctx.vs if _inside(box, l[2], l[0], l[2], l[1])]
  groups = TB.components(ctx, hs, vs)
  if not groups:
    return {"hs": 0, "vs": 0, "box": None}
  g = max(groups, key=lambda g: len(g["hs"]) * len(g["vs"]))
  return {"hs": len(g["hs"]), "vs": len(g["vs"]), "box": g["box"]}

def holds_schedule(ctx, box: tuple) -> tuple:
  g = grid_in(ctx, box)
  if g["box"] is None or g["hs"] < int(S.get("proposed", "min_h_rules")) or g["vs"] < int(S.get("proposed", "min_v_rules")):
    return False, f"NO_GRID: {g['hs']} horizontal and {g['vs']} vertical rules that cross"
  if area(g["box"]) < S.get("proposed", "cover") * area(box):
    return False, "GRID_TOO_SMALL: the ruled grid covers a small part of the box"
  return True, ""

def holds_section(ctx, box: tuple, dots: list) -> tuple:
  inside = [p for p in dots if box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3]]
  if len(inside) < int(S.get("proposed", "min_dots")):
    return False, f"NO_DOTS: {len(inside)} bar dots in the box"
  least = S.get("proposed", "min_outline") * ctx.h
  for r in ctx.raw.rings:
    if r.fill:
      continue
    b = ctx.frame_box(r.bbox)
    
    if min(b[2] - b[0], b[3] - b[1]) < least or not _inside(box, *b):
      continue
    held = [p for p in inside if b[0] <= p[0] <= b[2] and b[1] <= p[1] <= b[3]]
    if len(held) >= int(S.get("proposed", "min_dots")):
      return True, ""
  return False, "NO_OUTLINE: no closed outline in the box holds the dots"

def accept(ctx, found: list, proposals: list | None) -> tuple:
  report: dict = {"given": 0, "accepted": 0, "refused": []}
  if not proposals:
    return found, report
  dots = None
  out = list(found)
  for p in proposals:
    report["given"] += 1
    
    kind, raw_box = p.get("kind"), p.get("box")
    if kind not in KINDS or not isinstance(raw_box, (list, tuple)) or len(raw_box) != 4:
      report["refused"].append({"kind": kind, "box": raw_box, "why": "NOT_A_PROPOSAL"})
      continue
    page_box = tuple(float(v) for v in raw_box)
    box = ctx.frame_box(page_box)
    if area(box) <= 0:
      report["refused"].append({"kind": kind, "box": list(page_box), "why": "NO_AREA"})
      continue
    if any(r.kind == kind and share_inside(r.box, page_box) >= S.get("proposed", "same") and share_inside(page_box, r.box) >= S.get("proposed", "same") for r in out):
      report["refused"].append({"kind": kind, "box": list(page_box), "why": "ALREADY_FOUND"})
      continue
    
    if kind == SCHEDULE:
      ok, why = holds_schedule(ctx, box)
    else:
      dots = I.dots(ctx) if dots is None else dots
      ok, why = holds_section(ctx, box, dots)
    if not ok:
      report["refused"].append({"kind": kind, "box": list(page_box), "why": why})
      continue
    ids = ctx.words_in(box, share=0.5)
    out.append(Region(kind, page_box, str(p.get("title") or ""), sorted(ids), turn=ctx.turn, confidence=S.get("proposed", "confidence"), source=SOURCE, extra={"proposed": True}))
    report["accepted"] += 1
  return out, report
