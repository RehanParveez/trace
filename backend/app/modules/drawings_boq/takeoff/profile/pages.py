from __future__ import annotations
import ctypes
import re
from types import SimpleNamespace
import pypdfium2.raw as raw
from app.modules.drawings_boq.takeoff.prep import title_strip as TS

FT_IN = re.compile(r"\d+\s*['′]\s*-?\s*\d*\s*(?:\d/\d)?\s*[\"″”]?|\d+\s*[\"″”]\s*[xX]")
FT_IN_STRICT = re.compile(r"\d+\s*['′]\s*-\s*\d+(?:\s*\d/\d)?\s*[\"″”]?")
MM_TOKEN = re.compile(r"\b\d{2,5}\s*mm\b|\bmm\b", re.I)
MM_NOTE = re.compile(r"ALL\s+DIMENSIONS?\s+(?:ARE\s+)?IN\s+(MM|MILLIMET|FEET|FT|INCH)", re.I)
BAR_HASH = re.compile(r"(?<![A-Za-z0-9])#\s?\d{1,2}(?!\d)")
BAR_MM = re.compile(r"(?:[Øφø⌀]\s*\d{1,2}\s*(?:mm)?|\b\d{1,2}\s*mm\s*(?:dia|[Øφ]|bars?)|\b(?:dia\.?|bars?)\s*\d{1,2}\s*mm)", re.I)
BAR_T = re.compile(r"\b[TY]\d{2}\b|\b\d{1,2}\s*[TY]\s?\d{2}\b")
SECTION_FORMS = (
  ("LETTER_PAIR", re.compile(r"\bSECTION\s*[\"']?\s*[A-Z]\s*[-–]\s*[A-Z]\b|\bSEC\.?\s*[A-Z]\s*[-–]\s*[A-Z]\b", re.I)),
  ("NUMBER_PAIR", re.compile(r"\bSECTION\s*\d\s*[-–]\s*\d\b|\bSEC\.?\s*\d\s*[-–]\s*\d\b", re.I)),
  ("X_SECTION", re.compile(r"\bX\s*-?\s*SECTIONS?\b|\bCROSS\s+SECTION", re.I)),
  ("DETAIL_NUMBER", re.compile(r"\bDETAIL\s*[-:]?\s*\d{1,2}\b|\bDETAIL\s*[-:]?\s*[A-Z]\b", re.I)),
)
LEGEND = re.compile(r"\bLEGENDS?\b|\bSYMBOLS?\s+(?:LIST|LEGEND)\b|\bKEY\s+PLAN\b", re.I)
HEADER_WORDS = re.compile(r"^(?:SIZE|BARS?|REINF\w*|STIRRUPS?|TIES|MAIN|DIA\w*|MARK|TOP|BOTTOM|COLUMN|COLUMNS|BEAM|FOOTING|SCHEDULE|CORNER|MID)$", re.I)
MARK = re.compile(r"^(?:C|B|F|S|RB|FB|PC|CB|SB|LB|SF|W|D|T|G)-?\d{1,2}[A-Z]?$")
LABEL_WORDS = re.compile(r"^(?:CLIENT|PROJECT|CONSULTANT|DRAWN|CHECKED|DATE|SCALE|TITLE|DRAWING|SHEET|REV|REVISION|ARCHITECT|DESIGNED|APPROVED|SIGNATURE)\b", re.I)
SCALE_TEXT = re.compile(r"^(?:SCALE\s*[:\-]?\s*)?(?:\d\s*:\s*\d{2,4}|\d+(?:\s*/\s*\d+)?\s*[\"\u201d]\s*=\s*\d+\s*['\u2032](?:\s*-?\s*\d+\s*[\"\u201d]?)?)$", re.I)
WORD_CAP = 9000
PHRASE_CAP = 4000
ROW_TOL = 0.6
COL_TOL = 0.5
MIN_MARKS = 4
MIN_PATHS_FOR_PLAN = 800
WALL_MIN_LEN_MM = 14.0
WALL_MIN_ASPECT = 3.0
HATCH_MIN_MM, HATCH_MAX_MM = 1.0, 21.0
PT_MM = 25.4 / 72.0
DARK = 90

