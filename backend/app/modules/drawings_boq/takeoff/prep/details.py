from __future__ import annotations
import re
import math
import shutil
import os
import subprocess
from collections import Counter
import tempfile
import time
from app.modules.drawings_boq.takeoff.prep.texts import build_lines, to_visual
from PIL import Image

COLUMN_CAPTION = re.compile(r"^\s*(?:(?P<m1>[A-Z]{1,3}\s*-?\s*\d{1,2})\s+COLUMN(?:\s+DETAILS?)?|COLUMN\s+(?:DETAILS?\s+)?(?P<m2>[A-Z]{1,3}\s*-?\s*\d{1,2}))\s*$", re.I)
LABEL = re.compile(r"^(\d{1,2}(?:\.\d)?)\s*[\"”″'’′]{1,2}$")
INCH_MIN, INCH_MAX = 8.0, 48.0
BOX_MIN_PT, BOX_MAX_PT = 8.0, 90.0
SEARCH_REACH_PT = 130.0
STRIP_DEPTH_PT = 15.0
RENDER_SCALES = (8, 11)
MIN_AGREE = 2
EARLY_STOP_VOTES = 3
SQUARE_TOL = 0.06
OCR_BUDGET_S = 20.0

def norm_mark(text: str) -> str:
  """C-2, C 2 and c2 are the same mark."""
  return re.sub(r"[\s\-]", "", text or "").upper()

def find_captions(words: list) -> list[dict]:
  out = []
  for ln in build_lines(words):
    m = COLUMN_CAPTION.match(ln.text)
    if not m:
      continue
    ws = [w for _, _, w in ln.spans]
    out.append({"mark": norm_mark(m.group("m1") or m.group("m2")), "text": ln.text.strip(),
                "x": sum(w.cx for w in ws) / len(ws), "y": sum(w.cy for w in ws) / len(ws)})
  return out

def find_box(segs: list, x: float, y: float, vis) -> dict | None:
  """The drawn outline nearest above (on the page as read) the caption at (x, y): four straight segments forming a rectangle."""
  hs, vs = [], []
  
  for x1, y1, x2, y2, kind in segs:
    if kind:
      continue
    if abs(y1 - y2) < 0.05 and abs(x1 - x2) > 6.0:
      hs.append((min(x1, x2), max(x1, x2), y1))
    elif abs(x1 - x2) < 0.05 and abs(y1 - y2) > 6.0:
      vs.append((x1, min(y1, y2), max(y1, y2)))
  vx, vy = vis(x, y)
  best, best_d = None, None
  tol = 0.5
  
  for i, (xa, a0, a1) in enumerate(vs):
    for xb, b0, b1 in vs[i + 1:]:
      gap = abs(xb - xa)
      if gap < BOX_MIN_PT or gap > BOX_MAX_PT or abs(a0 - b0) > tol or abs(a1 - b1) > tol:
        continue
      lo, hi = min(xa, xb), max(xa, xb)
      h = a1 - a0
      if h < BOX_MIN_PT or h > BOX_MAX_PT:
        continue
      if not (_covers(hs, a0, lo, hi, tol) and _covers(hs, a1, lo, hi, tol)):
        continue
      corners = [vis(lo, a0), vis(hi, a1)]
      bx0, bx1 = sorted((corners[0][0], corners[1][0]))
      by0, by1 = sorted((corners[0][1], corners[1][1]))
      
      if by1 > vy + 4.0:
        continue
      d = math.hypot((bx0 + bx1) / 2 - vx, by1 - vy)
      if d > SEARCH_REACH_PT:
        continue
      if best_d is None or d < best_d:
        best, best_d = {"native": [lo, a0, hi, a1], "visual": [bx0, by0, bx1, by1]}, d
  return best

def _covers(hs: list, y: float, lo: float, hi: float, tol: float) -> bool:
  return any(abs(hy - y) <= tol and x0 <= lo + tol and x1 >= hi - tol for x0, x1, hy in hs)

def ocr_available() -> bool:
  """The reader needs the tesseract program and the Pillow and numpy packages."""
  if shutil.which("tesseract") is None:
    return False
  try:
    import numpy  
    import PIL  
  except ImportError:
    return False
  return True

def _tess(img, psm: str) -> str:
  from PIL import ImageOps
  img = ImageOps.expand(img, border=24, fill=255)
  fd, path = tempfile.mkstemp(suffix=".png")
  
  try:
    with os.fdopen(fd, "wb") as fh:
      img.save(fh, format="PNG")
    out = subprocess.run(["tesseract", path, "-", "--psm", psm, "-c", "tessedit_char_whitelist=0123456789\"'.-"],
      capture_output=True, text=True, timeout=8).stdout
  except Exception:
    return ""
  finally:
    try:
      os.remove(path)
    except OSError:
      pass
  return re.sub(r"\s+", "", out)

