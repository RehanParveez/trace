from __future__ import annotations
import os
import math
from app.modules.drawings_boq.takeoff.prep import ocr_layer

VECTOR_TEXT, VECTOR_OUTLINED, VECTOR_NOLETTER, RASTER, IMAGE_PAGE, EMPTY = "VECTOR_TEXT", "VECTOR_OUTLINED", "VECTOR_NOLETTER", "RASTER", "IMAGE_PAGE", "EMPTY"
TYPES = (VECTOR_TEXT, VECTOR_OUTLINED, VECTOR_NOLETTER, RASTER, IMAGE_PAGE, EMPTY)

ENABLED = os.environ.get("TRACE_OUTLINED_OCR", "1") != "0"
OCR_BUDGET_S = float(os.environ.get("TRACE_OUTLINED_OCR_BUDGET_S", "75"))
GLYPH_MIN_W_PT, GLYPH_MAX_W_PT = 0.8, 14.0
GLYPH_MIN_H_PT, GLYPH_MAX_H_PT = 3.0, 14.0
ROW_STEP_PT = 2.0
RUN_MIN = 5
SUSPECT_GLYPHS = 200
SUSPECT_RUN = 150
GLYPHS_PER_CHAR = 1.0
MIN_NEW_WORDS = 8
MAX_OVERLAP = 0.3
CELL_PT = 60.0
EMPTY_MAX_WORDS = 2
EMPTY_MAX_DRAWN = 20

def glyph_signal(rings: list) -> dict:
  rows: dict = {}

  total = 0
  for r in rings:
    if not r.fill:
      continue
    w, h = r.bbox[2] - r.bbox[0], r.bbox[3] - r.bbox[1]
    if w < GLYPH_MIN_W_PT or w > GLYPH_MAX_W_PT or h < GLYPH_MIN_H_PT or h > GLYPH_MAX_H_PT:
      continue
    total += 1
    k = round(r.bbox[1] / ROW_STEP_PT)
    rows[k] = rows.get(k, 0) + 1
  return {"glyphs": total, "run": sum(v for v in rows.values() if v >= RUN_MIN)}

def outlined_signal(rings: list, stats: dict) -> dict | None:
  sig = glyph_signal(rings)
  chars = int(stats.get("text_chars", 0) or 0)
  if sig["glyphs"] >= SUSPECT_GLYPHS and sig["run"] >= SUSPECT_RUN and sig["glyphs"] >= GLYPHS_PER_CHAR * chars:
    return sig
  return None

def image_cover(images: list, cropbox: tuple) -> float:
  l, b, r, t = cropbox
  area = max((r - l) * (t - b), 1.0)
  cover = 0.0
  for im in images:
    x0, y0, x1, y1 = im["bbox"]
    cover += max(0.0, min(x1, r) - max(x0, l)) * max(0.0, min(y1, t) - max(y0, b))
  return cover / area

def _cells(w) -> list:
  c0, c1 = int(math.floor(w.x0 / CELL_PT)), int(math.floor(w.x1 / CELL_PT))
  r0, r1 = int(math.floor(w.y0 / CELL_PT)), int(math.floor(w.y1 / CELL_PT))
  return [(c, r) for c in range(c0, c1 + 1) for r in range(r0, r1 + 1)]

def new_words(found: list, native: list) -> list:
  grid: dict = {}
  for n in native:
    for key in _cells(n):
      grid.setdefault(key, []).append(n)
  fresh: list = []
  for w in found:
    if not any(ch.isalnum() for ch in w.text):
      continue
    area = max((w.x1 - w.x0) * (w.y1 - w.y0), 1e-6)

    covered = False
    for key in _cells(w):
      for n in grid.get(key, ()):
        ix, iy = min(w.x1, n.x1) - max(w.x0, n.x0), min(w.y1, n.y1) - max(w.y0, n.y0)
        if ix > 0 and iy > 0 and ix * iy / area > MAX_OVERLAP:
          covered = True
          break
      if covered:
        break
    if not covered:
      fresh.append(w)
  return fresh

def route(page, out, crop: tuple, stats: dict, budget_s: float, scanned: bool) -> None:
  cover = image_cover(out.images, crop)
  info: dict = {"image_cover": round(cover, 2)}
  suspect = None if scanned else outlined_signal(out.rings, stats)
  bare = None
  if not scanned and not suspect and cover < ocr_layer.MIN_COVER and len(out.words) <= EMPTY_MAX_WORDS and len(out.segs) // 5 >= SUSPECT_GLYPHS:
    bare = {"drawn_segments": len(out.segs) // 5}
  added = 0
  error = None

  if suspect or bare:
    info.update(suspect or bare)
    if not ENABLED:
      error = "DISABLED"
    elif not ocr_layer.available():
      error = "UNAVAILABLE"
    else:
      found, oi = ocr_layer.read_page(page, out.rotation, crop, [], budget_s=min(OCR_BUDGET_S, max(15.0, budget_s)))
      error = oi.get("ocr_error")
      fresh = new_words(found, out.words) if found else []
      if len(fresh) >= MIN_NEW_WORDS:
        out.words = list(out.words) + fresh
        added = len(fresh)
        info.update(ocr_words_added=added, ocr_mean_conf=oi.get("ocr_mean_conf"), ocr_elapsed_s=oi.get("ocr_elapsed_s"))
        if oi.get("ocr_partial"):
          info["ocr_partial"] = True
      else:
        info["outlined_checked"] = True

  if scanned:
    kind = RASTER
  elif suspect and added:
    kind = VECTOR_OUTLINED
    info["text_recovered"] = True
  elif bare and added:
    kind = VECTOR_OUTLINED
    info.update(text_recovered=True, lettering="STROKES")
  elif suspect and error:
    kind = VECTOR_OUTLINED
    info.update(text_recovered=False, ocr_error=error)
  elif cover >= ocr_layer.MIN_COVER:
    kind = IMAGE_PAGE
  elif len(out.words) <= EMPTY_MAX_WORDS and not out.rings and len(out.segs) // 5 < EMPTY_MAX_DRAWN:
    kind = EMPTY
  elif len(out.words) <= EMPTY_MAX_WORDS and len(out.segs) // 5 >= SUSPECT_GLYPHS:
    kind = VECTOR_NOLETTER
    info.update(text_recovered=False, drawn_segments=len(out.segs) // 5)
    if error:
      info["ocr_error"] = error
  else:
    kind = VECTOR_TEXT
  stats["pdf_type"] = {"type": kind, **info}
