from __future__ import annotations
import ctypes
import os
import re
import yaml
import pypdfium2 as pdfium
import pypdfium2.raw as raw
from app.modules.drawings_boq.takeoff.prep import pdf_type as PT
from app.modules.drawings_boq.takeoff.proof.reading import match as M
from app.modules.drawings_boq.takeoff.proof.reading import vocab as V

WORDS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "words.txt")
TOKEN = re.compile(r"[A-Za-z]{3,}")
OFFSETS = [k for k in range(-64, 65) if k]
SHIFTS = range(1, 26)
MIN_FONT_TOKENS = 3
DECODE_MIN_RATE = 0.6
DECODE_MIN_GAIN = 0.3
DECODE_ONLY_BELOW = 0.5
CELL_PT = 20.0
SEG_LINE, SEG_BEZIER, SEG_MOVE = 0, 1, 2
_words: set = set()

def words() -> set:
  if not _words:
    with open(WORDS_PATH, encoding="utf-8") as fh:
      _words.update(w.strip().upper() for w in fh if w.strip())
  return _words

def tokens(text: str) -> list:
  return TOKEN.findall(text)

def pass_rate(texts: list) -> tuple:
  toks = [t for s in texts for t in tokens(s)]
  if not toks:
    return None, 0
  ok = sum(1 for t in toks if t.upper() in words())
  return round(ok / len(toks), 4), len(toks)

def _shift_letters(s: str, k: int) -> str:
  out = []
  for c in s:
    if "A" <= c <= "Z":
      out.append(chr((ord(c) - 65 + k) % 26 + 65))
    elif "a" <= c <= "z":
      out.append(chr((ord(c) - 97 + k) % 26 + 97))
    else:
      out.append(c)
  return "".join(out)

def _offset(s: str, k: int) -> str:
  return "".join(chr(ord(c) + k) if 32 <= ord(c) + k < 127 and ord(c) > 32 else c for c in s)

def decode_gain(texts: list, raw_rate) -> dict:
  base = raw_rate or 0.0
  best = {"kind": None, "value": None, "rate": base, "gain": 0.0}
  for kind, values, fn in (("offset", OFFSETS, _offset), ("shift", SHIFTS, _shift_letters)):
    for k in values:
      rate, _n = pass_rate([fn(s, k) for s in texts])
      if rate is not None and rate - base > best["gain"] + 1e-9:
        best = {"kind": kind, "value": k, "rate": rate, "gain": round(rate - base, 4)}
  return best

def _unmapped(c: str) -> bool:
  o = ord(c)
  return c == "�" or 0xE000 <= o <= 0xF8FF or (o < 32 and c not in "\t\n\r")

def _text_of(obj, tp) -> str:
  n = raw.FPDFTextObj_GetText(obj.raw, tp.raw, None, 0)
  buf = (ctypes.c_ushort * max(n, 1))()
  raw.FPDFTextObj_GetText(obj.raw, tp.raw, buf, n)
  return bytes(buf).decode("utf-16le", "replace").replace("\x00", "")

def _font_of(obj) -> str:
  buf = ctypes.create_string_buffer(256)
  raw.FPDFFont_GetBaseFontName(raw.FPDFTextObj_GetFont(obj.raw), buf, 256)
  return buf.value.decode("latin1") or "unnamed"

def _segments(obj) -> tuple:
  n = raw.FPDFPath_CountSegments(obj.raw)
  kinds = [raw.FPDFPathSegment_GetType(raw.FPDFPath_GetPathSegment(obj.raw, i)) for i in range(n)]
  rect = kinds in ([SEG_MOVE, SEG_LINE, SEG_LINE, SEG_LINE, SEG_LINE], [SEG_MOVE, SEG_LINE, SEG_LINE, SEG_LINE])
  return kinds.count(SEG_LINE), kinds.count(SEG_BEZIER), rect

def _filled(obj) -> bool:
  fill, stroke = ctypes.c_int(), ctypes.c_int()
  raw.FPDFPath_GetDrawMode(obj.raw, ctypes.byref(fill), ctypes.byref(stroke))
  return fill.value != 0

