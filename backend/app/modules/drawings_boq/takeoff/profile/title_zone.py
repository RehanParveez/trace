from __future__ import annotations
import math
import re
from collections import Counter

TOL_X = 0.08
TOL_Y = 0.08
WIDTH_RATIO = 1.5
SHARE_NEEDED = 0.5
MIN_PAGES = 2
CONSTANT_SHARE = 0.8
NUMBER_LIKE = re.compile(r"^[A-Z]{1,4}\s?-?\s?\d{1,3}[A-Z]?$")
SIDE_RIGHT, SIDE_BOTTOM = 0.70, 0.30

def _centre(b: list) -> tuple:
  return (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0

def _alike(c: dict, b: list) -> bool:
  cx, cy = _centre(b)
  w = max(b[2] - b[0], 1e-6)
  return abs(cx - c["cx"]) <= TOL_X and abs(cy - c["cy"]) <= TOL_Y and 1 / WIDTH_RATIO <= w / max(c["w"], 1e-6) <= WIDTH_RATIO

def learn(zones: list) -> list:
  clusters: list = []
  
  for idx, zone in enumerate(zones):
    for ph in zone:
      b = ph["b"]
      for c in clusters:
        if _alike(c, b):
          c["members"].append((idx, ph["t"], b))
          break
      else:
        cx, cy = _centre(b)
        clusters.append({"cx": cx, "cy": cy, "w": b[2] - b[0], "members": [(idx, ph["t"], b)]})
  need = max(MIN_PAGES, math.ceil(SHARE_NEEDED * len(zones)))
  
  out = []
  for c in clusters:
    pages = {m[0] for m in c["members"]}
    if len(pages) < need:
      continue
    
    texts = Counter(m[1].strip().upper() for m in c["members"])
    top, top_n = texts.most_common(1)[0]
    boxes = [m[2] for m in c["members"]]
    box = [round(sum(x[i] for x in boxes) / len(boxes), 4) for i in range(4)]
    cx, cy = _centre(box)
    like = sum(n for t, n in texts.items() if NUMBER_LIKE.match(t))
    out.append({"box": box, "pages": len(pages), "of": len(zones), "constant": top_n / len(c["members"]) >= CONSTANT_SHARE, "top_text": top[:40], "texts": len(texts),
      "number_like": round(like / len(c["members"]), 3), "side": "BOTTOM" if cy <= SIDE_BOTTOM else "RIGHT" if cx >= SIDE_RIGHT else "OTHER"})
  out.sort(key=lambda r: (-r["pages"], r["box"][1], r["box"][0]))
  return out

def side_of(boxes: list) -> tuple:
  count = Counter(b["side"] for b in boxes if b["side"] != "OTHER")
  if not count:
    return None, 0.0
  side, n = count.most_common(1)[0]
  return side, round(n / sum(count.values()), 3)