def _runs(flags, gap: int) -> list[tuple]:
  """Stretches of True values, joined across gaps of up to `gap`."""
  out = []
  start = last = None
  for i, f in enumerate(flags):
    if not f:
      continue
    if start is None:
      start = last = i
    elif i - last <= gap + 1:
      last = i
    else:
      out.append((start, last))
      start = last = i
  if start is not None:
    out.append((start, last))
  return out

def _clean(img, vertical: bool, far_start: bool):
  """The label alone: erase the long straight lines (the dimension line, extension lines), keep the band of ink farthest from the box (the
  label sits outside its dimension line; leader texts sit between the line and the box), and drop stray pieces such as tick marks."""
  import numpy as np
  a = np.array(img.convert("L")) < 150
  h, w = a.shape
  if h < 8 or w < 8:
    return None
  for _ in range(2):
    rows = np.where(a.sum(1) > 0.55 * w)[0]
    cols = np.where(a.sum(0) > 0.55 * h)[0]
    for d in (-2, -1, 0, 1, 2):
      a[np.clip(rows + d, 0, h - 1), :] = False
      a[:, np.clip(cols + d, 0, w - 1)] = False
  across = a.any(axis=0) if vertical else a.any(axis=1)
  bands = [r for r in _runs(across, 4) if r[1] - r[0] >= 8]
  
  if not bands:
    return None
  lo, hi = bands[0] if far_start else bands[-1]
  a = a[:, lo:hi + 1] if vertical else a[lo:hi + 1, :]
  along = a.any(axis=1) if vertical else a.any(axis=0)
  thick = hi - lo + 1
  pieces = _runs(along, max(4, int(0.7 * thick)))
  if not pieces:
    return None
  s, e = max(pieces, key=lambda r: int(a[r[0]:r[1] + 1, :].sum() if vertical else a[:, r[0]:r[1] + 1].sum()))
  a = a[s:e + 1, :] if vertical else a[:, s:e + 1]
  ys, xs = np.where(a)
  if len(ys) < 30:
    return None
  return Image.fromarray((~a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]).astype("uint8") * 255)

def parse_label(text: str) -> float | None:
  m = LABEL.match(text or "")
  if not m:
    return None
  v = float(m.group(1))
  return v if INCH_MIN <= v <= INCH_MAX else None

def _read_strip(img, vertical: bool, far_start: bool) -> list[str]:
  """What the reader makes of one strip. A vertical label reads from the bottom up, so it is turned clockwise; the other way is tried only
  when that finds nothing."""
  c = _clean(img, vertical, far_start)
  if c is None:
    return []
  found = []
  for rot in ((-90, 90) if vertical else (0,)):
    im = c.rotate(rot, expand=True, fillcolor=255) if rot else c
    for psm in ("7", "8"):
      t = _tess(im, psm)
      if t:
        found.append(t)
    if found:
      break
  return found

def _pick(c: Counter, min_votes: int = MIN_AGREE):
  """The value the readings agree on: at least `min_votes` of them and a lead of two over the next value, so a misread that turns up twice does
  not win against the right reading. Only readings that carry the inch mark are counted (a bare 8 is too often a 9)."""
  if not c:
    return None, 0
  top = c.most_common(2)
  n = top[0][1]
  rival = top[1][1] if len(top) > 1 else 0
  return (top[0][0], n) if n >= min_votes and n - rival >= 2 else (None, n)

READ_HEIGHTS_PX = (60, 40)     

def _variants(strip, vertical: bool, far_start: bool):
  """Readings of one strip, most useful first: the label at each height, plain and with thicker strokes."""
  from PIL import ImageFilter
  c = _clean(strip, vertical, far_start)
  if c is None:
    return
  for thick, psm, h in ((False, "7", READ_HEIGHTS_PX[0]), (False, "7", READ_HEIGHTS_PX[1]), (True, "7", READ_HEIGHTS_PX[0]), (True, "7", READ_HEIGHTS_PX[1]),
      (False, "8", READ_HEIGHTS_PX[0]), (False, "8", READ_HEIGHTS_PX[1])):
    im = c.filter(ImageFilter.MinFilter(3)) if thick else c
    k = h / max(im.height, 1)
    im = im.resize((max(1, int(im.width * k)), h))
    for rot in ((-90, 90) if vertical else (0,)):
      yield rot, psm, (im.rotate(rot, expand=True, fillcolor=255) if rot else im)

