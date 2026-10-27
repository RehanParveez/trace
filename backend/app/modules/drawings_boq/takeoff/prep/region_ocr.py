from __future__ import annotations
import time
from app.modules.drawings_boq.takeoff.prep import ocr_layer

DPI = 300.0
MAX_SIDE_PX = 9000
MIN_CONF = 50.0
MIN_CONF_SHORT = 70.0
MIN_H_PX = 5
BUDGET_S = 25.0

def view_box(box: tuple, rotation: int, cropbox: tuple) -> tuple:
  x0, y0, x1, y1 = box
  corners = [_user_to_view(ux, uy, rotation, cropbox) for ux, uy in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
  xs = [c[0] for c in corners]
  ys = [c[1] for c in corners]
  return min(xs), min(ys), max(xs), max(ys)

def user_box(view: tuple, rotation: int, cropbox: tuple) -> tuple:
  x0, y0, x1, y1 = view
  pts = [ocr_layer.view_to_user(a, b, rotation, cropbox) for a, b in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
  xs = [p[0] for p in pts]
  ys = [p[1] for p in pts]
  return min(xs), min(ys), max(xs), max(ys)

def _user_to_view(x: float, y: float, rotation: int, crop: tuple) -> tuple:
  cx0, cy0, cx1, cy1 = crop
  if rotation == 90:
    return y - cy0, x - cx0
  if rotation == 180:
    return cx1 - x, y - cy0
  if rotation == 270:
    return cy1 - y, cx1 - x
  return x - cx0, cy1 - y

def read_region(page, rotation: int, cropbox: tuple, view: tuple, dpi: float = DPI, psm: str = "11", budget_s: float = BUDGET_S) -> tuple:
  info: dict = {}
  if not ocr_layer.available():
    info["error"] = "UNAVAILABLE"
    return [], info

  started = time.monotonic()
  try:
    from PIL import Image
    Wv, Hv = page.get_size()
    vx0, vy0, vx1, vy1 = view
    vx0, vy0 = max(0.0, vx0), max(0.0, vy0)
    vx1, vy1 = min(Wv, vx1), min(Hv, vy1)
    if vx1 - vx0 < 8.0 or vy1 - vy0 < 8.0:
      info["error"] = "EMPTY_BOX"
      return [], info
    scale = dpi / 72.0
    longest = max(vx1 - vx0, vy1 - vy0) * scale
    if longest > MAX_SIDE_PX:
      scale *= MAX_SIDE_PX / longest
    img = page.render(scale=scale, crop=(vx0, Hv - vy1, Wv - vx1, vy0)).to_pil().convert("L")
  except Exception:
    info["error"] = "RENDER"
    return [], info

  rows = ocr_layer._tsv(img, max(5.0, budget_s - (time.monotonic() - started)), psm)
  words = []
  for r in rows:
    if r["conf"] < MIN_CONF or r["h"] < MIN_H_PX or not any(ch.isalnum() for ch in r["text"]):
      continue
    if len(r["text"]) <= 2 and r["conf"] < MIN_CONF_SHORT and not r["text"].isdigit():
      continue
    a0, b0 = vx0 + r["l"] / scale, vy0 + r["t"] / scale
    a1, b1 = vx0 + (r["l"] + r["w"]) / scale, vy0 + (r["t"] + r["h"]) / scale
    words.append(ocr_layer._build_word(r["text"], a0, b0, a1, b1, 0.0, rotation, cropbox))
  info.update(words=len(words), dpi=round(scale * 72.0, 1), seconds=round(time.monotonic() - started, 2))
  return words, info

RULE_FRAC = 0.75
INK_LEVEL = 200
MIN_BAND_PX = 10
BAND_PAD_PX = 3

def _bands(flags, min_len: int) -> list:
  """Runs of False in flags (the space between two rules) as (start, end)."""
  out, start = [], None
  for i, f in enumerate(list(flags) + [True]):
    if not f and start is None:
      start = i
    elif f and start is not None:
      if i - start >= min_len:
        out.append((start, i))
      start = None
  return out

def read_cells(page, rotation: int, cropbox: tuple, view: tuple, dpi: float = 450.0, budget_s: float = BUDGET_S) -> tuple:
  info: dict = {}
  if not ocr_layer.available():
    info["error"] = "UNAVAILABLE"
    return [], info
  started = time.monotonic()
  try:
    import numpy as np
    Wv, Hv = page.get_size()
    vx0, vy0, vx1, vy1 = view
    vx0, vy0, vx1, vy1 = max(0.0, vx0), max(0.0, vy0), min(Wv, vx1), min(Hv, vy1)
    if vx1 - vx0 < 8.0 or vy1 - vy0 < 8.0:
      info["error"] = "EMPTY_BOX"
      return [], info
    scale = dpi / 72.0
    img = page.render(scale=scale, crop=(vx0, Hv - vy1, Wv - vx1, vy0)).to_pil().convert("L")
  except Exception:
    info["error"] = "RENDER"
    return [], info

  arr = np.asarray(img)
  ink = arr < INK_LEVEL
  h, w = ink.shape
  rules = ink.mean(axis=1) >= RULE_FRAC
  vrules = ink.mean(axis=0) >= RULE_FRAC
  words = []
  for b0, b1 in _bands(rules, MIN_BAND_PX):
    band = ink[b0:b1, :].copy()
    band[:, vrules] = False
    cols = np.where(band.any(axis=0))[0]
    if len(cols) == 0:
      continue
    c0, c1 = max(0, int(cols[0]) - BAND_PAD_PX), min(w, int(cols[-1]) + 1 + BAND_PAD_PX)
    cell = arr[b0:b1, c0:c1].copy()
    cell[:, vrules[c0:c1]] = 255
    rows_with_ink = np.where((cell < INK_LEVEL).any(axis=1))[0]

    if len(rows_with_ink) == 0:
      continue
    from PIL import Image
    cell_img = Image.fromarray(cell)
    rows = ocr_layer._tsv(cell_img, max(3.0, budget_s - (time.monotonic() - started)), "7")
    text = " ".join(r["text"] for r in sorted(rows, key=lambda r: r["l"]) if any(ch.isalnum() for ch in r["text"]))
    if not text.strip():
      continue

    a0, a1 = vx0 + c0 / scale, vx0 + c1 / scale
    t0, t1 = vy0 + b0 / scale, vy0 + b1 / scale
    words.append(ocr_layer._build_word(text.strip(), a0, t0, a1, t1, 0.0, rotation, cropbox))
  info.update(words=len(words), dpi=round(scale * 72.0, 1), seconds=round(time.monotonic() - started, 2))
  return words, info
