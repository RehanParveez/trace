from __future__ import annotations
from app.modules.drawings_boq.takeoff.page.model import Region, area, contains_point

ATTR = "page_model_cache"

def to_page_of(page):
  from app.modules.drawings_boq.takeoff.extract import electrical_symbols as ES
  rot, ox, oy, wu, hu = ES._geometry(page)
  return lambda b: ES._to_page_rect(rot, ox, oy, wu, hu, tuple(b))

def model_of(raw, legend_rows: list | None = None, to_page=None) -> dict:
  got = getattr(raw, ATTR, None)
  if got is not None:
    return got
  from app.modules.drawings_boq.takeoff.page import build as B
  model = B.build(raw, legend_rows=legend_rows, to_page=to_page)
  try:
    setattr(raw, ATTR, model)
  except Exception:
    pass
  return model

def regions_of(model: dict | None, *kinds: str) -> list:
  return [Region.from_json(d) for d in (model or {}).get("regions") or [] if not kinds or d["kind"] in kinds]

def words_of(words: list, region: Region) -> list:
  return [words[i] for i in region.words if 0 <= i < len(words)]

def holder(regions: list, x: float, y: float):
  held = [r for r in regions if contains_point(r.box, x, y)]
  return min(held, key=lambda r: area(r.box)) if held else None

def holder_or_over(regions: list, vis, x: float, y: float, reach: float):
  home = holder(regions, x, y)
  if home is not None:
    return home, tuple(home.box)
  vx, vy = vis(x, y)
  over = []
  
  for r in regions:
    corners = [vis(px, py) for px in (r.box[0], r.box[2]) for py in (r.box[1], r.box[3])]
    x0, x1 = min(c[0] for c in corners), max(c[0] for c in corners)
    bottom = max(c[1] for c in corners)
    if x0 <= vx <= x1 and 0 < vy - bottom <= reach:
      over.append((area(r.box), r))
  if not over:
    return None, None
  r = min(over, key=lambda t: t[0])[1]
  return r, (min(r.box[0], x), min(r.box[1], y), max(r.box[2], x), max(r.box[3], y))

def compact(model: dict | None) -> dict | None:
  if not model:
    return None
  out = []
  for d in model.get("regions") or []:
    c = {k: v for k, v in d.items() if k != "words"}
    c["n_words"] = len(d.get("words") or [])
    out.append(c)
  return {**{k: v for k, v in model.items() if k != "regions"}, "regions": out}
