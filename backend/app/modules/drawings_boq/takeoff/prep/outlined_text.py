from __future__ import annotations
import os
import re
import time
from app.engine.measure import readings as RD
from app.modules.drawings_boq.takeoff.prep import pdf_type as PT, ocr_layer, text_repair as TR

MARK_WHITELIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"
MARK = re.compile(r"^[A-Z]{1,3}-?\d{1,2}[A-Z]?$")
LABELS_OUTLINED, OCR_LOW_CONFIDENCE = "LABELS_OUTLINED", "OCR_LOW_CONFIDENCE"
ENABLED = os.environ.get("TRACE_OUTLINED_REGIONS", "1") != "0"

def glyph_boxes(rings: list) -> list:
  out = []
  for r in rings:
    if not r.fill:
      continue
    w, h = r.bbox[2] - r.bbox[0], r.bbox[3] - r.bbox[1]
    if PT.GLYPH_MIN_W_PT <= w <= PT.GLYPH_MAX_W_PT and PT.GLYPH_MIN_H_PT <= h <= PT.GLYPH_MAX_H_PT:
      out.append(tuple(r.bbox))
  return out

def label_like(text: str) -> bool:
  t = text.strip().upper()
  return bool(MARK.match(t)) or (len(t) >= 3 and t.isalpha() and t in TR.words())

def _merge_runs(boxes: list, axis: int) -> list:
  other = 1 - axis
  order = sorted(boxes, key=lambda b: (round((b[other] + b[other + 2]) / 2 / 4.0), b[axis]))
  runs: list = []
  
  for b in order:
    for c in runs:
      cross = max(c["box"][other + 2] - c["box"][other], b[other + 2] - b[other], 1e-9)
      same_line = abs((c["box"][other] + c["box"][other + 2]) / 2 - (b[other] + b[other + 2]) / 2) < 0.5 * cross
      gap = b[axis] - c["box"][axis + 2]
      if same_line and -0.5 <= gap <= RD.OUTLINED_GAP_GLYPHS * (b[axis + 2] - b[axis]):
        c["box"] = (min(c["box"][0], b[0]), min(c["box"][1], b[1]), max(c["box"][2], b[2]), max(c["box"][3], b[3]))
        c["n"] += 1
        c["members"].append(b)
        break
    else:
      runs.append({"box": b, "n": 1, "axis": axis, "members": [b]})
  return runs

def clusters(rings: list) -> list:
  boxes = glyph_boxes(rings)
  found = [c for axis in (0, 1) for c in _merge_runs(boxes, axis) if c["n"] >= RD.OUTLINED_MIN_GLYPHS]
  keep: list = []
  for c in sorted(found, key=lambda c: -c["n"]):
    if not any(_overlap(c["box"], k["box"]) > 0.5 for k in keep):
      keep.append(c)
  return keep

def _overlap(a: tuple, b: tuple) -> float:
  ix, iy = min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])
  if ix <= 0 or iy <= 0:
    return 0.0
  return ix * iy / max(min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])), 1e-9)

def isolated(found: list, boxes: list) -> list:
  out = []
  for c in found:
    x0, y0, x1, y1 = c["box"]
    reach = RD.OUTLINED_HALO_GLYPHS * max(min(x1 - x0, y1 - y0), 3.0)
    own = {tuple(b) for b in c["members"]}
    inside = lambda b: _overlap(b, c["box"]) >= 0.5
    near = [b for b in boxes if tuple(b) not in own and not inside(b) and b[0] < x1 + reach and b[2] > x0 - reach and b[1] < y1 + reach and b[3] > y0 - reach]
    if c["n"] <= RD.OUTLINED_MAX_GLYPHS and len(near) <= RD.OUTLINED_MAX_NEIGHBOURS:
      out.append(c)
  return out

def uncovered(found: list, words: list) -> list:
  out = []
  for c in found:
    x0, y0, x1, y1 = c["box"]
    if not any(max(0.0, min(x1, w.x1) - max(x0, w.x0)) * max(0.0, min(y1, w.y1) - max(y0, w.y0)) > 0.3 * max((x1 - x0) * (y1 - y0), 1e-9) for w in words):
      out.append(c)
  return out

def evidence(rings: list, words: list) -> dict | None:
  if not ENABLED:
    return None
  found = isolated(uncovered(clusters(rings), words), glyph_boxes(rings))
  if len(found) < RD.OUTLINED_MIN_UNCOVERED:
    return None
  return {"partial_outline": True, "uncovered_clusters": len(found), "regions": [c["box"] for c in found[:RD.OUTLINED_MAX_REGIONS]]}

def _user_to_view(x: float, y: float, rotation: int, crop: tuple) -> tuple:
  cx0, cy0, cx1, cy1 = crop
  if rotation == 90:
    return y - cy0, x - cx0
  if rotation == 180:
    return cx1 - x, y - cy0
  if rotation == 270:
    return cy1 - y, cx1 - x
  return x - cx0, cy1 - y

def _view_box(box: tuple, rotation: int, crop: tuple) -> tuple:
  pts = [_user_to_view(x, y, rotation, crop) for x, y in ((box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3]))]
  return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)

def read_regions(page, rotation: int, cropbox: tuple, regions: list, budget_s: float) -> tuple:
  info: dict = {"regions": len(regions)}
  if not ocr_layer.available():
    info["error"] = "UNAVAILABLE"
    return [], info
  started = time.monotonic()
  words, unsure = [], 0
  marks: set = set()
  low: set = set()
  Wv, Hv = page.get_size()
  scale = RD.OUTLINED_OCR_DPI / 72.0
  
  for box in regions:
    if time.monotonic() - started > budget_s:
      info["partial"] = True
      break
  
    vx0, vy0, vx1, vy1 = _view_box(box, rotation, cropbox)
    m = RD.OUTLINED_REGION_MARGIN_PT
    vx0, vy0, vx1, vy1 = max(0.0, vx0 - m), max(0.0, vy0 - m), min(Wv, vx1 + m), min(Hv, vy1 + m)
    if vx1 - vx0 < 2.0 or vy1 - vy0 < 2.0:
      continue
    try:
      img = page.render(scale=scale, crop=(vx0, Hv - vy1, Wv - vx1, vy0)).to_pil().convert("L")
    except Exception:
      info["error"] = "RENDER"
      continue
  
    rows = ocr_layer._tsv(img, max(5.0, budget_s - (time.monotonic() - started)), "7", MARK_WHITELIST)
    text = "".join(r["text"] for r in sorted(rows, key=lambda r: r["l"]))
    if not text or not any(ch.isalnum() for ch in text):
      continue
    conf = min(r["conf"] for r in rows)
    if not label_like(text):
      info["not_a_label"] = info.get("not_a_label", 0) + 1
      continue
  
    w = ocr_layer._build_word(text, vx0 + m, vy0 + m, vx1 - m, vy1 - m, 0.0, rotation, cropbox)
    w.repair = LABELS_OUTLINED if conf >= RD.OUTLINED_MIN_CONFIDENCE else OCR_LOW_CONFIDENCE
    unsure += 0 if conf >= RD.OUTLINED_MIN_CONFIDENCE else 1
    marks.add(text.upper())
    if w.repair == OCR_LOW_CONFIDENCE:
      low.add(text.upper())
    words.append(w)
    
  info.update(words=len(words), unsure=unsure, marks=sorted(marks), low=sorted(low), dpi=RD.OUTLINED_OCR_DPI, seconds=round(time.monotonic() - started, 2))
  return words, info
