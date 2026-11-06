from __future__ import annotations
from app.modules.drawings_boq.takeoff.profile import pages as PG
from app.modules.drawings_boq.takeoff.prep import title_strip as TS

def zone_of(page) -> list:
  tp = page.get_textpage()
  text = tp.get_text_range()
  width, height = page.get_size()
  l, b, r, t = page.get_cropbox()
  words = PG._words(tp, text, int(page.get_rotation() or 0), r - l, t - b)
  return TS.zone_phrases(TS.phrases(words), (0.0, 0.0, float(width), float(height))) if words else []

def merge_zones(first: list, second: list) -> list:
  out = list(first)
  for z in second:
    cx, cy = (z["b"][0] + z["b"][2]) / 2.0, (z["b"][1] + z["b"][3]) / 2.0
    if not any(o["t"].strip() == z["t"].strip() and abs((o["b"][0] + o["b"][2]) / 2.0 - cx) <= 0.01 and abs((o["b"][1] + o["b"][3]) / 2.0 - cy) <= 0.01 for o in first):
      out.append(z)
  return out[:TS.ZONE_CAP * 2]

