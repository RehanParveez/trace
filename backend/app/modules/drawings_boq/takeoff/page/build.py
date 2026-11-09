from __future__ import annotations
import time
from app.modules.drawings_boq.takeoff.page import ink as I
from app.modules.drawings_boq.takeoff.page import tables as TB
from app.modules.drawings_boq.takeoff.page import title_block as TK
from app.modules.drawings_boq.takeoff.page import legends as LG
from app.modules.drawings_boq.takeoff.page import proposed as PR
from app.modules.drawings_boq.takeoff.page import notes as NO
from app.modules.drawings_boq.takeoff.page import sections as SEC
from app.modules.drawings_boq.takeoff.page import views as VW
from app.modules.drawings_boq.takeoff.page import callouts as CO
from app.modules.drawings_boq.takeoff.prep import words as WD
from app.modules.drawings_boq.takeoff.page.model import MODEL_VERSION, PRIORITY, Region, area, cut

def _rank(kind: str) -> int:
  return PRIORITY.index(kind)

def _parents(regions: list) -> None:
  for i, r in enumerate(regions):
    if r.kind == "VIEW" or r.parent is not None:
      continue
    held = [(j, o) for j, o in enumerate(regions) if o.kind == "VIEW" and j != i and cut(r.box, o.box) >= 0.8 * area(r.box)]
    if held:
      r.parent = min(held, key=lambda p: area(p[1].box))[0]

def _overlaps(regions: list) -> list:
  keep = []
  for r in regions:
    if r.kind == "VIEW":
      hit = [o for o in regions if o is not r and o.kind != "VIEW" and o.kind != "CALLOUT" and cut(r.box, o.box) >= 0.8 * area(r.box)]
      if hit:
        continue
    keep.append(r)
  return keep

def _text(regions: list, words: list) -> None:
  for r in regions:
    if r.kind == "CALLOUT":
      continue
    counts: dict = {}
    for i in r.words:
      if 0 <= i < len(words):
        s = getattr(words[i], "source", WD.NATIVE)
        counts[s] = counts.get(s, 0) + 1
    if counts:
      r.extra = {**r.extra, "text": counts}

def build(raw, legend_rows: list | None = None, to_page=None) -> dict:
  started = time.monotonic()
  ctx = I.Ctx(raw)
  frame = TB.sheet_frame(ctx)
  hs, vs = TB.drop_border(ctx, frame)
  found: list = []
  titles, hs, vs = TK.find(ctx, hs, vs, frame)
  found += titles
  
  masked = [ctx.frame_box(r.box) for r in titles]
  tabs = TB.merge_overlapping(TB.ruled(ctx, hs, vs))
  tabs = TB.merge_overlapping(tabs + TB.unruled(ctx, [t["box"] for t in tabs] + masked))
  tables = TB.regions(ctx, tabs)
  found += tables
  masked += [t["box"] for t in tabs]
  legends = LG.from_rows(ctx, legend_rows, to_page)
  found += legends
  masked += [ctx.frame_box(r.box) for r in legends]
  notes = NO.find(ctx, [m for m in masked if m not in [ctx.frame_box(r.box) for r in titles]])
  found += notes
  masked += [ctx.frame_box(r.box) for r in notes]
  pictures = SEC.find(ctx, I.dots(ctx), masked)
  found += pictures
  
  masked += [ctx.frame_box(r.box) for r in pictures]
  clusters, _frames = VW.clusters(ctx, masked)
  found += VW.regions(ctx, clusters)
  found.sort(key=lambda r: (_rank(r.kind), r.box[1], r.box[0]))
  found = _overlaps(found)
  found, proposed = PR.accept(ctx, found, getattr(raw, "ai_regions", None))
  found += CO.find(ctx, found)
  _parents(found)
  _text(found, raw.words)
  return {"version": MODEL_VERSION, "h": round(ctx.h, 3), "unit": round(ctx.unit, 4), "turn": ctx.turn, "seconds": round(time.monotonic() - started, 3), "regions": [r.to_json() for r in found], **({"proposed": proposed} if proposed["given"] else {})}