def _seen(box: tuple, rotation: int, w: float, h: float) -> tuple:
  q = (rotation // 90) % 4
  x0, y0, x1, y1 = box
  if q == 1:
    return (y0, w - x1, y1, w - x0)
  if q == 2:
    return (w - x1, h - y1, w - x0, h - y0)
  if q == 3:
    return (h - y1, x0, h - y0, x1)
  return (x0, y0, x1, y1)

def _words(tp, text: str, rotation: int, w: float, h: float) -> list:
  out = []
  
  n = tp.count_chars()
  for m in re.finditer(r"\S+", text):
    a, b = m.start(), min(m.end(), n)
    if a >= n:
      break
    boxes = [_seen(tp.get_charbox(i), rotation, w, h) for i in range(a, b)]
    if not boxes:
      continue
    
    out.append(SimpleNamespace(text=m.group(0), x0=min(x[0] for x in boxes), y0=min(x[1] for x in boxes), x1=max(x[2] for x in boxes), y1=max(x[3] for x in boxes), angle=0.0, cx=0.0, cy=0.0))
    if len(out) >= WORD_CAP:
      break
  for w in out:
    w.cx, w.cy = (w.x0 + w.x1) / 2.0, (w.y0 + w.y1) / 2.0
  return out

def _fill_rgb(obj) -> tuple:
  r, g, b, a = (ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint())
  ok = raw.FPDFPageObj_GetFillColor(obj.raw, ctypes.byref(r), ctypes.byref(g), ctypes.byref(b), ctypes.byref(a))
  return (r.value, g.value, b.value) if ok else (255, 255, 255)

def _drawn(obj) -> tuple:
  fill, stroke = ctypes.c_int(), ctypes.c_int()
  raw.FPDFPath_GetDrawMode(obj.raw, ctypes.byref(fill), ctypes.byref(stroke))
  return fill.value != 0, stroke.value != 0

def path_stats(page) -> dict:
  paths = fills = hatch = 0
  for obj in page.get_objects():
    if obj.type != raw.FPDF_PAGEOBJ_PATH:
      continue
    paths += 1
    
    l, b, r, t = obj.get_bounds()
    w, h = (r - l) * PT_MM, (t - b) * PT_MM
    fill, _stroke = _drawn(obj)
    long, short = max(w, h), max(min(w, h), 0.01)
    if fill and long >= WALL_MIN_LEN_MM and long / short >= WALL_MIN_ASPECT and max(_fill_rgb(obj)) <= DARK:
      fills += 1
    elif not fill and HATCH_MIN_MM <= w <= HATCH_MAX_MM and HATCH_MIN_MM <= h <= HATCH_MAX_MM and 0.8 <= w / max(h, 0.01) <= 1.25 and raw.FPDFPath_CountSegments(obj.raw) == 2:
      hatch += 1
  return {"paths": paths, "wall_fills": fills, "hatch": hatch}

def _count(rx, text: str) -> int:
  return len(rx.findall(text))

def _schedule_marks(words: list) -> dict:
  header = sum(1 for w in words if HEADER_WORDS.match(w.text))
  marks = [w for w in words if MARK.match(w.text.upper())]
  rows = cols = 0
  best_row = best_col = []
  
  for w in marks:
    h = max(w.y1 - w.y0, 1.0)
    on_row = {m.text for m in marks if abs(m.cy - w.cy) <= ROW_TOL * h}
    on_col = {m.text for m in marks if abs(m.cx - w.cx) <= COL_TOL * h * 3.0 and abs(m.cy - w.cy) > ROW_TOL * h}
    if len(on_row) > rows:
      rows, best_row = len(on_row), sorted(on_row)
    if len(on_col) + 1 > cols:
      cols, best_col = len(on_col) + 1, sorted(on_col | {w.text})
  return {"header_words": header, "across": rows, "down": cols, "across_marks": best_row[:8], "down_marks": best_col[:8]}

def facts(page, number: int) -> dict:
  tp = page.get_textpage()
  text = tp.get_text_range()
  width, height = page.get_size()
  rotation = int(page.get_rotation() or 0)
  l, b, r, t = page.get_cropbox()
  words = _words(tp, text, rotation, r - l, t - b)
  cropbox = (0.0, 0.0, float(width), float(height))
  
  ph = TS.phrases(words) if words else []
  sections = {name: _count(rx, text) for name, rx in SECTION_FORMS}
  labels = [w for w in words if LABEL_WORDS.match(w.text)]
  zone = TS.zone_phrases(ph[:PHRASE_CAP], cropbox) if ph else []
  ratios = sum(1 for p in ph if SCALE_TEXT.match(p["text"].strip()))
  note = MM_NOTE.search(text)
  
  return {"page": number, "words": len(words), "paper_pt": [round(width, 1), round(height, 1)],
    "ft_in": _count(FT_IN_STRICT, text), "mm": _count(MM_TOKEN, text), "dimension_note": note.group(1).upper() if note else None,
    "bar_hash": _count(BAR_HASH, text), "bar_mm": _count(BAR_MM, text), "bar_t": _count(BAR_T, text),
    "sections": sections, "legend": bool(LEGEND.search(text)), "legend_text": (LEGEND.search(text).group(0)[:30] if LEGEND.search(text) else None),
    "labels_bottom": sum(1 for w in labels if w.cy <= 0.30 * height), "labels_right": sum(1 for w in labels if w.cx >= 0.70 * width), "labels": len(labels),
    "scale_ratio_tokens": ratios, "schedule": _schedule_marks(words), "paths": path_stats(page), "zone": zone}
