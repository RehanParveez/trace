from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.page import sections as SEC
from app.modules.drawings_boq.takeoff.page.model import CALLOUT, Region, contains_point, area

SPACING_SHAPE = re.compile(r"^#\s*\d{1,2}\s*[\"”″']{0,2}\s*@\s*\d{1,2}(?:\.\d)?")

def bar_or_spacing(text: str) -> bool:
  return SEC.bar_string(text) or bool(SPACING_SHAPE.match((text or "").strip()))

def find(ctx, regions: list) -> list:
  views = [(i, r) for i, r in enumerate(regions) if r.kind == "VIEW"]
  blocked = [r for r in regions if r.kind in ("SCHEDULE", "LEGEND", "NOTES", "SECTION_PICTURE", "TITLE_BLOCK")]
  out = []
  
  for n, w in enumerate(ctx.words):
    if not bar_or_spacing(w.text):
      continue
    box = ctx.user_box((w.u0, w.v0, w.u1, w.v1))
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    if any(contains_point(b.box, cx, cy) for b in blocked):
      continue
    home = [(i, r) for i, r in views if contains_point(r.box, cx, cy)]
    parent = min(home, key=lambda p: area(p[1].box))[0] if home else None
    out.append(Region(CALLOUT, box, w.text, [n], lines=0, rings=0, turn=ctx.turn, confidence=0.9 if parent is not None else 0.6, source="callouts.bar_string", parent=parent))
  return out
