from __future__ import annotations
import collections
import functools
import math
import os
import re
import time
import yaml
from app.modules.drawings_boq.takeoff.prep import ocr_layer, text_repair as TR, words as WD

LETTERING_STROKES = "LETTERING_STROKES"
SINGLE = ("I", "1", "l", "|")

VOCABULARY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stroke_vocabulary.yaml")

def _s(name: str) -> float:
  return WD.setting(name)

@functools.lru_cache(maxsize=1)
def caption_words() -> frozenset:
  with open(VOCABULARY, encoding="utf-8") as fh:
    return frozenset(str(w).upper() for w in (yaml.safe_load(fh) or {}).get("caption_words") or [])

def text_height(words: list) -> float:
  hs = sorted(w.height for w in words if getattr(w, "height", 0) > 0)
  return hs[len(hs) // 2] if hs else 0.0

def components(segs, h: float) -> list:
  n = len(segs) // 5
  longest, eps = _s("stroke_short_h") * h, _s("stroke_join_h") * h
  short = []
  for i in range(n):
    x0, y0, x1, y1 = segs[5 * i], segs[5 * i + 1], segs[5 * i + 2], segs[5 * i + 3]
    if math.hypot(x1 - x0, y1 - y0) <= longest:
      short.append((x0, y0, x1, y1))
  if len(short) > _s("stroke_max_short"):
    return []
  parent = list(range(len(short)))

  def find(i: int) -> int:
    while parent[i] != i:
      parent[i] = parent[parent[i]]
      i = parent[i]
    return i
  cell = eps * 2
  
  grid: dict = collections.defaultdict(list)
  for i, g in enumerate(short):
    for x, y in ((g[0], g[1]), (g[2], g[3])):
      grid[(int(x // cell), int(y // cell))].append((i, x, y))
  for i, g in enumerate(short):
    for x, y in ((g[0], g[1]), (g[2], g[3])):
      cx, cy = int(x // cell), int(y // cell)
      for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
          for j, x2, y2 in grid.get((cx + dx, cy + dy), ()):
            if j != i and abs(x - x2) <= eps and abs(y - y2) <= eps:
              parent[find(i)] = find(j)
              
  groups: dict = collections.defaultdict(list)
  for i, g in enumerate(short):
    groups[find(i)].append(g)
  boxes = []
  for v in groups.values():
    boxes.append([min(min(g[0], g[2]) for g in v), min(min(g[1], g[3]) for g in v), max(max(g[0], g[2]) for g in v), max(max(g[1], g[3]) for g in v), len(v), list(v)])
  return _touching(boxes, _s("stroke_touch_h") * h, h)

def _touching(boxes: list, gap: float, h: float) -> list:
  parent = list(range(len(boxes)))

  def find(i: int) -> int:
    while parent[i] != i:
      parent[i] = parent[parent[i]]
      i = parent[i]
    return i
  cell = max(h, 1e-6)
  
  grid: dict = collections.defaultdict(list)
  for i, b in enumerate(boxes):
    for cx in range(int((b[0] - gap) // cell), int((b[2] + gap) // cell) + 1):
      for cy in range(int((b[1] - gap) // cell), int((b[3] + gap) // cell) + 1):
        grid[(cx, cy)].append(i)
  for members in grid.values():
    for a in range(len(members)):
      for c in range(a + 1, len(members)):
        i, j = members[a], members[c]
        bi, bj = boxes[i], boxes[j]
        if bi[0] - gap <= bj[2] and bj[0] - gap <= bi[2] and bi[1] - gap <= bj[3] and bj[1] - gap <= bi[3]:
          parent[find(i)] = find(j)
          
  merged: dict = {}
  for i, b in enumerate(boxes):
    r = merged.setdefault(find(i), [b[0], b[1], b[2], b[3], 0, []])
    r[0], r[1], r[2], r[3] = min(r[0], b[0]), min(r[1], b[1]), max(r[2], b[2]), max(r[3], b[3])
    r[4] += b[4]
    r[5].extend(b[5])
  return [tuple(v) for v in merged.values()]

def letters(boxes: list, h: float) -> list:
  lo, hi = _s("stroke_letter_min_h") * h, _s("stroke_letter_max_h") * h
  out = []
  for b in boxes:
    w, t = b[2] - b[0], b[3] - b[1]
    if lo <= max(w, t) <= hi and (b[4] >= 2 or (t >= 0.7 * h and w <= 0.3 * h)):
      out.append(b)
  return out

def lines_of(found: list, h: float, axis: int = 0) -> list:
  other = 1 - axis
  gap, reach = _s("stroke_letter_gap_h") * h, _s("stroke_line_gap_h") * h
  order = sorted(found, key=lambda b: (round((b[other] + b[other + 2]) / 2 / (0.5 * h)), b[axis]))
  runs: list = []
  for b in order:
    mid = (b[other] + b[other + 2]) / 2
    for r in runs:
      last = r[-1]
      if abs(mid - (last[other] + last[other + 2]) / 2) <= 0.35 * h and -0.3 * h <= b[axis] - last[axis + 2] <= reach:
        r.append(b)
        break
    else:
      runs.append([b])
      
  out = []
  for r in runs:
    if len(r) < _s("stroke_min_letters"):
      continue
    sizes = [x[other + 2] - x[other] for x in r if x[4] >= 2]
    if sizes and (max(sizes) - min(sizes)) > _s("stroke_height_spread") * max(sizes) + 0.2 * h:
      continue
    box = (min(x[0] for x in r), min(x[1] for x in r), max(x[2] for x in r), max(x[3] for x in r))
    out.append({"box": box, "n": len(r), "axis": axis, "strokes": [g for x in r for g in x[5]]})
  return out

def _covered(box: tuple, words: list) -> bool:
  x0, y0, x1, y1 = box
  area = max((x1 - x0) * (y1 - y0), 1e-9)
  hit = 0.0
  for w in words:
    ix, iy = min(x1, w.x1) - max(x0, w.x0), min(y1, w.y1) - max(y0, w.y0)
    if ix > 0 and iy > 0:
      hit += ix * iy
  return hit > 0.5 * area

def text_axis(words: list) -> int:
  along_y = sum(1 for w in words if round(float(getattr(w, "angle", 0.0)) / 90.0) % 2 == 1)
  return 1 if along_y * 2 > len(words) else 0

def evidence(segs, words: list) -> dict | None:
  h = text_height(words)
  if h <= 0 or len(segs) < 5 * 20:
    return None
  found = letters(components(segs, h), h)
  if len(found) < _s("stroke_min_letters"):
    return None
  lines = [ln for ln in lines_of(found, h, text_axis(words)) if not _covered(ln["box"], words)]
  if not lines:
    return None
  lines.sort(key=lambda ln: (-ln["n"], ln["box"][1], ln["box"][0]))
  cap = int(_s("stroke_max_lines"))
  return {"regions": [ln["box"] for ln in lines[:cap]], "n": [ln["n"] for ln in lines[:cap]], "strokes": [ln["strokes"] for ln in lines[:cap]], "left_out": max(0, len(lines) - cap), "text_h": round(h, 2)}

CAPTION_FIX = {"S": "5", "O": "0", "I": "1", "l": "1", "i": "1", "|": "1", "Z": "2", "B": "8"}

def caption_mark(text: str) -> str:
  t = text.strip()
  if len(t) < 2 or not t[0].isalpha():
    return text
  fixed = t[0].upper() + "".join(CAPTION_FIX.get(ch, ch) if not ch.isdigit() else ch for ch in t[1:])
  return fixed if fixed[1:].isdigit() else text

MARK_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
MARK_SHAPE = re.compile(r"^[A-Z]{1,2}\d{1,2}$")
MARK_READS = (("7", 1), ("7", 2), ("8", 2))

def reread_mark(img, row: dict, timeout: float) -> dict:
  from PIL import Image
  pad = 6
  crop = img.crop((max(0, row["l"] - pad), max(0, row["t"] - pad), row["l"] + row["w"] + pad, row["t"] + row["h"] + pad))
  best = None
  for psm, k in MARK_READS:
    big = crop.resize((crop.width * k, crop.height * k), Image.LANCZOS) if k > 1 else crop
    for r in ocr_layer._tsv(big, max(5.0, timeout), psm, MARK_ALPHABET):
      if MARK_SHAPE.match(r["text"].strip().upper()) and (best is None or r["conf"] > best["conf"]):
        best = {**row, "text": r["text"].strip().upper(), "conf": r["conf"]}
  return best if best is not None and best["conf"] >= row["conf"] - 5 or (best is not None and not MARK_SHAPE.match(row["text"].strip().upper())) else row

def keep(row: dict, vocabulary: set | None = None) -> bool:
  from app.engine.measure import steel_grammar as SG
  t = row["text"].strip()
  if row["conf"] < _s("stroke_keep_confidence") or not any(ch.isalnum() for ch in t) or not t.isascii():
    return False
  if len(t) >= 3 and all(ch in SINGLE for ch in t):
    return False
  if WD.parses(t, vocabulary) in ("MARK", "DIMENSION"):
    return True
  g = SG.parse_callout(t)
  if g["bars"] or g["spaced"]:
    return True
  word = t.strip(".,:;")
  return len(word) >= 2 and word.isalpha() and (word.isupper() or word.lower() in (vocabulary or ()))

def draw(strokes: list, box: tuple, rotation: int, cropbox: tuple, h: float):
  from PIL import Image, ImageDraw
  from app.modules.drawings_boq.takeoff.prep import outlined_text as OT
  scale = _s("stroke_dpi") / 72.0
  m = _s("stroke_margin_pt")
  vx0, vy0, vx1, vy1 = OT._view_box(box, rotation, cropbox)
  vx0, vy0, vx1, vy1 = vx0 - m, vy0 - m, vx1 + m, vy1 + m
  img = Image.new("L", (max(4, int((vx1 - vx0) * scale)), max(4, int((vy1 - vy0) * scale))), 255)
  pen = ImageDraw.Draw(img)
  
  width = max(2, int(round(_s("stroke_pen_h") * h * scale)))
  for x0, y0, x1, y1 in strokes:
    a = OT._user_to_view(x0, y0, rotation, cropbox)
    b = OT._user_to_view(x1, y1, rotation, cropbox)
    pen.line([((a[0] - vx0) * scale, (a[1] - vy0) * scale), ((b[0] - vx0) * scale, (b[1] - vy0) * scale)], fill=0, width=width)
  return img, (vx0, vy0, scale)

def read_lines(rotation: int, cropbox: tuple, regions: list, strokes: list, h: float, budget_s: float) -> tuple:
  info: dict = {"lines": len(regions)}
  if not ocr_layer.available():
    info["error"] = "UNAVAILABLE"
    return [], info
  started = time.monotonic()
  out = []
  
  vocabulary = TR.words()
  for i, box in enumerate(regions):
    if time.monotonic() - started > budget_s:
      info["partial"] = True
      info["not_read"] = {"reason": WD.OCR_BUDGET, "regions_left": len(regions) - i}
      break
    img, (vx0, vy0, scale) = draw(strokes[i], box, rotation, cropbox, h)
    rows = sorted(ocr_layer._tsv(img, max(5.0, budget_s - (time.monotonic() - started)), "7"), key=lambda r: r["l"])
    if not any(r["text"].upper().strip(".:,") in caption_words() for r in rows):
      info["lines_left"] = info.get("lines_left", 0) + 1
      continue
    
    for k, r in enumerate(rows):
      if k and rows[k - 1]["text"].upper().strip(".:") == "BEAM":
        r = rows[k] = reread_mark(img, r, budget_s - (time.monotonic() - started))
        r["text"] = caption_mark(r["text"])
      if not keep(r, vocabulary):
        continue
      a0, b0 = vx0 + r["l"] / scale, vy0 + r["t"] / scale
      w = ocr_layer._build_word(r["text"].strip(), a0, b0, a0 + r["w"] / scale, b0 + r["h"] / scale, 0.0, rotation, cropbox, WD.OUTLINED_OCR, r["conf"])
      w.repair = LETTERING_STROKES
      out.append(w)
  info.update(words=len(out), seconds=round(time.monotonic() - started, 2))
  return out, info