def _grid(boxes: list) -> dict:
  grid: dict = {}
  for b in boxes:
    for cx in range(int(b[0] // CELL_PT), int(b[2] // CELL_PT) + 1):
      for cy in range(int(b[1] // CELL_PT), int(b[3] // CELL_PT) + 1):
        grid.setdefault((cx, cy), []).append(b)
  return grid

def _covered(grid: dict, x: float, y: float) -> bool:
  return any(b[0] - 1 <= x <= b[2] + 1 and b[1] - 1 <= y <= b[3] + 1 for b in grid.get((int(x // CELL_PT), int(y // CELL_PT)), ()))

def profile_page(page) -> dict:
  tp = page.get_textpage()
  width, height = page.get_size()
  area = max(width * height, 1.0)
  text = tp.get_text_range()
  tokens_all = text.split()
  by_font: dict = {}
  lines = bezier = rects = filled_paths = images = paths = 0
  image_area = 0.0
  
  glyphs = []
  for obj in page.get_objects():
    if obj.type == raw.FPDF_PAGEOBJ_TEXT:
      s = _text_of(obj, tp)
      by_font.setdefault(_font_of(obj), []).append(s)
    elif obj.type == raw.FPDF_PAGEOBJ_IMAGE:
      images += 1
      l, b, r, t = obj.get_bounds()
      image_area += max(0.0, min(r, width) - max(l, 0.0)) * max(0.0, min(t, height) - max(b, 0.0))
    elif obj.type == raw.FPDF_PAGEOBJ_PATH:
      paths += 1
      n_line, n_bez, is_rect = _segments(obj)
      lines += n_line
      bezier += n_bez
      rects += 1 if is_rect else 0
      if _filled(obj):
        filled_paths += 1
        l, b, r, t = obj.get_bounds()
        if PT.GLYPH_MIN_W_PT <= r - l <= PT.GLYPH_MAX_W_PT and PT.GLYPH_MIN_H_PT <= t - b <= PT.GLYPH_MAX_H_PT:
          glyphs.append(((l + r) / 2, (b + t) / 2, b))
          
  boxes = [tp.get_charbox(i) for i in range(tp.count_chars())]
  grid = _grid([(b[0], b[1], b[2], b[3]) for b in boxes])
  loose = [g for g in glyphs if not _covered(grid, g[0], g[1])]
  rows: dict = {}
  for _x, _y, bottom in loose:
    k = round(bottom / PT.ROW_STEP_PT)
    rows[k] = rows.get(k, 0) + 1
  chars = sum(len(s) for ss in by_font.values() for s in ss)
  
  fonts = {}
  for name, ss in sorted(by_font.items()):
    n = sum(len(s) for s in ss)
    rate, ntok = pass_rate(ss)
    gain = decode_gain(ss, rate) if ntok >= MIN_FONT_TOKENS and (rate or 0.0) < DECODE_ONLY_BELOW else {"kind": None, "value": None, "rate": rate, "gain": 0.0}
    if gain["kind"] and (gain["rate"] < DECODE_MIN_RATE or gain["gain"] < DECODE_MIN_GAIN):
      gain = {"kind": None, "value": None, "rate": rate, "gain": 0.0}
    fonts[name] = {"chars": n, "share": round(n / chars, 4) if chars else 0.0, "unmapped_share": round(sum(1 for s in ss for c in s if _unmapped(c)) / n, 4) if n else 0.0,
      "tokens": ntok, "pass_rate": rate, "decode": gain}
  page_rate, page_tokens = pass_rate([s for ss in by_font.values() for s in ss])
  lines_text = text.splitlines()
  callout = sum(len(re.findall(r"\b\d-\d\b", ln)) for ln in lines_text if re.search(r"@|C/C|\bCC\b|BARS|STIRRUP|TIES", ln, re.I))
  return {"words": len(tokens_all), "chars": chars, "path_objects": paths, "line_segments": lines, "bezier_segments": bezier, "rect_paths": rects, "filled_paths": filled_paths, "image_objects": images,
    "image_share": round(min(1.0, image_area / area), 4), "fonts": fonts, "pass_rate": page_rate, "tokens": page_tokens, "loose_glyphs": len(loose), "loose_glyph_rows": sum(v for v in rows.values() if v >= PT.RUN_MIN),
    "glyph_loss": {"dash_digits_in_callout": callout, "at_spacing_two_digit_inch": len(re.findall(r"\d@\d{2}\"", text)), "digit_space_digit_inch": len(re.findall(r"\d \d\"", text))},
    "width_pt": round(width, 2), "height_pt": round(height, 2)}

def damaged_fonts(p: dict) -> list:
  r = M.rules()["profile"]
  return sorted(n for n, f in p["fonts"].items() if f["tokens"] >= r["damaged_min_tokens"] and (f["pass_rate"] or 0.0) < r["damaged_pass_rate"])

def text_type(p: dict) -> V.TextType:
  r = M.rules()["profile"]
  if p["image_share"] >= r["raster_share"] and p["words"] <= r["raster_max_words"]:
    return V.TextType.RASTER
  if p["words"] <= r["outlined_max_words"] and p["line_segments"] + p["bezier_segments"] >= r["outlined_min_segments"]:
    return V.TextType.OUTLINED
  if p["words"] > r["outlined_max_words"] and (damaged_fonts(p) or p["loose_glyph_rows"] >= r["partial_loose_rows"]):
    return V.TextType.PARTIAL
  if p["image_share"] >= r["mixed_image_share"]:
    return V.TextType.MIXED
  return V.TextType.TEXT

def profile_pdf(path: str) -> dict:
  doc = pdfium.PdfDocument(path)
  try:
    meta = doc.get_metadata_dict()
    pages = []
    for i in range(len(doc)):
      page = doc[i]
      try:
        p = profile_page(page)
      finally:
        page.close()
      p["sheet"] = i + 1
      p["text_type"] = text_type(p).value
      pages.append(p)
    return {"producer": meta.get("Producer") or meta.get("Creator") or None, "pages": pages}
  finally:
    doc.close()

def draft_rows(profile: dict, registers: dict, date: str) -> list:
  rows = []
  for p in profile["pages"]:
    reg = registers.get(p["sheet"]) or {}
    row = {"sheet": p["sheet"]}
    for name in ("sheet_no", "title", "role", "plan_kind", "floor", "discipline", "scale_ratio", "scale_basis"):
      if reg.get(name) is not None:
        row[name] = reg[name]
    row["role"] = row.get("role") or "UNKNOWN"
    row["text_type"] = p["text_type"]
    row["truth"] = {"by": "draft", "checked": False, "source": "trace_identity_and_profile", "date": date}
    rows.append(row)
  return rows

def write_register(folder: str, rows: list) -> None:
  with open(os.path.join(folder, "register.yaml"), "w", encoding="utf-8", newline="\n") as fh:
    yaml.safe_dump(rows, fh, sort_keys=False, width=200, allow_unicode=True)