def read_box_labels(page, box_vis: list, page_wh: tuple, deadline: float) -> dict:
  """The two dimensions written beside a detail box, in inches: {w_in, h_in, w_votes, h_votes, raw}. A value needs MIN_AGREE agreeing readings
  and a clear margin; the sides are read in turn and reading stops as soon as the horizontal and the vertical label are both settled."""
  Wv, Hv = page_wh
  x0, y0, x1, y1 = box_vis
  depth_pt = max(STRIP_DEPTH_PT, 0.8 * max(x1 - x0, y1 - y0))      
  pad = depth_pt + 4.0
  wx0, wy0, wx1, wy1 = max(0.0, x0 - pad), max(0.0, y0 - pad), min(Wv, x1 + pad), min(Hv, y1 + pad)
  tally = {False: Counter(), True: Counter()}
  done = {False: (None, 0), True: (None, 0)}
  raw: list = []
  renders: dict = {}
  def image(sc: int):
    if sc not in renders:
      try:
        renders[sc] = page.render(scale=sc, crop=(wx0, Hv - wy1, Wv - wx1, wy0)).to_pil().convert("L")
      except Exception:
        renders[sc] = None
    return renders[sc]

  sides = ((False, True, "top"), (True, True, "left"), (False, False, "bottom"), (True, False, "right"))
  for sc in RENDER_SCALES:
    for vertical, far_start, side in sides:
      if done[vertical][0] is not None or time.monotonic() > deadline:
        continue
      img = image(sc)
      if img is None:
        continue
      bx0, by0, bx1, by1 = (x0 - wx0) * sc, (y0 - wy0) * sc, (x1 - wx0) * sc, (y1 - wy0) * sc
      d = depth_pt * sc
      tw, th = 0.15 * (bx1 - bx0), 0.15 * (by1 - by0)
      box = {"top": (bx0 + tw, by0 - d, bx1 - tw, by0 - 1), "bottom": (bx0 + tw, by1 + 1, bx1 - tw, by1 + d),
             "left": (bx0 - d, by0 + th, bx0 - 1, by1 - th), "right": (bx1 + 1, by0 + th, bx1 + d, by1 - th)}[side]
      l, t, r, b = max(0, int(box[0])), max(0, int(box[1])), min(img.width, int(box[2])), min(img.height, int(box[3]))
      if r - l < 12 or b - t < 12:
        continue
      strong = tally[vertical]
      got_any = False
      
      for rot, psm, im in _variants(img.crop((l, t, r, b)), vertical, far_start):
        if got_any and rot != (-90 if vertical else 0):
          continue
        text = _tess(im, psm)
        if not text:
          continue
        got_any = True
        raw.append(text)
        v = parse_label(text)
        if v is not None:
          strong[v] += 1
        if _pick(strong, EARLY_STOP_VOTES)[0] is not None:
          break
      done[vertical] = _pick(strong)
  return {"w_in": done[False][0], "h_in": done[True][0], "w_votes": done[False][1], "h_votes": done[True][1], "raw": raw[:16]}

def read_column_details(words: list, index, page, page_wh: tuple, crop: tuple, rotation: int, use_ocr: bool = True, budget_s: float = OCR_BUDGET_S) -> dict:
  """Every column detail on the sheet: its mark, where it is drawn and, if the reader is available, the size written beside it."""
  caps = find_captions(words)
  ocr = bool(use_ocr and ocr_available())
  Wv, Hv = page_wh
  def vis(px, py):
    u, v = to_visual(px, py, crop, rotation)
    return u * Wv, v * Hv
  deadline = time.monotonic() + budget_s
  out = []
  
  for c in caps:
    segs, _, _ = index.window(c["x"] - SEARCH_REACH_PT, c["y"] - SEARCH_REACH_PT, c["x"] + SEARCH_REACH_PT, c["y"] + SEARCH_REACH_PT)
    box = find_box(segs, c["x"], c["y"], vis)
    rec = {"mark": c["mark"], "caption": c["text"], "x": round(c["x"], 1), "y": round(c["y"], 1),
           "box": box["native"] if box else None, "w_in": None, "h_in": None, "read": "NONE"}
    
    if box and ocr:
      got = read_box_labels(page, box["visual"], page_wh, deadline)
      rec.update(w_in=got["w_in"], h_in=got["h_in"], w_votes=got["w_votes"], h_votes=got["h_votes"], raw=got["raw"])
      bw, bh = box["visual"][2] - box["visual"][0], box["visual"][3] - box["visual"][1]
      if got["w_in"] and got["h_in"]:
        rec["read"] = "OCR"
      elif (got["w_in"] or got["h_in"]) and abs(bw - bh) <= SQUARE_TOL * max(bw, bh):
        rec["w_in"] = rec["h_in"] = got["w_in"] or got["h_in"]
        rec["read"] = "OCR_SQUARE"
      elif got["w_in"] or got["h_in"]:
        rec["read"] = "PARTIAL"
    out.append(rec)
  return {"ocr": "OK" if ocr else "UNAVAILABLE", "details": out}
