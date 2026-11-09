from __future__ import annotations
import io
import numpy as np
from app.modules.drawings_boq.takeoff.prep import ocr_layer

DARK = 140
MIN_SIDE_PX = 2
MAX_SIDE_SHARE = 0.5
MAX_CLUSTERS = 20000
OCR_TIMEOUT_S = 40.0
OCR_UPSCALE = 2

def _image(png: bytes):
  from PIL import Image
  return Image.open(io.BytesIO(png)).convert("L")

def _label(mask: np.ndarray) -> list:
  h, w = mask.shape
  parent: list = []
  def find(a: int) -> int:
    while parent[a] != a:
      parent[a] = parent[parent[a]]
      a = parent[a]
      
    return a
  prev: list = []
  runs_all: list = []
  for y in range(h):
    row = mask[y]
    if not row.any():
      prev = []
      continue
    d = np.diff(np.concatenate(([0], row.astype(np.int8), [0])))
    starts, ends = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
    cur = []
    for s, e in zip(starts, ends):
      idx = len(parent)
      parent.append(idx)
      runs_all.append((int(s), int(e), y))
      for ps, pe, pi in prev:
        if ps < e + 1 and s < pe + 1:
          a, b = find(idx), find(pi)
          if a != b:
            parent[a] = b
            
      cur.append((int(s), int(e), idx))
    prev = cur
  boxes: dict = {}
  for i, (s, e, y) in enumerate(runs_all):
    r = find(i)
    b = boxes.get(r)
    boxes[r] = [s, y, e, y + 1] if b is None else [min(b[0], s), min(b[1], y), max(b[2], e), max(b[3], y + 1)]
  return list(boxes.values())

def ink_clusters(png: bytes) -> list:
  img = _image(png)
  mask = np.asarray(img) < DARK
  if mask.size == 0 or int(mask.sum()) > mask.size * 0.6:
    return []
  
  h, w = mask.shape
  out = [b for b in _label(mask) if b[2] - b[0] >= MIN_SIDE_PX or b[3] - b[1] >= MIN_SIDE_PX]
  out = [b for b in out if (b[2] - b[0]) <= MAX_SIDE_SHARE * w and (b[3] - b[1]) <= MAX_SIDE_SHARE * h]
  return out[:MAX_CLUSTERS]

def ocr_words(png: bytes) -> list | None:
  if not ocr_layer.available():
    return None
  from PIL import Image
  img = _image(png)
  big = img.resize((img.width * OCR_UPSCALE, img.height * OCR_UPSCALE), Image.LANCZOS)
  rows = ocr_layer._tsv(big, OCR_TIMEOUT_S, "11")
  k = float(OCR_UPSCALE)
  return [{"text": r["text"], "conf": float(r["conf"]), "box": [r["l"] / k, r["t"] / k, (r["l"] + r["w"]) / k, (r["t"] + r["h"]) / k]} for r in rows]

def support_inputs(png: bytes) -> tuple:
  try:
    return ocr_words(png), ink_clusters(png)
  except Exception:
    return None, None
